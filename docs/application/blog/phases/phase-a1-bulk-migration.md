# Phase A-1: 一括移行手順（SSH+rsync方式）

**対象**: Xserver全18サイト（Phase 1: 4サイト + Phase 2: 5サイト + Unknown: 3サイト + Test: 6サイト）
**移行方式**: SSH+rsync一括移行（プラグイン不使用）
**テスト環境**: blog.*サブドメイン
**作成日**: 2025-11-09

---

## 📋 前提条件確認

### 1. Xserver SSH接続情報確認

**必須**: Xserver管理画面 → SSH設定 で以下を確認し、`claudedocs/xserver-credentials.env` を更新

```bash
# 確認が必要な情報
export XSERVER_SSH_HOST="<sv番号>.xserver.jp"  # 例: sv13071.xserver.jp
export XSERVER_SSH_USER="gwpbk492"              # サーバーID
export XSERVER_SSH_PORT="10022"                 # 通常10022
```

**確認方法**:
1. Xserverサーバーパネルにログイン
2. 「アカウント」→「サーバー情報」→ SSH接続先サーバー を確認
3. 「SSH設定」→ SSH接続ユーザー名 を確認

### 2. Dell側受け入れ準備確認

```bash
# ディレクトリ存在確認
ls -la /mnt/backup-hdd/blog/sites/
# 必要: fx-trader-life/, webmakeprofit/, webmakesprofit/, toyota-phv/, kuma8088/

# MariaDB 18DB存在確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "SHOW DATABASES LIKE 'wp_%';" | wc -l
# 期待値: 19行（ヘッダー1 + DB 18）

# nginx設定ファイル文法確認
docker compose exec nginx nginx -t
# 期待出力: nginx: configuration file /etc/nginx/nginx.conf test is successful

# blog.*サブドメイン設定確認（重要）
docker compose exec nginx sh -c "grep -h 'server_name' /etc/nginx/conf.d/*.conf"
# 期待出力: 全5サイトがblog.*サブドメインになっていること
#   server_name blog.fx-trader-life.com;
#   server_name blog.kuma8088.com;
#   server_name blog.toyota-phv.jp;
#   server_name blog.webmakeprofit.org;
#   server_name blog.webmakesprofit.com;
```

---

## 🚀 一括移行手順

### Step 1: SSH接続テスト

**前提**: `~/.ssh/xserver-dell.key`が存在し、Xserver管理画面でSSH公開鍵が登録済み

```bash
# SSH接続テスト
ssh -p 10022 -i ~/.ssh/xserver-dell.key gwpbk492@sv13071.xserver.jp "pwd"
# 期待出力: /home/gwpbk492
```

**エラー時の対処**:
- `Permission denied`: SSH公開鍵がXserverに未登録 → Xserver管理画面でSSH Keyを登録
- `No such file or directory`: `~/.ssh/xserver-dell.key`が存在しない → 鍵ペア生成が必要

---

### Step 2: ファイル一括移行（rsync）

**重要**: Xserverのディレクトリ構造を確認してから実行

#### 2-1. ディレクトリ構造確認

```bash
# Xserver側のWordPressインストール先確認
ssh -p 10022 -i ~/.ssh/xserver-dell.key gwpbk492@sv13071.xserver.jp \
  "ls -la /home/gwpbk492/"

# 期待出力: fx-trader-life.com, webmakeprofit.org, webmakesprofit.com, toyota-phv.jp, kuma8088.com
```

**確認された構造**:
```
/home/gwpbk492/
├── fx-trader-life.com/         # ドメイン名ディレクトリ
│   └── public_html/            # WordPress root
├── webmakeprofit.org/
│   └── public_html/
├── webmakesprofit.com/
│   └── public_html/
├── toyota-phv.jp/
│   └── public_html/
└── kuma8088.com/
    └── public_html/
```

#### 2-2. SSH Agent起動（パスフレーズ1回入力のため）

```bash
# SSH Agent起動
eval "$(ssh-agent -s)"

# 秘密鍵を追加（パスフレーズを1回だけ入力）
ssh-add ~/.ssh/xserver-dell.key
# パスフレーズを入力: ********
```

#### 2-3. 一括rsync実行

> **事前準備**  
> `docs/application/blog/claudedocs/site-map.csv` に以下のようなマッピングを用意し、必要に応じて追記してください（Git管理外）。
> ```
> slug,domain,xserver_path,xserver_db_name,dell_db_name
> fx-trader-life,fx-trader-life.com,fx-trader-life.com/public_html,gwpbk492_wp3,wp_fx_trader_life
> webmakeprofit,webmakeprofit.org,webmakeprofit.org/public_html,gwpbk492_wt1,wp_webmakeprofit
> webmakesprofit,webmakesprofit.com,webmakesprofit.com/public_html,gwpbk492_wt4,wp_webmakesprofit
> toyota-phv,toyota-phv.jp,toyota-phv.jp/public_html,gwpbk492_wt5,wp_toyota_phv
> kuma8088,kuma8088.com,kuma8088.com/public_html,gwpbk492_wp1,wp_kuma8088
> ```

```bash
# Dell側のターミナルで実行（site-map.csv を基に一括転送）
cd /opt/onprem-infra-system/project-root-infra/services/blog

SITE_MAP=../claudedocs/site-map.csv

while IFS=',' read -r slug domain xserver_path; do
  # ヘッダ行はスキップ
  [[ "$slug" == "slug" ]] && continue

  echo "==== Syncing ${domain} → ${slug} ===="
  sudo mkdir -p "/mnt/backup-hdd/blog/sites/${slug}"
  sudo chown -R 33:33 "/mnt/backup-hdd/blog/sites/${slug}"

  rsync -avz --progress \
    -e "ssh -p ${XSERVER_SSH_PORT:-10022} -i ${XSERVER_SSH_KEY:-~/.ssh/xserver-dell.key}" \
    "${XSERVER_SSH_USER}@${XSERVER_SSH_HOST}:/home/${XSERVER_SSH_USER}/${xserver_path}/" \
    "/mnt/backup-hdd/blog/sites/${slug}/"
done < "$SITE_MAP"
```

**オプション説明**:
- `-a`: archive（権限・タイムスタンプ保持）
- `-v`: verbose（詳細表示）
- `-z`: 圧縮転送
- `--delete`: 転送元にないファイルを転送先から削除
- `--progress`: 進捗表示

**所要時間目安**:
- Phase 1 (4サイト): 約31.8 GB → 30-60分
- kuma8088.com: 約0.8 MB → 数秒

**rsync完了後の確認**:
```bash
# ファイル転送確認
ls -lah /mnt/backup-hdd/blog/sites/*/
# 期待: 各ディレクトリにwp-config.php, wp-content/, wp-includes/等が存在

# WordPress設定ファイル存在確認
ls -la /mnt/backup-hdd/blog/sites/*/wp-config.php
# 期待: 5サイト全てでwp-config.phpが存在

# サイズ確認（Phase A-0の調査結果と比較）
du -sh /mnt/backup-hdd/blog/sites/*/
# 期待:
# 8.6G  fx-trader-life/
# 18G   webmakeprofit/
# 4.1G  webmakesprofit/
# 1.1G  toyota-phv/
# 800K  kuma8088/
```

---

### Step 3: データベース一括移行

#### 3-1. Xserver側からDB一括エクスポート

> **事前準備**  
> `docs/application/blog/claudedocs/site-map.csv` に `xserver_db_name` カラムを追加し、`xserver-credentials.env` に各DBの `*_DB_USER` / `*_DB_PASS` と `XSERVER_DB_HOST` を定義しておきます。  
> 例）`FX_TRADER_LIFE_DB_USER="gwpbk492_wp3"`、`FX_TRADER_LIFE_DB_PASS="********"` など。

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ../claudedocs/xserver-credentials.env
set +a

SITE_MAP=../claudedocs/site-map.csv
TMP_DIR=/tmp/xserver-dumps
mkdir -p "$TMP_DIR"

while IFS=',' read -r slug domain xserver_path xserver_db_name; do
  [[ "$slug" == "slug" ]] && continue

  db_var_name="$(echo "${slug^^}_DB_NAME" | sed 's/-/_/g')"
  user_var_name="$(echo "${slug^^}_DB_USER" | sed 's/-/_/g')"
  pass_var_name="$(echo "${slug^^}_DB_PASS" | sed 's/-/_/g')"

  DB_NAME="${!db_var_name:-$xserver_db_name}"
  DB_USER="${!user_var_name:?DBユーザー未設定}"
  DB_PASS="${!pass_var_name:?DBパスワード未設定}"

  echo "==== Dumping ${slug} (${DB_NAME}) ===="
  ssh -p "${XSERVER_SSH_PORT:-10022}" -i "${XSERVER_SSH_KEY:-~/.ssh/xserver-dell.key}" \
    "${XSERVER_SSH_USER}@${XSERVER_SSH_HOST}" \
    "mysqldump -h ${XSERVER_DB_HOST} -u ${DB_USER} -p'${DB_PASS}' ${DB_NAME} --single-transaction --quick --lock-tables=false" \
    | gzip > "${TMP_DIR}/${slug}.sql.gz"
done < "$SITE_MAP"
```

#### 3-2. Dell側へインポート

```bash
SITE_MAP=../claudedocs/site-map.csv
TMP_DIR=/tmp/xserver-dumps

while IFS=',' read -r slug domain _ xserver_db_name dell_db_name; do
  [[ "$slug" == "slug" ]] && continue
  dump_file="${TMP_DIR}/${slug}.sql.gz"
  [[ ! -f "$dump_file" ]] && { echo "⚠️ Dump not found for ${slug}, skip"; continue; }

  TARGET_DB=${dell_db_name:-"wp_${slug//-/_}"}

  echo "==== Importing ${slug} → ${TARGET_DB} ===="
  docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
    -e "DROP DATABASE IF EXISTS ${TARGET_DB}; CREATE DATABASE ${TARGET_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

  docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
    -e "GRANT ALL PRIVILEGES ON ${TARGET_DB}.* TO 'blog_user'@'%'; FLUSH PRIVILEGES;"

  gunzip < "$dump_file" | \
    docker compose exec -T mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${TARGET_DB}"
done < "$SITE_MAP"

# インポート確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  -e "SELECT table_schema, COUNT(*) AS tables FROM information_schema.tables WHERE table_schema LIKE 'wp_%' GROUP BY table_schema;"
```

---

### Step 4: wp-config.php一括修正

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
set -a
. ./.env
set +a

SITE_MAP=../claudedocs/site-map.csv

while IFS=',' read -r slug _ _ _ dell_db_name; do
  [[ "$slug" == "slug" ]] && continue
  cfg="/mnt/backup-hdd/blog/sites/${slug}/wp-config.php"
  [[ ! -f "$cfg" ]] && continue

  target_db=${dell_db_name:-"wp_${slug//-/_}"}

  echo "==== Updating wp-config.php for ${slug} (${target_db}) ===="
  sudo cp "$cfg" "${cfg}.xserver.bak"
  sudo sed -i \
    -e "s/'DB_NAME', *'[^']*'/'DB_NAME', '${target_db}'/" \
    -e "s/'DB_USER', *'[^']*'/'DB_USER', 'blog_user'/" \
    -e "s/'DB_PASSWORD', *'[^']*'/'DB_PASSWORD', '${MYSQL_PASSWORD}'/" \
    -e "s/'DB_HOST', *'[^']*'/'DB_HOST', 'mariadb:3306'/" \
    "$cfg"
done < "$SITE_MAP"
```

---

### Step 5: WordPress URL一括置換（wp-cli使用）

WordPress DBに保存されているURLをXserver本番URL → blog.*テストURLに一括置換：

```bash
# Dell側のターミナルで実行
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 全5サイトのURLを一括置換
declare -A domains
domains[fx-trader-life]="fx-trader-life.com"
domains[webmakeprofit]="webmakeprofit.org"
domains[webmakesprofit]="webmakesprofit.com"
domains[toyota-phv]="toyota-phv.jp"
domains[kuma8088]="kuma8088.com"

for site in fx-trader-life webmakeprofit webmakesprofit toyota-phv kuma8088; do
  domain="${domains[$site]}"
  echo "==== Replacing URLs for $site (https://$domain → http://blog.$domain) ===="
  docker run --rm \
    --volumes-from blog-wordpress \
    --network blog_blog_network \
    --user 33:33 \
    wordpress:cli wp search-replace \
      "https://$domain" "http://blog.$domain" \
      --path=/var/www/html/$site \
      --skip-columns=guid \
      --all-tables
done
```

**オプション説明**:
- `--skip-columns=guid`: GUID（投稿固有ID）は変更しない
- `--all-tables`: 全テーブルを対象（wp_postmeta, wp_options等含む）

**URL置換確認**:
```bash
# wp-cliの出力で置換件数を確認
# 期待出力例: "Success: Made 127 replacements."

# DBから直接確認（例: fx-trader-life）
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" wp_fx_trader_life \
  -e "SELECT option_value FROM wp_options WHERE option_name IN ('siteurl','home');"
# 期待出力:
# http://blog.fx-trader-life.com
# http://blog.fx-trader-life.com
```

---

### Step 6: パーミッション一括修正

WordPressが正常に動作するためのパーミッション設定：

```bash
# 全サイトを一括でwww-data（UID 33）に所有権変更
sudo chown -R 33:33 /mnt/backup-hdd/blog/sites/*

# ディレクトリ: 755、ファイル: 644
sudo find /mnt/backup-hdd/blog/sites -type d -exec chmod 755 {} \;
sudo find /mnt/backup-hdd/blog/sites -type f -exec chmod 644 {} \;

# wp-content/uploads: 書き込み可能
sudo chmod -R 775 /mnt/backup-hdd/blog/sites/*/wp-content/uploads

# パーミッション確認
ls -ld /mnt/backup-hdd/blog/sites/fx-trader-life
# 期待出力: drwxr-xr-x. ... 33 33 ... fx-trader-life （所有者: 33:33）

stat -c '%a %U:%G' /mnt/backup-hdd/blog/sites/fx-trader-life/wp-config.php
# 期待出力: 644 UNKNOWN:UNKNOWN （パーミッション: 644, UID:GID=33:33）
```

---

### Step 7: Dockerコンテナ再起動とテスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# コンテナ再起動（MariaDBのGRANT実行のため）
docker compose down
docker compose up -d

# ログ確認
docker compose logs -f nginx wordpress mariadb

# 期待出力（エラーがないこと）:
# nginx: "start worker process" が表示される
# wordpress: "NOTICE: ready to handle connections" が表示される
# mariadb: "ready for connections" が表示される
# エラー確認後 Ctrl+C で終了
```

---

## ✅ 動作確認

### 1. Cloudflare Tunnel接続確認

```bash
docker compose logs cloudflared | grep "Connection"
# 期待出力: registered tunnel connection ... connIndex=0-3
```

### 2. ブラウザアクセステスト

**Cloudflare Zero Trust Dashboard** → Public Hostnames に以下を追加:

| Subdomain | Domain | Type | URL |
|-----------|--------|------|-----|
| blog | fx-trader-life.com | HTTP | http://nginx:80 |
| blog | webmakeprofit.org | HTTP | http://nginx:80 |
| blog | webmakesprofit.com | HTTP | http://nginx:80 |
| blog | toyota-phv.jp | HTTP | http://nginx:80 |
| blog | kuma8088.com | HTTP | http://nginx:80 |

**コマンドラインでの簡易確認（Cloudflare Tunnel経由）**:
```bash
curl -I https://blog.fx-trader-life.com
# 期待出力: HTTP/2 200 （404や500でないこと）

curl -s https://blog.fx-trader-life.com | grep -o '<title>.*</title>'
# 期待出力: サイトタイトルが表示される（"Error establishing a database connection"でないこと）
```

**ブラウザでアクセス**:
- https://blog.fx-trader-life.com
- https://blog.webmakeprofit.org
- https://blog.webmakesprofit.com
- https://blog.toyota-phv.jp
- https://blog.kuma8088.com

**期待結果**:
- ✅ WordPressホーム画面表示（投稿一覧やヘッダー画像が見える）
- ✅ Cloudflare経由でSSL自動適用（鍵マーク🔒表示）
- ❌ 「Error establishing a database connection」が出ない
- ❌ 404 Not Found が出ない

### 3. WordPress管理画面テスト

各サイトの管理画面にログイン:
- https://blog.fx-trader-life.com/wp-admin
- https://blog.webmakeprofit.org/wp-admin
- （以下同様）

**確認項目**:
- [ ] ログイン成功（Xserverと同じ認証情報）
- [ ] ダッシュボード表示正常
- [ ] 投稿一覧表示正常
- [ ] メディアライブラリ画像表示正常
- [ ] プラグイン一覧表示正常

---

## 🔧 トラブルシューティング

### エラー1: データベース接続エラー

**症状**: "Error establishing a database connection"

**原因**: wp-config.phpのDB接続情報が間違っている

**対処**:
```bash
cd /mnt/backup-hdd/blog/sites/fx-trader-life
cat wp-config.php | grep DB_
# 確認: DB_NAME=wp_fx_trader_life, DB_USER=wpuser, DB_HOST=mariadb
```

### エラー2: 404 Not Found

**症状**: blog.*にアクセスすると404エラー

**原因**: nginx設定またはWordPress URLが間違っている

**対処**:
```bash
# nginx設定確認
docker compose exec nginx cat /etc/nginx/conf.d/fx-trader-life.conf | grep server_name
# 期待: server_name blog.fx-trader-life.com;

# WordPress URL確認
docker compose exec mariadb mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" wp_fx_trader_life \
  -e "SELECT option_value FROM wp_options WHERE option_name IN ('siteurl', 'home');"
# 期待: http://blog.fx-trader-life.com
```

### エラー3: 画像が表示されない

**症状**: 投稿内の画像が表示されない

**原因**: uploads/のパーミッション不足、またはURL置換漏れ

**対処**:
```bash
# パーミッション確認・修正
sudo chmod -R 775 /mnt/backup-hdd/blog/sites/*/wp-content/uploads

# URL置換再実行
docker run --rm \
  --volumes-from blog-wordpress \
  --network blog_blog_network \
  --user 33:33 \
  wordpress:cli wp search-replace \
    'https://fx-trader-life.com' 'http://blog.fx-trader-life.com' \
    --path=/var/www/html/fx-trader-life \
    --skip-columns=guid \
    --all-tables
```

---

## 📊 移行完了チェックリスト

### Phase 1: Root domain sites (4サイト)

- [ ] fx-trader-life.com
  - [ ] ファイルrsync完了
  - [ ] DB移行完了
  - [ ] wp-config.php修正
  - [ ] URL置換完了
  - [ ] blog.*でアクセス成功
  - [ ] 管理画面ログイン成功

- [ ] webmakeprofit.org
  - [ ] ファイルrsync完了
  - [ ] DB移行完了
  - [ ] wp-config.php修正
  - [ ] URL置換完了
  - [ ] blog.*でアクセス成功
  - [ ] 管理画面ログイン成功

- [ ] webmakesprofit.com
  - [ ] ファイルrsync完了
  - [ ] DB移行完了
  - [ ] wp-config.php修正
  - [ ] URL置換完了
  - [ ] blog.*でアクセス成功
  - [ ] 管理画面ログイン成功

- [ ] toyota-phv.jp
  - [ ] ファイルrsync完了
  - [ ] DB移行完了
  - [ ] wp-config.php修正
  - [ ] URL置換完了
  - [ ] blog.*でアクセス成功
  - [ ] 管理画面ログイン成功

### Phase 1.5: Static site

- [ ] kuma8088.com
  - [ ] ファイルrsync完了
  - [ ] blog.*でアクセス成功（静的ファイル表示）

---

## 🚀 次のステップ（Phase 2: 本番切り替え）

Phase 1のblog.*テストで問題なければ、Phase 2で本番切り替え:

1. **Cloudflare DNS変更**:
   - Xserver Aレコード削除（162.43.116.72）
   - Cloudflare Tunnel CNAME追加（rootドメイン）

2. **nginx設定変更**:
   - server_name を blog.* → root domain に変更
   - 例: `blog.fx-trader-life.com` → `fx-trader-life.com www.fx-trader-life.com`

3. **WordPress URL再置換**:
   - blog.* → rootドメインに再度search-replace

詳細は `phase-a2-production-cutover.md` に記載予定

---

**作成**: 2025-11-09
**更新**: -
