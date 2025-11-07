# Phase 11-B: リカバリー手順書

**ドキュメントバージョン**: 1.1
**最終更新日**: 2025-11-07
**対象フェーズ**: Phase 11-B（障害復旧手順）
**前提フェーズ**: Phase 10（ローカルバックアップ）、Phase 11-B（S3バックアップ）完了

---

## 目次

1. [概要](#1-概要)
2. [復旧の前提条件](#2-復旧の前提条件)
3. [シナリオ1: Githubからのインフラ復旧](#3-シナリオ1-githubからのインフラ復旧)
4. [シナリオ2: S3からのデータ復旧](#4-シナリオ2-s3からのデータ復旧)
5. [シナリオ3: 完全障害からの復旧](#5-シナリオ3-完全障害からの復旧)
6. [シナリオ4: 部分復旧（コンポーネント別）](#6-シナリオ4-部分復旧コンポーネント別)
7. [検証手順](#7-検証手順)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. 概要

### 1.1 復旧戦略

Mailserverシステムは2つのバックアップソースから復旧可能です：

```
┌─────────────────────────────────────────┐
│         復旧ソース                      │
├─────────────────────────────────────────┤
│                                         │
│  1. Github リポジトリ                   │
│     └─ IaC（Infrastructure as Code）   │
│        ├─ docker-compose.yml           │
│        ├─ Terraform 設定               │
│        ├─ 設定ファイル                 │
│        └─ スクリプト                   │
│                                         │
│  2. S3 バックアップ                     │
│     └─ データバックアップ              │
│        ├─ メールデータ                 │
│        ├─ MySQL データベース           │
│        ├─ 設定ファイル                 │
│        └─ ログ                         │
│                                         │
└─────────────────────────────────────────┘
```

### 1.2 復旧シナリオマトリクス

| シナリオ | 復旧対象 | 復旧元 | RTO | RPO |
|----------|----------|--------|-----|-----|
| **インフラ復旧** | Docker環境、設定 | Github | 2時間 | N/A |
| **データ復旧** | メール、DB | S3 | 1時間 | 24時間 |
| **完全障害** | すべて | Github + S3 | 4時間 | 24時間 |
| **部分復旧** | 特定コンポーネント | S3 | 30分 | 24時間 |

**用語説明**:
- **RTO (Recovery Time Objective)**: 目標復旧時間
- **RPO (Recovery Point Objective)**: 目標復旧時点（データ損失許容範囲）

### 1.3 復旧優先順位

```
1. インフラ基盤復旧（Github）
   ├─ ホスト環境確認
   ├─ Docker環境構築
   └─ ネットワーク設定

2. 設定ファイル復元（S3 or Github）
   ├─ Postfix/Dovecot設定
   ├─ MySQL設定
   └─ TLS証明書

3. データベース復旧（S3）
   └─ MySQL データベース

4. メールデータ復旧（S3）
   └─ Maildir データ

5. サービス起動・検証
   └─ 全サービス起動確認
```

---

## 2. 復旧の前提条件

### 2.1 ハードウェア要件

Dell WorkStation または同等環境:
- CPU: 6コア/12スレッド以上
- RAM: 32GB以上
- Storage:
  - SSD: 390GB以上（/var/lib/docker 用）
  - HDD: 3.6TB以上（バックアップ用）
- OS: Rocky Linux 9.6 以降

### 2.2 ネットワーク要件

- インターネット接続（Github、AWS S3アクセス）
- SSH ポート（22以外のカスタムポート）が開放
- Tailscale VPN接続（推奨）
- DNS設定（ドメイン名解決）

### 2.3 アクセス権限

**Github**:
- リポジトリ読み取り権限
- SSH鍵またはPATトークン

**AWS S3**:
- IAMプロファイル: `mailserver-backup-admin`（読み取り専用）
- AWS CLI設定済み（~/.aws/credentials, ~/.aws/config）

**システム**:
- root または sudo 権限
- system-admin ユーザー

### 2.4 必要な情報

復旧作業前に以下の情報を確認してください:

```bash
# 確認事項チェックリスト
□ AWS Account ID
□ S3 Bucket名: mailserver-backup-{ACCOUNT_ID}
□ 管理者メールアドレス
□ TLS証明書の有効期限
□ 最新バックアップ日付
□ Github リポジトリ URL
□ SSH カスタムポート番号
□ Tailscale 認証キー
□ SendGrid API Key
□ MySQL パスワード（MYSQL_PASSWORD, USERMGMT_DB_PASSWORD）
```

---

## 3. シナリオ1: Githubからのインフラ復旧

**目的**: IaC（Infrastructure as Code）からDocker環境とサービス設定を復旧

**対象**:
- Docker Compose 構成
- Terraform 設定
- サービス設定ファイル
- スクリプト

**所要時間**: 約2時間

### 3.1 事前準備

```bash
# 1. システム情報確認
cat /etc/os-release
uname -a

# 2. ディスク容量確認
df -h

# 3. 必要なパッケージインストール
sudo dnf install -y git vim wget curl

# 4. ホスト名設定
sudo hostnamectl set-hostname dell-mailserver.local
```

### 3.2 Githubリポジトリのクローン

```bash
# 1. SSH鍵の配置（既存の鍵を使用する場合）
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# 既存の秘密鍵を ~/.ssh/id_ed25519 に配置
chmod 600 ~/.ssh/id_ed25519

# 2. Github接続確認
ssh -T git@github.com

# 3. リポジトリクローン
cd /opt/onprem-infra-system
sudo git clone git@github.com:YOUR_USERNAME/project-root-infra.git

# 4. 所有権変更
sudo chown -R system-admin:system-admin project-root-infra

# 5. 最新状態に更新
cd project-root-infra
git pull origin main
git status
git branch
```

### 3.3 Docker環境構築

**参照**: [docs/infra/README.md](../../infra/README.md) - Phase 3: Docker環境構築

```bash
# 1. Docker インストール
cd /opt/onprem-infra-system/project-root-infra/docs/infra
# Phase 3の手順に従ってDockerをインストール

# 2. Docker Compose インストール
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Docker サービス起動
sudo systemctl enable docker
sudo systemctl start docker

# 4. 動作確認
docker --version
docker-compose --version
sudo docker ps
```

### 3.4 ストレージ構成

```bash
# 1. SSD マウント確認（/var/lib/docker 用）
lsblk
df -h /var/lib/docker

# 2. HDD マウント確認（バックアップ用）
df -h /mnt/backup-hdd

# 3. ストレージが未マウントの場合
# docs/infra/README.md の Phase 3: ストレージ構成を参照
```

### 3.5 環境変数設定

```bash
# 1. .env ファイル作成（Mailserver用）
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

cat > .env <<EOF
# Phase 10 & 11: Mailserver Configuration
MYSQL_ROOT_PASSWORD=YourSecureRootPassword
MYSQL_PASSWORD=YourSecureMySQLPassword
USERMGMT_DB_PASSWORD=SecureMailUserMgmt2024!

# SendGrid Configuration
SENDGRID_API_KEY=SG.your-sendgrid-api-key

# Domain Configuration
DOMAIN=your-domain.com

# TLS Configuration
TLS_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
TLS_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
EOF

chmod 600 .env

# 2. AWS環境変数設定（バックアップ用）
# セクション 4.2 で設定
```

### 3.6 Terraform 初期化（オプション）

**注意**: S3バックアップインフラが既に存在する場合はスキップ可能

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/s3-backup

# 1. Terraform 初期化
terraform init

# 2. 既存リソース確認
terraform plan

# 3. 必要に応じて apply
# terraform apply
```

### 3.7 サービス起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. Docker Compose 設定確認
docker-compose config

# 2. サービス起動
docker-compose up -d

# 3. ログ確認
docker-compose logs -f

# 4. コンテナ状態確認
docker-compose ps
```

### 3.8 動作確認

```bash
# 1. ポート確認
ss -tuln | grep -E ':(25|587|993|3306|8080)'

# 2. サービス疎通確認
# Postfix SMTP
timeout 5 openssl s_client -connect localhost:587 -starttls smtp
# Dovecot IMAPS
timeout 5 openssl s_client -connect localhost:993
# MariaDB
docker exec -it mailserver-mariadb mysql -u root -p -e "SHOW DATABASES;"

# 3. ログ確認
docker logs mailserver-postfix
docker logs mailserver-dovecot
docker logs mailserver-mariadb
```

---

## 4. シナリオ2: S3からのデータ復旧

**目的**: S3バックアップからメールデータとデータベースを復旧

**対象**:
- メールデータ（Maildir）
- MySQLデータベース
- 設定ファイル（オプション）

**所要時間**: 約1時間

### 4.1 前提条件確認

```bash
# 1. Docker環境が稼働していること
docker-compose ps

# 2. AWS CLI設定確認
aws --version
aws sts get-caller-identity --profile mailserver-backup-admin

# 3. スクリプト存在確認
ls -la /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-from-s3.sh
```

### 4.2 AWS環境変数設定

```bash
# 1. Terraform実行用環境変数（~/.bashrc）
cat >> ~/.bashrc <<'EOF'

# Phase 11-B: Terraform Configuration
export AWS_PROFILE=mailserver-backup
export AWS_DEFAULT_REGION=ap-northeast-1
export TF_VAR_admin_email="your-email@example.com"
EOF

source ~/.bashrc

# 2. スクリプト用設定ファイル（/etc/mailserver-backup/config）
sudo mkdir -p /etc/mailserver-backup
sudo tee /etc/mailserver-backup/config <<EOF
# Phase 11-B: Backup Script Configuration

# メール通知設定
ADMIN_EMAIL="your-email@example.com"

# AWS設定（cron実行時に必要）
AWS_PROFILE=mailserver-backup-uploader
AWS_DEFAULT_REGION=ap-northeast-1
EOF

sudo chmod 600 /etc/mailserver-backup/config
sudo chown system-admin:system-admin /etc/mailserver-backup/config

# 3. 設定確認
cat /etc/mailserver-backup/config
```

### 4.3 S3バックアップ一覧確認

```bash
# 1. S3バケット名取得
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/s3-backup
S3_BUCKET=$(terraform output -raw s3_bucket_name)
echo "S3 Bucket: ${S3_BUCKET}"

# 2. 利用可能なバックアップ一覧
aws s3 ls "s3://${S3_BUCKET}/daily/" \
  --profile mailserver-backup-admin

# 3. 最新バックアップ日付確認
aws s3 ls "s3://${S3_BUCKET}/daily/" \
  --profile mailserver-backup-admin \
  | awk '{print $2}' \
  | sed 's#/##g' \
  | sort -r \
  | head -n 5

# 4. 特定日付のバックアップ内容確認
BACKUP_DATE="2025-11-07"  # 復旧したい日付
aws s3 ls "s3://${S3_BUCKET}/daily/${BACKUP_DATE}/" \
  --recursive \
  --human-readable \
  --profile mailserver-backup-admin
```

### 4.4 最新バックアップからの完全復旧

**注意**: サービスを一時停止してからリストアを実行してください

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. サービス停止
docker-compose stop

# 2. スクリプト実行
cd scripts
./restore-from-s3.sh --component all

# 実行内容:
# - S3から最新バックアップをダウンロード
# - チェックサム検証
# - マルウェアスキャン
# - データリストア
# - サービス再起動

# 3. ログ確認
tail -100 /var/log/mailserver-backup/s3-backup.log

# 4. サービス状態確認
docker-compose ps
```

### 4.5 特定日付からのリストア

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. 指定日付のバックアップからリストア
BACKUP_DATE="2025-11-06"  # リストアしたい日付
./restore-from-s3.sh --date "${BACKUP_DATE}" --component all

# 2. ログ確認
tail -100 /var/log/mailserver-backup/s3-backup.log
```

### 4.6 コンポーネント別リストア

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# オプション1: メールデータのみリストア
./restore-from-s3.sh --component mail

# オプション2: MySQLデータベースのみリストア
docker-compose stop mariadb
./restore-from-s3.sh --component mysql
docker-compose start mariadb

# オプション3: 設定ファイルのみリストア
./restore-from-s3.sh --component config

# オプション4: すべてリストア
./restore-from-s3.sh --component all
```

### 4.7 手動リストア（スクリプト不使用）

**緊急時のみ使用**

```bash
# 1. S3からダウンロード
BACKUP_DATE="2025-11-07"
S3_BUCKET=$(cd ../terraform/s3-backup && terraform output -raw s3_bucket_name)
RESTORE_DIR="/tmp/manual-restore-${BACKUP_DATE}"

mkdir -p "${RESTORE_DIR}"
aws s3 sync "s3://${S3_BUCKET}/daily/${BACKUP_DATE}/" "${RESTORE_DIR}/" \
  --profile mailserver-backup-admin

# 2. チェックサム検証
cd "${RESTORE_DIR}"
sha256sum -c checksums.sha256

# 3. マルウェアスキャン
clamscan -r "${RESTORE_DIR}" --infected

# 4. サービス停止
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker-compose stop

# 5. メールデータリストア
# S3構造: mail/vmail/ → ホスト: ./data/mail/
sudo mkdir -p ./data/mail
sudo rsync -av "${RESTORE_DIR}"/mail/vmail/ ./data/mail/

# 6. MySQLデータリストア
# S3構造: mysql/*.sql.gz → ホスト: ./data/db/ （SQLファイルをインポート）
sudo mkdir -p ./data/db

# MySQL起動（データディレクトリ初期化のため）
docker-compose up -d mariadb
sleep 30

# SQLダンプをインポート
for sql_gz in "${RESTORE_DIR}"/mysql/*.sql.gz; do
    db_name=$(basename "${sql_gz}" .sql.gz)
    echo "Importing ${db_name}..."
    gunzip -c "${sql_gz}" | docker exec -i mailserver-mariadb \
        mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "${db_name}"
done

# 7. 設定ファイルリストア（オプション）
# S3構造: config/config.tar.gz → ホスト: ./config/
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
if [ -f "${RESTORE_DIR}"/config/config.tar.gz ]; then
    tar -xzf "${RESTORE_DIR}"/config/config.tar.gz -C ./
fi

# 8. DKIM鍵リストア（オプション）
# S3構造: dkim/opendkim-keys.tar.gz → ホスト: ./config/opendkim/
if [ -f "${RESTORE_DIR}"/dkim/opendkim-keys.tar.gz ]; then
    tar -xzf "${RESTORE_DIR}"/dkim/opendkim-keys.tar.gz -C ./config/opendkim/
fi

# 9. SSL証明書リストア（オプション）
# S3構造: ssl/certbot.tar.gz → ホスト: /etc/letsencrypt/
if [ -f "${RESTORE_DIR}"/ssl/certbot.tar.gz ]; then
    sudo tar -xzf "${RESTORE_DIR}"/ssl/certbot.tar.gz -C /etc/letsencrypt/
fi

# 10. すべてのサービス起動
docker-compose up -d

# 11. クリーンアップ
rm -rf "${RESTORE_DIR}"
```

**重要な注意事項**:

1. **S3構造**: ディレクトリ単位で格納（mail/, mysql/, config/, dkim/, ssl/）
2. **リストア先**: ホストディレクトリへのbind mount
   - メール: `./data/mail/` （docker-compose.yml の mail_data ボリューム）
   - MySQL: `./data/db/` （docker-compose.yml の db_data ボリューム）
3. **MySQLリストア**: SQLダンプファイルをインポート（ディレクトリコピーではない）
4. **環境変数**: MYSQL_ROOT_PASSWORD は .env ファイルから読み込み必要

---

## 5. シナリオ3: 完全障害からの復旧

**目的**: ハードウェア故障などによる完全障害からの復旧

**復旧順序**: Github（インフラ）→ S3（データ）

**所要時間**: 約4時間

### 5.1 復旧フロー

```
┌─────────────────────────────────────┐
│ 1. ハードウェア準備                │
│    └─ Dell WorkStation 準備        │
│       ├─ OS インストール           │
│       └─ 基本設定                  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 2. システム基盤構築                 │
│    └─ Phase 3 実施                 │
│       ├─ Docker インストール      │
│       └─ ストレージマウント        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 3. IaC復旧（Github）               │
│    └─ シナリオ1 実施               │
│       ├─ リポジトリクローン        │
│       ├─ 環境変数設定              │
│       └─ サービス起動              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 4. データ復旧（S3）                │
│    └─ シナリオ2 実施               │
│       ├─ バックアップダウンロード │
│       ├─ マルウェアスキャン        │
│       └─ データリストア            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 5. 検証・切り戻し                  │
│    └─ セクション 7 実施            │
│       ├─ サービス疎通確認          │
│       ├─ メール送受信テスト        │
│       └─ DNS切り戻し               │
└─────────────────────────────────────┘
```

### 5.2 Step 1: ハードウェア準備

#### 5.2.1 OS インストール

```bash
# Rocky Linux 9.6 インストール
# - Minimal Install 選択
# - ネットワーク設定
# - パーティション設定:
#   - /boot: 1GB
#   - /: 50GB（SSD）
#   - /var/lib/docker: 340GB（SSD残り）
#   - /mnt/backup-hdd: 3.6TB（HDD）

# インストール後の初期設定
sudo dnf update -y
sudo dnf install -y vim wget curl git net-tools

# ホスト名設定
sudo hostnamectl set-hostname dell-mailserver.local

# タイムゾーン設定
sudo timedatectl set-timezone Asia/Tokyo

# SELinux設定確認
getenforce
# → Enforcing であることを確認
```

#### 5.2.2 ネットワーク設定

```bash
# 1. 静的IP設定（必要に応じて）
sudo nmtui

# 2. SSH設定
sudo vim /etc/ssh/sshd_config
# → Port 22以外に変更（セキュリティのため）
# → PermitRootLogin no
# → PasswordAuthentication yes（初回のみ）

sudo systemctl restart sshd

# 3. ファイアウォール設定
sudo firewall-cmd --permanent --add-port=YOUR_SSH_PORT/tcp
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=25/tcp
sudo firewall-cmd --permanent --add-port=587/tcp
sudo firewall-cmd --permanent --add-port=993/tcp
sudo firewall-cmd --reload

# 4. Tailscale インストール（推奨）
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

#### 5.2.3 ユーザー作成

```bash
# system-admin ユーザー作成
sudo useradd -m -s /bin/bash system-admin
sudo passwd system-admin

# sudo 権限付与
echo "system-admin ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/system-admin

# SSH鍵設定
sudo su - system-admin
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# 公開鍵を ~/.ssh/authorized_keys に配置
chmod 600 ~/.ssh/authorized_keys
```

### 5.3 Step 2: システム基盤構築

```bash
# Phase 3: Docker環境構築を実施
# 参照: docs/infra/README.md

# 概要:
# 1. Docker インストール
# 2. Docker Compose インストール
# 3. ストレージマウント設定
# 4. Docker データディレクトリ設定

# 実施後、以下で確認
docker --version
docker-compose --version
df -h /var/lib/docker
df -h /mnt/backup-hdd
```

### 5.4 Step 3: IaC復旧（Github）

```bash
# シナリオ1（セクション 3）を実施

# 概要:
# 1. Githubリポジトリクローン
# 2. Docker Compose 起動
# 3. サービス起動確認

# 実施後、以下で確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker-compose ps
# → すべてのコンテナが Up 状態であることを確認
```

### 5.5 Step 4: データ復旧（S3）

```bash
# シナリオ2（セクション 4）を実施

# 概要:
# 1. AWS CLI設定
# 2. S3バックアップ一覧確認
# 3. restore-from-s3.sh 実行
# 4. データリストア

# 実施後、以下で確認
docker exec -it mailserver-mariadb mysql -u root -p -e "SHOW DATABASES;"
docker exec -it mailserver-mariadb mysql -u mailuser -p mailserver -e "SELECT COUNT(*) FROM users;"
sudo ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/
```

### 5.6 Step 5: 検証・切り戻し

セクション 7 を実施

---

## 6. シナリオ4: 部分復旧（コンポーネント別）

### 6.1 メールデータのみ復旧

**症状**: メールデータが破損したが、データベースと設定は正常

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. Dovecot停止
docker-compose stop dovecot

# 2. メールデータのみリストア
./restore-from-s3.sh --component mail

# 3. Dovecot起動
docker-compose start dovecot

# 4. ログ確認
docker logs mailserver-dovecot

# 5. メール受信テスト
# IMAPクライアントで接続確認
```

### 6.2 MySQLデータベースのみ復旧

**症状**: データベースが破損したが、メールデータと設定は正常

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. MySQL停止
docker-compose stop mariadb

# 2. 既存データバックアップ（念のため）
sudo tar -czf /tmp/mysql-broken-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/lib/docker/volumes/mailserver_mysql/_data/

# 3. MySQLデータベースのみリストア
./restore-from-s3.sh --component mysql

# 4. MySQL起動
docker-compose start mariadb

# 5. データベース確認
docker exec -it mailserver-mariadb mysql -u root -p <<EOF
SHOW DATABASES;
USE mailserver;
SHOW TABLES;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM domains;
SELECT COUNT(*) FROM aliases;
EOF

# 6. 依存サービス再起動
docker-compose restart postfix dovecot usermgmt
```

### 6.3 Postfix設定のみ復旧

**症状**: Postfix設定が誤って変更された

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. 現在の設定をバックアップ
sudo tar -czf /tmp/postfix-config-broken-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/

# 2. 設定ファイルのみリストア
./restore-from-s3.sh --component config

# または、Githubから復旧
cd /opt/onprem-infra-system/project-root-infra
git checkout config/postfix/main.cf
git checkout config/postfix/master.cf

# 3. Postfix再起動
docker-compose restart postfix

# 4. 設定確認
docker exec mailserver-postfix postconf -n

# 5. メール送信テスト
echo "Test mail" | mail -s "Test" test@example.com
docker logs mailserver-postfix | tail -50
```

### 6.4 Dovecot設定のみ復旧

**症状**: Dovecot設定が誤って変更された

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. 現在の設定をバックアップ
sudo tar -czf /tmp/dovecot-config-broken-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/

# 2. 設定ファイルをGithubから復旧
cd /opt/onprem-infra-system/project-root-infra
git checkout config/dovecot/dovecot.conf
git checkout config/dovecot/dovecot-sql.conf.ext
git checkout config/dovecot/10-auth.conf
git checkout config/dovecot/10-mail.conf
git checkout config/dovecot/10-master.conf
git checkout config/dovecot/10-ssl.conf

# 3. パスワード再設定（重要）
vim services/mailserver/config/dovecot/dovecot-sql.conf.ext
# → connect = host=mysql dbname=mailserver user=usermgmt password=YOUR_USERMGMT_PASSWORD

# 4. Dovecot再起動
cd services/mailserver
docker-compose restart dovecot

# 5. 設定確認
docker exec mailserver-dovecot doveconf -n

# 6. IMAP接続テスト
timeout 5 openssl s_client -connect localhost:993
```

### 6.5 TLS証明書復旧

**症状**: TLS証明書が期限切れまたは破損

```bash
# オプション1: S3バックアップから復旧
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./restore-from-s3.sh --component config

# オプション2: Tailscale証明書で再取得
sudo tailscale cert dell-mailserver.your-tailnet.ts.net

# オプション3: Let's Encrypt で再取得（外部公開サーバーの場合）
sudo certbot certonly --standalone -d your-domain.com

# 証明書パス更新
vim /opt/onprem-infra-system/project-root-infra/services/mailserver/.env
# → TLS_CERT_PATH, TLS_KEY_PATH を更新

# サービス再起動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker-compose restart postfix dovecot

# 証明書確認
openssl x509 -in /path/to/fullchain.pem -noout -dates -subject
```

### 6.6 User Management System復旧

**症状**: User Management WebUIが動作しない

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. コンテナ状態確認
docker-compose ps usermgmt

# 2. ログ確認
docker logs mailserver-usermgmt

# 3. 環境変数確認
docker exec mailserver-usermgmt printenv | grep -E '(DB_|USERMGMT_)'

# 4. データベース接続確認
docker exec mailserver-usermgmt python3 -c "
import mysql.connector
conn = mysql.connector.connect(
    host='mysql',
    user='usermgmt',
    password='YOUR_USERMGMT_PASSWORD',
    database='mailserver'
)
print('Connection successful')
conn.close()
"

# 5. 設定ファイルをGithubから復旧
cd /opt/onprem-infra-system/project-root-infra
git checkout services/mailserver/usermgmt/

# 6. コンテナ再ビルド
cd services/mailserver
docker-compose build usermgmt
docker-compose up -d usermgmt

# 7. WebUI確認
curl -I http://localhost:8080
```

---

## 7. 検証手順

### 7.1 インフラ検証

```bash
# 1. Dockerサービス確認
sudo systemctl status docker
docker --version
docker-compose --version

# 2. コンテナ状態確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker-compose ps
# → すべてのコンテナが Up 状態であることを確認

# 3. ネットワーク確認
docker network ls
docker network inspect mailserver_default

# 4. ボリューム確認
docker volume ls
docker volume inspect mailserver_mail_data
docker volume inspect mailserver_db_data

# ホストディレクトリ確認（bind mount先）
ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/
ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/db/

# 5. ディスク容量確認
df -h /var/lib/docker
df -h /mnt/backup-hdd
df -h /opt/onprem-infra-system
```

### 7.2 サービス疎通確認

```bash
# 1. ポートリスニング確認
ss -tuln | grep -E ':(25|587|993|3306|8080)'

# 2. Postfix SMTP接続
timeout 5 openssl s_client -connect localhost:587 -starttls smtp <<EOF
EHLO test
QUIT
EOF

# 3. Dovecot IMAPS接続
timeout 5 openssl s_client -connect localhost:993 <<EOF
a001 CAPABILITY
a002 LOGOUT
EOF

# 4. MySQL接続
docker exec -it mailserver-mariadb mysql -u root -p -e "SELECT VERSION();"

# 5. User Management WebUI
curl -I http://localhost:8080
```

### 7.3 データ整合性確認

```bash
# 1. データベース確認
docker exec -it mailserver-mariadb mysql -u root -p <<EOF
USE mailserver;
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS domain_count FROM domains;
SELECT COUNT(*) AS alias_count FROM aliases;
SELECT * FROM users LIMIT 5;
EOF

# 2. メールデータ確認
# ホストディレクトリ（bind mount先）
sudo ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/
sudo du -sh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/*/

# 3. 設定ファイル確認
docker exec mailserver-postfix postconf -n | grep -E '(myhostname|mydomain|relay_domains)'
docker exec mailserver-dovecot doveconf -n | grep -E '(mail_location|auth_mechanisms)'

# 4. ログ確認
docker logs mailserver-postfix --tail 50
docker logs mailserver-dovecot --tail 50
docker logs mailserver-mariadb --tail 50
```

### 7.4 メール送受信テスト

#### 7.4.1 送信テスト（Dell → 外部）

```bash
# 1. テストメール送信
docker exec -it mailserver-postfix bash -c "
echo 'Test mail from restored server' | \
  mail -s 'Test: Outbound Mail' external-test@gmail.com
"

# 2. ログ確認
docker logs mailserver-postfix | grep -A 5 "external-test@gmail.com"

# 3. SendGrid確認（EC2経由）
# SendGridダッシュボードで送信統計を確認
```

#### 7.4.2 受信テスト（外部 → Dell）

```bash
# 1. 外部からテストメール送信
# Gmail等から test@your-domain.com にメール送信

# 2. EC2 Postfixログ確認
ssh ec2-user@your-ec2-instance
sudo docker logs mailserver-postfix | tail -50

# 3. Dell Dovecotログ確認
docker logs mailserver-dovecot | tail -50

# 4. メールボックス確認
# ホストディレクトリ（bind mount先）
sudo ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/your-domain.com/test/new/
```

#### 7.4.3 IMAP接続テスト

```bash
# 1. IMAPクライアント設定
# Thunderbird / Outlook / macOS Mail 等で設定
# - サーバー: dell-mailserver.your-tailnet.ts.net
# - ポート: 993（IMAPS）
# - 認証: test@your-domain.com / password
# - TLS: 必須

# 2. コマンドラインテスト
openssl s_client -connect dell-mailserver.your-tailnet.ts.net:993 <<EOF
a001 LOGIN test@your-domain.com password
a002 LIST "" "*"
a003 SELECT INBOX
a004 FETCH 1:* (FLAGS)
a005 LOGOUT
EOF
```

### 7.5 バックアップ機能確認

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. ローカルバックアップ実行
./backup-mailserver.sh --daily

# 2. S3アップロード実行
./backup-to-s3.sh

# 3. バックアップ確認
aws s3 ls s3://$(cd ../terraform/s3-backup && terraform output -raw s3_bucket_name)/daily/ \
  --profile mailserver-backup-admin

# 4. マルウェアスキャン実行
./scan-mailserver.sh --daily

# 5. ログ確認
tail -100 /var/log/mailserver-backup/s3-backup.log
tail -50 /var/log/clamav/daily-scan.log
```

### 7.6 監視・アラート確認

```bash
# 1. CloudWatch Alarms確認
aws cloudwatch describe-alarms \
  --alarm-names mailserver-s3-backup-cost-warning mailserver-s3-backup-cost-critical \
  --region us-east-1 \
  --profile mailserver-backup

# 2. SNS Subscription確認
aws sns list-subscriptions-by-topic \
  --topic-arn $(cd ../terraform/s3-backup && terraform output -raw sns_topic_arn) \
  --region us-east-1 \
  --profile mailserver-backup

# 3. テストアラート送信
aws sns publish \
  --topic-arn $(cd ../terraform/s3-backup && terraform output -raw sns_topic_arn) \
  --subject "Test: Recovery Verification" \
  --message "Mailserver recovery completed successfully" \
  --region us-east-1 \
  --profile mailserver-backup
```

### 7.7 パフォーマンス確認

```bash
# 1. システムリソース
top -b -n 1 | head -20
free -h
df -h

# 2. Dockerリソース使用量
docker stats --no-stream

# 3. ネットワークスループット
sudo iftop -i enp1s0 -t -s 10

# 4. メール処理性能
# Postfix キュー確認
docker exec mailserver-postfix mailq

# 5. データベースパフォーマンス
docker exec -it mailserver-mariadb mysql -u root -p -e "SHOW PROCESSLIST;"
```

---

## 8. トラブルシューティング

### 8.1 復旧中のよくある問題

#### 8.1.1 Github クローン失敗

**症状**:
```
Permission denied (publickey).
fatal: Could not read from remote repository.
```

**原因**: SSH鍵が設定されていない、または権限が不正

**解決策**:

```bash
# 1. SSH鍵生成（新規の場合）
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. 公開鍵をGithubに登録
cat ~/.ssh/id_ed25519.pub
# → Githubの Settings → SSH and GPG keys → New SSH key

# 3. SSH接続確認
ssh -T git@github.com

# 4. パーミッション修正
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

#### 8.1.2 Docker起動失敗

**症状**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**原因**: Dockerサービスが起動していない

**解決策**:

```bash
# 1. Docker状態確認
sudo systemctl status docker

# 2. Docker起動
sudo systemctl start docker
sudo systemctl enable docker

# 3. ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
newgrp docker

# 4. 動作確認
docker ps
```

#### 8.1.3 S3アクセス拒否

**症状**:
```
An error occurred (AccessDenied) when calling the ListObjectsV2 operation
```

**原因**: AWS認証情報が設定されていない、または権限不足

**解決策**:

```bash
# 1. AWS CLI設定確認
aws configure list --profile mailserver-backup-admin

# 2. 認証情報再設定
aws configure --profile mailserver-backup-admin
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: ap-northeast-1
# Default output format: json

# 3. 認証確認
aws sts get-caller-identity --profile mailserver-backup-admin

# 4. S3アクセス確認
aws s3 ls --profile mailserver-backup-admin
```

#### 8.1.4 データベース接続失敗

**症状**:
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

**原因**: パスワードが間違っている、または.envファイルが読み込まれていない

**解決策**:

```bash
# 1. .envファイル確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
cat .env | grep -E '(MYSQL_ROOT_PASSWORD|MYSQL_PASSWORD|USERMGMT_DB_PASSWORD)'

# 2. パスワード再設定
vim .env
# → パスワードを正しい値に修正

# 3. コンテナ再起動
docker-compose restart mariadb

# 4. 接続確認
docker exec -it mailserver-mariadb mysql -u root -p
# → .env の MYSQL_ROOT_PASSWORD を入力
```

#### 8.1.5 メール送信失敗（Relay access denied）

**症状**:
```
Relay access denied
```

**原因**: EC2側の relay_domains にドメインが登録されていない

**解決策**:

```bash
# 1. EC2にSSH接続
ssh ec2-user@your-ec2-instance

# 2. Postfix設定確認
sudo docker exec mailserver-postfix postconf relay_domains

# 3. relay_domainsにドメイン追加
sudo docker exec -it mailserver-postfix bash
postconf -e "relay_domains = your-domain.com, another-domain.com"
exit

# 4. Postfix再起動
sudo docker restart mailserver-postfix

# 5. 送信テスト
# Dell側から再度メール送信
```

#### 8.1.6 TLS証明書エラー

**症状**:
```
SSL/TLS certificate verification failed
```

**原因**: 証明書が期限切れ、またはパスが間違っている

**解決策**:

```bash
# 1. 証明書確認
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -noout -dates

# 2. Tailscale証明書で再取得
sudo tailscale cert dell-mailserver.your-tailnet.ts.net

# 3. .envファイルのパス更新
vim /opt/onprem-infra-system/project-root-infra/services/mailserver/.env
# → TLS_CERT_PATH, TLS_KEY_PATH を更新

# 4. サービス再起動
docker-compose restart postfix dovecot

# 5. 証明書パーミッション確認
sudo ls -l /etc/letsencrypt/live/your-domain.com/
sudo chmod 644 /etc/letsencrypt/live/your-domain.com/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 8.2 リストア失敗時の対処

#### 8.2.1 チェックサム検証失敗

**症状**:
```
ERROR: Checksum verification failed
```

**原因**: ダウンロード中にデータが破損した

**解決策**:

```bash
# 1. ダウンロード一時ファイル削除
sudo rm -rf /tmp/s3-restore-*

# 2. 別の日付のバックアップを試す
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
BACKUP_DATE="2025-11-06"  # 前日のバックアップ
./restore-from-s3.sh --date "${BACKUP_DATE}" --component all

# 3. 手動ダウンロードで確認
aws s3 cp "s3://${S3_BUCKET}/daily/${BACKUP_DATE}/checksums.sha256" /tmp/ \
  --profile mailserver-backup-admin
cat /tmp/checksums.sha256
```

#### 8.2.2 マルウェア検出

**症状**:
```
ERROR: Malware detected in backup
```

**原因**: バックアップデータにマルウェアが含まれている

**解決策**:

```bash
# 1. 検出ファイル確認
tail -100 /var/log/clamav/restore-scan.log | grep FOUND

# 2. より古いバックアップから復旧
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
BACKUP_DATE="2025-11-05"  # さらに前のバックアップ
./restore-from-s3.sh --date "${BACKUP_DATE}" --component all

# 3. 感染ファイルを特定して除外
# 手動リストアでマルウェアファイルをスキップ

# 4. セキュリティ調査
# 感染原因の特定と対策
```

#### 8.2.3 ディスク容量不足

**症状**:
```
No space left on device
```

**原因**: ディスク容量が不足している

**解決策**:

```bash
# 1. ディスク使用状況確認
df -h

# 2. 不要なDockerリソース削除
docker system prune -af --volumes
# 警告: すべての停止コンテナ、未使用イメージ、ボリュームが削除されます

# 3. 古いバックアップ削除
sudo rm -rf /mnt/backup-hdd/mailserver/daily/2025-10-*

# 4. ログファイル削除
sudo journalctl --vacuum-time=7d
sudo find /var/log -name "*.log" -mtime +30 -delete

# 5. 容量確保後、再試行
./restore-from-s3.sh --component all
```

### 8.3 緊急連絡先

**システム管理者**:
- メール: admin@your-domain.com
- 電話: XXX-XXXX-XXXX

**エスカレーションフロー**:
1. トラブルシューティングセクション参照（本文書）
2. ログ収集・状況整理
3. システム管理者に連絡
4. 必要に応じて外部サポート（AWS Support等）

**ログ収集スクリプト**:

```bash
#!/bin/bash
# 緊急時ログ収集スクリプト

LOG_DIR="/tmp/mailserver-emergency-logs-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${LOG_DIR}"

# システムログ
sudo journalctl -xe > "${LOG_DIR}/journalctl.log"
dmesg > "${LOG_DIR}/dmesg.log"

# Dockerログ
docker-compose logs > "${LOG_DIR}/docker-compose.log"
docker ps -a > "${LOG_DIR}/docker-ps.log"

# サービスログ
docker logs mailserver-postfix > "${LOG_DIR}/postfix.log" 2>&1
docker logs mailserver-dovecot > "${LOG_DIR}/dovecot.log" 2>&1
docker logs mailserver-mariadb > "${LOG_DIR}/mysql.log" 2>&1

# バックアップログ
cp /var/log/mailserver-backup/s3-backup.log "${LOG_DIR}/" 2>/dev/null || true
cp /var/log/clamav/daily-scan.log "${LOG_DIR}/" 2>/dev/null || true

# システム情報
df -h > "${LOG_DIR}/disk-usage.log"
free -h > "${LOG_DIR}/memory-usage.log"
top -b -n 1 > "${LOG_DIR}/top.log"

# 圧縮
tar -czf "${LOG_DIR}.tar.gz" -C /tmp "$(basename ${LOG_DIR})"
echo "Logs collected: ${LOG_DIR}.tar.gz"
```

---

## 9. 付録

### A. 復旧チェックリスト

#### A.1 完全障害復旧チェックリスト

- [ ] **事前準備**
  - [ ] ハードウェア準備完了
  - [ ] OS インストール完了（Rocky Linux 9.6）
  - [ ] ネットワーク設定完了
  - [ ] system-admin ユーザー作成完了
  - [ ] SSH鍵設定完了

- [ ] **Phase 3: システム基盤**
  - [ ] Docker インストール完了
  - [ ] Docker Compose インストール完了
  - [ ] ストレージマウント完了
  - [ ] Docker データディレクトリ設定完了

- [ ] **シナリオ1: IaC復旧（Github）**
  - [ ] Githubリポジトリクローン完了
  - [ ] 環境変数設定完了（.env, ~/.bashrc）
  - [ ] Docker Compose 起動完了
  - [ ] すべてのコンテナが Up 状態

- [ ] **シナリオ2: データ復旧（S3）**
  - [ ] AWS CLI設定完了
  - [ ] S3バックアップ一覧確認完了
  - [ ] restore-from-s3.sh 実行完了
  - [ ] データリストア完了（メール、MySQL）

- [ ] **検証**
  - [ ] サービス疎通確認完了
  - [ ] データ整合性確認完了
  - [ ] メール送信テスト成功
  - [ ] メール受信テスト成功
  - [ ] IMAP接続テスト成功
  - [ ] バックアップ機能確認完了
  - [ ] 監視・アラート確認完了

- [ ] **本番切り替え**
  - [ ] DNS切り戻し（必要な場合）
  - [ ] ユーザーへの通知
  - [ ] 運用監視開始

#### A.2 部分復旧チェックリスト

**メールデータ復旧**:
- [ ] Dovecot停止
- [ ] メールデータリストア
- [ ] Dovecot起動
- [ ] IMAP接続確認

**データベース復旧**:
- [ ] MySQL停止
- [ ] データバックアップ（念のため）
- [ ] MySQLデータベースリストア
- [ ] MySQL起動
- [ ] データベース確認
- [ ] 依存サービス再起動

**設定ファイル復旧**:
- [ ] 現在の設定バックアップ
- [ ] 設定ファイルリストア（S3 or Github）
- [ ] サービス再起動
- [ ] 設定確認
- [ ] 疎通テスト

### B. RTO/RPO 目標値

| 障害レベル | RTO | RPO | 復旧シナリオ |
|-----------|-----|-----|------------|
| **Level 1: サービス停止** | 30分 | 0時間 | サービス再起動のみ |
| **Level 2: 設定破損** | 1時間 | 0時間 | 設定ファイル復旧（Github） |
| **Level 3: データ破損** | 2時間 | 24時間 | データ復旧（S3） |
| **Level 4: 部分障害** | 2時間 | 24時間 | コンポーネント別復旧 |
| **Level 5: 完全障害** | 4時間 | 24時間 | 完全復旧（Github + S3） |

### C. 参考ドキュメント

- [docs/infra/README.md](../../infra/README.md) - インフラ構築手順
- [docs/application/mailserver/README.md](../README.md) - Mailserver概要
- [03_implementation.md](03_implementation.md) - Phase 10実装ガイド
- [07_s3backup_implementation.md](07_s3backup_implementation.md) - Phase 11-B実装ガイド
- [services/mailserver/troubleshoot/README.md](../../../services/mailserver/troubleshoot/README.md) - トラブルシューティング

### D. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成（リカバリー手順書） | system-admin |
| 1.1 | 2025-11-07 | S3構造修正（単一tarファイル→ディレクトリ単位）、リストア先パス修正（Dockerボリューム→ホストbind mount）、コンテナ名/サービス名修正（mysql→mariadb） | system-admin |

---

**END OF DOCUMENT**
