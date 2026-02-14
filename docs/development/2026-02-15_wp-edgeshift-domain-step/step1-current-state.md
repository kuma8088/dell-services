# Step 1: 現状把握 - 調査結果

> 調査日: 2026-02-15

---

## 1. edgeshift.tech の現在のDNS設定

### ネームサーバー

| NS | ホスト |
|----|--------|
| NS1 | bethany.ns.cloudflare.com |
| NS2 | anirban.ns.cloudflare.com |

→ **Cloudflare管理下**

### Aレコード / AAAAレコード

| 種別 | ホスト | 値 | TTL |
|------|--------|----|-----|
| A | edgeshift.tech | 104.21.45.140 | 300 |
| A | edgeshift.tech | 172.67.215.47 | 300 |
| AAAA | edgeshift.tech | 2606:4700:3033::ac43:d72f | 300 |
| AAAA | edgeshift.tech | 2606:4700:3035::6815:2d8c | 300 |

→ **Cloudflare Proxy（オレンジクラウド）経由**。IPはCloudflareのエッジサーバー。

### wwwサブドメイン

| 種別 | ホスト | 値 |
|------|--------|----|
| A | www.edgeshift.tech | 104.21.45.140 |
| A | www.edgeshift.tech | 172.67.215.47 |

→ ルートドメインと同じCloudflare Proxy経由

### MXレコード

| 優先度 | ホスト |
|--------|--------|
| 12 | route2.mx.cloudflare.net |
| 84 | route1.mx.cloudflare.net |
| 94 | route3.mx.cloudflare.net |

→ **Cloudflare Email Routing** 使用。Dell Mailserverへ転送される構成。

### TXTレコード

| レコード | 用途 |
|----------|------|
| `v=spf1 include:_spf.mx.cloudflare.net include:sendgrid.net include:amazonses.com ~all` | SPF（メール送信元認証） |
| `google-site-verification=5BbgnZvsXopm113awQnPBjRO8dY7Iv527TcB76KYcAs` | Google Search Console認証 |

### edgeshift.tech サブドメイン（Dell WP環境で使用中）

| サブドメイン | A/CNAME | 向き先 | 用途 |
|-------------|---------|--------|------|
| importtest4.edgeshift.tech | A (Proxied) | 104.21.45.140 / 172.67.215.47 | WPテストサイト |
| udemydemo02.edgeshift.tech | A (Proxied) | 104.21.45.140 / 172.67.215.47 | Udemy連携デモサイト |
| blog.edgeshift.tech | 未設定 | - | DNSレコードなし |
| mail.edgeshift.tech | 未設定 | - | DNSレコードなし |

---

## 2. 現行edgeshiftサイトのサーバー情報

| 項目 | 値 |
|------|----|
| 公開URL | https://edgeshift.tech |
| フレームワーク | **Astro v5.16.6** |
| 言語 | 日本語 (lang="ja") |
| サイト名 | EdgeShift |
| 説明 | 「DXでビジネスのエッジを変化させる」 |
| ホスティング | **Cloudflare Pages**（Cloudflare Proxy IP経由） |
| Webサーバー | cloudflare |
| レスポンスヘッダ | `cf-cache-status: DYNAMIC`, `cf-ray: NRT`（東京POP） |

→ 現行サイトは **Cloudflare Pages** 上でホスティングされているAstro製の静的サイト。Cloudflare Proxy背後にあるため、オリジンIPは外部から見えない。

### メールボックス（Dell Mailserver上に存在）

- `contact@edgeshift.tech` - 使用中（受信メールあり）
- `admin@edgeshift.tech` - 使用中（未読メールあり）

→ DNS切り替え時、**MXレコードは変更不要**（Cloudflare Email Routing → Dell Mailserver構成は維持）

---

## 3. Dell WP環境のドメイン・バーチャルホスト構成一覧

### 稼働中のバーチャルホスト（21サイト）

| # | 設定ファイル | server_name | ドメイン |
|---|-------------|-------------|----------|
| 1 | kuma8088.conf | kuma8088.com, www.kuma8088.com | kuma8088.com |
| 2 | fx-trader-life.conf | fx-trader-life.com, www.fx-trader-life.com | fx-trader-life.com |
| 3 | webmakeprofit.conf | webmakeprofit.org, www.webmakeprofit.org | webmakeprofit.org |
| 4 | webmakesprofit.conf | webmakesprofit.com, www.webmakesprofit.com | webmakesprofit.com |
| 5 | toyota-phv.conf | toyota-phv.jp, www.toyota-phv.jp | toyota-phv.jp |
| 6 | 4line-fx-trader-life.conf | 4line.fx-trader-life.com | fx-trader-life.com サブドメイン |
| 7 | lp-fx-trader-life.conf | lp.fx-trader-life.com | fx-trader-life.com サブドメイン |
| 8 | mfkc-fx-trader-life.conf | mfkc.fx-trader-life.com | fx-trader-life.com サブドメイン |
| 9 | coconala-webmakeprofit.conf | coconala.webmakeprofit.org | webmakeprofit.org サブドメイン |
| 10 | camera-kuma8088.conf | camera.kuma8088.com | kuma8088.com サブドメイン |
| 11 | demo1-kuma8088.conf | demo1.kuma8088.com | kuma8088.com サブドメイン |
| 12 | demo2-kuma8088.conf | demo2.kuma8088.com | kuma8088.com サブドメイン |
| 13 | demo3-kuma8088.conf | demo3.kuma8088.com | kuma8088.com サブドメイン |
| 14 | demo4-kuma8088.conf | demo4.kuma8088.com | kuma8088.com サブドメイン |
| 15 | ec-test-kuma8088.conf | ec-test.kuma8088.com | kuma8088.com サブドメイン |
| 16 | admin.kuma8088.com.conf | admin.kuma8088.com | kuma8088.com サブドメイン |
| 17 | learndash-test.conf | ldtest.kuma8088.com | kuma8088.com サブドメイン |
| 18 | elementor-agency-demo-site.conf | agencydemo.kuma8088.com | kuma8088.com サブドメイン |
| 19 | udemy-agency-demo-site01.conf | udemy-agency-demo1.kuma8088.com | kuma8088.com サブドメイン |
| 20 | **importtest4.conf** | **importtest4.edgeshift.tech** | **edgeshift.tech サブドメイン** |
| 21 | **udemy-demo-agency-01.conf** | **udemydemo02.edgeshift.tech** | **edgeshift.tech サブドメイン** |

### edgeshift.tech関連（既にDell WP環境で稼働中）

| サブドメイン | Nginx設定 | 状況 |
|-------------|-----------|------|
| importtest4.edgeshift.tech | importtest4.conf | Cloudflare Tunnel経由で公開中 |
| udemydemo02.edgeshift.tech | udemy-demo-agency-01.conf | Cloudflare Tunnel経由で公開中 |
| **edgeshift.tech（ルート）** | **未設定** | **WP側にバーチャルホストなし** |

### kuma8088.com サブディレクトリサイト

`kuma8088-subdirs-generated.inc` にサブディレクトリ型WPサイトのlocation設定が含まれている（kuma8088.conf から include）。

---

## 4. SSL証明書の状態

### edgeshift.tech（ルートドメイン）

| 項目 | 値 |
|------|----|
| 発行元 | Google Trust Services (WE1) |
| 対象ドメイン | edgeshift.tech |
| 発行日 | 2025-12-21 |
| **有効期限** | **2026-03-21** |
| 配信元 | Cloudflare Edge（Universal SSL相当） |

### www.edgeshift.tech

| 項目 | 値 |
|------|----|
| 発行元 | Google Trust Services (WE1) |
| 対象ドメイン | www.edgeshift.tech |
| 発行日 | 2025-12-21 |
| **有効期限** | **2026-03-21** |
| 配信元 | Cloudflare Edge |

### Dell WP環境のSSL

Dell WP環境のSSLは **Cloudflare Tunnel** 経由で提供されている。Tunnel利用のため、Dell側でのSSL証明書管理は不要（Cloudflare Edge → Tunnel → Nginx (HTTP)）。

→ edgeshift.techをDell WP環境に移行した場合も、Cloudflare Tunnel経由であればSSL証明書の個別取得は不要。

---

## 5. 移行に関する考慮事項

### 現行構成の概要図

```
[ブラウザ] → [Cloudflare Edge (SSL)] → [Cloudflare Pages] → Astro静的サイト
                                      → [Cloudflare Tunnel] → Dell Nginx → WP (importtest4, udemydemo02)
                                      → [Email Routing] → Dell Mailserver
```

### 移行後の想定構成

```
[ブラウザ] → [Cloudflare Edge (SSL)] → [Cloudflare Tunnel] → Dell Nginx → WP (edgeshift.tech)
                                      → [Cloudflare Tunnel] → Dell Nginx → WP (importtest4, udemydemo02)
                                      → [staging向き先]     → staging環境 (Astro)
                                      → [Email Routing] → Dell Mailserver（変更なし）
```

### 注意点

1. **Cloudflare Pages → Tunnel切り替え**: 現行のPages設定を解除し、Tunnel（CNAME）に切り替える必要がある
2. **MXレコード**: 変更不要（Cloudflare Email Routing構成は維持）
3. **TXTレコード**: SPF・Google Search Verification は変更不要
4. **SSL**: Cloudflare Tunnel経由のため、Dell側での証明書管理は不要
5. **既存edgeshift.techサブドメイン**: importtest4, udemydemo02 は既にTunnel経由でDellに向いているため影響なし
6. **メールボックス**: contact@, admin@ がDell Mailserver上に存在、影響なし
