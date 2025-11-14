# タスク分解書（Web側/ローカル側明記）

**プロジェクト**: Unified Portal - Mailserver統合 + DNS管理強化

**バージョン**: 1.0

**作成日**: 2025-11-14

---

## 📊 タスクサマリー

| カテゴリ | Web側 | ローカル側 | 合計 |
|---------|-------|-----------|------|
| **Phase 1: Mailserver統合** | 25 | 8 | 33 |
| **Phase 2: DNS管理強化** | 10 | 2 | 12 |
| **Phase 3: テスト** | 5 | 5 | 10 |
| **Phase 4: デプロイ** | 0 | 8 | 8 |
| **合計** | **40** | **23** | **63** |

**Web側実行時間**: 約6-8時間（Claude Code on the web）
**ローカル側実行時間**: 約4-6時間（Dell WorkStation）

---

## 🌐 Web側タスク（Claude Code on the webで実行可能）

### Phase 1-W: Mailserver統合 - バックエンド実装

#### W-001: SQLAlchemyモデル作成
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/backend/app/models/mail_user.py`（NEW）

**内容**:
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class MailUser(Base):
    __tablename__ = "users"  # 既存テーブル名

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    maildir = Column(String(500), nullable=False)
    quota = Column(Integer, default=1024)
    uid = Column(Integer, default=5000)
    gid = Column(Integer, default=5000)
    enabled = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    domain = relationship("MailDomain", back_populates="users")
```

**依存**: なし
**検証**: ファイル作成確認のみ（Pythonシンタックスチェック）

---

#### W-002: MailDomainモデル作成
**実行場所**: 🌐 Web側
**所要時間**: 20分

**ファイル**: `services/unified-portal/backend/app/models/mail_domain.py`（NEW）

**依存**: なし

---

#### W-003: AuditLogモデル作成
**実行場所**: 🌐 Web側
**所要時間**: 15分

**ファイル**: `services/unified-portal/backend/app/models/audit_log.py`（NEW）

**依存**: なし

---

#### W-004: Pydanticスキーマ作成
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/backend/app/schemas/mailserver.py`（NEW）

**内容**:
```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# リクエストスキーマ
class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    domain_id: int
    quota: int = Field(default=1024, ge=100, le=10000)
    enabled: bool = True

class UserUpdateRequest(BaseModel):
    quota: Optional[int] = Field(None, ge=100, le=10000)
    enabled: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8)

# レスポンススキーマ
class UserResponse(BaseModel):
    id: int
    email: str
    domain_id: int
    domain_name: str  # JOIN結果
    quota: int
    enabled: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy ORM対応
```

**依存**: なし

---

#### W-005: MailUserService実装
**実行場所**: 🌐 Web側
**所要時間**: 90分

**ファイル**: `services/unified-portal/backend/app/services/mail_user_service.py`（NEW）

**内容**:
- `list_users()`: 一覧取得（ページング、フィルタ、ソート）
- `get_user_by_email()`: 詳細取得
- `create_user()`: 作成（パスワードハッシュ、maildir生成、監査ログ）
- `update_user()`: 更新
- `delete_user()`: 削除
- `change_password()`: パスワード変更
- `toggle_status()`: 有効/無効切替

**依存**: W-001, W-002, W-003, W-004

---

#### W-006: MailDomainService実装
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/backend/app/services/mail_domain_service.py`（NEW）

**依存**: W-002, W-003

---

#### W-007: AuditService実装
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/backend/app/services/audit_service.py`（NEW）

**依存**: W-003

---

#### W-008: Mailserver APIルーター実装
**実行場所**: 🌐 Web側
**所要時間**: 90分

**ファイル**: `services/unified-portal/backend/app/routers/mailserver.py`（NEW）

**内容**: 全エンドポイント実装（詳細は06_API_SPECIFICATION.md参照）

**依存**: W-005, W-006, W-007

---

#### W-009: database.py更新（Mail DB接続追加）
**実行場所**: 🌐 Web側
**所要時間**: 20分

**ファイル**: `services/unified-portal/backend/app/database.py`（既存更新）

**追加内容**:
```python
from app.config import get_settings

settings = get_settings()

# 既存のengineに加え、Mailserver用を追加
mail_engine = create_engine(
    settings.mail_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

MailSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mail_engine)

def get_mail_db():
    db = MailSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**依存**: W-010

---

#### W-010: config.py更新（Mail DB設定追加）
**実行場所**: 🌐 Web側
**所要時間**: 15分

**ファイル**: `services/unified-portal/backend/app/config.py`（既存更新）

**追加内容**:
```python
class Settings(BaseSettings):
    # ... 既存設定 ...

    # Mailserver Database
    mail_db_host: str = "172.20.0.60"
    mail_db_port: int = 3306
    mail_db_name: str = "mailserver_usermgmt"
    mail_db_user: str = "usermgmt"
    mail_db_password: str  # .envから読み込み

    @property
    def mail_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mail_db_user}:{self.mail_db_password}"
            f"@{self.mail_db_host}:{self.mail_db_port}/{self.mail_db_name}"
        )
```

**依存**: なし

---

#### W-011: main.py更新（ルーター登録）
**実行場所**: 🌐 Web側
**所要時間**: 5分

**ファイル**: `services/unified-portal/backend/app/main.py`（既存更新）

**追加内容**:
```python
from app.routers import mailserver

app.include_router(mailserver.router)
```

**依存**: W-008

---

#### W-012: requirements.txt更新
**実行場所**: 🌐 Web側
**所要時間**: 5分

**ファイル**: `services/unified-portal/backend/requirements.txt`（既存更新）

**追加内容**:
```
pymysql==1.1.0
passlib==1.7.4
```

**依存**: なし

---

### Phase 1-W: Mailserver統合 - フロントエンド実装

#### W-013: TypeScript型定義作成
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/types/mailserver.ts`（NEW）

**内容**:
```typescript
export interface MailUser {
  id: number;
  email: string;
  domain_id: number;
  domain_name: string;
  quota: number;
  enabled: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface MailDomain {
  id: number;
  name: string;
  description?: string;
  default_quota: number;
  enabled: boolean;
  user_count: number;
}

export interface AuditLog {
  id: number;
  action: string;
  user_email: string;
  admin_ip: string;
  details: string;
  created_at: string;
}

export interface UserCreateData {
  email: string;
  password: string;
  domain_id: number;
  quota?: number;
  enabled?: boolean;
}

export interface UserUpdateData {
  quota?: number;
  enabled?: boolean;
}
```

**依存**: なし

---

#### W-014: Mailserver APIクライアント作成
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/frontend/src/lib/mailserver-api.ts`（NEW）

**内容**: 全APIエンドポイントのクライアント関数

**依存**: W-013

---

#### W-015: UserTableコンポーネント作成
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/UserTable.tsx`（NEW）

**依存**: W-013

---

#### W-016: UserFormコンポーネント作成
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/UserForm.tsx`（NEW）

**依存**: W-013

---

#### W-017: DomainTableコンポーネント作成
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/DomainTable.tsx`（NEW）

**依存**: W-013

---

#### W-018: DomainFormコンポーネント作成
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/DomainForm.tsx`（NEW）

**依存**: W-013

---

#### W-019: AuditLogTableコンポーネント作成
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/AuditLogTable.tsx`（NEW）

**依存**: W-013

---

#### W-020: MailUserManagementページ作成
**実行場所**: 🌐 Web側
**所要時間**: 90分

**ファイル**: `services/unified-portal/frontend/src/pages/MailUserManagement.tsx`（NEW）

**内容**: ユーザー管理ページ（一覧、作成、編集、削除、パスワード変更、有効/無効切替）

**依存**: W-014, W-015, W-016

---

#### W-021: MailDomainManagementページ作成
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/frontend/src/pages/MailDomainManagement.tsx`（NEW）

**依存**: W-014, W-017, W-018

---

#### W-022: AuditLogsページ作成
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/frontend/src/pages/AuditLogs.tsx`（NEW）

**依存**: W-014, W-019

---

#### W-023: App.tsxルーティング追加
**実行場所**: 🌐 Web側
**所要時間**: 10分

**ファイル**: `services/unified-portal/frontend/src/App.tsx`（既存更新）

**追加内容**:
```typescript
<Route path="/mail/users" element={<MailUserManagement />} />
<Route path="/mail/domains" element={<MailDomainManagement />} />
<Route path="/mail/audit-logs" element={<AuditLogs />} />
```

**依存**: W-020, W-021, W-022

---

#### W-024: Layout.tsxナビゲーション追加
**実行場所**: 🌐 Web側
**所要時間**: 10分

**ファイル**: `services/unified-portal/frontend/src/components/layout/Layout.tsx`（既存更新）

**追加内容**: サイドバーに「メール管理」セクション追加

**依存**: W-023

---

#### W-025: useMailUsersカスタムフック作成
**実行場所**: 🌐 Web側
**所要時間**: 20分

**ファイル**: `services/unified-portal/frontend/src/hooks/useMailUsers.ts`（NEW）

**内容**: TanStack Query統合、キャッシング、自動再フェッチ

**依存**: W-014

---

### Phase 2-W: DNS管理強化（#017）

#### W-026: DomainManagement強化 - Cloudflareリンクボタン追加
**実行場所**: 🌐 Web側
**所要時間**: 15分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**追加内容**:
```typescript
<Button
  variant="outline"
  onClick={() => window.open(
    `https://dash.cloudflare.com/${zone.id}/dns`,
    '_blank'
  )}
>
  Cloudflareで管理 <ExternalLink className="ml-2 h-4 w-4" />
</Button>
```

**依存**: なし

---

#### W-027: DNSレコード編集機能実装（バックエンド）
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/backend/app/routers/domains.py`（既存更新）

**追加内容**:
```python
@router.put("/zones/{zone_id}/records/{record_id}")
async def update_dns_record(
    zone_id: str,
    record_id: str,
    data: DnsRecordUpdateRequest
):
    # Cloudflare API呼び出し
    ...
```

**依存**: なし

---

#### W-028: DNSレコード編集機能実装（フロントエンド）
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**追加内容**: 編集ダイアログ、フォーム、バリデーション

**依存**: W-027

---

#### W-029: バルク操作実装（複数レコード削除）
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**追加内容**: チェックボックス選択、一括削除ボタン

**依存**: W-028

---

#### W-030: CSVエクスポート機能実装
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**追加内容**:
```typescript
const exportToCsv = () => {
  const csv = records.map(r =>
    `${r.type},${r.name},${r.content},${r.ttl},${r.proxied}`
  ).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  // ダウンロード処理
};
```

**依存**: W-029

---

#### W-031: CSVインポート機能実装（バックエンド）
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/backend/app/routers/domains.py`（既存更新）

**追加内容**:
```python
@router.post("/zones/{zone_id}/records/import")
async def import_dns_records(
    zone_id: str,
    file: UploadFile
):
    # CSV解析 + バリデーション + 一括作成
    ...
```

**依存**: なし

---

#### W-032: CSVインポート機能実装（フロントエンド）
**実行場所**: 🌐 Web側
**所要時間**: 45分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**依存**: W-031

---

#### W-033: DNS検証ツール実装（バックエンド）
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/backend/app/routers/domains.py`（既存更新）

**追加内容**:
```python
@router.post("/dns/verify")
async def verify_dns_record(data: DnsVerifyRequest):
    import subprocess
    result = subprocess.run(
        ['dig', '+short', data.name, data.type],
        capture_output=True, text=True
    )
    return {"result": result.stdout}
```

**依存**: なし

---

#### W-034: DNS検証ツール実装（フロントエンド）
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**依存**: W-033

---

#### W-035: DNSレコード編集履歴表示（監査ログ統合）
**実行場所**: 🌐 Web側
**所要時間**: 30分

**ファイル**: `services/unified-portal/frontend/src/pages/DomainManagement.tsx`（既存更新）

**内容**: 監査ログから DNS 関連操作を表示

**依存**: W-022

---

### Phase 3-W: テストコード作成

#### W-036: バックエンドユニットテスト作成
**実行場所**: 🌐 Web側
**所要時間**: 90分

**ファイル**: `services/unified-portal/backend/tests/test_mailserver_router.py`（NEW）

**内容**: 全APIエンドポイントのテスト（正常系、異常系）

**依存**: W-008

---

#### W-037: サービス層ユニットテスト作成
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/backend/tests/test_mail_user_service.py`（NEW）

**依存**: W-005

---

#### W-038: フロントエンドコンポーネントテスト作成
**実行場所**: 🌐 Web側
**所要時間**: 60分

**ファイル**: `services/unified-portal/frontend/src/components/mailserver/__tests__/`（NEW）

**依存**: W-015, W-016, W-017, W-018, W-019

---

#### W-039: .env.example更新
**実行場所**: 🌐 Web側
**所要時間**: 5分

**ファイル**: `services/unified-portal/backend/.env.example`（既存更新）

**追加内容**:
```
# Mailserver Database
MAIL_DB_HOST=172.20.0.60
MAIL_DB_PORT=3306
MAIL_DB_NAME=mailserver_usermgmt
MAIL_DB_USER=usermgmt
MAIL_DB_PASSWORD=your_password_here
```

**依存**: W-010

---

#### W-040: README.md更新
**実行場所**: 🌐 Web側
**所要時間**: 15分

**ファイル**: `services/unified-portal/README.md`（既存更新）

**追加内容**: Mailserver統合機能の説明、環境変数設定方法

**依存**: なし

---

## 🖥️ ローカル側タスク（Dell WorkStationで実行必要）

### Phase 1-L: Mailserver統合 - 環境構築

#### L-001: .env設定ファイル作成
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**ファイル**: `services/unified-portal/backend/.env`（NEW）

**内容**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
cp .env.example .env

# .env編集
MAIL_DB_HOST=172.20.0.60
MAIL_DB_PORT=3306
MAIL_DB_NAME=mailserver_usermgmt
MAIL_DB_USER=usermgmt
MAIL_DB_PASSWORD=<実際のパスワード>  # services/mailserver/.envから取得
```

**依存**: W-039
**検証**: ファイル存在確認、パスワード設定確認

---

#### L-002: Python依存関係インストール
**実行場所**: 🖥️ ローカル
**所要時間**: 5分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate
pip install -r requirements.txt
```

**依存**: W-012
**検証**: `pip list | grep pymysql`

---

#### L-003: データベース接続確認
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate
python -c "
from app.database import mail_engine
from sqlalchemy import text
with mail_engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM users'))
    print(f'Users count: {result.scalar()}')
"
```

**依存**: L-001, L-002, W-009, W-010
**検証**: エラーなく実行完了、ユーザー数表示

---

#### L-004: バックエンド起動確認
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate
python -m app.main
```

**依存**: L-001, L-002, L-003
**検証**:
- サーバー起動成功（http://localhost:8000）
- `/docs` でSwagger UI表示
- `/health` で正常レスポンス

---

#### L-005: npm依存関係インストール
**実行場所**: 🖥️ ローカル
**所要時間**: 3分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend
npm install
```

**依存**: なし
**検証**: `node_modules/` 存在確認

---

#### L-006: フロントエンド起動確認
**実行場所**: 🖥️ ローカル
**所要時間**: 5分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend
npm run dev
```

**依存**: L-005
**検証**:
- 開発サーバー起動（http://localhost:5173）
- ブラウザで画面表示
- コンソールエラーなし

---

### Phase 2-L: DNS管理強化 - 動作確認

#### L-007: dig/nslookupコマンド確認
**実行場所**: 🖥️ ローカル
**所要時間**: 5分

**コマンド**:
```bash
which dig
which nslookup
dig +short google.com A
```

**依存**: なし
**検証**: `dig` コマンドが実行可能

---

#### L-008: DNS検証ツール動作確認
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**手順**:
1. バックエンド起動
2. `/docs` でDNS検証エンドポイントテスト
3. フロントエンドから検証ツール実行

**依存**: L-004, L-006, W-033, W-034
**検証**: dig結果が正しく表示される

---

### Phase 3-L: テスト実行

#### L-009: バックエンドユニットテスト実行
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate
pytest tests/ -v --cov=app --cov-report=html
```

**依存**: L-002, W-036, W-037
**検証**: 全テストパス、カバレッジ > 80%

---

#### L-010: フロントエンドテスト実行
**実行場所**: 🖥️ ローカル
**所要時間**: 5分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend
npm run test
```

**依存**: L-005, W-038
**検証**: 全テストパス

---

#### L-011: E2Eテスト実行（手動）
**実行場所**: 🖥️ ローカル
**所要時間**: 30分

**手順**:
1. メールユーザー作成
2. メールユーザー編集
3. パスワード変更
4. 有効/無効切替
5. メールユーザー削除
6. 監査ログ確認

**依存**: L-004, L-006
**検証**: 全操作が正常動作、Flask usermgmtと同じデータ表示

---

#### L-012: パフォーマンステスト
**実行場所**: 🖥️ ローカル
**所要時間**: 15分

**コマンド**:
```bash
# Apache Benchを使用
ab -n 100 -c 10 http://localhost:8000/api/v1/mailserver/users
```

**依存**: L-004
**検証**: 平均レスポンスタイム < 500ms

---

#### L-013: 並行稼働テスト
**実行場所**: 🖥️ ローカル
**所要時間**: 20分

**手順**:
1. Flask usermgmtでユーザー作成
2. Unified Portalで同じユーザーが表示されることを確認
3. Unified Portalでユーザー編集
4. Flask usermgmtで編集結果を確認

**依存**: L-011
**検証**: 両システムでデータが同期

---

### Phase 4-L: デプロイ・本番移行

#### L-014: Docker Compose設定作成
**実行場所**: 🖥️ ローカル
**所要時間**: 30分

**ファイル**: `services/unified-portal/docker-compose.yml`（既存更新）

**内容**: 本番用設定（ポート、ネットワーク、環境変数）

**依存**: なし

---

#### L-015: Nginx設定作成
**実行場所**: 🖥️ ローカル
**所要時間**: 20分

**ファイル**: `services/unified-portal/config/nginx/conf.d/admin-kuma8088.conf`（既存更新）

**依存**: なし

---

#### L-016: Cloudflare Tunnel設定更新
**実行場所**: 🖥️ ローカル
**所要時間**: 15分

**手順**: `admin.kuma8088.com` → Unified Portal へのトンネル設定

**依存**: L-015

---

#### L-017: Docker Compose起動
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
docker compose up -d
docker compose ps
docker compose logs -f
```

**依存**: L-014, L-015, L-016
**検証**: 全コンテナが `Up` 状態

---

#### L-018: 本番環境動作確認
**実行場所**: 🖥️ ローカル
**所要時間**: 30分

**手順**:
1. https://admin.kuma8088.com へアクセス
2. ログイン
3. 全機能テスト（E2E相当）

**依存**: L-017
**検証**: 全機能が正常動作

---

#### L-019: Flask usermgmt並行稼働確認
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**手順**:
1. Flask usermgmt起動確認
2. 両方同時アクセス可能か確認

**依存**: L-018
**検証**: 両システムが同時稼働

---

#### L-020: バックアップ作成
**実行場所**: 🖥️ ローカル
**所要時間**: 10分

**コマンド**:
```bash
# データベースバックアップ
docker exec mailserver-mariadb-1 mysqldump \
  -u usermgmt -p mailserver_usermgmt > \
  /mnt/backup-hdd/mailserver_usermgmt_pre-migration_$(date +%Y%m%d).sql
```

**依存**: なし
**検証**: バックアップファイル作成確認

---

#### L-021: ロールバックテスト
**実行場所**: 🖥️ ローカル
**所要時間**: 20分

**手順**:
1. Unified Portal停止
2. Flask usermgmtのみで動作確認
3. Unified Portal再起動

**依存**: L-020
**検証**: スムーズに切り戻し可能

---

#### L-022: 監視・アラート設定
**実行場所**: 🖥️ ローカル
**所要時間**: 30分

**手順**: ログ確認、エラーアラート設定（将来実装）

**依存**: L-018

---

#### L-023: ドキュメント最終確認
**実行場所**: 🖥️ ローカル
**所要時間**: 15分

**手順**: 全ドキュメントの実際の環境との整合性確認

**依存**: L-022

---

## 📊 タスク実行順序（推奨）

### 🌐 Web側（Day 1-2）
1. Phase 1-W バックエンド（W-001 ~ W-012）- 6時間
2. Phase 1-W フロントエンド（W-013 ~ W-025）- 8時間
3. Phase 2-W DNS強化（W-026 ~ W-035）- 4時間
4. Phase 3-W テスト（W-036 ~ W-040）- 4時間

**合計: 22時間（3日間で完了可能）**

### 🖥️ ローカル側（Day 3-4）
1. Phase 1-L 環境構築（L-001 ~ L-006）- 43分
2. Phase 2-L DNS確認（L-007 ~ L-008）- 15分
3. Phase 3-L テスト（L-009 ~ L-013）- 80分
4. Phase 4-L デプロイ（L-014 ~ L-023）- 200分

**合計: 6時間（1日で完了可能）**

---

## ✅ チェックリスト

### Web側完了条件
- [ ] 全40タスク完了
- [ ] Python/TypeScriptシンタックスエラーなし
- [ ] Git commit & push完了

### ローカル側完了条件
- [ ] 全23タスク完了
- [ ] データベース接続成功
- [ ] 全テストパス
- [ ] 並行稼働確認
- [ ] 本番環境デプロイ成功

---

**次のステップ**:
- Web側実装: [04_WEB_IMPLEMENTATION.md](04_WEB_IMPLEMENTATION.md)
- ローカル側実装: [05_LOCAL_IMPLEMENTATION.md](05_LOCAL_IMPLEMENTATION.md)
