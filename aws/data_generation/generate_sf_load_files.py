"""
Generate Salesforce-ready CSV load files from the ERP contact data.

Produces:
  sf_load_accounts.csv  — one Account per unique company name
  sf_load_contacts.csv  — 200 Contacts keyed to Accounts via ExternalId

These are loaded into the org via:
  sf data upsert bulk -o globallogistics-dev -f sf_load_accounts.csv -s Account -i ERP_External_Id__c
  sf data upsert bulk -o globallogistics-dev -f sf_load_contacts.csv  -s Contact -i ERP_External_Id__c
"""

import csv
import uuid
from pathlib import Path

CONTACTS_CSV = Path(__file__).parent / "salesforce_service_contacts.csv"

# Account companies from the generated data
ACCOUNTS = [
    "Global Logistics Inc.",
    "Acme Corp",
    "TechVentures LLC",
    "Harbor Freight",
    "NovaBridge Ltd",
]

# ── Build Accounts ──────────────────────────────────────────────────────────
account_rows = []
account_ext_id_map = {}  # name → external id

for name in ACCOUNTS:
    ext_id = f"ACC-{name.upper().replace(' ','_').replace('.','')[:20]}"
    account_ext_id_map[name] = ext_id
    account_rows.append({
        "ERP_External_Id__c": ext_id,
        "Name": name,
        "Industry": "Transportation and Logistics",
        "BillingCity": "Chicago",
        "BillingState": "IL",
        "BillingCountry": "US",
        "Phone": "+13125550100",
        "Website": "https://globallogisticsinc.com",
        "Description": "Global Logistics Inc. — mock ERP customer account for Data Cloud Identity Resolution demo",
    })

with open("sf_load_accounts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=account_rows[0].keys())
    w.writeheader()
    w.writerows(account_rows)
print(f"[Accounts] {len(account_rows)} rows → sf_load_accounts.csv")

# ── Build Contacts ───────────────────────────────────────────────────────────
with open(CONTACTS_CSV, newline="") as f:
    contacts = list(csv.DictReader(f))

contact_rows = []
for i, c in enumerate(contacts):
    account_name = c.get("account_name", "Global Logistics Inc.")
    acct_ext_id = account_ext_id_map.get(account_name, account_ext_id_map["Global Logistics Inc."])

    # External ID is the mock salesforce_id from our generator — stable across reruns
    ext_id = c["salesforce_id"]

    contact_rows.append({
        "ERP_External_Id__c": ext_id,
        "FirstName": c["first_name"],
        "LastName": c["last_name"],
        "Email": c["email_address"],
        "Phone": c["phone_number"],
        "Account.ERP_External_Id__c": acct_ext_id,   # relationship by external ID
        "LeadSource": "ERP Migration",
        "Description": (
            "Service Cloud contact imported from glERP mock — "
            "50 of these records share email/phone with ERP shipments table "
            "to demonstrate Data Cloud Identity Resolution merging."
        ),
    })

with open("sf_load_contacts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=contact_rows[0].keys())
    w.writeheader()
    w.writerows(contact_rows)
print(f"[Contacts] {len(contact_rows)} rows → sf_load_contacts.csv")
print()
print("Next steps:")
print("  1. Create custom field ERP_External_Id__c (Text 50, Unique) on Account and Contact")
print("  2. sf data upsert bulk -o globallogistics-dev -f sf_load_accounts.csv -s Account -i ERP_External_Id__c --wait 10")
print("  3. sf data upsert bulk -o globallogistics-dev -f sf_load_contacts.csv  -s Contact -i ERP_External_Id__c --wait 10")
