# Phase 011: blog.kuma8088.com サブディレクトリサイト表示問題

**起票日**: 2025-11-10
**ステータス**: 📝 起票済み（未着手）
**優先度**: 🔴 HIGH（10サイトが影響）
**担当**: TBD

---

## 📋 問題概要

### 症状

blog.kuma8088.com 配下のサブディレクトリに配置された10サイトで、Elementorプレビュー機能と静的ファイル（CSS/JS/画像）が正常に表示されない。

### 影響範囲

**不良表示群（10サイト）**:

| サイト名 | URL | 状態 |
|---------|-----|------|
| elementordemo1 | https://blog.kuma8088.com/elementordemo1/ | ❌ 表示崩れ |
| elementordemo02 | https://blog.kuma8088.com/elementordemo02/ | ❌ 表示崩れ |
| elementor-demo-03 | https://blog.kuma8088.com/elementor-demo-03/ | ❌ 表示崩れ |
| elementor-demo-04 | https://blog.kuma8088.com/elementor-demo-04/ | ❌ 表示崩れ |
| ec02test | https://blog.kuma8088.com/ec02test/ | ❌ 表示崩れ |
| cameramanual | https://blog.kuma8088.com/cameramanual/ | ❌ 表示崩れ |
| cameramanual-gwpbk492 | https://blog.kuma8088.com/cameramanual-gwpbk492/ | ❌ 表示崩れ |
| test | https://blog.kuma8088.com/test/ | ⚠️ 要確認 |
| kuma8088 (root) | https://blog.kuma8088.com/ | ⚠️ 要確認 |

**問題なし群（6サイト）**:

| サイト名 | URL | 状態 |
|---------|-----|------|
| webmakeprofit | https://blog.webmakeprofit.org/ | ✅ 正常 |
| coconala | https://blog.webmakeprofit.org/coconala/ | ✅ 正常 |
| webmakesprofit | https://blog.webmakesprofit.com/ | ✅ 正常 |
| fx-trader-life | https://blog.fx-trader-life.com/ | ✅ 正常 |
| fx-trader-life-* | https://blog.fx-trader-life.com/4line/ 等 | ✅ 正常 |
| toyota-phv | https://blog.toyota-phv.jp/ | ✅ 正常 |

---

## 🔍 根本原因分析

### 1. ドメイン構成の違い

#### 不良表示群（blog.kuma8088.com）

**特徴**:
- 1つのCloudflare Tunnel（blog.kuma8088.com）に複数WordPressをサブディレクトリで配置
- Nginxで `location ^~ /elementordemoXX/` による特殊なパス振り分け
- ドキュメントルートとWordPressルートが分離

**構成例**:
```nginx
# kuma8088.conf
server {
    server_name blog.kuma8088.com;
    root /var/www/html/kuma8088;  # ルートサイト

    location /elementordemo1 {
        alias /var/www/html/kuma8088-elementordemo1;  # 別ディレクトリ
        # ...
    }
}
```

**問題点**:
1. **Elementorプレビュー**: `/?elementor-preview=ID` のようなルート直下前提のリクエストが正しく振り分けられない
2. **admin-ajax.php**: `/wp-admin/admin-ajax.php` へのAjaxリクエストがサブディレクトリを考慮せず404
3. **絶対パス混在**: 旧ドメイン（gwpbk492.xsrv.jp）やルート直下（/wp-content/...）への絶対URLが残存

#### 問題なし群（独立ドメイン）

**特徴**:
- 各サイトが独立ドメイン（またはサブドメイン）を持つ
- ドキュメントルート = WordPressルート（1:1対応）
- Cloudflare Tunnelも独立設定

**構成例**:
```nginx
# webmakeprofit.conf
server {
    server_name blog.webmakeprofit.org;
    root /var/www/html/webmakeprofit;  # 1:1対応

    location / {
        try_files $uri $uri/ /index.php?$args;
    }
}
```

**正常動作理由**:
- プレビューURL（`/?elementor-preview=ID`）が直接正しいWordPressに到達
- 絶対URLが現行ドメインのみで統一されている
- Cloudflare WAFルールの適用が個別ドメイン単位で最適化されている

### 2. Nginx ルーティング方式の問題

#### 現在の設定（不良群）

```nginx
location /elementordemo1 {
    alias /var/www/html/kuma8088-elementordemo1;
    index index.php index.html;

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $request_filename;
    }

    try_files $uri $uri/ @elementordemo1;
}

location @elementordemo1 {
    rewrite /elementordemo1/(.*)$ /elementordemo1/index.php?/$1 last;
}
```

**問題**:
1. **SCRIPT_FILENAME**: `$request_filename` がサブディレクトリパスを正しく解決しない
2. **WordPress URL判定**: WordPressが自身のサイトURLを `/elementordemo1/` として認識できていない可能性
3. **リライトルール**: `try_files` と `@elementordemo1` の組み合わせがElementor Ajaxリクエストを適切に処理できない

### 3. 絶対URLの混在問題

#### データベース内の旧URL

```sql
-- wp_posts.guid に旧ドメインが残存
SELECT guid FROM wp_posts WHERE guid LIKE '%gwpbk492.xsrv.jp%';
-- 結果: 数百〜数千件の旧URL

-- wp_options の siteurl/home
SELECT option_name, option_value FROM wp_options
WHERE option_name IN ('siteurl', 'home');
-- 期待: https://blog.kuma8088.com/elementordemo1
-- 実際: 混在している可能性
```

#### CSS/JS内のハードコードURL

Elementorが生成したCSS/JSファイル内に:
```css
/* 旧ドメインへの参照 */
background-image: url('https://gwpbk492.xsrv.jp/wp-content/uploads/...');

/* ルート直下への参照 */
background-image: url('/wp-content/uploads/...');
/* → blog.kuma8088.com/wp-content/... を参照してしまう（存在しない） */
```

### 4. Cloudflare Tunnelとセキュリティレイヤーの影響

#### blog.kuma8088.com の構成

**特徴**:
- 1つのCloudflare Public Hostname: `blog.kuma8088.com`
- 14サイトをパス振り分けで処理
- WAF Rules, Bot Fight Modeが全サイトに一律適用

**問題**:
1. **Ajaxブロッキング**: `admin-ajax.php` や `?elementor-preview=` がBot/攻撃と誤判定
2. **混在コンテンツ検出**: 旧ドメイン（HTTP）への参照をCloudflareがブロック
3. **レート制限**: 複数サイト分のリクエストが1ホストに集中し、制限に引っかかりやすい

#### 独立ドメインの構成

**特徴**:
- ドメイン毎に独立したCloudflare Tunnel設定
- 各ドメイン専用のWAFルール
- トラフィックが分散

**正常動作理由**:
- プレビューAjaxが個別最適化されたルールで処理される
- 現行ドメインの絶対URLのみなので混在コンテンツなし
- レート制限の影響を受けにくい

---

## 🎯 解決策の提案

### 方針1: 独立ドメイン化（推奨）⭐

各サイトを独立サブドメインに移行:

**Before**:
```
https://blog.kuma8088.com/elementordemo1/
https://blog.kuma8088.com/elementordemo02/
...
```

**After**:
```
https://elementordemo1.kuma8088.com/
https://elementordemo2.kuma8088.com/
...
```

**メリット**:
- ✅ Nginxルーティングがシンプル（1ドメイン = 1 WordPress）
- ✅ 絶対URL問題が根本解決
- ✅ Cloudflare WAFルールを個別最適化可能
- ✅ Elementorプレビューが正常動作
- ✅ 将来的なスケーラビリティ向上

**デメリット**:
- ⚠️ Cloudflare Tunnel設定を追加（14 → 最大24 Public Hostnames）
- ⚠️ DNS設定変更が必要
- ⚠️ WordPress siteurl/home の変更作業

**実装コスト**: 中（2-3日）

---

### 方針2: Nginxルーティング修正（一時対応）

現在のサブディレクトリ構成を維持しつつ、Nginx設定を修正:

**修正内容**:
```nginx
location /elementordemo1 {
    alias /var/www/html/kuma8088-elementordemo1;
    index index.php index.html;

    # 修正: SCRIPT_FILENAMEを正しく解決
    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        # Before: fastcgi_param SCRIPT_FILENAME $request_filename;
        # After:
        fastcgi_param SCRIPT_FILENAME /var/www/html/kuma8088-elementordemo1$fastcgi_script_name;
    }

    # Elementor Ajax対応
    location ~ /wp-admin/admin-ajax\.php$ {
        include fastcgi_params;
        fastcgi_pass wordpress:9000;
        fastcgi_param SCRIPT_FILENAME /var/www/html/kuma8088-elementordemo1/wp-admin/admin-ajax.php;
    }

    try_files $uri $uri/ @elementordemo1;
}

location @elementordemo1 {
    # 修正: リライトルール
    rewrite ^/elementordemo1(.*)$ /elementordemo1/index.php?$1 last;
}
```

**メリット**:
- ✅ ドメイン変更不要
- ✅ DNS設定変更不要
- ✅ 即座に適用可能

**デメリット**:
- ❌ 絶対URL問題は残る（別途wp-cli search-replaceが必要）
- ❌ Cloudflare WAF問題は解決しない
- ❌ 根本的な解決にならない（技術的負債）

**実装コスト**: 小（半日）

---

### 方針3: URL一括置換 + Cloudflare WAF調整（補完対応）

方針2と組み合わせて実施:

**URL一括置換**:
```bash
# 旧ドメイン → 新ドメイン
docker compose exec wordpress wp search-replace \
  'gwpbk492.xsrv.jp' \
  'blog.kuma8088.com/elementordemo1' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --allow-root

# ルート直下 → サブディレクトリ
docker compose exec wordpress wp search-replace \
  '/wp-content/' \
  '/elementordemo1/wp-content/' \
  --path=/var/www/html/kuma8088-elementordemo1 \
  --all-tables \
  --allow-root
```

**Cloudflare WAF調整**:
1. Elementor Ajax用のWAFルール例外設定
2. Bot Fight Modeの調整
3. プレビュー用URLパターンの許可リスト追加

**メリット**:
- ✅ 絶対URL問題を緩和
- ✅ Cloudflareブロックを回避

**デメリット**:
- ❌ データベース内のすべてのURLを正確に置換するのは困難
- ❌ Elementor生成CSSファイル内のURLは残る可能性
- ❌ 定期的なメンテナンスが必要

**実装コスト**: 中（1-2日）

---

## 📋 推奨実装計画

### Phase 011-A: 緊急対応（方針2）

**期間**: 半日
**目的**: 最低限の表示を確保

1. Nginx設定修正（SCRIPT_FILENAME, admin-ajax.php対応）
2. Nginx reload
3. 動作確認（各サイトのフロント表示）

### Phase 011-B: 中期対応（方針3）

**期間**: 1-2日
**目的**: 絶対URL問題とCloudflare WAF問題を緩和

1. 各サイトでwp-cli search-replace実行
2. Elementorキャッシュクリア
3. Cloudflare WAFルール調整
4. 動作確認（Elementorプレビュー含む）

### Phase 011-C: 恒久対応（方針1）★推奨

**期間**: 2-3日
**目的**: 根本的な解決

1. サブドメイン設計（elementordemo1.kuma8088.com等）
2. DNS設定追加（Cloudflare）
3. Cloudflare Tunnel設定追加（Public Hostnames）
4. Nginx設定変更（独立vhost化）
5. WordPress siteurl/home変更
6. データベース内URL一括置換
7. 動作確認（全機能）
8. 旧URL（サブディレクトリ）からのリダイレクト設定

---

## ⚠️ リスク評価

| リスク | 影響 | 確率 | 対策 |
|--------|------|------|------|
| Phase 011-C実装中のサイトダウンタイム | HIGH | LOW | 段階的移行、並行稼働期間設定 |
| DNS変更の伝播遅延 | MEDIUM | MEDIUM | TTL事前短縮、段階的切り替え |
| 旧URLブックマークの無効化 | MEDIUM | HIGH | リダイレクト設定（301 Permanent） |
| Cloudflare Tunnel Public Hostname上限 | LOW | LOW | 現在14/25、余裕あり |

---

## 📊 影響範囲

### ユーザー影響

- **現状**: Elementor編集機能が使用不可、表示崩れによりサイト品質低下
- **Phase 011-A後**: フロント表示改善、Elementor編集は制限あり
- **Phase 011-B後**: Elementor編集機能部分的に回復
- **Phase 011-C後**: 全機能正常化、パフォーマンス向上

### システム影響

- **Nginx**: 設定ファイル変更（kuma8088.conf）
- **Cloudflare**: Tunnel設定追加、DNS設定追加
- **WordPress**: siteurl/home変更、データベース内URL置換
- **影響サイト数**: 最大10サイト

---

## 🔗 関連ドキュメント

- [02_design.md](./02_design.md) - Nginx設計
- [04_migration.md](./04_migration.md) - URL置換手順
- [cloudflare-tunnel-hostnames.md](./cloudflare-tunnel-hostnames.md) - Tunnel設定
- [/opt/onprem-infra-system/project-root-infra/services/blog/config/nginx/conf.d/kuma8088.conf](../../services/blog/config/nginx/conf.d/kuma8088.conf) - Nginx設定ファイル

---

## 📝 次のステップ

1. **優先度判断**: Phase 011-A, B, Cのどれを実施するか決定
2. **影響調査**: kuma8088ルートサイトとtestサイトの状態確認
3. **テスト実施**: 各ドメイン配下の /test/ ディレクトリサイトで動作確認
   - blog.kuma8088.com/test/
   - blog.fx-trader-life.com/test/ (作成予定)
   - blog.webmakeprofit.org/test/ (作成予定)
   - blog.webmakesprofit.com/test/ (作成予定)
   - blog.toyota-phv.jp/test/ (作成予定)
4. **リソース確保**: 実装担当者とスケジュール調整
5. **承認**: Phase 011-C実施の場合、DNS/Cloudflare変更の承認取得

---

**起票者**: Claude Code (AI Assistant)
**最終更新**: 2025-11-10
