# メールサーバー構築プロジェクト - 設計書

**文書バージョン**: 5.1
**作成日**: 2025-10-31（初版）/ 2025-11-01（v5.0改訂）/ 2025-11-02（v5.1改訂）
**対象環境**: AWS Fargate（MXゲートウェイ） + Dell RockyLinux 9.6（メール本体） + SendGrid SMTP Relay + Tailscale VPN
**設計方式**: ハイブリッドクラウド構成（AWS Fargate + オンプレミスDell + SaaSリレー）
**参照文書**: 01_requirements.md v5.0
**リージョン**: ap-northeast-1 (東京)

---

## 1. システムアーキテクチャ

### 1.1 全体構成図（Fargate + Dell + SendGrid + Tailscale VPN）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          インターネット（外部メール受信）                      │
│                                                                               │
│  ┌─────────────────┐                                                        │
│  │ 外部メールサーバー │  Port 25 SMTP                                        │
│  │ (Gmail, etc.)   │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           │  MX Record → xx.xx.xx.xx (Fargate Public IP or Elastic IP)     │
└───────────┼──────────────────────────────────────────────────────────────────┘
            │
            ▼ Port 25 (SMTP)
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AWS クラウド環境（東京リージョン）                    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              AWS ECS Fargate Service (MX Gateway)                    │   │
│  │              Public IP/Elastic IP 直接受信 (Port 25)                 │   │
│  │                                                                       │   │
│  │  ┌─────────────────────┐                                            │   │
│  │  │ Fargate Task        │                                            │   │
│  │  │ ┌─────────────────┐ │                                            │   │
│  │  │ │ Postfix         │ │                                            │   │
│  │  │ │ (Port 25 受信)  │ │                                            │   │
│  │  │ │ 172.17.0.2      │ │                                            │   │
│  │  │ │ Public IP: xx.xx.xx.xx (Dynamic or Elastic)                   │   │
│  │  │ └─────────────────┘ │                                            │   │
│  │  │ ┌─────────────────┐ │                                            │   │
│  │  │ │ Tailscale       │ │                                            │   │
│  │  │ │ Client          │ │                                            │   │
│  │  │ │ 100.x.x.1       │ │                                            │   │
│  │  │ └─────────────────┘ │                                            │   │
│  │  └─────────────────────┘                                            │   │
│  │  - タスク定義: CPU 256, Memory 512 MB                                │   │
│  │  - ネットワークモード: awsvpc                                         │   │
│  │  - Auto Scaling: 1-5タスク (将来拡張)                               │   │
│  │  - Public IP割り当て: 有効 (Dynamic or Elastic IP)                  │   │
│  │  - ログ: CloudWatch Logs (30日保存)                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AWS Secrets Manager                               │   │
│  │  - Tailscale Auth Key (Fargate用)                                   │   │
│  │  - SendGrid API Key                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└───────────────────────┬───────────────────────────────────────────────────────┘
                        │
                        │ Tailscale VPN Encrypted Tunnel
                        │ (LMTP/SMTP over Port 2525)
                        │
┌───────────────────────┴───────────────────────────────────────────────────────┐
│                     Tailscale VPN ネットワーク                                 │
│                  (100.x.x.x/10 プライベート空間)                               │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                        │
│  │  PC/Mac      │  │  iPhone      │  │   Android    │                        │
│  │  Tailscale   │  │  Tailscale   │  │   Tailscale  │                        │
│  │  Client      │  │  Client      │  │   Client     │                        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                        │
│         │                  │                  │                                 │
│         └──────────────────┼──────────────────┘                                 │
│                            │ Tailscale Encrypted Tunnel                        │
│                            ▼                                                    │
│                  ┌─────────────────────┐                                       │
│                  │   Tailscale Node    │                                       │
│                  │  mailserver         │                                       │
│                  │  100.x.x.10         │                                       │
│                  │  (MagicDNS有効)     │                                       │
└──────────────────┴─────────────────────┴───────────────────────────────────────┘
                              ▲ ▼
                    ┌─────────────────────┐
                    │   NTT RX-600KI      │
                    │   光電話ルータ       │
                    │  192.168.1.1        │
                    │ ─────────────────   │
                    │ ポート転送: 不要    │
                    │ (Tailscale VPN経由) │
                    └─────────────────────┘
                              ▲ ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Dell RockyLinux 9.6 ホスト（メール本体）                    │
│                   192.168.1.39 (ローカルネットワーク)                         │
│                   100.x.x.10 (Tailscale IP)                                   │
│                   mailserver.tail<xxxxx>.ts.net                               │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │           Docker Compose ネットワーク                                  │    │
│  │           (mailserver_network: 172.20.0.0/24)                         │    │
│  │                                                                        │    │
│  │  ┌──────────────┐    ┌──────────────┐                               │    │
│  │  │    Nginx      │    │  Dovecot     │                               │    │
│  │  │   (Reverse    │    │   (MDA)      │                               │    │
│  │  │    Proxy)     │    │  Port 993    │                               │    │
│  │  │ Port 80/443   │    │  Port 995    │                               │    │
│  │  │ 172.20.0.10   │    │  Port 2525   │  ← Fargate LMTP転送受信      │    │
│  │  │(Tailscale経由)│    │ 172.20.0.30  │                               │    │
│  │  └───────┬───────┘    └──────┬───────┘                               │    │
│  │          │                   │                                        │    │
│  │          │                   ▼                                        │    │
│  │          │             ┌─────────────┐                               │    │
│  │          │             │   Rspamd    │                               │    │
│  │          │             │ (スパム検知) │                               │    │
│  │          │             │ Port 11333  │                               │    │
│  │          │             │ 172.20.0.70 │                               │    │
│  │          │             └──────┬──────┘                               │    │
│  │          │                    │                                       │    │
│  │          │                    ▼                                       │    │
│  │          │             ┌─────────────┐                               │    │
│  │          │             │   ClamAV    │                               │    │
│  │          │             │(ウイルス検知)│                               │    │
│  │          │             │ Port 3310   │                               │    │
│  │          │             │ 172.20.0.80 │                               │    │
│  │          │             └──────┬──────┘                               │    │
│  │          │                    │                                       │    │
│  │    ┌─────▼─────────────────┬─▼──────────┐                          │    │
│  │    │      Roundcube        │  Postfix   │ Port 587 →               │    │
│  │    │      (Webmail)        │  (送信)    │ SendGrid SMTP Relay      │    │
│  │    │   Port 9000 (内部)    │172.20.0.20 │                          │    │
│  │    │   172.20.0.40         │            │                          │    │
│  │    └───────┬───────────────┴────────────┘                          │    │
│  │            │                                                          │    │
│  │      ┌─────▼──────┐                                                  │    │
│  │      │  MariaDB   │                                                  │    │
│  │      │   (DB)     │                                                  │    │
│  │      │ Port 3306  │                                                  │    │
│  │      │172.20.0.60 │                                                  │    │
│  │      └────────────┘                                                  │    │
│  │                                                                        │    │
│  │  ┌────────────────────────────────────────────────────────────┐     │    │
│  │  │         永続化ボリューム                                      │     │    │
│  │  │  /data/docker/volumes/mailserver/                            │     │    │
│  │  │    ├── mail/           (メールデータ)                        │     │    │
│  │  │    ├── db/             (データベース)                        │     │    │
│  │  │    ├── rspamd/         (スパム学習データ)                    │     │    │
│  │  │    ├── clamav/         (ウイルス定義)                        │     │    │
│  │  │    └── config/         (設定ファイル)                        │     │    │
│  │  └────────────────────────────────────────────────────────────┘     │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │              Tailscale エージェント                                   │    │
│  │  - MagicDNS: mailserver.tail<xxxxx>.ts.net                          │    │
│  │  - HTTPS証明書: 自動発行                                            │    │
│  │  - ACL: Tailscale管理画面で制御                                     │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Port 587/TLS (SMTP認証送信)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SendGrid SMTP Relay                                  │
│                          smtp.sendgrid.net:587                                │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  - SPF/DKIM/DMARC自動管理                                            │    │
│  │  - 送信ドメイン認証（DNS設定）                                        │    │
│  │  - 送信レピュテーション管理                                          │    │
│  │  - API Key認証                                                       │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└───────────────────────┬─────────────────────────────────────────────────────┘
                        │
                        │ 外部メール配信
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     外部メールサーバー（受信者）                               │
│                     (Gmail, Yahoo, etc.)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**重要な設計ポイント**:
- **AWS Fargate**: サーバーレスMXゲートウェイ（Port 25受信専用、ステートレス）
  - **Public IP/Elastic IP直接受信**: ALB不要、MXレコードでFargate IP直接指定
  - **動的Public IP** (無料): タスク再起動時にIP変更、DNS更新必要
  - **Elastic IP** (推奨、+$3.60/月): 固定IP、DNS更新不要
- **Dell RockyLinux**: Tailscale VPN経由でメールボックス管理・WEBメール提供
- **SendGrid SMTP Relay**: 外部送信専用（Port 587/TLS認証、SPF/DKIM/DMARC自動管理）
- **Tailscale VPN**: Fargate ↔ Dell間の暗号化トンネル（LMTP Port 2525）、クライアント ↔ Dell間のプライベートアクセス
- **AWS Secrets Manager**: Tailscale Auth Key、SendGrid API Keyの安全な保管
- **CloudWatch Logs**: Fargateコンテナログの集約・保存（30日）
- **東京リージョン (ap-northeast-1)**: 低レイテンシー、日本語サポート

---

### 1.2 コンポーネント一覧

#### 1.2.1 AWS Fargateコンポーネント

| コンポーネント | 役割 | IPアドレス | ポート（内部） | ポート（公開） | イメージ |
|----------------|------|-----------|----------------|----------------|----------|
| **Postfix (Fargate)** | SMTP受信専用（Port 25） | 172.17.0.2 (awsvpc) + Public IP | 25 | インターネット直接公開 | bokysan/postfix:latest |
| **Tailscale (Fargate)** | VPNクライアント | 100.x.x.1-5 | - | 41641/udp | tailscale/tailscale:stable |

#### 1.2.2 Dell RockyLinuxコンポーネント

| コンポーネント | 役割 | IPアドレス | ポート（内部） | ポート（公開） | イメージ |
|----------------|------|-----------|----------------|----------------|----------|
| **Nginx** | リバースプロキシ、SSL終端 | 172.20.0.10 | 80, 443 | Tailscale経由のみ | nginx:1.26-alpine |
| **Postfix (Dell)** | 送信専用（SendGrid経由） | 172.20.0.20 | 587 | - (内部のみ) | bokysan/postfix:latest |
| **Dovecot** | メール配信エージェント（MDA） | 172.20.0.30 | 993, 995, 2525 | Tailscale経由のみ | dovecot/dovecot:2.3.21 |
| **Roundcube** | WEBメールインターフェース | 172.20.0.40 | 9000 | - (Nginx経由) | roundcube/roundcubemail:1.6.7-apache |
| **MariaDB** | データベース | 172.20.0.60 | 3306 | - (内部のみ) | mariadb:10.11.7 |
| **Rspamd** | スパムフィルタ・milter | 172.20.0.70 | 11333, 11334 | - (内部のみ) | rspamd/rspamd:3.8 |
| **ClamAV** | ウイルススキャン | 172.20.0.80 | 3310 | - (内部のみ) | clamav/clamav:1.3 |
| **Tailscale (Dell)** | VPNエージェント | ホストネットワーク | - | 100.x.x.10/10 | tailscale/tailscale:latest |

#### 1.2.3 外部サービス

| サービス | 役割 | エンドポイント | 認証方式 |
|---------|------|--------------|----------|
| **SendGrid SMTP Relay** | 外部送信専用SMTP | smtp.sendgrid.net:587 | API Key (PLAIN認証) |
| **Tailscale Coordination** | VPN接続管理 | controlplane.tailscale.com | Auth Key |

**注記**:
- 各コンテナイメージのバージョンは四半期ごとに見直し、脆弱性修正が公開された場合は計画的に更新する
- Fargate側はステートレス設計（メール保存なし、即時Dell転送）
- Dell側のみデータ永続化を実施

---

## 2. ネットワーク設計

### 2.1 AWS VPCネットワーク構成

```yaml
VPC名: mailserver-vpc
CIDR: 10.0.0.0/16
リージョン: ap-northeast-1 (東京)

サブネット構成:
  - パブリックサブネット1: 10.0.1.0/24 (ap-northeast-1a)
  - パブリックサブネット2: 10.0.2.0/24 (ap-northeast-1c)

インターネットゲートウェイ: igw-mailserver
ルートテーブル:
  - 0.0.0.0/0 → igw-mailserver (インターネット向け)

セキュリティグループ:
  - fargate-sg:
      Inbound: Port 25/tcp (0.0.0.0/0) # SMTP受信（インターネット公開）
      Inbound: Port 41641/udp (0.0.0.0/0) # Tailscale VPN
      Outbound: All traffic
```

### 2.2 DNS設計（MXレコード構成）

#### 2.2.1 Public IP方式（動的IP）

**MXレコード設定**:
```dns
# MXレコードでFargate Public IPを直接指定
kuma8088.com.              IN  MX  10  xx.xx.xx.xx.
fx-trader-life.com.        IN  MX  10  xx.xx.xx.xx.
webmakeprofit.org.         IN  MX  10  xx.xx.xx.xx.
webmakesprofit.com.        IN  MX  10  xx.xx.xx.xx.
```

**注意事項**:
- Fargateタスク再起動時にPublic IPが変更される
- DNS更新が必要（手動またはスクリプト自動化）
- 低コスト（無料）だが運用負荷あり

#### 2.2.2 Elastic IP方式（固定IP）推奨

**Elastic IP設定**:
```yaml
Elastic IP名: mailserver-mx-eip
割り当て先: Fargate ENI (ECS Service起動時に自動割り当て)
コスト: $3.60/月
```

**MXレコード設定**:
```dns
# Elastic IPで固定（DNS更新不要）
kuma8088.com.              IN  MX  10  xx.xx.xx.xx.  # Elastic IP
fx-trader-life.com.        IN  MX  10  xx.xx.xx.xx.  # Elastic IP
webmakeprofit.org.         IN  MX  10  xx.xx.xx.xx.  # Elastic IP
webmakesprofit.com.        IN  MX  10  xx.xx.xx.xx.  # Elastic IP
```

**メリット**:
- タスク再起動でもIP不変
- DNS更新不要
- 運用負荷低減

#### 2.2.3 Fargate Public IP取得方法

```bash
# Fargate Task ENIのPublic IP取得
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --region ap-northeast-1 --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster mailserver-cluster --tasks $TASK_ARN --region ap-northeast-1 --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region ap-northeast-1 --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
echo "Fargate Public IP: $PUBLIC_IP"
```

### 2.3 Docker ネットワーク構成（Dell側）

```yaml
ネットワーク名: mailserver_network
タイプ: bridge
サブネット: 172.20.0.0/24
ゲートウェイ: 172.20.0.1
```

**注記**:
- Docker内部ネットワークは変更なし（Tailscale VPN導入による影響なし）
- コンテナ間通信は引き続き172.20.0.0/24ネットワーク内で実施
- Fargate側はawsvpcネットワークモード（172.17.0.0/16デフォルトレンジ）

### 2.4 ポートマッピング（ホスト→コンテナ）

#### 2.4.1 AWS Fargate

| サービス | ホストポート | コンテナポート | プロトコル | 用途 | アクセス元 |
|---------|-------------|---------------|-----------|------|-----------|
| Postfix | 25 | 25 | TCP | SMTP受信 | インターネット直接 (0.0.0.0/0) |
| Tailscale | 41641 | 41641 | UDP | VPN接続 | Tailscale coordination server |

#### 2.4.2 Dell RockyLinux

| サービス | ホストポート | コンテナポート | プロトコル | 用途 | アクセス元 |
|---------|-------------|---------------|-----------|------|-----------|
| Nginx | 80 | 80 | TCP | HTTP (Tailscale HTTPS認証) | Tailscale VPNのみ |
| Nginx | 443 | 443 | TCP | HTTPS (Webmail) | Tailscale VPNのみ |
| Dovecot | 993 | 993 | TCP | IMAPS | Tailscale VPNのみ |
| Dovecot | 995 | 995 | TCP | POP3S | Tailscale VPNのみ |
| Dovecot | 2525 | 2525 | TCP | LMTP (Fargate転送受信) | Tailscale VPNのみ |

**アクセス制御**:
- **Fargate Port 25（SMTP受信）**: インターネット直接公開（0.0.0.0/0、Public IP/Elastic IP）
- **Dell 全ポート**: Tailscale VPN経由でのみアクセス可能（ホストのfirewalldで制御）
- **Fargate → Dell転送**: Tailscale VPN経由Port 2525 LMTP

### 2.5 Tailscale VPN設定

#### 2.5.1 Tailscaleネットワーク設計

**Tailscale VPNの役割**:
- Fargateコンテナ → Dell間のメール転送経路（Port 2525 LMTP over VPN）
- クライアント → Dell間のプライベートアクセス（IMAP/POP3/HTTPS over VPN）
- 自動HTTPS証明書発行（Let's Encrypt/Certbot不要）
- MagicDNSによる自動ホスト名解決
- デバイス認証によるアクセス制御

#### 2.5.2 Tailscaleノード構成

| ノード名 | 役割 | Tailscale IP | MagicDNS |
|---------|------|-------------|----------|
| fargate-mx-1 | Fargate Task 1 | 100.x.x.1 | fargate-mx-1.tail<xxxxx>.ts.net |
| fargate-mx-2 | Fargate Task 2 | 100.x.x.2 | fargate-mx-2.tail<xxxxx>.ts.net |
| mailserver | Dell RockyLinux | 100.x.x.10 | mailserver.tail<xxxxx>.ts.net |
| client-pc | 管理者PC | 100.x.x.20 | client-pc.tail<xxxxx>.ts.net |
| client-iphone | iPhone | 100.x.x.21 | client-iphone.tail<xxxxx>.ts.net |

**注記**:
- Fargateタスクは動的にTailscale IPを取得（Auto Scalingで増減）
- MagicDNSにより、ノード間で名前解決が自動的に行われる

#### 2.5.3 Tailscale ACL（アクセス制御リスト）

**基本設定**（Tailscale管理画面で設定）:
```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:fargate-mx"],
      "dst": ["mailserver:2525"]
    },
    {
      "action": "accept",
      "src": ["autogroup:members"],
      "dst": ["mailserver:993,995,80,443"]
    }
  ],
  "tagOwners": {
    "tag:fargate-mx": ["autogroup:admin"]
  }
}
```

**説明**:
- `tag:fargate-mx`: Fargateタスクに付与するタグ（Tailscale Auth Key生成時に指定）
- `mailserver:2525`: Dell側のLMTPポート（Fargate転送受信専用）
- `autogroup:members`: Tailscaleネットワークに参加している全デバイス（クライアント向け）

#### 2.5.4 Tailscale Auth Key管理

**Fargate用Auth Key**:
- **タイプ**: Reusable, Ephemeral
- **タグ**: `tag:fargate-mx`
- **有効期限**: 90日（定期更新）
- **保管場所**: AWS Secrets Manager
- **シークレット名**: `mailserver/tailscale/fargate-auth-key`

**Dell用Auth Key**:
- **タイプ**: One-time, Persistent
- **タグ**: なし（手動承認）
- **保管場所**: `/opt/mailserver/.env`（権限600）

---

## 3. AWS Fargate コンポーネント詳細設計

### 3.1 ECS Cluster 設計

```yaml
クラスター名: mailserver-cluster
クラスタータイプ: Fargate
コンテナインサイト: 有効
```

### 3.2 ECS Task Definition 設計

```yaml
ファミリー: mailserver-mx-task
ネットワークモード: awsvpc
requiresCompatibilities: FARGATE
CPU: 256 (.25 vCPU)
Memory: 512 MB
タスクロール: mailserver-fargate-task-role
実行ロール: mailserver-fargate-execution-role

コンテナ定義:
  - postfix:
      名前: postfix
      イメージ: postfix:3.8-alpine
      CPU: 128
      Memory: 256
      必須: true
      ポートマッピング:
        - コンテナポート: 25
          プロトコル: tcp
      環境変数:
        - MYHOSTNAME: fargate-mx.kuma8088.com
        - RELAY_HOST: mailserver.tail<xxxxx>.ts.net:2525
        - RELAY_PROTOCOLS: lmtp
      ログ設定:
        logDriver: awslogs
        options:
          awslogs-group: /ecs/mailserver-mx
          awslogs-region: ap-northeast-1
          awslogs-stream-prefix: postfix
      ヘルスチェック:
        command: ["CMD-SHELL", "nc -z localhost 25 || exit 1"]
        interval: 30
        timeout: 5
        retries: 3
        startPeriod: 40

  - tailscale:
      名前: tailscale
      イメージ: tailscale/tailscale:stable
      CPU: 128
      Memory: 256
      必須: true
      ポートマッピング:
        - コンテナポート: 41641
          プロトコル: udp
      環境変数:
        - TS_AUTHKEY: <AWS Secrets Managerから注入>
        - TS_STATE_DIR: /var/lib/tailscale
        - TS_HOSTNAME: fargate-mx-${TASK_ID}
        - TS_USERSPACE: true
      secrets:
        - name: TS_AUTHKEY
          valueFrom: arn:aws:secretsmanager:ap-northeast-1:ACCOUNT_ID:secret:mailserver/tailscale/fargate-auth-key
      マウントポイント:
        - sourceVolume: tailscale-state
          containerPath: /var/lib/tailscale
      ログ設定:
        logDriver: awslogs
        options:
          awslogs-group: /ecs/mailserver-mx
          awslogs-region: ap-northeast-1
          awslogs-stream-prefix: tailscale

ボリューム:
  - name: tailscale-state
    ephemeral: {}
```

### 3.3 ECS Service 設計

```yaml
サービス名: mailserver-mx-service
クラスター: mailserver-cluster
タスク定義: mailserver-mx-task:latest
起動タイプ: FARGATE
プラットフォームバージョン: LATEST

デプロイ設定:
  デプロイメントタイプ: ROLLING_UPDATE
  最小正常パーセント: 100
  最大パーセント: 200

ネットワーク設定:
  VPC: mailserver-vpc
  サブネット:
    - パブリックサブネット1 (10.0.1.0/24)
  セキュリティグループ: fargate-sg
  パブリックIP割り当て: 有効
  Elastic IP: オプション（固定IPが必要な場合）

Auto Scaling:
  最小タスク数: 1
  最大タスク数: 5
  スケーリングポリシー:
    - タイプ: TargetTrackingScaling
      メトリクス: ECSServiceAverageCPUUtilization
      ターゲット値: 70%
      スケールアウトクールダウン: 60秒
      スケールインクールダウン: 300秒
```

### 3.4 IAM Role 設計

#### Task Role (mailserver-fargate-task-role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:ACCOUNT_ID:secret:mailserver/tailscale/fargate-auth-key-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-northeast-1:ACCOUNT_ID:log-group:/ecs/mailserver-mx:*"
    }
  ]
}
```

#### Execution Role (mailserver-fargate-execution-role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-northeast-1:ACCOUNT_ID:log-group:/ecs/mailserver-mx:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:ACCOUNT_ID:secret:mailserver/tailscale/fargate-auth-key-*"
      ]
    }
  ]
}
```

---

## 4. Dell RockyLinux コンポーネント詳細設計

### 4.1 Dovecot (MDA) 設計

#### 主要設定項目

| 設定項目 | 値 | 説明 |
|---------|-----|---------|
| `protocols` | imap pop3 lmtp | 有効プロトコル（LMTP追加） |
| `mail_location` | maildir:/var/mail/vhosts/%d/%n | Maildir形式 |
| `ssl` | required | SSL必須 |
| `ssl_cert` | </var/lib/tailscale/certs/mailserver.tail<xxxxx>.ts.net.crt | SSL証明書 |
| `ssl_key` | </var/lib/tailscale/certs/mailserver.tail<xxxxx>.ts.net.key | SSL秘密鍵 |
| `ssl_min_protocol` | TLSv1.2 | 最低TLSバージョン |
| `auth_mechanisms` | plain login | 認証メカニズム |
| `passdb` | passwd-file /etc/dovecot/users | パスワードDB |
| `userdb` | static uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n | ユーザーDB |

#### サービス設定（LMTP追加）

```
service lmtp {
  inet_listener lmtp {
    port = 2525
    address = *
  }
}

service imap-login {
  inet_listener imap {
    port = 0  # 平文IMAP無効
  }
  inet_listener imaps {
    port = 993
    ssl = yes
  }
}

service pop3-login {
  inet_listener pop3 {
    port = 0  # 平文POP3無効
  }
  inet_listener pop3s {
    port = 995
    ssl = yes
  }
}
```

**重要**: Port 2525はFargateからのLMTP転送受信専用（Tailscale VPN経由）

### 4.2 Postfix (送信専用) 設計

#### 主要設定項目

| 設定項目 | 値 | 説明 |
|---------|-----|---------|
| `myhostname` | mail.kuma8088.com | メールサーバーのFQDN |
| `mydomain` | kuma8088.com | プライマリドメイン |
| `myorigin` | $mydomain | 送信元ドメイン |
| `relayhost` | [smtp.sendgrid.net]:587 | SendGrid SMTP Relay |
| `smtp_sasl_auth_enable` | yes | SMTP認証有効 |
| `smtp_sasl_password_maps` | hash:/etc/postfix/sasl_passwd | SendGrid認証情報 |
| `smtp_sasl_security_options` | noanonymous | 匿名認証無効 |
| `smtp_tls_security_level` | encrypt | TLS必須 |
| `smtp_use_tls` | yes | TLS有効化 |

#### SendGrid認証設定 (sasl_passwd)

```
[smtp.sendgrid.net]:587 apikey:SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**重要**: SendGrid API Keyは`.env`ファイルまたはAWS Secrets Managerで管理

### 4.3 Nginx (Reverse Proxy) 設計

#### 主要設定項目

```nginx
server {
    listen 80;
    server_name mailserver.tail<xxxxx>.ts.net;

    # 常時HTTPSへリダイレクト（Tailscale経由アクセス想定）
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name mailserver.tail<xxxxx>.ts.net;

    # SSL設定（Tailscale HTTPS証明書）
    ssl_certificate /var/lib/tailscale/certs/mailserver.tail<xxxxx>.ts.net.crt;
    ssl_certificate_key /var/lib/tailscale/certs/mailserver.tail<xxxxx>.ts.net.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Roundcubeへプロキシ
    location / {
        proxy_pass http://roundcube:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # タイムアウト設定
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;

        # バッファ設定
        client_max_body_size 25M;
    }
}
```

### 4.4 Roundcube (Webmail) 設計

#### 主要設定項目

| 設定項目 | 値 | 説明 |
|---------|-----|---------|
| `db_dsnw` | mysql://roundcube:password@mariadb/roundcube | DB接続文字列 |
| `default_host` | ssl://dovecot:993 | IMAPサーバー |
| `smtp_server` | tls://postfix:587 | SMTPサーバー（Dell Postfix → SendGrid） |
| `smtp_user` | %u | SMTP認証ユーザー |
| `smtp_pass` | %p | SMTP認証パスワード |
| `support_url` | - | サポートURL（空） |
| `product_name` | Webmail | 製品名 |
| `des_key` | <ランダム生成> | 暗号化キー |
| `plugins` | ['archive', 'zipdownload', 'password'] | 有効プラグイン |
| `language` | ja_JP | デフォルト言語 |
| `timezone` | Asia/Tokyo | タイムゾーン |
| `message_size_limit` | 26214400 | 最大メッセージサイズ (25MB) |

---

## 5. SendGrid SMTP Relay 統合設計

### 5.1 SendGrid設定

#### Domain Authentication (送信ドメイン認証)

**設定手順**:
1. SendGrid管理画面で送信ドメイン登録（kuma8088.com等）
2. SendGridが提供するDNS設定値を取得
3. CloudflareでDNS設定を追加

**DNS設定例**（SendGrid提供値）:
```
# SPFレコード
kuma8088.com. TXT "v=spf1 include:sendgrid.net ~all"

# DKIMレコード（SendGrid生成）
s1._domainkey.kuma8088.com. CNAME s1.domainkey.u12345678.wl.sendgrid.net.
s2._domainkey.kuma8088.com. CNAME s2.domainkey.u12345678.wl.sendgrid.net.

# DMARCレコード
_dmarc.kuma8088.com. TXT "v=DMARC1; p=quarantine; rua=mailto:naoya.iimura@gmail.com"
```

### 5.2 API Key管理

#### API Key生成

**SendGrid管理画面**:
1. Settings → API Keys → Create API Key
2. 権限: "Mail Send" - Full Access
3. API Key名: mailserver-dell-production
4. 生成されたAPI Key: `SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX`

#### API Key保管

**Dell側 (.env)**:
```bash
SENDGRID_API_KEY=SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**AWS Secrets Manager（オプション）**:
```bash
aws secretsmanager create-secret \
  --name mailserver/sendgrid/api-key \
  --secret-string "SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX" \
  --region ap-northeast-1
```

### 5.3 送信量監視

**SendGrid Stats API**:
```bash
curl -X GET "https://api.sendgrid.com/v3/stats?start_date=2025-11-01" \
  -H "Authorization: Bearer SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

**日次送信量アラート設定**:
- SendGrid管理画面で送信量アラート設定（例: 90通/日で警告）
- CloudWatch Alarms連携（将来的）

---

## 6. セキュリティ設計

### 6.1 Secret管理設計

#### 6.1.1 AWS Secrets Manager（Fargate用）

**保管対象**:
- Tailscale Auth Key (Fargate用): `mailserver/tailscale/fargate-auth-key`
- SendGrid API Key (オプション - Level 2管理): `mailserver/sendgrid/api-key`

**Secret入力セキュリティ**:
- ❌ **禁止**: `read -s` での直接入力（シェル履歴にリークリスク）
- ✅ **推奨**: 一時ファイル経由 (`chmod 600`) で読み込み後即座に削除 + 履歴クリア

**アクセス制御**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:ap-northeast-1:ACCOUNT_ID:secret:mailserver/*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalArn": "arn:aws:iam::ACCOUNT_ID:role/mailserver-fargate-task-role"
        }
      }
    }
  ]
}
```

#### 6.1.2 .envファイル管理（Dell用）

```bash
# /opt/mailserver/.env (chmod 600)

# データベース認証情報
MYSQL_ROOT_PASSWORD=<強力なパスワード>
MYSQL_DATABASE=roundcube
MYSQL_USER=roundcube
MYSQL_PASSWORD=<強力なパスワード>

# Roundcube設定
ROUNDCUBE_DES_KEY=<ランダム生成24文字>
ROUNDCUBE_DB_TYPE=mysql
ROUNDCUBE_DB_HOST=mariadb
ROUNDCUBE_DB_NAME=roundcube
ROUNDCUBE_DB_USER=roundcube
ROUNDCUBE_DB_PASSWORD=<強力なパスワード>

# SendGrid SMTP Relay (Level 1: ローカルファイル管理)
# ⚠️ Level 2（Secrets Manager統合）の場合はこの行を削除し、
#    セクション6.1.3の fetch-sendgrid-key.sh を使用
SENDGRID_API_KEY=SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX
SENDGRID_FROM_EMAIL=noreply@kuma8088.com
SENDGRID_FROM_NAME=Kuma Mail Server

# メールサーバー設定
MAIL_DOMAIN=kuma8088.com
MAIL_HOSTNAME=mailserver.tail<xxxxx>.ts.net
MAIL_ADDITIONAL_DOMAINS="fx-trader-life.com webmakeprofit.org webmakesprofit.com"

# 管理者メールアドレス（アラート通知先）
ADMIN_EMAIL=naoya.iimura@gmail.com

# Tailscale設定（Dell用）
TAILSCALE_AUTHKEY=<Dell用Auth Key>
TAILSCALE_HOSTNAME=mailserver
```

#### 6.1.3 SendGrid API Key 管理戦略

**Level 1: 開発環境（ローカルファイル管理）**
- API Key を `.env` ファイルまたは `/opt/mailserver/config/postfix/sasl_passwd` に保存
- パーミッション 600 で保護
- バックアップ時は暗号化必須
- **メリット**: 簡単、追加コストなし
- **デメリット**: ローテーション手動、監査ログなし

**Level 2: 商用環境（AWS Secrets Manager統合 - 推奨）**
- API Key を AWS Secrets Manager に保存
- Dell ホストから AWS CLI で動的取得（`~/fetch-sendgrid-key.sh`）
- 定期的なローテーション機能利用可能
- CloudTrail 監査ログ記録
- **メリット**: セキュリティ高、監査可能、ローテーション自動化可能
- **デメリット**: Secrets Manager 料金（$0.40/月/シークレット）

**取得スクリプト例（Level 2）**:
```bash
#!/bin/bash
# ~/fetch-sendgrid-key.sh
aws secretsmanager get-secret-value \
  --secret-id mailserver/sendgrid/api-key \
  --query 'SecretString' \
  --output text
```

#### 6.1.4 Elastic IP vs Dynamic IP 戦略

**Elastic IP（固定IP - 商用環境推奨）**
- **月額コスト**: $3.60/月
- **メリット**: DNS 変更不要、SPF/MX レコード安定、運用シンプル
- **デメリット**: 追加コスト
- **適用ケース**: 商用環境、手動DNS管理、運用安定性重視

**Dynamic IP（可変IP - 開発環境）**
- **月額コスト**: 無料
- **メリット**: コスト最小化
- **デメリット**: タスク再起動時にDNS更新必要、自動化スクリプト必須
- **適用ケース**: 開発/検証環境、Cloudflare/Route53 API経由DNS更新可能
- **必須対応**: Lambda + CloudWatch Events で DNS A レコード自動更新

### 6.2 SSL/TLS設計

#### 証明書管理

| 項目 | 内容 |
|------|------|
| **証明書発行** | Tailscale HTTPS証明書 |
| **証明書形式** | RSA 2048bit または ECDSA P-256 |
| **更新方法** | Tailscale cert 自動更新（cron実行） |
| **更新頻度** | 日次チェック、必要時更新 |
| **対象ドメイン** | mailserver.tail<xxxxx>.ts.net |
| **SAN** | なし（Tailscale MagicDNS単一ホスト名） |

#### TLS設定基準

| プロトコル | 最小バージョン | 推奨Cipher |
|-----------|---------------|-----------|
| **HTTPS** | TLSv1.2 | HIGH:!aNULL:!MD5 |
| **SMTP (SendGrid)** | TLSv1.2 | HIGH:!aNULL:!MD5 |
| **IMAP/POP3** | TLSv1.2 | HIGH:!aNULL:!MD5 |
| **LMTP (Fargate→Dell)** | Tailscale VPN暗号化 | ChaCha20-Poly1305 |

### 6.3 アクセス制御設計

#### 6.3.1 AWS セキュリティグループ

**fargate-sg (Fargate Tasks)**:
```yaml
Inbound Rules:
  - Protocol: TCP
    Port: 25
    Source: 0.0.0.0/0
    Description: SMTP from Internet (Direct)
  - Protocol: UDP
    Port: 41641
    Source: 0.0.0.0/0
    Description: Tailscale coordination

Outbound Rules:
  - Protocol: All
    Destination: 0.0.0.0/0
```

#### 6.3.2 ファイアウォール（firewalld - Dell側）

```bash
# 許可ポート（Tailscale VPN経由のみ）
firewall-cmd --permanent --add-service=imaps       # Port 993
firewall-cmd --permanent --add-service=pop3s       # Port 995
firewall-cmd --permanent --add-service=http        # Port 80
firewall-cmd --permanent --add-service=https       # Port 443
firewall-cmd --permanent --add-port=2525/tcp       # LMTP (Fargate転送)
firewall-cmd --permanent --add-port=41641/udp      # Tailscale
firewall-cmd --reload
```

**重要**: Dell側はPort 25を公開しない（Fargate側で受信）

---

## 7. データフロー設計

### 7.1 メール受信フロー（インターネット → Fargate → Dell）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 外部メールサーバー → Port 25 → Fargate Public IP        │
│    - DNS MXレコード: xx.xx.xx.xx (Public IP or Elastic IP) │
│    - Fargate直接受信（ALB不要）                             │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Fargate Postfix (Port 25) 受信                          │
│    - Fargateコンテナで受信                                  │
│    - ステートレス（メール保存なし）                          │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Fargate Postfix → Tailscale VPN → Dell Dovecot          │
│    - Tailscale暗号化トンネル経由                            │
│    - LMTP プロトコル（Port 2525）                           │
│    - 宛先: mailserver.tail<xxxxx>.ts.net:2525              │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Dell Dovecot → Rspamd → ClamAV → スパム/ウイルス検知    │
│    - Rspamdでスパムスコアリング                             │
│    - ClamAVでウイルススキャン                               │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Dell Dovecot → メール保存                                │
│    - Maildir形式で保存                                      │
│    - /var/mail/vhosts/kuma8088.com/user/new/                │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 メール送信フロー（クライアント → Dell → SendGrid）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. メールクライアント → Port 587 → Dell Postfix              │
│    - Tailscale VPN経由                                      │
│    - STARTTLS開始                                           │
│    - SASL認証（Dovecot経由）                                │
│    - 宛先: mailserver.tail<xxxxx>.ts.net:587               │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Dell Postfix → SendGrid SMTP Relay                      │
│    - Port 587/TLS認証送信                                   │
│    - API Key認証（PLAIN）                                   │
│    - 宛先: smtp.sendgrid.net:587                            │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SendGrid → SPF/DKIM/DMARC署名付与                        │
│    - SendGrid管理のドメイン認証                             │
│    - 送信レピュテーション管理                                │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SendGrid → 外部メールサーバー                            │
│    - 外部ドメインへ配送                                      │
│    - 送信元: SendGrid IPアドレス                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 WEBメールアクセスフロー（クライアント → Dell）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ブラウザ → Port 443 → Dell Nginx                        │
│    - Tailscale VPN経由                                      │
│    - HTTPS接続（Tailscale証明書）                           │
│    - URL: https://mailserver.tail<xxxxx>.ts.net            │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Dell Nginx → Roundcube (Port 9000)                      │
│    - リバースプロキシ                                        │
│    - リクエスト転送                                          │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Roundcube → Dovecot (Port 993)                          │
│    - IMAP over SSL接続                                      │
│    - メール一覧取得                                          │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Roundcube → MariaDB                                     │
│    - ユーザー設定読込                                        │
│    - キャッシュ保存                                          │
└─────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. メール送信時: Roundcube → Dell Postfix → SendGrid       │
│    - SMTP認証送信（Port 587）                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 監視・運用設計

### 8.1 CloudWatch Logs 設計（Fargate）

#### ロググループ設計

```yaml
ロググループ名: /ecs/mailserver-mx
保存期間: 30日
暗号化: KMS (AES-256)

ログストリーム:
  - postfix/<task-id>
  - tailscale/<task-id>
```

#### ログフィルター設定

**SMTP受信成功**:
```
[postfix] status=sent
```

**SMTP受信エラー**:
```
[postfix] status=deferred OR status=bounced
```

**Tailscale接続エラー**:
```
[tailscale] connection failed OR authentication failed
```

### 8.2 CloudWatch Alarms 設計（Fargate）

#### アラーム設定

| アラーム名 | メトリクス | 閾値 | 期間 | アクション |
|----------|----------|------|------|----------|
| FargateHighCPU | CPUUtilization | > 80% | 10分 | SNS通知 |
| FargateHighMemory | MemoryUtilization | > 80% | 10分 | SNS通知 |
| FargateTaskFailure | TaskCount | = 0 | 1分 | SNS通知 + Auto Scaling |
| FargateTaskCrashed | TaskStopped (Reason: Error) | >= 1 | 5分 | SNS通知 |

### 8.3 ヘルスチェック設計

#### 8.3.1 Fargateヘルスチェック

**ECS Task Health Check**:
```yaml
コマンド: ["CMD-SHELL", "nc -z localhost 25 || exit 1"]
間隔: 30秒
タイムアウト: 5秒
再試行回数: 3
開始猶予期間: 40秒
```

#### 8.3.2 Dellヘルスチェック

**Dockerコンテナヘルスチェック**:
```yaml
# Dovecot
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "993"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Nginx
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Postfix
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "587"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Rspamd
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:11334/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# ClamAV
healthcheck:
  test: ["CMD", "/usr/local/bin/clamdcheck.sh"]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 120s

# MariaDB
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 8.4 アラート通知設計

#### 通知対象イベント

| イベント | 重要度 | 通知先 | 通知方法 |
|---------|--------|--------|----------|
| Fargateタスク異常停止 | 🔴 高 | 管理者メール | 即時 (SNS) |
| コンテナヘルスチェック失敗（Dell） | 🔴 高 | 管理者メール | 即時 |
| ディスク容量90%超過（Dell） | 🟡 中 | 管理者メール | 日次 |
| SSL証明書期限30日以内 | 🟡 中 | 管理者メール | 週次 |
| ウイルス検知 | 🔴 高 | 管理者メール | 即時 |
| スパム大量検知（100通/時） | 🟡 中 | 管理者メール | 1時間ごと |
| SendGrid送信量90%超過 | 🟡 中 | 管理者メール | 日次 |

#### SNS Topic設定（AWS）

```yaml
トピック名: mailserver-alerts
サブスクリプション:
  - プロトコル: Email
    エンドポイント: naoya.iimura@gmail.com
```

---

## 9. バックアップ・リカバリ設計

### 9.1 バックアップ対象

| 対象 | パス | 重要度 | 頻度 | 保管先 |
|------|------|--------|------|--------|
| **メールデータ** | /opt/mailserver/data/mail/ | 🔴 最高 | 日次 | Dell + 外部HDD |
| **データベース** | /opt/mailserver/data/db/ | 🔴 最高 | 日次 | Dell + 外部HDD |
| **設定ファイル** | /opt/mailserver/config/ | 🟡 高 | 週次 | Dell + 外部HDD |
| **Tailscale証明書** | /var/lib/tailscale/certs/ | 🟡 高 | 週次 | Dell + 外部HDD |
| **Fargate設定** | ECS Task Definition JSON | 🟡 高 | 変更時 | Git リポジトリ |
| **AWS設定** | Terraform/CloudFormation | 🟡 高 | 変更時 | Git リポジトリ |

**注記**:
- Fargate側はステートレス設計のためバックアップ不要
- Dell側のみデータバックアップを実施
- AWS設定はInfrastructure as Code（IaC）で管理

### 9.2 バックアップ方式

#### 日次バックアップ（Dell側）

```bash
#!/bin/bash
# /opt/mailserver/scripts/backup.sh

BACKUP_DIR="/mnt/backup/mailserver"
DATE=$(date +%Y%m%d)

# メールデータバックアップ
tar -czf $BACKUP_DIR/mail_$DATE.tar.gz /opt/mailserver/data/mail/

# データベースバックアップ
docker exec mailserver-mariadb mysqldump -u root -p$MYSQL_ROOT_PASSWORD roundcube > $BACKUP_DIR/db_$DATE.sql

# Tailscale証明書バックアップ
tar -czf $BACKUP_DIR/tailscale_certs_$DATE.tar.gz /var/lib/tailscale/certs/

# 7日以上前のバックアップ削除
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

#### cron設定

```bash
# 毎日深夜3:00にバックアップ実行
0 3 * * * /opt/mailserver/scripts/backup.sh >> /opt/mailserver/logs/backup.log 2>&1
```

---

## 10. ディレクトリ構造設計

### 10.1 Dell側プロジェクトディレクトリ構造

```
/opt/mailserver/
├── docker-compose.yml              # Docker Compose設定ファイル
├── .env                            # 環境変数設定ファイル（chmod 600）
├── README.md                       # プロジェクトREADME
│
├── config/                         # 設定ファイルディレクトリ
│   ├── postfix/
│   │   ├── main.cf                 # Postfix主設定（SendGrid Relay設定）
│   │   ├── master.cf               # Postfixサービス設定
│   │   └── sasl_passwd             # SendGrid認証情報
│   │
│   ├── dovecot/
│   │   ├── dovecot.conf            # Dovecotメイン設定
│   │   ├── 10-auth.conf            # 認証設定
│   │   ├── 10-mail.conf            # メールストレージ設定
│   │   ├── 10-master.conf          # サービス設定（LMTP追加）
│   │   ├── 10-ssl.conf             # SSL設定
│   │   └── users                   # ユーザーファイル（passwd形式）
│   │
│   ├── nginx/
│   │   ├── nginx.conf              # Nginxメイン設定
│   │   └── conf.d/
│   │       └── mailserver.conf     # Webmail用設定
│   │
│   └── roundcube/
│       ├── config.inc.php          # Roundcube設定
│       └── plugins/                # プラグイン設定
│
├── data/                           # 永続化データディレクトリ
│   ├── mail/                       # メールデータ（Maildir形式）
│   ├── db/                         # MariaDBデータ
│   └── certs/                      # Tailscale証明書
│
├── logs/                           # ログディレクトリ
│   ├── postfix/
│   ├── dovecot/
│   ├── nginx/
│   └── roundcube/
│
└── scripts/                        # 管理スクリプト
    ├── add-user.sh                 # ユーザー追加
    ├── add-domain.sh               # ドメイン追加
    ├── backup.sh                   # バックアップ
    └── health-monitor.sh           # ヘルスチェック監視
```

### 10.2 AWS Fargate設定ディレクトリ構造（IaC管理）

```
/opt/mailserver-infra/
├── terraform/                      # Terraform設定
│   ├── main.tf                     # メイン設定
│   ├── vpc.tf                      # VPC設定
│   ├── alb.tf                      # ALB設定
│   ├── ecs.tf                      # ECS Cluster/Service/Task設定
│   ├── iam.tf                      # IAMロール設定
│   ├── cloudwatch.tf               # CloudWatch Logs/Alarms設定
│   ├── secrets.tf                  # Secrets Manager設定
│   └── variables.tf                # 変数定義
│
└── task-definitions/               # ECS Task Definition JSON
    └── mailserver-mx-task.json     # Fargateタスク定義
```

---

## 11. トラブルシューティング設計

### 11.1 一般的な問題と対処

| 問題 | 原因 | 対処方法 |
|------|------|----------|
| メール受信できない（Fargate） | Fargateタスクヘルスチェック失敗 | CloudWatch Logs確認、Fargateタスク再起動 |
| MXレコード解決失敗 | Public IP変更（動的IP使用時） | Fargate Public IP取得 → DNS更新 |
| メール送信できない（Dell） | SendGrid認証エラー | API Key確認、sasl_passwd設定確認 |
| Fargate → Dell転送失敗 | Tailscale VPN接続断 | Tailscale状態確認、Dell側Tailscaleサービス再起動 |
| SSL証明書エラー | Tailscale証明書期限切れ | `tailscale cert`再実行 + サービス再起動 |
| WEBメールアクセス不可 | Nginx/Roundcube停止 | docker-compose ps確認、再起動 |
| SendGrid送信量超過 | 日次上限到達 | SendGrid管理画面で送信量確認、プランアップグレード |

### 11.2 診断コマンド

#### Fargate診断

```bash
# ECS Service状態確認
aws ecs describe-services \
  --cluster mailserver-cluster \
  --services mailserver-mx-service \
  --region ap-northeast-1

# Fargateタスク状態確認
aws ecs list-tasks \
  --cluster mailserver-cluster \
  --service-name mailserver-mx-service \
  --region ap-northeast-1

# CloudWatch Logs確認
aws logs tail /ecs/mailserver-mx --follow --region ap-northeast-1

# Fargate Public IP取得
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --region ap-northeast-1 --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster mailserver-cluster --tasks $TASK_ARN --region ap-northeast-1 --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region ap-northeast-1 --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
echo "Fargate Public IP: $PUBLIC_IP"
```

#### Dell診断

```bash
# コンテナ状態確認
docker-compose ps

# ログ確認
docker-compose logs --tail=100 dovecot
docker-compose logs --tail=100 postfix
docker-compose logs --tail=100 rspamd

# Tailscale状態確認
tailscale status
tailscale ping fargate-mx-1.tail<xxxxx>.ts.net

# ポート確認
netstat -tuln | grep -E '993|995|2525|80|443|587'

# DNS確認（MXレコード）
dig MX kuma8088.com
# 期待値: xx.xx.xx.xx (Fargate Public IP or Elastic IP)

# SendGrid接続テスト
openssl s_client -connect smtp.sendgrid.net:587 -starttls smtp
```

---

## 12. 承認

| 役割 | 氏名 | 承認日 | 署名 |
|------|------|--------|------|
| 設計者 | Claude (devops-architect) | 2025-11-01 | ✓ |
| レビュアー | - | - | - |
| 承認者 | プロジェクトオーナー | 2025-11-01 | ✓ |

---

**文書改訂履歴**

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|----------|--------|
| 1.0 | 2025-10-31 | 初版作成 | Claude |
| 2.0 | 2025-10-31 | 要件定義v2.1対応 | Claude |
| 3.0 | 2025-11-01 | Tailscale VPN前提への全面改訂 | Claude |
| 3.1 | 2025-11-01 | 外部SMTPリレー前提へドキュメント整合 | Codex |
| 5.0 | 2025-11-01 | サーバーレス化改訂（AWS Fargate + Dell + SendGrid + Tailscale VPN） | Claude (devops-architect) |
| 5.1 | 2025-11-02 | **ALB削除・Public IP直接受信化・東京リージョン化** | Claude (devops-architect) |

**v5.1 主要変更点（v5.0からの改訂）:**
- **ALB削除**: Application Load Balancer削除、コスト削減（~$16.20/月削減）
- **Public IP直接受信**: Fargate Public IP/Elastic IPでPort 25直接受信
- **東京リージョン化**: ap-northeast-1 → ap-northeast-1（低レイテンシー、日本語サポート）
- **DNS設計変更**: MXレコードでFargate Public IP/Elastic IP直接指定
- **Elastic IP推奨**: 固定IP（+$3.60/月）でタスク再起動時のDNS更新不要
- **セキュリティグループ簡素化**: alb-sg削除、fargate-sgのみ（Port 25直接公開）
- **Auto Scaling変更**: ALBRequestCountPerTarget → ECSServiceAverageCPUUtilization
- **コスト最適化**: v5.1総コスト ~$7-14/月（Public IP）、~$11-18/月（Elastic IP）
- **運用簡素化**: ALB管理不要、DNSのみ管理（Elastic IP推奨）

**v5.0 主要変更点（v3.1からの改訂）:**
- AWS Fargate MXゲートウェイ導入（EC2不要のサーバーレス設計）
- SendGrid SMTP Relay統合（外部送信専用、SPF/DKIM/DMARC自動管理）
- ハイブリッドアーキテクチャ設計（Fargate受信 + Dell保管 + SendGrid送信）
- AWS Secrets Manager統合（認証情報の安全な保管）
- CloudWatch Logs/Alarms追加（リアルタイム監視・アラート）
- Tailscale VPN拡張（Fargate ↔ Dell間LMTP転送）
- Dovecot LMTP追加（Port 2525/TCP）
- Dell Postfix送信専用化（SendGrid Relay経由のみ）
