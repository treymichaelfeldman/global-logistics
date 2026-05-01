"""
glERP — Global Logistics ERP Mock System
Flask application serving a retro 90s-styled web interface
over port 5000 (proxied by nginx to 80 on EC2).

Environment variables:
    GLERP_SECRET_KEY   — Flask secret key
    GLERP_ADMIN_PASS   — Login password (default: gl3rp@dmin!)
    ATHENA_MODE        — Set to '1' to query Athena instead of CSV
    GLUE_DATABASE      — Glue DB name (Athena mode only)
    ATHENA_S3_OUTPUT   — s3:// path for Athena query results
    AWS_DEFAULT_REGION — AWS region
"""

import csv
import io
import os
import time
from datetime import datetime, timezone
from functools import wraps

import boto3
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("GLERP_SECRET_KEY", os.urandom(32))

ADMIN_PASSWORD_HASH = generate_password_hash(
    os.environ.get("GLERP_ADMIN_PASS", "gl3rp@dmin!")
)

ATHENA_MODE = os.environ.get("ATHENA_MODE", "0") == "1"
GLUE_DATABASE = os.environ.get("GLUE_DATABASE", "global_logistics_iceberg_db")
ATHENA_S3_OUTPUT = os.environ.get("ATHENA_S3_OUTPUT", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

DATA_CSV = os.path.join(os.path.dirname(__file__), "..", "data_generation", "salesforce_service_contacts.csv")
SHIPMENTS_CSV = os.path.join(os.path.dirname(__file__), "..", "data_generation", "shipments_export.csv")

VALID_STATUSES = ["In Transit", "Delayed", "Delivered", "Pending Callback"]
VALID_SENTIMENTS = ["Positive", "Neutral", "Frustrated"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_shipments_csv(rows: list[dict]) -> None:
    if not rows:
        return
    with open(SHIPMENTS_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _query_athena(sql: str) -> list[dict]:
    client = boto3.client("athena", region_name=AWS_REGION)
    resp = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": GLUE_DATABASE},
        ResultConfiguration={"OutputLocation": ATHENA_S3_OUTPUT},
    )
    exec_id = resp["QueryExecutionId"]

    for _ in range(30):
        status = client.get_query_execution(QueryExecutionId=exec_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            return []
        time.sleep(1)

    paginator = client.get_paginator("get_query_results")
    rows: list[dict] = []
    headers: list[str] = []
    for page in paginator.paginate(QueryExecutionId=exec_id):
        result_rows = page["ResultSet"]["Rows"]
        if not headers:
            headers = [col["VarCharValue"] for col in result_rows[0]["Data"]]
            result_rows = result_rows[1:]
        for row in result_rows:
            rows.append(
                {headers[i]: col.get("VarCharValue", "") for i, col in enumerate(row["Data"])}
            )
    return rows


def get_shipments(limit: int = 100, search: str = "") -> list[dict]:
    if ATHENA_MODE:
        where = f"WHERE LOWER(email_address) LIKE '%{search.lower()}%' OR erp_party_id LIKE '%{search.upper()}%'" if search else ""
        return _query_athena(f"SELECT * FROM shipments {where} LIMIT {limit}")
    rows = _read_csv(SHIPMENTS_CSV)
    if search:
        s = search.lower()
        rows = [r for r in rows if s in r.get("email_address", "").lower()
                or s in r.get("erp_party_id", "").lower()
                or s in r.get("last_name", "").lower()]
    return rows[:limit]


def get_dashboard_stats() -> dict:
    if ATHENA_MODE:
        counts = _query_athena("SELECT status, COUNT(*) AS cnt FROM shipments GROUP BY status")
        return {r["status"]: int(r["cnt"]) for r in counts}
    rows = _read_csv(SHIPMENTS_CSV)
    stats: dict = {}
    for r in rows:
        key = r.get("status", "Unknown")
        stats[key] = stats.get(key, 0) + 1
    return stats


# ---------------------------------------------------------------------------
# Routes — auth
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if check_password_hash(ADMIN_PASSWORD_HASH, pw):
            session["authenticated"] = True
            session.permanent = True
            return redirect(url_for("dashboard"))
        error = "ACCESS DENIED — INVALID PASSWORD"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — main screens
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    total = sum(stats.values())
    return render_template("dashboard.html", stats=stats, total=total)


@app.route("/shipments")
@login_required
def shipments():
    search = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 100))
    rows = get_shipments(limit=limit, search=search)
    return render_template("shipments.html", rows=rows, search=search, limit=limit)


@app.route("/shipments/<order_id>")
@login_required
def shipment_detail(order_id: str):
    all_rows = get_shipments(limit=9999)
    row = next((r for r in all_rows if r.get("order_id") == order_id), None)
    if row is None:
        flash("RECORD NOT FOUND IN DATABASE")
        return redirect(url_for("shipments"))
    return render_template(
        "shipment_detail.html",
        row=row,
        valid_statuses=VALID_STATUSES,
        valid_sentiments=VALID_SENTIMENTS,
    )


@app.route("/shipments/<order_id>/edit", methods=["POST"])
@login_required
def shipment_edit(order_id: str):
    new_status = request.form.get("status", "").strip()
    new_sentiment = request.form.get("sentiment_flag", "").strip()
    new_quote = request.form.get("quote_amount", "").strip()

    if new_status not in VALID_STATUSES:
        flash(f"INVALID STATUS: {new_status}")
        return redirect(url_for("shipment_detail", order_id=order_id))
    if new_sentiment not in VALID_SENTIMENTS:
        flash(f"INVALID SENTIMENT: {new_sentiment}")
        return redirect(url_for("shipment_detail", order_id=order_id))
    try:
        new_quote_float = round(float(new_quote), 2)
        if not (0 < new_quote_float <= 999999):
            raise ValueError
    except (ValueError, TypeError):
        flash("INVALID QUOTE AMOUNT — must be a positive number")
        return redirect(url_for("shipment_detail", order_id=order_id))

    all_rows = _read_csv(SHIPMENTS_CSV)
    updated = False
    for row in all_rows:
        if row.get("order_id") == order_id:
            row["status"] = new_status
            row["sentiment_flag"] = new_sentiment
            row["quote_amount"] = str(new_quote_float)
            row["last_updated"] = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
            updated = True
            break

    if not updated:
        flash("RECORD NOT FOUND — update aborted")
        return redirect(url_for("shipments"))

    _write_shipments_csv(all_rows)
    flash(f"RECORD UPDATED — {order_id[:8]}... saved successfully")
    return redirect(url_for("shipment_detail", order_id=order_id))


@app.route("/contacts")
@login_required
def contacts():
    rows = _read_csv(DATA_CSV)
    search = request.args.get("q", "").strip().lower()
    if search:
        rows = [r for r in rows if search in r.get("email_address", "").lower()
                or search in r.get("last_name", "").lower()]
    return render_template("contacts.html", rows=rows[:200], search=search)


@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(get_dashboard_stats())


@app.route("/health")
def health():
    return "OK", 200


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
