# API エンドポイント仕様 (API Specification)

**バージョン**: 1.0.0
**ベースURL**: `https://dell-workstation.tail67811d.ts.net/admin`
**認証**: Flask-Login セッションベース認証
**コンテンツタイプ**: `application/json` または `application/x-www-form-urlencoded`

---

## 📋 概要

このドキュメントは、メールユーザ管理システムの API エンドポイント仕様を定義します。

**認証方式**:
- すべての管理エンドポイントは Flask-Login による認証が必須
- セッション Cookie を使用したステートフル認証
- Tailscale VPN (100.0.0.0/10) からのアクセスのみ許可

**レスポンス形式**:
- 成功時: HTTP 200 OK, JSON レスポンス
- エラー時: HTTP 4xx/5xx, JSON エラーメッセージ

---

## 🔐 認証エンドポイント

### POST /login

管理者ログイン

**リクエスト**:
```http
POST /admin/login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=admin&password=SecurePassword123
```

**レスポンス (成功)**:
```http
HTTP/1.1 302 Found
Location: /admin/
Set-Cookie: session=...; HttpOnly; Secure; SameSite=Strict
```

**レスポンス (失敗)**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ログイン画面にエラーメッセージ表示 -->
  <div class="alert alert-danger">ユーザー名またはパスワードが正しくありません</div>
</html>
```

**エラーコード**:
- `401 Unauthorized` - 認証失敗

---

### GET /login

ログイン画面表示

**リクエスト**:
```http
GET /admin/login HTTP/1.1
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ログインフォーム -->
</html>
```

---

### POST /logout

ログアウト

**リクエスト**:
```http
POST /admin/logout HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 302 Found
Location: /admin/login
Set-Cookie: session=; Expires=Thu, 01 Jan 1970 00:00:00 GMT
```

**認証**: 必須

---

## 🏠 ダッシュボード

### GET /

ダッシュボード画面表示 (ドメイン一覧)

**リクエスト**:
```http
GET /admin/ HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ダッシュボード: ドメイン一覧、統計情報 -->
</html>
```

**表示内容**:
- ドメイン一覧 (ドメイン名、ユーザ数、合計容量)
- 新規ユーザ追加ボタン

**認証**: 必須

---

## 👤 ユーザ管理エンドポイント

### GET /users

全ユーザ一覧表示

**リクエスト**:
```http
GET /admin/users HTTP/1.1
Cookie: session=...
```

**クエリパラメータ**:
- `domain` (オプション): ドメイン名でフィルタリング (例: `?domain=kuma8088.com`)

**レスポンス (HTML)**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ユーザ一覧テーブル -->
</html>
```

**レスポンス (JSON)** (将来実装):
```json
{
  "users": [
    {
      "email": "test@kuma8088.com",
      "domain": "kuma8088.com",
      "quota": 1024,
      "enabled": true,
      "created_at": "2025-11-04T10:30:00Z"
    },
    {
      "email": "info@kuma8088.com",
      "domain": "kuma8088.com",
      "quota": 2048,
      "enabled": true,
      "created_at": "2025-11-04T11:00:00Z"
    }
  ],
  "total": 2
}
```

**認証**: 必須

---

### GET /users/new

新規ユーザ作成フォーム表示

**リクエスト**:
```http
GET /admin/users/new HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ユーザ作成フォーム -->
</html>
```

**認証**: 必須

---

### POST /users/new

新規ユーザ作成

**リクエスト**:
```http
POST /admin/users/new HTTP/1.1
Cookie: session=...
Content-Type: application/x-www-form-urlencoded

email=newuser@kuma8088.com&password=SecurePassword123!&quota=2048&csrf_token=...
```

**フォームフィールド**:
- `email` (必須): メールアドレス (形式: `localpart@domain`)
- `password` (必須): パスワード (最小8文字、複雑性要件あり)
- `quota` (オプション): メールボックス容量 (MB単位、デフォルト: 1024)
- `csrf_token` (必須): CSRF トークン

**レスポンス (成功)**:
```http
HTTP/1.1 302 Found
Location: /admin/users?domain=kuma8088.com
```

Flash メッセージ: `ユーザ newuser@kuma8088.com を作成しました`

**レスポンス (エラー)**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- フォーム再表示 + エラーメッセージ -->
  <div class="alert alert-danger">このメールアドレスは既に登録されています</div>
</html>
```

**バリデーションエラー**:
- `400 Bad Request` - 必須フィールド欠落、形式不正
- `409 Conflict` - メールアドレス重複
- `422 Unprocessable Entity` - パスワードポリシー違反

**認証**: 必須

**監査ログ**: 作成成功時に `audit_logs` テーブルに記録

---

### GET /users/<email>/edit

ユーザ編集フォーム表示

**リクエスト**:
```http
GET /admin/users/test@kuma8088.com/edit HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ユーザ編集フォーム (既存データ入力済み) -->
</html>
```

**認証**: 必須

---

### POST /users/<email>/edit

ユーザ情報更新

**リクエスト**:
```http
POST /admin/users/test@kuma8088.com/edit HTTP/1.1
Cookie: session=...
Content-Type: application/x-www-form-urlencoded

quota=2048&enabled=true&csrf_token=...
```

**フォームフィールド**:
- `quota` (オプション): メールボックス容量 (MB単位)
- `enabled` (オプション): アカウント有効/無効 (true/false)
- `csrf_token` (必須): CSRF トークン

**レスポンス (成功)**:
```http
HTTP/1.1 302 Found
Location: /admin/users?domain=kuma8088.com
```

Flash メッセージ: `ユーザ test@kuma8088.com を更新しました`

**レスポンス (エラー)**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "ユーザが見つかりません"
}
```

**認証**: 必須

**監査ログ**: 更新成功時に記録

---

### POST /users/<email>/delete

ユーザ削除

**リクエスト**:
```http
POST /admin/users/test@kuma8088.com/delete HTTP/1.1
Cookie: session=...
Content-Type: application/x-www-form-urlencoded

csrf_token=...
```

**レスポンス (成功)**:
```http
HTTP/1.1 302 Found
Location: /admin/users
```

Flash メッセージ: `ユーザ test@kuma8088.com を削除しました`

**レスポンス (エラー)**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "ユーザが見つかりません"
}
```

**認証**: 必須

**監査ログ**: 削除成功時に記録

**⚠️ 警告**: 削除は取り消しできません。メールボックスデータは手動で削除する必要があります。

---

### GET /users/<email>/password

パスワード変更フォーム表示

**リクエスト**:
```http
GET /admin/users/test@kuma8088.com/password HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- パスワード変更フォーム -->
</html>
```

**認証**: 必須

---

### POST /users/<email>/password

パスワード変更

**リクエスト**:
```http
POST /admin/users/test@kuma8088.com/password HTTP/1.1
Cookie: session=...
Content-Type: application/x-www-form-urlencoded

new_password=NewSecurePassword123!&confirm_password=NewSecurePassword123!&csrf_token=...
```

**フォームフィールド**:
- `new_password` (必須): 新しいパスワード
- `confirm_password` (必須): パスワード確認 (new_password と一致必須)
- `csrf_token` (必須): CSRF トークン

**レスポンス (成功)**:
```http
HTTP/1.1 302 Found
Location: /admin/users?domain=kuma8088.com
```

Flash メッセージ: `パスワードを変更しました`

**レスポンス (エラー)**:
```http
HTTP/1.1 400 Bad Request
Content-Type: text/html

<html>
  <div class="alert alert-danger">パスワードが一致しません</div>
</html>
```

**バリデーションエラー**:
- `400 Bad Request` - パスワード不一致、パスワードポリシー違反

**認証**: 必須

**監査ログ**: 変更成功時に記録

---

## 🏢 ドメイン管理エンドポイント

### GET /domains

ドメイン一覧表示

**リクエスト**:
```http
GET /admin/domains HTTP/1.1
Cookie: session=...
```

**レスポンス (HTML)**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ドメイン一覧テーブル -->
</html>
```

**レスポンス (JSON)** (将来実装):
```json
{
  "domains": [
    {
      "name": "kuma8088.com",
      "description": "メインドメイン",
      "user_count": 2,
      "total_quota": 3072,
      "default_quota": 1024,
      "created_at": "2025-11-04T10:00:00Z"
    }
  ],
  "total": 1
}
```

**認証**: 必須

---

### GET /domains/<domain>

ドメイン詳細表示 (ドメイン別ユーザ一覧)

**リクエスト**:
```http
GET /admin/domains/kuma8088.com HTTP/1.1
Cookie: session=...
```

**レスポンス**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <!-- ドメイン詳細: ユーザ一覧、統計情報 -->
</html>
```

**認証**: 必須

---

## ⚙️ システムエンドポイント

### GET /health

ヘルスチェック (Docker healthcheck 用)

**リクエスト**:
```http
GET /admin/health HTTP/1.1
```

**レスポンス (正常)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "service": "mailserver-usermgmt",
  "version": "1.0.0",
  "database": "connected"
}
```

**レスポンス (異常)**:
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "unhealthy",
  "service": "mailserver-usermgmt",
  "version": "1.0.0",
  "error": "Database connection failed"
}
```

**認証**: 不要

---

## 📊 データモデル

### User (ユーザ)

```json
{
  "id": 1,
  "email": "test@kuma8088.com",
  "domain_id": 1,
  "password_hash": "{SHA512-CRYPT}$6$...",
  "quota": 1024,
  "uid": 5000,
  "gid": 5000,
  "maildir": "/var/mail/vhosts/kuma8088.com/test",
  "enabled": true,
  "created_at": "2025-11-04T10:30:00Z",
  "updated_at": "2025-11-04T10:30:00Z"
}
```

### Domain (ドメイン)

```json
{
  "id": 1,
  "name": "kuma8088.com",
  "description": "メインドメイン",
  "default_quota": 1024,
  "created_at": "2025-11-04T10:00:00Z",
  "updated_at": "2025-11-04T10:00:00Z"
}
```

### AuditLog (監査ログ)

```json
{
  "id": 1,
  "action": "create",
  "user_email": "test@kuma8088.com",
  "admin_ip": "100.64.0.5",
  "details": {
    "quota": 1024,
    "domain": "kuma8088.com"
  },
  "created_at": "2025-11-04T10:30:00Z"
}
```

---

## 🔒 セキュリティ

### 認証

- **セッションベース認証**: Flask-Login による Cookie ベース認証
- **セッション Cookie 設定**:
  - `HttpOnly`: JavaScript からのアクセス防止
  - `Secure`: HTTPS 接続のみ
  - `SameSite=Strict`: CSRF 攻撃防止

### CSRF 保護

- すべての POST/PUT/DELETE リクエストには CSRF トークンが必須
- Flask-WTF による自動 CSRF 検証

### アクセス制限

- **Tailscale VPN 必須**: Nginx で `100.0.0.0/10` からのアクセスのみ許可
- **HTTPS 強制**: HTTP リクエストは自動的に HTTPS にリダイレクト

### パスワードセキュリティ

- **ハッシュ方式**: SHA512-CRYPT (Dovecot 互換)
- **パスワードポリシー**:
  - 最小長: 8文字
  - 複雑性: 英大文字、英小文字、数字、記号のうち3種類以上

---

## 🚨 エラーコード

| コード | 説明 |
|-------|------|
| `200 OK` | リクエスト成功 |
| `302 Found` | リダイレクト (成功時のフォーム送信) |
| `400 Bad Request` | リクエストパラメータ不正 |
| `401 Unauthorized` | 認証失敗 |
| `403 Forbidden` | Tailscale VPN 外からのアクセス |
| `404 Not Found` | ユーザまたはドメインが見つからない |
| `409 Conflict` | メールアドレス重複 |
| `422 Unprocessable Entity` | バリデーションエラー |
| `500 Internal Server Error` | サーバーエラー |
| `503 Service Unavailable` | サービス停止中 (データベース接続失敗等) |

---

## 📝 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0.0 | 2025-11-05 | 初版作成 |

---

## 🔗 関連ドキュメント

- **プロジェクト概要**: `README.md`
- **開発進捗**: `DEVELOPMENT.md`
- **変更履歴**: `CHANGELOG.md`
- **設計書**: `../../Docs/application/mailserver/05_user_management_design.md`
