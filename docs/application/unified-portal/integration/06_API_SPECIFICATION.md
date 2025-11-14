# API仕様書（簡易版）

**プロジェクト**: Unified Portal - Mailserver統合

**ベースURL**: `https://admin.kuma8088.com/api/v1`

**認証**: JWT Bearer Token（全エンドポイント共通）

**作成日**: 2025-11-14

---

## 📋 エンドポイント一覧

### 1. メールユーザー管理

#### 1.1 ユーザー一覧取得
```
GET /mailserver/users
Query Parameters:
  - domain_id (optional): ドメインID
  - skip (optional): オフセット（default: 0）
  - limit (optional): 取得件数（default: 20）
  - search (optional): 検索文字列（email部分一致）
  - enabled (optional): 有効/無効フィルタ

Response: 200 OK
{
  "users": [
    {
      "id": 1,
      "email": "user@kuma8088.com",
      "domain_id": 1,
      "domain_name": "kuma8088.com",
      "quota": 1024,
      "enabled": true,
      "is_admin": false,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 100
}
```

#### 1.2 ユーザー作成
```
POST /mailserver/users
Body:
{
  "email": "newuser@kuma8088.com",
  "password": "SecurePass123!",
  "domain_id": 1,
  "quota": 1024,
  "enabled": true
}

Response: 201 Created
{
  "id": 2,
  "email": "newuser@kuma8088.com",
  ...
}
```

#### 1.3 ユーザー更新
```
PUT /mailserver/users/{email}
Body:
{
  "quota": 2048,
  "enabled": false
}

Response: 200 OK
```

#### 1.4 ユーザー削除
```
DELETE /mailserver/users/{email}
Response: 204 No Content
```

#### 1.5 パスワード変更
```
POST /mailserver/users/{email}/password
Body:
{
  "new_password": "NewSecurePass456!"
}

Response: 200 OK
```

#### 1.6 有効/無効切替
```
POST /mailserver/users/{email}/toggle
Response: 200 OK
```

---

### 2. メールドメイン管理

#### 2.1 ドメイン一覧取得
```
GET /mailserver/domains
Response: 200 OK
{
  "domains": [
    {
      "id": 1,
      "name": "kuma8088.com",
      "description": "Main domain",
      "default_quota": 1024,
      "enabled": true,
      "user_count": 5
    }
  ]
}
```

#### 2.2 ドメイン作成
```
POST /mailserver/domains
Body:
{
  "name": "newdomain.com",
  "description": "New domain",
  "default_quota": 1024,
  "enabled": true
}

Response: 201 Created
```

#### 2.3 ドメイン更新/削除
```
PUT /mailserver/domains/{id}
DELETE /mailserver/domains/{id}
```

---

### 3. 監査ログ

#### 3.1 ログ一覧取得
```
GET /mailserver/audit-logs
Query Parameters:
  - start_date (optional): 開始日時
  - end_date (optional): 終了日時
  - action (optional): 操作種別フィルタ
  - user_email (optional): 対象ユーザーフィルタ

Response: 200 OK
{
  "logs": [
    {
      "id": 1,
      "action": "create",
      "user_email": "user@kuma8088.com",
      "admin_ip": "192.168.1.100",
      "details": "{\"quota\": 1024}",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### 4. 管理者管理

#### 4.1 管理者一覧取得
```
GET /admin-users
Response: 200 OK
{
  "admin_users": [
    {
      "id": 1,
      "email": "admin@kuma8088.com",
      "role": "super_admin",
      "enabled": true,
      "last_login": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### 4.2 管理者作成
```
POST /admin-users
Body:
{
  "email": "newadmin@kuma8088.com",
  "password": "AdminPass123!",
  "role": "admin",
  "enabled": true
}

Response: 201 Created
```

---

### 5. パスワード再設定

#### 5.1 リセットリクエスト
```
POST /password-reset/request
Body:
{
  "email": "user@kuma8088.com"
}

Response: 200 OK
{
  "message": "リセットリンクをメールで送信しました"
}

Side Effect:
- リセットトークン生成（有効期限1時間）
- メール送信（noreply@kuma8088.com）
```

#### 5.2 トークン検証
```
POST /password-reset/verify
Body:
{
  "token": "uuid-token-here"
}

Response: 200 OK
{
  "valid": true,
  "email": "user@kuma8088.com"
}

Response: 400 Bad Request
{
  "detail": "トークンが無効または期限切れです"
}
```

#### 5.3 パスワードリセット実行
```
POST /password-reset/reset
Body:
{
  "token": "uuid-token-here",
  "new_password": "NewSecurePass789!"
}

Response: 200 OK
{
  "message": "パスワードをリセットしました"
}

Side Effect:
- パスワード更新
- トークンを使用済みに設定
- 成功通知メール送信
```

---

### 6. DNS管理（既存強化）

#### 6.1 DNSレコード編集
```
PUT /domains/zones/{zone_id}/records/{record_id}
Body:
{
  "type": "A",
  "name": "subdomain",
  "content": "192.0.2.1",
  "ttl": 3600,
  "proxied": true
}

Response: 200 OK
```

#### 6.2 DNS検証
```
POST /domains/dns/verify
Body:
{
  "name": "example.com",
  "type": "A"
}

Response: 200 OK
{
  "result": "192.0.2.1\n192.0.2.2",
  "query_time_ms": 15
}
```

---

## 🔒 認証

### JWTトークン取得
```
POST /auth/login
Body:
{
  "username": "admin@kuma8088.com",
  "password": "password"
}

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 認証ヘッダー
```
Authorization: Bearer <access_token>
```

---

## 7. WordPress管理

### 7.1 サイト一覧取得
```
GET /wordpress/sites
Query Parameters:
  - skip (optional): オフセット（default: 0）
  - limit (optional): 取得件数（default: 20）

Response: 200 OK
{
  "sites": [
    {
      "id": 1,
      "site_name": "kuma8088",
      "domain": "kuma8088.com",
      "database_name": "wp_kuma8088",
      "php_version": "8.2",
      "enabled": true,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 16
}
```

### 7.2 サイト作成
```
POST /wordpress/sites
Body:
{
  "site_name": "newsite",
  "domain": "newsite.kuma8088.com",
  "database_option": "auto",  // "auto" or "existing"
  "database_name": "wp_newsite",  // database_option="existing" の場合必須
  "php_version": "8.2",
  "admin_user": "admin",
  "admin_password": "SecurePass123!",
  "admin_email": "admin@kuma8088.com"
}

Response: 201 Created
{
  "id": 17,
  "site_name": "newsite",
  "domain": "newsite.kuma8088.com",
  "database_name": "wp_newsite",
  "php_version": "8.2",
  "enabled": true,
  "created_at": "2025-11-14T12:00:00Z"
}

Side Effect:
- データベース作成（database_option="auto" の場合）
- wp-cli core install実行
- WP Mail SMTP自動設定
- Nginx設定生成 + nginx -s reload
```

### 7.3 サイト更新（PHPバージョン切り替え）
```
PUT /wordpress/sites/{site_name}
Body:
{
  "domain": "kuma8088.com",  // optional
  "php_version": "8.1",  // PHPバージョン変更時にNginx再生成
  "enabled": false  // optional
}

Response: 200 OK

Side Effect (php_version変更時):
- Nginx設定再生成（fastcgi_pass変更）
- nginx -t 実行
- nginx -s reload 実行（ダウンタイムなし）
```

### 7.4 サイト削除
```
DELETE /wordpress/sites/{site_name}
Response: 204 No Content

Side Effect:
- wp-cli core uninstall実行
- Nginx設定削除
- wordpress_sitesテーブルから削除
```

---

## 8. Database管理

### 8.1 データベース一覧取得
```
GET /database/databases
Query Parameters:
  - target (required): "blog" or "mailserver"

Response: 200 OK
{
  "databases": [
    {
      "name": "wp_kuma8088",
      "charset": "utf8mb4",
      "size_mb": 120.5,
      "table_count": 15
    },
    {
      "name": "wp_demo1",
      "charset": "utf8mb4",
      "size_mb": 45.2,
      "table_count": 12
    }
  ],
  "total": 16
}
```

### 8.2 データベース作成
```
POST /database/databases
Body:
{
  "name": "wp_newsite",
  "charset": "utf8mb4",
  "target": "blog"
}

Response: 201 Created
{
  "name": "wp_newsite",
  "charset": "utf8mb4",
  "username": "wp_newsite_user",
  "created_at": "2025-11-14T12:00:00Z"
}

Side Effect:
- CREATE DATABASE実行
- 専用ユーザー作成（{name}_user）
- GRANT ALL PRIVILEGES実行
- パスワード暗号化保存（db_credentials）
```

### 8.3 データベース削除
```
DELETE /database/databases/{name}
Query Parameters:
  - target (required): "blog" or "mailserver"

Response: 204 No Content
```

### 8.4 データベースユーザー一覧
```
GET /database/users
Query Parameters:
  - target (required): "blog" or "mailserver"

Response: 200 OK
{
  "users": [
    {
      "username": "wp_kuma8088_user",
      "host": "%",
      "privileges": ["SELECT", "INSERT", "UPDATE", "DELETE"]
    }
  ]
}
```

### 8.5 データベースユーザー作成
```
POST /database/users
Body:
{
  "username": "newuser",
  "password": "SecurePass123!",
  "database_name": "wp_newsite",
  "target": "blog"
}

Response: 201 Created

Side Effect:
- CREATE USER実行
- パスワード暗号化保存（db_credentials）
```

### 8.6 SQLクエリ実行
```
POST /database/query
Body:
{
  "query": "SELECT * FROM wp_posts LIMIT 10",
  "target": "blog",
  "database_name": "wp_kuma8088"
}

Response: 200 OK
{
  "result": [
    {"id": 1, "post_title": "Hello World", ...}
  ],
  "row_count": 10,
  "execution_time_ms": 15
}

制限:
- SELECT文のみ許可（デフォルト）
- INSERT/UPDATE/DELETE: Super Adminのみ
- DROP/ALTER: 実行不可
```

---

## 9. PHP管理

### 9.1 PHPバージョン一覧
```
GET /php/versions

Response: 200 OK
{
  "versions": [
    {
      "version": "7.4",
      "status": "running",
      "site_count": 2,
      "container_id": "php74-fpm-1"
    },
    {
      "version": "8.0",
      "status": "running",
      "site_count": 5,
      "container_id": "php80-fpm-1"
    },
    {
      "version": "8.1",
      "status": "running",
      "site_count": 4,
      "container_id": "php81-fpm-1"
    },
    {
      "version": "8.2",
      "status": "running",
      "site_count": 5,
      "container_id": "php82-fpm-1"
    }
  ]
}
```

### 9.2 PHPバージョン追加
```
POST /php/versions
Body:
{
  "version": "8.3"
}

Response: 201 Created
{
  "version": "8.3",
  "status": "running",
  "site_count": 0
}

Side Effect:
- docker-compose.ymlにphp-fpmサービス追加
- docker compose up -d実行
- ヘルスチェック
```

### 9.3 PHPバージョン削除
```
DELETE /php/versions/{version}

Response: 204 No Content

前提条件:
- site_count == 0（使用サイト数0）

Side Effect:
- docker compose stop php{version}-fpm
- docker-compose.ymlから削除
```

### 9.4 PHP設定取得
```
GET /php/versions/{version}/config

Response: 200 OK
{
  "php_ini": "memory_limit = 256M\nupload_max_filesize = 64M\n...",
  "fpm_config": "pm = dynamic\npm.max_children = 50\n..."
}
```

### 9.5 PHP設定更新
```
PUT /php/versions/{version}/config
Body:
{
  "php_ini": "memory_limit = 512M\n..."
}

Response: 200 OK

Side Effect:
- php.ini書き込み
- docker compose restart php{version}-fpm
```

---

## ⚠️ エラーレスポンス

### 400 Bad Request
```json
{
  "detail": "バリデーションエラー: emailが不正です"
}
```

### 401 Unauthorized
```json
{
  "detail": "認証が必要です"
}
```

### 403 Forbidden
```json
{
  "detail": "権限がありません"
}
```

### 404 Not Found
```json
{
  "detail": "ユーザーが見つかりません"
}
```

### 500 Internal Server Error
```json
{
  "detail": "サーバーエラーが発生しました"
}
```

---

**参照**: [02_ARCHITECTURE.md](02_ARCHITECTURE.md) - アーキテクチャ詳細
