# Phase A-2: 本番ドメイン移行詳細手順書（全サブドメイン化）

**作成日**: 2025-11-11
**更新日**: 2025-11-11
**ステータス**: Draft（実施前）
**関連Issue**: I008_production-domain-migration.md
**移行方針**: **全サイトをサブドメイン化**（P011解決済み、長期運用の保守性重視）

---

## 🚀 作業順序クイックリファレンス

### 正しい作業順序（必読）

```
1. Cloudflare Tunnel Public Hostname追加 ← 最初
   └─ 新ドメインのルーティング確立

2. Nginx設定変更 (server_name変更)
   └─ Nginxが新ドメインを処理可能に

3. Nginx reload
   └─ 設定を反映

4. WordPress URL置換 (wp search-replace)
   └─ データベース内URLを新ドメインに変更

5. Elementorキャッシュクリア
   └─ キャッシュされたURLをクリア

6. 動作確認
   └─ 新ドメインで正常動作を確認

7. 301リダイレクト設定
   └─ 旧URL → 新URL自動転送

8. WP Mail SMTP設定（全Phase完了後）
   └─ 全サイトのメール送信設定
```

### 重要な注意事項

- ✅ **Cloudflare DNS変更は不要**: Public Hostname追加で自動設定
- ✅ **作業はCloudflare Tunnel設定から**: Nginx設定変更の前に実施
- ❌ **DNS A/CNAMEレコード手動追加は不要**: Cloudflare Zero Trust Dashboardで完結

---

## 📋 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [移行対象サイト（全14サイト確定）](#移行対象サイト全14サイト確定)
4. [移行戦略](#移行戦略)
5. [詳細手順](#詳細手順)
6. [ロールバック手順](#ロールバック手順)
7. [チェックリスト](#チェックリスト)

---

## 📋 概要

### 目的

Phase A-1で構築したテスト環境（`blog.*` サブドメイン）から、本番ドメインへ移行する。
**全サイトをサブドメイン化**し、長期運用の保守性を確保する。

### 移行方針の決定事項

✅ **全サイトをサブドメイン化**
- ルートサイト（5サイト）: `blog.domain.com` → `domain.com`
- サブディレクトリサイト（9サイト）: `blog.domain.com/path` → `path.domain.com`

### 重要: 301リダイレクトの実装

既存URL（`blog.*`）でアクセスするユーザーのため、**すべての旧URLから新URLへ301リダイレクト**を設定します。

---

## 📊 移行対象サイト（全14サイト確定）

### Phase 2: ルートサイト移行（5サイト）

| # | 現在URL | 移行先URL | 優先度 | データベース名 | ディレクトリ |
|---|---------|-----------|--------|---------------|-------------|
| 1 | blog.fx-trader-life.com | fx-trader-life.com | High | wp_fx_trader_life | /var/www/html/fx-trader-life |
| 2 | blog.webmakeprofit.org | webmakeprofit.org | High | wp_webmakeprofit | /var/www/html/webmakeprofit |
| 3 | blog.webmakesprofit.com | webmakesprofit.com | High | wp_webmakesprofit | /var/www/html/webmakesprofit |
| 4 | blog.toyota-phv.jp | toyota-phv.jp | High | wp_toyota_phv | /var/www/html/toyota-phv |
| 5 | blog.kuma8088.com | kuma8088.com | Low | wp_kuma8088 | /var/www/html/kuma8088 |

### Phase 3: サブドメイン化移行（9サイト）

#### fx-trader-life.com 配下（3サイト）

| # | 現在URL | 移行先URL | 優先度 | データベース名 | ディレクトリ |
|---|---------|-----------|--------|---------------|-------------|
| 6 | blog.fx-trader-life.com/MFKC | mfkc.fx-trader-life.com | Medium | wp_fx_trader_life_mfkc | /var/www/html/fx-trader-life-mfkc |
| 7 | blog.fx-trader-life.com/4-line-trade | 4line.fx-trader-life.com | Medium | wp_fx_trader_life_4line | /var/www/html/fx-trader-life-4line |
| 8 | blog.fx-trader-life.com/lp | lp.fx-trader-life.com | Low | wp_fx_trader_life_lp | /var/www/html/fx-trader-life-lp |

#### webmakeprofit.org 配下（1サイト）

| # | 現在URL | 移行先URL | 優先度 | データベース名 | ディレクトリ |
|---|---------|-----------|--------|---------------|-------------|
| 9 | blog.webmakeprofit.org/coconala | coconala.webmakeprofit.org | Medium | wp_webmakeprofit_coconala | /var/www/html/webmakeprofit-coconala |

#### kuma8088.com 配下（5サイト）

| # | 現在URL | 移行先URL | 優先度 | データベース名 | ディレクトリ |
|---|---------|-----------|--------|---------------|-------------|
| 10 | blog.kuma8088.com/cameramanual | camera.kuma8088.com | Low | wp_kuma8088_cameramanual | /var/www/html/kuma8088-cameramanual |
| 11 | blog.kuma8088.com/elementordemo1 | demo1.kuma8088.com | Low | wp_kuma8088_elementordemo1 | /var/www/html/kuma8088-elementordemo1 |
| 12 | blog.kuma8088.com/elementordemo02 | demo2.kuma8088.com | Low | wp_kuma8088_elementordemo02 | /var/www/html/kuma8088-elementordemo02 |
| 13 | blog.kuma8088.com/elementor-demo-03 | demo3.kuma8088.com | Low | wp_kuma8088_elementor_demo_03 | /var/www/html/kuma8088-elementor-demo-03 |
| 14 | blog.kuma8088.com/elementor-demo-04 | demo4.kuma8088.com | Low | wp_kuma8088_elementor_demo_04 | /var/www/html/kuma8088-elementor-demo-04 |
| 15 | blog.kuma8088.com/ec02test | ec-test.kuma8088.com | Low | wp_kuma8088_ec02test | /var/www/html/kuma8088-ec02test |

**合計**: 15サイト（ルート5 + サブドメイン化9）

---

## ⚠️ 前提条件

### 1. I009完了必須

- [x] 全14サイトの動作確認完了
- [x] Elementor Pro ライセンス状態確認完了
- [x] 有料プラグインライセンス確認完了
- [ ] PHP互換性問題の修正完了（camera.kuma8088.com等）
  - **注記**: cameramanualサイトは優先度Lowのため、移行後に対処
  - **問題**: 古いテーマ（sinka）が `create_function()` 等のPHP 8.x非対応関数を使用
  - **影響**: 現在PHP 7.4で動作中のため移行自体に影響なし
  - **対処時期**: Phase A-2完了後、PHP 8.x移行時に対処

### 2. バックアップ取得

- [ ] 全データベースの完全バックアップ
- [ ] 全WordPressファイルのバックアップ
- [ ] Nginx設定ファイルのバックアップ
- [ ] Cloudflare Tunnel設定のスクリーンショット保存

**推奨コマンド**: Phase 0の0.2を参照

### 3. DNS TTL短縮（移行24時間前）- **オプション**

- [ ] Cloudflare DNS設定でTTLを300秒に短縮（Cloudflare Tunnel使用時はオプション）
  - **注記**: Public Hostname追加で自動的にDNS設定されるため、このステップは省略可能
  - **推奨**: 念のため既存blog.*サブドメインのTTLを短縮（ロールバック時の影響最小化）

---

## 🎯 移行戦略

### 🔄 作業順序の原則（重要）

**正しい順序**:
1. **Cloudflare Tunnel Public Hostname追加** ← **最初**
2. **Nginx設定変更** (server_name変更)
3. **Nginx reload**
4. **WordPress URL置換**
5. **Elementorキャッシュクリア**
6. **動作確認**
7. **301リダイレクト設定**

**重要事項**:
- ✅ **Cloudflare DNS変更は不要**: Tunnel Public Hostnameを追加すると自動的にDNSルーティングが設定されます
- ✅ **Cloudflare Tunnel設定を先に**: 新しいドメインへのルーティングを確立してからNginx設定を変更
- ✅ **Nginx設定変更は後**: Cloudflare Tunnelが新ドメインを受け付けた後にNginxが対応
- ❌ **DNS A/CNAMEレコード手動追加は不要**: Cloudflare Zero Trust Dashboardで完結

**理由**:
- Cloudflare Tunnelを使用している場合、Public Hostnameの追加だけでCloudflareが自動的に該当ドメインへのトラフィックをTunnelにルーティングします
- 従来のDNS設定（A/CNAMEレコード手動追加）は不要です
- Nginx設定変更前にCloudflare Tunnel設定を完了させることで、Nginx reloadと同時に新ドメインが動作可能になります

### 段階的移行（推奨）

**Phase 1**: テスト移行（1サイト検証）
- `blog.kuma8088.com/elementordemo1` → `demo1.kuma8088.com`
- 全手順を実施し、問題点を洗い出し
- **所要時間**: 2-3時間

**Phase 2**: ルートサイト移行（5サイト）
- 優先度High: fx-trader-life, webmakeprofit, webmakesprofit, toyota-phv
- 優先度Low: kuma8088.com
- **所要時間**: 各サイト1時間 × 5 = 5時間

**Phase 3**: サブドメイン化移行（9サイト）
- 優先度Medium: MFKC, 4line, coconala
- 優先度Low: camera, demo1-4, ec-test
- **所要時間**: 各サイト1.5時間 × 9 = 13.5時間

**合計所要時間**: 約20時間（2-3日間に分散推奨）

---

## 📝 詳細手順

### Phase 0: 事前準備（D-1日）

#### 0.1 DNS TTL短縮（オプション）

**注意**: Cloudflare Tunnelを使用している場合、Public Hostname追加で自動的にDNS設定されるため、このステップは**オプション**です。

ただし、念のため既存のblog.*サブドメインのTTLを短縮しておくことを推奨します（ロールバック時の影響を最小化）。

```bash
# Cloudflare Dashboard で実施
# DNS → Records → 各レコードを確認（自動作成されたレコード）
# blog.fx-trader-life.com (CNAME または Tunnel routing)
# blog.webmakeprofit.org (CNAME または Tunnel routing)
# blog.webmakesprofit.com (CNAME または Tunnel routing)
# blog.toyota-phv.jp (CNAME または Tunnel routing)
# blog.kuma8088.com (CNAME または Tunnel routing)

# TTLを300秒に短縮（自動作成されたレコードのTTL変更は通常不要）
```

**Cloudflare Tunnelの場合の確認事項**:
- Zero Trust Dashboard → Networks → Tunnels → blog-tunnel → Configure
- Public Hostnames タブで現在のホスト名を確認
- 新しいホスト名追加時に自動的にDNSルーティングが設定されます

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
# 注: wp-config.phpの所有者が82:82 (www-data)、パーミッション600のため、sudoが必要
sudo tar -czf /mnt/backup-hdd/blog/backups/sites-pre-migration-$(date +%Y%m%d).tar.gz \
  -C /mnt/backup-hdd/blog/sites/ .

# 4. Nginx設定バックアップ
cp -r config/nginx /mnt/backup-hdd/blog/backups/nginx-pre-migration-$(date +%Y%m%d)

# 5. バックアップ確認
echo "=== データベースバックアップ確認 ==="
ls -lh /mnt/backup-hdd/blog/backups/pre-migration-$(date +%Y%m%d)/
echo "データベース数: $(ls -1 /mnt/backup-hdd/blog/backups/pre-migration-$(date +%Y%m%d)/*.sql 2>/dev/null | wc -l)"

echo -e "\n=== WordPressファイルバックアップ確認 ==="
ls -lh /mnt/backup-hdd/blog/backups/sites-pre-migration-$(date +%Y%m%d).tar.gz
# tarアーカイブの内容検証（最初の20ファイルを表示）
tar -tzf /mnt/backup-hdd/blog/backups/sites-pre-migration-$(date +%Y%m%d).tar.gz | head -20

echo -e "\n=== Nginx設定バックアップ確認 ==="
ls -lh /mnt/backup-hdd/blog/backups/nginx-pre-migration-$(date +%Y%m%d)/
ls -1 /mnt/backup-hdd/blog/backups/nginx-pre-migration-$(date +%Y%m%d)/conf.d/

echo -e "\n=== バックアップサイズサマリー ==="
du -sh /mnt/backup-hdd/blog/backups/pre-migration-$(date +%Y%m%d)/
du -sh /mnt/backup-hdd/blog/backups/sites-pre-migration-$(date +%Y%m%d).tar.gz
du -sh /mnt/backup-hdd/blog/backups/nginx-pre-migration-$(date +%Y%m%d)/
```

---

### Phase 1: テスト移行（demo1.kuma8088.com）

#### サイト: blog.kuma8088.com/elementordemo1 → demo1.kuma8088.com

このサイトで全手順を検証します。

#### 1.1 Cloudflare Tunnel Public Hostname追加（最初のステップ）

**重要**: この設定により、Cloudflareが自動的にDNSルーティングを設定します。手動でDNS A/CNAMEレコードを追加する必要はありません。

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
- HTTP Host Header: (空欄 または demo1.kuma8088.com)

3. Save hostname

設定後の確認:
- Public Hostnamesリストに demo1.kuma8088.com が表示されることを確認
- Statusが "Healthy" になるまで数秒待機

注意事項:
- 保存後、数秒〜数分でDNS伝播が完了します（通常は即座）
- dig demo1.kuma8088.com で Cloudflare IPが返ることを確認可能
- Cloudflare Dashboard → DNS → Records には自動的にレコードが追加されます
```

#### 1.2 Nginx新規仮想ホスト作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 新規server{}ブロック作成
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

#### 1.3 WordPress URL置換

**重要**: WordPressのsiteurl/homeは通常HTTPSで保存されているため、HTTPS版を先に実行します。

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 1. HTTPS版のdry-run（メイン: siteurl/home等を含む）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 2. HTTP版のdry-run（念のため: post_content内ハードコードURL用）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 出力を確認: 両方の "X replacements" の数を記録

# 3. HTTPS版の本実行
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. HTTP版の本実行
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementordemo1' \
  'https://demo1.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 5. データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_elementordemo1.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# 期待値: https://demo1.kuma8088.com
```

#### 1.4 Elementorキャッシュクリア

```bash
# Elementor導入サイトのみ（未導入ならスキップ）
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
# - Elementorエディタ動作確認（WordPress管理画面）
# - 内部リンククリック動作確認
```

#### 1.6 旧URL → 新URL 301リダイレクト設定（重要）

既存URL（`blog.kuma8088.com/elementordemo1`）でアクセスするユーザーを新URLへ自動転送します。

**方針**:
- kuma8088-subdirs-generated.inc から該当サイトの設定を削除
- kuma8088.conf に301リダイレクトを追加

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 1. 自動生成ファイルをバックアップ
cp config/nginx/conf.d/kuma8088-subdirs-generated.inc \
   config/nginx/conf.d/kuma8088-subdirs-generated.inc.pre-demo1

# 2. elementordemo1関連の設定を削除（29行から57行までを削除）
sed -i '30,57d' config/nginx/conf.d/kuma8088-subdirs-generated.inc

# 削除内容確認（elementordemo1が含まれないこと）
grep -n "elementordemo1" config/nginx/conf.d/kuma8088-subdirs-generated.inc
# 期待値: 何も出力されない（削除成功）

# 3. kuma8088.confに301リダイレクトを追加
# includeディレクティブの直後に追加
sed -i '/include .*kuma8088-subdirs-generated.inc;/a\
\
    # Redirect old elementordemo1 path to new subdomain\
    location /elementordemo1 {\
        return 301 https://demo1.kuma8088.com$request_uri;\
    }\
    location /elementordemo1/ {\
        return 301 https://demo1.kuma8088.com$request_uri;\
    }' config/nginx/conf.d/kuma8088.conf

# 追加内容確認
grep -A 6 "Redirect old elementordemo1" config/nginx/conf.d/kuma8088.conf

# 4. 設定テスト
docker compose exec nginx nginx -t

# 5. Nginxリロード
docker compose exec nginx nginx -s reload

# 6. リダイレクトテスト
curl -I https://blog.kuma8088.com/elementordemo1
# 期待値:
# HTTP/1.1 301 Moved Permanently
# Location: https://demo1.kuma8088.com/elementordemo1

curl -I https://blog.kuma8088.com/elementordemo1/
# 期待値:
# HTTP/1.1 301 Moved Permanently
# Location: https://demo1.kuma8088.com/elementordemo1/
```

**注意**: スクリプト `generate-nginx-subdirectories.sh` を再実行する場合は、elementordemo1を除外するよう修正が必要です。

#### 1.7 テスト移行の評価

以下をすべて確認してください:

- [ ] 新URL（https://demo1.kuma8088.com）で全ページが正常表示
- [ ] 画像・CSS・JSが正常読み込み
- [ ] Elementorエディタが動作
- [ ] 旧URL（https://blog.kuma8088.com/elementordemo1）が新URLへ301リダイレクト
- [ ] リダイレクトループが発生していない
- [ ] SSL証明書エラーが発生していない

**問題があれば、ロールバック実施**（手順は後述）

**問題なければ、Phase 2へ進行**

---

### Phase 2: ルートサイト移行（5サイト）

#### サイト1: blog.fx-trader-life.com → fx-trader-life.com

##### 2.1 Cloudflare Tunnel Public Hostname追加

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

3. Save hostname

注意: www.fx-trader-life.com も追加する場合は別途Public Hostname追加
```

##### 2.2 Nginx設定変更

**方針**:
- 既存server{}ブロックの `server_name` を本番ドメインに変更
- 旧ドメイン（blog.*）からのリダイレクト用server{}ブロックを追加

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 既存設定をバックアップ
cp config/nginx/conf.d/fx-trader-life.conf config/nginx/conf.d/fx-trader-life.conf.pre-migration

# 1. server_name を本番ドメインに変更
sed -i 's/server_name blog\.fx-trader-life\.com;/server_name fx-trader-life.com www.fx-trader-life.com;/' \
  config/nginx/conf.d/fx-trader-life.conf

# 2. 旧ドメインリダイレクト用server{}ブロックを追加
cat >> config/nginx/conf.d/fx-trader-life.conf <<'EOF'

# Redirect old domain to production domain
server {
    listen 80;
    server_name blog.fx-trader-life.com;
    return 301 https://fx-trader-life.com$request_uri;
}
EOF

# 3. 設定確認
echo "=== server_name 確認 ==="
grep "server_name" config/nginx/conf.d/fx-trader-life.conf
# 期待値:
#   server_name fx-trader-life.com www.fx-trader-life.com;
#   server_name blog.fx-trader-life.com;

# 4. 設定テスト
docker compose exec nginx nginx -t

# 5. Nginxリロード
docker compose exec nginx nginx -s reload

# 6. リダイレクトテスト
curl -I https://blog.fx-trader-life.com
# 期待値:
# HTTP/1.1 301 Moved Permanently
# Location: https://fx-trader-life.com/
```

##### 2.3 WordPress URL置換

```bash
# 1. HTTPS版のdry-run（メイン: siteurl/home等を含む）
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 2. HTTP版のdry-run（念のため: post_content内ハードコードURL用）
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 出力を確認: 両方の "X replacements" の数を記録

# 3. HTTPS版の本実行
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. HTTP版の本実行
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com' \
  'https://fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 5. データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_fx_trader_life.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# 期待値: https://fx-trader-life.com
```

##### 2.4 キャッシュクリア

```bash
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life \
  --allow-root

docker compose exec wordpress wp cache flush \
  --path=/var/www/html/fx-trader-life \
  --allow-root
```

##### 2.5 動作確認

```bash
# DNS確認
dig fx-trader-life.com +short

# HTTPアクセス確認
curl -I https://fx-trader-life.com

# ブラウザで動作確認
# https://fx-trader-life.com にアクセス
```

##### 2.6 24時間安定動作監視

```bash
# 翌日、エラーログ確認
docker compose logs nginx | grep fx-trader-life | grep -i error

# アクセスログ確認（リダイレクトが正常動作しているか）
docker compose exec nginx tail -100 /var/log/nginx/fx-trader-life-redirect-access.log
```

---

#### サイト2: blog.webmakeprofit.org → webmakeprofit.org

##### 2.1 Cloudflare Tunnel Public Hostname追加

```
Zero Trust Dashboard:
1. Networks → Tunnels → blog-tunnel → Configure
2. Public Hostnames → Add a public hostname

設定:
- Subdomain: (空欄)
- Domain: webmakeprofit.org
- Path: (空欄)
- Service: HTTP
- URL: nginx:80

3. Save hostname
```

##### 2.2 Nginx設定変更

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 既存設定をバックアップ
cp config/nginx/conf.d/webmakeprofit.conf config/nginx/conf.d/webmakeprofit.conf.pre-migration

# 1. server_name を本番ドメインに変更
sed -i 's/server_name blog\.webmakeprofit\.org;/server_name webmakeprofit.org www.webmakeprofit.org;/' \
  config/nginx/conf.d/webmakeprofit.conf

# 2. 旧ドメインリダイレクト用server{}ブロックを追加
cat >> config/nginx/conf.d/webmakeprofit.conf <<'EOF'

# Redirect old domain to production domain
server {
    listen 80;
    server_name blog.webmakeprofit.org;
    return 301 https://webmakeprofit.org$request_uri;
}
EOF

# 3. 設定確認
grep "server_name" config/nginx/conf.d/webmakeprofit.conf

# 4. 設定テスト
docker compose exec nginx nginx -t

# 5. Nginxリロード
docker compose exec nginx nginx -s reload

# 6. リダイレクトテスト
curl -I https://blog.webmakeprofit.org
```

##### 2.3 WordPress URL置換

```bash
# 1. HTTPS版のdry-run（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.webmakeprofit.org' \
  'https://webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 2. HTTP版のdry-run（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.webmakeprofit.org' \
  'https://webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 出力を確認: 両方の "X replacements" の数を記録

# 3. HTTPS版の本実行
docker compose exec wordpress wp search-replace \
  'https://blog.webmakeprofit.org' \
  'https://webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. HTTP版の本実行
docker compose exec wordpress wp search-replace \
  'http://blog.webmakeprofit.org' \
  'https://webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 5. データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_webmakeprofit.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# 期待値: https://webmakeprofit.org
```

##### 2.4 キャッシュクリア

```bash
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/webmakeprofit \
  --allow-root

docker compose exec wordpress wp cache flush \
  --path=/var/www/html/webmakeprofit \
  --allow-root
```

##### 2.5 動作確認

```bash
# DNS確認
dig webmakeprofit.org +short

# HTTPアクセス確認
curl -I https://webmakeprofit.org

# ブラウザで動作確認
# https://webmakeprofit.org にアクセス
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload
```

---

#### サイト3: blog.webmakesprofit.com → webmakesprofit.com

**方針**: サイト2と同じ手順（Cloudflare Tunnel → Nginx設定変更+301リダイレクト → URL置換 → 動作確認）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Cloudflare Tunnel Public Hostname: webmakesprofit.com を追加

# Nginx設定
cp config/nginx/conf.d/webmakesprofit.conf config/nginx/conf.d/webmakesprofit.conf.pre-migration
sed -i 's/server_name blog\.webmakesprofit\.com;/server_name webmakesprofit.com www.webmakesprofit.com;/' \
  config/nginx/conf.d/webmakesprofit.conf

cat >> config/nginx/conf.d/webmakesprofit.conf <<'EOF'

# Redirect old domain to production domain
server {
    listen 80;
    server_name blog.webmakesprofit.com;
    return 301 https://webmakesprofit.com$request_uri;
}
EOF

docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# WordPress URL置換（dry-run→actual、HTTPS→HTTP順）
docker compose exec wordpress wp search-replace \
  'https://blog.webmakesprofit.com' 'https://webmakesprofit.com' \
  --path=/var/www/html/webmakesprofit --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.webmakesprofit.com' 'https://webmakesprofit.com' \
  --path=/var/www/html/webmakesprofit --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'https://blog.webmakesprofit.com' 'https://webmakesprofit.com' \
  --path=/var/www/html/webmakesprofit --all-tables --skip-columns=guid --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.webmakesprofit.com' 'https://webmakesprofit.com' \
  --path=/var/www/html/webmakesprofit --all-tables --skip-columns=guid --allow-root

# DB確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value FROM wp_webmakesprofit.wp_options WHERE option_name IN ('siteurl', 'home');"

# キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css --path=/var/www/html/webmakesprofit --allow-root
docker compose exec wordpress wp cache flush --path=/var/www/html/webmakesprofit --allow-root

# 動作確認
curl -I https://webmakesprofit.com
curl -I https://blog.webmakesprofit.com  # 301確認
```

---

#### サイト4: blog.toyota-phv.jp → toyota-phv.jp

**方針**: サイト2/3と同じ手順

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Cloudflare Tunnel Public Hostname: toyota-phv.jp を追加

# Nginx設定
cp config/nginx/conf.d/toyota-phv.conf config/nginx/conf.d/toyota-phv.conf.pre-migration
sed -i 's/server_name blog\.toyota-phv\.jp;/server_name toyota-phv.jp www.toyota-phv.jp;/' \
  config/nginx/conf.d/toyota-phv.conf

cat >> config/nginx/conf.d/toyota-phv.conf <<'EOF'

# Redirect old domain to production domain
server {
    listen 80;
    server_name blog.toyota-phv.jp;
    return 301 https://toyota-phv.jp$request_uri;
}
EOF

docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# WordPress URL置換（dry-run→actual、HTTPS→HTTP順）
docker compose exec wordpress wp search-replace \
  'https://blog.toyota-phv.jp' 'https://toyota-phv.jp' \
  --path=/var/www/html/toyota-phv --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.toyota-phv.jp' 'https://toyota-phv.jp' \
  --path=/var/www/html/toyota-phv --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'https://blog.toyota-phv.jp' 'https://toyota-phv.jp' \
  --path=/var/www/html/toyota-phv --all-tables --skip-columns=guid --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.toyota-phv.jp' 'https://toyota-phv.jp' \
  --path=/var/www/html/toyota-phv --all-tables --skip-columns=guid --allow-root

# DB確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value FROM wp_toyota_phv.wp_options WHERE option_name IN ('siteurl', 'home');"

# キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css --path=/var/www/html/toyota-phv --allow-root
docker compose exec wordpress wp cache flush --path=/var/www/html/toyota-phv --allow-root

# 動作確認
curl -I https://toyota-phv.jp
curl -I https://blog.toyota-phv.jp  # 301確認
```

---

#### サイト5: blog.kuma8088.com → kuma8088.com

**方針**: サイト2-4と同じ手順（ただしサブディレクトリリダイレクトは既に設定済み）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Cloudflare Tunnel Public Hostname: kuma8088.com を追加

# Nginx設定
cp config/nginx/conf.d/kuma8088.conf config/nginx/conf.d/kuma8088.conf.pre-migration
sed -i 's/server_name blog\.kuma8088\.com;/server_name kuma8088.com www.kuma8088.com;/' \
  config/nginx/conf.d/kuma8088.conf

# 旧ドメインリダイレクト用serverブロックを追加（サブディレクトリリダイレクトの後に）
cat >> config/nginx/conf.d/kuma8088.conf <<'EOF'

# Redirect old domain to production domain
server {
    listen 80;
    server_name blog.kuma8088.com;
    return 301 https://kuma8088.com$request_uri;
}
EOF

docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# WordPress URL置換（dry-run→actual、HTTPS→HTTP順）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com' 'https://kuma8088.com' \
  --path=/var/www/html/kuma8088 --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com' 'https://kuma8088.com' \
  --path=/var/www/html/kuma8088 --all-tables --skip-columns=guid --dry-run --allow-root

docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com' 'https://kuma8088.com' \
  --path=/var/www/html/kuma8088 --all-tables --skip-columns=guid --allow-root

docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com' 'https://kuma8088.com' \
  --path=/var/www/html/kuma8088 --all-tables --skip-columns=guid --allow-root

# DB確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value FROM wp_kuma8088.wp_options WHERE option_name IN ('siteurl', 'home');"

# キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css --path=/var/www/html/kuma8088 --allow-root
docker compose exec wordpress wp cache flush --path=/var/www/html/kuma8088 --allow-root

# 動作確認
curl -I https://kuma8088.com
curl -I https://blog.kuma8088.com  # 301確認（ルート）
curl -I https://blog.kuma8088.com/elementordemo1  # 301確認（サブディレクトリ）
```

---

### Phase 3: サブドメイン化移行（9サイト）

#### サイト6: blog.fx-trader-life.com/MFKC → mfkc.fx-trader-life.com

##### 3.1 Cloudflare Tunnel Public Hostname追加

```
Zero Trust Dashboard:
1. Networks → Tunnels → blog-tunnel → Configure
2. Public Hostnames → Add a public hostname

設定:
- Subdomain: mfkc
- Domain: fx-trader-life.com
- Path: (空欄)
- Service: HTTP
- URL: nginx:80

3. Save hostname
```

##### 3.2 Nginx新規仮想ホスト作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

cat > config/nginx/conf.d/mfkc-fx-trader-life.conf <<'EOF'
# Virtual host: mfkc.fx-trader-life.com
# Production subdomain for MFKC
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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

##### 3.3 WordPress URL置換

```bash
# 1. HTTPS版のdry-run（メイン: siteurl/home等を含む）
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com/MFKC' \
  'https://mfkc.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-mfkc \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 2. HTTP版のdry-run（念のため: post_content内ハードコードURL用）
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com/MFKC' \
  'https://mfkc.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-mfkc \
  --all-tables \
  --skip-columns=guid \
  --dry-run \
  --allow-root

# 出力を確認: 両方の "X replacements" の数を記録

# 3. HTTPS版の本実行
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com/MFKC' \
  'https://mfkc.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-mfkc \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 4. HTTP版の本実行
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com/MFKC' \
  'https://mfkc.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-mfkc \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# 5. データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_fx_trader_life_mfkc.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# 期待値: https://mfkc.fx-trader-life.com
```

##### 3.4 キャッシュクリア

```bash
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life-mfkc \
  --allow-root

docker compose exec wordpress wp cache flush \
  --path=/var/www/html/fx-trader-life-mfkc \
  --allow-root
```

##### 3.5 動作確認

```bash
curl -I https://mfkc.fx-trader-life.com
# ブラウザで https://mfkc.fx-trader-life.com にアクセス
```

##### 3.6 旧URL → 新URL 301リダイレクト設定

`fx-trader-life.com` 系サブサイトは `blog.fx-trader-life.com/<subdir>` と
`fx-trader-life.com/<subdir>` のどちらからもアクセスされていたため、
**両方の server{} ブロック**にリダイレクト用 `location` を追加する。
以下のヘルパーは `SUBDIR`（旧サブディレクトリ）と `TARGET_HOST`
（新サブドメイン）を差し替えて再利用できる。

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

SUBDIR=MFKC
TARGET_HOST=mfkc.fx-trader-life.com

python - <<'PY'
import os, pathlib

slug = os.environ["SUBDIR"].strip("/")
target = os.environ["TARGET_HOST"]
path = pathlib.Path("config/nginx/conf.d/fx-trader-life.conf")
text = path.read_text()

root_marker = "    # Root domain site"
root_snippet = f"""    # Redirect /{slug} to https://{target} (root domain fallback)
    location /{slug} {{
        return 301 https://{target}$request_uri;
    }}
    location /{slug}/ {{
        return 301 https://{target}$request_uri;
    }}

"""

blog_marker = "    return 301 https://fx-trader-life.com$request_uri;"
blog_snippet = f"""    # Redirect /{slug} to https://{target} (blog.* fallback)
    location /{slug} {{
        return 301 https://{target}$request_uri;
    }}
    location /{slug}/ {{
        return 301 https://{target}$request_uri;
    }}

"""

if f"/{slug}" not in text:
    text = text.replace(root_marker, root_snippet + root_marker, 1)

if blog_snippet not in text:
    text = text.replace(blog_marker, blog_snippet + blog_marker, 1)

path.write_text(text)
PY

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

curl -I https://blog.fx-trader-life.com/${SUBDIR}    # 旧ドメイン
curl -I https://fx-trader-life.com/${SUBDIR}         # 本番ドメイン
# 期待値: Location: https://${TARGET_HOST}/${SUBDIR}
```

> SUBDIR/TARGET_HOST を `4-line-trade` / `4line.fx-trader-life.com`,
> `lp` / `lp.fx-trader-life.com` に入れ替えて同じヘルパーを実行すれば、
> 4line・lp サイト分のリダイレクトも一括で追加できる。

---

#### サイト7-15: 同様の手順を繰り返し

**以下のサイトで3.1〜3.6を実施**:

**サイト7: blog.fx-trader-life.com/4-line-trade → 4line.fx-trader-life.com**
```bash
# 3.1 Cloudflare Tunnel: 4line.fx-trader-life.com

# 3.2 Nginx: config/nginx/conf.d/4line-fx-trader-life.conf 作成
cat > config/nginx/conf.d/4line-fx-trader-life.conf <<'EOF'
# Virtual host: 4line.fx-trader-life.com
# Production subdomain for 4-line-trade
server {
    listen 80;
    server_name 4line.fx-trader-life.com;

    root /var/www/html/fx-trader-life-4line;
    index index.php index.html;

    access_log /var/log/nginx/4line-fx-trader-life-access.log;
    error_log /var/log/nginx/4line-fx-trader-life-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com/4-line-trade' \
  'https://4line.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-4line \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com/4-line-trade' \
  'https://4line.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-4line \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_fx_trader_life_4line.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life-4line \
  --allow-root

# 3.5 動作確認
curl -I https://4line.fx-trader-life.com

# 3.6 旧URL → 新URL 301リダイレクト
# SUBDIR=4-line-trade / TARGET_HOST=4line.fx-trader-life.com を指定して
# 3.6 の Python ヘルパーを再実行し、blog.* と fx-trader-life.com の両方に
# location ブロックを追加 → nginx -t → nginx -s reload → 両URLで curl -I を実施
```

**サイト8: blog.fx-trader-life.com/lp → lp.fx-trader-life.com**
```bash
# 3.1 Cloudflare Tunnel: lp.fx-trader-life.com

# 3.2 Nginx: config/nginx/conf.d/lp-fx-trader-life.conf 作成
cat > config/nginx/conf.d/lp-fx-trader-life.conf <<'EOF'
# Virtual host: lp.fx-trader-life.com
# Production subdomain for LP site
server {
    listen 80;
    server_name lp.fx-trader-life.com;

    root /var/www/html/fx-trader-life-lp;
    index index.php index.html;

    access_log /var/log/nginx/lp-fx-trader-life-access.log;
    error_log /var/log/nginx/lp-fx-trader-life-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.fx-trader-life.com/lp' \
  'https://lp.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-lp \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.fx-trader-life.com/lp' \
  'https://lp.fx-trader-life.com' \
  --path=/var/www/html/fx-trader-life-lp \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_fx_trader_life_lp.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/fx-trader-life-lp \
  --allow-root

# 3.5 動作確認
curl -I https://lp.fx-trader-life.com

# 3.6 旧URL → 新URL 301リダイレクト
# SUBDIR=lp / TARGET_HOST=lp.fx-trader-life.com で 3.6 の Python ヘルパーを再実行し、
# blog.* および fx-trader-life.com server{} に location を追加 → nginx再読み込み →
# https://blog.fx-trader-life.com/lp と https://fx-trader-life.com/lp の両方で 301 を確認
```

**サイト9: blog.webmakeprofit.org/coconala → coconala.webmakeprofit.org**
```bash
# 3.1 Cloudflare Tunnel: coconala.webmakeprofit.org

# 3.2 Nginx: config/nginx/conf.d/coconala-webmakeprofit.conf 作成
cat > config/nginx/conf.d/coconala-webmakeprofit.conf <<'EOF'
# Virtual host: coconala.webmakeprofit.org
server {
    listen 80;
    server_name coconala.webmakeprofit.org;

    root /var/www/html/webmakeprofit-coconala;
    index index.php index.html;

    access_log /var/log/nginx/coconala-webmakeprofit-access.log;
    error_log /var/log/nginx/coconala-webmakeprofit-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.webmakeprofit.org/coconala' \
  'https://coconala.webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit-coconala \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.webmakeprofit.org/coconala' \
  'https://coconala.webmakeprofit.org' \
  --path=/var/www/html/webmakeprofit-coconala \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_webmakeprofit_coconala.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/webmakeprofit-coconala \
  --allow-root

# 3.5 動作確認
curl -I https://coconala.webmakeprofit.org
```

**サイト10: blog.kuma8088.com/cameramanual → camera.kuma8088.com**
```bash
# 3.1 Cloudflare Tunnel: camera.kuma8088.com

# 3.2 Nginx: config/nginx/conf.d/camera-kuma8088.conf 作成
cat > config/nginx/conf.d/camera-kuma8088.conf <<'EOF'
# Virtual host: camera.kuma8088.com
server {
    listen 80;
    server_name camera.kuma8088.com;

    root /var/www/html/kuma8088-cameramanual;
    index index.php index.html;

    access_log /var/log/nginx/camera-kuma8088-access.log;
    error_log /var/log/nginx/camera-kuma8088-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/cameramanual' \
  'https://camera.kuma8088.com' \
  --path=/var/www/html/kuma8088-cameramanual \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/cameramanual' \
  'https://camera.kuma8088.com' \
  --path=/var/www/html/kuma8088-cameramanual \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_cameramanual.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-cameramanual \
  --allow-root

# 3.5 動作確認
curl -I https://camera.kuma8088.com
```

**サイト11: blog.kuma8088.com/elementordemo1 → demo1.kuma8088.com**
```bash
# Phase 1で完了済み
```

**サイト12: blog.kuma8088.com/elementordemo02 → demo2.kuma8088.com**
```bash
# 3.1 Cloudflare Tunnel: demo2.kuma8088.com

# 3.2 Nginx: config/nginx/conf.d/demo2-kuma8088.conf 作成
cat > config/nginx/conf.d/demo2-kuma8088.conf <<'EOF'
# Virtual host: demo2.kuma8088.com
server {
    listen 80;
    server_name demo2.kuma8088.com;

    root /var/www/html/kuma8088-elementordemo02;
    index index.php index.html;

    access_log /var/log/nginx/demo2-kuma8088-access.log;
    error_log /var/log/nginx/demo2-kuma8088-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementordemo02' \
  'https://demo2.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo02 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementordemo02' \
  'https://demo2.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementordemo02 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_elementordemo02.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-elementordemo02 \
  --allow-root

# 3.5 動作確認
curl -I https://demo2.kuma8088.com
```

**サイト13: blog.kuma8088.com/elementor-demo-03 → demo3.kuma8088.com**
```bash
# 3.1 Cloudflare Tunnel: demo3.kuma8088.com

# 3.2 Nginx: config/nginx/conf.d/demo3-kuma8088.conf 作成
cat > config/nginx/conf.d/demo3-kuma8088.conf <<'EOF'
# Virtual host: demo3.kuma8088.com
server {
    listen 80;
    server_name demo3.kuma8088.com;

    root /var/www/html/kuma8088-elementor-demo-03;
    index index.php index.html;

    access_log /var/log/nginx/demo3-kuma8088-access.log;
    error_log /var/log/nginx/demo3-kuma8088-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementor-demo-03' \
  'https://demo3.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementor-demo-03 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementor-demo-03' \
  'https://demo3.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementor-demo-03 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_elementor_demo_03.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-elementor-demo-03 \
  --allow-root

# 3.5 動作確認
curl -I https://demo3.kuma8088.com
```

**サイト14: blog.kuma8088.com/elementor-demo-04 → demo4.kuma8088.com**
```bash
# 3.1 Cloudflare Tunnel: demo4.kuma8088.com

# 3.2 Nginx: config/nginx/conf.d/demo4-kuma8088.conf 作成
cat > config/nginx/conf.d/demo4-kuma8088.conf <<'EOF'
# Virtual host: demo4.kuma8088.com
server {
    listen 80;
    server_name demo4.kuma8088.com;

    root /var/www/html/kuma8088-elementor-demo-04;
    index index.php index.html;

    access_log /var/log/nginx/demo4-kuma8088-access.log;
    error_log /var/log/nginx/demo4-kuma8088-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/elementor-demo-04' \
  'https://demo4.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementor-demo-04 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/elementor-demo-04' \
  'https://demo4.kuma8088.com' \
  --path=/var/www/html/kuma8088-elementor-demo-04 \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_elementor_demo_04.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-elementor-demo-04 \
  --allow-root

# 3.5 動作確認
curl -I https://demo4.kuma8088.com
```

**サイト15: blog.kuma8088.com/ec02test → ec-test.kuma8088.com**
```bash
# 3.1 Cloudflare Tunnel: ec-test.kuma8088.com

# 3.2 Nginx: config/nginx/conf.d/ec-test-kuma8088.conf 作成
cat > config/nginx/conf.d/ec-test-kuma8088.conf <<'EOF'
# Virtual host: ec-test.kuma8088.com
server {
    listen 80;
    server_name ec-test.kuma8088.com;

    root /var/www/html/kuma8088-ec02test;
    index index.php index.html;

    access_log /var/log/nginx/ec-test-kuma8088-access.log;
    error_log /var/log/nginx/ec-test-kuma8088-error.log;

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

docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 3.3 WordPress URL置換（HTTPS→HTTP順）
# HTTPS版（メイン）
docker compose exec wordpress wp search-replace \
  'https://blog.kuma8088.com/ec02test' \
  'https://ec-test.kuma8088.com' \
  --path=/var/www/html/kuma8088-ec02test \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# HTTP版（念のため）
docker compose exec wordpress wp search-replace \
  'http://blog.kuma8088.com/ec02test' \
  'https://ec-test.kuma8088.com' \
  --path=/var/www/html/kuma8088-ec02test \
  --all-tables \
  --skip-columns=guid \
  --allow-root

# データベース直接確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_value
  FROM wp_kuma8088_ec02test.wp_options
  WHERE option_name IN ('siteurl', 'home');
"

# 3.4 キャッシュクリア
# Elementor導入サイトのみ（未導入ならスキップ）
docker compose exec wordpress wp elementor flush-css \
  --path=/var/www/html/kuma8088-ec02test \
  --allow-root

# 3.5 動作確認
curl -I https://ec-test.kuma8088.com
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

# 例: fx-trader-life.com のロールバック

# 1. Nginx設定を旧構成に戻す
cp config/nginx/conf.d/fx-trader-life.conf.pre-migration config/nginx/conf.d/fx-trader-life.conf
docker compose exec nginx nginx -t
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

**所要時間**: 10-15分で復旧可能

---

## ✅ チェックリスト

### 事前準備（D-1日）

- [ ] I009完了確認（全サイト動作確認・ライセンス確認）
- [ ] DNS TTL短縮実施（3600秒 → 300秒）
- [ ] 完全バックアップ取得
  - [ ] データベース（全15サイト）
  - [ ] WordPressファイル（95GB）
  - [ ] Nginx設定
  - [ ] Cloudflare Tunnel設定スクリーンショット

### Phase 1: テスト移行（demo1.kuma8088.com）

- [ ] Cloudflare Tunnel Public Hostname追加
- [ ] Nginx設定ファイル作成（demo1-kuma8088.conf）
- [ ] WordPress URL置換（dry-run → 本実行）
- [ ] キャッシュクリア
- [ ] 動作確認
  - [ ] トップページ表示
  - [ ] 画像表示
  - [ ] 静的ファイル読み込み
  - [ ] Elementorエディタ動作
  - [ ] リンク動作
- [ ] 301リダイレクト設定
  - [ ] blog.kuma8088.com/elementordemo1 → demo1.kuma8088.com
  - [ ] リダイレクトループなし確認
- [ ] 問題なければPhase 2へ進行判断

### Phase 2: ルートサイト移行（5サイト）

**各サイトごとに実施**:

#### fx-trader-life.com
- [ ] Cloudflare Tunnel Public Hostname追加
- [ ] Nginx設定変更（server_name変更）
- [ ] WordPress URL置換（dry-run → 本実行）
- [ ] キャッシュクリア
- [ ] 動作確認
- [ ] 301リダイレクト設定（fx-trader-life.conf の blog.* server で確認）
- [ ] 24時間安定動作確認

#### webmakeprofit.org
- [ ] （同上）

#### webmakesprofit.com
- [ ] （同上）

#### toyota-phv.jp
- [ ] （同上）

#### kuma8088.com
- [ ] （同上）

### Phase 3: サブドメイン化移行（9サイト）

**各サイトごとに実施**:

#### mfkc.fx-trader-life.com
- [ ] Cloudflare Tunnel Public Hostname追加
- [ ] Nginx新規仮想ホスト作成（mfkc-fx-trader-life.conf）
- [ ] WordPress URL置換（dry-run → 本実行）
- [ ] キャッシュクリア
- [ ] 動作確認
- [ ] 301リダイレクト設定
  - [ ] blog.fx-trader-life.com/MFKC → mfkc.fx-trader-life.com
  - [ ] fx-trader-life.com/MFKC → mfkc.fx-trader-life.com

#### 4line.fx-trader-life.com
- [ ] （同上）

#### lp.fx-trader-life.com
- [ ] （同上）

#### coconala.webmakeprofit.org
- [ ] （同上）

#### camera.kuma8088.com
- [ ] （同上）

#### demo2.kuma8088.com
- [ ] （同上）

#### demo3.kuma8088.com
- [ ] （同上）

#### demo4.kuma8088.com
- [ ] （同上）

#### ec-test.kuma8088.com
- [ ] （同上）

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

# server_name確認
docker compose exec nginx grep -r "server_name" /etc/nginx/conf.d/
```

### 問題2: 画像が表示されない

**原因**: URL置換漏れ、またはパーミッション問題

```bash
# データベース内URL確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
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
# Elementor導入サイトのみ（未導入ならスキップ）
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
# Nginx設定確認（重複チェック）
docker compose exec nginx grep -r "return 301" /etc/nginx/conf.d/ | grep fx-trader-life

# WordPress URL確認
docker compose exec mariadb mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
  SELECT option_name, option_value
  FROM wp_fx_trader_life.wp_options
  WHERE option_name IN ('siteurl', 'home');
"
# siteurl と home が一致していることを確認
```

### 問題5: 301リダイレクトが動作しない

**原因**: locationブロックの順序、またはCloudflare Tunnel設定ミス

```bash
# Nginx設定確認（locationブロックの順序）
docker compose exec nginx sed -n '1,200p' /etc/nginx/conf.d/fx-trader-life.conf | grep -n "Redirect /"

# 注意: location /<subdir> は本番serverの location / より前、
# blog.* server では return 301 の前に配置されていること

# Cloudflare Tunnel確認
# Zero Trust Dashboard → Networks → Tunnels → blog-tunnel
# → Public Hostnames を確認

# リダイレクトテスト（詳細）
curl -v https://blog.fx-trader-life.com/MFKC 2>&1 | grep -i location
```

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

### Nginx公式ドキュメント

- [ngx_http_rewrite_module](https://nginx.org/en/docs/http/ngx_http_rewrite_module.html)
- [Creating NGINX Rewrite Rules](https://www.nginx.com/blog/creating-nginx-rewrite-rules/)

### Cloudflare公式ドキュメント

- [Cloudflare Tunnel Public Hostnames](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/routing-to-tunnel/dns/)

---

## 📋 移行作業スケジュール例

### 3日間スケジュール（推奨）

#### Day 1（土曜日 AM 2:00 - PM 12:00）

- **AM 2:00 - 3:00**: Phase 0 事前準備（DNS TTL短縮、バックアップ）
- **AM 3:00 - 5:00**: Phase 1 テスト移行（demo1.kuma8088.com）
- **AM 5:00 - 6:00**: Phase 1 評価、問題なければPhase 2へ進行判断
- **AM 6:00 - 11:00**: Phase 2 ルートサイト移行（5サイト）
- **AM 11:00 - PM 12:00**: Phase 2 動作確認、エラーログ確認

#### Day 2（日曜日 AM 2:00 - PM 1:00）

- **AM 2:00 - 3:00**: Phase 2 最終確認（24時間経過後のエラーログ）
- **AM 3:00 - 8:00**: Phase 3 サブドメイン化移行（優先度Medium: 4サイト）
- **AM 8:00 - PM 1:00**: Phase 3 サブドメイン化移行（優先度Low: 5サイト）

#### Day 3-7（月曜 - 金曜）

- **毎日AM 9:00**: エラーログ確認、アクセスログ確認
- **金曜PM 17:00**: 1週間の安定動作確認完了

---

## 次のステップ

1. **I009実施**: 全サイトの動作確認・ライセンス確認（1-2日）
2. **移行計画承認**: ユーザーと最終確認
3. **Phase 0実行**: 事前準備（DNS TTL短縮、バックアップ）
4. **Phase 1実行**: テスト移行（demo1.kuma8088.com検証）
5. **Phase 2-3実行**: 段階的本番移行
6. **WP Mail SMTP設定**: 全Phase完了後に実行

---

## Phase完了後: WP Mail SMTP設定

### 目的
全15サイトにWP Mail SMTPプラグインを設定し、ドメイン別送信元メールアドレスでPostfix経由メール送信を有効化。

### 実行タイミング
**Phase 1, 2, 3すべて完了後**（本番ドメイン移行が完了していること）

### 実行手順

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 1. 設定状況確認
./scripts/check-wp-mail-smtp.sh

# 2. 全サイト一括設定
./scripts/setup-wp-mail-smtp.sh

# 3. 設定確認
./scripts/check-wp-mail-smtp.sh

# 4. テストメール送信（任意）
./scripts/setup-wp-mail-smtp.sh --test-email your-email@example.com
```

### 設定内容
- **SMTP設定**: dell-workstation.tail67811d.ts.net:587 (TLS)
- **送信元メールアドレス**: ドメイン別自動設定
  - fx-trader-life系 → noreply@fx-trader-life.com
  - kuma8088系 → noreply@kuma8088.com
  - toyota-phv → noreply@toyota-phv.com
  - webmakeprofit系 → noreply@webmakeprofit.com
  - webmakesprofit → noreply@webmakesprofit.com

### 詳細情報
- スクリプト詳細: [services/blog/scripts/setup-wp-mail-smtp.sh](../../../../services/blog/scripts/setup-wp-mail-smtp.sh)
- セットアップガイド: [docs/application/blog/guides/WP-MAIL-SMTP-SETUP.md](../guides/WP-MAIL-SMTP-SETUP.md)

---

**作成日**: 2025-11-11
**バージョン**: 2.0（全サブドメイン化対応）
**作成者**: Claude
**ステータス**: Draft（実施前）
**重要**: 本手順書は全サイトをサブドメイン化する前提で作成されています。301リダイレクト設定により、既存URLでアクセスするユーザーも新URLへ自動転送されます。
