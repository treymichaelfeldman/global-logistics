# glERP × Salesforce Data Cloud — Demo Script
**Global Logistics Inc. | Identity Resolution Proof of Concept**

---

## Pre-Demo Checklist

- [ ] glERP running at `http://localhost:5000` (or EC2 public IP)
- [ ] Salesforce Data Cloud org open in a separate tab
- [ ] `salesforce_service_contacts.csv` imported as a Data Stream in Data Cloud
- [ ] Browser showing the glERP login screen

---

## Act 1 — "The Problem"  *(~2 min)*

**Open** `http://localhost:5000`

> *"This is glERP — Global Logistics Inc.'s legacy ERP system.
> It's been running since the late 90s. Thousands of customer shipment records
> live here and nowhere else. No Salesforce ID, no CRM linkage — just raw
> backend data that the service team has never been able to act on in real time."*

**Log in** — password: `gl3rp@dmin!`

> *"The moment you hit login, notice the 90s chrome — this is intentional.
> This is what the data looks like to the dev team: trapped behind a proprietary
> system with no native Salesforce connector."*

---

## Act 2 — "The Data"  *(~3 min)*

Click **[ SHIPMENTS ]**

> *"1,000 shipment records. Each one has three critical fields for Identity
> Resolution — an ERP Party ID, an email address, and a phone number.
> Without a connector, this data is invisible to your agents."*

Click any **ORDER ID** link to open a detail record.

Point to the yellow callout box at the bottom:

> *"This is the Data Cloud DMO mapping. Each field routes to a specific DMO:*
> - *`erp_party_id` → **Party Identification DMO** — this is the external key. Without this mapping, Data Cloud has no anchor to hang the identity on.*
> - *`email_address` → **Contact Point Email DMO***
> - *`phone_number` → **Contact Point Phone DMO***
>
> *These Contact Point DMOs are exactly what the Match Rules engine evaluates.
> Skip them, and your Identity Resolution rulesets have nothing to compare."*

---

## Act 3 — "The Bridge"  *(~2 min)*

Click **[ CONTACTS ]**

> *"This is your Service Cloud data — 200 existing contacts with standard
> 18-character Salesforce IDs. At first glance, zero overlap with the ERP.*
>
> *But look closer: 50 of these records share an exact email address or
> phone number with a record in the shipments table. Same person, two systems,
> two identities. Right now, your agents can't see it."*

Open the **API Stats** (`/api/stats`) in a new tab:

```
{"Delayed":259,"Delivered":218,"In Transit":279,"Pending Callback":244}
```

> *"244 customers are flagged 'Pending Callback'. Without Identity Resolution,
> your agents don't know which of those map to open Service Cloud cases."*

---

## Act 4 — "The Connection"  *(~4 min)*

Switch to **Salesforce Data Cloud**.

> *"The bridge is the Amazon S3 File Federation connector — also called Zero Copy.
> No ETL pipeline, no middleware. Data Cloud reaches directly into this S3 bucket
> and reads the Parquet files we just wrote.*
>
> S3 bucket: `s3://global-logistics-erp-mock-6p9mqdtq/data/shipments/`"*

Walk through the Data Stream setup:
1. **Setup → Data Cloud → Amazon S3 File Federation**
2. New Connected Source → paste the **Role ARN** from `aws/iam/create_role.sh`
3. Map `erp_party_id` → Party Identification DMO → `sourceSystemId`
4. Map `email_address` → Contact Point Email DMO → `emailAddress`
5. Map `phone_number` → Contact Point Phone DMO → `phoneNumber`

> *"This is the step most implementations get wrong. They map everything to
> the Individual DMO directly and wonder why match rules never fire.
> The engine needs the Contact Point DMOs to have normalized attributes to evaluate."*

---

## Act 5 — "The Merge"  *(~3 min)*

Navigate to **Identity Resolution → Rulesets → New Ruleset**

Configure two match rules:
- Rule 1: **Exact match** on `Contact Point Email → emailAddress`
- Rule 2: **Exact match** on `Contact Point Phone → formattedE164PhoneNumber`

Run the ruleset.

> *"Watch the Unified Individual count. Those 50 records we seeded — with identical
> emails and phone numbers across both systems — will collapse into Unified Profiles.
> One person. Two source records. One actionable identity."*

Navigate to a **Unified Profile** that merged:

> *"This profile now shows the ERP shipment history alongside the Service Cloud case.
> Your agent can see the 'Pending Callback' status, the quote amount, the sentiment flag —
> all surfaced in the Contact record. No migration, no integration project, no ETL."*

---

## Act 6 — "The Payoff"  *(~2 min)*

> *"The 244 'Pending Callback' records in glERP — those were invisible to your service team.*
>
> *After Identity Resolution, the subset that matched Service Cloud contacts are now
> surfaced as Unified Profiles. You can build a Data Cloud segment on:*
> - *`status = Pending Callback`*
> - *`sentiment_flag = Frustrated`*
>
> *And activate that segment directly to a Flow, an Agentforce action, or an outbound
> campaign — powered entirely by the ERP data that was locked in a 90s system
> ten minutes ago."*

---

## Key Talking Points

| What | Why it matters |
|---|---|
| Party Identification DMO | The anchor — without it, the external ID has no DMO home |
| Contact Point Email / Phone DMOs | What Match Rules actually evaluate |
| ~50 overlap records in the CSV | Concrete, auditable proof that merge happened |
| S3 Parquet (no ETL) | Zero Copy — no pipeline to build or maintain |
| `Pending Callback` + `Frustrated` segment | Immediate business value post-merge |

---

## Credentials & Endpoints

| Item | Value |
|---|---|
| glERP URL (local) | `http://localhost:5000` |
| glERP Password | `gl3rp@dmin!` |
| S3 Bucket | `global-logistics-erp-mock-6p9mqdtq` |
| S3 Data Path | `s3://global-logistics-erp-mock-6p9mqdtq/data/shipments/` |
| AWS Account | `598831254072` |
| AWS Region | `us-east-1` |
| IAM Role (create via) | `aws/iam/create_role.sh` |

---

## Restart glERP Anytime

```bash
cd "/Users/trey/Desktop/Projects/Global Logistics Demo/aws"
GLERP_ADMIN_PASS="gl3rp@dmin!" GLERP_SECRET_KEY="demo-secret-key-gli-2026" \
  .venv/bin/python gleRP/app.py
```

Then open `http://localhost:5000`
