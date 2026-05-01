#!/usr/bin/env bash
# =============================================================================
# glERP Deploy Script
# =============================================================================
# Packages the gleRP app directory and syncs it to the EC2 instance.
# Run this from your local machine after initial EC2 bootstrap.
#
# Usage:
#   EC2_HOST=<public-ip-or-dns> KEY_FILE=~/.ssh/my-key.pem bash deploy_app.sh
# =============================================================================

set -euo pipefail

: "${EC2_HOST:?Set EC2_HOST env var to the instance public IP or DNS}"
: "${KEY_FILE:?Set KEY_FILE env var to your PEM key path}"

APP_DIR="/opt/glerp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARBALL="/tmp/glerp_deploy.tar.gz"

echo "[deploy] Packaging application..."
tar -czf "${TARBALL}" \
    -C "${SCRIPT_DIR}" \
    gleRP/ \
    data_generation/

echo "[deploy] Uploading to EC2: ${EC2_HOST}"
scp -i "${KEY_FILE}" -o StrictHostKeyChecking=no "${TARBALL}" "ec2-user@${EC2_HOST}:/tmp/"

echo "[deploy] Extracting and restarting service..."
ssh -i "${KEY_FILE}" -o StrictHostKeyChecking=no "ec2-user@${EC2_HOST}" bash <<'REMOTE'
    set -euo pipefail
    sudo tar -xzf /tmp/glerp_deploy.tar.gz -C /opt/glerp --strip-components=0
    sudo chown -R glerp:glerp /opt/glerp
    sudo /opt/glerp/venv/bin/pip install -r /opt/glerp/gleRP/requirements.txt -q
    sudo systemctl restart glerp
    echo "Service status:"
    sudo systemctl status glerp --no-pager -l
REMOTE

echo "[deploy] Done. App available at http://${EC2_HOST}/"
