# Phase A-2: 本番ドメイン移行詳細手順書

**作成日**: 2025-11-11
**ステータス**: Draft（実施前）
**関連Issue**: I008_production-domain-migration.md

---

## 📋 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [移行対象サイト](#移行対象サイト)
4. [移行戦略](#移行戦略)
5. [詳細手順](#詳細手順)
6. [ロールバック手順](#ロールバック手順)
7. [チェックリスト](#チェックリスト)

---

## 📋 概要

### 目的

Phase A-1で構築したテスト環境（`blog.*` サブドメイン）から、本番ドメイン（`domain.com`等）へ移行する。

### 現在の構成（Phase A-1）

```
blog.fx-trader-life.com          ← ルートサイト
├── /MFKC                        ← サブディレクトリサイト
├── /4-line-trade                ← サブディレクトリサイト
└── /lp                          ← サブディレクトリサイト

blog.webmakeprofit.org           ← ルートサイト
└── /coconala                    ← サブディレクトリサイト

blog.webmakesprofit.com          ← ルートサイト

blog.toyota-phv.jp               ← ルートサイト

blog.kuma8088.com                ← ルートサイト（テスト用）
├── /cameramanual                ← サブディレクトリサイト
├── /elementordemo1              ← サブディレクトリサイト
├── /elementordemo02             ← サブディレクトリサイト
├── /elementor-demo-03           ← サブディレクトリサイト
├── /elementor-demo-04           ← サブディレクトリサイト
└── /ec02test                    ← サブディレクトリサイト
```

**合計**: 14サイト（ルート5 + サブディレクトリ9）

### 目標構成（Phase A-2）

⚠️ **重要**: 移行先ドメイン構成を最終決定する必要があります。

**想定される移行パターン**:

#### パターンA: ルートドメインへ移行
```
blog.fx-trader-life.com → fx-trader-life.com
blog.webmakeprofit.org  → webmakeprofit.org
blog.webmakesprofit.com → webmakesprofit.com
blog.toyota-phv.jp      → toyota-phv.jp
```

#### パターンB: サブディレクトリはどうするか？

**選択肢1**: 独立サブドメイン化（推奨）
```
blog.fx-trader-life.com/MFKC       → mfkc.fx-trader-life.com
blog.fx-trader-life.com/4-line-trade → 4-line-trade.fx-trader-life.com
```
- メリット: Elementor等の互換性向上、独立したSSL証明書
- デメリット: Cloudflare Tunnel Public Hostname数が増加

**選択肢2**: 本番ドメイン配下のサブディレクトリ維持
```
blog.fx-trader-life.com/MFKC → fx-trader-life.com/MFKC
```
- メリット: URL構造シンプル、移行作業量少
- デメリット: P011問題が継続する可能性

**選択肢3**: 別ドメインへ移行
```
blog.fx-trader-life.com/MFKC → mfkc-trading.com (新規独立ドメイン)
```
- メリット: 完全独立、ブランディング向上
- デメリット: ドメイン取得・管理コスト、SEO再構築

---

## ⚠️ 前提条件

### 1. I009完了必須

- [ ] 全14サイトの動作確認完了
- [ ] Elementor Pro ライセンス状態確認完了
- [ ] 有料プラグインライセンス確認完了
- [ ] PHP互換性問題の修正完了

### 2. 移行先ドメイン確定

- [ ] 各サイトの移行先URL決定（選択肢1/2/3）
- [ ] 新規ドメイン取得完了（該当する場合）
- [ ] Cloudflare DNS管理権限確認

### 3. バックアップ取得

- [ ] 全データベースの完全バックアップ
- [ ] 全WordPressファイルのバックアップ
- [ ] Nginx設定ファイルのバックアップ
- [ ] Cloudflare Tunnel設定のスクリーンショット保存

### 4. テスト環境準備（推奨）

- [ ] 1サイトでテスト移行実施（推奨: elementordemo1）
- [ ] dry-run結果の検証

---

## 📊 移行対象サイト

### テーブル: 移行マッピング

⚠️ **以下は例です。実際の移行先を確定してください。**

| # | 現在URL | 移行先URL（例） | 優先度 | 備考 |
|---|---------|----------------|--------|------|
| 1 | blog.fx-trader-life.com | fx-trader-life.com | High | メインサイト |
| 2 | blog.fx-trader-life.com/MFKC | mfkc.fx-trader-life.com | Medium | パスワード保護 |
| 3 | blog.fx-trader-life.com/4-line-trade | 4line.fx-trader-life.com | Medium | パスワード保護 |
| 4 | blog.fx-trader-life.com/lp | lp.fx-trader-life.com | Low | LP |
| 5 | blog.webmakeprofit.org | webmakeprofit.org | High | メインサイト |
| 6 | blog.webmakeprofit.org/coconala | webmakeprofit.org/coconala | Medium | サブディレクトリ維持 |
| 7 | blog.webmakesprofit.com | webmakesprofit.com | High | メインサイト |
| 8 | blog.toyota-phv.jp | toyota-phv.jp | High | メインサイト |
| 9 | blog.kuma8088.com | kuma8088.com | Low | テストサイト |
| 10 | blog.kuma8088.com/cameramanual | camera.kuma8088.com | Low | PHP互換性問題あり |
| 11 | blog.kuma8088.com/elementordemo1 | demo1.kuma8088.com | Low | テストサイト |
| 12 | blog.kuma8088.com/elementordemo02 | demo2.kuma8088.com | Low | テストサイト |
| 13 | blog.kuma8088.com/elementor-demo-03 | demo3.kuma8088.com | Low | テストサイト |
| 14 | blog.kuma8088.com/elementor-demo-04 | demo4.kuma8088.com | Low | テストサイト |
| 15 | blog.kuma8088.com/ec02test | ec-test.kuma8088.com | Low | テストサイト |

---

## 🎯 移行戦略

### 推奨: 段階的移行

**Phase 1**: テストサイトで検証（1サイト）
- elementordemo1 を demo1.kuma8088.com へ移行
- 全手順を実施し、問題点を洗い出し

**Phase 2**: 優先度High（4サイト）
- fx-trader-life.com
- webmakeprofit.org
- webmakesprofit.com
- toyota-phv.jp

**Phase 3**: 優先度Medium（4サイト）
- サブドメイン化サイト
- または coconala（サブディレクトリ維持）

**Phase 4**: 優先度Low（残り6サイト）
- kuma8088.com配下のテストサイト

### 移行タイミング

- **推奨時間帯**: 日本時間 AM 2:00 - 5:00（トラフィック最小）
- **DNS TTL短縮**: 移行24時間前に実施（3600秒 → 300秒）
- **監視期間**: 移行後1週間は毎日確認

---

## 📝 詳細手順

### Phase 0: 事前準備（D-1日）

#### 0.1 DNS TTL短縮

**目的**: DNS切り替え時の伝播時間を短縮

```bash
# Cloudflare Dashboard で実施
# DNS → Records → 各レコードのTTLを300秒に変更
# - blog.fx-trader-life.com (CNAME)
# - blog.webmakeprofit.org (CNAME)
# - blog.webmakesprofit.com (CNAME)
# - blog.toyota-phv.jp (CNAME)
# - blog.kuma8088.com (CNAME)
```

#### 0.2 完全バックアップ

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 1. データベース全バックアップ
docker compose exec mariadb bash -c '
  mkdir -p /tmp/pre-migration-backup
  for db in $(mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW DATABASES;" | grep ^wp_); do
    echo "Backing up $db..."
    mysqldump -uroot -p$MYSQL_ROOT_PASSWORD \
      --single-transaction \
      --routines \
      --triggers \
      $db > /tmp/pre-migration-backup/${db}.sql
  done
'

# 2. バックアップをホストにコピー
docker cp blog-mariadb:/tmp/pre-migration-backup /mnt/backup-hdd/blog/backups/pre-migration-$(date +%Y%m%d)

# 3. WordPressファイルのスナップショット
tar -czf /mnt/backup-hdd/blog/backups/sites-pre-migration-$(date +%Y%m%d).tar.gz \
  /mnt/backup-hdd/blog/sites/

# 4. Nginx設定バックアップ
cp -r config/nginx /mnt/backup-hdd/blog/backups/nginx-pre-migration-$(date +%Y%m%d)

# 5. Cloudflare Tunnel設定スクリーンショット
# Zero Trust Dashboard → Networks → Tunnels → blog-tunnel → Public Hostnames
# → スクリーンショットを /mnt/backup-hdd/blog/backups/ に保存
```

#### 0.3 移行計画の最終確認

```bash
# 移行マッピング表をファイル化
cat > /tmp/migration-mapping.txt <<'EOF'
# 移行マッピング（Phase 2: 優先度High）
blog.fx-trader-life.com|fx-trader-life.com|/var/www/html/fx-trader-life|wp_fx_trader_life
blog.webmakeprofit.org|webmakeprofit.org|/var/www/html/webmakeprofit|wp_webmakeprofit
blog.webmakesprofit.com|webmakesprofit.com|/var/www/html/webmakesprofit|wp_webmakesprofit
blog.toyota-phv.jp|toyota-phv.jp|/var/www/html/toyota-phv|wp_toyota_phv
EOF
```

---

### Phase 1: テスト移行（1サイト検証）

#### サイト: blog.kuma8088.com/elementordemo1 → demo1.kuma8088.com

#### 1.1 Cloudflare Tunnel Public Hostname追加

```
Zero Trust Dashboard:
https://one.dash.cloudflare.com/

1. Networks → Tunnels → blog-tunnel → Configure
2. Public Hostnames → Add a public hostname

設定:
- Subdomain: demo1
- Domain: kuma8088.com
- Path: (空欄)
- Service: HTTP
- URL: nginx:80
- HTTP Host Header: demo1.kuma8088.com

3. Save hostname
```

#### 1.2 Nginx設定ファイル作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 新規仮想ホスト設定作成
cat > config/nginx/conf.d/demo1-kuma8088.conf <<'EOF'
# Virtual host: demo1.kuma8088.com
# Production domain for elementordemo1
server {
    listen 80;
    server_name demo1.kuma8088.com;

    root /var/www/html/kuma8088-elementordemo1;
    index index.php index.html;

    access_log /var/log/nginx/demo1-kuma8088-access.log;
    error_log /var/log/nginx/demo1-kuma8088-error.log;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
    }

    location ~ /\.ht {
        deny all;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    location = /robots.txt {
        log_not_found off;
        access_log off;
        allow all;
    }

    location ~* \.(css|gif|ico|jpeg|jpg|js|png|svg|woff|woff2)$ {
        expires max;
        log_not_found off;
    }
}
EOF

# 設定テスト
docker compose exec nginx nginx -t

# Nginxリロード
docker compose exec nginx nginx -s reload
```

#### 1.3 WordPress URL置換（データベース）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# dry-run（変更なし、確認のみ）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 上記で問題なければ、本実行
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTPSも置換（念のため）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
  SELECT option_value
  FROM wp_kuma8088_elementordemo1.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# 期待値: https://demo1.kuma8088.com
```

#### 1.4 Elementorキャッシュクリア

```bash
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --allow-root

docker compose exec wordpress wp cache flush \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --allow-root
```

#### 1.5 動作確認

```bash
# 1. DNS伝播確認
dig demo1.kuma8088.com +short
# Cloudflare IPが返ることを確認

# 2. SSL証明書確認
curl -I https://demo1.kuma8088.com
# HTTP/2 200 が返ることを確認

# 3. ブラウザアクセス確認
# https://demo1.kuma8088.com にアクセス
# - トップページ表示確認
# - 画像表示確認
# - 静的ファイル（CSS/JS）読み込み確認
# - Elementorエディタ動作確認（管理画面）
# - リンククリック動作確認
```

#### 1.6 旧URL → 新URLリダイレクト設定

```bash
# kuma8088.confに301リダイレクト追加
cat >> config/nginx/conf.d/kuma8088.conf <<'EOF'

# Redirect old elementordemo1 path to new subdomain
location = /elementordemo1 {
    return 301 https://demo1.kuma8088.com$request_uri;
}
location ^~ /elementordemo1/ {
    return 301 https://demo1.kuma8088.com$request_uri;
}
EOF

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# リダイレクトテスト
curl -I http://blog.kuma8088.com/elementordemo1
# HTTP/1.1 301 Moved Permanently
# Location: https://demo1.kuma8088.com/elementordemo1
```

#### 1.7 テスト移行の評価

- [ ] 全ページが正常表示されるか？
- [ ] 画像・CSS・JSが正常読み込みされるか？
- [ ] Elementorエディタが動作するか？
- [ ] リダイレクトが正常動作するか？
- [ ] SSL証明書エラーが発生しないか？

**問題があれば、ロールバック実施**（手順は後述）

---

### Phase 2: 本番サイト移行（優先度High 4サイト）

#### サイト1: blog.fx-trader-life.com → fx-trader-life.com

#### 2.1 Cloudflare Tunnel Public Hostname追加

```
Zero Trust Dashboard:
1. Networks → Tunnels → blog-tunnel → Configure
2. Public Hostnames → Add a public hostname

設定:
- Subdomain: (空欄)
- Domain: fx-trader-life.com
- Path: (空欄)
- Service: HTTP
- URL: nginx:80
- HTTP Host Header: fx-trader-life.com

3. Save hostname
```

#### 2.2 Nginx設定変更

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 既存設定をバックアップ
cp config/nginx/conf.d/fx-trader-life.conf config/nginx/conf.d/fx-trader-life.conf.bak

# server_name を変更
sed -i 's/server_name blog\.fx-trader-life\.com;/server_name fx-trader-life.com www.fx-trader-life.com;/' \
  config/nginx/conf.d/fx-trader-life.conf

# 設定確認
docker compose exec nginx nginx -t

# Nginxリロード
docker compose exec nginx nginx -s reload
```

#### 2.3 WordPress URL置換

```bash
# dry-run
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 本実行
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTPSも置換
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --allow-root
```

#### 2.4 キャッシュクリア

```bash
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life \
  --allow-root

docker compose exec wordpress wp cache flush \
  --path=/var/www/html/fx-trader-life \
  --allow-root
```

#### 2.5 動作確認

```bash
curl -I https://fx-trader-life.com
# ブラウザで https://fx-trader-life.com にアクセス
```

#### 2.6 旧URL → 新URLリダイレクト

```bash
# blog.fx-trader-life.com用の新規server{}ブロック追加
cat > config/nginx/conf.d/fx-trader-life-redirect.conf <<'EOF'
# Redirect old blog subdomain to production domain
server {
    listen 80;
    server_name blog.fx-trader-life.com;

    # Redirect all requests to production domain
    location / {
        return 301 https://fx-trader-life.com$request_uri;
    }
}
EOF

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# リダイレクトテスト
curl -I https://blog.fx-trader-life.com
# Location: https://fx-trader-life.com/
```

---

#### サイト2-4: 同様の手順を繰り返し

- **webmakeprofit.org**
- **webmakesprofit.com**
- **toyota-phv.jp**

（各サイトで2.1〜2.6を実施）

---

### Phase 3: サブディレクトリサイト移行

#### パターンA: サブドメイン化（例: MFKC）

##### 3.1 移行: blog.fx-trader-life.com/MFKC → mfkc.fx-trader-life.com

```bash
# 1. Cloudflare Tunnel Public Hostname追加
# Subdomain: mfkc
# Domain: fx-trader-life.com
# Service: HTTP, URL: nginx:80

# 2. Nginx新規仮想ホスト作成
cat > config/nginx/conf.d/mfkc-fx-trader-life.conf <<'EOF'
server {
    listen 80;
    server_name mfkc.fx-trader-life.com;

    root /var/www/html/fx-trader-life-mfkc;
    index index.php index.html;

    access_log /var/log/nginx/mfkc-fx-trader-life-access.log;
    error_log /var/log/nginx/mfkc-fx-trader-life-error.log;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
    }

    location ~ /\.ht {
        deny all;
    }
}
EOF

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3. WordPress URL置換
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com/MFKC' \
  'https://mfkc.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-mfkc \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. キャッシュクリア + 動作確認
# 5. 旧URL → 新URLリダイレクト（fx-trader-life.confから/MFKCロケーション削除 & リダイレクト追加）
```

#### パターンB: サブディレクトリ維持（例: coconala）

##### 3.2 移行: blog.webmakeprofit.org/coconala → webmakeprofit.org/coconala

```bash
# 1. Cloudflare Tunnel設定変更不要（既存のwebmakeprofit.orgで対応）

# 2. Nginx設定はそのまま（webmakeprofit.confのserver_name変更済み）

# 3. WordPress URL置換
docker compose exec wordpress wp search-replace \
  'http://blog.webmakeprofit.org/coconala' \
  'https://webmakeprofit.org/coconala' \
  --path=/var/www/html/webmakeprofit-coconala \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. 動作確認
curl -I https://webmakeprofit.org/coconala
```

---

## 🔄 ロールバック手順

### 緊急ロールバック（移行後に致命的問題発生）

#### ロールバックシナリオ

- サイトが全く表示されない
- データベース破損が疑われる
- Elementor/プラグインが完全に動作しない

#### 手順

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 1. Nginx設定を旧構成に戻す
cp config/nginx/conf.d/fx-trader-life.conf.bak config/nginx/conf.d/fx-trader-life.conf
rm -f config/nginx/conf.d/fx-trader-life-redirect.conf
docker compose exec nginx nginx -s reload

# 2. Cloudflare Tunnel Public Hostname削除
# Zero Trust Dashboard → Networks → Tunnels → blog-tunnel
# → 新規追加したホスト名（fx-trader-life.com）を削除

# 3. データベースバックアップからリストア
BACKUP_DATE=$(date +%Y%m%d)
docker cp /mnt/backup-hdd/blog/backups/pre-migration-${BACKUP_DATE}/wp_fx_trader_life.sql blog-mariadb:/tmp/

docker compose exec mariadb bash -c "
  mysql -uroot -p\$MYSQL_ROOT_PASSWORD wp_fx_trader_life < /tmp/wp_fx_trader_life.sql
"

# 4. 動作確認
curl -I https://blog.fx-trader-life.com
# 旧URLで動作することを確認
```

### 部分ロールバック（特定サイトのみ問題）

特定サイトのみ旧URL（`blog.*`）に戻し、他サイトはそのまま本番運用継続。

---

## ✅ チェックリスト

### 事前準備（D-1日）

- [ ] I009完了確認（全サイト動作確認・ライセンス確認）
- [ ] 移行先ドメイン最終決定（移行マッピング表作成）
- [ ] DNS TTL短縮実施（3600秒 → 300秒）
- [ ] 完全バックアップ取得
  - [ ] データベース（全16サイト）
  - [ ] WordPressファイル（95GB）
  - [ ] Nginx設定
  - [ ] Cloudflare Tunnel設定スクリーンショット
- [ ] テスト移行計画作成（elementordemo1で検証）

### Phase 1: テスト移行（Dデー）

- [ ] Cloudflare Tunnel Public Hostname追加（demo1.kuma8088.com）
- [ ] Nginx設定ファイル作成
- [ ] WordPress URL置換（dry-run → 本実行）
- [ ] キャッシュクリア
- [ ] 動作確認
  - [ ] トップページ表示
  - [ ] 画像表示
  - [ ] 静的ファイル読み込み
  - [ ] Elementorエディタ動作
  - [ ] リンク動作
- [ ] 301リダイレクト設定
- [ ] 問題なければPhase 2へ進行判断

### Phase 2: 本番サイト移行（優先度High）

**各サイトごとに実施**:

#### fx-trader-life.com
- [ ] Cloudflare Tunnel Public Hostname追加
- [ ] Nginx設定変更（server_name変更）
- [ ] WordPress URL置換（dry-run → 本実行）
- [ ] キャッシュクリア
- [ ] 動作確認
- [ ] 301リダイレクト設定
- [ ] 24時間安定動作確認

#### webmakeprofit.org
- [ ] （同上）

#### webmakesprofit.com
- [ ] （同上）

#### toyota-phv.jp
- [ ] （同上）

### Phase 3: サブディレクトリサイト移行

**サブドメイン化サイト**:
- [ ] MFKC → mfkc.fx-trader-life.com
- [ ] 4-line-trade → 4line.fx-trader-life.com
- [ ] lp → lp.fx-trader-life.com
- [ ] （kuma8088.com配下の5サイト）

**サブディレクトリ維持サイト**:
- [ ] coconala → webmakeprofit.org/coconala

### 移行後監視（D+1週間）

- [ ] 毎日アクセスログ確認
- [ ] エラーログ確認
- [ ] 404エラー頻発していないか
- [ ] リダイレクトループ発生していないか
- [ ] SSL証明書エラー発生していないか
- [ ] パフォーマンス劣化していないか

### Phase 4: 旧blog.*サブドメイン削除（D+1ヶ月後）

- [ ] 301リダイレクト期間終了（最低1ヶ月）
- [ ] Googleアナリティクス等でblog.*へのアクセスがゼロに近いことを確認
- [ ] Cloudflare Tunnel Public Hostname削除（blog.*）
- [ ] Nginx設定からリダイレクト設定削除
- [ ] DNS TTLを元に戻す（3600秒）

---

## 📚 参考情報

### 関連ドキュメント

- [I008_production-domain-migration.md](./issue/active/I008_production-domain-migration.md) - Issue詳細
- [I009_site-validation.md](./issue/active/I009_site-validation.md) - 事前確認項目
- [phase-a1-bulk-migration.md](./phase-a1-bulk-migration.md) - Phase A-1実装記録
- [cloudflare-tunnel-hostnames.md](./cloudflare-tunnel-hostnames.md) - Cloudflare Tunnel設定

### WordPress公式ドキュメント

- [Moving WordPress](https://wordpress.org/support/article/moving-wordpress/)
- [Changing The Site URL](https://wordpress.org/support/article/changing-the-site-url/)

### Cloudflare公式ドキュメント

- [Cloudflare Tunnel Public Hostnames](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/routing-to-tunnel/dns/)

---

## 🆘 トラブルシューティング

### 問題1: サイトが表示されない（HTTP 502）

**原因**: Nginxがバックエンド（WordPress）に接続できない

```bash
# Nginxログ確認
docker compose logs nginx | tail -50

# WordPress起動確認
docker compose ps wordpress

# Nginx設定テスト
docker compose exec nginx nginx -t
```

### 問題2: 画像が表示されない

**原因**: URL置換漏れ、またはパーミッション問題

```bash
# データベース内URL確認
docker compose exec mariadb mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
  SELECT guid FROM wp_fx_trader_life.wp_posts
  WHERE post_type = 'attachment'
  LIMIT 10;
"
# 旧URLが残っている場合は再度search-replace実行

# パーミッション確認
docker compose exec wordpress ls -la /var/www/html/fx-trader-life/wp-content/uploads/
# 82:82 (www-data) 所有権確認
```

### 問題3: Elementorエディタが動作しない

**原因**: キャッシュ未クリア、またはライセンス無効化

```bash
# キャッシュ再クリア
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life \
  --allow-root

# Elementor Proライセンス確認
docker compose exec wordpress wp option get elementor_pro_license_key \
  --path=/var/www/html/fx-trader-life \
  --allow-root

# ライセンス再認証が必要な場合
# WordPress管理画面 → Elementor → License → Disconnect & Reconnect
```

### 問題4: リダイレクトループ

**原因**: Nginx設定の重複、またはWordPress側の設定不整合

```bash
# Nginx設定確認
docker compose exec nginx cat /etc/nginx/conf.d/fx-trader-life.conf | grep -A5 "location /"

# WordPress URL確認
docker compose exec mariadb mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
  SELECT option_name, option_value
  FROM wp_fx_trader_life.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# siteurl と home が一致していることを確認
```

---

**作成日**: 2025-11-11
**バージョン**: 1.0
**作成者**: Claude
**ステータス**: Draft（実施前）

---

## 次のステップ

1. **移行先ドメイン最終確認**: 上記「移行対象サイト」テーブルを確定
2. **I009実施**: 全サイトの動作確認・ライセンス確認
3. **テスト移行実施**: elementordemo1で全手順を検証
4. **本番移行計画承認**: ユーザーと最終確認
5. **Phase 2実行**: 優先度Highサイトから段階的移行

**重要**: 移行先ドメイン構成（特にサブディレクトリサイトの扱い）を確定してから実施してください。
