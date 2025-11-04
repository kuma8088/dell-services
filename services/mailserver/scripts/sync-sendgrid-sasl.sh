#!/bin/bash
set -euo pipefail

# Secrets Manager から SendGrid API Key を取得し、
# Postfix の SASL 認証ファイルに反映するヘルパースクリプト。
#
# 使い方:
#   ./sync-sendgrid-sasl.sh
#   ./sync-sendgrid-sasl.sh <secret-id-or-arn>
#
# 実行後に `docker compose restart postfix` で再読込してください。

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
SECRET_ID=${1:-mailserver/sendgrid/api-key}
SASL_FILE="/etc/postfix/custom/sasl_passwd"

echo "Fetching SendGrid API key from Secrets Manager (${SECRET_ID})..."
API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --query 'SecretString' \
  --output text)

if [[ -z "$API_KEY" ]]; then
  echo "ERROR: SecretString is empty. Aborting." >&2
  exit 1
fi

compose() {
  # prefer docker compose, fallback to docker-compose
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    docker compose "$@"
  fi
}

echo "Updating Postfix SASL credentials inside container..."
compose exec -T postfix sh -c "cat > ${SASL_FILE} <<'EOF'
[smtp.sendgrid.net]:587 apikey:${API_KEY}
EOF"
compose exec -T postfix chmod 600 ${SASL_FILE}
compose exec -T postfix postmap ${SASL_FILE}

echo "Updated $(compose exec -T postfix readlink -f ${SASL_FILE})"
echo
echo "Next steps:"
echo "  1. docker compose restart postfix"
echo "  2. docker compose logs postfix | grep -i sendgrid"
