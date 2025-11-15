# On-Premise Infrastructure System

**ハイブリッドクラウドメールサーバーインフラプロジェクト**

エンタープライズグレードのメールサーバーシステムを、オンプレミス環境とAWSを組み合わせたハイブリッド構成で実装。TDD開発手法とIaCを採用し、セキュリティとディザスタリカバリを重視した本格的なインフラ構築プロジェクト。

[![Infrastructure](https://img.shields.io/badge/Infrastructure-Hybrid_Cloud-blue)](docs/infra/README.md)
[![Mailserver](https://img.shields.io/badge/Mailserver-Production_Ready-green)](docs/application/mailserver/README.md)
[![Blog System](https://img.shields.io/badge/Blog-Phase_A--1_Complete-blue)](docs/application/blog/README.md)
[![TDD](https://img.shields.io/badge/Development-TDD-brightgreen)](docs/application/mailserver/backup/03_implementation.md)
[![IaC](https://img.shields.io/badge/IaC-Terraform-purple)](services/mailserver/terraform/main.tf)

---

## 📋 プロジェクト概要

### 🎯 目的

**Mailserver**: Xserver WEBメール相当の機能を持つメールサーバーを、オンプレミス環境（Dell WorkStation）とCloudflareを組み合わせたハイブリッドクラウド構成で構築。実運用を想定したセキュリティ、バックアップ、監視、復旧手順を完備。EC2 MX Gateway廃止により月額¥525削減（2025-11-12）。

**Blog System**: Xserver上の16 WordPressサイト（95GB）をDell WorkStation + Cloudflare Tunnelへ移植。コスト削減とデータ主権確保を実現。本番ドメイン移行完了（Phase A-2、2025-11-12）。

**Unified Portal**: Blog SystemとMailserverを統一管理するXserver風Webポータル。Cloudflare DNS API統合、Redis Object Cache統合完了（Phase 1実装中、2025-11-13）。

### 🏗️ アーキテクチャ概要

```
┌────────────────────────────────────────────────────────────────────┐
│                        Internet                                     │
└───────┬──────────────────────────────────┬─────────────────────────┘
        │                                  │
        │ MX (Port 25)                     │ HTTPS/Blog Access
        ▼                                  ▼
┌────────────────────┐           ┌────────────────────┐
│ Cloudflare Edge    │           │  Cloudflare Edge   │
│ - Email Routing    │           │  - SSL/TLS Auto    │
│ - Email Worker     │           │  - DDoS Protection │
│   (Serverless JS)  │           │  - CDN             │
└─────────┬──────────┘           └─────────┬──────────┘
          │ HTTPS POST                     │ Tunnel (outbound only)
          │ (via Tunnel)                   │
          ▼                                ▼
┌───────────────────────────────────────────────────────────────────┐
│   Dell WorkStation (Rocky Linux 9.6)                              │
│   Multi-Service Docker Compose Environment                        │
│                                                                    │
│   ┌─── Mailserver (9 Containers) ────────────────────────┐       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│   │  │ Postfix  │  │ Dovecot  │  │ MariaDB  │          │       │
│   │  │(SendGrid)│  │(IMAP/POP)│  │(User/RC) │          │       │
│   │  └──────────┘  └──────────┘  └──────────┘          │       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│   │  │  ClamAV  │  │  Rspamd  │  │Roundcube │          │       │
│   │  └──────────┘  └──────────┘  └──────────┘          │       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│   │  │UserMgmt  │  │  Nginx   │  │ Mail API │←─ ✅ Email Worker  │
│   │  │ (Flask)  │  │          │  │(FastAPI) │   転送先   │       │
│   │  └──────────┘  └──────────┘  └──────────┘          │       │
│   └────────────────────────────────────────────────────┘       │
│                                                                    │
│   ┌─── Blog System (5 Containers) ───────────────────────┐       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│   │  │WordPress │  │  Nginx   │  │ MariaDB  │          │       │
│   │  │ (PHP-FPM)│  │ (Proxy)  │  │ (16 DBs) │          │       │
│   │  └──────────┘  └──────────┘  └──────────┘          │       │
│   │  ┌──────────┐  ┌──────────┐                        │       │
│   │  │cloudflared│  │  Redis   │ ←─ ✅ Object Cache    │       │
│   │  └──────────┘  └──────────┘                        │       │
│   │  (16 WordPress Sites via 5 Domains)                │       │
│   └────────────────────────────────────────────────────┘       │
│                                                                    │
│   ┌─── Unified Portal (Dev) ─────────────────────────────┐       │
│   │  ┌──────────┐  ┌──────────┐                        │       │
│   │  │ FastAPI  │  │  React   │ ←─ 🔄 Phase 1実装中    │       │
│   │  │(Backend) │  │(Frontend)│   (Xserver風UI)       │       │
│   │  └──────────┘  └──────────┘                        │       │
│   │  (Cloudflare DNS API統合完了 ✅)                   │       │
│   └────────────────────────────────────────────────────┘       │
│                                                                    │
│   Storage: SSD 50GB (DBs/Logs) + HDD 3.6TB (Mail/Blog/Backups)  │
└────────────┬───────────────────────────────────────────┬─────────┘
             │                                           │
             ▼                                           ▼
   ┌────────────────────┐                  ┌────────────────────┐
   │  Local Backup      │                  │   AWS S3 Backup    │
   │  /mnt/backup-hdd   │                  │  (Object Lock +    │
   │  - Mailserver      │                  │   ClamAV Scan)     │
   │  - Blog (予定)     │                  │  - Versioning      │
   │  - Daily/Weekly    │                  │  - CloudWatch      │
   └────────────────────┘                  └────────────────────┘

**注記**:
- ✅ EC2 MX Gateway: 廃止済み（2025-11-12）
- ✅ Tailscale VPN: 不要に（Cloudflare Tunnel経由で通信）
- ✅ Email Worker: サーバーレス化により月額¥525→¥0削減
```

---

## 🚀 技術スタック

### **Infrastructure & Orchestration**

| 技術 | バージョン | 用途 |
|------|-----------|------|
| **Rocky Linux** | 9.6 | ホストOS（RHEL互換） |
| **Docker** | 24.x | コンテナ実行基盤 |
| **Docker Compose** | 2.x | マルチコンテナオーケストレーション |
| **Terraform** | 1.x | IaC (AWS S3, IAM, CloudWatch) |
| **KVM/QEMU** | 9.0 | 仮想化基盤（構築済み、将来使用） |
| **Tailscale** | - | ❌ **廃止済み**（2025-11-12、Cloudflare Tunnel経由で通信） |

### **Mail Server Stack**

| コンポーネント | 技術 | バージョン | 役割 |
|----------------|------|-----------|------|
| **MTA** | Postfix | 3.x | SMTP送信（SendGrid Relay） |
| **MDA** | Dovecot | 2.3.21 | IMAP/POP3受信、LMTP配送 |
| **Database** | MariaDB | 10.11.7 | ユーザー管理、Roundcube |
| **Webmail** | Roundcube | 1.6.7 | ブラウザメールクライアント |
| **AntiVirus** | ClamAV | 1.3+ | ウイルススキャン（8.7M signatures） |
| **Spam Filter** | Rspamd | 3.8 | スパムフィルタ・学習 |
| **Reverse Proxy** | Nginx | 1.26 | HTTPS終端、Tailscale証明書 |
| **User Management** | Flask + Python | 3.11 | ユーザー管理WebAPI（Phase 11） |

### **Blog System Stack**

| コンポーネント | 技術 | バージョン | 役割 |
|----------------|------|-----------|------|
| **CMS** | WordPress | 6.x | 16サイト運用 |
| **Web Server** | Nginx | 1.26 | リバースプロキシ、5仮想ホスト |
| **Application** | PHP-FPM | 8.x | WordPress実行環境 |
| **Database** | MariaDB | 10.11 | 16データベース |
| **Tunnel** | Cloudflared | Latest | Cloudflare Tunnel (5 Public Hostnames) |
| **Cache** | Redis | 7.x | Object Cache（WordPress高速化） ✅ |

### **Unified Portal Stack** 🆕

| コンポーネント | 技術 | バージョン | 役割 |
|----------------|------|-----------|------|
| **Backend** | FastAPI | 0.109+ | REST API（Python 3.9+） |
| **Frontend** | React | 18 | SPA（TypeScript + Vite） |
| **UI Framework** | Tailwind CSS + shadcn/ui | 3.x | Xserver風デザインシステム |
| **State Management** | Zustand + TanStack Query | Latest | 状態管理・データフェッチング |
| **Database** | SQLite/PostgreSQL | - | ポータルメタデータ |
| **External APIs** | Cloudflare API, Docker API, WordPress API | - | 統合管理 |

### **Cloud Infrastructure**

| サービス | プロバイダ | 用途 | 実装 |
|---------|-----------|------|------|
| **Email Routing** | Cloudflare | MX受信 (無料) | ✅ Email Worker連携（2025-11-12運用開始） |
| **Email Worker** | Cloudflare | サーバーレスメール処理 (無料) | ✅ FastAPI転送（EC2廃止、¥525/月削減） |
| **Cloudflare Tunnel** | Cloudflare | セキュアな公開 (無料) | ✅ Blog + Mail API |
| **S3** | AWS | オフサイトバックアップ (Object Lock) | ✅ 日次レプリケーション |
| **IAM** | AWS | 最小権限ロール (Uploader/Admin) | ✅ Terraform管理 |
| **CloudWatch** | AWS | コスト監視 (10円/100円閾値) | ✅ SNS通知連携 |
| **EC2** | AWS | MX Gateway | ❌ **廃止済み**（2025-11-12） |

### **Development & Testing**

| 技術 | 用途 | 実装規模 |
|------|------|---------|
| **TDD** | Test-Driven Development | 38 tests (Phase 10 Backup) |
| **pytest** | Python Testing Framework | usermgmt + backup scripts |
| **Bash Testing** | Shell Script Testing | backup/restore validation |
| **Git** | Version Control | Gitea (self-hosted) |

### **Security & Compliance**

| 技術/手法 | 実装内容 |
|-----------|---------|
| **SPF/DKIM/DMARC** | メール認証・なりすまし防止 |
| **SSL/TLS** | Tailscale自動証明書 (全プロトコル暗号化) |
| **Object Lock (COMPLIANCE)** | S3ランサムウェア対策 (30日間削除不可) |
| **ClamAV + rkhunter** | 3層マルウェア防御 (日次/週次スキャン) |
| **IAM Least Privilege** | 最小権限原則 (daily/* prefix制限) |
| **Firewall** | RX-600KI設定、非標準SSHポート |

---

## 💡 プロジェクトの特徴・アピールポイント

### 1. **ハイブリッドクラウド構成**
- オンプレミス（Dell）とクラウド（Cloudflare + AWS）の組み合わせ
- Cloudflare Email Worker（サーバーレスMX受信）+ Cloudflare Tunnel（セキュア公開）
- SendGrid SMTP Relayによる配信信頼性向上
- **EC2 MX Gateway廃止により月額¥525削減**（2025-11-12完了）
- **Tailscale VPN不要化**（Cloudflare Tunnel経由で通信）

### 2. **TDD（テスト駆動開発）の実践**
- **38 tests implemented** (Phase 10 Backup System)
- pytest + Bash testing framework
- 実装前にテストケース設計→実装→検証のサイクル

### 3. **Infrastructure as Code (IaC)**
```
services/mailserver/terraform/
├── main.tf           # AWS EC2, S3, IAM, CloudWatch
├── variables.tf      # 環境変数定義
├── outputs.tf        # Output values
└── locals.tf         # Local variables
```
- **再現可能なインフラ**: `terraform apply` で即座に復元
- **環境分離**: production/staging workspace
- **State管理**: S3バックエンド

### 4. **セキュリティ重視設計**

**ランサムウェア対策**:
```terraform
resource "aws_s3_bucket_object_lock_configuration" "backup_lock" {
  rule {
    default_retention {
      mode = "COMPLIANCE"  # 30日間削除不可
      days = 30
    }
  }
}
```

**マルウェアスキャン（3層防御)**:
- **Layer 1**: メール受信時スキャン（ClamAV @ Dell）
- **Layer 2**: バックアップ前スキャン（日次/週次）
- **Layer 3**: リストア前スキャン（S3 → Dell復旧時）

### 5. **本格的なバックアップ戦略**

**3-2-1 Backup Rule準拠**:
- **3 copies**: Production + Local HDD + S3
- **2 media types**: HDD + Cloud Storage
- **1 offsite**: AWS S3 (Tokyo ap-northeast-1)

**自動化**:
```cron
0 3 * * *   backup-mailserver.sh --daily   # ローカル日次
0 4 * * 0   backup-mailserver.sh --weekly  # ローカル週次
0 4 * * *   backup-to-s3.sh                # S3日次アップロード
0 5 * * *   scan-mailserver.sh --daily     # マルウェア日次スキャン
0 6 * * 0   scan-mailserver.sh --weekly    # マルウェア週次スキャン
```

### 6. **ディザスタリカバリ対応**

**RPO/RTO設計**:
| シナリオ | RPO | RTO | 手順 |
|---------|-----|-----|------|
| **GitHub復旧** | 0 (IaC) | 2h | Terraform apply |
| **S3データ復旧** | 24h | 1h | restore-mailserver.sh |
| **完全障害** | 24h | 4h | GitHub + S3 full restore |
| **部分復旧** | 24h | 30m | Component-specific restore |

### 7. **コスト最適化**

**月額想定コスト** (円建て):
```
【Cloudflare（完全無料）】
  Email Routing:           $0/月  (完全無料)
  Email Worker:            $0/月  (無料枠内: 10万リクエスト/日)
  Cloudflare Tunnel:       $0/月  (完全無料)

【AWS】
  S3 STANDARD:             ~$0.025/GB/月 (≈3.5円/GB)
  CloudWatch Logs:         ~$0.50/月  (≈70円)
  SNS:                     Free tier

Total:                     ~$1/月 (≈140円)
```

**コスト削減実績**:
- ✅ **EC2廃止により月額¥525 → ¥0**（2025-11-12完了）
  - Before: EC2 t3.nano (¥525/月) + Tailscale VPN
  - After: Cloudflare Email Worker (¥0/月) + Cloudflare Tunnel (¥0/月)
- ✅ **Tailscale VPN不要化**（管理コスト削減）
- ✅ **サーバーレス化により保守作業削減**（OS更新・セキュリティパッチ不要）
- ✅ **Xserver解約**（16サイト分、月額費用削減 - Phase A-1/A-2完了）

**コスト監視**:
- CloudWatch Alarms: 10円 (WARNING) / 100円 (CRITICAL)
- SNS Email通知
- 自動ライフサイクル管理: 30d STANDARD → 60d GLACIER → 90d DELETE

### 8. **ドキュメント駆動型開発**

**完全なドキュメント体系**:
```
docs/
├── infra/
│   ├── 01_requirements.md     # インフラ要件
│   ├── 02_design.md           # システム設計
│   └── procedures/            # 手順書（Phase 2-3）
└── application/mailserver/
    ├── 01_requirements.md     # Mailserver要件
    ├── 02_design.md           # Mailserver設計
    ├── 03_installation.md     # 構築手順
    ├── 04_testing.md          # テスト手順
    └── backup/
        ├── 03_implementation.md  # Phase 10実装
        ├── 05_s3backup_requirements.md  # Phase 11-B要件
        ├── 06_s3backup_design.md        # Phase 11-B設計
        ├── 07_s3backup_implementation.md # Phase 11-B実装
        └── 08_recovery_procedures.md    # リカバリー手順
```

### 9. **実運用想定の設計**

**ログ管理**:
```bash
logs/
├── postfix/      # SMTP送信ログ
├── dovecot/      # IMAP/POP3ログ
├── nginx/        # HTTPS access/error logs
├── clamav/       # ウイルススキャンログ
└── rspamd/       # スパムフィルタログ

# Centralized backup logs
~/.mailserver-backup.log         # メインログ
~/.mailserver-backup-error.log   # エラーログ
~/.s3-backup-cron.log            # S3アップロードログ
~/.scan-cron.log                 # マルウェアスキャンログ
```

**監視・アラート**:
- Dockerコンテナヘルスチェック
- ディスク容量監視（80%閾値）
- S3コスト監視（CloudWatch + SNS）
- マルウェア検出時即座通知

### 10. **Unified Portal - 統合管理ポータル** 🆕

**コンセプト**: Xserver風の直感的なUIで複数システムを一元管理

**技術選定**:
- **Backend**: FastAPI（高速、型安全、自動ドキュメント生成）
- **Frontend**: React 18 + TypeScript + Vite（モダンSPA）
- **UI**: Tailwind CSS + shadcn/ui（Xserver風デザインシステム）
- **State**: Zustand + TanStack Query（効率的な状態管理）

**実装済み機能** ✅:
- **Cloudflare DNS API統合**（ゾーン管理、DNSレコードCRUD、プロキシ設定）
- **Redis Object Cache統合**（WordPress高速化）
- **8つの管理ページUI**（Dashboard, Docker, Database, PHP, Security, WordPress, Domain, Backup）

**開発中機能** 🔄:
- Docker API統合（コンテナ管理）
- WordPress REST API統合（サイト管理）
- 認証システム（JWT）
- WebSocket（リアルタイム更新）

**設計思想**:
- API First（OpenAPI仕様準拠）
- 段階的実装（Phase 1: UI基盤 → Phase 4: 本番デプロイ）
- セキュリティ重視（認証・認可・CORS設定）
- ドキュメント完備（ARCHITECTURE.md, LOCAL_DEVELOPMENT.md等）

**参照**: [docs/application/unified-portal/README.md](docs/application/unified-portal/README.md)

---

## 📂 プロジェクト構成

```
/opt/onprem-infra-system/project-root-infra/
├── docs/                                   # ドキュメント
│   ├── infra/                              # インフラドキュメント
│   │   ├── README.md                       # インフラ概要
│   │   ├── 01_requirements.md              # インフラ要件
│   │   ├── 02_design.md                    # インフラ設計
│   │   └── procedures/                     # Phase別手順書
│   │       ├── 2-kvm/                      # KVM環境構築（完了、未使用）
│   │       └── 3-docker/                   # Docker環境構築
│   ├── application/mailserver/             # Mailserverドキュメント
│   │   ├── README.md                       # Mailserver概要
│   │   ├── 01_requirements.md              # 要件定義
│   │   ├── 02_design.md                    # 設計書
│   │   ├── 03_installation.md              # 構築手順
│   │   ├── 04_testing.md                   # テスト手順
│   │   ├── backup/                         # バックアップドキュメント
│   │   │   ├── 03_implementation.md        # Phase 10実装
│   │   │   ├── 05_s3backup_requirements.md # Phase 11-B要件
│   │   │   ├── 06_s3backup_design.md       # Phase 11-B設計
│   │   │   ├── 07_s3backup_implementation.md # Phase 11-B実装
│   │   │   └── 08_recovery_procedures.md   # リカバリー手順
│   │   ├── usermgmt/                       # User Management (Phase 11)
│   │   │   ├── README.md                   # Phase 11概要
│   │   │   ├── DEVELOPMENT.md              # 開発手順
│   │   │   └── TESTING.md                  # テスト手順
│   │   └── device/                         # デバイス手順書
│   └── application/blog/                   # Blog Systemドキュメント ✅ NEW
│       ├── README.md                       # Blog概要
│       ├── 01_requirements.md              # 要件定義
│       ├── 02_design.md                    # 設計書
│       ├── 03_installation.md              # 構築手順
│       ├── 04_migration.md                 # Xserver移行手順
│       ├── phase-a1-bulk-migration.md      # Phase A-1実装
│       └── cloudflare-tunnel-hostnames.md  # Cloudflare設定
├── services/mailserver/                    # Mailserver実装
│   ├── docker-compose.yml                  # マルチコンテナ定義
│   ├── .env                                # 環境変数（機密情報）
│   ├── config/                             # 設定ファイル
│   │   ├── postfix/                        # Postfix設定
│   │   ├── dovecot/                        # Dovecot設定
│   │   ├── nginx/                          # Nginx設定
│   │   ├── roundcube/                      # Roundcube設定
│   │   ├── rspamd/                         # Rspamd設定
│   │   └── clamav/                         # ClamAV設定
│   ├── data/                               # データ永続化
│   │   ├── mail/                           # メールボックス
│   │   ├── db/                             # MariaDB
│   │   └── rspamd/                         # Rspamd学習データ
│   ├── logs/                               # ログファイル
│   ├── scripts/                            # 運用スクリプト
│   │   ├── backup-config.sh                # バックアップ設定
│   │   ├── backup-mailserver.sh            # ローカルバックアップ
│   │   ├── backup-to-s3.sh                 # S3アップロード
│   │   ├── scan-mailserver.sh              # マルウェアスキャン
│   │   ├── restore-mailserver.sh           # リストア
│   │   └── sync-sendgrid-sasl.sh           # SendGrid設定
│   ├── terraform/                          # Terraform IaC
│   │   ├── main.tf                         # EC2, VPC, Security Group
│   │   ├── variables.tf                    # 変数定義
│   │   ├── outputs.tf                      # Output values
│   │   └── locals.tf                       # Local variables
│   ├── terraform-backup-s3/                # S3 Backup Terraform
│   │   ├── main.tf                         # S3, IAM, CloudWatch
│   │   ├── variables.tf                    # 変数定義
│   │   └── outputs.tf                      # Output values
│   ├── usermgmt/                           # User Management App
│   │   ├── app.py                          # Flask application
│   │   ├── app/                            # Application modules
│   │   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── routes/                     # Flask routes
│   │   │   └── services/                   # Business logic
│   │   ├── tests/                          # pytest tests
│   │   ├── Dockerfile                      # Container definition
│   │   └── requirements.txt                # Python dependencies
│   └── troubleshoot/                       # トラブルシューティング
├── services/blog/                          # Blog System実装 ✅
│   ├── docker-compose.yml                  # マルチコンテナ定義（5コンテナ）
│   ├── .env                                # 環境変数（機密情報）
│   ├── config/                             # 設定ファイル
│   │   ├── nginx/conf.d/                   # Nginx設定（5仮想ホスト）
│   │   ├── wordpress/                      # PHP設定、WP Mail SMTP設定
│   │   ├── mariadb/init/                   # MariaDB設定（16 DBs）
│   │   └── cloudflared/                    # Cloudflare Tunnel設定
│   └── scripts/                            # 運用スクリプト ✨
│       ├── create-new-wp-site.sh           # 新規サイト作成ウィザード
│       ├── setup-wp-mail-smtp.sh           # WP Mail SMTP一括設定
│       ├── check-wp-mail-smtp.sh           # SMTP設定確認
│       ├── generate-nginx-subdirectories.sh # Nginx設定生成
│       ├── setup-redis-object-cache.sh     # Redis Object Cache設定
│       └── test-redis-performance.sh       # Redis性能テスト
├── services/unified-portal/                # Unified Portal実装 🆕
│   ├── backend/                            # FastAPI バックエンド
│   │   ├── app/
│   │   │   ├── routers/                    # APIルーター
│   │   │   │   └── domains.py              # Cloudflare DNS API ✅
│   │   │   ├── config.py                   # 設定管理
│   │   │   ├── database.py                 # SQLAlchemy ORM
│   │   │   └── main.py                     # エントリーポイント
│   │   └── requirements.txt                # Python依存関係
│   ├── frontend/                           # React フロントエンド
│   │   ├── src/
│   │   │   ├── components/                 # UIコンポーネント（shadcn/ui）
│   │   │   ├── pages/                      # 8管理ページ
│   │   │   │   ├── DomainManagement.tsx    # Cloudflare DNS統合 ✅
│   │   │   │   └── ...                     # その他7ページ
│   │   │   └── lib/                        # API クライアント、ユーティリティ
│   │   └── package.json                    # npm依存関係
│   └── docker-compose.yml                  # 開発環境構成
└── README.md                               # 本ファイル（プロジェクト概要）
```

---

## 🎯 実装フェーズ

### **Phase 1-2: 基盤構築** ✅ 完了
- Rocky Linux 9.6インストール
- KVM仮想化環境構築（将来使用予定）
- 5セグメント仮想ネットワーク構築

### **Phase 3: Docker環境** ✅ 完了
- Docker CE インストール
- ストレージ構成（SSD + HDD分離）
- Docker Compose環境構築

### **Phase 4-9: Mailserver構築** ✅ 完了
- 8コンテナ構成（Postfix, Dovecot, MariaDB, etc.）
- Tailscale VPN設定
- EC2 MX Gateway構築（Terraform）
- SendGrid SMTP Relay設定
- SPF/DKIM/DMARC設定

### **Phase 10: ローカルバックアップ** ✅ 完了
- **TDD開発**: 38 tests implemented
- 日次/週次自動バックアップ（cron）
- コンポーネント別リストア機能
- チェックサム検証

### **Phase 11: User Management** ✅ 完了
- Flask Python アプリケーション
- ユーザー管理WebUI
- Dovecot SQL認証統合
- TDD開発（pytest）

### **Phase 11-A: User Management Enhanced** ✅ 完了
- パスワード強度検証
- セッション管理・CSRF対策
- Flask-Login統合
- 監査ログ機能

### **Phase 11-B: S3オフサイトバックアップ** ✅ 完了
- **Terraform IaC**: S3, IAM, CloudWatch, SNS
- **Object Lock COMPLIANCE**: ランサムウェア対策
- **マルウェアスキャン**: ClamAV + rkhunter (3層防御)
- **コスト監視**: CloudWatch Alarms (10円/100円閾値)
- **自動化**: cron日次アップロード＋スキャン

### **Phase A-1: Blog System構築** ✅ 完了 (2025-11-09)
- **Docker Compose環境**: nginx, wordpress, mariadb, cloudflared (4コンテナ)
- **WordPress 16サイト移行**: 95GB データ + DB完了
- **Cloudflare Tunnel**: 5 Public Hostnames（16 WordPress installations）設定済み
- **動作確認**: 14/16サイト正常動作

### **Phase A-2: 本番ドメイン移行** ✅ 完了 (2025-11-12)
- **本番ドメイン移行**: 15サイト（blog.* → 本番ドメイン）
- **全サイトサブドメイン化**: 保守性向上のためサブディレクトリ→サブドメイン移行
- **301リダイレクト**: 旧URL → 新URL自動転送設定
- **WP Mail SMTP設定**: 全16サイトでメール送信機能統合
- **自動化スクリプト**: 新規サイト作成ウィザード、WP Mail SMTP一括設定、Nginx設定生成

### **P011: サブディレクトリ表示問題** ✅ 解決 (2025-11-11)
- **Nginx HTTPS検出パラメータ追加**: `fastcgi_param HTTPS on;` 等を8箇所追加
- **Elementor jQuery 404エラー解消**: blog.kuma8088.com配下10サイト正常化

### **Cloudflare Email Worker移行** ✅ 完了 (2025-11-12)
- **EC2 MX Gateway廃止**: 月額¥525削減
- **Email Worker実装**: サーバーレスMX受信（JavaScript）
- **mailserver-api追加**: FastAPI（9コンテナ目）、LMTP転送エンドポイント
- **Tailscale VPN廃止**: Cloudflare Tunnel経由で通信、管理コスト削減
- **新フロー確立**: Internet → Cloudflare Email Routing → Email Worker → Cloudflare Tunnel → mailserver-api (FastAPI) → Dovecot LMTP

### **Redis Object Cache統合** ✅ 完了 (2025-11-13)
- **Redis 5コンテナ目追加**: Blog System高速化
- **自動化スクリプト**: setup-redis-object-cache.sh（全16サイト一括設定）
- **性能テストツール**: test-redis-performance.sh
- **関連Issue**: I006完了

### **Unified Portal Phase 1** 🔄 実装中 (2025-11-13-)
- ✅ **プロジェクト構造作成**: FastAPI + React + TypeScript
- ✅ **Cloudflare DNS API統合完了**: ゾーン管理、DNSレコードCRUD、プロキシ設定
- ✅ **8管理ページUI完成**: Dashboard, Docker, Database, PHP, Security, WordPress, Domain, Backup
- ✅ **Xserver風デザイン**: Tailwind CSS + shadcn/ui
- 🔄 **残りAPI統合**: Docker, WordPress, Database, Backup（Phase 2で実装予定）
- **関連Issue**: I001（ポータル統合）、I002（UI刷新完了）、I003（機能拡張）

### **Phase B: Blog Production Hardening** 📋 計画中
- バックアップシステム実装（Mailserver Phase 11-B統合検討）
- CDNキャッシュ最適化
- 監視・アラート整備
- ディザスタリカバリ手順確立

---

## 🛠️ セットアップ手順

### 1. **前提条件確認**

```bash
# システム情報
cat /etc/redhat-release
# Expected: Rocky Linux release 9.6 (Blue Onyx)

# ディスク容量
df -h
# Expected: SSD 50GB + HDD 3.6TB

# メモリ
free -h
# Expected: 32GB RAM

# CPU
lscpu | grep "^CPU(s)"
# Expected: 12 threads (6 cores)
```

### 2. **リポジトリクローン**

```bash
cd /opt
git clone <repository-url> onprem-infra-system
cd onprem-infra-system/project-root-infra
```

### 3. **ドキュメント確認**

```bash
# インフラ構築手順
cat docs/infra/README.md

# Mailserver構築手順
cat docs/application/mailserver/03_installation.md

# バックアップシステム実装
cat docs/application/mailserver/backup/03_implementation.md
cat docs/application/mailserver/backup/07_s3backup_implementation.md
```

### 4. **環境構築**

詳細な手順は各ドキュメントを参照してください:
- **インフラ**: [docs/infra/README.md](docs/infra/README.md)
- **Mailserver**: [docs/application/mailserver/03_installation.md](docs/application/mailserver/03_installation.md)
- **Phase 10 Backup**: [docs/application/mailserver/backup/03_implementation.md](docs/application/mailserver/backup/03_implementation.md)
- **Phase 11-B S3 Backup**: [docs/application/mailserver/backup/07_s3backup_implementation.md](docs/application/mailserver/backup/07_s3backup_implementation.md)

---

## 📊 テスト・検証

### **Phase 10 Backup System Tests**

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# バックアップテスト
pytest tests/ -v

# 手動バックアップ実行
./backup-mailserver.sh --daily

# リストアテスト
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component mail
```

**テスト結果**: 38 tests passed ✅

### **Phase 11-B S3 Backup Tests**

```bash
# Terraform検証
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform-backup-s3
terraform validate
terraform plan

# S3アップロードテスト
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./backup-to-s3.sh --date $(date +%Y-%m-%d)

# マルウェアスキャンテスト
./scan-mailserver.sh --daily
```

**実装結果**: All systems operational ✅

---

## 🔒 セキュリティ

### **実装済みセキュリティ対策**

| カテゴリ | 実装内容 |
|---------|---------|
| **ネットワーク** | Tailscale VPN (WireGuard), 非標準SSHポート, Firewall設定 |
| **暗号化** | TLS 1.2+ (全プロトコル), Tailscale自動証明書, SMTP STARTTLS |
| **認証** | SMTP-AUTH, Dovecot SQL認証, IAM Role, Flask-Login |
| **メール認証** | SPF, DKIM, DMARC |
| **マルウェア対策** | ClamAV (8.7M signatures), rkhunter, 3層スキャン |
| **ランサムウェア対策** | S3 Object Lock COMPLIANCE (30日間削除不可) |
| **アクセス制御** | IAM最小権限原則, Security Groups, Docker network isolation |
| **監査** | CloudWatch Logs, 監査ログ機能（usermgmt）, cron実行ログ |

---

## 📈 監視・運用

### **ログ確認**

```bash
# Docker コンテナログ
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose logs -f --tail=100 postfix
docker compose logs -f --tail=100 dovecot

# バックアップログ
tail -f ~/.mailserver-backup.log
tail -f ~/.s3-backup-cron.log
tail -f ~/.scan-cron.log

# システムログ
sudo journalctl -u docker -f
sudo tail -f /var/log/cron
```

### **監視ポイント**

```bash
# コンテナ稼働状況
docker compose ps

# リソース使用状況
docker stats

# ディスク容量
df -h /var/lib/docker
df -h /data/docker
df -h /mnt/backup-hdd

# バックアップ実行確認
ls -lah /mnt/backup-hdd/mailserver/daily/
aws s3 ls s3://system-backup-workstation/daily/ --profile mailserver-backup-uploader
```

---

## 🚧 トラブルシューティング

### **よくある問題と対処**

詳細なトラブルシューティング手順:
- [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)

### **緊急連絡先・参考資料**

| リソース | URL |
|---------|-----|
| **Docker公式ドキュメント** | https://docs.docker.com/ |
| **Postfix公式ドキュメント** | http://www.postfix.org/documentation.html |
| **Dovecot Wiki** | https://doc.dovecot.org/ |
| **Terraform AWS Provider** | https://registry.terraform.io/providers/hashicorp/aws/latest/docs |
| **ClamAV** | https://docs.clamav.net/ |

---

## 📝 開発者向け情報

### **開発環境**

```bash
# Python開発環境
cd services/mailserver/usermgmt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# テスト実行
pytest tests/ -v --cov=app

# Linting
flake8 app/
black app/
```

### **Terraform開発**

```bash
# Terraform初期化
cd services/mailserver/terraform-backup-s3
terraform init

# Plan確認
terraform plan

# Apply
terraform apply

# 状態確認
terraform show
```

---

## 🎓 学習・スキル習得

このプロジェクトを通じて習得できる技術スキル:

### **インフラスキル**
- ✅ Linux システム管理 (Rocky Linux 9.6 / RHEL系)
- ✅ Docker & Docker Compose (マルチコンテナオーケストレーション)
- ✅ Terraform (IaC実践、AWS Provider)
- ✅ ネットワーク設計 (VPC, Security Groups, Tailscale VPN)
- ✅ ストレージ管理 (SSD/HDD分離、LVM)
- ✅ バックアップ・ディザスタリカバリ設計

### **開発スキル**
- ✅ TDD (Test-Driven Development) 実践
- ✅ Python開発 (Flask, SQLAlchemy, pytest)
- ✅ Bash Scripting (運用自動化)
- ✅ Git workflow (feature branch, commit conventions)

### **クラウドスキル**
- ✅ AWS (EC2, S3, IAM, CloudWatch, SNS, Secrets Manager)
- ✅ ハイブリッドクラウド構成
- ✅ コスト最適化 (リソース最適化、監視)

### **セキュリティスキル**
- ✅ SSL/TLS証明書管理
- ✅ IAM権限設計 (Least Privilege原則)
- ✅ ランサムウェア対策 (Object Lock COMPLIANCE)
- ✅ マルウェア対策 (ClamAV, rkhunter)
- ✅ メール認証 (SPF, DKIM, DMARC)

### **DevOpsスキル**
- ✅ CI/CD思想 (自動テスト、自動デプロイ)
- ✅ Infrastructure as Code (Terraform)
- ✅ ログ管理・監視
- ✅ ドキュメント駆動開発

---

## 📄 ライセンス

このプロジェクトは個人学習・ポートフォリオ用途です。

使用しているオープンソースソフトウェアのライセンス:
- **Postfix**: IBM Public License (IPL) 1.0
- **Dovecot**: MIT License / LGPLv2.1
- **MariaDB**: GPL v2
- **Roundcube**: GPL v3+
- **ClamAV**: GPL v2
- **Rspamd**: Apache License 2.0
- **Nginx**: BSD-like license
- **Flask**: BSD-3-Clause
- **Terraform**: MPL 2.0

---

## 👤 作成者

**Project Owner**: Naoya Iimura

**Contact**: naoya.iimura@gmail.com

**Portfolio**: このプロジェクトは実運用を想定した本格的なインフラ構築の学習・実践を目的としています。

---

## 🔗 関連リンク

| リソース | リンク |
|---------|-------|
| **インフラドキュメント** | [docs/infra/README.md](docs/infra/README.md) |
| **Mailserverドキュメント** | [docs/application/mailserver/README.md](docs/application/mailserver/README.md) |
| **Blog Systemドキュメント** | [docs/application/blog/README.md](docs/application/blog/README.md) ✅ NEW |
| **Phase 10 Backup実装** | [docs/application/mailserver/backup/03_implementation.md](docs/application/mailserver/backup/03_implementation.md) |
| **Phase 11-B S3 Backup** | [docs/application/mailserver/backup/07_s3backup_implementation.md](docs/application/mailserver/backup/07_s3backup_implementation.md) |
| **User Management (Phase 11)** | [docs/application/mailserver/usermgmt/README.md](docs/application/mailserver/usermgmt/README.md) |
| **Cloudflare Email Worker** | [docs/application/mailserver/migration/cloudflare-email-worker-implementation.md](docs/application/mailserver/migration/cloudflare-email-worker-implementation.md) ✅ **運用中** |
| **Phase A-1 Blog Migration** | [docs/application/blog/phases/phase-a1-completion.md](docs/application/blog/phases/phase-a1-completion.md) ✅ |
| **Phase A-2 Production Domain** | [docs/application/blog/phases/phase-a2-completion.md](docs/application/blog/phases/phase-a2-completion.md) ✅ |
| **Blog Issue Management** | [docs/application/blog/issue/README.md](docs/application/blog/issue/README.md) |
| **Unified Portal** | [docs/application/unified-portal/README.md](docs/application/unified-portal/README.md) 🆕 **Phase 1実装中** |
| **トラブルシューティング (Mailserver)** | [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md) |

---

**Last Updated**: 2025-11-13
**Version**: 1.3.0
**Status**: Multi-Service Production (Mailserver ✅ + Blog System ✅) + Unified Portal 🔄 (Phase 1実装中)
**Recent Updates**:
- ✅ **Unified Portal Phase 1実装中**: Cloudflare DNS API統合完了、8管理ページUI完成 (2025-11-13)
- ✅ **Redis Object Cache統合完了**: WordPress高速化、全16サイト対応 (2025-11-13)
- ✅ **Cloudflare Email Worker運用開始**: EC2廃止により月額¥525削減 (2025-11-12)
- ✅ **Blog System Phase A-2完了**: 本番ドメイン移行、WP Mail SMTP設定 (2025-11-12)
