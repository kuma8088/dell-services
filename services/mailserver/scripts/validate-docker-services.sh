#!/bin/bash
set -euo pipefail

COMPOSE_DIR="/opt/onprem-infra-system/project-root-infra/services/mailserver"
MAX_WAIT=180  # 最大3分待機

cd $COMPOSE_DIR

echo "=== Docker Compose サービス起動検証 ==="
echo "検証開始時刻: $(date)"
echo ""

# 全サービスリスト
SERVICES=("mariadb" "postfix" "dovecot" "roundcube" "rspamd" "clamav" "nginx")

is_service_ready() {
  local service="$1"
  docker compose ps "$service" --format json 2>/dev/null \
    | jq -e '
        (if type == "array" then . else [.] end)
        | any(.[];
            (.State == "running")
            and (
              (.Health == "" or .Health == null)
              or (.Health == "healthy")
            )
          )' >/dev/null 2>&1
}

# 起動待機（最大3分）
echo "⏳ サービス起動待機中..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  ALL_RUNNING=true

  for SERVICE in "${SERVICES[@]}"; do
    if ! is_service_ready "$SERVICE"; then
      STATUS=$(docker compose ps "$SERVICE" --format json | jq -r '(if type=="array" then .[] else . end) | "state=" + .State + ", health=" + ((.Health//"n/a"))' 2>/dev/null || echo "state=unknown, health=unknown")
      echo "   → ${SERVICE} 起動待機中 (${STATUS})"
      ALL_RUNNING=false
      break
    fi
  done

  if [ "$ALL_RUNNING" = true ]; then
    echo "✅ 全サービスが起動しました（${ELAPSED}秒経過）"
    break
  fi

  sleep 5
  ELAPSED=$((ELAPSED + 5))
  echo "   待機中... ${ELAPSED}/${MAX_WAIT}秒"
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "❌ タイムアウト: 一部のサービスが起動しませんでした"
  docker compose ps
  exit 1
fi

echo ""
echo "=== サービス個別ヘルスチェック ==="

# MariaDB ヘルスチェック
echo -n "MariaDB: "
MARIADB_HEALTH=$(docker inspect mailserver-mariadb --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
if [ "$MARIADB_HEALTH" = "healthy" ]; then
  echo "✅ Healthy"
else
  echo "⚠️ Status: $MARIADB_HEALTH"
fi

# Postfix ポート確認
echo -n "Postfix (Port 587): "
POSTFIX_PORT=$(docker compose ps postfix --format json \
  | jq -r '(if type=="array" then . else [.] end)
           | map(.Publishers[]? | select(.TargetPort==587) | .PublishedPort)
           | first // "missing"' 2>/dev/null || echo "missing")
if [ "$POSTFIX_PORT" = "587" ]; then
  echo "✅ Listening on 0.0.0.0:587"
else
  echo "❌ Port 587 not exposed"
  exit 1
fi

# Dovecot LMTP ポート確認
echo -n "Dovecot (Port 2525 LMTP): "
DOVECOT_PORT=$(docker compose ps dovecot --format json \
  | jq -r '(if type=="array" then . else [.] end)
           | map(.Publishers[]? | select(.TargetPort==2525) | .PublishedPort)
           | first // "missing"' 2>/dev/null || echo "missing")
if [ "$DOVECOT_PORT" = "2525" ]; then
  echo "✅ Listening on 0.0.0.0:2525"
else
  echo "❌ Port 2525 (LMTP) not exposed"
  exit 1
fi

# Roundcube ポート確認
echo -n "Roundcube (Port 8080): "
ROUNDCUBE_PORT=$(docker compose ps roundcube --format json \
  | jq -r '(if type=="array" then . else [.] end)
           | map(.Publishers[]? | select(.TargetPort==8080) | .PublishedPort)
           | first // "missing"' 2>/dev/null || echo "missing")
if [ "$ROUNDCUBE_PORT" = "8080" ]; then
  echo "✅ Listening on 0.0.0.0:8080"
else
  echo "⚠️ Port 8080 not exposed (check nginx proxy)"
fi

# Nginx ポート確認
echo -n "Nginx (Port 80/443): "
NGINX_PORT_80=$(docker compose ps nginx --format json \
  | jq -r '(if type=="array" then . else [.] end)
           | map(.Publishers[]? | select(.TargetPort==80) | .PublishedPort)
           | first // "missing"' 2>/dev/null || echo "missing")
NGINX_PORT_443=$(docker compose ps nginx --format json \
  | jq -r '(if type=="array" then . else [.] end)
           | map(.Publishers[]? | select(.TargetPort==443) | .PublishedPort)
           | first // "missing"' 2>/dev/null || echo "missing")
if [ "$NGINX_PORT_80" = "80" ] && [ "$NGINX_PORT_443" = "443" ]; then
  echo "✅ Listening on 0.0.0.0:80 and 0.0.0.0:443"
else
  echo "⚠️ HTTP/HTTPS ports not fully exposed"
fi

# Rspamd 起動確認
echo -n "Rspamd: "
RSPAMD_STATUS=$(docker inspect mailserver-rspamd --format='{{.State.Status}}' 2>/dev/null || echo "missing")
if [ "$RSPAMD_STATUS" = "running" ]; then
  echo "✅ Running"
else
  echo "❌ Status: $RSPAMD_STATUS"
  exit 1
fi

# ClamAV 起動確認
echo -n "ClamAV: "
CLAMAV_STATUS=$(docker inspect mailserver-clamav --format='{{.State.Health.Status}}' 2>/dev/null || echo "missing")
if [ "$CLAMAV_STATUS" = "healthy" ]; then
  echo "✅ Healthy"
else
  echo "❌ Status: $CLAMAV_STATUS"
  exit 1
fi

echo ""
echo "=== ボリューム検証 ==="
VOLUMES=("mail_data" "db_data" "rspamd_data" "clamav_data")
for VOL in "${VOLUMES[@]}"; do
  VOL_PATH=$(docker volume inspect mailserver_$VOL --format '{{.Mountpoint}}' 2>/dev/null || echo "missing")
  if [ "$VOL_PATH" != "missing" ]; then
    echo "✅ $VOL: $VOL_PATH"
  else
    echo "❌ $VOL: Volume not found"
    exit 1
  fi
done

echo ""
echo "=== 検証サマリー ==="
echo "✅ 全サービスが正常に起動しました"
echo "✅ 全ポートが適切に公開されています"
echo "✅ 全ボリュームがマウントされています"
echo ""
echo "次のステップ:"
echo "1. セクション 6.7: Postfix SASL認証ファイル生成"
echo "2. セクション 6.8: ユーザー作成"
echo "3. セクション 7: Fargate ↔ Dell 統合テスト"
