# メールサーバーアーキテクチャ設計

**技術スタック**: Docker Compose, Postfix, Dovecot, Cloudflare

---

## 1. システム概要

### 1.1 アーキテクチャ方針

| 方針 | 内容 |
|------|------|
| コンテナ化 | 全サービスをDocker Composeで管理 |
| マイクロサービス | 機能ごとにコンテナを分離 |
| ゼロトラスト | Cloudflare Tunnel + Tailscale VPN |
| イミュータブルバックアップ | S3 Object Lock COMPLIANCE |

### 1.2 コンポーネント一覧（9コンテナ）

| サービス | イメージ | 役割 |
|---------|---------|------|
| Postfix | boky/postfix:latest | SMTP送信（外部Relay経由） |
| Dovecot | dovecot/dovecot:2.3.21 | IMAP/POP3/LMTP |
| MariaDB | mariadb:10.11.7 | Roundcube/usermgmt用DB |
| Roundcube | roundcube/roundcubemail:1.6.7 | Webメール |
| Rspamd | rspamd/rspamd:3.8 | スパムフィルタ |
| ClamAV | clamav/clamav:1.3 | ウイルススキャン |
| mailserver-api | カスタムビルド(FastAPI) | メール受信API |
| usermgmt | カスタムビルド(Flask) | ユーザー管理Web UI |
| Nginx | nginx:1.26-alpine | リバースプロキシ |

---

## 2. メールフロー設計

### 2.1 受信フロー（MX → メールボックス）

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet (MX)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cloudflare Email Routing                           │
│              (MXレコード受信、Port 25不要)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cloudflare Email Worker (JavaScript)               │
│              (メール解析、HTTPS変換)                             │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTPS POST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cloudflare Tunnel (Secure Connection)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              mailserver-api (FastAPI)                           │
│              (認証、メール変換)                                  │
└─────────────────────────────────────────────────────────────────┘
                              │ LMTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Dovecot                                            │
│              (メールボックス保存、Maildir形式)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 送信フロー（クライアント → Internet）

```
┌─────────────────────────────────────────────────────────────────┐
│              Mail Client (SMTP)                                 │
│              (Tailscale VPN経由)                                │
└─────────────────────────────────────────────────────────────────┘
                              │ SMTP (587/STARTTLS)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Postfix                                            │
│              (SMTP認証、DKIM署名)                                │
└─────────────────────────────────────────────────────────────────┘
                              │ Relay
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SendGrid (External SMTP Relay)                     │
│              (高到達率、SPF/DKIM対応)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Webメールフロー

```
┌─────────────────────────────────────────────────────────────────┐
│              Browser (HTTPS)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cloudflare (CDN/WAF)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cloudflare Tunnel                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Nginx (Reverse Proxy)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Roundcube (PHP)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │ IMAP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Dovecot                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. コンポーネント詳細設計

### 3.1 Postfix（MTA）

| 項目 | 設定 |
|------|------|
| 役割 | SMTP送信（受信はmailserver-api経由） |
| リレー先 | SendGrid SMTP Relay |
| 認証 | SASL認証必須（dovecot連携） |
| 暗号化 | STARTTLS必須 |
| DKIM | OpenDKIM連携 |

### 3.2 Dovecot（MDA）

| 項目 | 設定 |
|------|------|
| プロトコル | IMAP (993)、POP3 (995)、LMTP |
| メールボックス形式 | Maildir |
| 認証 | SQL認証（MariaDB連携） |
| SSL/TLS | 必須 |

### 3.3 mailserver-api（受信API）

| 項目 | 設定 |
|------|------|
| フレームワーク | FastAPI (Python) |
| 役割 | Cloudflare Worker → LMTP変換 |
| 認証 | Bearer Token |
| 出力 | Dovecot LMTP |

### 3.4 usermgmt（ユーザー管理）

| 項目 | 設定 |
|------|------|
| フレームワーク | Flask (Python) |
| 機能 | ユーザーCRUD、ドメイン管理 |
| データベース | MariaDB |
| UI | Bootstrap Web UI |

### 3.5 Rspamd（スパムフィルタ）

| 項目 | 設定 |
|------|------|
| 役割 | スパム判定、ヘッダー追加 |
| 連携 | Postfix milter |
| 学習 | Bayesフィルタ |

### 3.6 ClamAV（ウイルススキャン）

| 項目 | 設定 |
|------|------|
| 役割 | 添付ファイルスキャン |
| 連携 | Rspamd経由 |
| 定義更新 | freshclam自動更新 |

---

## 4. ネットワーク設計

### 4.1 Docker Network

```yaml
networks:
  mailserver_network:
    driver: bridge
```

### 4.2 ポート設計

| ポート | サービス | アクセス元 | 用途 |
|--------|---------|-----------|------|
| 25 | - | - | 未使用（Cloudflare Email経由） |
| 465 | Postfix | Tailscale VPN | SMTPS |
| 587 | Postfix | Tailscale VPN | Submission |
| 993 | Dovecot | Tailscale VPN | IMAPS |
| 995 | Dovecot | Tailscale VPN | POP3S |
| 443 | Nginx | Cloudflare Tunnel | HTTPS (Webmail/API) |

### 4.3 外部連携

| サービス | 用途 | 接続方式 |
|---------|------|----------|
| Cloudflare | Email Routing、Tunnel、DNS | HTTPS |
| SendGrid | SMTP Relay | SMTP over TLS |
| Tailscale | VPNアクセス | WireGuard |
| AWS S3 | オフサイトバックアップ | HTTPS (AWS SDK) |

---

## 5. データ設計

### 5.1 データベーススキーマ（usermgmt）

```sql
-- ドメインテーブル
CREATE TABLE domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザーテーブル
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    domain_id INT NOT NULL,
    quota_mb INT DEFAULT 2048,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

-- エイリアステーブル
CREATE TABLE aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    domain_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

### 5.2 ストレージ設計

| データ種別 | 保存先 | 理由 |
|-----------|--------|------|
| データベース | SSD | 高速I/O要求 |
| メールボックス | HDD | 大容量、コスト優先 |
| ログ | SSD | 頻繁な書き込み |
| バックアップ | HDD + S3 | 3-2-1ルール |

---

## 6. バックアップアーキテクチャ

### 6.1 バックアップフロー

```
┌─────────────────────────────────────────────────────────────────┐
│                    本番データ                                   │
│  (Maildir, MariaDB, Config, SSL, DKIM)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌───────────────────────────┐ ┌───────────────────────────────────┐
│   ローカルバックアップ      │ │   S3オフサイトバックアップ        │
│   (HDD: /mnt/backup-hdd)   │ │   (Object Lock COMPLIANCE)       │
│                           │ │                                   │
│   ├── daily/              │ │   ├── daily/                     │
│   │   └── YYYY-MM-DD/     │ │   │   └── YYYY-MM-DD/            │
│   └── weekly/             │ │   └── weekly/                    │
│       └── YYYY-WW/        │ │       └── YYYY-WW/               │
│                           │ │                                   │
│   保持: 日次7日, 週次4週   │ │   保持: 30日 (削除不可)          │
└───────────────────────────┘ └───────────────────────────────────┘
```

### 6.2 バックアップコンポーネント

```
backup-mailserver.sh
    │
    ├── backup_mailboxes()    # Maildir → tar.gz
    ├── backup_mysql()        # mysqldump
    ├── backup_configs()      # 設定ファイル
    ├── backup_ssl()          # SSL証明書
    ├── backup_dkim()         # DKIM鍵
    └── create_checksum()     # SHA256検証
```

### 6.3 リストアフロー

```
restore-mailserver.sh
    │
    ├── verify_backup()       # チェックサム検証
    ├── scan_for_malware()    # ClamAV + rkhunter
    │
    ├── restore_mysql()       # DB復元
    ├── restore_mailboxes()   # Maildir復元
    ├── restore_configs()     # 設定復元
    ├── restore_ssl()         # SSL復元
    └── restore_dkim()        # DKIM復元
```

---

## 7. セキュリティアーキテクチャ

### 7.1 多層防御

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Edge (Cloudflare)                                     │
│  - DDoS Protection (L3/L4/L7)                                   │
│  - WAF (OWASP Top 10)                                          │
│  - Bot Management                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Network (Cloudflare Tunnel + Tailscale)               │
│  - Zero Trust Access                                            │
│  - No Inbound Ports                                             │
│  - VPN for Mail Clients                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Application                                           │
│  - Rspamd (Spam Filter)                                         │
│  - ClamAV (Virus Scan)                                          │
│  - SMTP Authentication                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Data                                                  │
│  - S3 Object Lock COMPLIANCE                                    │
│  - Encryption at Rest                                           │
│  - Immutable Backups                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 認証フロー

```
                    ┌─────────────────────┐
                    │   ユーザー認証       │
                    └─────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │  Webメール     │ │  IMAP/SMTP    │ │  管理UI       │
    │  (Roundcube)  │ │  (Dovecot)    │ │  (usermgmt)   │
    └───────────────┘ └───────────────┘ └───────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │  IMAP認証     │ │  SQL認証      │ │  セッション    │
    │  → Dovecot    │ │  → MariaDB    │ │  → Flask      │
    └───────────────┘ └───────────────┘ └───────────────┘
```

---

## 8. 監視アーキテクチャ

### 8.1 ヘルスチェック

| サービス | チェック方法 | 間隔 |
|---------|------------|------|
| Postfix | SMTP接続確認 | 30秒 |
| Dovecot | サービスステータス | 30秒 |
| MariaDB | mysqladmin ping | 30秒 |
| Nginx | HTTP応答確認 | 30秒 |
| ClamAV | スキャン実行テスト | 60秒 |

### 8.2 ログ管理

| ログ種別 | 保存先 | 保持期間 |
|---------|--------|----------|
| Docker logs | /var/lib/docker/containers | 7日 |
| バックアップログ | ~/.mailserver-backup.log | 30日 |
| S3同期ログ | ~/.s3-backup-cron.log | 30日 |
| スキャンログ | ~/.scan-cron.log | 30日 |

---

## 9. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・監視・バックアップ運用 |
