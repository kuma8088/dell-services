# Mailserver 構築・運用ガイド (EC2版)

**バージョン**: v6.0 (EC2 + Tailscale)
**作成日**: 2025-11-04
**更新日**: 2025-11-04
**ステータス**: 運用中 (Production)

## 目的

本ガイドは、Hybrid Cloud Mail Server (AWS EC2 + Dell On-Premises + SendGrid) の構築・運用手順を提供します。

**アーキテクチャ背景**: Fargate版 (v5.1) はTailscale VPNネットワーク分離問題により廃止し、EC2版 (v6.0) に移行しました。

**参照**:
- Fargate環境のトラブルシューティング履歴: `services/mailserver/troubleshoot/INBOUND_MAIL_FAILURE_2025-11-03.md`
- EC2プロトコル設定問題の解決記録: `services/mailserver/troubleshoot/EC2_MAIL_PROTOCOL_ISSUE_2025-11-04.md`
- **メールクライアントログイン失敗 (TLS Cipher互換性)**: `services/mailserver/troubleshoot/MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md`
- **クライアント側設定ガイド (ユーザーガイド)**: `Docs/application/mailserver/device/01_device_access_design.md`

---

## 1. アーキテクチャ概要

### 1.1 システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│ Internet                                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ Port 25 (SMTP)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ AWS EC2 Instance (MX Gateway)                                │
│ - Instance Type: t4g.nano (ARM64, 2 vCPU, 0.5 GiB)          │
│ - OS: Amazon Linux 2023                                      │
│ - Public IP: 43.207.242.167 (Elastic IP)                    │
│ - Security Group: Port 25 (SMTP)                            │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Tailscale Daemon (Host Level)                        │   │
│ │ - VPN IP: 100.xxx.xxx.xxx                            │   │
│ │ - Interface: tailscale0                              │   │
│ │ - Accept Routes: enabled                             │   │
│ └──────────────────────────────────────────────────────┘   │
│                      ↓                                       │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Docker Container: Postfix (boky/postfix)             │   │
│ │ - Port: 25 (SMTP inbound)                            │   │
│ │ - Network: host mode                                 │   │
│ │ - RELAYHOST: [100.110.222.53]:2525                   │   │
│ │ - relay_domains: kuma8088.com                        │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ Tailscale VPN
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Dell WorkStation (On-Premises)                               │
│ - Tailscale IP: 100.110.222.53                              │
│ - Private Network: 10.0.x.0/24                              │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Docker Compose Stack                                 │   │
│ │ - Dovecot LMTP: 2525 (inbound from Fargate/EC2)     │   │
│ │ - Postfix Submission: 587 (outbound via SendGrid)   │   │
│ │ - Roundcube Webmail: 80/443                          │   │
│ │ - Rspamd, ClamAV, MariaDB, Nginx                     │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Fargate vs EC2 比較

| 項目 | Fargate (v5.1) | EC2 (v6.0) |
|------|----------------|------------|
| **Tailscale動作** | コンテナ内のみ (分離) | ホストOS全体 |
| **VPNアクセス** | ❌ Postfixから不可 | ✅ 全プロセスから可能 |
| **ネットワーク複雑度** | 高 (workaround必要) | 低 (標準構成) |
| **コスト (月額)** | ~$13-16 | ~$3 |
| **保守性** | 低 (制約多数) | 高 (標準Linux) |
| **Subnet Router** | ❌ 利用不可 | ✅ 完全サポート |

---

## 2. Fargateでの問題点と教訓

### 2.1 発生した問題 (Revision 1-11)

#### 問題 #1: Elastic IP / DNS ミスマッチ
- **事象**: MXレコード `43.207.242.167` に届かない
- **原因**: Fargate ENIは動的IP割り当て、Elastic IP直接関連付け不可
- **影響**: メール受信失敗

#### 問題 #2: Postfix アクセス制御設定ミス
- **事象**: `Client host rejected: Access denied`
- **原因**: `ALLOWED_SENDER_DOMAINS` で送信者ドメイン制限
- **修正**: `ALLOW_EMPTY_SENDER_DOMAINS=true` で任意の送信者を許可

#### 問題 #3: boky/postfix 環境変数名エラー
- **事象**: リレー設定が認識されない
- **原因**: `RELAY_HOST` (誤) → `RELAYHOST` (正)
- **修正**: 正しい環境変数名を使用

#### 問題 #4: Tailscale ネットワーク分離 (根本問題)
- **事象**: `Connection timed out` to Dell LMTP
- **原因**: Fargate awsvpc モードでコンテナ間のネットワーク名前空間が分離
- **影響**: Postfix → Tailscale VPN → Dell への通信不可能
- **結論**: アーキテクチャ上の根本的制約、回避不可能

### 2.2 学んだ教訓

#### 教訓 #1: インフラ設計時の技術的制約調査の重要性
- コンテナプラットフォームの制約を事前に理解すべき
- 概念実証 (PoC) でアーキテクチャを検証すべきだった

#### 教訓 #2: Docker イメージの仕様確認
- 環境変数名は Docker イメージ固有
- 公式ドキュメントを必ず参照
- boky/postfix は「送信専用リレー」として設計

#### 教訓 #3: 段階的エラー解決の落とし穴
- 各修正で一つの問題を解決しても、次の問題が表面化
- Revision 6-11 で合計 6 回の試行錯誤
- 最終的にアーキテクチャ上の根本的な問題に到達

#### 教訓 #4: Elastic IP の制約理解
- Fargate ENI は AWS マネージド、Elastic IP 直接関連付け不可
- NLB / EC2 Proxy / Dynamic DNS などの代替策が必要

---

## 3. EC2での解決策と要件

### 3.1 EC2アーキテクチャの利点

#### 利点 #1: Tailscale完全サポート
- **ホストレベルで動作**: カーネルネットワークスタックに統合
- **全プロセスからアクセス**: Dockerコンテナもネイティブプロセスも同じVPNインターフェース共有
- **標準機能フル活用**: Subnet Router、MagicDNS、Exit Nodeなど全機能利用可能

#### 利点 #2: Elastic IP 直接割り当て
- **固定IP**: タスク再起動時も変更なし
- **DNS安定性**: MXレコードとIPの整合性常に維持
- **シンプルな設定**: API操作不要

#### 利点 #3: コスト削減
- **t4g.nano**: ~$3.07/月 (Fargate: ~$13-16/月)
- **コスト削減率**: 76-81%

#### 利点 #4: 設計のシンプル化
- **標準Linux構成**: Amazon Linux 2023 + Docker + Tailscale
- **保守性向上**: 複雑なworkaround不要
- **柔軟性**: 必要に応じて機能追加可能

### 3.2 機能要件

#### FR-1: SMTP受信機能
- **受信ポート**: TCP/25 (SMTP)
- **対象ドメイン**: `kuma8088.com`, `m8088.com`
- **送信者制限**: なし (任意の送信者から受信可能)
- **受信者制限**: あり (対象ドメイン宛のみ)

#### FR-2: メールリレー機能
- **リレー先**: Dell WorkStation Dovecot LMTP (Tailscale経由)
- **リレーアドレス**: `100.110.222.53:2525`
- **プロトコル**: LMTP over Tailscale VPN
- **タイムアウト**: 30秒以内

#### FR-3: Tailscale VPN接続
- **動作モード**: ホストレベル (全プロセスから利用可能)
- **VPNインターフェース**: `tailscale0`
- **ルート受信**: 有効 (`--accept-routes`)
- **自動再接続**: 有効

#### FR-4: DNS解決
- **対象**: Tailscale hostname (`dell-workstation.tail67811d.ts.net`)
- **MagicDNS**: 有効 (Tailscale内部DNS)
- **IPv4/IPv6**: IPv4のみ (`inet_protocols=ipv4`)

### 3.3 非機能要件

#### NFR-1: 可用性
- **稼働率**: 99.5% (月間ダウンタイム <3.6時間)
- **自動起動**: システム起動時に自動起動 (systemd)
- **ヘルスチェック**: Docker healthcheck + 外部監視

#### NFR-2: セキュリティ
- **SSH**: ポート22無効化、鍵認証のみ
- **Firewall**: Security Group (Port 25のみ許可)
- **SELinux**: 有効 (Amazon Linux 2023デフォルト)
- **自動更新**: セキュリティパッチ自動適用

#### NFR-3: パフォーマンス
- **SMTP応答時間**: <1秒
- **メールリレー時間**: <5秒
- **CPU使用率**: <50% (平常時)
- **メモリ使用率**: <70% (平常時)

#### NFR-4: 監視・ログ
- **ログ収集**: CloudWatch Logs
- **メトリクス**: CloudWatch Metrics (CPU, Memory, Network)
- **アラート**: CloudWatch Alarm (CPU >80%, Memory >80%)
- **ログ保持期間**: 30日間

### 3.4 制約事項

#### 制約 #1: Fargateトラブルシューティングの教訓適用
- ✅ **Elastic IP 固定割り当て**: EC2インスタンス起動時に自動関連付け
- ✅ **boky/postfix環境変数**: `RELAYHOST` (正) を使用、`RELAY_HOST` (誤) は使用しない
- ✅ **アクセス制御**: `ALLOW_EMPTY_SENDER_DOMAINS=true` で任意の送信者許可
- ✅ **Tailscaleホストレベル**: コンテナ内ではなくホストOSで実行
- ✅ **IPv4専用**: `inet_protocols=ipv4` で IPv6 無効化
- ✅ **relay_domains設定**: 受信対象ドメインを明示的に設定

#### 制約 #2: Dell環境との互換性
- Dell Docker Compose環境は現状維持
- LMTP受信ポート: `2525` (変更なし)
- Tailscale IP: `100.110.222.53` (変更なし)

#### 制約 #3: DNSレコード
- MXレコード: `mx.kuma8088.com` → `43.207.242.167` (既存Elastic IP)
- 変更不要 (EC2にElastic IP関連付けのみ)

---

## 4. インフラ構築手順

### 4.1 Terraform構成

#### 4.1.1 EC2インスタンス定義

**ファイル**: `services/mailserver/terraform/ec2.tf`

```hcl
# ============================================================================
# EC2 MX Gateway Instance (v6.0)
# ============================================================================

resource "aws_instance" "mailserver_mx" {
  ami                         = "ami-0ad4e047a362f26b8"  # Amazon Linux 2023 (ARM64)
  instance_type               = "t4g.nano"
  subnet_id                   = aws_subnet.public_subnet_1a.id
  vpc_security_group_ids      = [aws_security_group.fargate_sg.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2_mx_profile.name

  user_data = file("${path.module}/user_data.sh")

  root_block_device {
    volume_type = "gp3"
    volume_size = 8  # 8 GiB (最小推奨)
    encrypted   = true
  }

  tags = {
    Name        = "mailserver-mx-gateway"
    Version     = "v6.0"
    Environment = var.environment
  }
}

# Elastic IP 関連付け
resource "aws_eip_association" "mailserver_eip" {
  instance_id   = aws_instance.mailserver_mx.id
  allocation_id = "eipalloc-04e838a5b1c9c7dde"  # 既存Elastic IP
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_mx_profile" {
  name = "mailserver-ec2-mx-profile"
  role = aws_iam_role.ec2_mx_role.name
}

# IAM Role for EC2
resource "aws_iam_role" "ec2_mx_role" {
  name = "mailserver-ec2-mx-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "mailserver-ec2-mx-role"
  }
}

# IAM Policy: Secrets Manager Access
resource "aws_iam_role_policy" "ec2_mx_secrets_access" {
  name = "mailserver-ec2-secrets-access"
  role = aws_iam_role.ec2_mx_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/tailscale/ec2-auth-key-*"
        ]
      }
    ]
  })
}

# IAM Policy: CloudWatch Logs
resource "aws_iam_role_policy_attachment" "ec2_mx_cloudwatch_logs" {
  role       = aws_iam_role.ec2_mx_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ec2_mx_logs" {
  name              = "/ec2/mailserver-mx"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "mailserver-ec2-mx-logs"
  }
}

# Outputs
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.mailserver_mx.id
}

output "ec2_public_ip" {
  description = "EC2 public IP (Elastic IP)"
  value       = aws_eip_association.mailserver_eip.public_ip
}

output "ec2_private_ip" {
  description = "EC2 private IP"
  value       = aws_instance.mailserver_mx.private_ip
}
```

#### 4.1.2 User Data Script

**ファイル**: `services/mailserver/terraform/user_data.sh`

```bash
#!/bin/bash
set -e

# ============================================================================
# EC2 MX Gateway User Data Script (v6.0)
# ============================================================================

# ログ設定
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== Starting EC2 MX Gateway Setup ==="
echo "Timestamp: $(date)"

# 1. システムアップデート
echo "=== Step 1: System Update ==="
dnf update -y

# 2. 必要なパッケージインストール
echo "=== Step 2: Install Required Packages ==="
dnf install -y \
  docker \
  amazon-cloudwatch-agent \
  awscli \
  nc \
  telnet

# 3. Docker起動と自動起動設定
echo "=== Step 3: Docker Setup ==="
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# 4. Docker Composeインストール
echo "=== Step 4: Install Docker Compose ==="
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 5. Tailscaleインストール
echo "=== Step 5: Install Tailscale ==="
curl -fsSL https://tailscale.com/install.sh | sh

# 6. Tailscale Auth Key取得とVPN接続
echo "=== Step 6: Connect to Tailscale VPN ==="
AUTHKEY=$(aws secretsmanager get-secret-value \
  --secret-id mailserver/tailscale/ec2-auth-key \
  --query SecretString \
  --output text \
  --region ap-northeast-1)

if [ -z "$AUTHKEY" ]; then
  echo "ERROR: Failed to retrieve Tailscale auth key from Secrets Manager"
  exit 1
fi

tailscale up --authkey="$AUTHKEY" --accept-routes --hostname="mailserver-mx-ec2"

# Tailscale接続確認
sleep 5
tailscale status

# 7. Docker Compose設定配置
echo "=== Step 7: Deploy Docker Compose Configuration ==="
mkdir -p /opt/mailserver
cat > /opt/mailserver/docker-compose.yml <<'EOF'
version: '3.8'

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
      - POSTFIX_smtpd_client_restrictions=permit_mynetworks, permit_sasl_authenticated, permit
      - POSTFIX_smtpd_sender_restrictions=permit_mynetworks, permit_sasl_authenticated, permit

      # EC2トラブルシューティング教訓: 有効なドメインのみ設定（m8088.com削除）
      - POSTFIX_relay_domains=kuma8088.com

      # その他の設定
      - POSTFIX_message_size_limit=26214400
      - HOSTNAME=mx.kuma8088.com
      - DOMAIN=kuma8088.com
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "25"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: awslogs
      options:
        awslogs-region: ap-northeast-1
        awslogs-group: /ec2/mailserver-mx
        awslogs-stream: postfix
EOF

# 8. Postfix起動
echo "=== Step 8: Start Postfix Container ==="
cd /opt/mailserver
docker-compose up -d

# 起動確認
sleep 10
docker ps
docker logs mailserver-postfix

# 9. CloudWatch Agent設定
echo "=== Step 9: Configure CloudWatch Agent ==="
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'EOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/ec2/mailserver-mx",
            "log_stream_name": "user-data"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "Mailserver/EC2",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {
            "name": "cpu_usage_idle",
            "rename": "CPU_IDLE",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "MEM_USED",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

systemctl start amazon-cloudwatch-agent
systemctl enable amazon-cloudwatch-agent

# 10. 動作確認
echo "=== Step 10: Health Check ==="

# Tailscale VPN確認
echo "Tailscale Status:"
tailscale status

# Dellへの接続確認
echo "Dell LMTP Connectivity:"
nc -zv 100.110.222.53 2525 || echo "WARNING: Dell LMTP not reachable"

# SMTP Port確認
echo "SMTP Port Check:"
nc -zv localhost 25 || echo "WARNING: SMTP port not open"

# Docker Container確認
echo "Docker Container Status:"
docker ps -a

echo "=== EC2 MX Gateway Setup Complete ==="
echo "Timestamp: $(date)"
```

### 4.2 Terraform適用手順

```bash
# 1. Terraform初期化
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform
terraform init

# 2. 変更プレビュー
terraform plan

# 期待される出力:
# + aws_instance.mailserver_mx
# + aws_eip_association.mailserver_eip
# + aws_iam_instance_profile.ec2_mx_profile
# + aws_iam_role.ec2_mx_role
# + aws_iam_role_policy.ec2_mx_secrets_access
# + aws_cloudwatch_log_group.ec2_mx_logs

# 3. インフラ適用
terraform apply

# 確認プロンプトで "yes" を入力

# 4. 出力確認
terraform output

# 期待される出力:
# ec2_instance_id = "i-xxxxxxxxxxxxx"
# ec2_public_ip = "43.207.242.167"
# ec2_private_ip = "10.0.1.xxx"
```

### 4.3 デプロイ確認

```bash
# 1. EC2インスタンス状態確認
aws ec2 describe-instances \
  --instance-ids $(terraform output -raw ec2_instance_id) \
  --query 'Reservations[0].Instances[0].{State:State.Name,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress}' \
  --output table

# 期待される出力:
# --------------------------------
# | DescribeInstances            |
# +------------+------------------+
# | PrivateIP  | 10.0.1.xxx       |
# | PublicIP   | 43.207.242.167   |
# | State      | running          |
# +------------+------------------+

# 2. User Data実行確認
aws ec2 get-console-output \
  --instance-id $(terraform output -raw ec2_instance_id) \
  --latest

# "EC2 MX Gateway Setup Complete" が表示されることを確認

# 3. SSH接続確認 (ec2-user)
ssh ec2-user@43.207.242.167

# EC2内で確認:
sudo su -

# Tailscale状態確認
tailscale status
# 出力例:
# 100.xxx.xxx.xxx mailserver-mx-ec2    tagged-devices linux   -

# Docker Container確認
docker ps
# 出力例:
# CONTAINER ID   IMAGE                 STATUS    PORTS
# xxxxx          boky/postfix:latest   Up

# Postfixログ確認
docker logs mailserver-postfix
# 出力例:
# ‣ NOTE  Forwarding all emails to [100.110.222.53]:2525 without any authentication.

# Dellへの接続確認
nc -zv 100.110.222.53 2525
# 出力例: Ncat: Connected to 100.110.222.53:2525
```

---

## 5. 動作テスト・検証

### 5.1 Tailscale接続テスト

```bash
# EC2からDellへのping
tailscale ping 100.110.222.53
# 期待される出力: pong from dell-workstation (100.110.222.53) via DERP in Xms

# EC2からDell LMTPへの接続
nc -zv 100.110.222.53 2525
# 期待される出力: Ncat: Connected to 100.110.222.53:2525

# Dell側からEC2への接続確認 (Dell WorkStationで実行)
tailscale ping <EC2 Tailscale IP>
# 期待される出力: pong from mailserver-mx-ec2 via DERP in Xms
```

### 5.2 SMTP受信テスト

```bash
# 外部からのSMTP接続テスト
telnet 43.207.242.167 25
# 期待される応答:
# 220 mx.kuma8088.com ESMTP Postfix

# EHLO送信
EHLO test.example.com
# 期待される応答:
# 250-mx.kuma8088.com
# 250-PIPELINING
# 250-SIZE 26214400
# 250-VRFY
# 250-ETRN
# 250-STARTTLS
# 250-ENHANCEDSTATUSCODES
# 250-8BITMIME
# 250 DSN

# テストメール送信
MAIL FROM:<test@example.com>
RCPT TO:<test@kuma8088.com>
DATA
Subject: Test Mail from EC2 MX Gateway

This is a test mail.
.
QUIT

# 期待される応答:
# 250 2.0.0 Ok: queued as XXXXX
```

### 5.3 メールリレー確認

```bash
# EC2でPostfixログ確認
docker logs mailserver-postfix --tail 20 | grep "relay="
# 期待される出力:
# postfix/smtp[xxx]: XXXXXX: to=<test@kuma8088.com>, relay=[100.110.222.53]:2525, ...status=sent

# Dell WorkStationでDovecotログ確認
docker logs mailserver-dovecot --tail 20 | grep "saved mail"
# 期待される出力:
# lmtp(xxx): xxxxx: msgid=<xxx>: saved mail to INBOX

# Roundcubeでメール受信確認
# https://dell-workstation.tail67811d.ts.net/
# test@kuma8088.com でログイン → 受信トレイにテストメールが表示されること
```

### 5.4 エラーパターンテスト

#### テスト #1: 無効なドメイン宛メール (拒否されるべき)

```bash
telnet 43.207.242.167 25
EHLO test.example.com
MAIL FROM:<test@example.com>
RCPT TO:<test@invalid-domain.com>
# 期待されるエラー:
# 554 5.7.1 <test@invalid-domain.com>: Relay access denied
QUIT
```

#### テスト #2: Tailscale VPN切断時の動作

```bash
# EC2でTailscale停止
sudo tailscale down

# メール送信テスト
telnet 43.207.242.167 25
MAIL FROM:<test@example.com>
RCPT TO:<test@kuma8088.com>
DATA
Test mail during Tailscale down
.
QUIT

# Postfixログ確認
docker logs mailserver-postfix --tail 20
# 期待される出力:
# status=deferred (connect to [100.110.222.53]:2525: No route to host)

# Tailscale再接続
sudo tailscale up --accept-routes

# キューフラッシュ (再送)
docker exec mailserver-postfix postqueue -f

# ログ確認 (再送成功)
docker logs mailserver-postfix --tail 20
# 期待される出力:
# status=sent (250 2.0.0 Ok: queued as XXXXX)
```

### 5.5 パフォーマンステスト

```bash
# 同時接続テスト (10並列)
for i in {1..10}; do
  (
    echo "EHLO test.example.com"
    sleep 1
    echo "QUIT"
  ) | nc 43.207.242.167 25 &
done
wait

# CPU/メモリ使用率確認
aws cloudwatch get-metric-statistics \
  --namespace Mailserver/EC2 \
  --metric-name CPU_IDLE \
  --dimensions Name=InstanceId,Value=$(terraform output -raw ec2_instance_id) \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average

# 期待される出力: CPU使用率 <50%
```

---

## 6. 監視・運用

### 6.1 CloudWatch監視設定

#### 6.1.1 CloudWatch Alarm作成

```bash
# CPU使用率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name mailserver-ec2-high-cpu \
  --alarm-description "EC2 MX Gateway CPU usage > 80%" \
  --metric-name CPU_IDLE \
  --namespace Mailserver/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 20 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=InstanceId,Value=$(terraform output -raw ec2_instance_id)

# メモリ使用率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name mailserver-ec2-high-memory \
  --alarm-description "EC2 MX Gateway Memory usage > 80%" \
  --metric-name MEM_USED \
  --namespace Mailserver/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=$(terraform output -raw ec2_instance_id)
```

#### 6.1.2 ログストリーム確認

```bash
# Postfixログ確認
aws logs tail /ec2/mailserver-mx --follow --filter-pattern "postfix"

# User Dataログ確認
aws logs tail /ec2/mailserver-mx --log-stream-name user-data
```

### 6.2 定期メンテナンス

#### 毎日のタスク

```bash
# ログ確認スクリプト (/opt/mailserver/daily-check.sh)
#!/bin/bash

echo "=== Daily Health Check: $(date) ==="

# Tailscale接続確認
tailscale status | grep -q "100.110.222.53" && echo "✅ Tailscale OK" || echo "❌ Tailscale DOWN"

# Docker Container確認
docker ps | grep -q "mailserver-postfix" && echo "✅ Postfix OK" || echo "❌ Postfix DOWN"

# SMTP Port確認
nc -zv localhost 25 && echo "✅ SMTP Port OK" || echo "❌ SMTP Port CLOSED"

# Dell LMTP確認
nc -zv 100.110.222.53 2525 && echo "✅ Dell LMTP OK" || echo "❌ Dell LMTP DOWN"

# Postfixキュー確認
QUEUE_COUNT=$(docker exec mailserver-postfix postqueue -p | tail -1 | awk '{print $5}')
echo "Mail Queue: $QUEUE_COUNT"

# ログローテーション
docker logs mailserver-postfix --tail 100 > /var/log/postfix-daily-$(date +%Y%m%d).log
```

#### 毎週のタスク

```bash
# セキュリティアップデート
sudo dnf update -y --security

# Dockerイメージ更新
cd /opt/mailserver
docker-compose pull
docker-compose up -d

# システム再起動 (必要に応じて)
sudo reboot
```

### 6.3 トラブルシューティング

#### 問題 #1: メール受信失敗

**症状**: 外部からメールが届かない

**確認手順**:
```bash
# 1. SMTP Port開放確認
nc -zv 43.207.242.167 25

# 2. Security Group確認
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw security_group_id) \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`25`]'

# 3. Postfixログ確認
docker logs mailserver-postfix --tail 50

# 4. DNS MXレコード確認
dig +short kuma8088.com MX
dig +short mx.kuma8088.com A
```

#### 問題 #2: Tailscale接続失敗

**症状**: Dell WorkStationへの接続不可

**確認手順**:
```bash
# 1. Tailscale状態確認
tailscale status

# 2. Tailscale再接続
sudo tailscale down
sudo tailscale up --accept-routes

# 3. Dell側確認 (Dell WorkStationで実行)
tailscale status
tailscale ping <EC2 Tailscale IP>

# 4. ルーティング確認
ip route | grep tailscale
```

#### 問題 #3: メールリレー失敗

**症状**: EC2でメール受信するが、Dellへリレーされない

**確認手順**:
```bash
# 1. Dell LMTP接続確認
nc -zv 100.110.222.53 2525

# 2. Postfixログ確認
docker logs mailserver-postfix --tail 50 | grep "relay="

# 3. Postfixキュー確認
docker exec mailserver-postfix postqueue -p

# 4. RELAYHOST設定確認
docker exec mailserver-postfix postconf relayhost
# 期待される出力: relayhost = [100.110.222.53]:2525
```

---

## 7. 移行計画

### 7.1 移行ステップ

#### Phase 1: EC2環境構築 (本ドキュメント)
- ✅ Terraform設定作成
- ✅ User Data Script作成
- ⏳ Terraformデプロイ
- ⏳ 動作確認・テスト

#### Phase 2: 並行運用 (1週間)
- EC2環境: テストメール受信
- Fargate環境: 本番メール受信
- 問題がないことを確認

#### Phase 3: 段階的移行
- MXレコード TTL短縮 (60秒)
- テストドメインをEC2に向ける
- 本番ドメインをEC2に向ける

#### Phase 4: Fargate停止
- EC2環境で安定稼働確認
- Fargateサービス停止
- Fargateリソース削除

### 7.2 ロールバック計画

**条件**: EC2環境で致命的な問題が発生した場合

**手順**:
```bash
# 1. MXレコードをFargateに戻す (DNS更新)
# 2. EC2インスタンス停止
terraform destroy -target=aws_instance.mailserver_mx
# 3. Fargateサービス再開 (既に稼働中の場合は不要)
```

---

## 8. コスト試算

### 8.1 月額コスト

| 項目 | 詳細 | 月額 (USD) |
|------|------|------------|
| **EC2 Instance** | t4g.nano (ARM64, 0.5 GiB) | $3.07 |
| **EBS Volume** | 8 GiB gp3 | $0.80 |
| **Elastic IP** | 割り当て済み (課金なし) | $0.00 |
| **Data Transfer** | ~1 GB/月 (メール送受信) | $0.09 |
| **CloudWatch Logs** | ~500 MB/月 | $0.25 |
| **CloudWatch Metrics** | カスタムメトリクス 2個 | $0.60 |
| **合計** | | **$4.81** |

### 8.2 コスト比較

| 項目 | Fargate (v5.1) | EC2 (v6.0) | 削減額 |
|------|----------------|------------|--------|
| **月額コスト** | $13-16 | $4.81 | $8-11 |
| **年間コスト** | $156-192 | $57.72 | $98-134 |
| **削減率** | - | - | **63-73%** |

---

## 9. 付録

### 9.1 関連ドキュメント

- **Fargate構成**: `Docs/application/mailserver/04_installation.md`
- **トラブルシューティング**: `services/mailserver/troubleshoot/INBOUND_MAIL_FAILURE_2025-11-03.md`
- **Terraform main**: `services/mailserver/terraform/main.tf`
- **Docker Compose (Dell)**: `services/mailserver/docker-compose.yml`

### 9.2 参考リソース

- **Tailscale Documentation**: https://tailscale.com/kb/
- **Amazon Linux 2023 User Guide**: https://docs.aws.amazon.com/linux/al2023/
- **boky/postfix Docker Hub**: https://hub.docker.com/r/boky/postfix
- **Docker Compose Documentation**: https://docs.docker.com/compose/

### 9.3 変更履歴

| 日付 | バージョン | 変更内容 |
|------|------------|----------|
| 2025-11-04 | v6.0 Draft | 初版作成 (EC2構成設計) |

---

## 10. 実装トラブルシューティング履歴

### 10.1 初回デプロイ問題 (2025-11-04)

#### 問題 #1: AMIアーキテクチャミスマッチ

**症状**:
```
Error: creating EC2 Instance: operation error EC2: RunInstances
api error InvalidParameterValue: The architecture 'arm64' of the specified
instance type does not match the architecture 'x86_64' of the specified AMI.
```

**原因**:
- 使用したAMI `ami-0d52744d6551d851e` がx86_64アーキテクチャ
- インスタンスタイプ `t4g.nano` はARM64 (Graviton)

**解決**:
```hcl
# main.tf line 434
resource "aws_instance" "mailserver_mx" {
  ami           = "ami-0ad4e047a362f26b8"  # Amazon Linux 2023 ARM64に変更
  instance_type = "t4g.nano"
  # ...
}
```

**教訓**: Gravitonインスタンス (t4g系) は必ずARM64 AMIを使用すること

---

#### 問題 #2: Docker Compose未インストール

**症状**:
```
[user_data.sh]: unknown shorthand flag: 'd' in -d
[user_data.sh]: See 'docker --help'.
```

**原因**:
- Amazon Linux 2023のDockerパッケージにはdocker-composeが含まれていない
- `docker compose up -d` コマンドが実行できない

**解決**:

user_data.sh にDocker Compose v2インストールを追加:

```bash
# Docker Compose インストール (user_data.sh lines 30-35)
log "Installing Docker Compose"
DOCKER_COMPOSE_VERSION="v2.24.0"
curl -SL "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-aarch64" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
```

コマンド構文も修正:
```bash
# 修正前
docker compose up -d

# 修正後
docker-compose up -d
```

**教訓**: Amazon Linux 2023ではDocker Composeを手動インストールする必要がある

---

#### 問題 #3: Tailscale Auth Key 無効化

**症状**:
```
backend error: invalid key: API key kd1VosWS4g11CNTRL not valid
```

**原因**:
- 前回のEC2インスタンス (i-018511fba55b0881e) で既に使用済み
- Tailscale auth keyは一度しか使用できない（**reusable設定がfalse**の場合）

**誤診断の経緯**:
1. 初回インスタンスでDocker Compose問題により、user_data.shがTailscale接続まで到達せず
2. Auth keyが**使われていない**と誤認
3. 実際には、`tailscale up --authkey` コマンドは実行されており、keyは消費済みだった

**解決**:

新しいreusable auth keyを生成してSecrets Managerに登録:

```bash
# Tailscale管理画面で新しいauth keyを生成
# 設定:
# - Reusable: ☑️ チェック (再利用可能)
# - Tags: tag:fargate-mx
# - Pre-approved: ☑️ チェック

# Secrets Manager更新
aws secretsmanager put-secret-value \
  --secret-id mailserver/tailscale/ec2-auth-key \
  --secret-string "tskey-auth-kJSTzBehBa11CNTRL-3AkWfjiji14F8hi1brck24BRh8iuXEyT"
```

EC2インスタンス再作成:
```bash
terraform taint aws_instance.mailserver_mx
terraform apply -auto-approve
```

**教訓**:
- Tailscale auth keyは**reusable設定**を必ず有効化すること
- EC2再作成が必要な環境では、one-time keyは使用不可
- `tailscale up` コマンドが実行された時点でkeyは消費される（成功/失敗に関わらず）

---

#### 問題 #4: Tailscale ACL タグ大文字小文字不一致

**症状**:
```bash
# EC2インスタンスは起動しているが、外部からSMTP接続できない
nc -zv 43.207.242.167 25
# Connection timed out

# Tailscale経由のSSHも接続できない
ssh ec2-user@100.70.131.116
# Connection timed out

# EC2ログにはSMTPトラフィックが一切記録されない
aws logs tail /ec2/mailserver-mx --since 30m
# MARK メッセージのみ、接続ログなし
```

**原因**:
- EC2インスタンスのTailscaleタグ: **`tag:frontec2`** (小文字)
- Tailscale ACLのgrantsルール: **`tag:FrontEC2`** (大文字混じり)
- **Tailscaleのタグは大文字小文字を区別する**ため、ACLルールがマッチせず全トラフィックがブロックされる

**詳細調査**:

1. **EC2インスタンスタグ確認**:
```bash
# Dell WorkStationから確認
tailscale status | grep mailserver-mx-ec2

# 出力:
# 100.70.131.116  mailserver-mx-ec2  tagged-devices  linux  idle
#   Tags: ["tag:frontec2"]  ← 小文字
```

2. **Tailscale ACL設定** (抜粋):
```json
{
    "grants": [
        {
            "src": ["tag:fargate-mx", "naoya.iimura@gmail.com", "tag:FrontEC2"],
            "dst": ["tag:mailserver"],
            "ip":  ["tcp:25", "tcp:2525", "udp:41641"],
        }
    ],
    "tagOwners": {
        "tag:FrontEC2": ["autogroup:admin"],
    }
}
```

3. **接続失敗の証拠**:
```bash
# 外部からSMTP接続テスト
nc -zv 43.207.242.167 25
# nc: connect to 43.207.242.167 port 25 (tcp) timed out

# Tailscale経由でSMTP接続テスト
nc -zv 100.70.131.116 25
# nc: connect to 100.70.131.116 port 25 (tcp) timed out

# Tailscale経由でSSH接続テスト
ssh ec2-user@100.70.131.116
# ssh: connect to host 100.70.131.116 port 22: Connection timed out
```

**解決方法**:

**Option A: Tailscale ACLに小文字タグを追加** (推奨)

Tailscale管理画面 (https://login.tailscale.com/admin/acls) で以下のように修正:

```json
{
    "grants": [
        {
            "src": [
                "tag:fargate-mx",
                "naoya.iimura@gmail.com",
                "tag:FrontEC2",
                "tag:frontec2"  // ← 小文字タグを追加
            ],
            "dst": ["tag:mailserver"],
            "ip":  ["tcp:25", "tcp:2525", "udp:41641"],
        }
    ],
    "tagOwners": {
        "tag:FrontEC2": ["autogroup:admin"],
        "tag:frontec2": ["autogroup:admin"],  // ← tagOwners にも追加
    }
}
```

**Option B: EC2インスタンスのタグを大文字に変更**

Tailscale管理画面でEC2デバイスのタグを `tag:frontec2` → `tag:FrontEC2` に変更

**検証手順**:

ACL修正後、以下を確認:

```bash
# 1. ACL伝播待機 (通常は即座)
sleep 10

# 2. Tailscale経由でSSH接続テスト
ssh ec2-user@100.70.131.116 "whoami"
# 期待される出力: ec2-user

# 3. Tailscale経由でSMTP接続テスト
nc -zv 100.70.131.116 25
# 期待される出力: Ncat: Connected to 100.70.131.116:25.

# 4. 外部からSMTP接続テスト
nc -zv 43.207.242.167 25
# 期待される出力: Ncat: Connected to 43.207.242.167:25.

# 5. テストメール送信
(echo "EHLO test.example.com"; sleep 1; \
 echo "MAIL FROM:<test@example.com>"; sleep 1; \
 echo "RCPT TO:<test@kuma8088.com>"; sleep 1; \
 echo "DATA"; sleep 1; \
 echo "Subject: ACL Test"; echo ""; echo "Test body"; echo "."; sleep 1; \
 echo "QUIT") | nc 43.207.242.167 25

# 6. EC2ログでSMTPトラフィック確認
aws logs tail /ec2/mailserver-mx --since 5m --format short | grep "connect from"
# 期待される出力: connect from <送信元ホスト>
```

**教訓**:
- **Tailscaleのタグは大文字小文字を厳密に区別する**
- ACL設定時は、実際のデバイスタグとgratsルールのタグが**完全一致**することを確認
- デプロイ後は必ず接続テストを実施し、ACLが正しく適用されているか検証すること
- `tailscale status` で表示されるTagsフィールドを常に確認

---

### 10.2 デプロイ成功確認手順

#### ステップ1: 新しいインスタンス情報確認

```bash
terraform output

# 期待される出力:
# ec2_instance_id = "i-029e28809c430c815"
# ec2_instance_public_ip = "43.207.242.167"
# ec2_instance_private_ip = "10.0.1.158"
```

#### ステップ2: user_data.sh実行完了待機 (180秒)

```bash
echo "⏳ Waiting for user_data.sh to execute (180 seconds)..."
sleep 180
```

#### ステップ3: CloudWatch Logs確認

```bash
# User Data実行ログ確認
aws logs tail /ec2/mailserver-mx --since 10m --format short

# 期待されるログ:
# [timestamp] Installing Docker Compose
# [timestamp] Starting Tailscale service
# [timestamp] Connecting to Tailscale VPN
# [timestamp] Starting Postfix container
# [timestamp] Postfix container started successfully
# [timestamp] EC2 MX Gateway setup completed successfully
```

#### ステップ4: EC2コンソール出力確認

```bash
aws ec2 get-console-output \
  --instance-id i-029e28809c430c815 \
  --latest \
  --query 'Output' \
  --output text | tail -50
```

#### ステップ5: Tailscale接続確認

```bash
# Dell WorkStationから確認
tailscale status | grep mailserver-mx-ec2

# 期待される出力:
# 100.xxx.xxx.xxx  mailserver-mx-ec2  tagged-devices  linux  idle, tx xxx rx xxx
```

#### ステップ6: SMTP受信テスト

```bash
# 外部からSMTP接続テスト
nc -zv 43.207.242.167 25

# 期待される出力:
# Ncat: Connected to 43.207.242.167:25.
```

---

### 10.3 よくある問題と解決策

#### Q1: user_data.sh実行完了の確認方法は？

**A**: CloudWatch LogsまたはEC2コンソール出力で以下のメッセージを確認:

```
EC2 MX Gateway setup completed successfully
Timestamp: [日時]
```

#### Q2: Tailscale接続が確立されない

**A**: 以下を順に確認:

1. Auth keyの有効性確認:
```bash
aws secretsmanager get-secret-value \
  --secret-id mailserver/tailscale/ec2-auth-key \
  --query SecretString --output text
```

2. Tailscale管理画面でauth keyステータス確認
   - https://login.tailscale.com/admin/settings/keys
   - **Used** または **Expired** の場合は新しいkeyを生成

3. EC2インスタンスからTailscale再接続:
```bash
ssh ec2-user@43.207.242.167
sudo tailscale down
sudo tailscale up --authkey="新しいauth key" --accept-routes --hostname="mailserver-mx-ec2"
```

#### Q3: Docker Composeコマンドが見つからない

**A**: user_data.sh内のインストールステップを確認:

```bash
# EC2にSSH接続
ssh ec2-user@43.207.242.167

# Docker Composeバージョン確認
docker-compose --version

# インストールされていない場合は手動インストール:
sudo curl -SL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-aarch64" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
```

#### Q4: Postfixコンテナが起動しない

**A**: コンテナログで原因を確認:

```bash
ssh ec2-user@43.207.242.167
docker logs mailserver-postfix

# よくあるエラー:
# - Tailscale VPNが接続されていない → Q2参照
# - 環境変数設定ミス → docker-compose.ymlを確認
# - ポート25が既に使用中 → `ss -tuln | grep :25` で確認
```

#### Q5: メールがDellにリレーされない

**A**: 接続性を段階的に確認:

```bash
# 1. Tailscale VPN接続確認
tailscale status | grep dell-workstation

# 2. Dell LMTP接続確認
nc -zv 100.110.222.53 2525

# 3. Postfixログでリレー状況確認
docker logs mailserver-postfix | grep "relay="

# 4. Postfixキュー確認
docker exec mailserver-postfix postqueue -p
```

---

### 10.4 緊急時ロールバック手順

**条件**: EC2環境で致命的な問題が発生し、即座にサービス復旧が必要な場合

**手順**:

```bash
# 1. MXレコードをFargate環境に戻す (DNS管理画面で手動変更)
# mx.kuma8088.com A レコード:
# 変更前: 43.207.242.167 (EC2 Elastic IP)
# 変更後: [Fargate Public IP] (aws ecs describe-tasks で取得)

# 2. Fargateタスク起動確認
aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service

# タスクが起動していない場合:
aws ecs update-service \
  --cluster mailserver-cluster \
  --service mailserver-mx-service \
  --desired-count 1

# 3. EC2インスタンス停止 (課金停止)
terraform destroy -target=aws_instance.mailserver_mx -target=aws_eip_association.mailserver_eip_ec2

# 4. サービス復旧確認
nc -zv [Fargate Public IP] 25
```

**ロールバック所要時間**: 約5-10分
**影響**: DNS TTL分のメール受信遅延 (最大60秒)

---

## 11. EC2内部診断チェックリスト

**目的**: SSH接続後、EC2インスタンス内部で確認すべき全項目を体系的にチェックする

### 11.1 前提条件

```bash
# SSH接続 (Public IP経由)
ssh -i ~/.ssh/your-key.pem ec2-user@43.207.242.167

# または Tailscale VPN経由
ssh -i ~/.ssh/your-key.pem ec2-user@100.70.131.116

# rootユーザーに切り替え (必要に応じて)
sudo su -
```

---

### 11.2 システム基本情報確認

#### 11.2.1 OS情報・カーネルバージョン

```bash
# OS バージョン確認
cat /etc/os-release
# 期待される出力:
# NAME="Amazon Linux"
# VERSION="2023"
# ID="amzn"
# PLATFORM_ID="platform:al2023"

# カーネルバージョン確認
uname -a
# 期待される出力: Linux ... 5.x.x-xxx.amzn2023.aarch64 #1 SMP ... aarch64 GNU/Linux

# アーキテクチャ確認
lscpu | grep -E "Architecture|CPU op-mode"
# 期待される出力:
# Architecture:            aarch64
# CPU op-mode(s):          32-bit, 64-bit
```

#### 11.2.2 システムアップタイム・ロードアベレージ

```bash
# システムアップタイム確認
uptime
# 期待される出力: up X days, Y hours, load average: 0.XX, 0.XX, 0.XX

# より詳細な起動時刻確認
who -b
# 期待される出力: system boot YYYY-MM-DD HH:MM
```

#### 11.2.3 システムサービス状態

```bash
# 重要なサービスの状態確認
systemctl status docker
systemctl status tailscaled
systemctl status amazon-cloudwatch-agent

# 全サービスの起動失敗確認
systemctl --failed
# 期待される出力: 0 loaded units listed. (起動失敗なし)
```

---

### 11.3 ネットワーク構成確認

#### 11.3.1 ネットワークインターフェース

```bash
# インターフェース一覧
ip addr show
# 期待される出力:
# 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
#    inet 127.0.0.1/8 scope host lo
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9001 qdisc mq state UP
#    inet 10.0.1.XXX/24 brd 10.0.1.255 scope global dynamic eth0
# 3: tailscale0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1280 qdisc fq_codel state UNKNOWN
#    inet 100.XXX.XXX.XXX/32 scope global tailscale0

# インターフェースのトラフィック統計
ip -s link show
# 期待される出力: RX/TX パケット数、エラー数、ドロップ数
```

#### 11.3.2 ルーティングテーブル

```bash
# IPv4 ルーティングテーブル
ip route show
# 期待される出力:
# default via 10.0.1.1 dev eth0
# 10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.XXX
# 100.64.0.0/10 dev tailscale0  ← Tailscale VPN ルート
# 100.100.100.100 dev tailscale0  ← Tailscale DERP relay

# Tailscale専用ルート確認
ip route show dev tailscale0
# 期待される出力: 100.64.0.0/10, DERP relay routes
```

#### 11.3.3 DNS解決確認

```bash
# DNS設定確認
cat /etc/resolv.conf
# 期待される出力:
# nameserver 10.0.0.2  (VPC DNS)
# nameserver 100.100.100.100  (Tailscale MagicDNS)

# DNS解決テスト (外部)
dig +short google.com
# 期待される出力: IP addresses

# DNS解決テスト (Tailscale MagicDNS)
dig +short dell-workstation.tail67811d.ts.net
# 期待される出力: 100.110.222.53
```

#### 11.3.4 ファイアウォール設定

```bash
# firewalld 状態確認 (Amazon Linux 2023ではデフォルト無効)
systemctl status firewalld
# 期待される出力: Unit firewalld.service could not be found.

# iptables ルール確認
sudo iptables -L -n -v
# 期待される出力:
# Chain INPUT (policy ACCEPT XX packets, XX bytes)
# Chain FORWARD (policy ACCEPT XX packets, XX bytes)
# Chain OUTPUT (policy ACCEPT XX packets, XX bytes)

# Tailscale関連のiptablesルール確認
sudo iptables -t nat -L -n -v | grep -A 10 "ts-"
# 期待される出力: Tailscale NAT rules

# Security Group設定確認 (AWS CLI)
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SecurityGroups' \
  --output table
# 期待される出力: Security Group ID と Name
```

---

### 11.4 Docker環境確認

#### 11.4.1 Docker Daemon状態

```bash
# Docker サービス状態
systemctl status docker
# 期待される出力: active (running)

# Docker バージョン
docker --version
# 期待される出力: Docker version 20.x.x, build xxxxx

# Docker システム情報
docker system info
# 期待される出力:
# Server Version: 20.x.x
# Storage Driver: overlay2
# Logging Driver: json-file
# Cgroup Driver: systemd
# Total Memory: ~512 MiB (t4g.nano)
```

#### 11.4.2 Docker Compose確認

```bash
# Docker Compose バージョン
docker-compose --version
# 期待される出力: Docker Compose version v2.24.0

# docker-compose.yml 配置確認
ls -la /opt/mailserver/docker-compose.yml
# 期待される出力: -rw-r--r-- 1 root root XXXX ... docker-compose.yml

# docker-compose.yml 内容確認
cat /opt/mailserver/docker-compose.yml
# 期待される出力: Postfix service definition
```

#### 11.4.3 コンテナ状態

```bash
# 実行中のコンテナ一覧
docker ps
# 期待される出力:
# CONTAINER ID   IMAGE                 STATUS         PORTS     NAMES
# xxxxx          boky/postfix:latest   Up XX minutes  (empty)   mailserver-postfix

# 全コンテナ (停止含む)
docker ps -a
# 期待される出力: mailserver-postfix のみ

# コンテナ詳細情報
docker inspect mailserver-postfix --format='{{json .State}}' | jq
# 期待される出力:
# {
#   "Status": "running",
#   "Running": true,
#   "Paused": false,
#   "Restarting": false,
#   "Health": {
#     "Status": "healthy",
#     "FailingStreak": 0
#   }
# }

# コンテナリソース使用状況
docker stats --no-stream mailserver-postfix
# 期待される出力: CPU%, MEM USAGE / LIMIT, NET I/O, BLOCK I/O
```

#### 11.4.4 Docker ネットワーク

```bash
# ネットワーク一覧
docker network ls
# 期待される出力:
# NETWORK ID   NAME      DRIVER    SCOPE
# xxxx         bridge    bridge    local
# xxxx         host      host      local  ← Postfixが使用
# xxxx         none      null      local

# Postfixコンテナのネットワーク設定確認
docker inspect mailserver-postfix --format='{{.HostConfig.NetworkMode}}'
# 期待される出力: host
```

#### 11.4.5 Docker ログドライバー

```bash
# Postfixログドライバー設定確認
docker inspect mailserver-postfix --format='{{.HostConfig.LogConfig.Type}}'
# 期待される出力: awslogs

# ログドライバー設定詳細
docker inspect mailserver-postfix --format='{{json .HostConfig.LogConfig}}' | jq
# 期待される出力:
# {
#   "Type": "awslogs",
#   "Config": {
#     "awslogs-group": "/ec2/mailserver-mx",
#     "awslogs-region": "ap-northeast-1",
#     "awslogs-stream": "postfix"
#   }
# }
```

---

### 11.5 Postfix構成確認

#### 11.5.1 Postfix環境変数

```bash
# コンテナ内環境変数確認
docker exec mailserver-postfix env | grep -E "ALLOW_EMPTY|RELAYHOST|POSTFIX_"
# 期待される出力:
# ALLOW_EMPTY_SENDER_DOMAINS=true
# ALLOWED_SENDER_DOMAINS=
# RELAYHOST=[100.110.222.53]:2525
# POSTFIX_inet_protocols=ipv4
# POSTFIX_relay_domains=kuma8088.com, m8088.com
# POSTFIX_smtpd_recipient_restrictions=...
# ...
```

#### 11.5.2 Postfix設定値確認

```bash
# RELAYHOSTの実際の設定値
docker exec mailserver-postfix postconf relayhost
# 期待される出力: relayhost = [100.110.222.53]:2525

# relay_domainsの実際の設定値
docker exec mailserver-postfix postconf relay_domains
# 期待される出力: relay_domains = kuma8088.com, m8088.com

# inet_protocols設定確認 (IPv4のみか確認)
docker exec mailserver-postfix postconf inet_protocols
# 期待される出力: inet_protocols = ipv4

# smtpd_recipient_restrictionsの確認
docker exec mailserver-postfix postconf smtpd_recipient_restrictions
# 期待される出力: smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated, check_relay_domains, permit

# myhostname設定確認
docker exec mailserver-postfix postconf myhostname
# 期待される出力: myhostname = mx.kuma8088.com
```

#### 11.5.3 Postfixキュー状況

```bash
# メールキュー確認
docker exec mailserver-postfix postqueue -p
# 期待される出力:
# Mail queue is empty (正常時)
# または
# (キューにメールがある場合はメール一覧)

# キューサマリー
docker exec mailserver-postfix postqueue -p | tail -1
# 期待される出力: -- 0 Kbytes in 0 Requests. (キュー空の場合)

# 配信待ちメールの詳細確認 (キューにメールがある場合)
docker exec mailserver-postfix postcat -vq <queue_id>
```

#### 11.5.4 Postfixプロセス確認

```bash
# Postfixマスタープロセス確認
docker exec mailserver-postfix ps aux | grep -E "master|pickup|qmgr|smtpd"
# 期待される出力:
# root     1  ... /bin/sh -c /docker-init.sh && postfix start-fg
# postfix  XX ... pickup -l -t unix -u
# postfix  XX ... qmgr -l -t unix -u
# postfix  XX ... smtpd -n smtp -t inet -u -c ...
```

---

### 11.6 Tailscale VPN状態確認

#### 11.6.1 Tailscale サービス状態

```bash
# Tailscaleサービス状態
systemctl status tailscaled
# 期待される出力: active (running)

# Tailscale接続状態
tailscale status
# 期待される出力:
# 100.110.222.53  dell-workstation  tagged-devices  linux  active; direct 192.168.x.x:xxxxx, tx XXX rx XXX
# 100.XXX.XXX.XXX mailserver-mx-ec2 tagged-devices  linux  -

# Tailscale詳細情報
tailscale status --json | jq '.Self'
# 期待される出力:
# {
#   "ID": "...",
#   "HostName": "mailserver-mx-ec2",
#   "DNSName": "mailserver-mx-ec2.tail67811d.ts.net.",
#   "OS": "linux",
#   "TailscaleIPs": ["100.XXX.XXX.XXX"],
#   "Tags": ["tag:frontec2"]
# }
```

#### 11.6.2 Tailscale タグ確認

```bash
# デバイスに割り当てられているタグ確認
tailscale status --json | jq '.Self.Tags'
# 期待される出力: ["tag:frontec2"]

# ピア(Dell)の情報確認
tailscale status --json | jq '.Peer[] | select(.HostName=="dell-workstation")'
# 期待される出力: Dell WorkStationのピア情報
```

#### 11.6.3 Tailscale接続性テスト

```bash
# Dell WorkStationへのpingテスト (Tailscale経由)
tailscale ping 100.110.222.53
# 期待される出力: pong from dell-workstation (100.110.222.53) via DERP in XXms

# Dell WorkStationへのpingテスト (ICMP)
ping -c 3 100.110.222.53
# 期待される出力: 3 packets transmitted, 3 received, 0% packet loss

# Dell LMTP ポート接続テスト
nc -zv 100.110.222.53 2525
# 期待される出力: Ncat: Connected to 100.110.222.53:2525.

# Dell LMTP ポート接続テスト (timeout付き)
timeout 5 nc -zv 100.110.222.53 2525 && echo "SUCCESS" || echo "FAILED"
```

#### 11.6.4 Tailscale ルーティング確認

```bash
# Tailscale経由のルート確認
ip route show dev tailscale0
# 期待される出力:
# 100.64.0.0/10 dev tailscale0 scope link
# 100.100.100.100 dev tailscale0 scope link  ← DERP relay

# --accept-routes オプション確認
tailscale status --json | jq '.Self.AllowedIPs'
# 期待される出力: Tailscaleから広告されているルート
```

---

### 11.7 ポート・リスニング状態確認

#### 11.7.1 全リスニングポート確認

```bash
# TCP/UDP リスニングポート一覧
ss -tuln
# 期待される出力:
# Netid  State   Recv-Q  Send-Q  Local Address:Port   Peer Address:Port
# tcp    LISTEN  0       100     0.0.0.0:25            0.0.0.0:*       ← Postfix SMTP
# tcp    LISTEN  0       128     0.0.0.0:22            0.0.0.0:*       ← SSH
# udp    UNCONN  0       0       0.0.0.0:41641         0.0.0.0:*       ← Tailscale

# より詳細なリスニング情報 (プロセス名表示)
sudo ss -tulnp
# 期待される出力: プロセス名とPIDも表示
```

#### 11.7.2 SMTP ポート確認

```bash
# ポート25がリスニング中か確認
ss -tuln | grep :25
# 期待される出力:
# tcp   LISTEN  0  100  0.0.0.0:25  0.0.0.0:*

# ポート25のプロセス確認
sudo lsof -i :25
# 期待される出力:
# COMMAND   PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# master    XXX  postfix   13u  IPv4  XXXX      0t0  TCP *:smtp (LISTEN)

# ローカルからSMTP接続テスト
nc -zv localhost 25
# 期待される出力: Ncat: Connected to localhost:25.

# SMTP バナー確認
echo "QUIT" | nc localhost 25
# 期待される出力:
# 220 mx.kuma8088.com ESMTP Postfix
# 221 2.0.0 Bye
```

#### 11.7.3 Tailscale ポート確認

```bash
# Tailscale UDP ポート確認 (通常41641)
ss -tuln | grep 41641
# 期待される出力:
# udp   UNCONN  0  0  0.0.0.0:41641  0.0.0.0:*

# Tailscaleプロセス確認
sudo lsof -i UDP:41641
# 期待される出力:
# COMMAND     PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# tailscaled  XXX root   XX   IPv4  XXXX      0t0  UDP *:41641
```

---

### 11.8 ログファイル確認

#### 11.8.1 user_data.sh 実行ログ

```bash
# user_data.sh実行ログ確認
cat /var/log/user-data.log
# 期待される出力:
# [timestamp] Starting EC2 MX Gateway setup
# [timestamp] Updating system packages
# ...
# [timestamp] EC2 MX Gateway setup completed successfully

# 最後の20行確認 (エラー検出)
tail -20 /var/log/user-data.log

# エラー行の検索
grep -i error /var/log/user-data.log
# 期待される出力: (何も表示されない = エラーなし)
```

#### 11.8.2 Postfix ログ (Dockerコンテナ)

```bash
# Postfix最新ログ確認
docker logs mailserver-postfix --tail 50
# 期待される出力:
# postfix/master[X]: daemon started -- version X.X.X
# ‣ NOTE  Forwarding all emails to [100.110.222.53]:2525 without any authentication.

# リアルタイムログ監視
docker logs mailserver-postfix -f

# エラーログのみ抽出
docker logs mailserver-postfix 2>&1 | grep -i -E "error|warning|fatal"

# リレー状況確認
docker logs mailserver-postfix 2>&1 | grep "relay=" | tail -10
# 期待される出力: to=<...>, relay=[100.110.222.53]:2525, ...status=sent
```

#### 11.8.3 システムログ (journalctl)

```bash
# Docker サービスログ
journalctl -u docker --since "1 hour ago" --no-pager
# 期待される出力: Docker daemon起動・コンテナ操作ログ

# Tailscale サービスログ
journalctl -u tailscaled --since "1 hour ago" --no-pager
# 期待される出力: Tailscale VPN接続・切断ログ

# CloudWatch Agent ログ
journalctl -u amazon-cloudwatch-agent --since "1 hour ago" --no-pager
# 期待される出力: CloudWatch Agentメトリクス送信ログ

# カーネルログ (ネットワーク関連)
journalctl -k --since "1 hour ago" --no-pager | grep -i -E "eth0|tailscale|network"
```

#### 11.8.4 CloudWatch Logs (AWS CLI)

```bash
# EC2インスタンスIDの取得
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)

# CloudWatch Logs 最新ログ確認
aws logs tail /ec2/mailserver-mx --since 30m --format short

# Postfixログストリーム確認
aws logs tail /ec2/mailserver-mx --log-stream-name postfix --since 30m --format short

# user-dataログストリーム確認
aws logs tail /ec2/mailserver-mx --log-stream-name user-data --format short
```

---

### 11.9 接続性テスト

#### 11.9.1 内部から外部への接続

```bash
# インターネット接続確認
ping -c 3 8.8.8.8
# 期待される出力: 3 packets transmitted, 3 received, 0% packet loss

# DNS解決確認
ping -c 3 google.com
# 期待される出力: PING google.com (142.250.x.x) ... 3 packets transmitted, 3 received

# HTTP/HTTPS接続確認
curl -I https://www.google.com
# 期待される出力: HTTP/2 200
```

#### 11.9.2 Dell WorkStationへの接続

```bash
# Tailscale VPN経由でDell Workstationにping
ping -c 3 100.110.222.53
# 期待される出力: 3 packets transmitted, 3 received, 0% packet loss

# Dell LMTP ポート接続確認
nc -zv 100.110.222.53 2525
# 期待される出力: Ncat: Connected to 100.110.222.53:2525.

# Dell LMTPとの対話的接続テスト
telnet 100.110.222.53 2525
# 期待される応答:
# 220 dell-workstation.tail67811d.ts.net ESMTP Postfix (Dovecot LMTP)
# (QUIT で終了)
```

#### 11.9.3 外部からEC2への接続 (Dell WorkStationから実行)

**注意**: この操作はDell WorkStation側で実行

```bash
# Dell WorkStationからEC2へのping (Tailscale経由)
tailscale ping <EC2 Tailscale IP>
# 期待される出力: pong from mailserver-mx-ec2 via DERP in XXms

# Dell WorkStationからEC2 SMTP接続テスト
nc -zv <EC2 Tailscale IP> 25
# 期待される出力: Ncat: Connected to <EC2 IP>:25.

# Dell WorkStationからEC2 Public IP SMTP接続テスト
nc -zv 43.207.242.167 25
# 期待される出力: Ncat: Connected to 43.207.242.167:25.
```

#### 11.9.4 SMTP E2Eテスト

```bash
# EC2にSSH接続した状態で、外部メールサーバー経由でSMTP受信テスト
# (事前にDellのRoundcubeにログインし、受信トレイを確認できる状態にしておく)

# テストメール送信 (別のターミナルから)
(echo "EHLO test.example.com"; sleep 1; \
 echo "MAIL FROM:<test@example.com>"; sleep 1; \
 echo "RCPT TO:<your-email@kuma8088.com>"; sleep 1; \
 echo "DATA"; sleep 1; \
 echo "Subject: EC2 MX Gateway Test"; echo ""; \
 echo "This is a test mail from EC2 MX Gateway"; \
 echo "."; sleep 1; \
 echo "QUIT") | nc 43.207.242.167 25

# EC2でPostfixログ確認
docker logs mailserver-postfix --tail 20 | grep "relay="
# 期待される出力: status=sent (relay to Dell via Tailscale)

# Dell でDovecotログ確認 (Dell WorkStationで実行)
docker logs mailserver-dovecot --tail 20 | grep "saved mail"
# 期待される出力: lmtp(...): saved mail to INBOX

# Roundcubeで受信トレイ確認 (ブラウザ)
# https://dell-workstation.tail67811d.ts.net/
# 受信トレイに "EC2 MX Gateway Test" というメールが届いているか確認
```

---

### 11.10 セキュリティ設定確認

#### 11.10.1 SELinux状態

```bash
# SELinux状態確認
getenforce
# 期待される出力: Enforcing (有効) または Disabled (無効)

# SELinux設定確認
cat /etc/selinux/config
# 期待される出力: SELINUX=enforcing または permissive または disabled

# SELinux拒否ログ確認 (有効な場合)
ausearch -m avc -ts recent
# 期待される出力: <no matches> (拒否なし) または 拒否ログ
```

#### 11.10.2 iptablesルール確認

```bash
# IPv4 iptables ルール確認
sudo iptables -L -n -v
# 期待される出力: デフォルトポリシーACCEPT、Tailscale関連ルール

# NAT テーブル確認
sudo iptables -t nat -L -n -v
# 期待される出力: Tailscale NAT rules (ts-forward, ts-input)

# Tailscale専用チェーン確認
sudo iptables -L ts-forward -n -v
sudo iptables -L ts-input -n -v
# 期待される出力: Tailscale traffic forwarding rules
```

#### 11.10.3 SSH設定確認

```bash
# SSH設定ファイル確認
sudo cat /etc/ssh/sshd_config | grep -E "PermitRootLogin|PasswordAuthentication|PubkeyAuthentication"
# 期待される出力:
# PermitRootLogin no または prohibit-password
# PasswordAuthentication no
# PubkeyAuthentication yes

# SSH公開鍵確認
cat ~/.ssh/authorized_keys
# 期待される出力: 登録済み公開鍵リスト

# SSHアクティブ接続確認
who
# 期待される出力: 現在のSSHセッション情報
```

#### 11.10.4 AWS Security Group確認

```bash
# インスタンスIDの取得
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)

# Security Group ID取得
SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Security Group Ingress ルール確認
aws ec2 describe-security-groups --group-ids $SG_ID \
  --query 'SecurityGroups[0].IpPermissions' \
  --output table

# ポート25のルール詳細確認
aws ec2 describe-security-groups --group-ids $SG_ID \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`25`]' \
  --output table
# 期待される出力:
# FromPort: 25
# ToPort: 25
# IpProtocol: tcp
# IpRanges: 0.0.0.0/0
```

---

### 11.11 リソース使用状況確認

#### 11.11.1 CPU・メモリ使用率

```bash
# リアルタイムリソース監視 (top)
top -n 1 -b | head -20
# 期待される出力: CPU使用率, メモリ使用率, プロセス一覧

# CPU使用率のみ確認
top -n 1 -b | grep "Cpu(s)" | awk '{print $2}' | cut -d% -f1
# 期待される出力: XX.X (CPUアイドル率)

# メモリ使用状況
free -h
# 期待される出力:
#               total        used        free      shared  buff/cache   available
# Mem:          480Mi       XXXMi       XXXMi       XXMi       XXXMi       XXXMi
# Swap:           0B          0B          0B

# プロセス別メモリ使用状況
ps aux --sort=-%mem | head -10
# 期待される出力: メモリ使用率上位10プロセス
```

#### 11.11.2 ディスク使用状況

```bash
# ディスク使用率
df -h
# 期待される出力:
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/xvda1      8.0G  X.XG  X.XG  XX% /
# tmpfs           240M     0  240M   0% /dev/shm
# /dev/xvda128     10M  X.XM  X.XM  XX% /boot/efi

# inode使用状況
df -i
# 期待される出力: inode使用率 (通常 <10%)

# Docker関連ディスク使用状況
docker system df
# 期待される出力:
# TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
# Images          X         X         XXX MB    XXX MB (XX%)
# Containers      X         X         XXX kB    XXX kB (XX%)
# Local Volumes   X         X         XXX MB    XXX MB (XX%)
```

#### 11.11.3 ネットワーク帯域使用状況

```bash
# インターフェース別トラフィック統計
ip -s link show
# 期待される出力:
# eth0: RX bytes: XXXXXXX, TX bytes: XXXXXXX
# tailscale0: RX bytes: XXXXXXX, TX bytes: XXXXXXX

# リアルタイムネットワーク使用率 (ifstat がある場合)
# sudo dnf install -y sysstat
# ifstat -i eth0,tailscale0 1 3
# 期待される出力: 1秒ごとの送受信レート (KB/s)

# Docker コンテナのネットワーク使用状況
docker stats --no-stream mailserver-postfix --format "table {{.Name}}\t{{.NetIO}}"
# 期待される出力: mailserver-postfix    XXX kB / XXX kB
```

---

### 11.12 CloudWatch Agent確認

#### 11.12.1 CloudWatch Agent状態

```bash
# CloudWatch Agent サービス状態
systemctl status amazon-cloudwatch-agent
# 期待される出力: active (running)

# CloudWatch Agent 設定ファイル確認
cat /opt/aws/amazon-cloudwatch-agent/etc/config.json
# 期待される出力: logs と metrics 設定

# CloudWatch Agent ログ確認
journalctl -u amazon-cloudwatch-agent --since "1 hour ago" --no-pager | tail -50
# 期待される出力: メトリクス送信・ログ送信のログ
```

#### 11.12.2 CloudWatch Metrics送信確認

```bash
# インスタンスIDの取得
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)

# CloudWatch カスタムメトリクス確認 (CPU使用率)
aws cloudwatch get-metric-statistics \
  --namespace Mailserver/EC2 \
  --metric-name CPU_IDLE \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average \
  --output table

# CloudWatch カスタムメトリクス確認 (メモリ使用率)
aws cloudwatch get-metric-statistics \
  --namespace Mailserver/EC2 \
  --metric-name MEM_USED \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average \
  --output table
```

---

### 11.13 よくある問題の診断コマンド集

#### 11.13.1 メール受信失敗時

```bash
# 1. SMTP ポート開放確認
ss -tuln | grep :25
# 期待される出力: LISTEN 状態

# 2. Postfix プロセス確認
docker exec mailserver-postfix ps aux | grep master
# 期待される出力: postfix master process

# 3. Postfix エラーログ確認
docker logs mailserver-postfix 2>&1 | grep -i -E "error|fatal|warning" | tail -20

# 4. Security Group確認
aws ec2 describe-security-groups --group-ids $(aws ec2 describe-instances \
  --instance-ids $(ec2-metadata --instance-id | cut -d " " -f 2) \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text) \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`25`]'

# 5. iptables確認
sudo iptables -L INPUT -n -v | grep -E "25|ACCEPT"
```

#### 11.13.2 Tailscale接続失敗時

```bash
# 1. Tailscale サービス確認
systemctl status tailscaled
# 期待される出力: active (running)

# 2. Tailscale接続状態確認
tailscale status
# 期待される出力: Dell WorkStationが "active" または "idle"

# 3. Tailscale再接続
sudo tailscale down
sudo tailscale up --accept-routes

# 4. Tailscale ログ確認
journalctl -u tailscaled --since "10 minutes ago" --no-pager | tail -30

# 5. Tailscale ping確認
tailscale ping 100.110.222.53
# 期待される出力: pong from dell-workstation
```

#### 11.13.3 メールリレー失敗時

```bash
# 1. RELAYHOST設定確認
docker exec mailserver-postfix postconf relayhost
# 期待される出力: relayhost = [100.110.222.53]:2525

# 2. Dell LMTP接続確認
nc -zv 100.110.222.53 2525
# 期待される出力: Ncat: Connected

# 3. Postfixキュー確認
docker exec mailserver-postfix postqueue -p
# 期待される出力: Mail queue is empty (正常) または キューにメールあり

# 4. Postfixリレーログ確認
docker logs mailserver-postfix 2>&1 | grep "relay=" | tail -10
# 期待される出力: status=sent または status=deferred

# 5. Dell側のLMTPログ確認 (Dell WorkStationで実行)
docker logs mailserver-dovecot 2>&1 | grep "lmtp" | tail -20
```

#### 11.13.4 Docker起動失敗時

```bash
# 1. Docker サービス状態確認
systemctl status docker
# 期待される出力: active (running)

# 2. Docker サービス起動
sudo systemctl start docker

# 3. Docker ログ確認
journalctl -u docker --since "10 minutes ago" --no-pager | tail -30

# 4. Docker Compose設定確認
cd /opt/mailserver && docker-compose config
# 期待される出力: パースされたdocker-compose.yml

# 5. コンテナ手動起動
cd /opt/mailserver && docker-compose up -d
```

---

### 11.14 診断結果レポート生成

全ての確認項目を自動実行し、レポートファイルに出力するスクリプト例:

```bash
#!/bin/bash
# EC2診断レポート生成スクリプト
# 実行: sudo bash /opt/mailserver/diagnostic-report.sh

REPORT_FILE="/var/log/ec2-diagnostic-$(date +%Y%m%d-%H%M%S).log"

echo "=== EC2 MX Gateway Diagnostic Report ===" > $REPORT_FILE
echo "Timestamp: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 1. System Information ###" >> $REPORT_FILE
uname -a >> $REPORT_FILE
cat /etc/os-release >> $REPORT_FILE
uptime >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 2. Service Status ###" >> $REPORT_FILE
systemctl status docker --no-pager >> $REPORT_FILE 2>&1
systemctl status tailscaled --no-pager >> $REPORT_FILE 2>&1
systemctl status amazon-cloudwatch-agent --no-pager >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "### 3. Network Interfaces ###" >> $REPORT_FILE
ip addr show >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 4. Routing Table ###" >> $REPORT_FILE
ip route show >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 5. Listening Ports ###" >> $REPORT_FILE
ss -tuln >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 6. Docker Containers ###" >> $REPORT_FILE
docker ps -a >> $REPORT_FILE
docker stats --no-stream mailserver-postfix >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "### 7. Postfix Configuration ###" >> $REPORT_FILE
docker exec mailserver-postfix postconf relayhost >> $REPORT_FILE 2>&1
docker exec mailserver-postfix postconf relay_domains >> $REPORT_FILE 2>&1
docker exec mailserver-postfix postqueue -p >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "### 8. Tailscale Status ###" >> $REPORT_FILE
tailscale status >> $REPORT_FILE
tailscale ping 100.110.222.53 >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "### 9. Connectivity Tests ###" >> $REPORT_FILE
nc -zv localhost 25 >> $REPORT_FILE 2>&1
nc -zv 100.110.222.53 2525 >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "### 10. Resource Usage ###" >> $REPORT_FILE
free -h >> $REPORT_FILE
df -h >> $REPORT_FILE
top -n 1 -b | head -20 >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "### 11. Recent Logs ###" >> $REPORT_FILE
echo "--- user_data.sh ---" >> $REPORT_FILE
tail -50 /var/log/user-data.log >> $REPORT_FILE
echo "--- Postfix ---" >> $REPORT_FILE
docker logs mailserver-postfix --tail 30 >> $REPORT_FILE 2>&1
echo "--- Tailscale ---" >> $REPORT_FILE
journalctl -u tailscaled --since "30 minutes ago" --no-pager >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "=== Report Generated: $REPORT_FILE ===" >> $REPORT_FILE

echo "✅ Diagnostic report generated: $REPORT_FILE"
cat $REPORT_FILE
```

使用方法:

```bash
# レポート生成スクリプト作成
sudo cat > /opt/mailserver/diagnostic-report.sh <<'EOF'
[上記のスクリプト内容]
EOF

# 実行権限付与
sudo chmod +x /opt/mailserver/diagnostic-report.sh

# レポート生成
sudo /opt/mailserver/diagnostic-report.sh

# レポート確認
ls -lh /var/log/ec2-diagnostic-*.log
```

---

## 12. 重要な設定上の注意事項

### ⚠️ SMTP→LMTPプロトコル設定の重要性

**概要**: EC2 PostfixからDell Dovecotへのメールリレー時には、**必ずLMTPプロトコルを使用**すること。

#### プロトコルの違い

| プロトコル | 用途 | Postfix環境変数 | 使用例 |
|-----------|------|----------------|--------|
| **SMTP** | MTA間メール転送 (Server-to-Server) | `RELAYHOST` | 外部メールサーバーへのリレー |
| **LMTP** | MTA→MDA最終配信 (Server-to-Local) | `POSTFIX_relay_transport=lmtp:` | Dovecotへの最終配信 |

#### ❌ 誤った設定例

```yaml
environment:
  - RELAYHOST=[100.110.222.53]:2525  # ❌ SMTPプロトコル → エラー発生
```

**エラーログ**:
```
status=bounced (host 100.110.222.53[100.110.222.53] refused to talk to me: 500 5.5.1 Unknown command)
```

**原因**: PostfixがSMTP `HELO`コマンドを送信するが、DovecotはLMTPプロトコルを期待しているため拒否。

#### ✅ 正しい設定例

```yaml
environment:
  - POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525  # ✅ LMTPプロトコル
```

**成功ログ**:
```
status=sent (250 2.0.0 <recipient@kuma8088.com> ... Saved)
```

#### 設定チェックリスト

EC2メールサーバーを構築・再構築する際は、以下を必ず確認してください:

- [ ] `RELAYHOST`環境変数を**使用していない**こと
- [ ] `POSTFIX_relay_transport=lmtp:[Dell-IP]:2525`を設定していること
- [ ] Dell側のポート2525がDovecot **LMTPサービス**であることを確認
- [ ] `relay_domains`に**有効なドメインのみ**が含まれていること（例: kuma8088.com）
- [ ] 不要なドメイン（例: m8088.com）が**削除されている**こと

#### 検証方法

```bash
# 1. Postfix設定確認
docker exec mailserver-postfix postconf relay_transport
# 期待される出力: relay_transport = lmtp:[100.110.222.53]:2525

# 2. テストメール送信
echo "Test" | docker exec -i mailserver-postfix sendmail -f test@kuma8088.com target@kuma8088.com

# 3. 成功ログ確認
docker logs mailserver-postfix | grep "status=sent.*Saved"
# 期待される出力: status=sent (250 2.0.0 ... Saved)

# 4. Dell側LMTP配信確認 (Dell WorkStationで実行)
docker logs mailserver-dovecot | grep "saved mail"
# 期待される出力: lmtp(...): saved mail to INBOX
```

#### トラブルシューティング参照

プロトコル設定に関する詳細なトラブルシューティングは、以下のドキュメントを参照してください:

- **完全なトラブルシューティングガイド**: `services/mailserver/troubleshoot/EC2_MAIL_PROTOCOL_ISSUE_2025-11-04.md`
- **根本原因分析**: SMTP→LMTPプロトコル不一致の詳細な解説
- **再構築時のチェックリスト**: 全ての設定ファイルの一貫性確認手順

---

**作成者**: Claude Code
**レビュー**: 未実施
**承認**: 未実施
**ステータス**: 実装中 (デプロイ完了待ち)
