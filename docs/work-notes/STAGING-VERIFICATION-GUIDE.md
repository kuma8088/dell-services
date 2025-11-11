# Staging環境検証ガイド - リポジトリ改善項目

**作成日**: 2025-11-11
**対象**: オンプレミスDell WorkStation (Rocky Linux 9.6)
**前提**: Docker Compose環境構築済み

---

## 📋 目次

1. [Staging環境構築手順](#1-staging環境構築手順)
2. [検証が必要な改善項目](#2-検証が必要な改善項目)
3. [検証手順](#3-検証手順)
4. [ロールバック手順](#4-ロールバック手順)
5. [トラブルシューティング](#5-トラブルシューティング)

---

## 1. Staging環境構築手順

### 1-1. 前提条件確認

```bash
# システム確認
cat /etc/redhat-release
# Expected: Rocky Linux release 9.6

# Docker確認
docker --version
docker compose version

# 現在の本番環境確認
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose ps
```

### 1-2. Staging環境の選択肢

#### **Option A: 同一ホスト上でポート分離（推奨）** ⭐

**メリット**:
- ✅ 追加ハードウェア不要
- ✅ 本番環境と同じOS/カーネル
- ✅ セットアップ15分

**構成**:
```
Dell WorkStation
├── Production (既存)
│   ├── blog_network: 172.22.0.0/24
│   ├── Nginx: 8080
│   └── MariaDB: 3307
│
└── Staging (新規)
    ├── blog_staging_network: 172.23.0.0/24
    ├── Nginx: 8081
    └── MariaDB: 3308
```

**セットアップ手順**:

```bash
# 1. Stagingディレクトリ作成
cd /opt/onprem-infra-system/project-root-infra/services
cp -r blog blog-staging

# 2. docker-compose.yml修正
cd blog-staging
vi docker-compose.yml
```

`docker-compose.yml` 修正内容:
```yaml
version: '3.8'

services:
  nginx:
    container_name: blog-staging-nginx
    ports:
      - "8081:80"  # 本番は8080
    networks:
      blog_staging_network:
        ipv4_address: 172.23.0.10

  wordpress:
    container_name: blog-staging-wordpress
    networks:
      blog_staging_network:
        ipv4_address: 172.23.0.20

  mariadb:
    container_name: blog-staging-mariadb
    ports:
      - "3308:3306"  # 本番は3307
    networks:
      blog_staging_network:
        ipv4_address: 172.23.0.50

  cloudflared:
    container_name: blog-staging-cloudflared
    # コメントアウト（Staging環境では不要）
    # または別トンネル設定

networks:
  blog_staging_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.23.0.0/24
```

```bash
# 3. .env作成
cp ../blog/.env .env.staging
vi .env.staging
# MYSQL_ROOT_PASSWORDなど必要に応じて変更

# 4. データディレクトリ作成
mkdir -p /mnt/backup-hdd/blog-staging/sites

# 5. 起動
docker compose -f docker-compose.yml --env-file .env.staging up -d

# 6. 確認
docker compose ps
curl http://localhost:8081
```

#### **Option B: 個別設定ファイルでの検証（最小限）**

テスト用Nginx設定のみを別ファイルで作成:

```bash
# Nginx設定のテスト版作成
cd /opt/onprem-infra-system/project-root-infra/services/blog/config/nginx/conf.d
cp kuma8088.conf kuma8088.test.conf

# 修正実施
vi kuma8088.test.conf

# Nginxコンテナ内でテスト
docker compose exec nginx nginx -t -c /etc/nginx/nginx.conf

# テスト設定を反映（リスクあり、Option Aを推奨）
docker compose exec nginx nginx -s reload
```

---

## 2. 検証が必要な改善項目

以下の5項目はStaging環境での検証が必須です。

| # | 項目 | 優先度 | 影響範囲 | 所要時間 |
|---|------|--------|---------|---------|
| **#2** | Nginx HTTPS パラメータ追加 | 🔴 CRITICAL | 10サイト | 修正5分 + テスト30分 |
| **#7** | Nginx設定の重複解消 | 🟡 MEDIUM | 全16サイト | 修正1h + テスト1h |
| **#11** | Nginxログ設定統一 | 🟢 LOW | ログ出力 | 修正15分 + テスト15分 |
| **#13** | スクリプトプリフライトチェック | 🟡 MEDIUM | バックアップ | 修正2h + テスト1h |
| **#14** | ローカルリストアスクリプト | 🟡 MEDIUM | リストア機能 | 作成3h + テスト2h |

---

## 3. 検証手順

### 3-1. 【CRITICAL】Nginx HTTPS パラメータ追加

#### 背景

**問題**: blog.kuma8088.com配下10サイトでElementorプレビュー/静的ファイルが404エラー

**原因**: Nginx設定で `fastcgi_param HTTPS on;` が欠落

**影響**: WordPress が HTTP と誤判定 → Elementor が HTTP URL生成 → 混在コンテンツエラー

#### 対象ファイル

`services/blog/config/nginx/conf.d/kuma8088.conf`

#### 修正内容

8箇所の location ブロックに `fastcgi_param HTTPS on;` を追加:

**修正前**:
```nginx
location ~ \.php$ {
    include fastcgi_params;
    fastcgi_pass wordpress:9000;
    fastcgi_param SCRIPT_FILENAME $request_filename;
    # MISSING: fastcgi_param HTTPS on;
}
```

**修正後**:
```nginx
location ~ \.php$ {
    include fastcgi_params;
    fastcgi_pass wordpress:9000;
    fastcgi_param SCRIPT_FILENAME $request_filename;
    fastcgi_param HTTPS on;
    fastcgi_param HTTP_X_FORWARDED_PROTO https;
}
```

#### 修正箇所（行番号）

以下の8箇所を修正:
- Line 28: `/cameramanual` location
- Line 56: `/elementordemo1` location
- Line 82: `/elementordemo02` location
- Line 109: `/elementor-demo-03` location
- Line 136: `/elementor-demo-04` location
- Line 163: `/ec02test` location
- Line 185: `/cameramanual-gwpbk492` location
- Line 201: `/test` location

#### Staging環境での検証手順

```bash
# 1. Staging環境で修正
cd /opt/onprem-infra-system/project-root-infra/services/blog-staging/config/nginx/conf.d
cp kuma8088.conf kuma8088.conf.backup-$(date +%Y%m%d-%H%M%S)

vi kuma8088.conf
# 上記8箇所を修正

# 2. Nginx設定テスト
docker compose exec nginx nginx -t
# Expected: syntax is ok, test is successful

# 3. Nginx リロード
docker compose exec nginx nginx -s reload

# 4. 確認 - WordPress HTTPS検出
docker compose exec wordpress bash -c "cd /var/www/html/kuma8088-elementordemo1 && wp option get siteurl --allow-root"
# Expected: https://... (not http://)

# 5. Elementor動作確認
curl -I http://localhost:8081/elementordemo1/
# Expected: HTTP 200

curl http://localhost:8081/elementordemo1/wp-content/themes/twentytwentyone/style.css
# Expected: CSSファイルが返却される

# 6. 全サブディレクトリサイトで同様確認
for site in cameramanual elementordemo1 elementordemo02 elementor-demo-03 elementor-demo-04 ec02test cameramanual-gwpbk492 test; do
  echo "Testing /$site..."
  curl -I http://localhost:8081/$site/ | head -1
done
# Expected: 全て HTTP 200または302
```

#### 本番適用手順

```bash
# Stagingで問題なければ本番適用
cd /opt/onprem-infra-system/project-root-infra/services/blog/config/nginx/conf.d
cp kuma8088.conf kuma8088.conf.backup-$(date +%Y%m%d-%H%M%S)

# Staging設定をコピー
cp /opt/onprem-infra-system/project-root-infra/services/blog-staging/config/nginx/conf.d/kuma8088.conf .

# Nginx再起動
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# 本番確認（Cloudflare経由）
curl -I https://blog.kuma8088.com/elementordemo1/
# Expected: HTTP 200
```

#### 成功基準

- ✅ Nginx設定テスト成功
- ✅ 全8サブディレクトリサイトで HTTP 200
- ✅ Elementorエディタ動作（管理画面で確認）
- ✅ 静的ファイル（CSS/JS）読み込み成功
- ✅ Nginxエラーログに404エラーなし

---

### 3-2. 【MEDIUM】Nginx設定の重複解消

#### 背景

現在 `kuma8088.conf` は231行あり、8つのほぼ同一な location ブロックが重複。

#### 改善案

**Option A: テンプレート生成スクリプト**

`scripts/generate-nginx-subdirectories.sh`:
```bash
#!/bin/bash
set -euo pipefail

SITES=(
    "elementordemo1"
    "elementordemo02"
    "elementor-demo-03"
    "elementor-demo-04"
    "ec02test"
    "cameramanual"
    "cameramanual-gwpbk492"
    "test"
)

for site in "${SITES[@]}"; do
    cat <<EOF
# ${site}
location ~ ^/${site}/(wp-content|wp-includes)/(.*)$ {
    alias /var/www/html/kuma8088-${site}/\$1/\$2;
    expires max;
    access_log off;
}

location /${site} {
    alias /var/www/html/kuma8088-${site};
    index index.php index.html;

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$request_filename;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
    }

    try_files \$uri \$uri/ @${site};
}

location @${site} {
    rewrite /${site}/(.*)$ /${site}/index.php?/\$1 last;
}

EOF
done
```

#### Staging検証手順

```bash
# 1. スクリプト作成
cd /opt/onprem-infra-system/project-root-infra/services/blog-staging/config/nginx
vi generate-nginx-subdirectories.sh
chmod +x generate-nginx-subdirectories.sh

# 2. 設定生成
./generate-nginx-subdirectories.sh > conf.d/kuma8088-subdirs.conf

# 3. kuma8088.confで読み込み
vi conf.d/kuma8088.conf
# 8つのlocationブロックを削除し、以下を追加:
# include /etc/nginx/conf.d/kuma8088-subdirs.conf;

# 4. テスト
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 5. 全サイト動作確認
# （上記3-1の手順と同様）
```

#### リスク

- ⚠️ 設定ミスで全サイトダウンの可能性
- **対策**: Staging環境で十分検証、バックアップ必須

---

### 3-3. 【MEDIUM】スクリプトプリフライトチェック追加

#### 対象スクリプト

- `services/mailserver/scripts/backup-mailserver.sh`
- `services/mailserver/scripts/backup-to-s3.sh`
- `services/mailserver/scripts/scan-mailserver.sh`

#### 追加する機能

```bash
# Pre-flight checks function
pre_flight_checks() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running pre-flight checks..."

    # 1. Disk space check
    local required_space=$((50*1024*1024*1024))  # 50GB in KB
    local available_space=$(df /mnt/backup-hdd | awk 'NR==2 {print $4*1024}')
    if [ "$available_space" -lt "$required_space" ]; then
        echo "ERROR: Insufficient disk space. Required: 50GB, Available: $((available_space/1024/1024/1024))GB" >&2
        exit 1
    fi
    echo "✓ Disk space OK ($((available_space/1024/1024/1024))GB available)"

    # 2. Docker daemon check
    if ! docker ps > /dev/null 2>&1; then
        echo "ERROR: Docker daemon not responding" >&2
        exit 1
    fi
    echo "✓ Docker daemon OK"

    # 3. Network connectivity check (for S3 backup)
    if [[ "$0" == *"s3"* ]]; then
        if ! ping -c 1 s3.ap-northeast-1.amazonaws.com > /dev/null 2>&1; then
            echo "WARNING: Cannot reach AWS S3. Backup may fail." >&2
        else
            echo "✓ AWS S3 reachable"
        fi
    fi

    # 4. Required commands check
    for cmd in docker aws mysql; do
        if ! command -v $cmd &> /dev/null; then
            echo "ERROR: Required command '$cmd' not found" >&2
            exit 1
        fi
    done
    echo "✓ Required commands available"
}

# スクリプト冒頭で実行
pre_flight_checks
```

#### Staging検証手順

```bash
# 1. テスト用スクリプト作成
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
cp backup-mailserver.sh backup-mailserver-test.sh

# 2. Pre-flight checks追加
vi backup-mailserver-test.sh
# 上記関数を追加

# 3. テスト実行
./backup-mailserver-test.sh --daily --dry-run

# 4. エラーケーステスト
# ディスク不足シミュレーション（実施不要、コード確認のみ）

# 5. 正常系テスト
./backup-mailserver-test.sh --daily

# 6. ログ確認
tail -f ~/.mailserver-backup.log
```

---

### 3-4. 【MEDIUM】ローカルリストアスクリプト作成

#### 背景

現在、Phase 10（ローカルバックアップ）のリストアスクリプトが存在しない。

#### スクリプト仕様

`services/mailserver/scripts/restore-mailserver.sh`:
```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BASE="/mnt/backup-hdd/mailserver"
LOG_FILE="$HOME/.mailserver-restore.log"

# Usage function
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --from PATH          Backup directory path (required)
    --component NAME     Component to restore (all, mail, db, config, roundcube)
    --dry-run            Show what would be restored without restoring
    -h, --help           Show this help message

Examples:
    $0 --from /mnt/backup-hdd/mailserver/daily/backup-2025-11-11 --component all
    $0 --from /mnt/backup-hdd/mailserver/latest --component mail
EOF
    exit 1
}

# Parse arguments
BACKUP_PATH=""
COMPONENT="all"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --from)
            BACKUP_PATH="$2"
            shift 2
            ;;
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate
if [ -z "$BACKUP_PATH" ]; then
    echo "ERROR: --from is required"
    usage
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "ERROR: Backup path not found: $BACKUP_PATH"
    exit 1
fi

# Restore functions
restore_mail() {
    echo "Restoring mail data from $BACKUP_PATH/mail.tar.gz..."
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would extract to /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/"
    else
        docker compose exec dovecot doveadm stop
        tar -xzf "$BACKUP_PATH/mail.tar.gz" -C /opt/onprem-infra-system/project-root-infra/services/mailserver/data/
        docker compose restart dovecot
        echo "✓ Mail data restored"
    fi
}

restore_db() {
    echo "Restoring MariaDB from $BACKUP_PATH/mariadb-mailserver.sql..."
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would import to MariaDB"
    else
        docker compose exec -T mariadb mysql -u root -p"$MYSQL_ROOT_PASSWORD" mailserver < "$BACKUP_PATH/mariadb-mailserver.sql"
        echo "✓ MariaDB restored"
    fi
}

# Main
case "$COMPONENT" in
    mail)
        restore_mail
        ;;
    db)
        restore_db
        ;;
    all)
        restore_mail
        restore_db
        ;;
    *)
        echo "ERROR: Invalid component: $COMPONENT"
        usage
        ;;
esac

echo "Restore completed at $(date)"
```

#### Staging検証手順

```bash
# 1. スクリプト作成
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
vi restore-mailserver.sh
chmod +x restore-mailserver.sh

# 2. Dry-runテスト
./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/backup-2025-11-10 --component all --dry-run

# 3. テスト用バックアップから復元（Staging環境）
cd /opt/onprem-infra-system/project-root-infra/services/mailserver-staging
./scripts/restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/backup-2025-11-10 --component mail

# 4. 復元確認
docker compose exec dovecot doveadm mailbox list -u test@example.com
```

---

## 4. ロールバック手順

### 4-1. Nginx設定ロールバック

```bash
# バックアップから復元
cd /opt/onprem-infra-system/project-root-infra/services/blog/config/nginx/conf.d
cp kuma8088.conf.backup-YYYYMMDD-HHMMSS kuma8088.conf

# Nginx再起動
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose restart nginx
```

### 4-2. スクリプトロールバック

```bash
# Gitから復元
cd /opt/onprem-infra-system/project-root-infra
git checkout services/mailserver/scripts/backup-mailserver.sh
```

---

## 5. トラブルシューティング

### 問題: Nginx起動失敗

```bash
# ログ確認
docker compose logs nginx | tail -50

# 設定テスト
docker compose exec nginx nginx -t

# よくあるエラー:
# - Syntax error: 括弧やセミコロン不足
# - Unknown directive: タイポ
```

### 問題: WordPress HTTPS検出失敗

```bash
# 環境変数確認
docker compose exec wordpress env | grep -i https

# wp-config.php確認
docker compose exec wordpress cat /var/www/html/SITE/wp-config.php | grep -i https

# WordPressオプション確認
docker compose exec wordpress wp option get home --path=/var/www/html/SITE --allow-root
```

### 問題: スクリプト実行失敗

```bash
# 権限確認
ls -la services/mailserver/scripts/*.sh

# Shebang確認
head -1 services/mailserver/scripts/backup-mailserver.sh

# 実行権限付与
chmod +x services/mailserver/scripts/*.sh
```

---

## 📝 チェックリスト

### Staging検証完了チェック

- [ ] Staging環境構築完了
- [ ] #2 Nginx HTTPS パラメータ追加 → 8サイト動作確認
- [ ] #7 Nginx重複解消（オプション） → 全16サイト動作確認
- [ ] #11 Nginxログ設定統一 → ログ出力確認
- [ ] #13 プリフライトチェック → エラーハンドリング確認
- [ ] #14 ローカルリストア → 復元成功確認

### 本番適用前チェック

- [ ] Staging環境で全項目正常動作
- [ ] バックアップ取得済み
- [ ] ロールバック手順確認
- [ ] 作業時間帯確認（深夜メンテナンス推奨）
- [ ] エスカレーション先確認

---

**Last Updated**: 2025-11-11
**Author**: Claude
**Status**: ✅ Ready for Staging Verification
