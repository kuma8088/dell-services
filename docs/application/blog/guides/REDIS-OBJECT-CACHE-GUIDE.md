# WordPress Redis Object Cache 導入ガイド

**関連Issue**: I006 - キャッシュシステム導入
**作成日**: 2025-11-13
**対象**: Blog System（16 WordPressサイト）

---

## 📋 概要

WordPress Object CacheにRedisを導入し、データベースクエリを削減してパフォーマンスを向上させます。

### 導入効果（予想）

- **TTFB (Time To First Byte)**: 30%短縮
- **ページロード時間**: 40%短縮
- **データベースクエリ数**: 50%削減

---

## 🏗️ アーキテクチャ

### Redis構成

- **Image**: redis:7-alpine
- **IP Address**: 172.22.0.60
- **Port**: 6379
- **Memory Limit**: 512MB
- **Eviction Policy**: allkeys-lru
- **Persistence**: AOF (Append Only File)

### WordPress構成

- **Plugin**: Redis Object Cache
- **Sites**: 全16サイト
- **Database Index**: サイトごとに0-15を割り当て
- **Prefix**: サイト名を使用（例: `kuma8088_`）

---

## 🚀 セットアップ手順

### Step 1: Redisコンテナ起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Docker Composeで起動
docker compose up -d redis

# Redis起動確認
docker compose exec redis redis-cli ping
# 期待される出力: PONG

# Redis情報確認
docker compose exec redis redis-cli INFO server
```

### Step 2: Redis Object Cache プラグインのインストールと設定

```bash
# 自動設定スクリプトを実行可能にする
chmod +x ./scripts/setup-redis-object-cache.sh

# Dry-runで確認（実際には実行しない）
./scripts/setup-redis-object-cache.sh --dry-run

# 全16サイトに自動設定
./scripts/setup-redis-object-cache.sh
```

### Step 3: 動作確認

```bash
# キャッシュ状態確認（demo1サイト）
docker compose exec wordpress \
  wp redis status --path="/var/www/html/demo1-kuma8088"

# Redis メモリ使用量確認
docker compose exec redis redis-cli INFO memory

# キースペース確認
docker compose exec redis redis-cli INFO keyspace
```

---

## 🧪 パフォーマンステスト

### 自動テストスクリプト実行

```bash
# テストスクリプトを実行可能にする
chmod +x ./scripts/test-redis-performance.sh

# demo1サイトでテスト
./scripts/test-redis-performance.sh demo1-kuma8088

# 他のサイトでテスト
./scripts/test-redis-performance.sh kuma8088
```

### 手動テスト

#### Before（キャッシュなし）

```bash
# キャッシュ無効化
docker compose exec wordpress \
  wp redis disable --path="/var/www/html/demo1-kuma8088"

# ページロード時間測定（3回）
for i in {1..3}; do
  echo "Test $i:"
  curl -o /dev/null -s -w '%{time_total}\n' https://demo1.kuma8088.com
done
```

#### After（キャッシュ有効）

```bash
# キャッシュ有効化
docker compose exec wordpress \
  wp redis enable --path="/var/www/html/demo1-kuma8088"

# キャッシュフラッシュ
docker compose exec wordpress \
  wp redis flush --path="/var/www/html/demo1-kuma8088"

# ページロード時間測定（3回）
for i in {1..3}; do
  echo "Test $i:"
  curl -o /dev/null -s -w '%{time_total}\n' https://demo1.kuma8088.com
done
```

### Redis Monitor（リアルタイム監視）

```bash
# Redisコマンドをリアルタイムで監視
docker compose exec redis redis-cli monitor

# 別ターミナルでWordPressサイトにアクセスして動作確認
```

---

## 📊 モニタリング

### Redis統計情報

```bash
# キャッシュヒット率
docker compose exec redis redis-cli INFO stats | grep keyspace

# メモリ使用量
docker compose exec redis redis-cli INFO memory | grep used_memory_human

# 接続数
docker compose exec redis redis-cli INFO clients

# スローログ確認（100μs以上のクエリ）
docker compose exec redis redis-cli SLOWLOG GET 10
```

### WordPress側の確認

```bash
# 全サイトのキャッシュ状態一括確認
for site in kuma8088 demo1-kuma8088 webmakeprofit; do
  echo "=== $site ==="
  docker compose exec wordpress wp redis status --path="/var/www/html/$site"
done
```

---

## 🛠️ トラブルシューティング

### 問題: Redis接続エラー

**症状**:
```
Error: Connection to Redis failed
```

**解決策**:
```bash
# Redisコンテナ起動確認
docker compose ps redis

# Redis起動
docker compose up -d redis

# ネットワーク確認
docker compose exec wordpress ping -c 3 172.22.0.60
```

### 問題: メモリ不足エラー

**症状**:
```
OOM command not allowed when used memory > 'maxmemory'
```

**解決策**:
```bash
# メモリ使用量確認
docker compose exec redis redis-cli INFO memory

# キャッシュクリア
docker compose exec redis redis-cli FLUSHALL

# メモリ上限変更（docker-compose.yml）
# maxmemory 512mb → 1gb に変更
docker compose up -d redis
```

### 問題: キャッシュが効かない

**症状**:
- ページロード時間が改善しない
- `keyspace_hits` が増えない

**解決策**:
```bash
# wp-config.php の設定確認
docker compose exec wordpress \
  grep -A5 "WP_REDIS_HOST" /var/www/html/demo1-kuma8088/wp-config.php

# Object Cache drop-in確認
docker compose exec wordpress \
  ls -la /var/www/html/demo1-kuma8088/wp-content/object-cache.php

# drop-inが無い場合、再度有効化
docker compose exec wordpress \
  wp redis enable --path="/var/www/html/demo1-kuma8088"
```

---

## 🔧 メンテナンス

### キャッシュクリア

```bash
# 特定サイトのキャッシュクリア
docker compose exec wordpress \
  wp redis flush --path="/var/www/html/demo1-kuma8088"

# 全サイトのキャッシュクリア（Redis全体）
docker compose exec redis redis-cli FLUSHALL
```

### バックアップ

```bash
# AOFファイルの手動セーブ
docker compose exec redis redis-cli BGSAVE

# AOFファイルのバックアップ
docker cp blog-redis:/data/appendonly.aof /mnt/backup-hdd/blog/redis-backup/
```

### 再起動

```bash
# Redisコンテナのみ再起動
docker compose restart redis

# 全コンテナ再起動
docker compose restart
```

---

## 📋 設定ファイル

### docker-compose.yml

```yaml
redis:
  image: redis:7-alpine
  container_name: blog-redis
  hostname: redis
  restart: always
  networks:
    blog_network:
      ipv4_address: 172.22.0.60
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### wp-config.php

```php
// Redis Object Cache Configuration
define('WP_REDIS_HOST', '172.22.0.60');
define('WP_REDIS_PORT', 6379);
define('WP_REDIS_DATABASE', 0);  // サイトごとに0-15
define('WP_REDIS_PREFIX', 'kuma8088_');
define('WP_REDIS_TIMEOUT', 1);
define('WP_REDIS_READ_TIMEOUT', 1);
define('WP_CACHE', true);
```

---

## 📚 参考リソース

- [Redis Object Cache Plugin](https://wordpress.org/plugins/redis-cache/)
- [Redis Documentation](https://redis.io/docs/)
- [WordPress Object Cache](https://developer.wordpress.org/reference/classes/wp_object_cache/)

---

## 📝 チェックリスト

- [ ] Redisコンテナ起動確認
- [ ] 全16サイトにプラグインインストール
- [ ] wp-config.php設定追加
- [ ] Object Cache有効化
- [ ] パフォーマンステスト実施
- [ ] Before/After比較データ取得
- [ ] メモリ使用量監視
- [ ] キャッシュヒット率監視

---

## 📅 更新履歴

- 2025-11-13: 初版作成（Redis導入ガイド）
