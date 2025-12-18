# ブログシステムデプロイメント戦略

**技術スタック**: Docker Compose, Nginx, WordPress, Cloudflare Tunnel

---

## 1. デプロイメント方針

### 1.1 Infrastructure as Code（IaC）

| レイヤー | ツール | 管理対象 |
|---------|-------|---------|
| コンテナ定義 | Docker Compose | 5サービスコンテナ |
| 設定管理 | Git + 環境変数 | 設定ファイル、.env |
| エッジサービス | Cloudflare Dashboard | Tunnel, DNS |
| 自動化 | Shell Scripts | 新規サイト作成、設定更新 |

**原則**:
- すべての設定変更はGitでバージョン管理
- 手動変更は禁止（緊急時を除く）
- 変更は必ずテスト後に適用

### 1.2 ディレクトリ構成

```
services/blog/
├── docker-compose.yml      # コンテナ定義
├── .env                    # 環境変数（Git管理外）
├── .env.example            # 環境変数テンプレート
├── config/                 # 設定ファイル
│   ├── nginx/
│   │   └── conf.d/         # 仮想ホスト設定
│   ├── mariadb/
│   │   └── init/           # DB初期化スクリプト
│   ├── wordpress/
│   │   └── php.ini         # PHP設定
│   └── cloudflared/
│       └── config.yml      # Tunnel設定
├── scripts/                # 運用スクリプト
│   ├── create-new-wp-site.sh
│   ├── setup-wp-mail-smtp.sh
│   ├── fix-permissions.sh
│   └── generate-nginx-subdirectories.sh
└── data/                   # 永続データ（Git管理外）
    ├── wordpress/          # wp-content
    ├── mysql/              # MariaDBデータ
    └── redis/              # Redisデータ
```

---

## 2. Docker Compose 戦略

### 2.1 サービス構成（5コンテナ）

| サービス | イメージ | 役割 | リソース制限 |
|---------|---------|------|-------------|
| nginx | nginx:alpine | リバースプロキシ | CPU: 0.5, MEM: 256M |
| wordpress | wordpress:php8.2-fpm-alpine | PHP-FPM | CPU: 2.0, MEM: 2G |
| mariadb | mariadb:10.11 | データベース | CPU: 1.0, MEM: 1G |
| cloudflared | cloudflare/cloudflared | Tunnel | CPU: 0.5, MEM: 128M |
| redis | redis:alpine | キャッシュ | CPU: 0.5, MEM: 512M |

### 2.2 ボリューム戦略

```yaml
volumes:
  # パフォーマンス重視: SSD
  db_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/ssd/mariadb

  # 容量重視: HDD
  wp_content:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/backup-hdd/blog/wordpress
```

**設計意図**:
- **SSD**: データベース、Redisキャッシュ（頻繁なI/O）
- **HDD**: メディアファイル、バックアップ（大容量）

### 2.3 ネットワーク戦略

```yaml
networks:
  blog_network:
    driver: bridge
```

**設計意図**:
- 他サービスとのネットワーク分離
- コンテナ間通信の制御

### 2.4 ヘルスチェック設計

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

| サービス | チェック方法 |
|---------|------------|
| Nginx | HTTP応答確認 |
| WordPress | PHP-FPM ping |
| MariaDB | `mysqladmin ping` |
| Redis | `redis-cli ping` |
| cloudflared | プロセス確認 |

---

## 3. デプロイメントワークフロー

### 3.1 初期デプロイ

```bash
# 1. 環境変数設定
cp .env.example .env
# .env を編集（DB パスワード等）

# 2. ディレクトリ準備
mkdir -p /path/to/ssd/mariadb
mkdir -p /mnt/backup-hdd/blog/{wordpress,daily,weekly}

# 3. 設定ファイル確認
docker compose config

# 4. イメージ取得・起動
docker compose pull
docker compose up -d

# 5. 起動確認
docker compose ps
docker compose logs --tail=50
```

### 3.2 通常デプロイ（更新）

```bash
# 1. 変更確認
git pull origin main
docker compose config  # 設定検証

# 2. イメージ更新
docker compose pull

# 3. ローリングアップデート
docker compose up -d --remove-orphans

# 4. ヘルスチェック
docker compose ps
docker compose logs --tail=50
```

### 3.3 設定変更デプロイ

```bash
# Nginx設定変更の場合
vim config/nginx/conf.d/main-site.conf

# 設定検証
docker compose exec nginx nginx -t

# 設定リロード（再起動不要）
docker compose exec nginx nginx -s reload

# 動作確認
curl -I https://blog.example.com/
```

### 3.4 デプロイ前チェックリスト

```
□ 設定ファイルの構文チェック（docker compose config）
□ 環境変数の確認（.env の必須項目）
□ ディスク空き容量の確認
□ 現在のサービス状態の記録（docker compose ps）
□ バックアップの確認（直近のバックアップが成功しているか）
□ ロールバック手順の確認
```

---

## 4. 新規サイト作成手順

### 4.1 自動化スクリプト（推奨）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 対話式ウィザード起動
./scripts/create-new-wp-site.sh
```

**自動処理内容**:
1. データベース作成（MariaDB）
2. WordPressファイルコピー
3. wp-config.php生成
4. パーミッション設定
5. Nginx設定ファイル生成案

### 4.2 手動手順（詳細理解用）

```bash
# 1. データベース作成
docker compose exec mariadb mysql -u root -p \
  -e "CREATE DATABASE blog_newsite CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. WordPressディレクトリ作成
docker compose exec wordpress bash -c "
  mkdir -p /var/www/html/newsite
  cp -r /usr/src/wordpress/* /var/www/html/newsite/
"

# 3. wp-config.php作成
# テンプレートから生成し、DB名・プレフィックスを設定

# 4. パーミッション修正
./scripts/fix-permissions.sh

# 5. Nginx設定追加
vim config/nginx/conf.d/newsite.conf

# 6. Nginx設定リロード
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload

# 7. Cloudflare Tunnel設定更新（必要に応じて）
vim config/cloudflared/config.yml
docker compose restart cloudflared
```

### 4.3 Nginx設定テンプレート

**サブディレクトリサイト**:
```nginx
location /newsite {
    alias /var/www/html/newsite;
    index index.php;
    try_files $uri $uri/ /newsite/index.php?$args;

    location ~ \.php$ {
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $request_filename;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
        include fastcgi_params;
    }
}
```

**独立ドメインサイト**:
```nginx
server {
    listen 80;
    server_name newsite.example.com;
    root /var/www/html/newsite;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
        include fastcgi_params;
    }
}
```

---

## 5. イメージ管理

### 5.1 バージョン固定

```yaml
# Good: バージョン固定
image: mariadb:10.11
image: nginx:1.26-alpine
image: wordpress:php8.2-fpm-alpine

# Bad: latest（本番では避ける）
image: wordpress:latest
```

**理由**:
- 再現性確保
- 予期しないアップデート防止
- ロールバック容易化

### 5.2 イメージ更新ポリシー

| カテゴリ | 更新頻度 | 手順 |
|---------|---------|------|
| セキュリティパッチ | 即時 | docker compose pull → up |
| マイナーバージョン | 月次 | テスト環境検証後 |
| メジャーバージョン | 慎重に | 互換性確認後 |

---

## 6. 秘密情報管理

### 6.1 環境変数

```bash
# .env（本番）- Git管理外
MYSQL_ROOT_PASSWORD=<secure-password>
MYSQL_DATABASE=blog_main
MYSQL_USER=wordpress
MYSQL_PASSWORD=<secure-password>
WORDPRESS_DB_PASSWORD=<secure-password>
SENDGRID_API_KEY=<api-key>
```

### 6.2 .gitignore

```
.env
.env.*
!.env.example
config/cloudflared/credentials.json
data/
*.log
```

### 6.3 シークレットローテーション

| シークレット | ローテーション頻度 | 方法 |
|-------------|------------------|------|
| DBパスワード | 90日 | 手動更新、wp-config.php同時更新 |
| SendGrid APIキー | 365日 | SendGrid管理画面で再生成 |
| Cloudflare Tunnel | 必要時 | cloudflared tunnel token |

---

## 7. ロールバック戦略

### 7.1 Dockerロールバック

```bash
# 直前のイメージに戻す
docker compose down
git checkout HEAD~1 -- docker-compose.yml
docker compose up -d

# 特定バージョンに戻す
docker compose down
# docker-compose.yml のイメージタグを変更
docker compose up -d
```

### 7.2 設定ロールバック

```bash
# Git から復元
git checkout HEAD~1 -- config/nginx/conf.d/main-site.conf
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

### 7.3 データロールバック

```bash
# バックアップからリストア
# 1. サービス停止
docker compose stop wordpress

# 2. データベースリストア
docker compose exec -T mariadb mysql -u root -p < backup.sql

# 3. ファイルリストア
rsync -av /mnt/backup-hdd/blog/daily/YYYY-MM-DD/wordpress/ data/wordpress/

# 4. サービス再開
docker compose start wordpress
```

---

## 8. Cloudflare Tunnel設定

### 8.1 Tunnel作成

```bash
# Cloudflare認証
cloudflared tunnel login

# Tunnel作成
cloudflared tunnel create blog-tunnel

# 認証情報を配置
mv ~/.cloudflared/<tunnel-id>.json config/cloudflared/credentials.json
```

### 8.2 config.yml

```yaml
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # メインサイト
  - hostname: blog.example.com
    service: http://nginx:80
    originRequest:
      noTLSVerify: true

  # 追加ドメイン
  - hostname: site-b.example.net
    service: http://nginx:80
  - hostname: site-c.example.jp
    service: http://nginx:80
  - hostname: site-d.example.com
    service: http://nginx:80
  - hostname: elementor-demo.example.com
    service: http://nginx:80

  # フォールバック
  - service: http_status:404
```

### 8.3 DNS設定（Cloudflare）

| タイプ | 名前 | 内容 | プロキシ |
|--------|------|------|---------|
| CNAME | blog | <tunnel-id>.cfargotunnel.com | ✅ |
| CNAME | @ (cameramanual.net) | <tunnel-id>.cfargotunnel.com | ✅ |
| CNAME | @ (wpbook.jp) | <tunnel-id>.cfargotunnel.com | ✅ |

---

## 9. WP Mail SMTP設定

### 9.1 一括設定スクリプト

```bash
# 全サイト一括設定
./scripts/setup-wp-mail-smtp.sh

# プレビュー（実行せず確認のみ）
./scripts/setup-wp-mail-smtp.sh --dry-run

# 単一サイト指定
./scripts/setup-wp-mail-smtp.sh --site sitename blog.example.com noreply@example.com

# テストメール送信
./scripts/setup-wp-mail-smtp.sh --test-email your@email.com
```

### 9.2 設定内容

```php
// wp-config.php または options
define('WPMS_ON', true);
define('WPMS_MAILER', 'sendgrid');
define('WPMS_SENDGRID_API_KEY', getenv('SENDGRID_API_KEY'));
define('WPMS_MAIL_FROM', 'noreply@domain.com');
define('WPMS_MAIL_FROM_NAME', 'Site Name');
```

---

## 10. 継続的改善

### 10.1 イメージ更新チェック

```bash
# 月次: セキュリティアップデート確認
docker compose pull
docker images --format "{{.Repository}}:{{.Tag}} {{.CreatedSince}}"

# 変更があれば再起動
docker compose up -d
```

### 10.2 依存関係監査

- **Docker**: ベースイメージの脆弱性スキャン
- **WordPress**: コア・プラグイン・テーマの更新確認
- **PHP**: バージョン互換性確認

---

## 11. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [operations.md](operations.md) | 運用設計・監視・バックアップ運用 |
