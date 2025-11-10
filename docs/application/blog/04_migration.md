# ブログシステム移行手順書

**プロジェクト名**: Xserverブログ移植プロジェクト
**対象環境**: Xserver → Dell WorkStation (Rocky Linux 9.6) + Docker Compose
**作成日**: 2025-11-08
**バージョン**: 1.0

---

## 📋 目次

1. [移行フロー全体像](#1-移行フロー全体像)
2. [Phase A-0: サイト調査と移行方法選択](#2-phase-a-0-サイト調査と移行方法選択)
3. [方法A: WPvivid GUI移行](#3-方法a-wpvivid-gui移行)
4. [方法B: WPvivid分割移行](#4-方法b-wpvivid分割移行)
5. [方法C: SSH/rsyncスクリプト移行](#5-方法c-sshrsyncスクリプト移行)
6. [方法D: Migrate Guru自動移行](#6-方法d-migrate-guru自動移行)
7. [Phase C: 1サイト目テスト移行](#7-phase-c-1サイト目テスト移行)
8. [Phase D: 残り6サイト移行](#8-phase-d-残り6サイト移行)
9. [Phase E: DNS切替と本番化](#9-phase-e-dns切替と本番化)
10. [トラブルシューティング](#10-トラブルシューティング)

---

## 1. 移行フロー全体像

### 1.1 推定所要時間

| Phase | 内容 | 所要時間 |
|-------|------|----------|
| **Phase A-0** | サイト調査・移行方法選択 | 2-3時間 |
| **Phase C** | 1サイト目テスト移行 | 2-4時間 |
| **Phase D** | 残り6サイト移行 | 6-12時間 |
| **Phase E** | DNS切替・本番化 | 1-2時間 |
| **合計** | - | **11-21時間** |

### 1.2 前提条件

**Dell環境**:
- ✅ 03_installation.md (Phase A〜F) が完了している
- ✅ 1サイト目（kuma8088.com）が空のWordPressとして稼働中
- ✅ Cloudflare Tunnelが稼働中
- ✅ バックアップシステムが動作確認済み

**Xserver環境**:
- ✅ 全サイトへの管理者権限あり
- ✅ SSH/SFTP接続が可能（または管理画面のみでも可）
- ✅ Phase A-0調査が完了している

---

## 2. Phase A-0: サイト調査と移行方法選択

### 📋 Phase A-0 現状と必要な情報（2025-11-08時点）

**完了済み**:
- ✅ 全18個のデータベース情報整理完了（`claudedocs/xserver-db-summary.md`）
- ✅ 移行対象サイトの容量確認完了（約530-600 MB、Phase 1で6サイト）
- ✅ パスワード判明サイト（12サイト）の情報保存完了（`claudedocs/xserver-credentials.env`）
- ✅ `.gitignore` での機密情報保護確認完了

**⚠️ Xserver管理画面で確認が必要な項目**:

| 優先度 | 項目 | 詳細 | 所要時間 |
|-------|------|------|---------|
| 🔴 最優先 | **kuma8088.com メインサイトのDB情報** | DB名・ユーザー名・パスワード不明 | 5分 |
| 🔴 最優先 | **独自ドメイン3サイトのパスワード** | webmakeprofit.org, webmakesprofit.com, toyota-phv.jp | 5分 |
| 🔴 必須 | **SSH/FTP情報** | ホスト名・ユーザー名確認 | 3分 |
| 🟡 任意 | **不明DB 3件の用途確認** | gwpbk492_p3ca6, wp5, wt2（移行対象か判断） | 5分 |

**📝 詳細チェックリスト**: [`claudedocs/xserver-checklist.md`](./claudedocs/xserver-checklist.md)
**📊 DB情報詳細**: [`claudedocs/xserver-db-summary.md`](./claudedocs/xserver-db-summary.md)
**🔐 認証情報テンプレート**: [`claudedocs/xserver-credentials.env`](./claudedocs/xserver-credentials.env)

**次のアクション**:
1. Xserver管理画面で上記4項目を確認（15-20分）
2. `xserver-credentials.env` を実際の情報で更新
3. Phase A-0の残りのステップへ進む

---

### Phase A-0-1: 各サイトのサイズ調査

**目的**: サイトサイズを把握し、最適な移行方法を選択

#### ステップ 1: Xserver サーバーパネルでディスク使用量確認

**実行アクション**:
1. Xserverサーバーパネルへログイン: https://www.xserver.ne.jp/login_server.php
2. 「ファイル管理」→「ディスク使用量」を開く
3. 各ドメインのディスク使用量を記録

**記録フォーマット** (`claudedocs/xserver-site-sizes.md`):
```markdown
# Xserver サイトサイズ調査結果

## 調査日
2025-11-XX

## サイト別サイズ

| サイト名 | ディスク使用量 | DB推定サイズ | 合計 | 移行方法 |
|---------|--------------|------------|------|---------|
| kuma8088.com | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| courses.kuma8088.com | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| fx-trader-life.com | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| courses.fx-trader-life.com | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| toyota-phv.jp | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| webmakeprofit.org | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
| webmakesprofit.com | XXX MB | XX MB | XXX MB | [Phase A-0-3で決定] |
```

#### ステップ 2: SSHでディスク使用量を正確に確認（SSH利用可能な場合）

**実行コマンド** (Xserver SSH接続):
```bash
# Xserverへ接続
ssh <xserver-username>@<xserver-host>

# ディレクトリ構造確認（実際の出力）
ls -la ~/
# 出力:
# kuma8088.com/
# fx-trader-life.com/
# toyota-phv.jp/
# webmakeprofit.org/
# webmakesprofit.com/

# 各サイトのファイルサイズ確認
du -sh ~/kuma8088.com/public_html/
du -sh ~/fx-trader-life.com/public_html/
du -sh ~/toyota-phv.jp/public_html/
du -sh ~/webmakeprofit.org/public_html/
du -sh ~/webmakesprofit.com/public_html/

# サブドメイン構造確認（重要！）
ls -la ~/kuma8088.com/
ls -la ~/fx-trader-life.com/
# 出力例:
#   public_html/
#   subdomains/courses/public_html/  ← サブドメインがある場合

# サブドメインサイズ確認（存在する場合）
du -sh ~/kuma8088.com/subdomains/courses/public_html/ 2>/dev/null || echo "サブドメインなし"
du -sh ~/fx-trader-life.com/subdomains/courses/public_html/ 2>/dev/null || echo "サブドメインなし"

# wp-content/uploadsのみ確認（メディアライブラリサイズ）
du -sh ~/kuma8088.com/public_html/wp-content/uploads/
```

#### ステップ 3: データベースサイズ確認

**方法1: phpMyAdminで確認** (SSH不可の場合):
1. Xserver phpMyAdminへログイン
2. 対象データベースを選択
3. 「構造」タブで合計サイズを確認

**方法2: SSHでmysqldump実行** (SSH利用可能な場合):
```bash
# データベースサイズ確認（実際のdumpサイズ）
mysqldump -u <user> -p <database_name> | gzip | wc -c

# 例: kuma8088.com のDB
mysqldump -u xserver_user -p xserver_wp1 | gzip | wc -c
# 出力: 5242880 (5MB)
```

#### ステップ 4: WordPress・PHP・MySQL バージョン確認

**実行コマンド** (Xserver SSH接続):
```bash
# PHP バージョン確認
php -v
# 出力例: PHP 7.4.33 (cli)

# MySQL/MariaDB バージョン確認
mysql --version
# 出力例: mysql Ver 15.1 Distrib 10.5.18-MariaDB

# WordPress バージョン確認（各サイト）
grep "wp_version = " ~/kuma8088.com/public_html/wp-includes/version.php
# 出力例: $wp_version = '6.4.2';

# または
head -20 ~/kuma8088.com/public_html/wp-includes/version.php | grep wp_version
```

**記録すべき情報** (`claudedocs/xserver-versions.md`):
```markdown
# Xserver 環境バージョン情報

## システム環境
- PHP: 7.4.33
- MySQL: MariaDB 10.5.18

## 各サイトのWordPressバージョン
| サイト名 | WordPressバージョン |
|---------|-------------------|
| kuma8088.com | 6.4.2 |
| fx-trader-life.com | 6.3.1 |
...

## Dell側との互換性チェック
- Dell PHP: 8.2+ → ✅ 互換性あり（WordPress 6.3+はPHP 8.2対応）
- Dell MariaDB: 10.11 → ✅ 互換性あり
```

#### ステップ 5: データベース接続情報の完全取得

**実行コマンド** (Xserver SSH接続):
```bash
# 各サイトのwp-config.phpからDB接続情報抽出
cd ~/kuma8088.com/public_html
grep "DB_" wp-config.php | grep -v "//"

# 出力例:
# define('DB_NAME', 'xserver_wp1');
# define('DB_USER', 'xserver_user');
# define('DB_PASSWORD', 'xserver_pass');
# define('DB_HOST', 'mysql123.xserver.jp');
# define('DB_CHARSET', 'utf8mb4');
# define('DB_COLLATE', 'utf8mb4_unicode_ci');
```

**記録フォーマット** (`claudedocs/xserver-db-credentials.md`):
```markdown
# Xserver データベース接続情報

## kuma8088.com
- DB_NAME: xserver_wp1
- DB_USER: xserver_user
- DB_PASSWORD: ********
- DB_HOST: mysql123.xserver.jp

## fx-trader-life.com
- DB_NAME: xserver_wp2
...

※ 注: このファイルは機密情報のため Git 管理外（.gitignore追加済み）
```

#### ステップ 6: .htaccess・セキュリティ設定確認

**実行コマンド** (Xserver SSH接続):
```bash
# .htaccess 存在確認
ls -la ~/kuma8088.com/public_html/.htaccess

# .htaccess 内容確認（パーマリンク・リダイレクト設定）
cat ~/kuma8088.com/public_html/.htaccess

# .user.ini 確認（PHP設定）
cat ~/kuma8088.com/public_html/.user.ini 2>/dev/null || echo ".user.iniなし"

# 隠しファイル一覧
find ~/kuma8088.com/public_html/ -maxdepth 2 -name ".*" -type f

# 出力例:
# .htaccess
# .htpasswd（存在する場合）
# .user.ini
```

**記録すべき情報** (`claudedocs/xserver-htaccess.md`):
```markdown
# .htaccess 設定内容

## kuma8088.com
```apache
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress

# カスタム設定（あれば）
...
```
```

#### ステップ 7: アップロードディレクトリ構造・パーミッション確認

**実行コマンド** (Xserver SSH接続):
```bash
# uploads ディレクトリ構造確認
ls -la ~/kuma8088.com/public_html/wp-content/uploads/

# 年月別フォルダ確認
tree -L 2 ~/kuma8088.com/public_html/wp-content/uploads/ 2>/dev/null || \
find ~/kuma8088.com/public_html/wp-content/uploads/ -maxdepth 2 -type d | head -20

# パーミッション確認
stat ~/kuma8088.com/public_html/wp-content/uploads/

# シンボリックリンク確認
find ~/kuma8088.com/public_html/ -type l -ls
```

#### ステップ 8: WordPress サイトURL確認（DB直接）

**実行コマンド** (Xserver SSH接続):
```bash
# wp-config.php から接続情報取得
cd ~/kuma8088.com/public_html
DB_NAME=$(grep "DB_NAME" wp-config.php | cut -d"'" -f4)
DB_USER=$(grep "DB_USER" wp-config.php | cut -d"'" -f4)
DB_PASS=$(grep "DB_PASSWORD" wp-config.php | cut -d"'" -f4)
DB_HOST=$(grep "DB_HOST" wp-config.php | cut -d"'" -f4)

# サイトURL確認
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

# 出力例:
# +-------------+---------------------------+
# | option_name | option_value              |
# +-------------+---------------------------+
# | siteurl     | http://kuma8088.com       |
# | home        | http://kuma8088.com       |
# +-------------+---------------------------+

# 有効プラグイン確認
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  -e "SELECT option_value FROM wp_options WHERE option_name='active_plugins';" -sN
```

**記録フォーマット** (`claudedocs/xserver-site-urls.md`):
```markdown
# Xserver サイトURL一覧

## kuma8088.com
- 旧URL (siteurl): http://kuma8088.com
- 旧URL (home): http://kuma8088.com
- 新URL (Dell): https://kuma8088.com
- URL置換コマンド: `wp search-replace 'http://kuma8088.com' 'https://kuma8088.com'`

## fx-trader-life.com
...
```

#### ステップ 9: cron・定期実行タスク確認

**実行コマンド** (Xserver SSH接続):
```bash
# cron設定確認
crontab -l

# 出力がない場合: "no crontab for user"
# 出力がある場合: 定期実行タスク一覧が表示
```

#### ステップ 10: 全サイト一括調査スクリプト実行（推奨）

**目的**: ステップ1-9の全コマンドを自動実行し、結果を一括取得

**⚠️ セキュリティ注意**: 認証情報を平文でスクリプトに埋め込まない

**安全な実行方法**:

**方法1: 環境変数を使った安全な実行**（推奨）:
```bash
# ローカルPCで環境変数ファイル作成（Git管理外）
cat > claudedocs/xserver-credentials.env << 'EOF'
# Xserver Database Credentials (NEVER commit to Git)
XSERVER_KUMA8088_DB_USER="gwpbk492_wt3"
XSERVER_KUMA8088_DB_PASS="<Xserver管理画面で確認>"
XSERVER_KUMA8088_DB_NAME="gwpbk492_wt3"

XSERVER_FX_TRADER_DB_USER="gwpbk492_wp2"
XSERVER_FX_TRADER_DB_PASS="<Xserver管理画面で確認>"
XSERVER_FX_TRADER_DB_NAME="gwpbk492_wp3"

XSERVER_TOYOTA_DB_USER="gwpbk492_wt6"
XSERVER_TOYOTA_DB_PASS="<Xserver管理画面で確認>"
XSERVER_TOYOTA_DB_NAME="gwpbk492_wt5"

XSERVER_WEBMAKEPROFIT_DB_USER="gwpbk492_wt4"
XSERVER_WEBMAKEPROFIT_DB_PASS="<Xserver管理画面で確認>"
XSERVER_WEBMAKEPROFIT_DB_NAME="gwpbk492_wt1"

XSERVER_WEBMAKESPROFIT_DB_USER="gwpbk492_wt5"
XSERVER_WEBMAKESPROFIT_DB_PASS="<Xserver管理画面で確認>"
XSERVER_WEBMAKESPROFIT_DB_NAME="gwpbk492_wt4"
EOF

chmod 600 claudedocs/xserver-credentials.env

# 調査スクリプトテンプレート作成（認証情報は環境変数から取得）
cat > claudedocs/xserver-investigation-template.sh << 'SCRIPT_EOF'
#!/bin/bash
# Xserver 全サイト調査スクリプト（環境変数版）
# 使用方法:
#   1. xserver-credentials.env を作成
#   2. source xserver-credentials.env
#   3. ./xserver-investigation-template.sh > results.txt

set -euo pipefail

echo "=== Xserver 全サイト調査開始 ==="
echo "実行日時: $(date)"
echo ""

# 環境変数確認
if [ -z "${XSERVER_KUMA8088_DB_USER:-}" ]; then
  echo "エラー: 環境変数が設定されていません"
  echo "実行前に: source xserver-credentials.env"
  exit 1
fi

# Phase A-0 Step 1: ディレクトリ構造
echo "=== ディレクトリ構造 ==="
ls -la ~/

# Phase A-0 Step 2: ファイルサイズ
echo ""
echo "=== ファイルサイズ確認 ==="
du -sh ~/kuma8088.com/public_html/
du -sh ~/fx-trader-life.com/public_html/
du -sh ~/toyota-phv.jp/public_html/
du -sh ~/webmakeprofit.org/public_html/
du -sh ~/webmakesprofit.com/public_html/

# Phase A-0 Step 3: データベースサイズ（環境変数使用）
echo ""
echo "=== データベースサイズ確認（圧縮後） ==="

echo -n "kuma8088.com: "
mysqldump -h localhost -u "$XSERVER_KUMA8088_DB_USER" -p"$XSERVER_KUMA8088_DB_PASS" "$XSERVER_KUMA8088_DB_NAME" | gzip | wc -c | awk '{printf "%.2f MB\n", $1/1024/1024}'

echo -n "fx-trader-life.com: "
mysqldump -h localhost -u "$XSERVER_FX_TRADER_DB_USER" -p"$XSERVER_FX_TRADER_DB_PASS" "$XSERVER_FX_TRADER_DB_NAME" | gzip | wc -c | awk '{printf "%.2f MB\n", $1/1024/1024}'

echo -n "toyota-phv.jp: "
mysqldump -h localhost -u "$XSERVER_TOYOTA_DB_USER" -p"$XSERVER_TOYOTA_DB_PASS" "$XSERVER_TOYOTA_DB_NAME" | gzip | wc -c | awk '{printf "%.2f MB\n", $1/1024/1024}'

echo -n "webmakeprofit.org: "
mysqldump -h localhost -u "$XSERVER_WEBMAKEPROFIT_DB_USER" -p"$XSERVER_WEBMAKEPROFIT_DB_PASS" "$XSERVER_WEBMAKEPROFIT_DB_NAME" | gzip | wc -c | awk '{printf "%.2f MB\n", $1/1024/1024}'

echo -n "webmakesprofit.com: "
mysqldump -h localhost -u "$XSERVER_WEBMAKESPROFIT_DB_USER" -p"$XSERVER_WEBMAKESPROFIT_DB_PASS" "$XSERVER_WEBMAKESPROFIT_DB_NAME" | gzip | wc -c | awk '{printf "%.2f MB\n", $1/1024/1024}'

# Phase A-0 Step 4: バージョン確認
echo ""
echo "=== システムバージョン ==="
php -v | head -1
mysql --version

echo ""
echo "=== WordPressバージョン ==="
grep "wp_version = " ~/kuma8088.com/public_html/wp-includes/version.php
grep "wp_version = " ~/fx-trader-life.com/public_html/wp-includes/version.php
grep "wp_version = " ~/toyota-phv.jp/public_html/wp-includes/version.php
grep "wp_version = " ~/webmakeprofit.org/public_html/wp-includes/version.php
grep "wp_version = " ~/webmakesprofit.com/public_html/wp-includes/version.php

# Phase A-0 Step 8: サイトURL確認（環境変数使用）
echo ""
echo "=== サイトURL確認 ==="

echo "--- kuma8088.com ---"
mysql -h localhost -u "$XSERVER_KUMA8088_DB_USER" -p"$XSERVER_KUMA8088_DB_PASS" "$XSERVER_KUMA8088_DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

echo ""
echo "--- fx-trader-life.com ---"
mysql -h localhost -u "$XSERVER_FX_TRADER_DB_USER" -p"$XSERVER_FX_TRADER_DB_PASS" "$XSERVER_FX_TRADER_DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

echo ""
echo "--- toyota-phv.jp ---"
mysql -h localhost -u "$XSERVER_TOYOTA_DB_USER" -p"$XSERVER_TOYOTA_DB_PASS" "$XSERVER_TOYOTA_DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

echo ""
echo "--- webmakeprofit.org ---"
mysql -h localhost -u "$XSERVER_WEBMAKEPROFIT_DB_USER" -p"$XSERVER_WEBMAKEPROFIT_DB_PASS" "$XSERVER_WEBMAKEPROFIT_DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

echo ""
echo "--- webmakesprofit.com ---"
mysql -h localhost -u "$XSERVER_WEBMAKESPROFIT_DB_USER" -p"$XSERVER_WEBMAKESPROFIT_DB_PASS" "$XSERVER_WEBMAKESPROFIT_DB_NAME" \
  -e "SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"

echo ""
echo "=== 調査完了 ==="
SCRIPT_EOF

chmod +x claudedocs/xserver-investigation-template.sh

# Xserverへ安全に転送・実行
# 1. スクリプトテンプレートを転送
scp claudedocs/xserver-investigation-template.sh \
  <xserver-username>@<xserver-host>:~/investigation.sh

# 2. SSH接続して環境変数を手動設定し実行
ssh <xserver-username>@<xserver-host>

# Xserver上で実行（環境変数を手動設定）
export XSERVER_KUMA8088_DB_USER="gwpbk492_wt3"
export XSERVER_KUMA8088_DB_PASS="<Xserver管理画面で確認>"
export XSERVER_KUMA8088_DB_NAME="gwpbk492_wt3"
# ... 他のサイトも同様に設定

# スクリプト実行
./investigation.sh > ~/xserver-investigation-results.txt 2>&1

# 結果確認
less ~/xserver-investigation-results.txt

# 実行後、環境変数をクリア（セキュリティ）
unset XSERVER_KUMA8088_DB_PASS
unset XSERVER_FX_TRADER_DB_PASS
unset XSERVER_TOYOTA_DB_PASS
unset XSERVER_WEBMAKEPROFIT_DB_PASS
unset XSERVER_WEBMAKESPROFIT_DB_PASS

# ログアウト
exit

# 結果をローカルPCにダウンロード
scp <xserver-username>@<xserver-host>:~/xserver-investigation-results.txt \
  ~/Downloads/
```

**方法2: 手動実行**（小規模・単発調査の場合）:
- ステップ1-9の各コマンドを個別に実行
- 認証情報はXserver管理画面から都度コピー・ペースト
- スクリプト化しない

---

#### ステップ 11: 調査結果の安全な保管（必須）

**⚠️ 重要**: 調査結果ファイル（`xserver-investigation-results.txt`）には以下の機密情報が含まれます:
- データベース認証情報（`grep "DB_" wp-config.php`の出力）
- .htaccess内容（セキュリティ設定）
- ディレクトリ構造、ファイルパス

**安全な保管手順**:

**方法1: 機密情報を即座に削除・分離**（推奨）:
```bash
# 調査結果をローカルPCにダウンロード後、機密情報を削除
cd ~/Downloads

# 1. 認証情報を別ファイルに分離
grep -A 5 "=== データベース接続情報 ===" xserver-investigation-results.txt > xserver-db-credentials-SENSITIVE.txt

# 2. 元ファイルから認証情報セクションを削除
sed -i '/=== データベース接続情報 ===/,/=== .htaccess ファイルサイズ ===/d' xserver-investigation-results.txt

# 3. 機密情報ファイルを暗号化（GPG）
gpg --symmetric --cipher-algo AES256 xserver-db-credentials-SENSITIVE.txt
# パスフレーズ入力 → xserver-db-credentials-SENSITIVE.txt.gpg が生成

# 4. 平文ファイルを即座に削除
shred -u xserver-db-credentials-SENSITIVE.txt

# 5. 暗号化ファイルのパーミッション厳格化
chmod 400 xserver-db-credentials-SENSITIVE.txt.gpg

# 6. 一般情報ファイルを安全なディレクトリに移動
mkdir -p ~/Documents/blog-migration-investigation
mv xserver-investigation-results.txt ~/Documents/blog-migration-investigation/
chmod 600 ~/Documents/blog-migration-investigation/xserver-investigation-results.txt
```

**方法2: 調査結果全体を暗号化保管**:
```bash
# ダウンロード後、即座に暗号化
cd ~/Downloads

# GPG暗号化（AES256）
gpg --symmetric --cipher-algo AES256 xserver-investigation-results.txt
# パスフレーズ入力 → xserver-investigation-results.txt.gpg が生成

# 平文ファイルを安全に削除
shred -u xserver-investigation-results.txt

# 暗号化ファイルを安全な場所に移動
mkdir -p ~/Documents/blog-migration-investigation
mv xserver-investigation-results.txt.gpg ~/Documents/blog-migration-investigation/
chmod 400 ~/Documents/blog-migration-investigation/xserver-investigation-results.txt.gpg
```

**方法3: パスワード付きZIP暗号化**（GPG不可の場合）:
```bash
# 7-Zipでパスワード付き暗号化（AES256）
7z a -p -mhe=on -t7z xserver-investigation-results.7z xserver-investigation-results.txt
# パスワード入力

# または zipコマンド（暗号化強度低い、非推奨）
zip -e xserver-investigation-results.zip xserver-investigation-results.txt

# 平文ファイルを削除
shred -u xserver-investigation-results.txt

# 暗号化ファイルを安全な場所に移動
mkdir -p ~/Documents/blog-migration-investigation
mv xserver-investigation-results.7z ~/Documents/blog-migration-investigation/
chmod 600 ~/Documents/blog-migration-investigation/xserver-investigation-results.7z
```

**復号化方法**（必要時のみ）:
```bash
# GPG復号化
gpg --decrypt xserver-db-credentials-SENSITIVE.txt.gpg > temp-credentials.txt
# 使用後、即座に削除
shred -u temp-credentials.txt

# 7-Zip復号化
7z x xserver-investigation-results.7z
# 使用後、即座に削除
shred -u xserver-investigation-results.txt
```

**保管場所の推奨**:
```bash
# ✅ 推奨: ローカルPCの暗号化ディレクトリ
~/Documents/blog-migration-investigation/  （パーミッション700）

# ✅ 推奨: 暗号化外付けHDD/USB
/media/encrypted-backup/blog-migration/

# ⚠️ 注意: クラウドストレージの場合は必ず暗号化
~/Dropbox/encrypted-blog-migration/  （GPG暗号化済みファイルのみ）

# ❌ 禁止: Git管理ディレクトリ
# /opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/
# → .gitignore追加済みだが、誤コミットリスクあり
```

**保管期間管理**:
```bash
# 移行完了後（Phase E完了後）、即座に削除
# 目安: DNS切替完了 + 2週間並行運用完了後

# 削除前に最終確認
echo "移行完了確認:"
echo "- Dell側でWordPress正常動作: OK"
echo "- DNS浸透完了: OK"
echo "- Xserver解約完了: OK"
echo "上記が全てOKの場合のみ削除可"

# 暗号化ファイルの安全な削除
shred -u ~/Documents/blog-migration-investigation/xserver-db-credentials-SENSITIVE.txt.gpg
shred -u ~/Documents/blog-migration-investigation/xserver-investigation-results.txt.gpg

# ディレクトリ削除
rm -rf ~/Documents/blog-migration-investigation/
```

**Xserver側の調査結果ファイルも削除**:
```bash
# Xserver SSH接続
ssh <xserver-username>@<xserver-host>

# 調査スクリプトと結果を削除
shred -u ~/investigation.sh
shred -u ~/xserver-investigation-results.txt

# データベースダンプファイルも削除（ステップC-1で作成した場合）
shred -u ~/kuma8088_db_*.sql.gz
shred -u ~/migration_*_db_*.sql.gz

# ログアウト
exit
```

**Git管理の徹底確認**:
```bash
# 調査結果ファイルがGit追跡されていないことを確認
cd /opt/onprem-infra-system/project-root-infra
git status --ignored | grep -E "xserver-investigation|xserver-credentials"

# 出力例（正常）:
# !! docs/application/blog/claudedocs/xserver-investigation-results.txt
# !! docs/application/blog/claudedocs/xserver-credentials.env

# "!!" が付いていればGit管理外（.gitignore適用）
```

**期待される出力内容** (`xserver-investigation-results.txt`):
- 全5サイトのディレクトリ構造
- ファイルサイズ（du -sh結果）
- データベースサイズ（gzip圧縮後）
- PHP/MySQL/WordPressバージョン
- データベース接続情報（wp-config.php抽出結果）
- .htaccessファイルサイズ
- uploadsディレクトリ構造
- サイトURL（データベースから取得）
- cron設定
- ファイル数
- 投稿数

**検証項目**:
- **アクション**: `claudedocs/xserver-site-sizes.md` に全5サイトの情報が記録されているか確認
- **期待結果**: 各サイトの「ファイルサイズ」「DBサイズ」「合計」「バージョン情報」が明確
- **失敗時**: Xserverサーバーパネルで再確認

---

### Phase A-0-X: ⚠️ 重大な互換性問題の確認（必読）

#### 問題1: PHP互換性 ✅ **解決済み**

**調査結果**（実際のXserver環境）:
- **Xserver PHP**: **8.3.21（2024年更新済み）** ✅
- **Dell PHP**: 8.3系（同一バージョン）
- **WordPress**: バージョン確認必要、6.4+へ更新推奨

**状況**: ✅ **PHP 8.3.21で統一されているため、互換性問題なし**

**残存リスク**:
- WordPress本体・プラグインがPHP 8.3に対応しているか要確認
- 古いプラグインがPHP 8.3で非推奨警告を出す可能性

**対処方法**:
1. **移行前にWordPress更新**（推奨）:
   ```bash
   # Xserver側でWordPress更新（管理画面 or WP-CLI）
   # 「ダッシュボード」→「更新」→「今すぐ更新」
   # 最新安定版（6.4+）はPHP 8.3完全対応
   ```

2. **移行後に互換性確認**:
   ```bash
   # Dell側でPHPエラーログ確認
   docker compose logs wordpress | grep -i "deprecated\|warning\|error"

   # WordPress Debug Logを有効化（wp-config.php）
   define('WP_DEBUG', true);
   define('WP_DEBUG_LOG', true);
   define('WP_DEBUG_DISPLAY', false);
   ```

3. **プラグイン互換性確認**:
   - Phase C（1サイト目）でプラグイン動作を徹底検証
   - 非対応プラグインは代替プラグインへ置き換えまたは更新

#### 問題2: Apache → Nginx 変換の必要性

**調査結果**（実際の.htaccess内容）:
- **kuma8088.com**: WpFastestCache使用（Apache mod_rewrite多用）
- **webmakesprofit.com**: 画像hotlink保護（RewriteCond使用）
- **全サイト**: Xserver固有キャッシュヘッダー（`Ngx_Cache_*`環境変数）

**問題**:
- Nginxは`.htaccess`を解釈しない
- Apache `mod_rewrite`ルールはNginx `rewrite`へ手動変換必要
- Xserver固有のヘッダー設定は削除必要

**対処方法**:
1. **.htaccess内容の記録**:
   ```bash
   # 各サイトの.htaccessを保存
   # claudedocs/xserver-htaccess-kuma8088.md
   # claudedocs/xserver-htaccess-webmakesprofit.md
   ```

2. **Nginx設定への変換**（移行後に実施）:
   - WpFastestCacheルール → Nginx `location`ブロックへ変換
   - RewriteCond/RewriteRule → Nginx `rewrite`へ変換
   - 画像hotlink保護 → Nginx `valid_referers`へ変換

3. **キャッシュプラグイン再設定**:
   - WpFastestCache設定を一旦無効化
   - Nginx側でFastCGI Cacheを設定（推奨）
   - またはW3 Total Cache等のNginx対応プラグインへ変更

#### 問題3: データベース認証情報の安全な管理

**重要**: データベース認証情報は平文でドキュメントに記載せず、以下の方法で管理してください。

**推奨管理方法**:

**方法1: 環境変数ファイルで管理**（推奨）:
```bash
# claudedocs/xserver-credentials.env を作成（Git管理外）
cat > claudedocs/xserver-credentials.env << 'EOF'
# Xserver Database Credentials (NEVER commit to Git)
# kuma8088.com
XSERVER_KUMA8088_DB_NAME="gwpbk492_wt3"
XSERVER_KUMA8088_DB_USER="gwpbk492_wt3"
XSERVER_KUMA8088_DB_PASS="<Xserver管理画面で確認>"
XSERVER_KUMA8088_DB_HOST="localhost"

# fx-trader-life.com
XSERVER_FX_TRADER_DB_NAME="gwpbk492_wp3"
XSERVER_FX_TRADER_DB_USER="gwpbk492_wp2"
XSERVER_FX_TRADER_DB_PASS="<Xserver管理画面で確認>"
XSERVER_FX_TRADER_DB_HOST="localhost"

# toyota-phv.jp
XSERVER_TOYOTA_DB_NAME="gwpbk492_wt5"
XSERVER_TOYOTA_DB_USER="gwpbk492_wt6"
XSERVER_TOYOTA_DB_PASS="<Xserver管理画面で確認>"
XSERVER_TOYOTA_DB_HOST="localhost"

# webmakeprofit.org
XSERVER_WEBMAKEPROFIT_DB_NAME="gwpbk492_wt1"
XSERVER_WEBMAKEPROFIT_DB_USER="gwpbk492_wt4"
XSERVER_WEBMAKEPROFIT_DB_PASS="<Xserver管理画面で確認>"
XSERVER_WEBMAKEPROFIT_DB_HOST="localhost"

# webmakesprofit.com
XSERVER_WEBMAKESPROFIT_DB_NAME="gwpbk492_wt4"
XSERVER_WEBMAKESPROFIT_DB_USER="gwpbk492_wt5"
XSERVER_WEBMAKESPROFIT_DB_PASS="<Xserver管理画面で確認>"
XSERVER_WEBMAKESPROFIT_DB_HOST="localhost"
EOF

# パーミッション厳格化（所有者のみ読み書き可）
chmod 600 claudedocs/xserver-credentials.env
```

**方法2: 1Passwordやパスワード管理ツール**:
- 各サイトのDB認証情報をパスワード管理ツールに保存
- 実行時に手動コピー・ペースト

**方法3: Ansible Vaultで暗号化**（大規模環境向け）:
```bash
# Ansible Vaultで暗号化
ansible-vault create claudedocs/xserver-credentials-vault.yml
# パスワード入力後、認証情報をYAML形式で記載

# 使用時に復号化
ansible-vault view claudedocs/xserver-credentials-vault.yml
```

**セキュリティ対策**:
```bash
# .gitignoreに追加（必須）
cat >> .gitignore << 'EOF'

# Xserver credentials (NEVER commit these)
docs/application/blog/claudedocs/xserver-credentials.env
docs/application/blog/claudedocs/xserver-credentials-vault.yml
docs/application/blog/claudedocs/*-credentials.*
EOF

# ⚠️ 既にGit履歴に認証情報をコミットしている場合の緊急対処
# 1. 認証情報を即座にXserver管理画面で変更
# 2. Git履歴から完全削除（git filter-branchまたはBFG Repo-Cleaner使用）
# 3. 詳細: https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

---

### Phase A-0-Y: 移行優先モード（セキュリティ簡易版）

**方針**: セキュリティ対処は本番稼働後に実施し、まず移行を完遂することを優先

#### 移行中の最小限セキュリティ対策

**現状のリスク認識**:
- ✅ 認識済み: 調査結果ファイル・スクリプトに平文DB認証情報が含まれる
- ✅ 認識済み: `.gitignore`追加済みだが、誤コミットリスクあり
- ✅ 認識済み: ローカルPC上に平文ファイルが一時的に存在

**移行中の暫定的な管理方法**:

```bash
# 1. アクセス制限（最小限のメンバーのみ）
# 調査結果ファイルは作業者のみアクセス可能に
chmod 600 ~/Downloads/xserver-investigation-results.txt
chmod 600 docs/application/blog/claudedocs/xserver-credentials.env

# 2. 保管場所の限定
# Git管理外ディレクトリに保管（.gitignore適用確認済み）
ls -la docs/application/blog/claudedocs/
# → .gitignoreが適用されていることを確認

# 3. 移行完了までの一時保管
mkdir -p ~/Documents/blog-migration-temp
mv ~/Downloads/xserver-investigation-results.txt ~/Documents/blog-migration-temp/
chmod 700 ~/Documents/blog-migration-temp
chmod 600 ~/Documents/blog-migration-temp/*

# 4. Git誤コミット防止確認
git status --ignored | grep -E "xserver-|claudedocs/"
# → "!!" が表示されればGit管理外（正常）
```

**影響範囲の把握**:

| 情報 | 影響範囲 | リスクレベル |
|------|---------|------------|
| **Xserver DB認証情報** | WordPress DB（5サイト分）にアクセス可能 | 🔴 High |
| **Xserver SSH認証情報** | Xserver全ファイル・全DBにアクセス可能 | 🔴 High |
| **Dell DB認証情報** | Dell側WordPress DB（移行後）にアクセス可能 | 🔴 High |
| **.htaccess内容** | セキュリティルール、リダイレクト設定が判明 | 🟡 Medium |
| **ディレクトリ構造** | ファイルパス、構成が判明 | 🟢 Low |

**移行期間中のセキュリティ方針**:
- ⚠️ **認証情報は移行作業中のみ保持**（Phase E完了まで）
- ⚠️ **作業者以外のアクセス禁止**（`chmod 600`, ディレクトリ`chmod 700`）
- ⚠️ **Git管理外を徹底**（`.gitignore`適用確認を毎日実施）
- ✅ **Phase E完了後、即座にPhase Fへ移行**（セキュリティ強化）

---

### Phase A-0-2: プラグイン・テーマ情報確認

**目的**: 移行時の互換性問題を事前把握

#### ステップ 1: WordPress管理画面でプラグイン一覧確認

**実行アクション**:
1. 各サイトのWordPress管理画面へログイン
2. 「プラグイン」→「インストール済みプラグイン」を開く
3. 有効化されているプラグインをリスト化

**記録すべき情報**:
- プラグイン名
- バージョン
- 有効/無効状態
- **特に重要**: キャッシュ系、セキュリティ系、CDN連携系プラグイン

**記録フォーマット** (`claudedocs/xserver-plugins.md`):
```markdown
# Xserver プラグイン調査結果

## kuma8088.com
- WP Super Cache (1.9.0) - 有効
- Yoast SEO (21.0) - 有効
- Contact Form 7 (5.8) - 有効
- [その他リスト化]

## courses.kuma8088.com
- [同様に記録]
```

#### ステップ 2: テーマ情報確認

**実行アクション**:
1. 「外観」→「テーマ」を開く
2. 現在有効なテーマ名とバージョンを記録

---

### Phase A-0-3: 移行方法の選択

**判断基準**: 以下のフローチャートに従って各サイトの移行方法を決定

```
サイト合計サイズ確認
    ├─ <500MB
    │   └─ 方法A: WPvivid GUI移行（簡単、GUI操作）
    │
    ├─ 500MB 〜 3GB
    │   └─ 方法B: WPvivid分割移行（安定、自動分割）
    │
    ├─ >3GB
    │   └─ 方法C: SSH/rsyncスクリプト移行（確実、完全制御）
    │
    └─ 7サイト一括自動化希望
        └─ 方法D: Migrate Guru自動移行（効率、サーバー間直結）
```

**選択結果の記録** (`claudedocs/xserver-site-sizes.md` の「移行方法」列):
```markdown
| サイト名 | Xserverパス | ディスク使用量 | DB推定サイズ | 合計 | 移行方法 |
|---------|-------------|--------------|------------|------|---------|
| kuma8088.com | `~/kuma8088.com/public_html/` | 320 MB | 15 MB | 335 MB | **方法A: WPvivid GUI** |
| fx-trader-life.com | `~/fx-trader-life.com/public_html/` | 450 MB | 20 MB | 470 MB | **方法A: WPvivid GUI** |
| toyota-phv.jp | `~/toyota-phv.jp/public_html/` | 280 MB | 12 MB | 292 MB | **方法A: WPvivid GUI** |
| webmakeprofit.org | `~/webmakeprofit.org/public_html/` | 350 MB | 18 MB | 368 MB | **方法A: WPvivid GUI** |
| webmakesprofit.com | `~/webmakesprofit.com/public_html/` | 400 MB | 22 MB | 422 MB | **方法A: WPvivid GUI** |
| courses.kuma8088.com | `~/kuma8088.com/subdomains/courses/` (※確認必要) | 1.2 GB | 45 MB | 1.25 GB | **方法B: WPvivid分割** |
| courses.fx-trader-life.com | `~/fx-trader-life.com/subdomains/courses/` (※確認必要) | 1.5 GB | 50 MB | 1.55 GB | **方法B: WPvivid分割** |

※ サブドメインのパスは Phase A-0 Step 2 で `ls -la ~/kuma8088.com/` を実行して実際の構造を確認してください
```

---

## 3. 方法A: WPvivid GUI移行

### 3.1 前提条件

- ✅ サイト合計サイズ: **<500MB**
- ✅ Xserver側でプラグインインストール可能
- ✅ Dell側でプラグインインストール可能
- ✅ ZIPファイルのダウンロード・アップロードが可能

### 3.2 メリット/注意点

**メリット**:
- 🎯 GUI操作で簡単、技術知識不要
- 🎯 失敗時のリトライが容易
- 🎯 URL・パス自動書き換え
- 🎯 完全無料、容量制限なし（分割対応）

**注意点**:
- ⚠️ 500MB超えると処理に時間がかかる（方法Bへ移行推奨）
- ⚠️ Xserver側のタイムアウト設定に依存

### 3.3 手順

#### ステップ A-1: Xserver側でWPvividインストール

**実行アクション**:
1. Xserver側WordPressにログイン（例: https://kuma8088.com/wp-admin/）
2. 「プラグイン」→「新規追加」
3. 検索: `WPvivid Backup Plugin`
4. 「今すぐインストール」→「有効化」

#### ステップ A-2: バックアップ実行

**実行アクション**:
1. WordPress管理画面左メニュー: 「WPvivid Backup」
2. 「Backup & Restore」タブを開く
3. バックアップ設定:
   - **Backup Content**: "Backup WordPress core files, Themes, Plugins, Uploads, Database"
   - **Backup to**: "Localhost"（デフォルト）
4. **Backup Now** をクリック

**期待される出力**:
```
Backup started...
Creating backup list...
Backing up database...
Backing up files...
Backup completed successfully!
Backup file: wpvivid-xxxxx_kuma8088_2025-11-08-15-30_backup.zip
```

**検証項目**:
- **アクション**: 「Backups」タブで作成されたZIPファイルを確認
- **期待結果**: ZIPファイルが表示され、サイズが合計サイズと近い値
- **失敗時**: エラーメッセージを確認、タイムアウトなら方法Bへ

#### ステップ A-3: バックアップファイルのダウンロード

**実行アクション**:
1. 「Backups」タブでZIPファイルの横にある「Download」をクリック
2. ローカルPCにダウンロード（例: `~/Downloads/wpvivid-xxxxx_kuma8088_2025-11-08-15-30_backup.zip`）

**検証項目**:
- **アクション**: ダウンロードしたZIPファイルのサイズ確認
- **期待結果**: Phase A-0で調査したサイズと一致
- **失敗時**: 再度ダウンロード実行

#### ステップ A-4: Dell側でWPvividインストール

**実行アクション**:
1. Dell側WordPress（例: https://kuma8088.com/wp-admin/）にログイン
2. 「プラグイン」→「新規追加」
3. 検索: `WPvivid Backup Plugin`
4. 「今すぐインストール」→「有効化」

#### ステップ A-5: バックアップファイルのアップロード

**方法1: WPvivid GUIでアップロード**:
1. Dell側WordPress管理画面: 「WPvivid Backup」→「Backup & Restore」
2. **Upload** タブを開く
3. 「Choose File」でローカルのZIPファイルを選択
4. **Upload** をクリック

**方法2: SCPで直接転送**（推奨、高速）:
```bash
# ローカルPCからDellへSCP転送
scp ~/Downloads/wpvivid-xxxxx_kuma8088_2025-11-08-15-30_backup.zip \
  <user>@<dell-ip>:/mnt/backup-hdd/blog/sites/kuma8088/wp-content/wpvivid-backup/

# Dellでパーミッション修正
ssh <user>@<dell-ip>
cd /mnt/backup-hdd/blog/sites/kuma8088/wp-content/wpvivid-backup/
sudo chown -R 33:33 wpvivid-xxxxx_kuma8088_2025-11-08-15-30_backup.zip
```

**検証項目**:
- **アクション**: Dell側WPvivid「Backups」タブでアップロードしたZIPが表示されるか確認
- **期待結果**: ZIPファイルが一覧に表示される

#### ステップ A-6: リストア実行

**⚠️ 重要**: この操作は既存のWordPressデータを上書きします。必ず事前にバックアップを取得してください。

**実行アクション**:
1. Dell側WPvivid「Backups」タブ
2. アップロードしたZIPファイルの横にある「Restore」をクリック
3. 確認ダイアログで **Restore** を再度クリック

**期待される出力**:
```
Restore started...
Extracting backup files...
Restoring database...
Restoring files...
Restore completed successfully!
```

**検証項目**:
- **アクション**: ブラウザで https://kuma8088.com へアクセス
- **期待結果**: Xserver側と同じデザイン・コンテンツが表示される
- **失敗時**: ログ確認（ステップA-8）、必要に応じてロールバック

#### ステップ A-7: 動作確認

**確認項目**:
1. **フロントエンド表示**: トップページ、記事ページ、カテゴリページ
2. **画像表示**: メディアライブラリ、記事内画像
3. **パーマリンク**: 記事URLがXserver側と一致しているか
4. **管理画面ログイン**: Xserver側と同じ認証情報でログイン可能か
5. **プラグイン動作**: コンタクトフォーム、検索機能等

**実行コマンド** (データベース確認):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

# サイトURL確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "USE blog_db_kuma8088; SELECT option_value FROM wp_options WHERE option_name='siteurl';"

# 投稿数確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "USE blog_db_kuma8088; SELECT COUNT(*) FROM wp_posts WHERE post_status='publish' AND post_type='post';"
```

**期待される出力**:
```
+---------------------------+
| option_value              |
+---------------------------+
| https://kuma8088.com      |
+---------------------------+

+----------+
| COUNT(*) |
+----------+
|       45 |  ← Xserver側と一致すること
+----------+
```

#### ステップ A-8: エラー時のログ確認

**実行アクション**:
1. Dell側WPvivid「Logs」タブを開く
2. 最新のログエントリを確認
3. エラーメッセージをコピーして保存

**よくあるエラーと対処**:
- `Maximum execution time exceeded`: PHPタイムアウト → `config/php/php.ini`の`max_execution_time`を600に増やす
- `Allowed memory size exhausted`: メモリ不足 → `memory_limit`を512Mに増やす

---

## 4. 方法B: WPvivid分割移行

### 4.1 前提条件

- ✅ サイト合計サイズ: **500MB 〜 3GB**
- ✅ 方法Aと同じ前提条件

### 4.2 メリット/注意点

**メリット**:
- 🎯 大容量サイトでも自動分割で安定動作
- 🎯 タイムアウト回避
- 🎯 方法Aと同じGUI操作

**注意点**:
- ⚠️ 分割ZIPファイル数が多いとアップロード手間増加
- ⚠️ 3GB超えると処理時間が長い（方法Cへ移行推奨）

### 4.3 手順

#### ステップ B-1〜B-3: 方法Aと同じ

WPvividインストール、バックアップ実行、ダウンロードは方法Aと同じ手順。

**違い**: バックアップ設定で**分割オプション**を有効化

#### ステップ B-4: 分割バックアップ設定

**実行アクション** (Xserver側):
1. WPvivid「Settings」タブを開く
2. **Backup & Restore** セクション
3. **Split backup archive**: **Enabled**
4. **Split size**: `2048 MB`（2GB、デフォルトのまま）
5. **Save Changes**

#### ステップ B-5: バックアップ実行（分割）

**実行アクション**:
1. 「Backup & Restore」タブで **Backup Now** をクリック
2. 分割処理が自動実行される

**期待される出力**:
```
Backup started...
Creating backup list...
Backing up database...
Backing up files...
Splitting archive into 2GB parts...
Part 1/3 created: wpvivid-xxxxx_kuma8088_part1.zip
Part 2/3 created: wpvivid-xxxxx_kuma8088_part2.zip
Part 3/3 created: wpvivid-xxxxx_kuma8088_part3.zip
Backup completed successfully!
```

#### ステップ B-6: 分割ファイル全てをダウンロード

**実行アクション**:
1. 「Backups」タブで分割されたZIPファイル（part1, part2, part3...）を**全て**ダウンロード
2. ローカルPC上で同じディレクトリに保存

**検証項目**:
- **アクション**: ダウンロードしたファイル数が表示された分割数と一致するか確認
- **期待結果**: 3分割なら3ファイル全て存在
- **失敗時**: 不足ファイルを再ダウンロード

#### ステップ B-7: Dell側へ分割ファイル全てアップロード

**方法1: WPvivid GUIで順次アップロード**:
1. Dell側WPvivid「Upload」タブ
2. part1.zip → Upload
3. part2.zip → Upload
4. part3.zip → Upload

**方法2: SCPで一括転送**（推奨）:
```bash
# 全分割ファイルを一括転送
scp ~/Downloads/wpvivid-xxxxx_kuma8088_part*.zip \
  <user>@<dell-ip>:/mnt/backup-hdd/blog/sites/kuma8088/wp-content/wpvivid-backup/

# パーミッション修正
ssh <user>@<dell-ip>
cd /mnt/backup-hdd/blog/sites/kuma8088/wp-content/wpvivid-backup/
sudo chown -R 33:33 wpvivid-xxxxx_kuma8088_part*.zip
```

#### ステップ B-8〜B-10: 方法Aと同じ

リストア実行、動作確認、エラー時のログ確認は方法Aと同じ手順。

**違い**: WPvividが自動的に分割ファイルを結合してリストア

---

## 5. 方法C: SSH/rsyncスクリプト移行

### 5.1 前提条件

- ✅ サイト合計サイズ: **>3GB** または完全制御希望
- ✅ Xserver SSHアクセス可能
- ✅ Dell SSH/SCPアクセス可能
- ✅ mysqldump, rsync コマンド利用可能

### 5.2 メリット/注意点

**メリット**:
- 🎯 容量無制限
- 🎯 プログレス可視化、中断・再開可能
- 🎯 スクリプト化で7サイト自動化容易
- 🎯 タイムアウト・メモリ制限なし
- 🎯 完全制御、透明性高い

**注意点**:
- ⚠️ コマンドライン操作必須
- ⚠️ wp-config.php、.htaccess の手動調整必要
- ⚠️ URL置換を手動実行（Search-Replace-DB等）

### 5.3 手順

#### ステップ C-1: Xserver側でデータベースダンプ

**実行コマンド** (Xserver SSH接続):
```bash
# Xserverへ接続
ssh <xserver-username>@<xserver-host>

# データベース情報確認（wp-config.phpから取得）
cd ~/kuma8088.com/public_html
grep DB_ wp-config.php

# 出力例:
# define('DB_NAME', 'xserver_wp1');
# define('DB_USER', 'xserver_user');
# define('DB_PASSWORD', 'xserver_pass');
# define('DB_HOST', 'mysql123.xserver.jp');

# データベースダンプ（gzip圧縮）
mysqldump -h mysql123.xserver.jp \
  -u xserver_user \
  -p'xserver_pass' \
  xserver_wp1 \
  --single-transaction \
  --quick \
  --lock-tables=false \
  | gzip > ~/kuma8088_db_$(date +%Y%m%d).sql.gz

# ファイルサイズ確認
ls -lh ~/kuma8088_db_*.sql.gz
```

**期待される出力**:
```
-rw-r--r-- 1 user user 15M Nov  8 15:30 kuma8088_db_20251108.sql.gz
```

**検証項目**:
- **アクション**: ダンプファイルが正常に作成されているか確認
- **期待結果**: ファイルサイズがPhase A-0調査のDBサイズと近い値（gzip圧縮で1/5〜1/10）
- **失敗時**: パスワード確認、接続先ホスト確認

#### ステップ C-2: Dell側へデータベースダンプ転送

**実行コマンド** (ローカルPCまたはDell):
```bash
# Xserver → Dell 直接転送
ssh <xserver-username>@<xserver-host> \
  "cat ~/kuma8088_db_20251108.sql.gz" | \
  ssh <dell-user>@<dell-ip> \
  "cat > /tmp/kuma8088_db_20251108.sql.gz"

# または2段階転送（ローカルPC経由）
# 1. Xserver → ローカルPC
scp <xserver-username>@<xserver-host>:~/kuma8088_db_20251108.sql.gz \
  ~/Downloads/

# 2. ローカルPC → Dell
scp ~/Downloads/kuma8088_db_20251108.sql.gz \
  <dell-user>@<dell-ip>:/tmp/
```

**検証項目**:
- **アクション**: Dell側で `ls -lh /tmp/kuma8088_db_20251108.sql.gz`
- **期待結果**: ファイルが存在し、サイズが一致

#### ステップ C-3: Dell側でデータベースインポート

**実行コマンド** (Dell SSH接続):
```bash
# Dellへ接続
ssh <dell-user>@<dell-ip>

# .envから認証情報取得
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

# データベースクリア（既存データ削除、注意！）
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "DROP DATABASE IF EXISTS blog_db_kuma8088; CREATE DATABASE blog_db_kuma8088 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 権限再付与
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "GRANT ALL PRIVILEGES ON blog_db_kuma8088.* TO 'blog_user'@'%'; FLUSH PRIVILEGES;"

# データベースインポート
gunzip < /tmp/kuma8088_db_20251108.sql.gz | \
docker compose exec -T mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" blog_db_kuma8088

# インポート確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "USE blog_db_kuma8088; SELECT COUNT(*) FROM wp_posts WHERE post_status='publish';"
```

**期待される出力**:
```
+----------+
| COUNT(*) |
+----------+
|       45 |  ← Xserver側と一致
+----------+
```

#### ステップ C-4: Xserver側でファイル同期準備

**実行コマンド** (Xserver SSH接続):
```bash
# Xserver公開ディレクトリ確認
cd ~/kuma8088.com/public_html
pwd
# 出力: /home/xserver-username/kuma8088.com/public_html

# ファイル数確認
find . -type f | wc -l
# 出力: 3542

# ディスクサイズ確認
du -sh .
# 出力: 320M
```

#### ステップ C-5: rsyncでファイル同期

**方法1: 全サイト一括スクリプト（推奨）**

**実行コマンド** (Dell SSH接続):
```bash
# Dellへ接続
ssh <dell-user>@<dell-ip>

# 全サイト一括rsyncスクリプト作成
cat > /tmp/rsync-all-sites.sh << 'EOF'
#!/bin/bash
set -euo pipefail

XSERVER_USER="<xserver-username>"
XSERVER_HOST="<xserver-host>"

# サイトマッピング（サイト名:Xserverパス:Dell保存先）
declare -A SITES=(
  ["kuma8088"]="kuma8088.com/public_html"
  ["fx-trader-life"]="fx-trader-life.com/public_html"
  ["toyota-phv"]="toyota-phv.jp/public_html"
  ["webmakeprofit"]="webmakeprofit.org/public_html"
  ["webmakesprofit"]="webmakesprofit.com/public_html"
  # サブドメイン（存在する場合は以下のコメント解除）
  # ["courses-kuma8088"]="kuma8088.com/subdomains/courses/public_html"
  # ["courses-fx-trader-life"]="fx-trader-life.com/subdomains/courses/public_html"
)

for SITE_NAME in "${!SITES[@]}"; do
  XSERVER_PATH="${SITES[$SITE_NAME]}"
  DELL_PATH="/mnt/backup-hdd/blog/sites/${SITE_NAME}"

  echo "======================================"
  echo "Syncing: ${SITE_NAME}"
  echo "From: ~/${XSERVER_PATH}"
  echo "To: ${DELL_PATH}"
  echo "======================================"

  # ディレクトリ作成
  sudo mkdir -p "${DELL_PATH}"
  sudo chown -R 33:33 "${DELL_PATH}"

  # rsync同期
  rsync -avz \
    --progress \
    --delete \
    --stats \
    "${XSERVER_USER}@${XSERVER_HOST}:~/${XSERVER_PATH}/" \
    "${DELL_PATH}/" \
    || { echo "❌ Failed: ${SITE_NAME}"; continue; }

  # ファイル数確認
  FILE_COUNT=$(find "${DELL_PATH}" -type f | wc -l)
  echo "✅ Completed: ${SITE_NAME} (${FILE_COUNT} files)"
  echo ""
done

echo "======================================"
echo "All sites synced successfully!"
echo "======================================"
EOF

chmod +x /tmp/rsync-all-sites.sh

# スクリプト実行
/tmp/rsync-all-sites.sh
```

**方法2: 単一サイトrsync（個別実行時）**

```bash
# 同期先ディレクトリ確認・作成
sudo mkdir -p /mnt/backup-hdd/blog/sites/kuma8088
sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/kuma8088

# rsync同期実行（Xserver → Dell）
# 実際のXserverディレクトリ構造:
#   ~/kuma8088.com/public_html/           ← kuma8088.com
#   ~/kuma8088.com/subdomains/courses/    ← courses.kuma8088.com（存在する場合）
#   ~/fx-trader-life.com/public_html/     ← fx-trader-life.com
#   ~/toyota-phv.jp/public_html/          ← toyota-phv.jp
#   ~/webmakeprofit.org/public_html/      ← webmakeprofit.org
#   ~/webmakesprofit.com/public_html/     ← webmakesprofit.com

rsync -avz \
  --progress \
  --delete \
  <xserver-username>@<xserver-host>:~/kuma8088.com/public_html/ \
  /mnt/backup-hdd/blog/sites/kuma8088/

# 同期確認
ls -la /mnt/backup-hdd/blog/sites/kuma8088/
```

**期待される出力**:
```
receiving incremental file list
./
index.php
wp-config.php
wp-content/
wp-content/uploads/
...
sent 1,234 bytes  received 335,544,321 bytes  1,234,567.89 bytes/sec
total size is 335,544,321  speedup is 1.00
```

**検証項目** (方法1を実行した場合):
- **アクション**: スクリプト出力で各サイトの `✅ Completed` が表示されるか確認
- **期待結果**: 全5サイト（+サブドメイン）が成功メッセージ表示
- **確認コマンド**:
  ```bash
  # 各サイトのファイル数確認
  for site in kuma8088 fx-trader-life toyota-phv webmakeprofit webmakesprofit; do
    echo -n "$site: "
    find /mnt/backup-hdd/blog/sites/$site/ -type f 2>/dev/null | wc -l
  done
  ```

**検証項目** (方法2を実行した場合):
- **アクション**: ファイル数がXserver側と一致するか確認
  ```bash
  find /mnt/backup-hdd/blog/sites/kuma8088/ -type f | wc -l
  ```
- **期待結果**: Xserver側と同じファイル数（例: 3542）

#### ステップ C-6: wp-config.php書き換え

**実行コマンド** (Dell):
```bash
# wp-config.phpバックアップ
sudo cp /mnt/backup-hdd/blog/sites/kuma8088/wp-config.php \
        /mnt/backup-hdd/blog/sites/kuma8088/wp-config.php.xserver.bak

# データベース接続情報を書き換え
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

sudo tee /tmp/wp-config-patch.php << 'EOF'
<?php
// WordPress wp-config.php database settings patch for Dell environment

define('DB_NAME', 'blog_db_kuma8088');
define('DB_USER', 'blog_user');
define('DB_PASSWORD', getenv('MYSQL_PASSWORD'));  // 環境変数から取得
define('DB_HOST', 'mariadb:3306');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', 'utf8mb4_unicode_ci');
EOF

# wp-config.phpを編集（手動）
sudo vi /mnt/backup-hdd/blog/sites/kuma8088/wp-config.php
```

**編集内容** (wp-config.php):
```php
// 以下の行を変更
// 旧（Xserver）:
// define('DB_NAME', 'xserver_wp1');
// define('DB_USER', 'xserver_user');
// define('DB_PASSWORD', 'xserver_pass');
// define('DB_HOST', 'mysql123.xserver.jp');

// 新（Dell）:
define('DB_NAME', 'blog_db_kuma8088');
define('DB_USER', 'blog_user');
define('DB_PASSWORD', '<.envのMYSQL_PASSWORDの値をここにコピー>');
define('DB_HOST', 'mariadb:3306');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', 'utf8mb4_unicode_ci');
```

**検証項目**:
- **アクション**: `sudo cat /mnt/backup-hdd/blog/sites/kuma8088/wp-config.php | grep DB_`
- **期待結果**: 新しいDB接続情報が設定されている

#### ステップ C-7: データベース内URL置換

**背景**: WordPressはDBに絶対URLを保存するため、Xserver → Dell移行時にURL置換が必要

**方法1: WP-CLIで置換**（推奨）:
```bash
# .envから情報取得
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

# 旧URL確認
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp option get siteurl \
    --path=/var/www/html/kuma8088

# 出力: http://kuma8088.com（Xserver側URL）

# URL置換実行（DRY RUN、実際には変更しない）
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'http://kuma8088.com' \
    'https://kuma8088.com' \
    --path=/var/www/html/kuma8088 \
    --dry-run

# 出力確認後、本番実行（--dry-runを削除）
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'http://kuma8088.com' \
    'https://kuma8088.com' \
    --path=/var/www/html/kuma8088

# 置換確認
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp option get siteurl \
    --path=/var/www/html/kuma8088

# 出力: https://kuma8088.com（Dell側URL）
```

**方法2: Search-Replace-DBスクリプト**（WP-CLI不可の場合）:
```bash
# Search-Replace-DBダウンロード
cd /tmp
wget https://github.com/interconnectit/Search-Replace-DB/archive/refs/heads/master.zip
unzip master.zip
sudo mv Search-Replace-DB-master /mnt/backup-hdd/blog/sites/kuma8088/search-replace-db

# ブラウザでアクセス
# http://<dell-ip>:8080/search-replace-db/
# 1. 旧URL: http://kuma8088.com
# 2. 新URL: https://kuma8088.com
# 3. 「dry run」で確認 → 「live run」で実行

# 完了後、セキュリティのため削除
sudo rm -rf /mnt/backup-hdd/blog/sites/kuma8088/search-replace-db
```

#### ステップ C-8: パーミッション修正

**実行コマンド** (Dell):
```bash
# www-data (UID:33) に所有権変更
sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/kuma8088/

# ディレクトリ: 755、ファイル: 644
sudo find /mnt/backup-hdd/blog/sites/kuma8088/ -type d -exec chmod 755 {} \;
sudo find /mnt/backup-hdd/blog/sites/kuma8088/ -type f -exec chmod 644 {} \;

# wp-config.php: 600（セキュリティ強化）
sudo chmod 600 /mnt/backup-hdd/blog/sites/kuma8088/wp-config.php
```

#### ステップ C-9: 動作確認

**確認項目**:
1. **フロントエンド表示**: https://kuma8088.com へアクセス
2. **画像表示**: 記事内画像、メディアライブラリ
3. **管理画面ログイン**: https://kuma8088.com/wp-admin/
4. **パーマリンク**: 記事URL確認

**実行コマンド** (動作確認):
```bash
# Nginxアクセスログ確認
docker compose logs nginx | grep kuma8088 | tail -20

# PHP-FPMエラーログ確認
docker compose logs wordpress | grep -i error | tail -20

# データベース接続確認
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp db check \
    --path=/var/www/html/kuma8088
```

---

### 5.4 スクリプト化（7サイト自動化）

#### スクリプト例: `scripts/migrate-site.sh`

**実行コマンド** (作成):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

cat > scripts/migrate-site.sh << 'SCRIPT_EOF'
#!/bin/bash
# Single site migration script (Xserver → Dell)
# Usage: ./migrate-site.sh <site-name> <xserver-db-name> <xserver-db-user> <xserver-db-pass> <xserver-db-host> <xserver-site-path>
#
# Examples:
#   ./migrate-site.sh kuma8088 xserver_wp1 user pass mysql.xserver.jp kuma8088.com/public_html
#   ./migrate-site.sh courses-kuma8088 xserver_wp2 user pass mysql.xserver.jp kuma8088.com/subdomains/courses/public_html

set -euo pipefail

SITE_NAME="$1"
XSERVER_DB_NAME="$2"
XSERVER_DB_USER="$3"
XSERVER_DB_PASS="$4"
XSERVER_DB_HOST="$5"
XSERVER_SITE_PATH="$6"  # Actual path on Xserver (e.g., kuma8088.com/public_html or kuma8088.com/subdomains/courses/public_html)

XSERVER_USER="${XSERVER_USER:-xserver-username}"
XSERVER_HOST="${XSERVER_HOST:-xserver-host}"
DELL_USER="${DELL_USER:-dell-user}"
DELL_IP="${DELL_IP:-dell-ip}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$HOME/.blog-migration-${SITE_NAME}-${TIMESTAMP}.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting migration for site: $SITE_NAME"

# Step 1: Database dump on Xserver
log "Step 1: Dumping database on Xserver..."
ssh "$XSERVER_USER@$XSERVER_HOST" \
  "mysqldump -h $XSERVER_DB_HOST -u $XSERVER_DB_USER -p'$XSERVER_DB_PASS' $XSERVER_DB_NAME --single-transaction --quick | gzip > ~/migration_${SITE_NAME}_db_${TIMESTAMP}.sql.gz"

# Step 2: Transfer database dump to Dell
log "Step 2: Transferring database dump to Dell..."
ssh "$XSERVER_USER@$XSERVER_HOST" \
  "cat ~/migration_${SITE_NAME}_db_${TIMESTAMP}.sql.gz" | \
  ssh "$DELL_USER@$DELL_IP" \
  "cat > /tmp/migration_${SITE_NAME}_db_${TIMESTAMP}.sql.gz"

# Step 3: Import database on Dell
log "Step 3: Importing database on Dell..."
ssh "$DELL_USER@$DELL_IP" bash -c "
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

DB_NAME=\"blog_db_\${SITE_NAME//-/_}\"

docker compose exec -T mariadb mysql -uroot -p\"\${MYSQL_ROOT_PASSWORD}\" \\
  -e \"DROP DATABASE IF EXISTS \$DB_NAME; CREATE DATABASE \$DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\"

docker compose exec -T mariadb mysql -uroot -p\"\${MYSQL_ROOT_PASSWORD}\" \\
  -e \"GRANT ALL PRIVILEGES ON \$DB_NAME.* TO 'blog_user'@'%'; FLUSH PRIVILEGES;\"

gunzip < /tmp/migration_${SITE_NAME}_db_${TIMESTAMP}.sql.gz | \\
docker compose exec -T mariadb mysql -uroot -p\"\${MYSQL_ROOT_PASSWORD}\" \$DB_NAME

rm /tmp/migration_${SITE_NAME}_db_${TIMESTAMP}.sql.gz
"

# Step 4: Rsync files
log "Step 4: Syncing files with rsync..."
ssh "$DELL_USER@$DELL_IP" \
  "sudo mkdir -p /mnt/backup-hdd/blog/sites/$SITE_NAME && sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/$SITE_NAME"

rsync -avz --progress --delete \
  "$XSERVER_USER@$XSERVER_HOST:~/$XSERVER_SITE_PATH/" \
  "$DELL_USER@$DELL_IP:/mnt/backup-hdd/blog/sites/$SITE_NAME/"

log "Migration completed for site: $SITE_NAME"
log "Next steps:"
log "1. Edit wp-config.php on Dell: /mnt/backup-hdd/blog/sites/$SITE_NAME/wp-config.php"
log "2. Run URL replacement with WP-CLI"
log "3. Verify site at: https://${SITE_NAME}.com"
SCRIPT_EOF

chmod +x scripts/migrate-site.sh
```

**使用例**:
```bash
# 環境変数設定
export XSERVER_USER="xserver-username"
export XSERVER_HOST="xserver-host"
export DELL_USER="dell-user"
export DELL_IP="dell-ip"

# 1. kuma8088.com 移行
./scripts/migrate-site.sh \
  kuma8088 \
  xserver_wp1 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  kuma8088.com/public_html

# 2. fx-trader-life.com 移行
./scripts/migrate-site.sh \
  fx-trader-life \
  xserver_wp2 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  fx-trader-life.com/public_html

# 3. toyota-phv.jp 移行
./scripts/migrate-site.sh \
  toyota-phv \
  xserver_wp3 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  toyota-phv.jp/public_html

# 4. webmakeprofit.org 移行
./scripts/migrate-site.sh \
  webmakeprofit \
  xserver_wp4 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  webmakeprofit.org/public_html

# 5. webmakesprofit.com 移行
./scripts/migrate-site.sh \
  webmakesprofit \
  xserver_wp5 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  webmakesprofit.com/public_html

# サブドメイン移行例（存在する場合）
# courses.kuma8088.com
./scripts/migrate-site.sh \
  courses-kuma8088 \
  xserver_wp6 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  kuma8088.com/subdomains/courses/public_html

# courses.fx-trader-life.com
./scripts/migrate-site.sh \
  courses-fx-trader-life \
  xserver_wp7 \
  xserver_user \
  xserver_pass \
  mysql123.xserver.jp \
  fx-trader-life.com/subdomains/courses/public_html

# 注: Phase A-0 Step 2 でサブドメインディレクトリ構造を確認してください
# ssh xserver-username@xserver-host "ls -la ~/kuma8088.com/"
```

---

## 6. 方法D: Migrate Guru自動移行

### 6.1 前提条件

- ✅ **7サイト一括自動化希望**
- ✅ Dell側で一時的に外部公開URL提供可能（Cloudflare Tunnel）
- ✅ Xserver側でプラグインインストール可能
- ✅ Dell側でプラグインインストール可能

### 6.2 メリット/注意点

**メリット**:
- 🎯 サーバー間直結コピー（ダウンロード・アップロード不要）
- 🎯 容量無制限（最大100GB）
- 🎯 URL・パス自動書き換え
- 🎯 サーバー設定自動調整（タイムアウト回避）
- 🎯 7サイト繰り返しが効率的

**注意点**:
- ⚠️ Dell側に一時的に外部公開URL必須
- ⚠️ Migrate Guruのクラウド経由（プライバシー懸念がある場合は方法C推奨）
- ⚠️ 転送中はXserver/Dell両方のサイトが一時的に利用不可

### 6.3 手順

#### ステップ D-1: Dell側でCloudflare Tunnel一時公開設定

**前提**: 03_installation.md Phase Cが完了し、Cloudflare Tunnelが稼働中

**実行アクション** (Cloudflare Zero Trust ダッシュボード):
1. **Tunnels** → `blog-dell-workstation` を選択
2. **Public Hostname** タブ
3. **Add a public hostname** をクリック
4. 設定:
   - **Subdomain**: (空欄)
   - **Domain**: `kuma8088.com`
   - **Service Type**: `HTTP`
   - **Service URL**: `blog-nginx:80`
5. **Save hostname**

**検証項目**:
- **アクション**: ブラウザで https://kuma8088.com へアクセス
- **期待結果**: Dell側WordPress（空または03_installation.mdで作成したテスト投稿）が表示される
- **失敗時**: Cloudflare Tunnel状態確認、Public Hostname設定確認

#### ステップ D-2: Xserver側でMigrate Guruインストール

**実行アクション**:
1. Xserver側WordPress（例: https://old-kuma8088.xserver.jp/wp-admin/）にログイン
2. 「プラグイン」→「新規追加」
3. 検索: `Migrate Guru`
4. 「今すぐインストール」→「有効化」

#### ステップ D-3: Dell側でMigrate Guruインストール

**実行アクション**:
1. Dell側WordPress（https://kuma8088.com/wp-admin/）にログイン
2. 同様に「Migrate Guru」をインストール・有効化

#### ステップ D-4: Migrate Guru設定とメール認証

**実行アクション** (Xserver側):
1. WordPress管理画面左メニュー: 「Migrate Guru」
2. メールアドレス入力（移行通知受信用）
3. 受信したメールのリンクをクリックして認証

#### ステップ D-5: 移行先URL入力と実行

**実行アクション** (Xserver側):
1. Migrate Guru設定画面
2. **Destination Site URL**: `https://kuma8088.com` （Dell側URL）
3. **Advanced Options**（任意）:
   - **Skip media files**: チェックしない（全ファイル転送）
   - **Skip themes**: チェックしない
   - **Skip plugins**: チェックしない
4. **Migrate** をクリック

**期待される出力**:
```
Migration started...
Uploading database...
Uploading files...
Processing: 25% (約5-30分、サイズによる)
Processing: 50%
Processing: 75%
Processing: 100%
Migration completed successfully!
```

**検証項目**:
- **アクション**: メール通知を確認
- **期待結果**: "Migration completed successfully" メールが届く
- **失敗時**: エラーメッセージ確認、ログ確認

#### ステップ D-6: 動作確認

**確認項目**:
1. **フロントエンド表示**: https://kuma8088.com へアクセス（Dell側）
2. **Xserver側と比較**: デザイン・コンテンツが一致しているか
3. **画像表示**: メディアライブラリ、記事内画像
4. **管理画面ログイン**: https://kuma8088.com/wp-admin/

**実行コマンド** (Dell):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

# 投稿数確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "USE blog_db_kuma8088; SELECT COUNT(*) FROM wp_posts WHERE post_status='publish';"

# URL確認
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp option get siteurl \
    --path=/var/www/html/kuma8088
```

**期待される出力**:
```
+----------+
| COUNT(*) |
+----------+
|       45 |  ← Xserver側と一致
+----------+

https://kuma8088.com  ← Dell側URL
```

#### ステップ D-7: Migrate Guruプラグイン削除

**実行アクション** (Dell側):
1. WordPress管理画面: 「プラグイン」→「インストール済みプラグイン」
2. Migrate Guruを「停止」→「削除」

**理由**: 移行完了後は不要、セキュリティリスク削減

#### ステップ D-8: Cloudflare Tunnel一時公開解除（任意）

**実行アクション**:
- DNS切替前（Phase E前）: Public Hostnameを残す（検証継続のため）
- DNS切替後（Phase E後）: 既にDNSがDell側を向いているため、Public Hostnameは削除不要

---

## 7. Phase C: 1サイト目テスト移行

### Phase C-1: kuma8088.com テスト移行

**目的**: 1サイト目で移行手順を確立し、残り6サイトに適用

#### ステップ C-1: Phase A-0結果に基づく方法選択

**実行アクション**:
1. `claudedocs/xserver-site-sizes.md` で kuma8088.com の移行方法を確認
2. 該当する方法（A/B/C/D）の手順を実行

**例**:
```markdown
| サイト名 | ディスク使用量 | DB推定サイズ | 合計 | 移行方法 |
|---------|--------------|------------|------|---------|
| kuma8088.com | 320 MB | 15 MB | 335 MB | **方法A: WPvivid GUI** |
```
→ **方法A**（セクション3）の手順を実行

#### ステップ C-2: 移行後検証チェックリスト

**確認項目** (必須):
- [ ] トップページが正常表示
- [ ] 記事ページが正常表示（最低3記事確認）
- [ ] 画像が正常表示（メディアライブラリ確認）
- [ ] カテゴリ・タグが正常機能
- [ ] 検索機能が動作
- [ ] コメント機能が動作（該当する場合）
- [ ] コンタクトフォームが動作（該当する場合）
- [ ] RSS/Atomフィードが生成される
- [ ] sitemap.xmlが生成される（SEOプラグイン使用時）
- [ ] 管理画面ログイン可能
- [ ] 管理画面で投稿・固定ページ編集可能
- [ ] メディアアップロード可能

**実行コマンド** (自動検証):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

cat > scripts/verify-migration.sh << 'SCRIPT_EOF'
#!/bin/bash
# Migration verification script
# Usage: ./verify-migration.sh <site-name>

SITE_NAME="$1"
SITE_URL="https://${SITE_NAME}.com"

echo "Verifying migration for: $SITE_NAME"

# 1. HTTP status check
echo -n "1. HTTP status check: "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL")
if [ "$STATUS" = "200" ]; then
    echo "✅ OK (200)"
else
    echo "❌ FAIL ($STATUS)"
fi

# 2. Image check
echo -n "2. Image loading check: "
IMAGE_COUNT=$(curl -s "$SITE_URL" | grep -o '<img[^>]*src="[^"]*"' | wc -l)
if [ "$IMAGE_COUNT" -gt 0 ]; then
    echo "✅ OK ($IMAGE_COUNT images found)"
else
    echo "⚠️  WARNING (no images found)"
fi

# 3. RSS feed check
echo -n "3. RSS feed check: "
RSS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL/feed/")
if [ "$RSS_STATUS" = "200" ]; then
    echo "✅ OK (200)"
else
    echo "❌ FAIL ($RSS_STATUS)"
fi

# 4. Database post count
echo -n "4. Database post count: "
set -a
. ./.env
set +a
DB_NAME="blog_db_${SITE_NAME//-/_}"
POST_COUNT=$(docker compose exec -T mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "USE $DB_NAME; SELECT COUNT(*) FROM wp_posts WHERE post_status='publish' AND post_type='post';" -sN)
echo "$POST_COUNT posts"

# 5. wp-admin access check
echo -n "5. wp-admin access check: "
ADMIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL/wp-admin/")
if [ "$ADMIN_STATUS" = "302" ] || [ "$ADMIN_STATUS" = "200" ]; then
    echo "✅ OK ($ADMIN_STATUS)"
else
    echo "❌ FAIL ($ADMIN_STATUS)"
fi

echo ""
echo "Verification completed for: $SITE_NAME"
SCRIPT_EOF

chmod +x scripts/verify-migration.sh

# 実行
./scripts/verify-migration.sh kuma8088
```

**期待される出力**:
```
Verifying migration for: kuma8088
1. HTTP status check: ✅ OK (200)
2. Image loading check: ✅ OK (12 images found)
3. RSS feed check: ✅ OK (200)
4. Database post count: 45 posts
5. wp-admin access check: ✅ OK (302)

Verification completed for: kuma8088
```

#### ステップ C-3: 問題発見時の対処

**よくある問題と対処**:

| 問題 | 原因 | 対処 |
|------|------|------|
| 画像が表示されない | パーミッション不足 | `sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/<site>/` |
| 404エラー | パーマリンク設定未反映 | WP管理画面「設定」→「パーマリンク設定」→「変更を保存」 |
| DB接続エラー | wp-config.php設定ミス | DB_NAME, DB_USER, DB_PASSWORD, DB_HOST確認 |
| 管理画面ログイン不可 | URL置換漏れ | WP-CLIでURL再置換実行 |

#### ステップ C-4: 手順ドキュメント化

**実行アクション**:
```bash
cat > claudedocs/migration-procedure-kuma8088.md << 'EOF'
# kuma8088.com 移行手順実績

## 実施日
2025-11-XX

## 選択した方法
方法A: WPvivid GUI移行

## 実施手順
1. [実際に実行した手順を記録]
2. [所要時間、問題点、解決方法を記載]

## 検証結果
- トップページ: ✅
- 記事ページ: ✅
- 画像表示: ✅
- 管理画面: ✅

## 教訓・改善点
- [次回移行で改善すべき点]
- [効率化のアイデア]

## 残り6サイトへの適用
- この手順を courses.kuma8088.com 以降に適用する
EOF
```

---

## 8. Phase D: 残り6サイト移行

### Phase D-1: 移行順序決定

**推奨順序**:
1. ✅ kuma8088.com（Phase Cで完了）
2. courses.kuma8088.com（サブドメイン、kuma8088と同じ方法）
3. fx-trader-life.com（メインドメイン）
4. courses.fx-trader-life.com（サブドメイン）
5. toyota-phv.jp（検討中サイト、移行判断による）
6. webmakeprofit.org（検討中サイト）
7. webmakesprofit.com（検討中サイト）

**理由**: サブドメインはメインドメインと同じ構成のため、連続実施で効率化

### Phase D-2: 各サイト移行実施

**実行フロー** (2サイト目以降):
1. `claudedocs/xserver-site-sizes.md` で移行方法確認
2. 該当する方法（A/B/C/D）の手順を実行
3. `scripts/verify-migration.sh <site-name>` で検証
4. Nginx仮想ホスト設定追加（セクション8.3）
5. Cloudflare Tunnel Public Hostname追加（セクション8.4）

### Phase D-3: Nginx仮想ホスト設定追加

**実行コマンド** (各サイト移行後に実施):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 例: courses.kuma8088.com の設定追加
cat > config/nginx/conf.d/courses-kuma8088.conf << 'EOF'
# Virtual host: courses.kuma8088.com
server {
    listen 80;
    server_name courses.kuma8088.com;

    root /var/www/html/courses-kuma8088;
    index index.php index.html;

    access_log /var/log/nginx/courses-kuma8088-access.log;
    error_log /var/log/nginx/courses-kuma8088-error.log;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;

        fastcgi_buffers 16 16k;
        fastcgi_buffer_size 32k;
        fastcgi_read_timeout 300;
    }

    location ~ /\.ht {
        deny all;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    location = /robots.txt {
        allow all;
        log_not_found off;
        access_log off;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires max;
        log_not_found off;
    }
}
EOF

# Nginx設定テスト
docker compose exec nginx nginx -t

# Nginx再読み込み
docker compose exec nginx nginx -s reload
```

### Phase D-4: Cloudflare Tunnel Public Hostname追加

**実行アクション** (Cloudflare Zero Trust ダッシュボード):
1. **Tunnels** → `blog-dell-workstation`
2. **Public Hostname** タブ → **Add a public hostname**
3. 設定（例: courses.kuma8088.com）:
   - **Subdomain**: `courses`
   - **Domain**: `kuma8088.com`
   - **Service Type**: `HTTP`
   - **Service URL**: `blog-nginx:80`
4. **Save hostname**

**検証**:
```bash
# 外部アクセス確認
curl -I https://courses.kuma8088.com
```

---

## 9. Phase E: DNS切替と本番化

### Phase E-1: DNS切替前最終確認

**確認項目** (全7サイト):
- [ ] Dell側で全サイトが正常動作
- [ ] Xserver側と内容が一致
- [ ] Cloudflare Tunnel Public Hostnameが全サイト分設定済み
- [ ] バックアップが正常取得されている
- [ ] ロールバック手順が明確

**実行コマンド** (全サイト一括検証):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

for site in kuma8088 courses-kuma8088 fx-trader-life courses-fx-trader-life toyota-phv webmakeprofit webmakesprofit; do
    echo "=== Verifying: $site ==="
    ./scripts/verify-migration.sh $site
    echo ""
done
```

### Phase E-2: TTL短縮（切替24時間前）

**目的**: DNS変更時の浸透時間を短縮

**実行アクション** (Cloudflare DNS ダッシュボード):
1. **Websites** → 対象ドメイン（例: kuma8088.com）
2. **DNS** → **Records**
3. 各レコードのTTLを **Auto** → **1 minute** に変更
4. 24時間待機

### Phase E-3: DNS切替実施

**実行アクション** (Cloudflare DNS ダッシュボード):
1. **DNS** → **Records**
2. 既存Aレコード（Xserver IP）を削除
3. CNAMEレコードを確認（Tunnel経由で自動作成済み）
   - `kuma8088.com` → `<tunnel-id>.cfargotunnel.com` (Proxied: ✅)
   - `www.kuma8088.com` → `<tunnel-id>.cfargotunnel.com` (Proxied: ✅)

**既にPublic Hostnameで設定済みの場合**: DNS設定は自動適用済み、追加作業不要

### Phase E-4: DNS浸透確認

**実行コマンド** (複数地点で確認):
```bash
# ローカルDNS確認
nslookup kuma8088.com

# 外部DNS確認（複数）
dig @8.8.8.8 kuma8088.com
dig @1.1.1.1 kuma8088.com

# DNS浸透チェックサービス利用
# https://www.whatsmydns.net/
```

**期待される結果**: CloudflareのIPアドレス（104.x.x.x等）が返される

### Phase E-5: 本番アクセス監視

**実行コマンド** (Dell):
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Nginxアクセスログをリアルタイム監視
docker compose logs -f nginx

# エラーログ監視
docker compose logs -f nginx | grep -i error

# 別ターミナルでWordPressログ監視
docker compose logs -f wordpress | grep -i error
```

**監視期間**: DNS切替後24-48時間

### Phase E-6: Xserver並行運用

**期間**: 2週間

**目的**:
- Dell側で問題発生時のロールバック可能性確保
- DNS浸透完了確認
- 移行漏れ検出

**実行アクション**:
1. Xserver側WordPressを「メンテナンスモード」に設定（新規投稿停止）
2. Dell側で新規投稿を開始
3. 毎日アクセスログ確認（Xserver側アクセスが減少していることを確認）

### Phase E-7: Xserver解約手続き

**実行タイミング**: 2週間並行運用完了後

**手順**:
1. Xserver側で最終バックアップ取得
2. ローカルPC/外部ストレージに保管
3. Xserverサーバーパネルで解約申請
4. 契約終了日確認

---

## 10. Phase F: 本番稼働後のセキュリティ強化（必須）

**実施タイミング**: Phase E完了（DNS切替 + 2週間並行運用完了）後、**即座に実施**

**目的**: 移行期間中に暫定的に保持していた認証情報を完全にリセットし、セキュリティリスクを除去

---

### Phase F-1: 認証情報の完全リセット

**実施順序**: Xserver → Dell の順で実施（逆にするとロールバック不可）

#### ステップ F-1-1: Xserver認証情報の変更

**前提確認**:
- ✅ Dell側でWordPress正常動作（2週間以上）
- ✅ DNS浸透完了（Xserver側アクセスなし）
- ✅ Xserver解約手続き完了または解約予定確定

**実行手順** (Xserver管理画面):

```bash
# 1. Xserverサーバーパネルへログイン
# https://www.xserver.ne.jp/login_server.php

# 2. MySQL設定 → ユーザーパスワード変更
# 全5サイト分のDBパスワードを変更:
# - gwpbk492_wt3（kuma8088.com）
# - gwpbk492_wp2（fx-trader-life.com）
# - gwpbk492_wt6（toyota-phv.jp）
# - gwpbk492_wt4（webmakeprofit.org）
# - gwpbk492_wt5（webmakesprofit.com）

# 新しいパスワード:
# - 16文字以上のランダム文字列（パスワード管理ツールで生成推奨）
# - 記録不要（Xserver解約後は不要）

# 3. SSHアカウント設定 → パスワード変更（SSH利用していた場合）
# 新しいSSHパスワード: 16文字以上のランダム文字列

# 4. FTPアカウント設定 → パスワード変更（FTP利用していた場合）
# 新しいFTPパスワード: 16文字以上のランダム文字列
```

**検証**:
```bash
# 旧パスワードで接続できないことを確認
mysql -h localhost -u gwpbk492_wt3 -p'<旧パスワード>' gwpbk492_wt3
# → ERROR 1045 (28000): Access denied（正常）

# 新パスワードで接続できることを確認
mysql -h localhost -u gwpbk492_wt3 -p'<新パスワード>' gwpbk492_wt3
# → 接続成功
```

#### ステップ F-1-2: Dell認証情報の変更

**実行手順** (Dell SSH接続):

```bash
# Dellへ接続
ssh <dell-user>@<dell-ip>

# 1. MariaDB rootパスワード変更
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 現在のrootパスワード確認
grep MYSQL_ROOT_PASSWORD .env

# 新しいrootパスワード生成（32文字）
NEW_ROOT_PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)
echo "$NEW_ROOT_PASS"  # 記録しておく

# MariaDBコンテナ内でパスワード変更
docker compose exec mariadb mysql -uroot -p"$(grep MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  -e "ALTER USER 'root'@'%' IDENTIFIED BY '$NEW_ROOT_PASS'; FLUSH PRIVILEGES;"

# .envファイル更新
sed -i "s/^MYSQL_ROOT_PASSWORD=.*/MYSQL_ROOT_PASSWORD=$NEW_ROOT_PASS/" .env

# 2. blog_user パスワード変更
NEW_USER_PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)
echo "$NEW_USER_PASS"  # 記録しておく

docker compose exec mariadb mysql -uroot -p"$NEW_ROOT_PASS" \
  -e "ALTER USER 'blog_user'@'%' IDENTIFIED BY '$NEW_USER_PASS'; FLUSH PRIVILEGES;"

# .envファイル更新
sed -i "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=$NEW_USER_PASS/" .env

# 3. 各サイトのwp-config.phpも更新
for site in kuma8088 fx-trader-life toyota-phv webmakeprofit webmakesprofit; do
  WP_CONFIG="/mnt/backup-hdd/blog/sites/$site/wp-config.php"
  if [ -f "$WP_CONFIG" ]; then
    sudo sed -i "s/define('DB_PASSWORD', '.*');/define('DB_PASSWORD', '$NEW_USER_PASS');/" "$WP_CONFIG"
    echo "✅ Updated: $site"
  fi
done

# 4. コンテナ再起動（新パスワード反映）
docker compose restart wordpress

# 5. 接続確認
docker compose exec mariadb mysql -uroot -p"$NEW_ROOT_PASS" -e "SHOW DATABASES;"
```

**検証**:
```bash
# WordPressサイトが正常動作することを確認
curl -I https://kuma8088.com
# → HTTP/2 200（正常）

# 管理画面ログイン確認
curl -I https://kuma8088.com/wp-admin/
# → HTTP/2 302（リダイレクト、正常）
```

---

### Phase F-2: 機密ファイルの完全削除

#### ステップ F-2-1: ローカルPC上のファイル削除

```bash
# 1. 調査結果ファイルの完全削除
shred -u ~/Documents/blog-migration-temp/xserver-investigation-results.txt
shred -u ~/Downloads/xserver-investigation-results.txt 2>/dev/null || true

# 2. 認証情報ファイルの完全削除
shred -u docs/application/blog/claudedocs/xserver-credentials.env 2>/dev/null || true
shred -u ~/Documents/blog-migration-temp/xserver-credentials.env 2>/dev/null || true

# 3. 一時ディレクトリ削除
rm -rf ~/Documents/blog-migration-temp/

# 4. Downloadsフォルダ内の関連ファイル確認
ls -la ~/Downloads/ | grep -E "xserver|migration|wpvivid"
# → 残っているファイルがあれば個別に削除
```

#### ステップ F-2-2: Xserver上のファイル削除

```bash
# Xserver SSH接続
ssh <xserver-username>@<xserver-host>

# 調査スクリプトと結果の削除
shred -u ~/investigation.sh 2>/dev/null || true
shred -u ~/xserver-investigation-results.txt 2>/dev/null || true

# データベースダンプファイルの削除
shred -u ~/kuma8088_db_*.sql.gz 2>/dev/null || true
shred -u ~/migration_*_db_*.sql.gz 2>/dev/null || true
shred -u ~/*_db_*.sql.gz 2>/dev/null || true

# 一時ファイル確認
ls -la ~/ | grep -E "investigation|migration|dump|backup"
# → 残っているファイルがあれば個別に削除

# ログアウト
exit
```

---

### Phase F-3: Git履歴からの機密情報削除

**⚠️ 重要**: 誤って機密情報をコミットしていた場合のみ実施

#### ステップ F-3-1: Git履歴スキャン

```bash
cd /opt/onprem-infra-system/project-root-infra

# 1. 機密情報が含まれるファイルのコミット履歴確認
git log --all --full-history --source --pretty=format:"%H %ad %s" \
  -- "docs/application/blog/claudedocs/xserver-investigation-commands.sh"

# コミット履歴がある場合 → Phase F-3-2へ
# コミット履歴がない場合 → Phase F-4へスキップ
```

#### ステップ F-3-2: BFG Repo-Cleanerで完全削除（推奨）

```bash
# 1. BFG Repo-Cleanerダウンロード
cd /tmp
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 2. リポジトリのバックアップ
cd /opt/onprem-infra-system/project-root-infra
git clone --mirror . /tmp/project-root-infra-backup.git

# 3. 機密情報ファイルを削除
java -jar /tmp/bfg-1.14.0.jar \
  --delete-files "xserver-investigation-commands.sh" \
  --delete-files "xserver-credentials.env" \
  --delete-files "xserver-investigation-results.txt" \
  .git

# 4. Git履歴をクリーンアップ
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. リモートリポジトリへ強制プッシュ（注意！）
git push origin --force --all
git push origin --force --tags

# 6. 全作業者に通知
echo "⚠️ Git履歴を書き換えたため、全作業者は以下を実行してください:"
echo "cd /opt/onprem-infra-system/project-root-infra"
echo "git fetch origin"
echo "git reset --hard origin/main"
```

**代替方法: git filter-repo**（BFG不可の場合）:
```bash
# git filter-repoインストール
pip3 install git-filter-repo

# 機密情報ファイルを履歴から完全削除
git filter-repo --path docs/application/blog/claudedocs/xserver-investigation-commands.sh --invert-paths
git filter-repo --path docs/application/blog/claudedocs/xserver-credentials.env --invert-paths

# リモートリポジトリへ強制プッシュ
git remote add origin <repository-url>
git push origin --force --all
```

---

### Phase F-4: ドキュメント内の平文情報スキャン

```bash
cd /opt/onprem-infra-system/project-root-infra

# 1. 平文パスワードスキャン
# 注意: 旧パスワードは既に変更済みなので、検出されても問題なし
grep -r "381pjkb9n3\|mx9ssys031\|brvfr0h9n3\|z3mxq7ovnx\|kogpt01olh" \
  docs/application/blog/ 2>/dev/null || echo "✅ 平文パスワード検出なし"

# 2. DB接続情報の記載確認
grep -r "gwpbk492_" docs/application/blog/ | grep -v ".md:" | grep -v "例:"
# → 検出された場合、該当ドキュメントを確認

# 3. .htaccess内容の記載確認（セキュリティ上問題ないか確認）
grep -r "RewriteRule\|RewriteCond" docs/application/blog/

# 4. 検出された内容の判断
# - 例示・説明目的 → 問題なし
# - 実際の認証情報 → 削除または変数化
```

---

### Phase F-5: セキュリティ強化完了確認

**チェックリスト**:

```bash
# ✅ 完了確認
cat << 'EOF'
Phase F セキュリティ強化完了確認

□ F-1-1: Xserver認証情報変更完了
  □ MySQL全5サイト分のパスワード変更
  □ SSHパスワード変更（利用していた場合）
  □ FTPパスワード変更（利用していた場合）

□ F-1-2: Dell認証情報変更完了
  □ MariaDB rootパスワード変更
  □ blog_userパスワード変更
  □ 各サイトwp-config.php更新
  □ WordPress正常動作確認

□ F-2-1: ローカルPC上のファイル削除
  □ xserver-investigation-results.txt削除
  □ xserver-credentials.env削除
  □ 一時ディレクトリ削除

□ F-2-2: Xserver上のファイル削除
  □ investigation.sh削除
  □ 調査結果ファイル削除
  □ DBダンプファイル削除

□ F-3: Git履歴からの削除（該当する場合のみ）
  □ BFG/git filter-repo実行
  □ リモートリポジトリへ強制プッシュ
  □ 全作業者へ通知

□ F-4: ドキュメント平文情報スキャン
  □ 平文パスワード検出なし
  □ 実認証情報の記載なし

□ F-5: 最終確認
  □ WordPress全サイト正常動作
  □ 認証情報は全て変更済み
  □ 機密ファイルは全て削除済み
  □ Git履歴に機密情報なし
EOF
```

**完了報告フォーマット**:
```markdown
# Phase F セキュリティ強化完了報告

**実施日**: 2025-XX-XX
**実施者**: [作業者名]

## 実施内容
- ✅ Xserver認証情報変更（DB 5サイト + SSH + FTP）
- ✅ Dell認証情報変更（MariaDB root + blog_user）
- ✅ 機密ファイル完全削除（ローカルPC + Xserver）
- ✅ Git履歴クリーンアップ（該当なし/実施済み）
- ✅ ドキュメント平文情報スキャン（検出なし）

## 検証結果
- ✅ WordPress全サイト正常動作確認
- ✅ 旧認証情報で接続不可確認
- ✅ Git履歴に機密情報なし確認

## 備考
[特記事項があれば記載]
```

---

**Phase F完了後の状態**:
- ✅ 移行期間中に使用した全認証情報が無効化
- ✅ 機密ファイルが完全削除（復元不可）
- ✅ Git履歴に機密情報が残っていない
- ✅ 新しい認証情報でWordPress正常動作
- ✅ セキュリティリスクが除去された状態

**次のステップ**: 定期的なセキュリティ監査（月次推奨）

---

## 11. トラブルシューティング

### 問題 1: WPvividバックアップがタイムアウト

**症状**:
```
Backup failed: Maximum execution time of 60 seconds exceeded
```

**原因**: PHPタイムアウト設定が短い

**対処**:
```bash
# Dell側 config/php/php.ini 編集
vi config/php/php.ini

# 以下を変更
max_execution_time = 600
memory_limit = 512M

# WordPress再起動
docker compose restart wordpress
```

---

### 問題 2: 画像が表示されない（404エラー）

**症状**: 記事内画像、メディアライブラリの画像が表示されない

**原因**: パーミッション不足、またはURL置換漏れ

**対処**:
```bash
# パーミッション修正
sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/<site-name>/
sudo find /mnt/backup-hdd/blog/sites/<site-name>/wp-content/uploads/ -type f -exec chmod 644 {} \;

# URL置換確認
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'http://old-domain.com' \
    'https://new-domain.com' \
    --path=/var/www/html/<site-name> \
    --dry-run
```

---

### 問題 3: パーマリンクが404エラー

**症状**: トップページは表示されるが、記事ページが404

**原因**: .htaccess未生成、またはNginx rewriteルール不足

**対処**:
```bash
# WordPress管理画面で再保存
# 「設定」→「パーマリンク設定」→「変更を保存」をクリック

# または WP-CLIで実行
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp rewrite flush \
    --path=/var/www/html/<site-name>
```

---

### 問題 4: データベース接続エラー

**症状**:
```
Error establishing a database connection
```

**原因**: wp-config.php の DB接続情報が間違っている

**対処**:
```bash
# wp-config.php 確認
cat /mnt/backup-hdd/blog/sites/<site-name>/wp-config.php | grep DB_

# 正しい値に修正
sudo vi /mnt/backup-hdd/blog/sites/<site-name>/wp-config.php

# 接続テスト
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp db check \
    --path=/var/www/html/<site-name>
```

---

### 問題 5: Migrate Guru転送が進まない

**症状**: 転送進捗が50%で停止

**原因**: Xserver側タイムアウト、またはファイルサイズ制限

**対処**:
1. Xserver側で一時的にPHP設定変更（php.ini編集権限がある場合）
2. 方法Cへ切り替え（SSH/rsync）
3. 小分けに転送（メディアライブラリを除外 → 後でrsync追加）

---

### 問題 6: URL置換後も一部が旧URLのまま

**症状**: 画像や内部リンクが一部 http://old-domain.com のまま

**原因**: シリアライズされたデータ、またはテーマ/プラグイン独自テーブル

**対処**:
```bash
# WP-CLIで全テーブル対象に再実行
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'http://old-domain.com' \
    'https://new-domain.com' \
    --all-tables \
    --path=/var/www/html/<site-name>

# 特定テーブルのみ（例: wp_postmeta）
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'http://old-domain.com' \
    'https://new-domain.com' \
    wp_postmeta \
    --path=/var/www/html/<site-name>
```

---

**作成日**: 2025-11-08
**バージョン**: 1.0
**作成者**: Claude

**次のステップ**: [05_testing.md](05_testing.md) - テスト計画書作成

---

### 問題 7: プラグインインストール時のFTPエラー

**症状**: 
- プラグインやテーマをWordPress管理画面からインストールしようとすると「FTP接続情報を入力してください」と表示される
- All-in-One WP Migrationプラグインがファイル作成権限エラーを出す

**原因**: 
WordPressがファイルシステムへの直接アクセス権限を持っていない（デフォルトはFTP/FTPS経由を想定）

**対処法**:

#### 1. wp-config.phpに`FS_METHOD`を設定

**方法A: WP-CLI経由（推奨）**
```bash
docker compose exec wordpress wp config set FS_METHOD direct --raw \
  --path=/var/www/html/<site-name> \
  --allow-root
```

**方法B: 手動編集**
```bash
# wp-config.phpを編集して以下を追加（`/* That's all, stop editing! */`の前）
docker compose exec wordpress bash -c "cat >> /var/www/html/<site-name>/wp-config.php << 'WPEOF'

define('FS_METHOD', 'direct');
WPEOF
"
```

#### 2. ディレクトリ権限の確認と修正

```bash
# wp-content全体の所有権をwww-dataに変更
docker compose exec wordpress chown -R www-data:www-data \
  /var/www/html/<site-name>/wp-content

# ディレクトリ権限: 755
docker compose exec wordpress find /var/www/html/<site-name>/wp-content \
  -type d -exec chmod 755 {} \;

# ファイル権限: 644
docker compose exec wordpress find /var/www/html/<site-name>/wp-content \
  -type f -exec chmod 644 {} \;
```

#### 3. All-in-One WP Migration用の特定ディレクトリ作成

```bash
# 必要なディレクトリを事前作成
docker compose exec wordpress bash -c "
cd /var/www/html/<site-name> &&
mkdir -p wp-content/ai1wm-backups &&
mkdir -p wp-content/plugins/all-in-one-wp-migration/storage &&
chown -R www-data:www-data wp-content/ai1wm-backups &&
chown -R www-data:www-data wp-content/plugins/all-in-one-wp-migration/storage
"
```

#### 4. プラグイン再有効化

```bash
# プラグインを再有効化して保護ファイルを作成
docker compose exec wordpress wp plugin deactivate all-in-one-wp-migration \
  --path=/var/www/html/<site-name> --allow-root
docker compose exec wordpress wp plugin activate all-in-one-wp-migration \
  --path=/var/www/html/<site-name> --allow-root
```

**検証**:
- WordPress管理画面 → プラグイン → 新規追加 → 任意のプラグインをインストール
- FTP情報を求められず、インストールが完了すればOK

**注意点**:
- `FS_METHOD direct`はDocker環境では標準的な設定
- セキュリティ的にも問題なし（コンテナ内でのみ動作）
- すべての新規サイトで初期セットアップ時に設定すべき

---

### 問題 8: 移行後の静的ファイル404エラー（CSS/JS/画像）

**症状**: 
- ページHTMLは表示されるが、CSS/JS/画像が404エラー
- ブラウザコンソールに大量の404エラー

**原因**:
- データベース内のURL設定（`siteurl`/`home`）は正しいが、`wp_posts.guid`に旧ドメインが残っている
- WordPressがguid列を参照してメディアURLを生成している

**対処法**:

#### 確認コマンド
```bash
# guidに旧ドメインがあるか確認
docker compose exec mariadb mysql -uroot -p'${MYSQL_ROOT_PASSWORD}' \
  <database-name> \
  -e "SELECT COUNT(*) FROM wp_posts WHERE guid LIKE '%old-domain%';"
```

#### 修正コマンド（wp-cli search-replace）
```bash
# ドライラン（実行前確認）
docker compose exec wordpress wp search-replace \
  'old-domain.com/subdirectory' \
  'new-domain.com/subdirectory' \
  --dry-run \
  --path=/var/www/html/<site-name> \
  --allow-root

# 実行（guidは通常スキップ推奨だが、移行では置換必要）
docker compose exec wordpress wp search-replace \
  'old-domain.com/subdirectory' \
  'new-domain.com/subdirectory' \
  --path=/var/www/html/<site-name> \
  --allow-root
```

**注意**:
- `guid`はWordPress内部IDなので通常は変更しないが、ドメイン完全移行時は必要
- プロトコル（http/https）も含めて正確に指定すること

---

**更新日**: 2025-11-10  
**バージョン**: 1.1  
**更新内容**: FTP問題・静的ファイル404問題のトラブルシューティング追加


#### 補足: FS_METHOD設定時の注意点

**⚠️ 重要**: `wp config set`で`--raw`フラグを使うとクォートが抜けて500エラーになります。

**誤った方法（500エラー発生）**:
```bash
# ❌ --raw フラグを使うとクォートが抜ける
docker compose exec wordpress wp config set FS_METHOD direct --raw \
  --path=/var/www/html/<site-name> --allow-root
# 結果: define( 'FS_METHOD', direct ); ← クォートなしでPHPエラー
```

**正しい方法**:
```bash
# ✅ 方法1: --rawなしで実行
docker compose exec wordpress wp config set FS_METHOD direct \
  --path=/var/www/html/<site-name> --allow-root
# 結果: define('FS_METHOD', 'direct'); ← 正しい

# ✅ 方法2: 手動でwp-config.phpに追記（最も確実）
docker compose exec wordpress bash -c "
grep -q 'FS_METHOD' /var/www/html/<site-name>/wp-config.php || \
sed -i \"/That's all, stop editing/i define('FS_METHOD', 'direct');\n\" \
/var/www/html/<site-name>/wp-config.php
"
```

**既に500エラーになっている場合の修正**:
```bash
# クォートを追加して修正
docker compose exec wordpress sed -i \
  "s/define( 'FS_METHOD', direct );/define('FS_METHOD', 'direct');/" \
  /var/www/html/<site-name>/wp-config.php

# 修正確認
docker compose exec wordpress grep "FS_METHOD" /var/www/html/<site-name>/wp-config.php
# 期待出力: define('FS_METHOD', 'direct');
```

**エラーログ確認**:
```bash
# PHP Fatal errorを確認
docker compose logs wordpress --tail 50 | grep "Fatal error"
# 出力例: PHP Fatal error: Uncaught Error: Undefined constant "direct"
```

