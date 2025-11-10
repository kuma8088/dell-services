# I006: キャッシュシステム導入（Blog System）

**関連タスク**: [#006] キャッシュシステム（blogsystem）
**ステータス**: Inbox
**優先度**: Low
**作成日**: 2025-11-10
**担当**: 未割当

---

## 📋 課題概要

WordPress デフォルトキャッシュのみでは、14サイト同時運用時のパフォーマンスが最適化されていない。Redis/Memcached等の導入でレスポンス改善を図る。

---

## 🎯 目標

ページロード時間を30-50%短縮し、サーバーリソース効率を向上させる。

---

## 📌 現状

### キャッシュ構成
- WordPress OPcache: 有効（PHP 8.3）
- オブジェクトキャッシュ: なし
- ページキャッシュ: なし（プラグイン未導入）
- CDN: Cloudflare（外部キャッシュ）

### パフォーマンス指標（未測定）
- TTFB (Time To First Byte): 未測定
- ページロード時間: 未測定
- データベースクエリ数: 未測定

---

## 💡 提案される解決策

### 案A: Redis + Object Cache Pro
- WordPress Object Cache（WP_Object_Cache）をRedisバックエンドに
- メリット: データベース負荷削減、セッション管理統合
- デメリット: Redis管理コスト、メモリ使用量増加

### 案B: Redis + W3 Total Cache
- ページキャッシュ + オブジェクトキャッシュ統合
- メリット: 総合的なキャッシュ戦略、無料
- デメリット: 設定複雑、プラグイン肥大化

### 案C: LiteSpeed Cache（Nginx環境では不可）
- Nginx環境のため非推奨

---

## 📋 要件（案）

### 機能要件
- [ ] オブジェクトキャッシュ（データベースクエリ結果）
- [ ] ページキャッシュ（HTML出力）
- [ ] セッション管理（Redis）
- [ ] キャッシュパージ機能（投稿更新時等）

### 非機能要件
- [ ] キャッシュヒット率: 80%以上
- [ ] キャッシュ応答時間: < 10ms
- [ ] メモリ使用量: < 512MB（Redis）
- [ ] 高可用性: Redis Sentinel（将来的に）

---

## 🔧 実装案

### Phase 1: Redis導入
```yaml
# docker-compose.yml に追加
redis:
  image: redis:7-alpine
  container_name: blog-redis
  restart: always
  networks:
    blog_network:
      ipv4_address: 172.22.0.60
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

### Phase 2: WordPress設定
```php
// wp-config.php
define('WP_REDIS_HOST', '172.22.0.60');
define('WP_REDIS_PORT', 6379);
define('WP_CACHE', true);
```

### Phase 3: プラグインインストール
- Redis Object Cache プラグイン（全14サイト）

---

## 📊 効果測定

### Before（キャッシュなし）
- TTFB: 測定必要
- ページロード時間: 測定必要
- DBクエリ数: 測定必要

### After（目標値）
- TTFB: 30%短縮
- ページロード時間: 40%短縮
- DBクエリ数: 50%削減

---

## 🚧 ブロッカー

なし（パフォーマンス測定から開始可能）

---

## 📝 次のステップ

1. パフォーマンスベースライン測定
2. Redis導入検証（1サイトでPOC）
3. 効果測定
4. 全サイト展開

---

## 📚 関連ドキュメント

- `docs/application/01_improvement+issue.md` - タスク#006
- `services/blog/docker-compose.yml` - Docker構成

---

## 📅 更新履歴

- 2025-11-10: Issue作成
