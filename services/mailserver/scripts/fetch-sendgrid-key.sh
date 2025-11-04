#!/bin/bash
set -euo pipefail

# Secrets Manager から SendGrid API Key を取得するユーティリティ
# 使い方:
#   ./fetch-sendgrid-key.sh                              # 既定 ID: mailserver/sendgrid/api-key
#   ./fetch-sendgrid-key.sh arn:aws:secretsmanager:...   # 任意の Secret ID / ARN

SECRET_ID=${1:-mailserver/sendgrid/api-key}

aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --query 'SecretString' \
  --output text
