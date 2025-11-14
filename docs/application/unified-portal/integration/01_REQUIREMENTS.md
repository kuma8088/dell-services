# 実装要件書

**プロジェクト**: Unified Portal - Mailserver統合 + DNS管理強化

**バージョン**: 1.0

**作成日**: 2025-11-14

---

## 1. ビジネス要件

### 1.1 背景
現在、Blog SystemとMailserverの管理が分離されており、運用効率が低下している。

**現状**:
- Mailserver: Flask usermgmt（http://172.20.0.80:5000）
- Blog: Unified Portal（開発中、DNS管理のみ実装済み）
- ドメイン管理: Cloudflare（Web UIで手動操作）

**課題**:
- 管理画面が分散（Flask、Cloudflare、未実装機能多数）
- 操作が煩雑（複数システムを切り替え）
- 監視・ログが統一されていない

### 1.2 目的
統一された管理ポータルを構築し、全システムを一元管理する。

**期待効果**:
- 運用時間 50%削減
- 操作ミス防止
- 監視・アラート統合
- モダンなUI/UX（Xserver風）

---

## 2. 機能要件

### 2.1 Phase 1: Mailserver機能統合（最優先）

#### 2.1.1 メールユーザー管理
**機能ID**: `MAIL-USER-001`

**要件**:
- ユーザー一覧表示（ページング、ソート、検索）
- ユーザー作成（email、password、domain、quota）
- ユーザー編集（quota、enabled）
- ユーザー削除（確認ダイアログ付き）
- パスワード変更（管理者による変更）
- 有効/無効切替（トグルボタン）

**データ項目**:
| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| email | string | ✓ | メールアドレス（ユニーク） |
| password | string | ✓ | パスワード（SHA512-CRYPT） |
| domain_id | integer | ✓ | 所属ドメインID |
| quota | integer | ✓ | メール容量（MB）、デフォルト1024 |
| maildir | string | ✓ | メールディレクトリパス（自動生成） |
| uid/gid | integer | ✓ | Unix UID/GID（固定5000） |
| enabled | boolean | ✓ | 有効/無効フラグ |
| is_admin | boolean | ✓ | 管理者フラグ |

**既存システムとの互換性**:
- Flask usermgmtと同じテーブル（`users`）を使用
- パスワードハッシュアルゴリズム: SHA512-CRYPT（Dovecot互換）
- maildir形式: `/var/mail/vmail/{domain}/{username}/`

#### 2.1.2 メールドメイン管理
**機能ID**: `MAIL-DOMAIN-001`

**要件**:
- ドメイン一覧表示（ユーザー数、quota合計）
- ドメイン作成（name、description、default_quota）
- ドメイン編集（description、default_quota、enabled）
- ドメイン削除（所属ユーザーがいる場合は警告）

**データ項目**:
| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| name | string | ✓ | ドメイン名（ユニーク） |
| description | string | | 説明 |
| default_quota | integer | ✓ | デフォルトquota（MB） |
| enabled | boolean | ✓ | 有効/無効フラグ |

#### 2.1.3 監査ログ
**機能ID**: `MAIL-AUDIT-001`

**要件**:
- 全操作のログ記録（作成、更新、削除、パスワード変更）
- ログ一覧表示（日時、操作者、操作内容、対象ユーザー）
- ログ検索・フィルタ（日付範囲、操作種別、ユーザー）
- ログエクスポート（CSV）

**データ項目**:
| 項目 | 型 | 説明 |
|------|-----|------|
| action | string | 操作種別（create, update, delete, password_change） |
| user_email | string | 対象ユーザー |
| admin_ip | string | 操作者IP/識別子 |
| details | text | 詳細（JSON） |
| created_at | datetime | 操作日時 |

#### 2.1.4 管理者管理
**機能ID**: `ADMIN-USER-001`

**要件**:
- 管理者ユーザー一覧表示
- 管理者ユーザー作成（email、password、権限レベル）
- 管理者ユーザー削除
- 管理者権限レベル設定（Super Admin, Admin, Editor, Viewer）
- 管理者アカウントの有効/無効切替

**データ項目**:
| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| email | string | ✓ | 管理者メールアドレス（ユニーク） |
| password_hash | string | ✓ | パスワード（bcrypt） |
| role | string | ✓ | 権限レベル（super_admin, admin, editor, viewer） |
| enabled | boolean | ✓ | 有効/無効フラグ |
| last_login | datetime | | 最終ログイン日時 |
| created_at | datetime | ✓ | 作成日時 |

**権限レベル定義**:
- **Super Admin**: 全機能アクセス可能、管理者管理可能
- **Admin**: メールユーザー・ドメイン・DNS管理可能
- **Editor**: 参照・編集可能、削除不可
- **Viewer**: 参照のみ

#### 2.1.5 パスワード再設定機能
**機能ID**: `PASSWORD-RESET-001`

**要件**:
- パスワード再設定リクエスト（メールアドレス入力）
- リセットトークン生成（セキュアランダム、有効期限1時間）
- リセットリンク付きメール送信（Mailserver経由）
- トークン検証（有効期限、使用済みチェック）
- 新パスワード設定
- 成功通知メール送信

**メール送信要件**:
- SMTPサーバー: Mailserver（Postfix、172.20.0.20:25）
- From: `noreply@kuma8088.com`
- 件名: `[Unified Portal] パスワード再設定のご案内`
- 本文: リセットリンク（`https://admin.kuma8088.com/reset-password?token=<token>`）
- HTMLメール対応

**データ項目**（password_reset_tokens テーブル）:
| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| id | integer | ✓ | トークンID |
| email | string | ✓ | 対象メールアドレス |
| token | string | ✓ | リセットトークン（UUID） |
| expires_at | datetime | ✓ | 有効期限（1時間後） |
| used_at | datetime | | 使用日時（NULL=未使用） |
| created_at | datetime | ✓ | 作成日時 |

**セキュリティ要件**:
- トークンは暗号学的に安全な乱数（UUID v4）
- トークンはハッシュ化してDB保存
- 有効期限切れトークンは拒否
- 使用済みトークンは再利用不可
- レート制限（同一メールアドレス: 5分間に1回まで）

---

### 2.2 Phase 2: DNS管理強化（#017）

#### 2.2.1 Cloudflareダッシュボードリンク
**機能ID**: `DNS-LINK-001`

**要件**:
- 各ゾーンに「Cloudflareで管理」ボタン追加
- クリックで新規タブでCloudflareダッシュボードを開く
- URL: `https://dash.cloudflare.com/{zone_id}/dns`

#### 2.2.2 DNSレコード編集
**機能ID**: `DNS-EDIT-001`

**要件**:
- 既存レコードの編集（現在は削除のみ実装済み）
- 編集項目: type, name, content, ttl, proxied
- バリデーション（Cloudflare API仕様に準拠）

#### 2.2.3 バルク操作
**機能ID**: `DNS-BULK-001`

**要件**:
- 複数レコード一括削除（チェックボックス選択）
- CSVエクスポート（全レコード）
- CSVインポート（検証付き）

#### 2.2.4 DNS検証ツール
**機能ID**: `DNS-VERIFY-001`

**要件**:
- dig/nslookup相当の機能（バックエンドでsubprocess実行）
- DNS伝播状況確認（複数DNSサーバーへクエリ）
- 結果表示（レスポンスタイム、TTL、値）

---

### 2.3 Phase 3: 追加機能（中期実装）

#### 2.3.1 認証統一
**機能ID**: `AUTH-001`

**要件**:
- JWT認証（アクセストークン + リフレッシュトークン）
- HTTPOnly Cookie使用（XSS対策）
- ロールベースアクセス制御（Admin, Editor, Viewer）
- セッション管理（複数デバイス対応）

#### 2.3.2 Docker Management
**機能ID**: `DOCKER-001`

**要件**:
- コンテナ一覧（ステータス、リソース使用率）
- コンテナ操作（起動、停止、再起動）
- ログ表示（リアルタイムストリーミング）
- イメージ管理（一覧、削除）

#### 2.3.3 WordPress Management
**機能ID**: `WP-001`

**要件**:
- サイト一覧表示（16サイト、ドメイン・DB・PHPバージョン表示）
- **新規サイト作成ウィザード**:
  - サイト名・ドメイン入力
  - **データベース選択**:
    - Option 1: 自動作成（wp_<site_name>）
    - Option 2: 既存DB選択（Database管理で事前作成）
  - **PHPバージョン選択**（7.4, 8.0, 8.1, 8.2）
  - WordPress自動インストール
  - WP Mail SMTP自動設定
- **サイト設定編集**:
  - ドメイン変更
  - **PHPバージョン切り替え**（ドロップダウン選択）
  - データベース変更（切り替え）
  - 有効/無効切替
- プラグイン/テーマ管理（wp-cli経由）
- WP Mail SMTP一括設定
- バックアップ/リストア

**データ項目**（wordpress_sites テーブル）:
| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| id | integer | ✓ | サイトID |
| site_name | string | ✓ | サイト名（例: kuma8088） |
| domain | string | ✓ | ドメイン名（例: kuma8088.com） |
| database_name | string | ✓ | データベース名（例: wp_kuma8088） |
| **php_version** | string | ✓ | PHPバージョン（例: 8.2） |
| enabled | boolean | ✓ | 有効/無効フラグ |
| created_at | datetime | ✓ | 作成日時 |
| updated_at | datetime | ✓ | 更新日時 |

**PHPバージョン切り替え仕様**:
- サポートバージョン: 7.4, 8.0, 8.1, 8.2
- 変更時の動作:
  1. wordpress_sites.php_versionを更新
  2. Nginx設定ファイル自動生成（fastcgi_pass変更）
  3. nginx -s reload実行（ダウンタイムなし）
  4. 監査ログ記録
- バリデーション: 選択したPHPバージョンのコンテナが起動していること

#### 2.3.4 Database Management（汎用DB管理ツール）
**機能ID**: `DB-001`

**要件**:
- **複数データベース対応**:
  - Blog用MariaDB（172.20.0.30:3306、16個のWordPress DB）
  - Mailserver用MariaDB（172.20.0.60:3306、mailserver_usermgmt）
- **データベース一覧表示**:
  - DB名、サイズ、テーブル数、文字セット
  - 接続先（Blog/Mailserver）別タブ表示
  - 検索・フィルタ機能
- **新規データベース作成**:
  - DB名入力（バリデーション: 英数字_のみ）
  - 文字セット選択（utf8mb4推奨）
  - 接続先選択（Blog/Mailserver）
  - 自動でDBユーザー作成（DB名と同じユーザー名）
- **データベース削除**:
  - 確認ダイアログ（DB名入力必須）
  - 関連DBユーザーも削除
  - WordPress使用中の場合は警告
- **データベースユーザー管理**:
  - ユーザー一覧（ユーザー名、ホスト、権限）
  - 新規ユーザー作成
  - パスワード変更
  - 権限変更（SELECT, INSERT, UPDATE, DELETE等）
  - ユーザー削除
- **SQLクエリ実行**（制限付き）:
  - SELECT文のみ許可（デフォルト）
  - INSERT/UPDATE/DELETE: Super Adminのみ
  - DROP/ALTER: 実行不可（安全性）
  - クエリ履歴表示
  - 結果をCSVエクスポート

**データベース認証**:
- **専用管理ユーザー**: `portal_admin`（Blog用・Mailserver用それぞれ作成）
- 権限:
  ```sql
  GRANT ALL PRIVILEGES ON `wp_%`.* TO 'portal_admin'@'%';
  GRANT ALL PRIVILEGES ON `mailserver_%`.* TO 'portal_admin'@'%';
  GRANT CREATE, DROP, ALTER ON *.* TO 'portal_admin'@'%';
  GRANT SELECT, INSERT, UPDATE, DELETE ON mysql.user TO 'portal_admin'@'%';
  ```
- パスワード: **暗号化して保存**（Fernet対称暗号化、.envに保存）

**セキュリティ要件**:
- rootユーザーは使用しない
- 危険なクエリはブロック（DROP DATABASE, TRUNCATE等）
- クエリタイムアウト: 30秒
- 1クエリあたりの最大行数: 1000行

#### 2.3.5 PHP Management
**機能ID**: `PHP-001`

**要件**:
- **PHPバージョン管理**:
  - インストール済みバージョン一覧（7.4, 8.0, 8.1, 8.2）
  - 各バージョンの使用サイト数表示
  - **新しいバージョン追加**:
    - docker-compose.ymlにphp-fpmサービス追加
    - Docker imageビルド
    - コンテナ起動
  - **未使用バージョン削除**:
    - 使用サイト数が0の場合のみ削除可能
    - コンテナ停止・削除
- **バージョン別設定**:
  - php.ini表示・編集（バージョン別）
  - PHP-FPM設定表示・編集（pm.max_children等）
  - 拡張モジュール一覧
  - エラーログ表示（バージョン別）
- **サイト別使用状況**:
  - サイト名、ドメイン、PHPバージョンの一覧表示
  - バージョン別グループ表示
  - 一括バージョン変更（複数サイト選択）

**技術構成**（PHP-FPM複数バージョン）:
```yaml
services:
  php74-fpm:
    image: wordpress:php7.4-fpm
    volumes:
      - ./wordpress:/var/www/html
  php80-fpm:
    image: wordpress:php8.0-fpm
    volumes:
      - ./wordpress:/var/www/html
  php81-fpm:
    image: wordpress:php8.1-fpm
    volumes:
      - ./wordpress:/var/www/html
  php82-fpm:
    image: wordpress:php8.2-fpm
    volumes:
      - ./wordpress:/var/www/html
```

**Nginx設定自動生成**:
- サイトごとに`fastcgi_pass`を動的変更
- 例: PHP 8.2使用 → `fastcgi_pass php82-fpm:9000;`

#### 2.3.6 Backup Management
**機能ID**: `BACKUP-001`

**要件**:
- バックアップ一覧（ローカル + S3）
- 手動バックアップ実行
- リストア操作（確認ダイアログ付き）
- スケジュール設定UI

---

## 3. 非機能要件

### 3.1 パフォーマンス
- API レスポンスタイム: 平均 < 500ms、95パーセンタイル < 1000ms
- ページロード時間: 初回 < 3秒、キャッシュ後 < 1秒
- 同時接続数: 10ユーザー対応（現状は管理者1名のみ）

### 3.2 セキュリティ
- **認証**: JWT（HS256、有効期限15分）
- **通信**: HTTPS必須（Cloudflare Tunnel経由）
- **CORS**: フロントエンドドメインのみ許可
- **SQLインジェクション対策**: Parameterized Query徹底
- **XSS対策**: 入力値サニタイズ、Content-Security-Policy
- **CSRF対策**: JWTベーストークン
- **パスワード暗号化**:
  - **メールユーザーパスワード**: SHA512-CRYPT（Dovecot互換）
  - **管理者パスワード**: bcrypt（rounds=12）
  - **データベース接続パスワード**: Fernet対称暗号化
    - 暗号化キー: 環境変数`ENCRYPTION_KEY`（32バイト、base64エンコード）
    - ライブラリ: `cryptography.fernet`
    - 保存場所: `.env`ファイル（暗号化済み）
    - 復号化: アプリケーション起動時のみ
  - **パスワードリセットトークン**: SHA256ハッシュ化

### 3.3 可用性
- 目標稼働率: 99.9%（月間ダウンタイム < 43分）
- バックアップ: 日次自動（AM 3:00）
- 復旧時間目標（RTO）: 1時間以内
- 復旧ポイント目標（RPO）: 24時間以内

### 3.4 保守性
- コードカバレッジ: 80%以上
- ドキュメント: 全API、全機能
- ログレベル: INFO（本番）、DEBUG（開発）
- エラーメッセージ: ユーザーフレンドリー + 内部詳細ログ

### 3.5 スケーラビリティ
- 現状は単一サーバー（Dell WorkStation）
- 将来的にAWS移行可能な設計（コンテナ化）
- データベース: Read Replica対応可能（MySQL Replication）

---

## 4. 技術要件

### 4.1 バックエンド
- **言語**: Python 3.9+
- **フレームワーク**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **データベース**: MariaDB 10.6+（複数接続：Blog + Mailserver）
- **認証**: python-jose（JWT）、passlib（パスワードハッシュ）
- **バリデーション**: Pydantic 2.0+
- **暗号化**: cryptography.fernet（DB接続パスワード暗号化）
- **メール送信**: smtplib（Mailserver経由）

### 4.2 フロントエンド
- **言語**: TypeScript 5.0+
- **フレームワーク**: React 18.2+
- **ビルドツール**: Vite 5.0+
- **UI**: Tailwind CSS 3.3+ + shadcn/ui
- **状態管理**: Zustand + TanStack Query
- **ルーティング**: React Router 6.0+

### 4.3 インフラ
- **コンテナ**: Docker 24.0+、Docker Compose 2.20+
- **Webサーバー**: Nginx（リバースプロキシ）
- **SSL**: Cloudflare Tunnel（自動証明書）
- **ログ**: Loguru（バックエンド）、Console（フロントエンド）

### 4.4 開発環境
- **エディタ**: Claude Code on the web（コード生成）+ ローカルエディタ
- **バージョン管理**: Git（現在のリポジトリ）
- **ブランチ**: `claude/unified-portal-update-013A39eBWkgFoYTVLvM3V19t`

---

## 5. 制約事項

### 5.1 既存システムへの影響
- **絶対条件**: 既存 `services/mailserver/usermgmt/` を一切変更しない
- **並行稼働**: Flask usermgmtと同時稼働可能
- **データベース**: 既存テーブル構造を変更しない（カラム追加も禁止）

### 5.2 環境制約
- **Dell WorkStation**: ローカル開発・本番環境（リソース制約あり）
- **データベース**: 172.20.0.60:3306（Dockerコンテナ）
- **ネットワーク**: Dockerネットワーク `mailserver_default`（既存）

### 5.3 運用制約
- **管理者**: 現在1名（将来的に複数対応）
- **メンテナンス時間**: 深夜のみ（AM 2:00-5:00）
- **バックアップ時間**: AM 3:00（既存）

---

## 6. 受け入れ基準

### 6.1 Phase 1（Mailserver統合）
- [ ] メールユーザーCRUD操作が正常動作
- [ ] Flask usermgmtと同じデータが表示される
- [ ] 監査ログが全操作で記録される
- [ ] レスポンスタイム < 500ms
- [ ] 単体テストカバレッジ > 80%
- [ ] 既存Flask usermgmtに影響なし

### 6.2 Phase 2（DNS管理）
- [ ] Cloudflareリンクが正常動作
- [ ] DNSレコード編集が成功
- [ ] バルク操作（削除、CSV）が動作
- [ ] DNS検証ツールが正確な結果を返す

### 6.3 Phase 3（追加機能）
- [ ] JWT認証が安全に動作
- [ ] Docker操作が正常動作
- [ ] WordPress API統合が完了
- [ ] 全E2Eテストがパス

---

## 7. マイルストーン

### Week 1: 設計・準備（Web側）
- [ ] 全ドキュメント作成完了
- [ ] バックエンドコード生成完了
- [ ] フロントエンドコード生成完了

### Week 2: 統合・テスト（ローカル）
- [ ] Docker Compose起動確認
- [ ] データベース接続確認
- [ ] 全機能動作確認
- [ ] テスト実行・修正

### Week 3: デプロイ・移行
- [ ] 本番環境デプロイ
- [ ] 並行稼働テスト
- [ ] ユーザー移行（管理者）
- [ ] Flask usermgmt廃止準備

---

## 8. 用語集

| 用語 | 説明 |
|------|------|
| **Unified Portal** | 統合管理ポータル（本プロジェクトの成果物） |
| **Flask usermgmt** | 既存のMailserver管理システム（Flask製） |
| **Mailserver** | メールサーバー（Postfix + Dovecot + MariaDB） |
| **Blog System** | WordPress 16サイト（Nginx + MariaDB + Redis） |
| **Dell WorkStation** | 開発・本番環境（Rocky Linux 9.6） |
| **Web側** | Claude Code on the webで実行可能な作業 |
| **ローカル側** | Dell WorkStationで実行する作業 |
| **SHA512-CRYPT** | Dovecot互換パスワードハッシュアルゴリズム |
| **JWT** | JSON Web Token（認証方式） |
| **RBAC** | Role-Based Access Control（ロールベースアクセス制御） |

---

**次のステップ**: [02_ARCHITECTURE.md](02_ARCHITECTURE.md) でアーキテクチャ設計を確認
