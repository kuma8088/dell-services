# ブログシステムアーキテクチャ設計

**技術スタック**: Docker Compose, WordPress, Nginx, MariaDB, Redis, Cloudflare Tunnel

---

## 1. システム概要

### 1.1 アーキテクチャ方針

| 方針 | 内容 |
|------|------|
| コンテナ化 | Docker Composeによる一元管理 |
| 独立性 | 複数独立WordPress（マルチサイト不使用） |
| ゼロトラスト | Cloudflare Tunnel経由、ポート開放不要 |
| 高速化 | Redis Object Cache、OPcache |

### 1.2 全体構成図

```
                    Internet
                        │
                        ▼
              ┌─────────────────┐
              │   Cloudflare    │
              │   (DNS/CDN/WAF) │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ Cloudflare Edge │
              │   (SSL終端)     │
              └────────┬────────┘
                       │ HTTPS
                       ▼
              ┌─────────────────┐
              │ Cloudflare      │
              │ Tunnel (cloudflared)│
              └────────┬────────┘
                       │ HTTP
        ┌──────────────┴──────────────┐
        │     Docker Network          │
        │     blog_network            │
        │  ┌─────────────────────┐    │
        │  │      Nginx          │    │
        │  │  (リバースプロキシ)  │    │
        │  └──────────┬──────────┘    │
        │             │               │
        │  ┌──────────▼──────────┐    │
        │  │    WordPress        │    │
        │  │  (PHP-FPM + Sites)  │    │
        │  └──────────┬──────────┘    │
        │        ┌────┴────┐          │
        │        ▼         ▼          │
        │  ┌──────────┐ ┌───────┐     │
        │  │ MariaDB  │ │ Redis │     │
        │  └──────────┘ └───────┘     │
        └─────────────────────────────┘
```

---

## 2. コンポーネント構成

### 2.1 コンテナ一覧

| コンテナ | イメージ | 役割 | ポート |
|---------|---------|------|--------|
| nginx | nginx:alpine | リバースプロキシ、静的ファイル配信 | 80 |
| wordpress | wordpress:php8.2-fpm-alpine | PHP-FPM、WordPress実行 | 9000 (FastCGI) |
| mariadb | mariadb:10.11 | データベース | 3306 |
| cloudflared | cloudflare/cloudflared | Cloudflare Tunnel | - |
| redis | redis:alpine | オブジェクトキャッシュ | 6379 |

### 2.2 ネットワーク設計

```yaml
networks:
  blog_network:
    driver: bridge
```

| コンテナ | 役割 |
|---------|------|
| nginx | リバースプロキシ |
| wordpress | アプリケーション |
| mariadb | データベース |
| cloudflared | トンネル |
| redis | キャッシュ |

---

## 3. Nginx設計

### 3.1 仮想ホスト構成

16サイトを5つの仮想ホスト設定ファイルで管理:

| ファイル | 対象サイト |
|---------|-----------|
| main-site.conf | blog.example.com（サブディレクトリ10サイト） |
| site-b.conf | site-b.example.net |
| elementor-demo.conf | elementor-demo.example.com |
| site-c.conf | site-c.example.com |
| site-d.conf | site-d.example.jp |

### 3.2 サブディレクトリ構成

```
blog.example.com/
├── /                    # メインサイト
├── /ec02test/           # テストサイト
├── /gallery-demo/       # ギャラリーデモ
├── /jstork-gallery/     # JSTORKギャラリー
├── /jstork-demo/        # JSTORKデモ
├── /new-standard/       # New Standardテーマ
├── /opencage/           # OpenCageデモ
├── /portfolio-demo/     # ポートフォリオデモ
├── /simplicity2-demo/   # Simplicity2デモ
└── /swell-demo/         # SWELLデモ
```

### 3.3 Nginx設定パターン

```nginx
# メインサイト
location / {
    try_files $uri $uri/ /index.php?$args;
}

# サブディレクトリサイト
location /subdirectory {
    alias /var/www/html/subdirectory;
    try_files $uri $uri/ /subdirectory/index.php?$args;

    location ~ \.php$ {
        fastcgi_pass wordpress:9000;
        fastcgi_param SCRIPT_FILENAME $request_filename;
        fastcgi_param HTTPS on;
        include fastcgi_params;
    }
}
```

---

## 4. WordPress設計

### 4.1 複数サイト構成

**採用**: 複数独立WordPress（Multisite不使用）

| 項目 | 独立構成（採用） | Multisite |
|------|----------------|-----------|
| プラグイン自由度 | ✅ サイト別 | ❌ ネットワーク共通 |
| 障害影響範囲 | ✅ 限定的 | ❌ 全サイト |
| バックアップ | ✅ 個別可能 | ❌ 一括のみ |
| リソース | ❌ 多め | ✅ 効率的 |

### 4.2 ディレクトリ構成

```
/var/www/html/
├── wp-config.php           # メインサイト設定
├── wp-content/
│   ├── plugins/            # 共通プラグイン
│   ├── themes/             # 共通テーマ
│   └── uploads/            # メインサイトメディア
├── subdirectory1/
│   ├── wp-config.php       # サブサイト1設定
│   └── wp-content/
├── subdirectory2/
│   ├── wp-config.php
│   └── wp-content/
└── ...
```

### 4.3 wp-config.php 重要設定

```php
// HTTPSプロキシ対応
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) &&
    $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
}

// Redis Object Cache
define('WP_REDIS_HOST', 'redis');
define('WP_REDIS_PORT', 6379);

// ファイル編集無効化
define('DISALLOW_FILE_EDIT', true);

// SSL強制
define('FORCE_SSL_ADMIN', true);
```

---

## 5. データベース設計

### 5.1 MariaDB構成

**1インスタンス・16データベース方式**:

```sql
-- データベース一覧
blog_main               -- メインサイト
blog_main_subsite1      -- サブディレクトリサイト
blog_main_subsite2      -- ...
blog_site_b             -- 独立ドメインサイト
blog_site_c             -- ...
```

### 5.2 テーブルプレフィックス

| サイト | プレフィックス |
|--------|--------------|
| メインサイト | wp_ |
| サブサイト | wp_ （DB分離で衝突回避） |

### 5.3 バックアップ戦略

```bash
# サイト別論理バックアップ
mysqldump -u root -p blog_main > main.sql
mysqldump -u root -p blog_site_b > site_b.sql
```

---

## 6. キャッシュ設計

### 6.1 キャッシュレイヤー

```
┌─────────────────────────────────────────┐
│ Layer 1: Cloudflare CDN                 │
│ - 静的ファイルキャッシュ                 │
│ - 画像最適化                            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Layer 2: Nginx                          │
│ - 静的ファイル配信                       │
│ - gzip圧縮                              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Layer 3: PHP OPcache                    │
│ - PHPバイトコードキャッシュ              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Layer 4: Redis Object Cache             │
│ - WordPressオブジェクトキャッシュ        │
│ - DB負荷軽減                            │
└─────────────────────────────────────────┘
```

### 6.2 Redis Object Cache設定

```php
// wp-config.php
define('WP_REDIS_HOST', 'redis');
define('WP_REDIS_PORT', 6379);
define('WP_REDIS_DATABASE', 0);
define('WP_REDIS_PREFIX', 'wp_sitename:'); // サイト別プレフィックス
```

---

## 7. セキュリティ設計

### 7.1 多層防御

```
Layer 1: Cloudflare
├── DDoS保護（L3/L4/L7）
├── WAF（OWASP Top 10）
├── Bot Management
└── SSL/TLS終端

Layer 2: Network
├── Cloudflare Tunnel（Inbound不要）
├── Docker Network分離
└── ポート開放なし

Layer 3: Application
├── WordPress Security Headers
├── ファイル編集無効化
└── WP Mail SMTP（SendGrid経由）

Layer 4: Data
├── HTTPS強制
├── DB内部ネットワーク限定
└── バックアップ暗号化
```

### 7.2 Cloudflare Tunnel

```yaml
# config.yml
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: blog.example.com
    service: http://nginx:80
  - hostname: site-b.example.net
    service: http://nginx:80
  - hostname: site-c.example.jp
    service: http://nginx:80
  # ... 他のドメイン
  - service: http_status:404
```

### 7.3 WordPress セキュリティ

| 項目 | 設定 |
|------|------|
| DISALLOW_FILE_EDIT | true（管理画面からのファイル編集禁止） |
| FORCE_SSL_ADMIN | true（管理画面HTTPS強制） |
| WP_DEBUG | false（本番環境） |
| wp-config.php | 440パーミッション |

---

## 8. メール送信設計

### 8.1 WP Mail SMTP構成

```
WordPress → WP Mail SMTP → SendGrid API → Internet
```

**設定内容**:
- Mailer: SendGrid
- From Email: noreply@domain.com
- From Name: サイト名
- API Key: SendGrid発行キー

### 8.2 16サイト一括設定

```bash
# 自動設定スクリプト
./scripts/setup-wp-mail-smtp.sh

# 設定確認
./scripts/check-wp-mail-smtp.sh
```

---

## 9. 通信フロー

### 9.1 Web閲覧フロー

```
User Browser
    │
    ▼ HTTPS
Cloudflare Edge (SSL終端、キャッシュ)
    │
    ▼ HTTP (Tunnel内)
cloudflared Container
    │
    ▼ HTTP
Nginx Container (Host振り分け、静的配信)
    │
    ▼ FastCGI
WordPress Container (PHP処理)
    │
    ├──▶ MariaDB (データ取得)
    └──▶ Redis (キャッシュ参照)
```

### 9.2 WordPress管理画面フロー

```
Admin Browser
    │
    ▼ HTTPS
Cloudflare Edge (WAF検査)
    │
    ▼ HTTP
cloudflared → Nginx → WordPress
    │
    ▼ 認証
WordPress (/wp-admin, /wp-login.php)
```

---

## 10. スケーラビリティ設計

### 10.1 現在の構成

| リソース | 現在 | 上限目安 |
|---------|------|---------|
| サイト数 | 16 | 20 |
| 記事総数 | - | 5,000 |
| メディア容量 | 95GB | 150GB |
| 月間PV | - | 50,000 |

### 10.2 将来の拡張パス

**水平スケール（サイト追加）**:
1. 新規データベース作成
2. wp-config.php設定
3. Nginx仮想ホスト追加
4. Cloudflare Tunnel設定更新

**垂直スケール（性能向上）**:
- PHP-FPMワーカー増加
- MariaDBバッファ調整
- Redis maxmemory調整

---

## 11. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・バックアップ・トラブルシューティング |
