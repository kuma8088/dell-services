# アーキテクチャ設計書

**プロジェクト**: Unified Portal - Mailserver統合 + WordPress管理 + Database管理 + PHP管理 + DNS管理強化

**バージョン**: 2.0

**作成日**: 2025-11-14
**更新日**: 2025-11-14 (WordPress/Database/PHP管理追加)

---

## 1. システム概要

### 1.1 アーキテクチャスタイル
- **3層アーキテクチャ**: プレゼンテーション層、ビジネスロジック層、データアクセス層
- **マイクロサービス的分離**: 各機能（Mailserver、DNS、Docker等）を独立モジュールで実装
- **RESTful API**: HTTPベースの標準的なAPI設計
- **SPA（Single Page Application）**: React製フロントエンド

### 1.2 システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Internet / User                               │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Cloudflare Tunnel                                │
│                     (HTTPS, admin.kuma8088.com)                         │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Dell WorkStation (Rocky Linux 9.6)                   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Docker Compose: unified-portal                        │ │
│  │                                                                     │ │
│  │  ┌──────────────────┐      ┌──────────────────┐                   │ │
│  │  │  Nginx           │      │  Frontend        │                   │ │
│  │  │  (Reverse Proxy) │─────▶│  (React + Vite)  │                   │ │
│  │  │  Port: 80/443    │      │  Port: 5173      │                   │ │
│  │  └──────┬───────────┘      └──────────────────┘                   │ │
│  │         │                                                           │ │
│  │         ▼                                                           │ │
│  │  ┌──────────────────┐                                              │ │
│  │  │  Backend         │                                              │ │
│  │  │  (FastAPI)       │                                              │ │
│  │  │  Port: 8000      │                                              │ │
│  │  └──────┬───────────┘                                              │ │
│  │         │                                                           │ │
│  │         ├──────────┬──────────┬──────────┬──────────┬──────────┐   │ │
│  │         │          │          │          │          │          │   │ │
│  │         ▼          ▼          ▼          ▼          ▼          ▼   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │
│  │  │ MariaDB  │ │ MariaDB  │ │ Docker   │ │Cloudflare│ │ wp-cli   │ │ │
│  │  │ (Mail)   │ │ (Blog)   │ │ Engine   │ │ API      │ │          │ │ │
│  │  │172.20.0  │ │172.20.0  │ │ (Unix    │ │ (HTTPS)  │ │          │ │ │
│  │  │   .60    │ │   .30    │ │ Socket)  │ │          │ │          │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │         Docker Compose: blog (WordPress管理対象)                   │ │
│  │                                                                     │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │ │
│  │  │ PHP 7.4  │  │ PHP 8.0  │  │ PHP 8.1  │  │ PHP 8.2  │          │ │
│  │  │ -FPM     │  │ -FPM     │  │ -FPM     │  │ -FPM     │          │ │
│  │  │ :9000    │  │ :9000    │  │ :9000    │  │ :9000    │          │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │ │
│  │       ▲             ▲             ▲             ▲                  │ │
│  │       └─────────────┴─────────────┴─────────────┘                  │ │
│  │                            │                                        │ │
│  │  ┌─────────────────────────┴──────────────────────┐                │ │
│  │  │          Nginx (Blog Reverse Proxy)            │                │ │
│  │  │       サイトごとにPHP-FPMバージョン振り分け      │                │ │
│  │  └────────────────────────────────────────────────┘                │ │
│  │                                                                     │ │
│  │  ┌────────────────────────────────────────────────┐                │ │
│  │  │         WordPress (16サイト)                   │                │ │
│  │  │  - kuma8088.com (PHP 8.2)                      │                │ │
│  │  │  - demo1.kuma8088.com (PHP 8.1)                │                │ │
│  │  │  - ... (14 more sites)                         │                │ │
│  │  └────────────────────────────────────────────────┘                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │           既存システム（変更なし・並行稼働）                        │ │
│  │                                                                     │ │
│  │  ┌──────────────────┐      ┌──────────────────┐                   │ │
│  │  │ Flask usermgmt   │      │ MariaDB          │                   │ │
│  │  │ Port: 5000       │─────▶│ (mailserver_     │                   │ │
│  │  │ (既存・並行稼働)  │      │  usermgmt)       │                   │ │
│  │  └──────────────────┘      │ 172.20.0.60:3306 │                   │ │
│  │                            └──────────────────┘                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. コンポーネント設計

### 2.1 フロントエンド（React）

#### ディレクトリ構造
```
services/unified-portal/frontend/
├── src/
│   ├── components/          # UIコンポーネント
│   │   ├── layout/
│   │   │   └── Layout.tsx   # 共通レイアウト（既存）
│   │   ├── ui/              # shadcn/ui（既存）
│   │   ├── mailserver/      # Mailserver固有コンポーネント（NEW）
│   │   │   ├── UserTable.tsx
│   │   │   ├── UserForm.tsx
│   │   │   ├── DomainTable.tsx
│   │   │   ├── DomainForm.tsx
│   │   │   ├── AuditLogTable.tsx
│   │   │   ├── AdminUserTable.tsx
│   │   │   └── AdminUserForm.tsx
│   │   ├── wordpress/       # WordPress管理コンポーネント（NEW）
│   │   │   ├── SiteTable.tsx
│   │   │   ├── SiteForm.tsx
│   │   │   └── PhpVersionSelector.tsx
│   │   ├── database/        # Database管理コンポーネント（NEW）
│   │   │   ├── DatabaseTable.tsx
│   │   │   ├── DatabaseForm.tsx
│   │   │   ├── UserTable.tsx
│   │   │   ├── UserForm.tsx
│   │   │   └── QueryExecutor.tsx
│   │   └── php/             # PHP管理コンポーネント（NEW）
│   │       ├── VersionTable.tsx
│   │       ├── ConfigEditor.tsx
│   │       └── UsageStats.tsx
│   ├── pages/               # ページコンポーネント
│   │   ├── Dashboard.tsx            # 既存
│   │   ├── DomainManagement.tsx     # 既存（強化）
│   │   ├── MailUserManagement.tsx   # NEW
│   │   ├── MailDomainManagement.tsx # NEW
│   │   ├── AuditLogs.tsx            # NEW
│   │   ├── AdminUserManagement.tsx  # NEW
│   │   ├── WordPressManagement.tsx  # NEW
│   │   ├── DatabaseManagement.tsx   # NEW
│   │   ├── PhpManagement.tsx        # NEW
│   │   ├── ForgotPassword.tsx       # NEW
│   │   └── ResetPassword.tsx        # NEW
│   ├── lib/                 # ユーティリティ
│   │   ├── api.ts           # ベースAPIクライアント（既存）
│   │   ├── domains-api.ts   # Cloudflare DNS API（既存）
│   │   ├── mailserver-api.ts # Mailserver API（NEW）
│   │   ├── wordpress-api.ts # WordPress API（NEW）
│   │   ├── database-api.ts  # Database API（NEW）
│   │   └── php-api.ts       # PHP API（NEW）
│   ├── contexts/
│   │   └── AuthContext.tsx  # 認証コンテキスト（既存・強化）
│   ├── hooks/               # カスタムフック
│   │   ├── useMailUsers.ts  # NEW
│   │   ├── useMailDomains.ts # NEW
│   │   ├── useAdminUsers.ts # NEW
│   │   ├── useWordPressSites.ts # NEW
│   │   ├── useDatabases.ts  # NEW
│   │   └── usePhpVersions.ts # NEW
│   └── types/               # TypeScript型定義
│       ├── mailserver.ts    # NEW
│       ├── wordpress.ts     # NEW
│       ├── database.ts      # NEW
│       └── php.ts           # NEW
```

#### 主要コンポーネント

**MailUserManagement.tsx**（NEW）
```typescript
機能:
- ユーザー一覧表示（テーブル、ページング）
- 検索・フィルタ（email、domain、enabled）
- ソート（email、quota、created_at）
- CRUD操作（作成、編集、削除、パスワード変更、有効/無効切替）
- ローディング・エラーハンドリング

使用コンポーネント:
- UserTable（一覧表示）
- UserForm（作成・編集フォーム）
- Dialog（モーダル）
- Button, Input（shadcn/ui）
```

**MailDomainManagement.tsx**（NEW）
```typescript
機能:
- ドメイン一覧表示（ユーザー数、quota合計）
- CRUD操作（作成、編集、削除）
- 削除時の警告（所属ユーザーあり）

使用コンポーネント:
- DomainTable
- DomainForm
- AlertDialog（削除確認）
```

**AuditLogs.tsx**（NEW）
```typescript
機能:
- 監査ログ一覧表示
- フィルタ（日付範囲、操作種別、ユーザー）
- CSVエクスポート

使用コンポーネント:
- AuditLogTable
- DateRangePicker
- Select（フィルタ）
```

**WordPressManagement.tsx**（NEW）
```typescript
機能:
- WordPress サイト一覧表示（16サイト）
- サイト情報表示（ドメイン、DB名、PHPバージョン）
- 新規サイト作成ウィザード:
  - サイト名・ドメイン入力
  - データベース選択（自動作成 or 既存選択）
  - PHPバージョン選択（7.4, 8.0, 8.1, 8.2）
  - WordPress自動インストール
  - WP Mail SMTP自動設定
- サイト設定編集:
  - ドメイン変更
  - PHPバージョン切り替え（ドロップダウン）
  - データベース変更
  - 有効/無効切替
- サイト削除（確認ダイアログ付き）

使用コンポーネント:
- SiteTable（一覧表示）
- SiteForm（作成・編集フォーム）
- PhpVersionSelector（PHPバージョン選択）
- Dialog（モーダル）
```

**DatabaseManagement.tsx**（NEW）
```typescript
機能:
- データベース一覧表示:
  - Blog MariaDB（172.20.0.30:3306）
  - Mailserver MariaDB（172.20.0.60:3306）
  - 各DBのデータベース一覧
- 新規データベース作成:
  - DB名入力（バリデーション）
  - 文字セット選択（utf8mb4推奨）
  - 接続先選択（Blog/Mailserver）
  - 自動でDBユーザー作成
- データベースユーザー管理:
  - ユーザー一覧
  - 新規ユーザー作成
  - パスワード変更（Fernet暗号化）
  - 権限変更（SELECT, INSERT, UPDATE, DELETE等）
- SQLクエリ実行（制限付き）:
  - SELECT文のみ許可（デフォルト）
  - INSERT/UPDATE/DELETE: Super Adminのみ
  - DROP/ALTER: 実行不可

使用コンポーネント:
- DatabaseTable（DB一覧）
- DatabaseForm（DB作成フォーム）
- UserTable（ユーザー一覧）
- UserForm（ユーザー作成・編集）
- QueryExecutor（SQL実行）
- Tabs（Blog/Mailserver切り替え）
```

**PhpManagement.tsx**（NEW）
```typescript
機能:
- PHPバージョン一覧表示:
  - インストール済みバージョン（7.4, 8.0, 8.1, 8.2）
  - 各バージョンの使用サイト数
  - 各バージョンのステータス（Running/Stopped）
- PHPバージョン追加:
  - バージョン選択
  - docker-compose.ymlにサービス追加
  - イメージビルド
  - コンテナ起動
- PHPバージョン削除:
  - 使用サイト数が0の場合のみ削除可能
  - 確認ダイアログ
- PHP設定管理:
  - php.ini編集（メモリ上限、最大アップロードサイズ等）
  - PHP-FPM設定編集
  - 設定変更後の再起動

使用コンポーネント:
- VersionTable（バージョン一覧）
- ConfigEditor（設定編集）
- UsageStats（使用統計）
- CodeEditor（php.ini編集）
```

---

### 2.2 バックエンド（FastAPI）

#### ディレクトリ構造
```
services/unified-portal/backend/
├── app/
│   ├── models/              # SQLAlchemyモデル
│   │   ├── __init__.py
│   │   ├── mail_user.py     # NEW
│   │   ├── mail_domain.py   # NEW
│   │   ├── audit_log.py     # NEW
│   │   ├── admin_user.py    # NEW
│   │   ├── password_reset.py # NEW
│   │   ├── wordpress_site.py # NEW
│   │   └── db_credential.py # NEW
│   ├── schemas/             # Pydanticスキーマ
│   │   ├── __init__.py
│   │   ├── mailserver.py    # NEW（リクエスト/レスポンス）
│   │   ├── wordpress.py     # NEW
│   │   ├── database.py      # NEW
│   │   └── php.py           # NEW
│   ├── routers/             # APIルーター
│   │   ├── __init__.py
│   │   ├── auth.py          # 既存（強化予定）
│   │   ├── domains.py       # 既存（Cloudflare DNS）
│   │   ├── mailserver.py    # NEW
│   │   ├── admin_users.py   # NEW
│   │   ├── password_reset.py # NEW
│   │   ├── wordpress.py     # NEW
│   │   ├── database.py      # NEW
│   │   └── php.py           # NEW
│   ├── services/            # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── mail_user_service.py   # NEW
│   │   ├── mail_domain_service.py # NEW
│   │   ├── audit_service.py       # NEW
│   │   ├── admin_user_service.py  # NEW
│   │   ├── password_reset_service.py # NEW
│   │   ├── email_service.py       # NEW
│   │   ├── wordpress_service.py   # NEW
│   │   ├── database_service.py    # NEW
│   │   ├── php_service.py         # NEW
│   │   ├── encryption_service.py  # NEW（Fernet暗号化）
│   │   └── nginx_config_service.py # NEW（Nginx設定生成）
│   ├── database.py          # 既存（DB接続設定・更新）
│   ├── config.py            # 既存（環境変数・更新）
│   ├── auth.py              # 既存（JWT認証）
│   └── main.py              # 既存（エントリーポイント・更新）
├── migrations/              # マイグレーションSQL（NEW）
│   ├── 001_add_admin_tables.sql
│   └── 002_add_wordpress_sites.sql
├── scripts/                 # セットアップスクリプト（NEW）
│   ├── create-portal-admin-users.sh
│   ├── generate-encryption-key.sh
│   └── setup.sh
├── tests/                   # テスト
│   ├── test_mailserver_router.py  # NEW
│   ├── test_mail_user_service.py  # NEW
│   ├── test_mail_domain_service.py # NEW
│   ├── test_admin_user_service.py # NEW
│   ├── test_password_reset.py     # NEW
│   ├── test_wordpress_service.py  # NEW
│   ├── test_database_service.py   # NEW
│   └── test_php_service.py        # NEW
└── requirements.txt         # 既存（依存関係追加）
```

#### 主要モジュール

**models/mail_user.py**（NEW）
```python
クラス: MailUser
機能: 既存テーブル `users` をSQLAlchemyでマッピング

属性:
- id: Integer, PrimaryKey
- email: String(255), Unique, Index
- password_hash: String(255)
- domain_id: Integer, ForeignKey('domains.id')
- maildir: String(500)
- quota: Integer
- uid: Integer
- gid: Integer
- enabled: Boolean
- is_admin: Boolean
- created_at: DateTime
- updated_at: DateTime

リレーション:
- domain: Relationship to MailDomain
```

**services/mail_user_service.py**（NEW）
```python
クラス: MailUserService
機能: ユーザー管理のビジネスロジック

メソッド:
- list_users(domain_id, skip, limit, search, enabled)
- get_user_by_email(email)
- create_user(email, password, domain_id, quota, enabled)
  └─ パスワードハッシュ化（SHA512-CRYPT）
  └─ maildir自動生成
  └─ 監査ログ記録
- update_user(email, quota, enabled)
- delete_user(email)
- change_password(email, new_password)
- toggle_status(email)

例外:
- ValueError: バリデーションエラー
- IntegrityError: DB制約違反
```

**routers/mailserver.py**（NEW）
```python
プレフィックス: /api/v1/mailserver
タグ: Mailserver

エンドポイント:
- GET    /users              # ユーザー一覧
- POST   /users              # ユーザー作成
- GET    /users/{email}      # ユーザー詳細
- PUT    /users/{email}      # ユーザー更新
- DELETE /users/{email}      # ユーザー削除
- POST   /users/{email}/password  # パスワード変更
- POST   /users/{email}/toggle    # 有効/無効切替
- GET    /domains            # ドメイン一覧
- POST   /domains            # ドメイン作成
- GET    /domains/{id}       # ドメイン詳細
- PUT    /domains/{id}       # ドメイン更新
- DELETE /domains/{id}       # ドメイン削除
- GET    /audit-logs         # 監査ログ一覧

認証: すべてJWT必須（Depends(get_current_user)）
```

**models/wordpress_site.py**（NEW）
```python
クラス: WordPressSite
機能: wordpress_sites テーブルをSQLAlchemyでマッピング

属性:
- id: Integer, PrimaryKey
- site_name: String(100), Unique, Index
- domain: String(255), Unique
- database_name: String(100)
- php_version: String(10)  # "7.4", "8.0", "8.1", "8.2"
- enabled: Boolean
- created_at: DateTime
- updated_at: DateTime

ビジネスロジック:
- PHPバージョン変更時にNginx設定自動生成
- データベース切り替え時のwp-config.php更新
```

**services/wordpress_service.py**（NEW）
```python
クラス: WordPressService
機能: WordPress管理のビジネスロジック

メソッド:
- list_sites() - サイト一覧取得
- get_site(site_name) - サイト詳細取得
- create_site(site_name, domain, database_option, php_version)
  └─ データベース作成（自動 or 既存選択）
  └─ wp-cliでWordPressインストール
  └─ WP Mail SMTP自動設定
  └─ Nginx設定生成
  └─ 監査ログ記録
- update_site(site_name, domain, database_name, php_version, enabled)
  └─ PHPバージョン変更時にNginx設定再生成
  └─ nginx -s reload実行
- delete_site(site_name)
  └─ 確認チェック
  └─ wp-cliでアンインストール

例外:
- SiteAlreadyExistsError
- SiteNotFoundError
- InvalidPhpVersionError
```

**services/database_service.py**（NEW）
```python
クラス: DatabaseService
機能: 汎用データベース管理のビジネスロジック

メソッド:
- list_databases(target: "blog"|"mailserver") - DB一覧取得
- create_database(name, charset, target)
  └─ CREATE DATABASE実行
  └─ 専用ユーザー作成（DB名と同じ）
  └─ GRANT権限付与
  └─ パスワード暗号化保存（Fernet）
  └─ 監査ログ記録
- delete_database(name, target)
- list_users(target) - DBユーザー一覧
- create_user(username, password, target)
  └─ CREATE USER実行
  └─ パスワードFernet暗号化
- update_user_password(username, new_password, target)
  └─ ALTER USER実行
  └─ パスワード再暗号化
- grant_privileges(username, database, privileges, target)
- execute_query(query, target, user_role)
  └─ SQLインジェクション対策
  └─ 権限チェック（SELECT only / Admin only）

データベース接続:
- Blog MariaDB: 172.20.0.30:3306（portal_admin）
- Mailserver MariaDB: 172.20.0.60:3306（portal_admin）

例外:
- DatabaseAlreadyExistsError
- InvalidDatabaseNameError
- InsufficientPrivilegesError
```

**services/php_service.py**（NEW）
```python
クラス: PhpService
機能: PHP-FPM複数バージョン管理

メソッド:
- list_versions() - インストール済みバージョン一覧
  └─ docker ps でPHP-FPMコンテナ確認
  └─ 各バージョンの使用サイト数カウント
- add_version(version: "7.4"|"8.0"|"8.1"|"8.2")
  └─ docker-compose.ymlにphp-fpmサービス追加
  └─ docker compose up -d実行
  └─ ヘルスチェック
- remove_version(version)
  └─ 使用サイト数 == 0 確認
  └─ docker compose stop php{version}-fpm
  └─ docker-compose.ymlから削除
- get_config(version) - php.ini取得
- update_config(version, config)
  └─ php.ini書き込み
  └─ docker compose restart php{version}-fpm
- get_usage_stats(version) - 使用統計
  └─ 使用サイト一覧
  └─ メモリ使用量、リクエスト数等

例外:
- PhpVersionNotFoundError
- PhpVersionInUseError
```

**services/encryption_service.py**（NEW）
```python
クラス: EncryptionService
機能: Fernet対称暗号化によるパスワード保護

from cryptography.fernet import Fernet
import base64
import os

属性:
- encryption_key: bytes（環境変数ENCRYPTION_KEYから取得）
- fernet: Fernet(encryption_key)

メソッド:
- encrypt_password(plain_password: str) -> str
  └─ Fernet暗号化
  └─ base64エンコード
  └─ 文字列として返却
- decrypt_password(encrypted_password: str) -> str
  └─ base64デコード
  └─ Fernet復号化
  └─ 平文パスワード返却

環境変数:
- ENCRYPTION_KEY: 32バイトbase64エンコードされたキー
- 生成コマンド: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**services/nginx_config_service.py**（NEW）
```python
クラス: NginxConfigService
機能: Nginx設定ファイル自動生成

メソッド:
- generate_site_config(site: WordPressSite) -> str
  └─ Jinjaテンプレートから設定生成
  └─ fastcgi_pass を php{version}-fpm:9000 に設定
  └─ HTTPS検出パラメータ追加
  └─ 設定文字列返却
- write_config(site_name: str, config: str)
  └─ /services/blog/config/nginx/conf.d/{site_name}.conf に書き込み
- test_config() -> bool
  └─ docker exec blog-nginx nginx -t 実行
  └─ 成功/失敗を返却
- reload_nginx()
  └─ docker exec blog-nginx nginx -s reload 実行
  └─ エラーハンドリング

テンプレート例:
server {
    listen 80;
    server_name {{ domain }};
    root /var/www/html/{{ site_name }};

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_pass php{{ php_version.replace('.', '') }}-fpm:9000;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param HTTPS on;
        include fastcgi_params;
    }
}
```

---

### 2.3 データベース設計

#### 既存テーブル（変更なし）

**users テーブル**
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    domain_id INT NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    maildir VARCHAR(500) NOT NULL,
    quota INT DEFAULT 1024,
    uid INT DEFAULT 5000,
    gid INT DEFAULT 5000,
    enabled BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);
```

**domains テーブル**
```sql
CREATE TABLE domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(500),
    default_quota INT DEFAULT 1024,
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);
```

**audit_logs テーブル**
```sql
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    admin_ip VARCHAR(100) NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (user_email),
    INDEX idx_created_at (created_at)
);
```

#### 新規テーブル（追加）

**admin_users テーブル**（Portal管理者）
```sql
CREATE TABLE admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt
    role VARCHAR(50) NOT NULL DEFAULT 'admin',  -- 'super_admin', 'admin'
    enabled BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);
```

**password_reset_tokens テーブル**（パスワードリセット）
```sql
CREATE TABLE password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) UNIQUE NOT NULL,  -- SHA256
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_hash (token_hash),
    INDEX idx_user_email (user_email),
    INDEX idx_expires_at (expires_at)
);
```

**wordpress_sites テーブル**（WordPress管理）
```sql
CREATE TABLE wordpress_sites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(100) UNIQUE NOT NULL,  -- 'kuma8088', 'demo1'
    domain VARCHAR(255) UNIQUE NOT NULL,     -- 'kuma8088.com', 'demo1.kuma8088.com'
    database_name VARCHAR(100) NOT NULL,     -- 'wp_kuma8088'
    php_version VARCHAR(10) NOT NULL,        -- '7.4', '8.0', '8.1', '8.2'
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_site_name (site_name),
    INDEX idx_domain (domain),
    INDEX idx_php_version (php_version)
);
```

**db_credentials テーブル**（データベース接続情報）
```sql
CREATE TABLE db_credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target VARCHAR(20) NOT NULL,         -- 'blog', 'mailserver'
    database_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    encrypted_password TEXT NOT NULL,    -- Fernet暗号化
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_target_db_user (target, database_name, username),
    INDEX idx_target (target),
    INDEX idx_database_name (database_name)
);
```

#### データベース接続設定

**config.py 更新内容**
```python
# 既存設定に追加
class Settings(BaseSettings):
    # ... 既存設定 ...

    # Mailserver Database（NEW）
    mail_db_host: str = "172.20.0.60"
    mail_db_port: int = 3306
    mail_db_name: str = "mailserver_usermgmt"
    mail_db_user: str = "portal_admin"
    mail_db_password: str

    # Blog Database（NEW）
    blog_db_host: str = "172.20.0.30"
    blog_db_port: int = 3306
    blog_db_name: str = "blog_management"  # Portal用メタデータDB
    blog_db_user: str = "portal_admin"
    blog_db_password: str

    # Encryption（NEW）
    encryption_key: str  # Fernet暗号化キー（32バイトbase64）

    # Email（NEW）
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = "noreply@kuma8088.com"
    smtp_password: str
    smtp_from_name: str = "Unified Portal"

    @property
    def mail_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mail_db_user}:{self.mail_db_password}"
            f"@{self.mail_db_host}:{self.mail_db_port}/{self.mail_db_name}"
        )

    @property
    def blog_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.blog_db_user}:{self.blog_db_password}"
            f"@{self.blog_db_host}:{self.blog_db_port}/{self.blog_db_name}"
        )
```

**database.py 更新内容**
```python
# Mailserver Database（既存テーブル: users, domains, audit_logs）
mail_engine = create_engine(
    settings.mail_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

MailSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=mail_engine
)

def get_mail_db():
    db = MailSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Blog Database（新規テーブル: admin_users, password_reset_tokens, wordpress_sites, db_credentials）
blog_engine = create_engine(
    settings.blog_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

BlogSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=blog_engine
)

def get_blog_db():
    db = BlogSessionLocal()
    try:
        yield db
    finally:
        db.close()

# データベース管理用接続（動的接続先切り替え）
def get_db_connection(target: str):
    """
    target: "blog" or "mailserver"
    Returns: SQLAlchemy engine for the specified target
    """
    if target == "blog":
        return create_engine(
            f"mysql+pymysql://portal_admin:{settings.blog_db_password}"
            f"@172.20.0.30:3306/",  # DBなし（管理操作用）
            pool_pre_ping=True
        )
    elif target == "mailserver":
        return create_engine(
            f"mysql+pymysql://portal_admin:{settings.mail_db_password}"
            f"@172.20.0.60:3306/",
            pool_pre_ping=True
        )
    else:
        raise ValueError(f"Invalid target: {target}")
```

---

## 3. データフロー

### 3.1 ユーザー作成フロー

```
[User Browser]
    │
    ├─ POST /api/v1/mailserver/users
    │  Body: {email, password, domain_id, quota}
    ▼
[Frontend: MailUserManagement]
    │
    ├─ mailserver-api.createUser()
    │  ├─ バリデーション（email形式、パスワード強度）
    │  └─ HTTPリクエスト送信
    ▼
[Backend: mailserver.py router]
    │
    ├─ JWT認証チェック（get_current_user）
    ├─ Pydanticバリデーション（UserCreateRequest）
    ▼
[Service: MailUserService.create_user()]
    │
    ├─ ドメイン存在確認（DomainService）
    ├─ メール重複チェック（SELECT email FROM users）
    ├─ パスワードハッシュ化（SHA512-CRYPT）
    ├─ maildir生成（/var/mail/vmail/{domain}/{user}/）
    ├─ INSERT INTO users
    ├─ 監査ログ記録（AuditService.log_audit()）
    ▼
[Database: MariaDB]
    │
    ├─ トランザクション開始
    ├─ users テーブル INSERT
    ├─ audit_logs テーブル INSERT
    └─ COMMIT
    ▼
[Response: UserResponse]
    │
    ├─ JSON: {id, email, domain, quota, enabled, created_at}
    ▼
[Frontend: MailUserManagement]
    │
    ├─ テーブル再フェッチ（TanStack Query）
    ├─ 成功メッセージ表示（Toast）
    └─ モーダルクローズ
```

### 3.2 DNS管理強化フロー（#017）

```
[User Browser]
    │
    ├─ Click "Cloudflareで管理" Button
    ▼
[Frontend: DomainManagement]
    │
    ├─ window.open(`https://dash.cloudflare.com/${zoneId}/dns`, '_blank')
    └─ 新規タブでCloudflareダッシュボード表示

---

[User Browser]
    │
    ├─ Edit DNS Record
    ▼
[Frontend: DomainManagement]
    │
    ├─ domains-api.updateDnsRecord(zoneId, recordId, data)
    ▼
[Backend: domains.py router]
    │
    ├─ PUT /api/v1/domains/zones/{zone_id}/records/{record_id}
    ├─ Cloudflare API呼び出し
    │  PUT https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}
    ▼
[Cloudflare API]
    │
    ├─ レコード更新
    └─ Response: {success, result}
    ▼
[Frontend: DomainManagement]
    │
    ├─ レコード一覧再フェッチ
    └─ 成功メッセージ表示
```

### 3.3 WordPress サイト作成フロー

```
[User Browser]
    │
    ├─ POST /api/v1/wordpress/sites
    │  Body: {site_name, domain, database_option, php_version}
    ▼
[Frontend: WordPressManagement]
    │
    ├─ wordpress-api.createSite()
    │  ├─ バリデーション（site_name, domain, php_version）
    │  └─ HTTPリクエスト送信
    ▼
[Backend: wordpress.py router]
    │
    ├─ JWT認証チェック
    ├─ Pydanticバリデーション（SiteCreateRequest）
    ▼
[Service: WordPressService.create_site()]
    │
    ├─ Step 1: データベース作成
    │  ├─ database_option == "auto" の場合:
    │  │  └─ DatabaseService.create_database(f"wp_{site_name}")
    │  └─ database_option == "existing" の場合:
    │      └─ 既存DB使用
    ▼
    ├─ Step 2: WordPress インストール
    │  ├─ wp-cli core download
    │  ├─ wp-cli config create（database_name, portal_admin, password）
    │  ├─ wp-cli core install（site_url, site_title, admin_user, admin_email）
    │  └─ wp-cli plugin install wp-mail-smtp --activate
    ▼
    ├─ Step 3: WP Mail SMTP 設定
    │  └─ wp-cli option update wp_mail_smtp（JSON設定）
    ▼
    ├─ Step 4: Nginx 設定生成
    │  ├─ NginxConfigService.generate_site_config(site)
    │  │  └─ fastcgi_pass php{version}-fpm:9000
    │  ├─ NginxConfigService.write_config(site_name, config)
    │  ├─ NginxConfigService.test_config()
    │  └─ NginxConfigService.reload_nginx()
    ▼
    ├─ Step 5: DB登録
    │  └─ INSERT INTO wordpress_sites
    ▼
    ├─ Step 6: 監査ログ
    │  └─ AuditService.log_audit("wordpress_site_created", ...)
    ▼
[Response: SiteResponse]
    │
    └─ JSON: {id, site_name, domain, database_name, php_version}
```

### 3.4 データベース作成フロー

```
[User Browser]
    │
    ├─ POST /api/v1/database/databases
    │  Body: {name, charset, target: "blog"|"mailserver"}
    ▼
[Frontend: DatabaseManagement]
    │
    ├─ database-api.createDatabase()
    ▼
[Backend: database.py router]
    │
    ├─ JWT認証チェック
    ├─ Pydanticバリデーション（DatabaseCreateRequest）
    ▼
[Service: DatabaseService.create_database()]
    │
    ├─ Step 1: 接続先選択
    │  └─ engine = get_db_connection(target)  # blog or mailserver
    ▼
    ├─ Step 2: データベース作成
    │  └─ CREATE DATABASE {name} CHARACTER SET {charset}
    ▼
    ├─ Step 3: 専用ユーザー作成
    │  ├─ CREATE USER '{name}_user'@'%' IDENTIFIED BY '<random_password>'
    │  ├─ GRANT ALL PRIVILEGES ON {name}.* TO '{name}_user'@'%'
    │  └─ FLUSH PRIVILEGES
    ▼
    ├─ Step 4: パスワード暗号化保存
    │  ├─ EncryptionService.encrypt_password(random_password)
    │  └─ INSERT INTO db_credentials (target, database_name, username, encrypted_password)
    ▼
    ├─ Step 5: 監査ログ
    │  └─ AuditService.log_audit("database_created", ...)
    ▼
[Response: DatabaseResponse]
    │
    └─ JSON: {name, charset, username, created_at}
```

### 3.5 PHPバージョン切り替えフロー

```
[User Browser]
    │
    ├─ PUT /api/v1/wordpress/sites/{site_name}
    │  Body: {php_version: "8.2"}
    ▼
[Frontend: WordPressManagement]
    │
    ├─ wordpress-api.updateSite(site_name, {php_version: "8.2"})
    ▼
[Backend: wordpress.py router]
    │
    ├─ JWT認証チェック
    ▼
[Service: WordPressService.update_site()]
    │
    ├─ Step 1: サイト情報取得
    │  └─ site = db.query(WordPressSite).filter_by(site_name=site_name).first()
    ▼
    ├─ Step 2: PHPバージョン変更検出
    │  └─ if site.php_version != new_php_version:
    ▼
    ├─ Step 3: Nginx設定再生成
    │  ├─ site.php_version = new_php_version
    │  ├─ NginxConfigService.generate_site_config(site)
    │  │  └─ fastcgi_pass php{{ php_version.replace('.', '') }}-fpm:9000
    │  │     例: php82-fpm:9000
    │  ├─ NginxConfigService.write_config(site_name, config)
    │  ├─ NginxConfigService.test_config()
    │  │  └─ docker exec blog-nginx nginx -t
    │  └─ NginxConfigService.reload_nginx()
    │     └─ docker exec blog-nginx nginx -s reload（ダウンタイムなし）
    ▼
    ├─ Step 4: DB更新
    │  └─ UPDATE wordpress_sites SET php_version = "8.2", updated_at = NOW()
    ▼
    ├─ Step 5: 監査ログ
    │  └─ AuditService.log_audit("php_version_changed", ...)
    ▼
[Response: SiteResponse]
    │
    └─ JSON: {id, site_name, domain, php_version: "8.2"}
```

---

## 4. セキュリティ設計

### 4.1 認証・認可

**JWT認証フロー**
```
[Login]
POST /api/v1/auth/login
Body: {username, password}
    ↓
[Backend: auth.py]
- ユーザー検証（将来的にDBから取得）
- JWTトークン生成（HS256、有効期限15分）
    ↓
Response: {access_token, token_type: "bearer"}
    ↓
[Frontend: AuthContext]
- トークンをlocalStorageに保存
- Authorizationヘッダーに自動付与
```

**保護されたAPIアクセス**
```
[API Request]
GET /api/v1/mailserver/users
Header: Authorization: Bearer <token>
    ↓
[Backend: get_current_user dependency]
- トークン検証（署名、有効期限）
- ペイロード抽出（username）
    ↓
[Router]
- 処理実行
```

### 4.2 パスワードセキュリティ

**多層パスワード保護戦略**

システムでは3種類のパスワード保護方式を使い分けます:

**1. メールユーザーパスワード（SHA512-CRYPT）**
```python
# Dovecot互換SHA512-CRYPT
from passlib.hash import sha512_crypt

def hash_mail_user_password(password: str) -> str:
    return sha512_crypt.hash(password, rounds=5000)

def verify_mail_user_password(plain_password: str, hashed: str) -> bool:
    return sha512_crypt.verify(plain_password, hashed)

# 使用箇所: users テーブル（Mailserver）
```

**2. 管理者パスワード（bcrypt）**
```python
# セキュアなbcryptハッシュ
from passlib.hash import bcrypt

def hash_admin_password(password: str) -> str:
    return bcrypt.hash(password, rounds=12)

def verify_admin_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.verify(plain_password, hashed)

# 使用箇所: admin_users テーブル（Portal）
```

**3. データベース接続パスワード（Fernet対称暗号化）**
```python
# Fernet対称暗号化（復号化可能）
from cryptography.fernet import Fernet
import base64
import os

class EncryptionService:
    def __init__(self):
        # 環境変数ENCRYPTION_KEYから取得
        key = os.getenv("ENCRYPTION_KEY").encode()
        self.fernet = Fernet(key)

    def encrypt_password(self, plain_password: str) -> str:
        """
        パスワードを暗号化してbase64エンコード文字列を返す
        """
        encrypted = self.fernet.encrypt(plain_password.encode())
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        暗号化パスワードを復号化して平文を返す
        """
        encrypted_bytes = base64.b64decode(encrypted_password.encode('utf-8'))
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')

# 使用箇所: db_credentials テーブル（データベース接続情報）
# 理由: データベース接続時に平文パスワードが必要
```

**暗号化キー生成**
```bash
# 初回セットアップ時に実行
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# .env に保存
ENCRYPTION_KEY=<generated_key_here>
```

**パスワードポリシー**
- 最小長: 8文字
- 推奨: 英大文字、英小文字、数字、記号を含む
- フロントエンドでリアルタイムバリデーション
- メールユーザー: 強力なパスワード推奨（外部からのメール受信）
- 管理者: 必須（2FA将来実装予定）

### 4.3 SQL インジェクション対策
```python
# ✅ 正しい方法（Parameterized Query）
user = db.query(MailUser).filter(MailUser.email == email).first()

# ❌ 間違った方法（文字列結合）
# query = f"SELECT * FROM users WHERE email = '{email}'"
```

### 4.4 CORS設定
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 開発環境
        "https://admin.kuma8088.com"  # 本番環境
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 5. パフォーマンス最適化

### 5.1 データベース最適化
```sql
-- 既存インデックス（維持）
INDEX idx_email ON users(email);
INDEX idx_name ON domains(name);
INDEX idx_user_email ON audit_logs(user_email);
INDEX idx_created_at ON audit_logs(created_at);

-- クエリ最適化
-- ✅ ページング付き一覧取得
SELECT * FROM users
WHERE domain_id = ? AND enabled = ?
ORDER BY email
LIMIT 20 OFFSET 0;

-- ✅ N+1問題回避（Eager Loading）
# SQLAlchemy
query = db.query(MailUser).options(joinedload(MailUser.domain))
```

### 5.2 フロントエンド最適化
```typescript
// TanStack Query でキャッシング
const { data, isLoading } = useQuery({
  queryKey: ['mailUsers', domainId, page],
  queryFn: () => mailserverApi.getUsers(domainId, page),
  staleTime: 5 * 60 * 1000, // 5分間キャッシュ
});

// React.memo で再レンダリング防止
const UserTable = React.memo(({ users }) => {
  // ...
});
```

### 5.3 API レスポンスタイム目標
| エンドポイント | 目標 | 最大 |
|--------------|------|------|
| GET /users | 200ms | 500ms |
| POST /users | 300ms | 1000ms |
| GET /audit-logs | 250ms | 750ms |

---

## 6. エラーハンドリング

### 6.1 バックエンド
```python
# カスタム例外
class MailUserNotFoundError(Exception):
    pass

# エラーハンドラー
@app.exception_handler(MailUserNotFoundError)
async def mail_user_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Mail user not found"}
    )

# サービス層
def get_user_by_email(email: str):
    user = db.query(MailUser).filter_by(email=email).first()
    if not user:
        raise MailUserNotFoundError(f"User {email} not found")
    return user
```

### 6.2 フロントエンド
```typescript
// APIクライアント
try {
  const user = await mailserverApi.createUser(data);
  toast.success("ユーザーを作成しました");
} catch (error) {
  if (error.response?.status === 400) {
    toast.error(error.response.data.detail);
  } else {
    toast.error("予期しないエラーが発生しました");
    console.error(error);
  }
}
```

---

## 7. 並行稼働戦略

### 7.1 段階的移行

**Phase 1: 並行稼働開始**
```
Flask usermgmt (Port 5000) ─┐
                            ├─▶ MariaDB (mailserver_usermgmt)
Unified Portal (Port 8000) ─┘

両方とも同じDBにアクセス
管理者は両方使用可能
```

**Phase 2: 機能確認期間（1-2週間）**
```
- Unified Portalで全操作を試す
- Flask usermgmtは参照のみ使用
- 問題あればすぐFlaskに戻す
```

**Phase 3: 完全移行**
```
- Unified Portalのみ使用
- Flask usermgmtコンテナ停止（削除はしない）
```

### 7.2 ロールバック条件
以下の場合は即座にFlask usermgmtに戻す：
- データ不整合が発生
- パフォーマンス劣化（レスポンス > 3秒）
- 重大なバグ発見
- ユーザー操作が不可能

---

## 8. モニタリング・ログ

### 8.1 アプリケーションログ
```python
# Loguru設定
logger.add(
    "/var/log/unified-portal/app.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

# ログ出力例
logger.info(f"User created: {user.email}")
logger.warning(f"Failed login attempt: {username}")
logger.error(f"Database connection failed: {e}")
```

### 8.2 監査ログ
```python
# 全CRUD操作を記録
audit_service.log_audit(
    action="create",
    user_email=user.email,
    admin_ip=request.client.host,
    details=json.dumps({
        "quota": quota,
        "domain": domain.name
    })
)
```

### 8.3 メトリクス（将来実装）
- リクエスト数/秒
- レスポンスタイム（p50, p95, p99）
- エラー率
- データベース接続プール使用率

---

**次のステップ**: [03_TASK_BREAKDOWN.md](03_TASK_BREAKDOWN.md) でタスク分解を確認
