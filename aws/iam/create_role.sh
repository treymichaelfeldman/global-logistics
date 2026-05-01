#!/usr/bin/env bash
# Convenience script — creates the Salesforce Data Cloud IAM role and attaches the policy.
# Prerequisites: AWS CLI configured with sufficient IAM permissions.
# Usage: BUCKET_SUFFIX=abc12345 AWS_ACCOUNT_ID=123456789012 bash create_role.sh

set -euo pipefail

ROLE_NAME="SalesforceDataCloudRole"
POLICY_NAME="SalesforceDataCloudPolicy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

: "${BUCKET_SUFFIX:?Must set BUCKET_SUFFIX env var}"
: "${AWS_ACCOUNT_ID:?Must set AWS_ACCOUNT_ID env var}"
: "${EXTERNAL_ID:?Must set EXTERNAL_ID env var}"
: "${SF_DC_AWS_ACCOUNT:?Must set SF_DC_AWS_ACCOUNT env var (Salesforce Data Cloud AWS account ID)}"

# Substitute placeholders
POLICY_DOC=$(sed \
  -e "s/<BUCKET_SUFFIX>/${BUCKET_SUFFIX}/g" \
  -e "s/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g" \
  "${SCRIPT_DIR}/salesforce_datacloud_policy.json")

TRUST_DOC=$(sed \
  -e "s/<SALESFORCE_DATA_CLOUD_AWS_ACCOUNT_ID>/${SF_DC_AWS_ACCOUNT}/g" \
  -e "s/<EXTERNAL_ID>/${EXTERNAL_ID}/g" \
  "${SCRIPT_DIR}/salesforce_datacloud_trust_policy.json")

echo "[IAM] Creating role: ${ROLE_NAME}"
aws iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document "${TRUST_DOC}" \
  --description "Role assumed by Salesforce Data Cloud Zero-Copy S3 File Federation connector"

echo "[IAM] Creating inline policy: ${POLICY_NAME}"
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "${POLICY_DOC}"

ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)
echo ""
echo "✓ IAM Role ready."
echo "  Role ARN    : ${ROLE_ARN}"
echo "  External ID : ${EXTERNAL_ID}"
echo ""
echo "Enter these values in Salesforce Data Cloud:"
echo "  Setup → Data Cloud → Amazon S3 File Federation → New Connected Source"
