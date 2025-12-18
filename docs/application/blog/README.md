# ブログシステム

Docker Compose環境で複数のWordPressサイトをホスティングするブログシステム

---

## ドキュメント構成

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システム設計・アーキテクチャ図 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・監視・バックアップ |

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **OS** | Rocky Linux 9.6 |
| **コンテナ** | Docker, Docker Compose |
| **Web** | Nginx 1.26, WordPress 6.4+, PHP-FPM 8.2 |
| **DB** | MariaDB 10.11 |
| **キャッシュ** | Redis 7 |
| **CDN/セキュリティ** | Cloudflare (Tunnel, CDN, WAF) |
| **メール送信** | WP Mail SMTP + SendGrid |

---

## プロジェクト概要

### 目的

**主目標**: 複数のWordPressサイトを自前インフラでホスティングし、コスト削減とデータ主権を実現

**技術目標**:
- ✅ Docker Compose環境構築
- ✅ Cloudflare Tunnel統合（動的IP対応）
- ✅ 既存インフラとの共存
- ✅ Redis Object Cache統合
- ✅ WP Mail SMTP一括設定

---

## システムアーキテクチャ

### コンテナ構成

```
blog_network (Docker Bridge)
├── wordpress (PHP-FPM 8.2 + wp-cli) - 17サイト
├── nginx (リバースプロキシ) - 17仮想ホスト
├── mariadb (10.11) - 17データベース
├── redis (Object Cache)
└── cloudflared (Cloudflare Tunnel)
```

### ネットワークフロー

```
[ユーザー] → [Cloudflare Edge] → [Tunnel] → [nginx:8080] → [WordPress]
              ↓                    ↓
           DDoS防御            アウトバウンド接続のみ
           SSL/TLS自動          （ポート開放不要）
           CDNキャッシュ
```

### ストレージ設計

| データ種別 | 格納先 | デバイス | 理由 |
|-----------|--------|----------|------|
| MariaDB | Dockerボリューム | SSD | 高速DB処理 |
| ログ | Dockerボリューム | SSD | 高速ログ書き込み |
| WordPressファイル | データボリューム | HDD | 大容量メディア格納 |
| バックアップ | バックアップボリューム | HDD | 長期保存 |

---

## 現在の稼働状況

### 本番稼働中

| コンテナ | 状態 | 稼働期間 |
|---------|------|----------|
| wordpress | ✅ Healthy | 5週間 |
| nginx | ✅ Healthy | 2週間 |
| mariadb | ✅ Healthy | 5週間 |
| redis | ✅ Healthy | 4週間 |
| cloudflared | ✅ Healthy | 2週間 |

### 完了済み作業

1. **Docker Compose環境**
   - 5コンテナ構成（nginx, wordpress, mariadb, redis, cloudflared）
   - 内部ポート設定済み
   - 分離されたネットワークブリッジ

2. **マルチサイトWordPress移行**
   - 17サイト分のデータベースインポート完了
   - 大容量ファイル転送完了（rsync、95GB）
   - 設定ファイル更新（wp-config.php）
   - URL一括置換完了

3. **Nginx設定**
   - 17仮想ホスト設定
   - ルートドメインとサブディレクトリサイト対応
   - Alias設定最適化

4. **Cloudflare Tunnel設定**
   - 公開ホスト名登録
   - HTTPS自動証明書プロビジョニング
   - DNS自動設定

5. **Redis Object Cache**
   - 全17サイトにRedis統合
   - WordPress高速化実現

6. **WP Mail SMTP**
   - 全17サイト一括設定完了
   - SendGrid経由のメール送信

---

## 解決済みの問題

### Elementorキャッシュ問題
- **症状**: ページで画像が表示されない（Elementorエディタでは表示）
- **原因**: Elementorキャッシュ
- **解決**: キャッシュクリアで解決済み

### HTTPS検出問題
- **症状**: Elementorプレビューと静的ファイル（CSS/JS/画像）が読み込めない
- **根本原因**: NginxのHTTPS検出パラメータ欠落 → WordPressがHTTPと判定 → 混在コンテンツエラー
- **解決策**: `fastcgi_param HTTPS on;` と `HTTP_X_FORWARDED_PROTO https;` を追加
- **結果**: 全サイト正常稼働、Elementor編集機能復旧

---

## 既知の問題

### PHP互換性問題
- **症状**: 特定サイトでHTTP 500エラー
- **原因**: テーマが非推奨の `create_function()` を使用（PHP 7.2で非推奨、8.0で削除）
- **対応**: テーマコード更新または代替テーマへの切り替え
- **優先度**: 中

---

## ディレクトリ構成

```
services/blog/
├── docker-compose.yml        # Docker Compose定義
├── .env                       # 環境変数（Git管理外）
├── config/
│   ├── nginx/
│   │   ├── nginx.conf        # Nginx基本設定
│   │   └── conf.d/           # 仮想ホスト設定
│   ├── php/
│   │   └── php.ini           # PHP設定
│   ├── wordpress/
│   │   └── wp-mail-smtp.php  # SMTP設定
│   └── mariadb/
│       ├── my.cnf            # MariaDB設定
│       └── init/
│           └── 01-create-databases.sql  # DB初期化SQL
├── scripts/
│   ├── create-new-wp-site.sh        # 新規サイト作成ウィザード
│   ├── setup-wp-mail-smtp.sh        # SMTP一括設定
│   ├── check-wp-mail-smtp.sh        # SMTP設定確認
│   ├── generate-nginx-subdirectories.sh  # Nginx設定生成
│   └── fix-permissions.sh           # パーミッション修正
└── (データは外部ボリュームからマウント)
```

---

## 運用コマンド

### Docker操作

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# コンテナ状態確認
docker compose ps

# ログ確認
docker compose logs -f nginx
docker compose logs -f wordpress

# サービス再起動
docker compose restart nginx

# コンテナシェルアクセス
docker compose exec wordpress bash
docker compose exec nginx sh
```

### WordPress操作

```bash
# wp-cliコマンド実行
docker compose exec -T wordpress wp --help --allow-root

# URL一括置換例
docker compose exec -T wordpress wp search-replace \
  "https://old-domain.com" "https://new-domain.com" \
  --path=/var/www/html/site-name \
  --allow-root \
  --skip-columns=guid
```

### 新規サイト作成

```bash
# 対話式ウィザードで新規サイト作成
./scripts/create-new-wp-site.sh
```

---

## セキュリティ対策

### 実装済み

- ✅ **通信暗号化**: Cloudflare証明書（HTTPS自動）
- ✅ **データベース**: Docker内部ネットワーク限定（非公開ポート）
- ✅ **ファイルパーミッション**: www-data所有設定
- ✅ **認証情報管理**: `.env`ファイルはGit管理外
- ✅ **WAF**: Cloudflare WAFによる攻撃防御
- ✅ **DDoS保護**: Cloudflare DDoS Protection

---

## パフォーマンス

| 項目 | 目標 | 現状 |
|------|------|------|
| ページ読み込み時間 | 3秒以内 | ✅ 達成 |
| 同時接続ユーザー | 10-50人 | 初期見積もり |
| 稼働率 | 99%以上（月間） | 監視中 |
| DB応答時間 | 100ms以内 | ✅ SSDで高速化 |

---

## リソース使用状況

| 項目 | Blog System | 合計 | 状態 |
|------|-------------|------|------|
| **RAM** | 約4GB | 15GB / 32GB | ✅ 余裕あり |
| **HDD** | 95GB | 96GB / 3.4TB | ✅ 余裕あり |

---

## 参考情報

### 公式ドキュメント

- [WordPress Requirements](https://wordpress.org/about/requirements/)
- [Docker Hub - WordPress](https://hub.docker.com/_/wordpress)
- [Docker Hub - MariaDB](https://hub.docker.com/_/mariadb)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

---

**Version**: 3.0
**現在のフェーズ**: 本番稼働中（17サイト）
