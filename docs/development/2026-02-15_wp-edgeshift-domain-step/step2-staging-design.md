# Step 2: staging環境の設計提案

> 作成日: 2026-02-15
> ステータス: **Naoyaの意思決定待ち**

---

## 前提（Step 1調査結果より）

- 現行edgeshift.techは **Cloudflare Pages** 上のAstro静的サイト
- DNS・SSL・CDNはすべて **Cloudflare管理下**
- Dell WP環境へのアクセスは **Cloudflare Tunnel** 経由
- edgeshift.techサブドメイン（importtest4, udemydemo02）は既にTunnel経由で稼働中

---

## 1. staging用サブドメイン候補

### 候補A: `staging.edgeshift.tech`（推奨）

| 項目 | 内容 |
|------|------|
| メリット | 業界標準の命名。目的が一目瞭然。検索エンジンにインデックスされにくい慣例名 |
| デメリット | 特になし |
| 適性 | ★★★ |

### 候補B: `dev.edgeshift.tech`

| 項目 | 内容 |
|------|------|
| メリット | 短くて覚えやすい。開発継続の意図が明確 |
| デメリット | 「開発中」の印象が強く、クライアント向けの確認用に見せづらい。将来ローカル開発環境と混同する可能性 |
| 適性 | ★★☆ |

### 候補C: `v1.edgeshift.tech`

| 項目 | 内容 |
|------|------|
| メリット | 「初代サイト」のバージョニングとして明確。将来v2, v3と拡張できる |
| デメリット | 命名規則がプロジェクト独自で、チーム外の人にはわかりにくい |
| 適性 | ★☆☆ |

### 推奨: `staging.edgeshift.tech`

理由: 最も一般的で誤解がない。仕様書にも既に例示されており、関係者の認識が統一されている。

---

## 2. DNSレコード設計

### 現行構成（変更前）

```
edgeshift.tech     → Cloudflare Pages（Astroサイト）
www.edgeshift.tech → Cloudflare Pages（Astroサイト）
```

### 移行後の構成

```
edgeshift.tech          → Cloudflare Tunnel → Dell Nginx → WordPress（新規）
www.edgeshift.tech      → Cloudflare Tunnel → Dell Nginx → WordPress（新規）
staging.edgeshift.tech  → Cloudflare Pages（Astroサイト、現行サイト継続）
```

### 必要なDNSレコード

#### staging.edgeshift.tech（新規追加）

| 種別 | ホスト | 値 | Proxy | 備考 |
|------|--------|-----|-------|------|
| CNAME | staging | `[pages-project].pages.dev` | ON (Proxied) | Cloudflare Pagesのカスタムドメイン |

**設定手順**:
1. Cloudflare Pagesプロジェクトの「Custom domains」に `staging.edgeshift.tech` を追加
2. Cloudflare DNSに自動でCNAMEレコードが作成される
3. 既存の `edgeshift.tech` カスタムドメインをPagesから削除

→ **Cloudflare Pages側の操作だけで完結**。Astroサイトのビルド設定やデプロイパイプラインの変更は不要。

#### edgeshift.tech（変更 - Step 4/5で実施）

| 種別 | ホスト | 変更内容 | 備考 |
|------|--------|----------|------|
| A/AAAA | @ | Pages向き → Tunnel CNAME に変更 | Step 5で実施 |
| CNAME | www | Pages向き → Tunnel CNAME に変更 | Step 5で実施 |

#### 変更不要なレコード

| 種別 | ホスト | 理由 |
|------|--------|------|
| MX | @ | Cloudflare Email Routing → Dell Mailserver は維持 |
| TXT (SPF) | @ | メール送信元認証は変更なし |
| TXT (Google) | @ | Search Console認証は維持 |
| A | importtest4 | 既存サブドメイン、影響なし |
| A | udemydemo02 | 既存サブドメイン、影響なし |

---

## 3. アクセス制限方式の比較

### 選択肢

| 方式 | 実装場所 | コスト | セットアップ | 柔軟性 |
|------|----------|--------|-------------|--------|
| **Cloudflare Access** | Cloudflare Edge | 無料（50ユーザーまで） | 簡単 | ★★★ |
| Basic認証 | Cloudflare Pages Functions or _headers | 無料 | やや複雑 | ★★☆ |
| IP制限 | Cloudflare WAF | 無料 | 簡単 | ★☆☆ |

### 詳細比較

#### A. Cloudflare Access（推奨）

```
アクセスフロー:
[ブラウザ] → [Cloudflare Edge] → [Access認証画面] → [メールOTP or Google認証] → [Pages]
```

| 項目 | 内容 |
|------|------|
| 認証方法 | メールOTP（ワンタイムパスコード）/ Google / GitHub等 |
| 設定場所 | Cloudflare Zero Trust ダッシュボード |
| メリット | サイト側の改修不要。認証がEdgeで完結。複数認証方式を選択可能。ログイン履歴が残る |
| デメリット | Cloudflare Zero Trustの初期設定が必要（一度だけ） |
| 推奨理由 | **既にCloudflare管理下のため最も自然な選択。Astroサイトのコードを一切変更せずに適用可能** |

#### B. Basic認証

| 項目 | 内容 |
|------|------|
| 認証方法 | ユーザー名 + パスワード |
| 設定場所 | Cloudflare Pages Functions or `_headers` ファイル |
| メリット | シンプルで理解しやすい |
| デメリット | Cloudflare Pagesでのネイティブ対応なし（Functionsでの実装が必要）。パスワード管理が煩雑。ブラウザキャッシュで意図しないログイン状態になることがある |

#### C. IP制限

| 項目 | 内容 |
|------|------|
| 認証方法 | 送信元IPアドレスのホワイトリスト |
| 設定場所 | Cloudflare WAF Rules |
| メリット | 認証なしでアクセス可能（許可IP内なら） |
| デメリット | **自宅IP変動時にアクセス不能になる**。外出先・モバイルからアクセスできない。VPN使用時に設定変更が必要 |

### 推奨: Cloudflare Access（メールOTP方式）

**理由**:
1. Astroサイトのコード変更が一切不要
2. Cloudflare管理下のため設定がダッシュボードで完結
3. 無料枠（50ユーザー）で十分
4. 場所を問わずアクセス可能（IP固定不要）
5. アクセスログが自動的に記録される

**設定イメージ**:
- 保護対象: `staging.edgeshift.tech/*`
- 許可ポリシー: 指定メールアドレス（例: naoya@edgeshift.tech）にOTPを送信
- セッション有効期限: 24時間（調整可能）

---

## まとめ（決定事項候補）

| 項目 | 推奨案 | 決定 |
|------|--------|------|
| stagingドメイン | `staging.edgeshift.tech` | ☐ Naoya承認待ち |
| DNS設定方式 | Cloudflare PagesのCustom Domain追加（CNAMEレコード自動作成） | ☐ Naoya承認待ち |
| アクセス制限 | Cloudflare Access（メールOTP） | ☐ Naoya承認待ち |

### 次のアクション（承認後）

1. **Mac側CC**: Cloudflare PagesプロジェクトにCustom Domain `staging.edgeshift.tech` を追加
2. **Mac側CC**: Cloudflare Accessポリシーを `staging.edgeshift.tech` に適用
3. **Dell側CC**: Step 3以降のWP環境受け入れ準備に進む

> **注意**: staging側の作業（Cloudflare Pages/Access設定）は主にMac側CCの担当範囲です。Dell側CCはDNS設計の支援と、Step 4以降のWP環境構築を担当します。
