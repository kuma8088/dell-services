# メールサーバーリカバリー手順書

**作成日**: 2025-11-07
**バージョン**: 1.1
**対象システム**: Dell Mailserver (Docker Compose 環境)
**前提ドキュメント**: [01_requirements.md](./01_requirements.md), [02_design.md](./02_design.md), [03_implementation.md](./03_implementation.md)

**変更履歴**:
- v1.1 (2025-11-07): ファイル名修正 - `.env`ファイルパスを`config/.env`→`config/env`に修正、DKIMアーカイブ名を`opendkim-keys.tar.gz`→`dkim.tar.gz`に修正、SSL証明書リストアに存在確認を追加

---

## 📋 目次

1. [リカバリー前の確認事項](#1-リカバリー前の確認事項)
2. [シナリオ1: 完全リカバリー（ハードウェア故障）](#2-シナリオ1-完全リカバリーハードウェア故障)
3. [シナリオ2: メールデータのみリカバリー](#3-シナリオ2-メールデータのみリカバリー)
4. [シナリオ3: データベースのみリカバリー](#4-シナリオ3-データベースのみリカバリー)
5. [シナリオ4: 設定ファイルのみリカバリー](#5-シナリオ4-設定ファイルのみリカバリー)
6. [シナリオ5: SSL証明書/DKIM鍵のみリカバリー](#6-シナリオ5-ssl証明書dkim鍵のみリカバリー)
7. [リカバリー検証手順](#7-リカバリー検証手順)
8. [ロールバック手順](#8-ロールバック手順)
9. [トラブルシューティング](#9-トラブルシューティング)

---

## 1. リカバリー前の確認事項

### 1.1 バックアップの確認

```bash
# 1. 利用可能なバックアップの確認
ls -lh /mnt/backup-hdd/mailserver/daily/
ls -lh /mnt/backup-hdd/mailserver/weekly/

# 2. 最新バックアップの確認
ls -lh /mnt/backup-hdd/mailserver/latest/

# 3. バックアップ内容の確認
cat /mnt/backup-hdd/mailserver/latest/backup.log

# 4. バックアップ日時の確認
BACKUP_DATE=$(readlink /mnt/backup-hdd/mailserver/latest | cut -d'/' -f2)
echo "バックアップ日時: ${BACKUP_DATE}"
```

### 1.2 バックアップ整合性の検証

```bash
# チェックサムによる検証
cd /mnt/backup-hdd/mailserver/latest/
sha256sum -c checksums.sha256

# 期待される結果: 全てのファイルで "OK" が表示される
```

### 1.3 リカバリー対象の決定

| リカバリー範囲 | 対象コンポーネント | ダウンタイム | 難易度 |
|-------------|-----------------|------------|--------|
| **完全リカバリー** | 全て | 2-4時間 | 🔴 高 |
| **メールデータ** | mail/ | 30分-1時間 | 🟡 中 |
| **データベース** | MySQL | 10-30分 | 🟡 中 |
| **設定ファイル** | config/ | 10-20分 | 🟢 低 |
| **SSL/DKIM** | ssl/, dkim/ | 5-10分 | 🟢 低 |

### 1.4 事前準備

```bash
# 1. 作業ディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 2. 現在の状態を記録
docker compose ps > /tmp/pre-recovery-status.txt
df -h > /tmp/pre-recovery-disk.txt

# 3. リストアスクリプトの存在確認
ls -l scripts/restore-mailserver.sh

# 4. バックアップソースの指定
export BACKUP_SOURCE="/mnt/backup-hdd/mailserver/latest"
```

---

## 2. シナリオ1: 完全リカバリー（ハードウェア故障）

**想定状況**: サーバー全体が故障し、新しいハードウェアで復旧する

**所要時間**: 2-4時間

**前提条件**:
- 新しいハードウェアに Rocky Linux 9.6 がインストール済み
- 外付けHDDがアクセス可能

### 2.1 OS環境の準備

```bash
# 1. システムパッケージの更新
sudo dnf update -y

# 2. 必要なツールのインストール
sudo dnf install -y git rsync mysql tar gzip

# 3. Docker のインストール
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker

# 4. ユーザーを docker グループに追加
sudo usermod -aG docker system-admin
newgrp docker

# 5. Docker 確認
docker --version
docker compose version
```

### 2.2 外付けHDDのマウント

```bash
# 1. デバイスの確認
lsblk

# 2. マウントポイント作成
sudo mkdir -p /mnt/backup-hdd

# 3. マウント
sudo mount /dev/sda1 /mnt/backup-hdd

# 4. fstab への追加（恒久化）
UUID=$(sudo blkid /dev/sda1 -s UUID -o value)
echo "UUID=${UUID}  /mnt/backup-hdd  ext4  defaults,nofail  0  2" | sudo tee -a /etc/fstab

# 5. マウント確認
df -h /mnt/backup-hdd
```

### 2.3 プロジェクトディレクトリの準備

```bash
# 1. プロジェクトルート作成
sudo mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver

# 2. 所有権変更
sudo chown -R system-admin:system-admin /opt/onprem-infra-system

# 3. ディレクトリ移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
```

### 2.4 設定ファイルのリストア

```bash
# 1. バックアップソース指定
export BACKUP_SOURCE="/mnt/backup-hdd/mailserver/latest"

# 2. 設定ファイルリストア
tar -xzf "${BACKUP_SOURCE}/config/config.tar.gz" -C /opt/onprem-infra-system/project-root-infra/services/mailserver/

# 3. docker-compose.yml リストア
cp "${BACKUP_SOURCE}/config/docker-compose.yml" ./docker-compose.yml

# 4. .env ファイルリストア
cp "${BACKUP_SOURCE}/config/env" ./.env
chmod 600 ./.env

# 5. 設定確認
ls -la config/
ls -la docker-compose.yml .env
```

### 2.5 SSL証明書とDKIM鍵のリストア

```bash
# 1. SSL証明書リストア（存在する場合）
if [ -f "${BACKUP_SOURCE}/ssl/certbot.tar.gz" ]; then
    mkdir -p data/certbot
    tar -xzf "${BACKUP_SOURCE}/ssl/certbot.tar.gz" -C data/
    ls -la data/certbot/live/
fi

# 2. DKIM鍵リストア
# config/opendkim/ ディレクトリに展開（tar は opendkim/ 基準で作成されている）
mkdir -p config/opendkim
tar -xzf "${BACKUP_SOURCE}/dkim/dkim.tar.gz" -C config/opendkim/

# 代替方法: リストアスクリプトを使用（推奨）
# /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh \
#   --from "${BACKUP_SOURCE}" --component dkim

# 3. パーミッション確認
ls -la config/opendkim/keys/
```

### 2.6 メールデータのリストア

```bash
# 1. メールデータディレクトリ作成
mkdir -p data/mail

# 2. rsync でリストア
rsync -av "${BACKUP_SOURCE}/mail/" data/mail/

# 3. 所有権とパーミッション設定
sudo chown -R 5000:5000 data/mail
sudo chmod -R 700 data/mail

# 4. リストア確認
du -sh data/mail/
ls -la data/mail/vmail/
```

### 2.7 Docker Compose起動

```bash
# 1. Docker Compose 起動
docker compose up -d

# 2. コンテナ起動確認
docker compose ps

# 期待される結果: 全コンテナが "Up" 状態

# 3. ログ確認
docker compose logs -f --tail=50
```

### 2.8 データベースのリストア

```bash
# 1. MariaDB コンテナ稼働確認
docker ps | grep mailserver-mariadb

# 2. データベースの準備（既存DBを削除して再作成）
docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" <<EOF
DROP DATABASE IF EXISTS usermgmt;
DROP DATABASE IF EXISTS roundcubemail;
CREATE DATABASE usermgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE roundcubemail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# 3. usermgmt データベースリストア
gunzip -c "${BACKUP_SOURCE}/mysql/usermgmt.sql.gz" | \
    docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" usermgmt

# 4. roundcubemail データベースリストア
gunzip -c "${BACKUP_SOURCE}/mysql/roundcubemail.sql.gz" | \
    docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" roundcubemail

# 5. リストア確認
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" -e "SHOW DATABASES;"
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" -e "USE usermgmt; SHOW TABLES;"
```

### 2.9 サービス再起動と確認

```bash
# 1. 全サービス再起動
docker compose restart

# 2. ヘルスチェック
docker compose ps
docker compose logs --tail=100

# 3. 次の検証セクションへ
```

---

## 3. シナリオ2: メールデータのみリカバリー

**想定状況**: メールデータが破損または誤削除された

**所要時間**: 30分-1時間

**前提条件**:
- Docker Compose 環境が稼働中
- バックアップが利用可能

### 3.1 現在のメールデータのバックアップ

```bash
# 1. 現在のメールデータを退避
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo mv data/mail data/mail.backup.${TIMESTAMP}

# 2. 退避確認
ls -la data/mail.backup.${TIMESTAMP}/
```

### 3.2 restore-mailserver.sh を使用したリストア

```bash
# 1. スクリプトによるリストア
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component mail

# 2. リストア確認
du -sh ../data/mail/
ls -la ../data/mail/vmail/

# 3. パーミッション確認
ls -ld ../data/mail/
# Expected: drwx------ 5000:5000
```

### 3.3 サービス再起動

```bash
# 1. Dovecot 再起動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose restart mailserver-dovecot

# 2. ログ確認
docker compose logs -f mailserver-dovecot
```

---

## 4. シナリオ3: データベースのみリカバリー

**想定状況**: データベースが破損またはデータ不整合が発生

**所要時間**: 10-30分

**前提条件**:
- Docker Compose 環境が稼働中
- バックアップが利用可能

### 4.1 現在のデータベースのバックアップ

```bash
# 1. 現在のDBをダンプ（念のため）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /tmp/db-backup-${TIMESTAMP}

docker exec mailserver-mariadb mysqldump -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" \
    --single-transaction usermgmt | gzip > /tmp/db-backup-${TIMESTAMP}/usermgmt.sql.gz

docker exec mailserver-mariadb mysqldump -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" \
    --single-transaction roundcubemail | gzip > /tmp/db-backup-${TIMESTAMP}/roundcubemail.sql.gz

# 2. バックアップ確認
ls -lh /tmp/db-backup-${TIMESTAMP}/
```

### 4.2 restore-mailserver.sh を使用したリストア

```bash
# 1. スクリプトによるリストア
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component mysql

# 2. リストア確認
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD ../..env | cut -d'=' -f2)" \
    -e "SELECT COUNT(*) FROM usermgmt.users;"

docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD ../.env | cut -d'=' -f2)" \
    -e "SELECT COUNT(*) FROM roundcubemail.users;"
```

### 4.3 アプリケーション再起動

```bash
# 1. usermgmt 再起動
docker compose restart mailserver-usermgmt

# 2. Roundcube 再起動
docker compose restart mailserver-roundcube

# 3. ログ確認
docker compose logs -f mailserver-usermgmt mailserver-roundcube
```

---

## 5. シナリオ4: 設定ファイルのみリカバリー

**想定状況**: 設定ファイルが誤編集または破損

**所要時間**: 10-20分

**前提条件**:
- バックアップが利用可能

### 5.1 現在の設定のバックアップ

```bash
# 1. 現在の設定を退避
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
tar -czf /tmp/config-backup-${TIMESTAMP}.tar.gz config/ docker-compose.yml .env

# 2. バックアップ確認
ls -lh /tmp/config-backup-${TIMESTAMP}.tar.gz
```

### 5.2 restore-mailserver.sh を使用したリストア

```bash
# 1. スクリプトによるリストア
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component config

# 2. リストア確認
ls -la ../config/
ls -la ../docker-compose.yml ../.env
```

### 5.3 設定の反映

```bash
# 1. Docker Compose 設定確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose config

# 2. 全サービス再起動
docker compose restart

# 3. 起動確認
docker compose ps
```

---

## 6. シナリオ5: SSL証明書/DKIM鍵のみリカバリー

**想定状況**: 証明書・鍵ファイルが失われた

**所要時間**: 5-10分

**前提条件**:
- バックアップが利用可能

### 6.1 SSL証明書のリストア

```bash
# 1. 現在の証明書を退避
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
sudo mv data/certbot data/certbot.backup.${TIMESTAMP}

# 2. スクリプトによるリストア
cd scripts
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component ssl

# 3. リストア確認
ls -la ../data/certbot/live/
ls -la ../data/certbot/renewal/
```

### 6.2 DKIM鍵のリストア

```bash
# 1. 現在のDKIM鍵を退避
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
sudo mv config/opendkim config/opendkim.backup.${TIMESTAMP}

# 2. スクリプトによるリストア
cd scripts
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest --component dkim

# 3. リストア確認
ls -la ../config/opendkim/keys/
```

### 6.3 関連サービス再起動

```bash
# 1. Postfix 再起動（SSL）
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose restart mailserver-postfix

# 2. OpenDKIM 再起動（DKIM）
docker compose restart mailserver-opendkim

# 3. ログ確認
docker compose logs -f mailserver-postfix mailserver-opendkim
```

---

## 7. リカバリー検証手順

### 7.1 システムレベル検証

```bash
# 1. 全コンテナ稼働確認
docker compose ps
# Expected: 全コンテナが "Up" 状態

# 2. ディスク使用量確認
df -h
du -sh data/mail/

# 3. ログエラー確認
docker compose logs --tail=100 | grep -i error
```

### 7.2 メール送受信テスト

```bash
# 1. SMTP接続テスト
telnet localhost 587
# 入力: EHLO test.example.com
# 期待: 250-mail.example.com の応答

# 2. IMAP接続テスト
telnet localhost 143
# 入力: a001 LOGIN testuser@example.com password
# 期待: a001 OK の応答

# 3. テストメール送信（curl使用）
curl --url 'smtp://localhost:587' \
     --ssl-reqd \
     --mail-from 'test@example.com' \
     --mail-rcpt 'recipient@example.com' \
     --user 'test@example.com:password' \
     --upload-file - <<EOF
From: test@example.com
To: recipient@example.com
Subject: Recovery Test

This is a recovery test email.
EOF
```

### 7.3 Webメール動作確認

```bash
# 1. Roundcube アクセス確認
curl -I http://localhost/roundcube/
# Expected: HTTP/1.1 200 OK

# 2. ブラウザでアクセス
# URL: http://mail.example.com/roundcube/
# ログイン: testuser@example.com / password
# 確認: メールボックスが表示される
```

### 7.4 User Management API確認

```bash
# 1. API ヘルスチェック
curl http://localhost:5001/health
# Expected: {"status": "healthy"}

# 2. ユーザー一覧取得テスト
curl -X GET http://localhost:5001/api/users \
     -H "Content-Type: application/json"
# Expected: ユーザーリストのJSON
```

### 7.5 データベース整合性確認

```bash
# 1. usermgmt テーブル確認
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" \
    -e "SELECT COUNT(*) AS user_count FROM usermgmt.users;"

# 2. roundcubemail テーブル確認
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" \
    -e "SELECT COUNT(*) AS user_count FROM roundcubemail.users;"

# 3. 外部キー制約確認
docker exec mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" \
    -e "SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_TYPE = 'FOREIGN KEY' AND TABLE_SCHEMA = 'usermgmt';"
```

---

## 8. ロールバック手順

### 8.1 リカバリー失敗時のロールバック

**状況**: リカバリーが失敗し、元の状態に戻す必要がある

```bash
# 1. Docker Compose 停止
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose down

# 2. リストアしたデータを削除
sudo rm -rf data/mail
sudo rm -rf config/

# 3. バックアップから復元
TIMESTAMP="20251107_143022"  # 実際のタイムスタンプに置き換え
sudo mv data/mail.backup.${TIMESTAMP} data/mail
tar -xzf /tmp/config-backup-${TIMESTAMP}.tar.gz -C .

# 4. Docker Compose 再起動
docker compose up -d

# 5. 状態確認
docker compose ps
```

### 8.2 データベースロールバック

```bash
# 1. リストアしたDBを削除
docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" <<EOF
DROP DATABASE IF EXISTS usermgmt;
DROP DATABASE IF EXISTS roundcubemail;
CREATE DATABASE usermgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE roundcubemail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# 2. 退避したDBから復元
TIMESTAMP="20251107_143022"  # 実際のタイムスタンプに置き換え
gunzip -c /tmp/db-backup-${TIMESTAMP}/usermgmt.sql.gz | \
    docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" usermgmt

gunzip -c /tmp/db-backup-${TIMESTAMP}/roundcubemail.sql.gz | \
    docker exec -i mailserver-mariadb mysql -u root -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)" roundcubemail

# 3. アプリケーション再起動
docker compose restart
```

---

## 9. トラブルシューティング

### 9.1 リストアスクリプトが失敗する

**症状**:
```
Error: Backup directory not found
```

**対処**:
```bash
# 1. バックアップパス確認
ls -la /mnt/backup-hdd/mailserver/latest/
readlink /mnt/backup-hdd/mailserver/latest

# 2. パスを明示的に指定
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/2025-11-07 --component all

# 3. パーミッション確認
ls -ld /mnt/backup-hdd/mailserver/
# Expected: drwx------ system-admin
```

### 9.2 データベースリストアが失敗する

**症状**:
```
ERROR 1044 (42000): Access denied for user 'root'@'localhost' to database 'usermgmt'
```

**対処**:
```bash
# 1. MySQL root パスワード確認
grep MYSQL_ROOT_PASSWORD /opt/onprem-infra-system/project-root-infra/services/mailserver/.env

# 2. MariaDB コンテナ内で直接実行
docker exec -it mailserver-mariadb mysql -u root -p

# 3. データベース作成確認
SHOW DATABASES;

# 4. 権限確認
SHOW GRANTS FOR 'root'@'localhost';
```

### 9.3 メールデータのパーミッションエラー

**症状**:
```
Permission denied: /var/mail/vmail/example.com/user1/
```

**対処**:
```bash
# 1. 所有権確認
ls -la data/mail/vmail/

# 2. 所有権修正
sudo chown -R 5000:5000 data/mail/
sudo chmod -R 700 data/mail/

# 3. Dovecot 再起動
docker compose restart mailserver-dovecot

# 4. ログ確認
docker compose logs -f mailserver-dovecot
```

### 9.4 SSL証明書エラー

**症状**:
```
SSL certificate problem: unable to get local issuer certificate
```

**対処**:
```bash
# 1. 証明書ファイル確認
ls -la data/certbot/live/mail.example.com/
# Expected: fullchain.pem, privkey.pem

# 2. 証明書有効期限確認
openssl x509 -in data/certbot/live/mail.example.com/fullchain.pem -noout -dates

# 3. Postfix 設定確認
docker exec mailserver-postfix postconf | grep smtpd_tls_cert_file

# 4. Postfix 再起動
docker compose restart mailserver-postfix
```

### 9.5 DKIM署名エラー

**症状**:
```
dkim=fail (signature verification failed)
```

**対処**:
```bash
# 1. DKIM鍵ファイル確認
ls -la config/opendkim/keys/mail.example.com/
# Expected: default.private, default.txt

# 2. KeyTable 確認
cat config/opendkim/KeyTable

# 3. DNS レコード確認
dig default._domainkey.mail.example.com TXT

# 4. OpenDKIM 再起動
docker compose restart mailserver-opendkim

# 5. ログ確認
docker compose logs -f mailserver-opendkim
```

### 9.6 Docker Compose 起動失敗

**症状**:
```
Error: service "mailserver-mysql" is not running
```

**対処**:
```bash
# 1. docker-compose.yml 構文確認
docker compose config

# 2. コンテナ名確認（mysql vs mariadb）
grep "container_name.*mariadb" docker-compose.yml

# 3. ボリューム確認
docker volume ls | grep mailserver

# 4. ログ詳細確認
docker compose logs mailserver-mariadb

# 5. 強制再作成
docker compose down -v
docker compose up -d
```

---

## 📝 付録

### A. リカバリーチェックリスト

**完全リカバリー**:
- [ ] OS環境準備完了
- [ ] Docker インストール完了
- [ ] 外付けHDD マウント完了
- [ ] プロジェクトディレクトリ作成完了
- [ ] 設定ファイルリストア完了
- [ ] SSL証明書リストア完了
- [ ] DKIM鍵リストア完了
- [ ] メールデータリストア完了
- [ ] Docker Compose 起動完了
- [ ] データベースリストア完了
- [ ] メール送受信テスト成功
- [ ] Webメールアクセス成功
- [ ] User Management API動作確認

**部分リカバリー**:
- [ ] 現在のデータバックアップ完了
- [ ] restore-mailserver.sh 実行成功
- [ ] サービス再起動完了
- [ ] 動作確認成功
- [ ] ログエラーなし

### B. 緊急連絡先

| 役割 | 担当者 | 連絡先 |
|-----|-------|--------|
| **システム管理者** | system-admin | naoya.iimura@gmail.com |
| **バックアップ管理** | system-admin | naoya.iimura@gmail.com |
| **障害対応** | system-admin | naoya.iimura@gmail.com |

### C. 関連ドキュメント

- [01_requirements.md](./01_requirements.md) - 要件定義書
- [02_design.md](./02_design.md) - 設計書
- [03_implementation.md](./03_implementation.md) - 実装ガイド
- [Mailserver README](../README.md) - Mailserver全体ドキュメント
- [Troubleshooting Guide](../../../services/mailserver/troubleshoot/README.md) - トラブルシューティング

### D. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成 | system-admin |

---

**END OF DOCUMENT**
