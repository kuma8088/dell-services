# P010: HTTPS Mixed Content エラー（Elementor/画像表示問題）

**関連タスク**: 緊急トラブルシューティング（新規発生）
**ステータス**: Processing
**優先度**: Critical ⚠️
**作成日**: 2025-11-10
**担当**: 調査中

---

## 📋 問題概要

2025-11-10 02:00頃、Phase 1（メール送信機能実装）完了後、WordPress管理画面で以下のエラーが発生：

1. **Elementor編集画面**: "ブロック読み込みエラー: 現在オフラインのようです"
2. **アイキャッチ画像**: "アイキャッチ画像データを取得できませんでした"
3. **フロントエンド**: 画像表示不可、YouTubeの埋め込みエラー

**影響範囲**:
- ✅ blog.fx-trader-life.com: 正常動作
- ❌ blog.webmakeprofit.org: エラー発生
- ❌ blog.toyota-phv.jp: YouTubeエラー

---

## 🎯 根本原因（確定）

### 原因1: データベースURLがHTTPのまま
- **問題**: データベースの `home`/`siteurl` が `http://blog.webmakeprofit.org/`
- **影響**: Elementor REST APIがHTTPのURLを返す → Mixed Contentエラー
- **ブラウザ動作**: HTTPSページ内のHTTPリソースをブロック

### 原因2: リダイレクトループ（HTTPSへの変更後）
- **問題**: データベースURLをHTTPSに変更 → 無限リダイレクト発生
- **原因**: WordPressがリバースプロキシ経由のHTTPS接続を認識できない
- **エラー**: `net::ERR_TOO_MANY_REDIRECTS`

### 原因3: Nginx設定不足
- **問題**: NginxがWordPressにHTTPS情報を渡していない
- **結果**: WordPress側で `$_SERVER['HTTPS']` が未設定 → HTTP扱い

---

## 📌 現状（2025-11-10 13:45時点）

### アーキテクチャ
```
外部HTTPS → Cloudflare Tunnel → Nginx (HTTP:80) → PHP-FPM → WordPress
```

### 設定状態

**データベース**:
- ✅ webmakeprofit: `http://blog.webmakeprofit.org/` （HTTPに戻した）
- ✅ toyota-phv: `http://blog.toyota-phv.jp/` （HTTPに戻した）
- ❌ 他12サイト: `http://` のまま

**wp-config.php**（webmakeprofit, toyota-phv）:
```php
// Cloudflare HTTPS detection for reverse proxy
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = 443;
}
if (isset($_SERVER['HTTP_CLOUDFLARE_VISITOR'])) {
    $visitor = json_decode($_SERVER['HTTP_CLOUDFLARE_VISITOR']);
    if (isset($visitor->scheme) && $visitor->scheme === 'https') {
        $_SERVER['HTTPS'] = 'on';
        $_SERVER['SERVER_PORT'] = 443;
    }
}
define('FORCE_SSL_ADMIN', true);
```

**Nginx設定** (`config/nginx/conf.d/webmakeprofit.conf`):
```nginx
location ~ \.php$ {
    fastcgi_param HTTPS on;        # 追加済み
    fastcgi_param SERVER_PORT 443; # 追加済み
}
```

**PHP設定** (`config/php/https-fix.php`):
```php
// X-Forwarded-Proto ヘッダー検出
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = 443;
}
```

### MCPブラウザテスト結果

**Playwright検証** (2025-11-10 12:13):
```
URL: https://blog.webmakeprofit.org/
Status: net::ERR_TOO_MANY_REDIRECTS

Console Errors:
- Mixed Content: HTTPSページ内のHTTPリソース読み込み試行
- Access to font at 'https://webmakeprofit.org/...' (ドメイン不一致)
- Failed to load resource: net::ERR_FAILED (多数)
```

**問題点**:
1. ❌ リダイレクトループ継続
2. ❌ Mixed Contentエラー多数
3. ❌ フォント/画像URLが `webmakeprofit.org` （blogサブドメインなし）

---

## 💡 実施した対処

### 対処1: データベースURLをHTTPSに変更（失敗 → 戻した）
```sql
UPDATE wp_options SET option_value = 'https://blog.webmakeprofit.org/'
WHERE option_name IN ('siteurl', 'home');
```
**結果**: ❌ リダイレクトループ発生 → ✅ HTTPに戻して解消

### 対処2: PHP HTTPS検出スクリプト作成（失敗）
```php
// config/php/https-fix.php
if ($_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
}
```
**結果**: ❌ リダイレクトループ継続（Cloudflareはヘッダーを送っていない可能性）

### 対処3: Nginx fastcgi_param追加（失敗）
```nginx
fastcgi_param HTTPS on;
fastcgi_param SERVER_PORT 443;
```
**結果**: ❌ リダイレクトループ継続

### 対処4: fx-trader-lifeとの差分調査（完了）
**発見事項**:
- ✅ テーマの違い: fx-trader-life（SWELL） vs webmakeprofit（Astra + Elementor）
- ✅ プラグイン構成の違い: fx-trader-lifeはシンプル、webmakeprofitは大量のマーケティングプラグイン
- ✅ 両サイトともwp-config.phpにHTTPS関連設定なし

**結論**: SWELLテーマとElementorの違いが影響している可能性

### 対処5: wp-config.phpにHTTPS検出コード追加（効果なし）
```php
// Cloudflare HTTPS detection
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = 443;
}
if (isset($_SERVER['HTTP_CLOUDFLARE_VISITOR'])) {
    $visitor = json_decode($_SERVER['HTTP_CLOUDFLARE_VISITOR']);
    if (isset($visitor->scheme) && $visitor->scheme === 'https') {
        $_SERVER['HTTPS'] = 'on';
        $_SERVER['SERVER_PORT'] = 443;
    }
}
define('FORCE_SSL_ADMIN', true);
```
**結果**: ❌ リダイレクトループは解消したが、Mixed Contentエラー継続

**新たな問題発見**:
- URLが `https://webmakeprofit.org/wp-content/...` （サブドメイン"blog"なし）
- データベース内に保存されているURLが間違っている可能性

---

## 🚧 改善しなかった理由

### 問題の本質
**Cloudflare TunnelとWordPressの認識ずれ**:
1. Cloudflare: HTTPSでアクセス
2. Nginx: ポート80でHTTP受信
3. WordPress: HTTPS情報を受け取れない → HTTPと判断
4. WordPress: データベースがHTTPSなので `https://` にリダイレクト
5. ループ: 3に戻る

### 正常動作しているfx-trader-lifeとの違い

**共通点**:
- データベースURL: `http://` （両方同じ）
- Nginx設定: fastcgi_param設定なし（同じ）

**相違点**:
- ✅ fx-trader-life: ページ内URLが自動的にHTTPSに変換されている
- ❌ webmakeprofit: ページ内URLがHTTPのまま

**推測**: fx-trader-lifeでは何らかのプラグインまたはテーマがURL変換を行っている可能性

---

## 📝 次のステップ

### ✅ 完了: 緊急対応（一時的解決）

**案A: データベースURLをHTTPに戻す**（実施済み）
```sql
UPDATE wp_options SET option_value = 'http://blog.webmakeprofit.org/'
WHERE option_name IN ('siteurl', 'home');
```
- ✅ サイトアクセス復旧（リダイレクトループ解消）
- ❌ Elementorエラー/画像エラーは継続
- 理由: データベース内のURLが `webmakeprofit.org` (サブドメインなし)

### 根本解決（要調査）

**案B: wp-config.php でHTTPS強制**
```php
// wp-config.php に追加
if (isset($_SERVER['HTTP_CLOUDFLARE_VISITOR'])) {
    $visitor = json_decode($_SERVER['HTTP_CLOUDFLARE_VISITOR']);
    if ($visitor->scheme == 'https') {
        $_SERVER['HTTPS'] = 'on';
    }
}

define('FORCE_SSL_ADMIN', true);
if ($_SERVER['HTTP_X_FORWARDED_PROTO'] == 'https')
    $_SERVER['HTTPS']='on';
```

**案C: WordPress Really Simple SSL プラグイン**
- リバースプロキシ検出機能あり
- 自動URL書き換え
- Mixed Content自動修正

**案D: fx-trader-lifeの設定を調査**（実施済み）
```bash
# プラグイン比較（実施済み）
diff <(ls /var/www/html/webmakeprofit/wp-content/plugins/) \
     <(ls /var/www/html/fx-trader-life/wp-content/plugins/)
```
- ✅ 完了: テーマの違いを発見（SWELL vs Astra + Elementor）
- ✅ 完了: プラグイン構成の違いを確認

**案E: データベース内URLの一括置換（推奨）**
```sql
-- wp_posts テーブル内のURL置換
UPDATE wp_posts
SET post_content = REPLACE(post_content, 'https://webmakeprofit.org/', 'https://blog.webmakeprofit.org/');

UPDATE wp_posts
SET guid = REPLACE(guid, 'https://webmakeprofit.org/', 'https://blog.webmakeprofit.org/');

-- wp_postmeta テーブル内のURL置換
UPDATE wp_postmeta
SET meta_value = REPLACE(meta_value, 'https://webmakeprofit.org/', 'https://blog.webmakeprofit.org/');

-- Elementor データの再構築
-- WordPressダッシュボード → Elementor → ツール → データを再生成
```
⚠️ **注意**: 実行前に必ずバックアップ取得

---

## 🔧 検証が必要な項目

### Cloudflare設定確認
- [ ] SSL/TLS設定: Flexible / Full / Full (strict) のどれか？
- [ ] Automatic HTTPS Rewrites: 有効/無効？
- [ ] X-Forwarded-Protoヘッダー: 送信されているか？

### WordPress設定確認
- [ ] fx-trader-lifeのwp-config.php内容
- [ ] fx-trader-lifeのプラグインリスト
- [ ] webmakeprofitとの設定差分

### 動作確認
```bash
# Cloudflareヘッダー確認
curl -I https://blog.webmakeprofit.org/ | grep -i "x-forwarded\|cloudflare"

# WordPress内部でのHTTPS認識確認
docker compose exec wordpress php -r '
include("/var/www/html/webmakeprofit/wp-config.php");
echo "HTTPS: " . ($_SERVER["HTTPS"] ?? "not set") . "\n";
echo "X-Forwarded-Proto: " . ($_SERVER["HTTP_X_FORWARDED_PROTO"] ?? "not set") . "\n";
'
```

---

## ⚠️ ブロッカー

1. **CloudflareのHTTPS検出方法が不明**
   - X-Forwarded-Protoヘッダーが送られているか不明
   - Cloudflare特有のヘッダーを使うべきか不明

2. **正常動作サイトとの差分が不明**
   - fx-trader-lifeは同じ構成で正常動作
   - 設定差分の特定が必要

3. **WordPress HTTPS検出ロジックの理解不足**
   - リバースプロキシ経由のHTTPS検出方法
   - WordPressコア動作の詳細把握が必要

---

## 📚 関連ドキュメント

- `docs/application/blog/README.md` - Blog System概要
- `services/blog/docker-compose.yml` - サービス構成
- `services/blog/config/nginx/conf.d/` - Nginx設定
- `services/blog/config/php/` - PHP設定

---

## 📅 タイムライン

- 2025-11-10 02:00: Phase 1完了後、エラー発生を確認
- 2025-11-10 02:30: WordPressコンテナのインターネット接続確認（正常）
- 2025-11-10 03:00: データベースURLがHTTPと判明
- 2025-11-10 03:01: HTTPSに変更 → リダイレクトループ発生
- 2025-11-10 03:05: https-fix.php作成・適用（効果なし）
- 2025-11-10 03:07: Nginx設定追加（効果なし）
- 2025-11-10 03:13: MCPブラウザテスト実施 → リダイレクトループ確認
- 2025-11-10 03:15: P010ドキュメント初版作成
- 2025-11-10 13:30: データベースURLをHTTPに戻してリダイレクトループ解消
- 2025-11-10 13:35: fx-trader-lifeとの差分調査 → テーマの違い発見（SWELL vs Elementor）
- 2025-11-10 13:40: wp-config.phpにHTTPS検出コード追加
- 2025-11-10 13:45: MCPブラウザ再テスト → Mixed Contentエラー継続、URLにサブドメインなし問題発見
- 2025-11-10 13:50: P010ドキュメント更新（対処5まで追加、案E提案）

---

## 📊 影響サイト一覧

| サイト | データベースURL | 動作状況 | 備考 |
|--------|-----------------|----------|------|
| fx-trader-life | `http://` | ✅ 正常 | なぜか正常動作 |
| webmakeprofit | `https://` | ❌ ループ | 調査対象 |
| toyota-phv | `https://` | ❌ ループ | YouTubeエラー |
| その他12サイト | `http://` | 🔍 未確認 | 同様の問題の可能性 |

---

## 🎯 優先度判断

**Critical理由**:
1. Elementor編集不可 → コンテンツ更新不可
2. 画像表示不可 → ユーザー体験悪化
3. 本番稼働前（Phase A-1）だが、早期解決必須

**推奨対応順**:
1. ✅ **完了**: データベースURLをHTTPに戻して一時復旧（リダイレクトループ解消）
2. ✅ **完了**: fx-trader-lifeとの差分調査（テーマの違い発見）
3. ⚠️ **次**: データベース内URL一括置換（案E）でサブドメイン問題解決
4. **その後**: Elementorデータ再生成で最終確認
5. **1週間以内**: 全14サイトで同一対策実施
