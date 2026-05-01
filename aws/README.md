# Global Logistics Inc. — AWS ERP Mock Environment

Mock legacy ERP backend for Salesforce Data Cloud Identity Resolution demos.
Stores shipment data as Apache Iceberg tables in S3, cataloged via AWS Glue,
and exposed through the **glERP** retro web interface on EC2.

---

## Architecture

```
EC2 (glERP Flask App)
    └── nginx :80 → gunicorn :5000 → Flask app
              ├── Reads shipments CSV (local, default)
              └── OR queries Athena → Glue Catalog → S3 Iceberg (ATHENA_MODE=1)

Salesforce Data Cloud
    └── Amazon S3 File Federation (Zero Copy)
              └── IAM Role (SalesforceDataCloudRole)
                        ├── s3:GetObject / s3:ListBucket
                        └── glue:GetTable / GetDatabase / GetPartitions
```

---

## Quick Start

### 1. Provision Infrastructure

```bash
cd infra
pip install boto3
python setup_infrastructure.py --region us-east-1
# Writes infra_config.json with bucket name
```

### 2. Generate Mock Data

```bash
cd data_generation
pip install awswrangler pandas
python generate_data.py
# Outputs:
#   - Iceberg table in S3 → Glue: global_logistics_iceberg_db.shipments (1,000 rows)
#   - salesforce_service_contacts.csv (200 rows, ~50 overlap for Identity Resolution)
```

### 3. Create IAM Role for Salesforce Data Cloud

```bash
cd iam
export BUCKET_SUFFIX=<your-suffix>          # from infra_config.json
export AWS_ACCOUNT_ID=<your-account-id>
export EXTERNAL_ID=<generate-a-uuid>
export SF_DC_AWS_ACCOUNT=<salesforce-dc-aws-account-id>  # from SF Setup
bash create_role.sh
```

Take the output **Role ARN** and **External ID** into:
`Salesforce Setup → Data Cloud → Amazon S3 File Federation → New Connected Source`

### 4. Launch EC2 (glERP Web Interface)

1. Launch **Amazon Linux 2023**, `t3.micro`, with the `SalesforceDataCloudRole` instance profile.
2. Paste `ec2_userdata.sh` as User Data (or run it manually as root after launch).
3. Open port **80** in the Security Group.
4. Deploy the app code:

```bash
EC2_HOST=<public-ip> KEY_FILE=~/.ssh/my-key.pem bash deploy_app.sh
```

5. Visit `http://<EC2-PUBLIC-IP>/` — default password: `gl3rp@dmin!`

---

## Data Schema → Salesforce Data Cloud DMO Mapping

| Column | DMO | Notes |
|---|---|---|
| `erp_party_id` | **Party Identification DMO** | `partyIdentificationType = ERP`, `sourceSystemId` |
| `email_address` | **Contact Point Email DMO** | Primary match key for Identity Resolution |
| `phone_number` | **Contact Point Phone DMO** | Secondary match key |
| `first_name` / `last_name` | Individual DMO | Name normalization rule support |
| `order_id` | Sales Order DMO (optional) | Can link to Order object in SF |

### Identity Resolution Proof

`salesforce_service_contacts.csv` contains 200 Service Cloud contacts with standard
18-character Salesforce IDs. Approximately **50 records** share an `email_address`
or `phone_number` with the ERP shipments table. When both data streams land in
Data Cloud and you configure match rules on Contact Point Email / Phone,
those 50 records will **merge** — proving cross-source Identity Resolution.

---

## Environment Variables (glERP App)

| Variable | Default | Description |
|---|---|---|
| `GLERP_SECRET_KEY` | random | Flask session secret key |
| `GLERP_ADMIN_PASS` | `gl3rp@dmin!` | Login password — **change this** |
| `ATHENA_MODE` | `0` | Set to `1` to query Athena live |
| `GLUE_DATABASE` | `global_logistics_iceberg_db` | Glue DB name |
| `ATHENA_S3_OUTPUT` | — | s3:// path for Athena query results |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |

---

## File Map

```
aws/
├── infra/
│   └── setup_infrastructure.py   # Boto3 IaC: S3 bucket + Glue DB
├── data_generation/
│   └── generate_data.py          # Iceberg data + salesforce_service_contacts.csv
├── iam/
│   ├── salesforce_datacloud_policy.json   # IAM permission policy
│   ├── salesforce_datacloud_trust_policy.json  # Trust policy (sts:AssumeRole)
│   └── create_role.sh            # CLI helper to create the role
├── gleRP/
│   ├── app.py                    # Flask application
│   ├── requirements.txt
│   └── templates/
│       ├── base.html             # 90s ERP chrome
│       ├── login.html
│       ├── dashboard.html
│       ├── shipments.html
│       ├── shipment_detail.html
│       └── contacts.html
├── ec2_userdata.sh               # EC2 bootstrap script (Amazon Linux 2023)
└── deploy_app.sh                 # Local → EC2 deploy helper
```
