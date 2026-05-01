"""
Global Logistics Inc. — AWS Infrastructure Setup
Creates the S3 bucket and Glue database required for the
Salesforce Data Cloud Zero-Copy (Amazon S3 File Federation) connector.

Usage:
    python setup_infrastructure.py [--region us-east-1]
"""

import argparse
import json
import random
import string
import sys

import boto3
from botocore.exceptions import ClientError


GLUE_DATABASE = "global_logistics_iceberg_db"
BUCKET_SUFFIX_LENGTH = 8


def random_suffix(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def create_bucket(s3_client, bucket_name: str, region: str) -> str:
    print(f"[S3] Creating bucket: {bucket_name} in {region}")
    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        # Block all public access
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        # Enable versioning (Iceberg benefits from this)
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"},
        )
        # Server-side encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
        )
        print(f"[S3]  Bucket ready: s3://{bucket_name}")
        return bucket_name
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print(f"[S3]  Bucket already exists and is owned by you — reusing.")
            return bucket_name
        raise


def create_glue_database(glue_client, bucket_name: str) -> None:
    print(f"[Glue] Creating database: {GLUE_DATABASE}")
    try:
        glue_client.create_database(
            DatabaseInput={
                "Name": GLUE_DATABASE,
                "Description": "Global Logistics Inc. ERP mock — Apache Iceberg tables for Salesforce Data Cloud Zero-Copy connector",
                "LocationUri": f"s3://{bucket_name}/",
            }
        )
        print(f"[Glue]  Database ready: {GLUE_DATABASE}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "AlreadyExistsException":
            print("[Glue]  Database already exists — reusing.")
        else:
            raise


def write_config(bucket_name: str, region: str) -> None:
    """Persist bucket name so the data-gen script can read it without re-prompting."""
    config = {"bucket_name": bucket_name, "region": region, "glue_database": GLUE_DATABASE}
    config_path = "infra_config.json"
    with open(config_path, "w") as fh:
        json.dump(config, fh, indent=2)
    print(f"[Config] Saved to {config_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision GLI ERP mock infrastructure")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    args = parser.parse_args()

    region = args.region
    bucket_name = f"global-logistics-erp-mock-{random_suffix(BUCKET_SUFFIX_LENGTH)}"

    session = boto3.Session(region_name=region)
    s3_client = session.client("s3")
    glue_client = session.client("glue")

    bucket_name = create_bucket(s3_client, bucket_name, region)
    create_glue_database(glue_client, bucket_name)
    write_config(bucket_name, region)

    print("\n✓ Infrastructure provisioned successfully.")
    print(f"  Bucket : s3://{bucket_name}")
    print(f"  Database: {GLUE_DATABASE}")
    print(f"  Region  : {region}")
    print("\nNext step: python ../data_generation/generate_data.py")


if __name__ == "__main__":
    main()
