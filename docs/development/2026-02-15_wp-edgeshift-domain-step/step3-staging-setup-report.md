# Step 3: staging環境セットアップ - 進捗報告

> 作成日: 2026-02-15
> ステータス: **Naoya / Mac側CC の作業待ち**

---

## 実施結果サマリー

| # | タスク | 状況 | 担当 |
|---|--------|------|------|
| 1 | DNSレコード追加 | ✅ 完了 | Dell側CC |
| 2 | Cloudflare Pages Custom Domain登録 | ❌ 未完了（権限不足） | **Naoya / Mac側CC** |
| 3 | SSL証明書 | ⏳ Custom Domain登録後に自動取得 | 自動 |
| 4 | アクセス制限（Cloudflare Access） | ⏳ 未実施 | **Naoya** |

---

## 1. DNSレコード追加 ✅ 完了

Cloudflare DNS APIで以下のレコードを追加済み。

| 項目 | 値 |
|------|----|
| レコードID | `49f23659b21dc2c9a87131aa68e3c8ae` |
| 種別 | CNAME |
| ホスト | staging.edgeshift.tech |
| 向き先 | edgeshift.pages.dev |
| Proxy | ON (Proxied) |
| TTL | Auto |

名前解決確認:
```
staging.edgeshift.tech → 104.21.45.140, 172.67.215.47（Cloudflare Proxy IP）
```

→ DNS層は正常に動作。

---

## 2. Cloudflare Pages Custom Domain登録 ❌ 要手動設定

### 現状

`https://staging.edgeshift.tech` にアクセスすると **HTTP 522** エラーが発生。

### 原因

DNSレコードだけではCloudflare Pagesがリクエストをルーティングできない。PagesプロジェクトにCustom Domainとして `staging.edgeshift.tech` を登録する必要がある。

Dell側のCloudflare APIトークンにはPages権限がないため、この操作はDell側CCでは実行不可。

### Naoya / Mac側CC への依頼手順

**Cloudflareダッシュボードで以下を実施してください:**

1. [Cloudflareダッシュボード](https://dash.cloudflare.com) にログイン
2. 左メニュー「Workers & Pages」を選択
3. `edgeshift` プロジェクトを開く
4. 「Custom domains」タブを選択
5. 「Set up a custom domain」をクリック
6. `staging.edgeshift.tech` を入力
7. DNSレコードは既に作成済みなので「Activate domain」で完了

**所要時間**: 1〜2分（DNS確認は即時、SSL証明書発行は最大15分）

---

## 3. SSL証明書 ⏳ 自動取得

Cloudflare PagesのCustom Domain登録が完了すると、SSL証明書は自動的に発行される。

- 発行元: Cloudflare（またはGoogle Trust Services）
- 種別: Universal SSL（Edge Certificate）
- 対象: staging.edgeshift.tech
- 期間: 自動更新

Dell側での証明書管理は不要。

---

## 4. アクセス制限（Cloudflare Access） ⏳ 未実施

### Naoya への依頼手順

**Cloudflare Zero Trustダッシュボードで以下を実施してください:**

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com) にアクセス
2. 初回の場合: チーム名を設定（例: `edgeshift`）→ Free planを選択
3. 「Access」→「Applications」→「Add an application」
4. 「Self-hosted」を選択
5. 設定値:

| 項目 | 値 |
|------|----|
| Application name | EdgeShift Staging |
| Application domain | staging.edgeshift.tech |
| Session Duration | 24 hours |

6. 「Add a policy」:

| 項目 | 値 |
|------|----|
| Policy name | Allow Owner |
| Action | Allow |
| Include - Emails | （自分のメールアドレス） |

7. 保存

**動作**: `staging.edgeshift.tech` にアクセス → Cloudflare認証画面 → メールOTP入力 → サイト表示

---

## 確認チェックリスト（全手順完了後）

```
[ ] staging.edgeshift.tech の名前解決が正常
    → dig staging.edgeshift.tech A +short
[ ] https://staging.edgeshift.tech でAstroサイトが表示される
[ ] SSL証明書エラーなし
[ ] Cloudflare Access認証画面が表示される（アクセス制限が有効）
[ ] 認証後、現行edgeshift.techと同じサイトが表示される
```

---

## Dell側CCが追加で対応可能なこと

Naoya / Mac側CCの作業完了後、必要であれば:
- staging環境のHTTPSアクセス確認
- DNSレコードの修正（向き先変更等）
- Cloudflare Tunnel側の設定変更（将来的にPages以外に移す場合）
