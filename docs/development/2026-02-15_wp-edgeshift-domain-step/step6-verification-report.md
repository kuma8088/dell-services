# Step 6: 動作確認結果

> 確認日: 2026-02-15
> 担当: Dell側CC
> ステータス: **✅ 完了**

---

## 確認結果サマリー

| # | 確認項目 | 結果 | 備考 |
|---|----------|------|------|
| 1 | edgeshift.tech 名前解決 | ✅ OK | 104.21.45.140 / 172.67.215.47（Cloudflare Proxy IP） |
| 2 | `https://edgeshift.tech` WPサイト表示 | ✅ OK | HTTP/2 200、タイトル「EdgeShift」 |
| 3 | SSL証明書 | ✅ OK | Cloudflare Edge Certificate（エラーなし） |
| 4 | HTTP→HTTPSリダイレクト | ✅ OK | Cloudflare側で処理（Always Use HTTPS） |
| 5 | WP管理画面アクセス | ✅ OK | `/wp-admin/` → `wp-login.php` にリダイレクト |
| 6 | www.edgeshift.tech リダイレクト | ✅ OK | 301 → `https://edgeshift.tech`（Nginx設定追加で対応） |
| 7 | staging.edgeshift.tech 表示 | ✅ OK | HTTP/2 200（Astroサイト） |
| 8 | MXレコード（メール受信） | ✅ 変更なし | Cloudflare Email Routing → Dell Mailserver構成を維持 |

---

## 1. DNS名前解決

```
$ dig edgeshift.tech @1.1.1.1 A +short
104.21.45.140
172.67.215.47

$ dig www.edgeshift.tech @1.1.1.1 A +short
104.21.45.140
172.67.215.47

$ dig staging.edgeshift.tech @1.1.1.1 A +short
104.21.45.140
172.67.215.47
```

全ドメインがCloudflare Proxy IPを返却。正常。

---

## 2. HTTPS アクセス確認

### edgeshift.tech（本番 → WordPress）

```
HTTP/2 200
content-type: text/html; charset=UTF-8
server: cloudflare
cf-ray: 9ce0228f2cbf48e5-NRT
<title>EdgeShift</title>
```

Cloudflare Tunnel → Dell Nginx → WordPress で正常にレスポンス。

### www.edgeshift.tech（リダイレクト）

```
HTTP/2 301
location: https://edgeshift.tech/
server: cloudflare
cf-ray: 9ce025a5692bd805-NRT
```

Nginx の server block で301リダイレクト。SEO的にも正しい構成。

### staging.edgeshift.tech（現行Astroサイト）

```
HTTP/2 200
content-type: text/html
server: cloudflare
cf-ray: 9ce022972819e385-NRT
```

Cloudflare Pages経由で現行Astroサイトが表示。

---

## 3. WP管理画面

```
$ curl -sI https://edgeshift.tech/wp-admin/
HTTP/2 302
location: https://edgeshift.tech/wp-login.php?redirect_to=https%3A%2F%2Fedgeshift.tech%2Fwp-admin%2F&reauth=1
```

ログイン画面に正しくリダイレクト。URLもedgeshift.techドメインで統一されている。

---

## 4. メール（影響なし確認）

| 項目 | 状態 |
|------|------|
| MXレコード | route1/2/3.mx.cloudflare.net（変更なし） |
| SPFレコード | `v=spf1 include:_spf.mx.cloudflare.net include:sendgrid.net include:amazonses.com ~all`（変更なし） |
| メールボックス | contact@edgeshift.tech, admin@edgeshift.tech（Dell Mailserver上、影響なし） |

---

## 5. 移行中に対応した問題

### www.edgeshift.tech 不正リダイレクト

- **症状**: `www.edgeshift.tech` が `4line.fx-trader-life.com` にリダイレクトされる
- **原因**: Nginx側に `www.edgeshift.tech` のバーチャルホストが未設定、デフォルトserver blockに当たった
- **対応**: `edgeshift.conf` に www → non-www 301リダイレクト用 server block を追加
- **結果**: 正常にリダイレクト動作を確認

### DNS 1016エラー（一時的）

- **症状**: Pages Custom Domain削除直後に Error 1016（Origin DNS error）が発生
- **原因**: Pages Custom Domain削除時にDNSレコードのName が `@`（ルート）ではなく `edgeshift`（= edgeshift.edgeshift.tech）で設定されていた
- **対応**: CNAMEレコードの Name を `@` に修正
- **結果**: 数分でブラウザDNSキャッシュが更新され正常アクセス可能に

---

## 6. 最終構成

```
[ブラウザ] → [Cloudflare Edge (SSL)]
    │
    ├─ edgeshift.tech          → [Cloudflare Tunnel] → Dell Nginx → WordPress ✅
    ├─ www.edgeshift.tech      → [Cloudflare Tunnel] → Dell Nginx → 301 → edgeshift.tech ✅
    ├─ staging.edgeshift.tech  → [Cloudflare Pages]  → Astroサイト ✅
    ├─ importtest4.edgeshift.tech → [Cloudflare Tunnel] → Dell Nginx → WP ✅（既存・変更なし）
    ├─ udemydemo02.edgeshift.tech → [Cloudflare Tunnel] → Dell Nginx → WP ✅（既存・変更なし）
    ├─ images.edgeshift.tech   → [Cloudflare R2]     → 画像配信 ✅（変更なし）
    ├─ /api/* (Worker routes)  → [Cloudflare Worker] → Newsletter/Contact API ✅（変更なし）
    └─ MX                     → [Email Routing]     → Dell Mailserver ✅（変更なし）
```

---

## 7. 完了定義の照合

| 完了条件（仕様書より） | 結果 |
|------------------------|------|
| `https://edgeshift.tech` → WPサイト表示 | ✅ |
| `https://staging.edgeshift.tech` → 現行サイト表示 | ✅ |
| SSL証明書エラーなし | ✅ |
| 名前解決が正常 | ✅ |

**全完了条件を満たしています。**

---

## 残作業（スコープ外・後続対応）

| 項目 | 優先度 | 備考 |
|------|--------|------|
| Cloudflare Access（staging アクセス制限） | Low | 現時点では誰でもstagingにアクセス可能 |
| WPサイトのコンテンツ制作・テーマ構築 | - | 仕様書のスコープ外 |
| SEOリダイレクト（旧Astroページ → WP） | Medium | 必要に応じて別途対応 |
| テスト・Terraform・ドキュメントのドメイン更新 | Low | Mac側カテゴリD〜F（後続対応） |
