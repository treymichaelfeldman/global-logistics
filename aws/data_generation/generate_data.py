"""
Global Logistics Inc. — Mock Data Generator
============================================
Produces:
  1. 1,000-row shipments dataset:
       - Written to S3 as Parquet (partitioned by status) for Data Cloud S3
         File Federation ingestion.
       - Written locally as shipments_export.csv for glERP web app.

  2. salesforce_service_contacts.csv — 200 Service Cloud records where ~50
     intentionally share an email_address or phone_number with the shipments
     table to prove Identity Resolution merging in Data Cloud.

DMO Mapping:
  erp_party_id  → Party Identification DMO  (externalSourceId)
  email_address → Contact Point Email DMO
  phone_number  → Contact Point Phone DMO

Usage:
    python generate_data.py
    python generate_data.py --config ../infra/infra_config.json
"""

import argparse
import io
import json
import os
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = Path(__file__).parent.parent / "infra" / "infra_config.json"
TABLE_NAME = "shipments"
SALESFORCE_CSV = "salesforce_service_contacts.csv"
SHIPMENTS_CSV = "shipments_export.csv"

STATUSES = ["In Transit", "Delayed", "Delivered", "Pending Callback"]
SENTIMENTS = ["Positive", "Neutral", "Frustrated"]

FIRST_NAMES = [
    "James", "Maria", "David", "Sarah", "Michael", "Jennifer", "Robert", "Linda",
    "William", "Patricia", "Richard", "Barbara", "Joseph", "Susan", "Thomas", "Jessica",
    "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy", "Matthew", "Betty",
    "Anthony", "Margaret", "Donald", "Sandra", "Mark", "Ashley", "Paul", "Dorothy",
    "Steven", "Kimberly", "Andrew", "Emily", "Kenneth", "Donna", "Joshua", "Michelle",
    "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Timothy", "Deborah",
    "Ronald", "Stephanie",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "protonmail.com", "icloud.com", "globallogisticsinc.com",
]


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def erp_id() -> str:
    return "ERP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def email(first: str, last: str) -> str:
    sep = random.choice([".", "_", ""])
    num = random.choice(["", str(random.randint(1, 99))])
    return f"{first.lower()}{sep}{last.lower()}{num}@{random.choice(EMAIL_DOMAINS)}"


def phone() -> str:
    return f"+1{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"


def timestamp(days_back: int = 365) -> datetime:
    now = datetime.now(tz=timezone.utc)
    return now - timedelta(seconds=random.randint(0, days_back * 86400))


def sf_id() -> str:
    return "003" + "".join(random.choices(string.ascii_letters + string.digits, k=15))


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_shipments(n: int = 1000) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        rows.append({
            "order_id": str(uuid.uuid4()),
            "erp_party_id": erp_id(),
            "first_name": first,
            "last_name": last,
            "email_address": email(first, last),
            "phone_number": phone(),
            "status": random.choice(STATUSES),
            "quote_amount": round(random.uniform(100.0, 5000.0), 2),
            "sentiment_flag": random.choice(SENTIMENTS),
            "last_updated": timestamp(),
        })
    df = pd.DataFrame(rows)
    df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True)
    return df


def generate_sf_contacts(shipments_df: pd.DataFrame, total: int = 200, overlap: int = 50) -> pd.DataFrame:
    overlap_rows = shipments_df.sample(n=overlap, random_state=42)[
        ["first_name", "last_name", "email_address", "phone_number"]
    ].copy()
    overlap_rows["salesforce_id"] = [sf_id() for _ in range(overlap)]
    overlap_rows["account_name"] = "Global Logistics Inc."
    overlap_rows["source"] = "ServiceCloud"

    pure = []
    for _ in range(total - overlap):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        pure.append({
            "salesforce_id": sf_id(),
            "first_name": first,
            "last_name": last,
            "email_address": email(first, last),
            "phone_number": phone(),
            "account_name": random.choice([
                "Acme Corp", "TechVentures LLC", "Harbor Freight",
                "NovaBridge Ltd", "Global Logistics Inc.",
            ]),
            "source": "ServiceCloud",
        })
    return (
        pd.concat([overlap_rows, pd.DataFrame(pure)], ignore_index=True)
        .sample(frac=1, random_state=99)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# S3 upload — Parquet (no Glue dependency)
# ---------------------------------------------------------------------------

def upload_to_s3(df: pd.DataFrame, bucket: str, region: str) -> None:
    """
    Upload shipments as Parquet files partitioned by status to:
        s3://<bucket>/data/shipments/status=<value>/part-0.parquet

    This layout is directly readable by the Salesforce Data Cloud
    S3 File Federation connector without requiring Glue.
    """
    s3 = boto3.client("s3", region_name=region)
    print(f"[S3] Uploading Parquet partitions to s3://{bucket}/data/shipments/")

    for status_val, partition_df in df.groupby("status"):
        # Parquet can't serialize timezone-aware datetimes in all versions;
        # convert to string for maximum compatibility with Data Cloud ingest.
        part = partition_df.copy()
        part["last_updated"] = part["last_updated"].astype(str)

        buf = io.BytesIO()
        part.to_parquet(buf, index=False, engine="pyarrow")
        buf.seek(0)

        safe_key = status_val.replace(" ", "_")
        key = f"data/shipments/status={safe_key}/part-0.parquet"
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue(), ContentType="application/octet-stream")
        print(f"  ✓ status={safe_key}  ({len(partition_df):,} rows)")

    # Also upload a single combined CSV for easy Data Cloud preview
    csv_buf = io.BytesIO()
    export = df.copy()
    export["last_updated"] = export["last_updated"].astype(str)
    export.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    s3.put_object(Bucket=bucket, Key="data/shipments/shipments_full.csv", Body=csv_buf.getvalue(), ContentType="text/csv")
    print(f"  ✓ shipments_full.csv  (combined, {len(df):,} rows)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GLI ERP mock data")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}. Run setup_infrastructure.py first.")
        raise SystemExit(1)

    with open(config_path) as fh:
        config = json.load(fh)

    bucket = config["bucket_name"]
    region = config["region"]

    print("=== Global Logistics Inc. — Data Generation ===")
    print(f"Bucket : s3://{bucket}")
    print(f"Region : {region}\n")

    random.seed(42)
    shipments_df = generate_shipments(1000)
    print(f"[Data] Generated {len(shipments_df):,} shipment rows")

    # Local CSV for glERP (no AWS needed at runtime)
    local_export = shipments_df.copy()
    local_export["last_updated"] = local_export["last_updated"].astype(str)
    local_export.to_csv(SHIPMENTS_CSV, index=False)
    print(f"[Data] Saved local glERP CSV → {os.path.abspath(SHIPMENTS_CSV)}")

    sf_df = generate_sf_contacts(shipments_df, total=200, overlap=50)
    sf_df.to_csv(SALESFORCE_CSV, index=False)
    print(f"[Data] Saved {len(sf_df):,} Service Cloud contacts → {os.path.abspath(SALESFORCE_CSV)}")
    print(f"       50 records share email/phone with shipments (Identity Resolution overlap)")

    upload_to_s3(shipments_df, bucket, region)

    print("\n✓ Done.")
    print(f"  S3 data path : s3://{bucket}/data/shipments/")
    print(f"  Local CSV    : {os.path.abspath(SHIPMENTS_CSV)}")
    print(f"  SF Contacts  : {os.path.abspath(SALESFORCE_CSV)}")
    print("\nNext: cd ../gleRP && python app.py")


if __name__ == "__main__":
    main()
