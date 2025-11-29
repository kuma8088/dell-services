# On-Premise Infrastructure System

Dell WorkStation (Rocky Linux 9.6) 上で Mailserver と Blog System を運用するインフラプロジェクト。

## 概要

オンプレミス環境と Cloudflare/AWS を組み合わせたハイブリッド構成で、メールサーバーと WordPress サイト群を運用しています。

**現在の構成**:
- Mailserver: 9コンテナ（Postfix, Dovecot, MariaDB, Roundcube 等）
- Blog System: 5コンテナ（WordPress 17サイト、Redis Object Cache）
- Unified Portal: 統合管理ポータル（FastAPI + React）

## アーキテクチャ

```
Internet
    │
    ├── MX (Port 25) ─────────────────┐
    │                                 │
    ▼                                 ▼
Cloudflare                        Cloudflare
├─ Email Routing                  ├─ SSL/TLS
├─ Email Worker (JS)              ├─ DDoS Protection
└─ Tunnel ────────────────────────┴─ CDN
    │
    ▼
Dell WorkStation (Rocky Linux 9.6)
├── Mailserver (9 containers)
│   ├─ Postfix → SendGrid Relay
│   ├─ Dovecot (IMAP/POP)
│   ├─ MariaDB
│   ├─ Roundcube
│   ├─ ClamAV, Rspamd
│   ├─ User Management (Flask)
│   └─ Mail API (FastAPI) ← Email Worker
│
├── Blog System (5 containers)
│   ├─ WordPress (PHP-FPM)
│   ├─ Nginx (17 virtual hosts)
│   ├─ MariaDB (17 databases)
│   ├─ Redis (Object Cache)
│   └─ cloudflared (Tunnel)
│
├── Unified Portal
│   ├─ FastAPI (Backend)
│   └─ React (Frontend)
│
└── Storage
    ├─ SSD 50GB (DB, Logs)
    └─ HDD 3.6TB (Mail, Blog, Backups)
         │
         ▼
    AWS S3 (Offsite Backup)
    ├─ Object Lock (ransomware protection)
    └─ CloudWatch (cost monitoring)
```

## できること

| 機能 | 説明 |
|------|------|
| メール送受信 | IMAP/POP3、Webmail (Roundcube)、SendGrid経由送信 |
| スパム/ウイルス対策 | Rspamd + ClamAV |
| ユーザー管理 | Web UI でメールアカウント CRUD |
| WordPress 運用 | 17サイト、ドメイン別管理、Redis キャッシュ |
| 自動バックアップ | 日次/週次ローカル + S3 オフサイト |
| 統合管理 | Cloudflare DNS、Docker、DB を単一ポータルから操作 |

## ディレクトリ構成

```
project-root-infra/
├── docs/
│   ├── infra/                    # インフラ構築手順
│   └── application/
│       ├── mailserver/           # Mailserver 設計・運用
│       ├── blog/                 # Blog System 設計・運用
│       └── unified-portal/       # 統合ポータル設計
├── services/
│   ├── mailserver/               # Mailserver 実装
│   │   ├── docker-compose.yml
│   │   ├── config/               # Postfix, Dovecot 等の設定
│   │   ├── scripts/              # バックアップ、リストア
│   │   ├── terraform/            # AWS IaC
│   │   └── usermgmt/             # Flask ユーザー管理
│   ├── blog/                     # Blog System 実装
│   │   ├── docker-compose.yml
│   │   ├── config/               # Nginx, WordPress 設定
│   │   └── scripts/              # サイト作成、SMTP設定
│   └── unified-portal/           # 統合ポータル実装
│       ├── backend/              # FastAPI
│       └── frontend/             # React + TypeScript
└── README.md
```

## クイックスタート

### 前提条件

- Rocky Linux 9.6
- Docker & Docker Compose
- 十分なストレージ（HDD 3TB 以上推奨）

### Mailserver 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
cp .env.example .env  # 環境変数を設定
docker compose up -d
```

### Blog System 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
cp .env.example .env
docker compose up -d
```

### Unified Portal 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
cp .env.example .env
docker compose up -d
```

## 運用コマンド

### 状態確認

```bash
# Mailserver
cd services/mailserver && docker compose ps

# Blog
cd services/blog && docker compose ps

# ログ確認
docker compose logs -f postfix
docker compose logs -f wordpress
```

### バックアップ

```bash
cd services/mailserver/scripts

# ローカルバックアップ
./backup-mailserver.sh --daily

# S3アップロード
./backup-to-s3.sh

# マルウェアスキャン
./scan-mailserver.sh --daily
```

### リストア

```bash
cd services/mailserver/scripts

# プレビュー
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/2025-11-29 --dry-run

# 実行
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/2025-11-29 --component all
```

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| OS | Rocky Linux 9.6 |
| コンテナ | Docker, Docker Compose |
| Mail | Postfix, Dovecot, Roundcube |
| Web | Nginx, WordPress, PHP-FPM |
| DB | MariaDB |
| Cache | Redis |
| IaC | Terraform |
| Cloud | Cloudflare (Tunnel, Email Worker), AWS (S3, CloudWatch) |
| Backend | FastAPI, Flask |
| Frontend | React, TypeScript, Tailwind CSS |

## セキュリティ

- SPF/DKIM/DMARC によるメール認証
- ClamAV + Rspamd によるマルウェア/スパム対策
- S3 Object Lock (COMPLIANCE) によるランサムウェア対策
- Cloudflare Tunnel による安全な公開（ポート開放不要）
- IAM 最小権限原則

## コスト

| サービス | 月額 |
|---------|------|
| Cloudflare (Tunnel, Email Worker) | 無料 |
| AWS S3 + CloudWatch | 約 150円 |
| SendGrid | 無料枠 |

EC2 MX Gateway を廃止し、月額 525円 削減済み。

## ドキュメント

- [インフラ構築](docs/infra/README.md)
- [Mailserver](docs/application/mailserver/README.md)
- [Blog System](docs/application/blog/README.md)
- [Unified Portal](services/unified-portal/README.md)
- [トラブルシューティング](services/mailserver/troubleshoot/README.md)

## 作成者

Naoya Iimura (naoya.iimura@gmail.com)
