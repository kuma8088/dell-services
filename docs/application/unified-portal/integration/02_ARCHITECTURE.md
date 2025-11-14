# アーキテクチャ設計書

**プロジェクト**: Unified Portal - Mailserver統合 + DNS管理強化

**バージョン**: 1.0

**作成日**: 2025-11-14

---

## 1. システム概要

### 1.1 アーキテクチャスタイル
- **3層アーキテクチャ**: プレゼンテーション層、ビジネスロジック層、データアクセス層
- **マイクロサービス的分離**: 各機能（Mailserver、DNS、Docker等）を独立モジュールで実装
- **RESTful API**: HTTPベースの標準的なAPI設計
- **SPA（Single Page Application）**: React製フロントエンド

### 1.2 システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet / User                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Cloudflare Tunnel                           │
│                  (HTTPS, admin.kuma8088.com)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Dell WorkStation (Rocky Linux 9.6)           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           Docker Compose: unified-portal                  │ │
│  │                                                            │ │
│  │  ┌──────────────────┐      ┌──────────────────┐          │ │
│  │  │  Nginx           │      │  Frontend        │          │ │
│  │  │  (Reverse Proxy) │─────▶│  (React + Vite)  │          │ │
│  │  │  Port: 80/443    │      │  Port: 5173      │          │ │
│  │  └──────┬───────────┘      └──────────────────┘          │ │
│  │         │                                                  │ │
│  │         ▼                                                  │ │
│  │  ┌──────────────────┐                                     │ │
│  │  │  Backend         │                                     │ │
│  │  │  (FastAPI)       │                                     │ │
│  │  │  Port: 8000      │                                     │ │
│  │  └──────┬───────────┘                                     │ │
│  │         │                                                  │ │
│  │         ├────────────────────────────────────────────┐    │ │
│  │         │                │                │          │    │ │
│  │         ▼                ▼                ▼          ▼    │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐  ┌──────┐ │ │
│  │  │ MariaDB  │    │ Docker   │    │Cloudflare│  │ wp-  │ │ │
│  │  │ (Mail)   │    │ Engine   │    │ API      │  │ cli  │ │ │
│  │  │172.20.0.60│    │ (Unix    │    │ (HTTPS)  │  │      │ │ │
│  │  └──────────┘    │ Socket)  │    └──────────┘  └──────┘ │ │
│  │                  └──────────┘                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │        既存システム（変更なし・並行稼働）                    │ │
│  │                                                            │ │
│  │  ┌──────────────────┐      ┌──────────────────┐          │ │
│  │  │ Flask usermgmt   │      │ MariaDB          │          │ │
│  │  │ Port: 5000       │─────▶│ (mailserver_     │          │ │
│  │  │ (既存・並行稼働)  │      │  usermgmt)       │          │ │
│  │  └──────────────────┘      │ 172.20.0.60:3306 │          │ │
│  │                            └──────────────────┘          │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
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
│   │   └── mailserver/      # Mailserver固有コンポーネント（NEW）
│   │       ├── UserTable.tsx
│   │       ├── UserForm.tsx
│   │       ├── DomainTable.tsx
│   │       ├── DomainForm.tsx
│   │       └── AuditLogTable.tsx
│   ├── pages/               # ページコンポーネント
│   │   ├── Dashboard.tsx            # 既存
│   │   ├── DomainManagement.tsx     # 既存（強化）
│   │   ├── MailUserManagement.tsx   # NEW
│   │   ├── MailDomainManagement.tsx # NEW
│   │   └── AuditLogs.tsx            # NEW
│   ├── lib/                 # ユーティリティ
│   │   ├── api.ts           # ベースAPIクライアント（既存）
│   │   ├── domains-api.ts   # Cloudflare DNS API（既存）
│   │   └── mailserver-api.ts # Mailserver API（NEW）
│   ├── contexts/
│   │   └── AuthContext.tsx  # 認証コンテキスト（既存・強化）
│   ├── hooks/               # カスタムフック
│   │   ├── useMailUsers.ts  # NEW
│   │   └── useMailDomains.ts # NEW
│   └── types/               # TypeScript型定義
│       └── mailserver.ts    # NEW
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
│   │   └── audit_log.py     # NEW
│   ├── schemas/             # Pydanticスキーマ
│   │   ├── __init__.py
│   │   └── mailserver.py    # NEW（リクエスト/レスポンス）
│   ├── routers/             # APIルーター
│   │   ├── __init__.py
│   │   ├── auth.py          # 既存（強化予定）
│   │   ├── domains.py       # 既存（Cloudflare DNS）
│   │   └── mailserver.py    # NEW
│   ├── services/            # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── mail_user_service.py   # NEW
│   │   ├── mail_domain_service.py # NEW
│   │   └── audit_service.py       # NEW
│   ├── database.py          # 既存（DB接続設定）
│   ├── config.py            # 既存（環境変数）
│   ├── auth.py              # 既存（JWT認証）
│   └── main.py              # 既存（エントリーポイント）
├── tests/                   # テスト
│   ├── test_mailserver_router.py  # NEW
│   ├── test_mail_user_service.py  # NEW
│   └── test_mail_domain_service.py # NEW
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
    mail_db_user: str = "usermgmt"
    mail_db_password: str

    @property
    def mail_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mail_db_user}:{self.mail_db_password}"
            f"@{self.mail_db_host}:{self.mail_db_port}/{self.mail_db_name}"
        )
```

**database.py 更新内容**
```python
# 既存のengineに加え、Mailserver用engineを追加
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

**ハッシュアルゴリズム**
```python
# Dovecot互換SHA512-CRYPT
from passlib.hash import sha512_crypt

def hash_password(password: str) -> str:
    return sha512_crypt.hash(password, rounds=5000)

def verify_password(plain_password: str, hashed: str) -> bool:
    return sha512_crypt.verify(plain_password, hashed)
```

**パスワードポリシー**
- 最小長: 8文字
- 推奨: 英大文字、英小文字、数字、記号を含む
- フロントエンドでリアルタイムバリデーション

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
