# edgeshift.tech ドメイン移行仕様書

## 概要

edgeshift.tech（オリジンドメイン）をWordPress環境で利用するため、現行のedgeshiftサイトをstagingへ移行し、WPがedgeshift.techで公開できる状態にする。

## 背景・目的

- 現行edgeshiftサイト（Claude Code構築）は開発コストが高く、ビジネス速度に合わない
- 「売る」部分はWPで迅速に構築・運用する
- 現行サイトはstaging環境として開発継続可能な状態を維持する

## 対象環境

| 項目 | パス / 情報 |
|------|------------|
| WP環境（Dell） | `/Users/naoya/srv/workspace/prod/dell-services` |
| edgeshift（現行） | `/Users/naoya/srv/workspace/dev/edgeshift` |
| edgeshift-premium | `/Users/naoya/srv/workspace/dev/edgeshift-premium` |
| オリジンドメイン | edgeshift.tech |

## 担当分担

| 担当CC | 役割 |
|--------|------|
| Mac側CC | edgeshiftアプリ構築（staging移行作業） |
| Dell側CC | WP基盤構築（ドメイン受け入れ・名前解決） |

---

## ステップ定義

### Step 1: 現状把握

**要件:**

- 現行edgeshift.techのDNS設定（Aレコード、CNAMEなど）の現状を確認する
- 現行サイトがどのサーバー・IPで公開されているか特定する
- WP環境（dell-services）の現在のドメイン設定・バーチャルホスト構成を確認する
- SSL証明書の現状（発行元、有効期限、対象ドメイン）を確認する

**完了条件:** 現行構成の一覧が文書化されていること

**担当:** Dell側CC

**CCプロンプト（Dell側CC）:**

> 以下の現状を調査して、結果を一覧で報告して。コマンド実行結果をそのまま貼るのではなく、整理した形で出して。
>
> 1. edgeshift.techの現在のDNS設定（Aレコード、CNAME、MX、TXTなど全レコード）
> 2. 現行edgeshiftサイトが公開されているサーバーのIPアドレスとホスト情報
> 3. dell-services内のWP環境で現在設定されているドメイン・バーチャルホスト構成の一覧
> 4. edgeshift.techに関連するSSL証明書の状態（発行元、有効期限、対象ドメイン）
>
> 調査結果はこの仕様書と同じディレクトリに `step1-current-state.md` として保存して。

---

### Step 2: staging環境の定義

**要件:**

- 現行edgeshiftサイトで使用するstagingドメインを決定する（例: staging.edgeshift.tech, dev.edgeshift.tech など）
- stagingドメインのDNSレコードを設計する
- staging環境のアクセス制限方針を決定する（Basic認証、IP制限など）

**完了条件:** stagingドメイン名とDNS設計が確定していること

**担当:** Naoya（意思決定） → Dell側CC（DNS設計支援）

**CCプロンプト（Dell側CC）:**

> Step 1の調査結果を踏まえて、以下を提案して。
>
> 1. staging用サブドメインの候補を2〜3案出して、それぞれのメリット・デメリットを簡潔に説明して
> 2. 選定したstagingドメインに必要なDNSレコードの設計（レコード種別、向き先の考え方）を示して
> 3. staging環境のアクセス制限方式の選択肢（Basic認証、IP制限など）を比較して推奨案を出して
>
> 提案内容は `step2-staging-design.md` として保存して。最終決定は私が行う。

---

### Step 3: 現行edgeshiftサイトのstaging移行

**要件:**

- 現行edgeshiftサイトをstagingドメインで名前解決できるようにする
- 現行サイトの機能がstaging環境で正常動作すること
- staging環境にアクセス制限を適用すること

**完了条件:** stagingドメインで現行サイトが表示・動作確認できること

**担当:** Mac側CC（アプリ設定変更） / Dell側CC（DNS・サーバー設定）

**CCプロンプト（Dell側CC）:**

> Step 2で確定したstagingドメイン `[staging.edgeshift.tech ]` を名前解決できるようにして。
>
> 1. stagingドメインのDNSレコードを追加して、現行edgeshiftサイトのサーバーに向けて
> 2. Webサーバー側でstagingドメインのバーチャルホスト設定を追加して
> 3. stagingドメイン用のSSL証明書を取得・設定して
> 4. Step 2で決定したアクセス制限を適用して
>
> 設定完了後、stagingドメインでHTTPSアクセスできることを確認して結果を報告して。

**CCプロンプト（Mac側CC）:**

> 現行edgeshiftアプリの設定で、ドメインやURLをハードコードしている箇所を調査して。
>
> 1. edgeshift.techをハードコードしている全ファイル・全箇所を一覧で出して
> 2. stagingドメイン `[staging.edgeshift.tech ]` でも正常動作するよう、環境変数やConfig分離が必要な箇所を特定して
> 3. 必要な設定変更を行い、stagingドメインで動作確認して結果を報告して
>
> 変更前に変更予定の一覧を私に確認してから実施して。

---

### Step 4: WP環境のedgeshift.tech受け入れ準備

**要件:**

- WP環境のWebサーバー（Apache/Nginx）でedgeshift.techをホストとして受け入れる設定を行う
- WPのサイトURL設定をedgeshift.techに合わせる
- SSL証明書をedgeshift.tech用に取得・設定する（Let's Encrypt等）

**完了条件:** WP環境がedgeshift.techでリクエストを受け付ける準備が完了していること

**担当:** Dell側CC

**CCプロンプト（Dell側CC）:**

> WP環境でedgeshift.techを受け入れる準備をして。DNS切り替えはまだ行わない。
>
> 1. Webサーバーにedgeshift.techのバーチャルホスト設定を追加して
> 2. WordPressのサイトURL・ホームURLをedgeshift.techに設定して
> 3. edgeshift.tech用のSSL証明書を取得・設定して（DNS認証が使えない場合は、DNS切り替え後に取得する手順を準備して）
> 4. WP環境にedgeshift.techでアクセスした場合の想定動作を確認して報告して
>
> この時点ではDNSは切り替えないので、hostsファイルやローカルでの動作確認方法も提示して。

---

### Step 5: DNS切り替え

**要件:**

- edgeshift.techのDNSレコードをWP環境のIPアドレスに向ける
- TTLを事前に短縮し、切り替え時の影響を最小化する
- 切り替え前にTTL短縮の浸透を待つ

**完了条件:** DNSレコードがWP環境を指していること

**担当:** Dell側CC（DNS変更） / Naoya（ドメインレジストラ操作が必要な場合）

**CCプロンプト（Dell側CC）:**

> DNS切り替えの準備と実行をして。以下の順序で進めて。
>
> 1. まずedgeshift.techのTTLを短縮して（300秒程度）、浸透を待つ必要がある旨を報告して
> 2. TTL短縮の浸透確認後、私に「DNS切り替え実行OK」の承認を求めて
> 3. 承認後、edgeshift.techのAレコードをWP環境のIPアドレスに変更して
> 4. 切り替え後、DNSの浸透状況を確認して報告して
>
> レジストラ側での操作が必要な場合は、私に操作手順（画面ベース）を指示して。自分では操作しないで。

---

### Step 6: 動作確認

**要件:**

- edgeshift.techでWPサイトが表示されること
- SSL（HTTPS）で正常にアクセスできること
- staging環境の現行サイトが引き続き正常動作すること
- 主要ページ・機能の疎通確認を行うこと

**完了条件:** 以下がすべてOK

- `https://edgeshift.tech` → WPサイト表示
- `https://staging.edgeshift.tech`（または決定したstaging URL） → 現行サイト表示
- SSL証明書エラーなし
- 名前解決が正常

**担当:** Naoya（最終確認） / 各CC（技術確認）

**CCプロンプト（Dell側CC）:**

> DNS切り替え後の動作確認をして。以下をすべてチェックして結果を一覧で報告して。
>
> 1. edgeshift.techの名前解決がWP環境のIPを返すこと
> 2. `https://edgeshift.tech` でWPサイトが正常表示されること
> 3. SSL証明書がedgeshift.tech用として有効であること（エラーなし）
> 4. HTTPからHTTPSへのリダイレクトが正常に動作すること
> 5. WP管理画面にedgeshift.techドメインでアクセスできること
>
> 問題があれば切り戻し手順とともに報告して。

**CCプロンプト（Mac側CC）:**

> staging環境の動作確認をして。以下をチェックして結果を報告して。
>
> 1. stagingドメインで現行edgeshiftサイトが正常表示されること
> 2. SSL証明書がstaging用として有効であること
> 3. アクセス制限が正常に機能していること
> 4. 主要機能（ページ遷移、API通信など）が正常動作すること
>
> 問題があれば詳細と影響範囲を報告して。

---

## 完了定義（全体）

WP側でedgeshift.techにアクセスした際にWordPressサイトが表示され、名前解決が正常に行われること。

## スコープ外

- WPサイトのコンテンツ制作・テーマ構築
- 現行edgeshiftサイトの機能追加・改修
- SEOリダイレクト設定（必要に応じて別途対応）
- メールサーバー設定の変更（影響がある場合は別途検討）