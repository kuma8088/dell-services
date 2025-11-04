#!/bin/bash
# EC2 MX Gateway User Data Script
# 参照: Docs/application/mailserver/04_EC2Server.md Section 4.1.2

set -e

# CloudWatch Logs エージェント設定用変数
AWS_REGION="ap-northeast-1"
LOG_GROUP="/ec2/mailserver-mx"

# ログ記録関数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/user-data.log
}

log "Starting EC2 MX Gateway setup"

# システムアップデートとパッケージインストール
log "Updating system packages"
dnf update -y

log "Installing required packages"
dnf install -y docker amazon-cloudwatch-agent

# Docker サービス開始
log "Starting Docker service"
systemctl enable docker
systemctl start docker

# Docker Compose インストール
log "Installing Docker Compose"
DOCKER_COMPOSE_VERSION="v2.24.0"
curl -SL "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-aarch64" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Tailscale インストール
log "Installing Tailscale"
dnf config-manager --add-repo https://pkgs.tailscale.com/stable/amazon-linux/2023/tailscale.repo
dnf install -y tailscale

# Tailscale サービス開始
log "Starting Tailscale service"
systemctl enable tailscaled
systemctl start tailscaled

# Tailscale Auth Key 取得と接続
log "Retrieving Tailscale auth key from Secrets Manager"
TAILSCALE_AUTH_KEY=$(aws secretsmanager get-secret-value \
    --secret-id mailserver/tailscale/ec2-auth-key \
    --query SecretString \
    --output text \
    --region ${AWS_REGION})

if [ -z "$TAILSCALE_AUTH_KEY" ]; then
    log "ERROR: Failed to retrieve Tailscale auth key"
    exit 1
fi

log "Connecting to Tailscale VPN"
tailscale up --authkey="${TAILSCALE_AUTH_KEY}" --hostname=mailserver-mx-ec2

# Tailscale 接続確認
log "Verifying Tailscale connection"
sleep 10
if tailscale status | grep -q "100."; then
    TAILSCALE_IP=$(tailscale ip -4)
    log "Tailscale connected successfully. IP: ${TAILSCALE_IP}"
else
    log "ERROR: Tailscale connection failed"
    exit 1
fi

# CloudWatch Logs エージェント設定
log "Configuring CloudWatch Logs agent"
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'EOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/ec2/mailserver-mx",
            "log_stream_name": "{instance_id}/user-data"
          },
          {
            "file_path": "/opt/mailserver/logs/postfix.log",
            "log_group_name": "/ec2/mailserver-mx",
            "log_stream_name": "{instance_id}/postfix"
          }
        ]
      }
    }
  }
}
EOF

log "Starting CloudWatch Logs agent"
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# mailserver ディレクトリ作成
log "Creating mailserver directory"
mkdir -p /opt/mailserver/logs

# Docker Compose 設定作成
log "Creating Docker Compose configuration"
cat > /opt/mailserver/docker-compose.yml <<'EOF'
services:
  postfix:
    image: boky/postfix:latest
    container_name: mailserver-postfix
    restart: always
    network_mode: host
    environment:
      # Fargateトラブルシューティング教訓 #2: 送信者ドメイン制限なし
      - ALLOW_EMPTY_SENDER_DOMAINS=true
      - ALLOWED_SENDER_DOMAINS=

      # EC2トラブルシューティング教訓: LMTP配信設定（SMTP→LMTPプロトコル変換）
      - POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525

      # Fargateトラブルシューティング教訓 #3: IPv4のみ
      - POSTFIX_inet_protocols=ipv4

      # Fargateトラブルシューティング教訓 #2: アクセス制御
      - POSTFIX_smtpd_recipient_restrictions=permit_mynetworks, permit_sasl_authenticated, check_relay_domains, permit

      # EC2トラブルシューティング教訓: 有効なドメインのみ設定（m8088.com削除）
      - POSTFIX_relay_domains=kuma8088.com

      # Fargateトラブルシューティング教訓 #2: 送信者制限なし
      - POSTFIX_smtpd_client_restrictions=permit_mynetworks, permit_sasl_authenticated, permit
      - POSTFIX_smtpd_sender_restrictions=permit_mynetworks, permit_sasl_authenticated, permit

    volumes:
      - /opt/mailserver/logs:/var/log

    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 25 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
EOF

# Postfix コンテナ起動
log "Starting Postfix container"
cd /opt/mailserver
docker-compose up -d

# コンテナ起動確認
log "Verifying Postfix container startup"
sleep 15
if docker ps | grep -q mailserver-postfix; then
    log "Postfix container started successfully"
else
    log "ERROR: Postfix container failed to start"
    docker-compose logs
    exit 1
fi

# Dell への接続テスト
log "Testing connectivity to Dell Dovecot"
if docker exec mailserver-postfix nc -zv 100.110.222.53 2525 2>&1 | grep -q succeeded; then
    log "Dell Dovecot connectivity test: SUCCESS"
else
    log "WARNING: Dell Dovecot connectivity test failed"
fi

# SMTP ポート確認
log "Verifying SMTP port 25 is listening"
if ss -tuln | grep -q ":25 "; then
    log "SMTP port 25 is listening"
else
    log "ERROR: SMTP port 25 is not listening"
    exit 1
fi

log "EC2 MX Gateway setup completed successfully"
log "Tailscale IP: ${TAILSCALE_IP}"
log "Postfix container: $(docker ps --filter name=mailserver-postfix --format '{{.Status}}')"
