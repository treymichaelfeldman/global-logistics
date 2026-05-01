#!/usr/bin/env bash
# glERP EC2 Bootstrap — Amazon Linux 2023 ARM64 (t4g.nano)
set -euo pipefail

BUCKET="global-logistics-erp-mock-6p9mqdtq"
REGION="us-east-1"
APP_DIR="/opt/glerp"
APP_USER="glerp"
GLERP_ADMIN_PASS="gl3rp@dmin!"
GLERP_SECRET_KEY="gli-demo-secret-2026-$(openssl rand -hex 8)"

log() { echo "[glerp-init] $*" | tee -a /var/log/glerp-init.log; }
log "=== Bootstrap start ==="

# System packages
dnf update -y -q
dnf install -y -q python3.11 python3.11-pip nginx

# App user + dir
useradd -r -s /sbin/nologin "$APP_USER" || true
mkdir -p "$APP_DIR"

# Pull app bundle from S3
log "Fetching app bundle from S3..."
aws s3 cp "s3://${BUCKET}/deploy/glerp_bundle.tar.gz" /tmp/glerp_bundle.tar.gz \
  --region "$REGION"
tar -xzf /tmp/glerp_bundle.tar.gz -C "$APP_DIR"

# Python venv
log "Installing Python dependencies..."
python3.11 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip wheel -q
"$APP_DIR/.venv/bin/pip" install flask werkzeug gunicorn boto3 pandas pyarrow -q

# Environment file
cat > "$APP_DIR/.env" <<ENV
GLERP_SECRET_KEY=${GLERP_SECRET_KEY}
GLERP_ADMIN_PASS=${GLERP_ADMIN_PASS}
AWS_DEFAULT_REGION=${REGION}
ATHENA_MODE=0
GLUE_DATABASE=global_logistics_iceberg_db
ENV
chmod 600 "$APP_DIR/.env"

# Patch app.py paths to use absolute paths under APP_DIR
sed -i "s|os.path.join(os.path.dirname(__file__), \"..\", \"data_generation\", \"salesforce_service_contacts.csv\")|\"${APP_DIR}/data_generation/salesforce_service_contacts.csv\"|g" "$APP_DIR/gleRP/app.py"
sed -i "s|os.path.join(os.path.dirname(__file__), \"..\", \"data_generation\", \"shipments_export.csv\")|\"${APP_DIR}/data_generation/shipments_export.csv\"|g" "$APP_DIR/gleRP/app.py"

# systemd service
cat > /etc/systemd/system/glerp.service <<SERVICE
[Unit]
Description=glERP - Global Logistics ERP
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn --workers 1 --bind 127.0.0.1:5000 --timeout 60 gleRP.app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

# nginx
cat > /etc/nginx/conf.d/glerp.conf <<NGINX
server {
    listen 80 default_server;
    server_name _;
    add_header X-Frame-Options SAMEORIGIN;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 60s;
    }
    location ~ /\. { deny all; }
}
NGINX
rm -f /etc/nginx/conf.d/default.conf

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

systemctl daemon-reload
systemctl enable --now nginx
systemctl enable --now glerp

log "=== Bootstrap complete. glERP running on port 80. ==="
