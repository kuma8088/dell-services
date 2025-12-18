# ブログシステム運用設計

**技術スタック**: Docker Compose, WordPress, Nginx, wp-cli

---

## 1. 運用方針

### 1.1 運用原則

| 原則 | 内容 |
|------|------|
| 自動化優先 | 定型作業はスクリプト化 |
| 監視と通知 | 異常検知→即時対応 |
| ドキュメント化 | 手順書整備、変更履歴記録 |
| 最小権限 | 運用に必要な権限のみ付与 |

### 1.2 運用担当範囲

| カテゴリ | 担当 | 頻度 |
|---------|------|------|
| 日常監視 | 自動/手動 | 毎日 |
| バックアップ | 自動（cron） | 毎日 |
| WordPress更新 | 手動 | 月次 |
| 障害対応 | 手動 | 随時 |

---

## 2. 監視設計

### 2.1 監視項目

| カテゴリ | 監視項目 | 閾値 | 通知 |
|---------|---------|------|------|
| リソース | CPU使用率 | 80%以上 | 警告 |
| リソース | メモリ使用率 | 80%以上 | 警告 |
| リソース | ディスク使用率 | 70%以上 | 警告 |
| サービス | コンテナ状態 | unhealthy | 緊急 |
| サービス | サイト応答 | 5秒以上 | 警告 |
| サービス | HTTP 5xx | 発生 | 緊急 |

### 2.2 ヘルスチェック

```bash
# コンテナ状態確認
docker compose ps

# サービス別確認
docker compose exec nginx nginx -t
docker compose exec mariadb mysqladmin -u root ping
docker compose exec redis redis-cli ping

# サイト応答確認
curl -I https://blog.example.com/
curl -I https://site-b.example.net/
curl -I https://site-c.example.jp/
```

### 2.3 ログ監視

| ログ | 確認方法 | 確認ポイント |
|------|---------|-------------|
| Nginx | `docker logs blog-nginx` | 5xx エラー、アクセス異常 |
| WordPress | `docker logs blog-wordpress` | PHP Fatal、警告 |
| MariaDB | `docker logs blog-mariadb` | 接続エラー、スロークエリ |
| cloudflared | `docker logs blog-cloudflared` | Tunnel接続状態 |

---

## 3. バックアップ運用

### 3.1 バックアップ対象

| 対象 | 内容 | 重要度 |
|------|------|--------|
| データベース | 16サイト分のDB | 必須 |
| wp-content | プラグイン、テーマ、アップロード | 必須 |
| 設定ファイル | Nginx、wp-config.php | 必須 |
| Tunnel設定 | credentials.json | 必須 |

### 3.2 バックアップスケジュール

| 種別 | cron設定 | 実行時間 | 保持期間 |
|------|---------|----------|---------|
| 日次バックアップ | `0 3 * * *` | AM 3:00 | 7日 |
| 週次バックアップ | `0 2 * * 0` | 日曜 AM 2:00 | 4週 |

### 3.3 バックアップ手順

**データベースバックアップ**:
```bash
# 全データベースバックアップ
docker compose exec mariadb mysqldump \
  --all-databases \
  -u root -p > /mnt/backup-hdd/blog/daily/$(date +%Y-%m-%d)/all-databases.sql

# サイト別バックアップ
docker compose exec mariadb mysqldump \
  -u root -p blog_main > main.sql
```

**ファイルバックアップ**:
```bash
# wp-contentバックアップ
rsync -av --delete \
  data/wordpress/ \
  /mnt/backup-hdd/blog/daily/$(date +%Y-%m-%d)/wordpress/

# 設定ファイルバックアップ
tar czf /mnt/backup-hdd/blog/daily/$(date +%Y-%m-%d)/config.tar.gz \
  config/nginx/ config/wordpress/ config/cloudflared/
```

### 3.4 バックアップ確認

```bash
# バックアップディレクトリ確認
ls -lah /mnt/backup-hdd/blog/daily/

# バックアップサイズ確認
du -sh /mnt/backup-hdd/blog/daily/*

# SQLファイル整合性確認
head -20 /mnt/backup-hdd/blog/daily/$(date +%Y-%m-%d)/all-databases.sql
```

---

## 4. リストア手順

### 4.1 リストア前チェック

```bash
# 1. バックアップの存在確認
ls -la /mnt/backup-hdd/blog/daily/

# 2. SQLファイル確認
file /mnt/backup-hdd/blog/daily/YYYY-MM-DD/*.sql

# 3. 現在のサービス状態記録
docker compose ps > /tmp/service-status-before.txt
```

### 4.2 データベースリストア

```bash
# 1. WordPressサービス停止
docker compose stop wordpress

# 2. リストア実行
docker compose exec -T mariadb mysql -u root -p < \
  /mnt/backup-hdd/blog/daily/YYYY-MM-DD/all-databases.sql

# 3. サービス再開
docker compose start wordpress

# 4. 動作確認
curl -I https://blog.example.com/
```

### 4.3 ファイルリストア

```bash
# 1. 現在のデータバックアップ（念のため）
mv data/wordpress data/wordpress.bak

# 2. リストア実行
rsync -av /mnt/backup-hdd/blog/daily/YYYY-MM-DD/wordpress/ data/wordpress/

# 3. パーミッション修正
./scripts/fix-permissions.sh

# 4. サービス再起動
docker compose restart wordpress nginx
```

### 4.4 リストア後確認

```bash
# サービス起動確認
docker compose ps

# ログ確認
docker compose logs --tail=50

# サイト表示確認
curl -I https://blog.example.com/
curl -I https://site-b.example.net/
```

---

## 5. 障害対応

### 5.1 障害レベル定義

| レベル | 定義 | 目標復旧時間 | 例 |
|--------|------|-------------|-----|
| Critical | 全サイト停止 | 1時間 | 全コンテナ停止 |
| High | 主要サイト停止 | 2時間 | メインサイト表示不可 |
| Medium | 一部機能停止 | 4時間 | 特定サイトのみ不具合 |
| Low | 軽微な問題 | 24時間 | 表示崩れ、軽微なエラー |

### 5.2 障害対応フロー

```
障害検知
    │
    ▼
┌─────────────────────┐
│ 1. 影響範囲確認     │
│    docker compose ps│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. ログ確認         │
│    docker logs ...  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. 原因特定         │
│    設定/リソース/外部│
└─────────────────────┘
    │
    ├── 設定問題 → 設定修正 → Nginx reload
    ├── リソース問題 → リソース解放
    └── 外部問題 → Cloudflare確認
    │
    ▼
┌─────────────────────┐
│ 4. 復旧確認         │
│    サイト表示テスト  │
└─────────────────────┘
```

### 5.3 よくある障害と対処

#### サイトが表示されない（503/502）
```bash
# 1. コンテナ状態確認
docker compose ps

# 2. Nginx確認
docker compose logs nginx | tail -50

# 3. WordPress確認
docker compose logs wordpress | tail -50

# 4. 再起動
docker compose restart nginx wordpress
```

#### データベース接続エラー
```bash
# 1. MariaDB状態確認
docker compose exec mariadb mysqladmin -u root -p status

# 2. 接続テスト
docker compose exec wordpress php -r "new PDO('mysql:host=mariadb;dbname=blog_main', 'wordpress', 'password');"

# 3. 再起動
docker compose restart mariadb wordpress
```

#### プラグイン/テーマ更新失敗
```bash
# 原因: パーミッション問題

# 1. パーミッション確認
docker compose exec wordpress ls -la /var/www/html/wp-content/

# 2. パーミッション修正
./scripts/fix-permissions.sh

# 3. 再試行
# WordPress管理画面から更新を再実行
```

#### Cloudflare Tunnel切断
```bash
# 1. Tunnel状態確認
docker compose logs cloudflared | tail -50

# 2. 再起動
docker compose restart cloudflared

# 3. Cloudflare Dashboard確認
# Cloudflare > Zero Trust > Tunnels で接続状態確認
```

#### PHP Fatal Error
```bash
# 1. エラー内容確認
docker compose logs wordpress | grep -i fatal

# 2. 問題プラグイン特定
# wp-content/plugins/ を確認

# 3. プラグイン無効化（CLIから）
docker compose exec wordpress wp plugin deactivate <plugin-name> --path=/var/www/html/<site>/
```

---

## 6. サイト管理

### 6.1 wp-cli操作

```bash
# コンテナ内でwp-cli実行
docker compose exec wordpress wp <command> --path=/var/www/html/<site>/

# 例: プラグイン一覧
docker compose exec wordpress wp plugin list --path=/var/www/html/

# 例: キャッシュクリア
docker compose exec wordpress wp cache flush --path=/var/www/html/

# 例: データベース最適化
docker compose exec wordpress wp db optimize --path=/var/www/html/
```

### 6.2 サイト追加

```bash
# 自動化スクリプト（推奨）
./scripts/create-new-wp-site.sh

# 手順:
# 1. DB作成
# 2. WordPressファイルコピー
# 3. wp-config.php設定
# 4. Nginx設定追加
# 5. Cloudflare Tunnel設定更新（必要時）
```

### 6.3 サイト削除

```bash
# 1. Nginx設定から削除
vim config/nginx/conf.d/<site>.conf

# 2. データベース削除
docker compose exec mariadb mysql -u root -p \
  -e "DROP DATABASE blog_<site>;"

# 3. ファイル削除
rm -rf data/wordpress/<site>/

# 4. Nginx reload
docker compose exec nginx nginx -s reload

# 5. Cloudflare Tunnel設定更新（必要時）
```

---

## 7. WP Mail SMTP管理

### 7.1 設定確認

```bash
# 全サイトの設定状況確認
./scripts/check-wp-mail-smtp.sh
```

### 7.2 一括設定

```bash
# プレビュー
./scripts/setup-wp-mail-smtp.sh --dry-run

# 実行
./scripts/setup-wp-mail-smtp.sh
```

### 7.3 テストメール送信

```bash
# テストメール送信
./scripts/setup-wp-mail-smtp.sh --test-email your@email.com
```

---

## 8. 定期メンテナンス

### 8.1 日次タスク

| タスク | 確認方法 |
|--------|---------|
| バックアップ成功確認 | `ls /mnt/backup-hdd/blog/daily/` |
| コンテナ状態確認 | `docker compose ps` |
| エラーログ確認 | `docker compose logs --since 24h | grep -i error` |

### 8.2 週次タスク

| タスク | 確認方法 |
|--------|---------|
| 週次バックアップ確認 | `ls /mnt/backup-hdd/blog/weekly/` |
| ディスク使用量確認 | `df -h` |
| WordPress更新確認 | 管理画面のダッシュボード |

### 8.3 月次タスク

| タスク | 手順 |
|--------|------|
| バックアップリストアテスト | テスト環境でリストア検証 |
| WordPress コア更新 | テスト後に本番適用 |
| プラグイン更新 | 互換性確認後に更新 |
| Dockerイメージ更新 | `docker compose pull` |
| SSL証明書確認 | Cloudflare自動管理 |

### 8.4 年次タスク

| タスク | 手順 |
|--------|------|
| DR訓練 | 完全リストア訓練 |
| セキュリティ監査 | 設定・権限見直し |
| キャパシティ計画 | ストレージ・リソース見直し |
| PHPバージョン検討 | 互換性確認・アップグレード検討 |

---

## 9. セキュリティ運用

### 9.1 WordPress更新ポリシー

| 対象 | 更新頻度 | 手順 |
|------|---------|------|
| コア（セキュリティ） | 即時 | テスト後に全サイト適用 |
| コア（メジャー） | 月次 | 互換性確認後 |
| プラグイン | 月次 | 互換性確認後 |
| テーマ | 月次 | 互換性確認後 |

### 9.2 パーミッション管理

```bash
# パーミッション一括修正スクリプト
./scripts/fix-permissions.sh

# 内容:
# - wp-content: 755
# - wp-content/uploads: 755
# - ファイル: 644
# - 所有者: www-data (82:82)
```

### 9.3 アクセスログ確認

```bash
# Nginxアクセスログ確認
docker compose logs nginx | grep -E "POST|DELETE"

# 不審なアクセス確認
docker compose logs nginx | grep -E "4[0-9]{2}|5[0-9]{2}"

# wp-login.php へのアクセス確認
docker compose logs nginx | grep wp-login.php
```

---

## 10. 運用スクリプト一覧

| スクリプト | 用途 |
|-----------|------|
| create-new-wp-site.sh | 新規サイト作成ウィザード |
| setup-wp-mail-smtp.sh | WP Mail SMTP一括設定 |
| check-wp-mail-smtp.sh | SMTP設定確認 |
| fix-permissions.sh | パーミッション一括修正 |
| generate-nginx-subdirectories.sh | Nginx設定自動生成 |

---

## 11. 運用チェックリスト

### 11.1 障害発生時

```
□ 影響範囲の確認
□ ログの確認
□ 原因の特定
□ 対処の実施
□ 復旧の確認
□ 関係者への報告
□ 事後分析・再発防止策
```

### 11.2 デプロイ時

```
□ バックアップの確認
□ 変更内容のレビュー
□ ロールバック手順の確認
□ デプロイの実行
□ 動作確認
□ ログ確認
```

### 11.3 WordPress更新時

```
□ バックアップ取得
□ テスト環境で更新・確認
□ 本番環境で更新
□ サイト表示確認
□ プラグイン動作確認
□ ログ確認
```

---

## 12. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
