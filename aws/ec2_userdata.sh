#!/usr/bin/env bash
# =============================================================================
# glERP EC2 Bootstrap — User Data Script
# =============================================================================
# Launch an Amazon Linux 2023 t3.micro (or larger) with this as User Data.
# Installs Python 3.11, nginx, the glERP Flask app, and configures systemd.
#
# Required EC2 instance setup before launching:
#   1. IAM Instance Profile with the SalesforceDataCloudRole policy attached
#      (so boto3 picks up credentials via IMDS automatically).
#   2. Security Group: inbound TCP 80, 443 (and optionally 22 for SSH).
#   3. Set the environment variables below OR replace defaults before launch.
#
# Cost optimization: t3.micro in us-east-1 = ~$0.0104/hr (~$7.50/month).
# =============================================================================

set -euo pipefail

# ── Configurable values ────────────────────────────────────────────────────
GLERP_ADMIN_PASS="${GLERP_ADMIN_PASS:-gl3rp@dmin!}"
GLERP_SECRET_KEY="${GLERP_SECRET_KEY:-$(openssl rand -hex 32)}"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
APP_DIR="/opt/glerp"
APP_USER="glerp"
# ──────────────────────────────────────────────────────────────────────────

log() { echo "[userdata] $*" | tee -a /var/log/glerp-setup.log; }

log "=== glERP Bootstrap Start ==="

# ── System packages ────────────────────────────────────────────────────────
log "Installing system packages..."
dnf update -y
dnf install -y python3.11 python3.11-pip python3.11-devel nginx git gcc openssl

# ── App user ──────────────────────────────────────────────────────────────
log "Creating app user: ${APP_USER}"
useradd -r -s /sbin/nologin -d "${APP_DIR}" "${APP_USER}" || true

# ── Clone / copy app ──────────────────────────────────────────────────────
log "Setting up application directory: ${APP_DIR}"
mkdir -p "${APP_DIR}"

# Copy from EC2 instance store if you used an AMI bake, or pull from S3:
# aws s3 cp s3://your-deploy-bucket/glerp.tar.gz /tmp/ && tar -xz -C "${APP_DIR}" -f /tmp/glerp.tar.gz
# For a demo, we write the app inline below (see deploy_app.sh for the real workflow).

# ── Python virtual environment ────────────────────────────────────────────
log "Creating Python virtualenv..."
python3.11 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip wheel

# Install requirements (assumes gleRP/requirements.txt was copied to APP_DIR)
if [ -f "${APP_DIR}/requirements.txt" ]; then
    "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
fi

# ── Environment file ──────────────────────────────────────────────────────
log "Writing .env file..."
cat > "${APP_DIR}/.env" <<ENV
GLERP_SECRET_KEY=${GLERP_SECRET_KEY}
GLERP_ADMIN_PASS=${GLERP_ADMIN_PASS}
AWS_DEFAULT_REGION=${AWS_REGION}
ATHENA_MODE=0
GLUE_DATABASE=global_logistics_iceberg_db
ENV
chmod 600 "${APP_DIR}/.env"

# ── systemd service ───────────────────────────────────────────────────────
log "Installing systemd service..."
cat > /etc/systemd/system/glerp.service <<SERVICE
[Unit]
Description=glERP - Global Logistics ERP Mock
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5000 \
    --timeout 60 \
    --access-logfile /var/log/glerp-access.log \
    --error-logfile /var/log/glerp-error.log \
    gleRP.app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
touch /var/log/glerp-access.log /var/log/glerp-error.log
chown "${APP_USER}:${APP_USER}" /var/log/glerp-access.log /var/log/glerp-error.log

# ── nginx configuration ───────────────────────────────────────────────────
log "Configuring nginx..."
cat > /etc/nginx/conf.d/glerp.conf <<NGINX
server {
    listen 80;
    server_name _;

    # Security headers (minimal for demo)
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # Block direct access to .env or internal paths
    location ~ /\. { deny all; }
}
NGINX

# Remove default nginx config
rm -f /etc/nginx/conf.d/default.conf

nginx -t
systemctl enable nginx
systemctl start nginx

# ── Start app ─────────────────────────────────────────────────────────────
log "Enabling and starting glERP service..."
systemctl daemon-reload
systemctl enable glerp
systemctl start glerp

log "=== glERP Bootstrap Complete ==="
log "Application accessible at http://<EC2-PUBLIC-IP>/"
log "Default password stored in ${APP_DIR}/.env (GLERP_ADMIN_PASS)"
