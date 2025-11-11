# Phase 11: Extended機能 - 開発手順書

**作成日**: 2025-11-05
**ステータス**: 準備中
**見積もり**: Phase 11-A (2h) + Phase 11-B (3.5h) = 合計 5.5時間

---

## 📋 Phase 11 概要

### Phase 11-A: 管理者・ユーザー権限分離機能
- **目的**: adminユーザー1名のみが管理画面にアクセス可能にする
- **見積もり**: 2時間
- **前提条件**: Phase 10 完了

### Phase 11-B: ドメイン管理機能
- **目的**: ドメインの追加・編集・削除機能を実装
- **見積もり**: 3.5時間
- **前提条件**: Phase 11-A 完了

---

## 🚀 Phase 11-A: 管理者・ユーザー権限分離

### Phase 11-A-1: データベースマイグレーション (0.5時間)

#### ステップ1: マイグレーションSQLファイル作成

**ファイル**: `migrations/011_add_is_admin_column.sql`

```sql
-- =========================================
-- Phase 11-A: Add is_admin column to users
-- =========================================

-- Step 1: Add is_admin column
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- Step 2: Set admin@kuma8088.com as admin
UPDATE users SET is_admin = TRUE WHERE email = 'admin@kuma8088.com';

-- Step 3: Add constraint to ensure only one admin
-- MySQL 8.0.13+ supports filtered unique indexes
-- CREATE UNIQUE INDEX idx_users_single_admin ON users (is_admin) WHERE is_admin = TRUE;

-- MySQL 8.0.12 and earlier: Use trigger
DELIMITER $$
CREATE TRIGGER trg_single_admin_check
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
    IF NEW.is_admin = TRUE AND OLD.is_admin = FALSE THEN
        IF (SELECT COUNT(*) FROM users WHERE is_admin = TRUE) > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '管理者は1ユーザーのみ設定可能です';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_single_admin_check_insert
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF NEW.is_admin = TRUE THEN
        IF (SELECT COUNT(*) FROM users WHERE is_admin = TRUE) > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '管理者は1ユーザーのみ設定可能です';
        END IF;
    END IF;
END$$
DELIMITER ;

-- Step 4: Create index for performance
CREATE INDEX idx_users_is_admin ON users (is_admin);
```

**ロールバックSQL**: `migrations/011_rollback.sql`

```sql
-- =========================================
-- Phase 11-A: Rollback is_admin column
-- =========================================

-- Drop triggers
DROP TRIGGER IF EXISTS trg_single_admin_check;
DROP TRIGGER IF EXISTS trg_single_admin_check_insert;

-- Drop index
DROP INDEX IF EXISTS idx_users_is_admin ON users;
-- DROP INDEX IF EXISTS idx_users_single_admin ON users; -- If MySQL 8.0.13+

-- Drop column
ALTER TABLE users DROP COLUMN is_admin;
```

#### ステップ2: バックアップ取得

```bash
# データベースバックアップ
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
./scripts/backup-mailserver.sh

# バックアップ確認
ls -lh backups/
```

#### ステップ3: マイグレーション実行

```bash
# MariaDB接続
docker exec -it mailserver-mariadb mysql \
  -u usermgmt \
  -p'SecureMailUserMgmt2024!' \
  mailserver_usermgmt

# マイグレーション実行
source /path/to/migrations/011_add_is_admin_column.sql

# 確認
SHOW COLUMNS FROM users LIKE 'is_admin';
SELECT email, is_admin FROM users;
SHOW TRIGGERS LIKE 'trg_single_admin_%';
```

#### ステップ4: 検証

```bash
# Pythonで検証
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    # 管理者確認
    admin = User.query.filter_by(email='admin@kuma8088.com').first()
    print(f'Admin user: {admin.email}, is_admin={admin.is_admin}')

    # 通常ユーザー確認
    users = User.query.filter_by(is_admin=False).all()
    print(f'Regular users: {len(users)} users')
    for u in users[:3]:
        print(f'  - {u.email}, is_admin={u.is_admin}')
"
```

**期待される出力**:
```
Admin user: admin@kuma8088.com, is_admin=True
Regular users: 5 users
  - user1@kuma8088.com, is_admin=False
  - user2@kuma8088.com, is_admin=False
  - user3@kuma8088.com, is_admin=False
```

---

### Phase 11-A-2: バックエンド実装 (1時間)

#### ステップ1: モデル更新

**ファイル**: `app/models/user.py`

```python
# 既存のUserクラスに以下を追加

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # ... existing columns ...

    # Phase 11-A: Admin flag
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # ... existing methods ...
```

**テスト**:
```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(email='admin@kuma8088.com').first()
    print(f'Model test: {user.email}, is_admin={user.is_admin}')
    assert user.is_admin == True
    print('✅ Model update successful')
"
```

#### ステップ2: 認可デコレーター実装

**ファイル**: `app/decorators.py` (新規作成)

```python
"""
Authorization decorators for route protection
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """
    Require admin privileges for route access

    Usage:
        @bp.route('/admin-only')
        @login_required
        @admin_required
        def admin_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('auth.login'))

        if not current_user.is_admin:
            flash('管理者権限が必要です。', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function
```

**テスト**:
```bash
# Pythonで簡易テスト
docker exec mailserver-usermgmt python -c "
from app.decorators import admin_required
print('✅ Decorator module created successfully')
"
```

#### ステップ3: ルート保護

**ファイル**: `app/routes/users.py`

すべてのユーザー管理ルートに `@admin_required` を追加:

```python
from app.decorators import admin_required

# 既存の各ルートに @admin_required を追加

@bp.route('/')
@login_required
@admin_required  # 追加
def list():
    """List all users"""
    # ... existing code ...

@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required  # 追加
def create():
    """Create new user"""
    # ... existing code ...

@bp.route('/<email>/edit', methods=['GET', 'POST'])
@login_required
@admin_required  # 追加
def edit(email):
    """Edit user"""
    # ... existing code ...

@bp.route('/<email>/delete', methods=['POST'])
@login_required
@admin_required  # 追加
def delete(email):
    """Delete user"""
    # ... existing code ...

@bp.route('/<email>/password', methods=['GET', 'POST'])
@login_required
@admin_required  # 追加
def change_password(email):
    """Change user password"""
    # ... existing code ...

@bp.route('/<email>/toggle', methods=['POST'])
@login_required
@admin_required  # 追加
def toggle_status(email):
    """Toggle user status"""
    # ... existing code ...
```

#### ステップ4: ダッシュボード保護

**ファイル**: `app/__init__.py`

```python
# register_blueprints関数内のdashboardルートに @admin_required を追加

from app.decorators import admin_required

def register_blueprints(app):
    # ... existing blueprint registrations ...

    # Dashboard route (protected)
    @app.route('/')
    @login_required
    @admin_required  # 追加
    def dashboard():
        """Dashboard route (admin only)"""
        return render_template('dashboard.html')
```

#### ステップ5: ログイン処理変更

**ファイル**: `app/routes/auth.py`

```python
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('メールアドレスまたはパスワードが正しくありません。', 'error')
            return render_template('login.html'), 200

        # Verify password
        if not verify_password(password, user.password_hash):
            flash('メールアドレスまたはパスワードが正しくありません。', 'error')
            return render_template('login.html'), 200

        # Check if user is enabled
        if not user.enabled:
            flash('アカウントが無効です。管理者にお問い合わせください。', 'error')
            return render_template('login.html'), 200

        # Phase 11-A: Check if user is admin
        if not user.is_admin:
            flash('管理者のみログイン可能です。', 'error')
            return render_template('login.html'), 200

        # Login successful
        login_user(user, remember=True)
        return redirect(url_for('dashboard'))

    return render_template('login.html')
```

#### ステップ6: コンテナ再起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose restart usermgmt

# 起動確認
docker logs mailserver-usermgmt --tail 20
```

---

### Phase 11-A-3: テスト・検証 (0.5時間)

#### テスト1: 管理者ログイン

```bash
# ブラウザまたはcurlでテスト
curl -c cookies.txt -X POST http://172.20.0.90:5000/auth/login \
  -d "email=admin@kuma8088.com" \
  -d "password=AdminPass2025!"

# ダッシュボードアクセス
curl -b cookies.txt http://172.20.0.90:5000/
# 期待: ダッシュボードHTML表示
```

#### テスト2: 通常ユーザーログイン拒否

```bash
# 通常ユーザーでログイン試行
curl -c cookies2.txt -X POST http://172.20.0.90:5000/auth/login \
  -d "email=user1@kuma8088.com" \
  -d "password=UserPass123!"

# 期待: "管理者のみログイン可能です" エラーメッセージ
```

#### テスト3: 権限保護テスト

```bash
# 非ログイン状態でダッシュボードアクセス
curl http://172.20.0.90:5000/
# 期待: ログイン画面へリダイレクト

# 非ログイン状態でユーザー一覧アクセス
curl http://172.20.0.90:5000/users
# 期待: ログイン画面へリダイレクト
```

#### テスト4: IMAPアクセステスト（通常ユーザー）

```bash
# 通常ユーザーのIMAPログイン（管理画面はNG、IMAPはOK）
openssl s_client -connect localhost:993 -quiet -crlf <<EOF
a1 LOGIN user1@kuma8088.com UserPass123!
a2 LOGOUT
EOF

# 期待: a1 OK Logged in (IMAPは正常動作)
```

#### テスト5: 制約テスト

```bash
# 2人目の管理者作成試行
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.models import User
from app.database import db

app = create_app()
with app.app_context():
    user = User.query.filter_by(email='user1@kuma8088.com').first()
    user.is_admin = True
    try:
        db.session.commit()
        print('❌ 制約が機能していません！')
    except Exception as e:
        db.session.rollback()
        print(f'✅ 制約が正常に機能: {str(e)}')
"

# 期待: "管理者は1ユーザーのみ設定可能です" エラー
```

---

## 🌐 Phase 11-B: ドメイン管理機能

### Phase 11-B-1: データベースマイグレーション (0.5時間)

#### ステップ1: マイグレーションSQLファイル作成

**ファイル**: `migrations/012_add_domain_enabled_column.sql`

```sql
-- =========================================
-- Phase 11-B: Add enabled column to domains
-- =========================================

-- Step 1: Add enabled column
ALTER TABLE domains ADD COLUMN enabled BOOLEAN DEFAULT TRUE NOT NULL;

-- Step 2: Create index for filtering
CREATE INDEX idx_domains_enabled ON domains (enabled);

-- Step 3: Ensure foreign key constraint exists
ALTER TABLE users
  DROP FOREIGN KEY IF EXISTS fk_users_domain,
  ADD CONSTRAINT fk_users_domain
    FOREIGN KEY (domain_id) REFERENCES domains(id)
    ON DELETE RESTRICT;
```

**ロールバックSQL**: `migrations/012_rollback.sql`

```sql
-- =========================================
-- Phase 11-B: Rollback domain enabled column
-- =========================================

DROP INDEX IF EXISTS idx_domains_enabled ON domains;
ALTER TABLE domains DROP COLUMN enabled;
```

#### ステップ2: マイグレーション実行

```bash
# MariaDB接続
docker exec -it mailserver-mariadb mysql \
  -u usermgmt \
  -p'SecureMailUserMgmt2024!' \
  mailserver_usermgmt

# マイグレーション実行
source /path/to/migrations/012_add_domain_enabled_column.sql

# 確認
SHOW COLUMNS FROM domains LIKE 'enabled';
SELECT id, name, enabled FROM domains;
```

#### ステップ3: 検証

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.models import Domain

app = create_app()
with app.app_context():
    domains = Domain.query.all()
    print(f'Domains: {len(domains)} found')
    for d in domains:
        print(f'  - {d.name}, enabled={d.enabled}')
"

# 期待: kuma8088.com, enabled=True
```

---

### Phase 11-B-2: バックエンド実装 (1.5時間)

#### ステップ1: モデル更新

**ファイル**: `app/models/domain.py`

```python
"""
Domain model for mailserver usermgmt application
"""
from app.database import db
from datetime import datetime


class Domain(db.Model):
    """
    Domain model representing email domains

    Each domain can have multiple users
    """
    __tablename__ = 'domains'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Domain name (matches 'name' column in database)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Domain metadata
    description = db.Column(db.String(500), nullable=True)
    default_quota = db.Column(db.Integer, default=1024, nullable=False)

    # Phase 11-B: Enable/disable domain
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    users = db.relationship('User', backref='domain', lazy='dynamic')

    def user_count(self):
        """Return the number of users in this domain"""
        return self.users.count()

    def __repr__(self):
        """String representation of Domain"""
        return f'<Domain {self.name}>'
```

#### ステップ2: DomainService実装

**ファイル**: `app/services/domain_service.py` (新規作成)

```python
"""
Domain Service - Business logic for domain management operations

Handles CRUD operations for domains with audit logging
"""
import json
from app.database import db
from app.models import Domain, AuditLog
from sqlalchemy.exc import IntegrityError
from typing import List, Optional


class DomainService:
    """
    Domain management service with audit logging

    Provides methods for:
    - Listing domains
    - Creating domains
    - Updating domains
    - Deleting domains
    """

    @staticmethod
    def list_domains(enabled_only: bool = False) -> List[Domain]:
        """
        List all domains, optionally filtered by enabled status

        Args:
            enabled_only: If True, return only enabled domains

        Returns:
            List of Domain objects

        Examples:
            >>> DomainService.list_domains()  # All domains
            >>> DomainService.list_domains(enabled_only=True)  # Enabled only
        """
        query = Domain.query

        if enabled_only:
            query = query.filter_by(enabled=True)

        return query.order_by(Domain.name).all()

    @staticmethod
    def get_domain_by_id(domain_id: int) -> Optional[Domain]:
        """
        Get domain by ID

        Args:
            domain_id: Domain ID

        Returns:
            Domain object if found, None otherwise
        """
        return Domain.query.get(domain_id)

    @staticmethod
    def create_domain(
        name: str,
        description: str = '',
        default_quota: int = 1024,
        enabled: bool = True,
        admin_ip: str = 'system'
    ) -> Domain:
        """
        Create a new domain

        Args:
            name: Domain name
            description: Domain description
            default_quota: Default quota in MB (default: 1024)
            enabled: Whether domain is enabled (default: True)
            admin_ip: Who performed this action (for audit log)

        Returns:
            Created Domain object

        Raises:
            ValueError: If domain name already exists

        Examples:
            >>> DomainService.create_domain(
            ...     name='example.com',
            ...     description='Test domain',
            ...     default_quota=2048
            ... )
        """
        # Check if domain already exists
        existing_domain = Domain.query.filter_by(name=name).first()
        if existing_domain:
            raise ValueError("このドメイン名は既に登録されています")

        # Create domain
        domain = Domain(
            name=name,
            description=description,
            default_quota=default_quota,
            enabled=enabled
        )

        try:
            db.session.add(domain)
            db.session.commit()

            # Log audit
            DomainService.log_audit(
                action='create',
                domain_name=name,
                admin_ip=admin_ip,
                details=json.dumps({
                    "message": "Domain created",
                    "default_quota_mb": default_quota,
                    "enabled": enabled
                })
            )

            return domain

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"データベースエラー: {str(e)}")

    @staticmethod
    def update_domain(
        domain_id: int,
        admin_ip: str = 'system',
        **kwargs
    ) -> Domain:
        """
        Update domain attributes

        Args:
            domain_id: Domain ID
            admin_ip: Who performed this action (for audit log)
            **kwargs: Attributes to update (description, default_quota, enabled)

        Returns:
            Updated Domain object

        Raises:
            ValueError: If domain not found or domain name change attempted

        Examples:
            >>> DomainService.update_domain(
            ...     domain_id=1,
            ...     description='Updated description',
            ...     default_quota=2048
            ... )
        """
        # Prevent domain name changes
        if 'name' in kwargs:
            raise ValueError("ドメイン名は変更できません")

        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # Track changes for audit log
        changes = []

        # Update allowed attributes
        allowed_attrs = ['description', 'default_quota', 'enabled']
        for attr, value in kwargs.items():
            if attr in allowed_attrs and hasattr(domain, attr):
                old_value = getattr(domain, attr)
                if old_value != value:
                    setattr(domain, attr, value)
                    changes.append(f"{attr}: {old_value} → {value}")

        if changes:
            try:
                db.session.commit()

                # Log audit
                DomainService.log_audit(
                    action='update',
                    domain_name=domain.name,
                    admin_ip=admin_ip,
                    details=json.dumps({
                        "message": "Domain updated",
                        "changes": changes
                    })
                )

            except IntegrityError as e:
                db.session.rollback()
                raise ValueError(f"データベースエラー: {str(e)}")

        return domain

    @staticmethod
    def delete_domain(domain_id: int, admin_ip: str = 'system') -> None:
        """
        Delete domain

        Args:
            domain_id: Domain ID
            admin_ip: Who performed this action (for audit log)

        Raises:
            ValueError: If domain not found or has users

        Examples:
            >>> DomainService.delete_domain(2)
        """
        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # Check if domain has users
        user_count = domain.user_count()
        if user_count > 0:
            raise ValueError(
                f"このドメインには {user_count} 人のユーザーが存在します。"
                "先にユーザーを削除してください。"
            )

        domain_name = domain.name

        try:
            db.session.delete(domain)
            db.session.commit()

            # Log audit
            DomainService.log_audit(
                action='delete',
                domain_name=domain_name,
                admin_ip=admin_ip,
                details=json.dumps({"message": "Domain deleted"})
            )

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"データベースエラー: {str(e)}")

    @staticmethod
    def log_audit(
        action: str,
        domain_name: str,
        admin_ip: str,
        details: str = ''
    ) -> AuditLog:
        """
        Create audit log entry for domain operations

        Args:
            action: Action type (create, update, delete)
            domain_name: Domain name
            admin_ip: Who performed the action
            details: Additional details (JSON format)

        Returns:
            Created AuditLog object
        """
        audit_log = AuditLog(
            action=action,
            user_email=f'domain:{domain_name}',  # Prefix to identify domain operations
            admin_ip=admin_ip,
            details=details
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log
```

**`app/services/__init__.py` に追加**:
```python
from app.services.user_service import UserService
from app.services.domain_service import DomainService  # 追加

__all__ = ['UserService', 'DomainService']  # 追加
```

#### ステップ3: ルート実装

**ファイル**: `app/routes/domains.py` (新規作成)

```python
"""
Domain management routes

Provides CRUD endpoints for domain management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.decorators import admin_required
from app.services import DomainService


# Create blueprint
bp = Blueprint('domains', __name__, url_prefix='/domains')


@bp.route('/')
@login_required
@admin_required
def list():
    """
    List all domains

    GET /domains
    """
    try:
        domains = DomainService.list_domains()

        return render_template(
            'domains/list.html',
            domains=domains
        )
    except Exception as e:
        flash(f'ドメイン一覧の取得に失敗しました: {str(e)}', 'danger')
        return render_template('domains/list.html', domains=[])


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """
    Create new domain

    GET /domains/new - Show create form
    POST /domains/new - Create domain
    """
    if request.method == 'GET':
        return render_template('domains/create.html')

    # POST request
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', 1024, type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Validation
        if not name:
            flash('ドメイン名は必須です。', 'warning')
            return redirect(url_for('domains.create'))

        # Create domain
        domain = DomainService.create_domain(
            name=name,
            description=description,
            default_quota=default_quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ドメイン {domain.name} を作成しました。', 'success')
        return redirect(url_for('domains.list'))

    except ValueError as e:
        flash(f'ドメイン作成に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('domains.create'))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('domains.create'))


@bp.route('/<int:domain_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(domain_id):
    """
    Edit domain

    GET /domains/<domain_id>/edit - Show edit form
    POST /domains/<domain_id>/edit - Update domain
    """
    domain = DomainService.get_domain_by_id(domain_id)
    if not domain:
        flash('ドメインが見つかりません。', 'danger')
        return redirect(url_for('domains.list'))

    if request.method == 'GET':
        return render_template('domains/edit.html', domain=domain)

    # POST request
    try:
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Update domain
        domain = DomainService.update_domain(
            domain_id=domain_id,
            description=description,
            default_quota=default_quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ドメイン {domain.name} を更新しました。', 'success')
        return redirect(url_for('domains.list'))

    except ValueError as e:
        flash(f'ドメイン更新に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('domains.edit', domain_id=domain_id))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('domains.edit', domain_id=domain_id))


@bp.route('/<int:domain_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(domain_id):
    """
    Delete domain

    POST /domains/<domain_id>/delete
    """
    try:
        domain = DomainService.get_domain_by_id(domain_id)
        if not domain:
            flash('ドメインが見つかりません。', 'danger')
            return redirect(url_for('domains.list'))

        domain_name = domain.name
        DomainService.delete_domain(
            domain_id=domain_id,
            admin_ip=request.remote_addr
        )

        flash(f'ドメイン {domain_name} を削除しました。', 'success')
    except ValueError as e:
        flash(f'ドメイン削除に失敗しました: {str(e)}', 'danger')
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')

    return redirect(url_for('domains.list'))
```

**`app/__init__.py` に登録**:
```python
def register_blueprints(app):
    # Import and register auth blueprint
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Import and register users blueprint
    from app.routes.users import bp as users_bp
    app.register_blueprint(users_bp)

    # Phase 11-B: Import and register domains blueprint
    from app.routes.domains import bp as domains_bp
    app.register_blueprint(domains_bp)

    # ... existing routes ...
```

#### ステップ4: ユーザー作成画面のドメイン選択修正

**ファイル**: `app/routes/users.py`

```python
from app.services import UserService, DomainService  # DomainServiceを追加

@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Create new user"""
    if request.method == 'GET':
        # Phase 11-B: Use DomainService to get enabled domains only
        domains = DomainService.list_domains(enabled_only=True)
        return render_template('users/create.html', domains=domains)

    # ... existing POST logic ...
```

---

### Phase 11-B-3: フロントエンド実装 (1時間)

#### テンプレート作成

**ディレクトリ作成**:
```bash
mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt/templates/domains
```

**ファイル1**: `templates/domains/list.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ドメイン一覧 - メールユーザー管理</title>

    <!-- Bootstrap 5.3.x CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">

    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .content-card {
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 15px;
            border: none;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">メールユーザー管理</a>
            <div class="navbar-nav me-auto">
                <a class="nav-link" href="{{ url_for('users.list') }}">ユーザー</a>
                <a class="nav-link active" href="{{ url_for('domains.list') }}">ドメイン</a>
            </div>
            <div class="d-flex">
                <form method="POST" action="{{ url_for('auth.logout') }}">
                    <button type="submit" class="btn btn-outline-light">ログアウト</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card content-card">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2><i class="bi bi-globe"></i> ドメイン一覧</h2>
                    <a href="{{ url_for('domains.create') }}" class="btn btn-primary">
                        <i class="bi bi-plus-circle"></i> 新規ドメイン追加
                    </a>
                </div>

                {% if domains %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ドメイン名</th>
                                <th>説明</th>
                                <th>デフォルト容量</th>
                                <th>ユーザー数</th>
                                <th>状態</th>
                                <th>作成日</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for domain in domains %}
                            <tr>
                                <td><strong>{{ domain.name }}</strong></td>
                                <td>{{ domain.description or '-' }}</td>
                                <td>{{ domain.default_quota }} MB</td>
                                <td>{{ domain.user_count() }}</td>
                                <td>
                                    {% if domain.enabled %}
                                        <span class="badge bg-success">有効</span>
                                    {% else %}
                                        <span class="badge bg-secondary">無効</span>
                                    {% endif %}
                                </td>
                                <td>{{ domain.created_at.strftime('%Y-%m-%d') }}</td>
                                <td>
                                    <a href="{{ url_for('domains.edit', domain_id=domain.id) }}"
                                       class="btn btn-sm btn-outline-primary">
                                        <i class="bi bi-pencil"></i> 編集
                                    </a>
                                    {% if domain.user_count() == 0 %}
                                    <form method="POST"
                                          action="{{ url_for('domains.delete', domain_id=domain.id) }}"
                                          style="display: inline;"
                                          onsubmit="return confirm('本当にドメイン {{ domain.name }} を削除しますか？');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger">
                                            <i class="bi bi-trash"></i> 削除
                                        </button>
                                    </form>
                                    {% else %}
                                    <button type="button" class="btn btn-sm btn-outline-secondary" disabled>
                                        <i class="bi bi-trash"></i> 削除不可
                                    </button>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> ドメインが登録されていません。
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

**ファイル2**: `templates/domains/create.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ドメイン作成 - メールユーザー管理</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">

    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .content-card {
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 15px;
            border: none;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">メールユーザー管理</a>
            <div class="d-flex">
                <form method="POST" action="{{ url_for('auth.logout') }}">
                    <button type="submit" class="btn btn-outline-light">ログアウト</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card content-card">
            <div class="card-body p-4">
                <h2 class="mb-4"><i class="bi bi-globe-plus"></i> 新規ドメイン作成</h2>

                <form method="POST" action="{{ url_for('domains.create') }}">
                    <!-- Domain Name -->
                    <div class="mb-3">
                        <label for="name" class="form-label">
                            <i class="bi bi-globe"></i> ドメイン名 <span class="text-danger">*</span>
                        </label>
                        <input type="text"
                               class="form-control"
                               id="name"
                               name="name"
                               placeholder="example.com"
                               required
                               pattern="^[a-z0-9.-]+\.[a-z]{2,}$">
                        <div class="form-text">
                            ドメイン名を入力してください（例: example.com）
                        </div>
                    </div>

                    <!-- Description -->
                    <div class="mb-3">
                        <label for="description" class="form-label">
                            <i class="bi bi-card-text"></i> 説明
                        </label>
                        <input type="text"
                               class="form-control"
                               id="description"
                               name="description"
                               placeholder="ドメインの説明（任意）"
                               maxlength="500">
                        <div class="form-text">
                            このドメインの用途や説明を入力できます（任意）
                        </div>
                    </div>

                    <!-- Default Quota -->
                    <div class="mb-3">
                        <label for="default_quota" class="form-label">
                            <i class="bi bi-hdd"></i> デフォルト容量 (MB)
                        </label>
                        <input type="number"
                               class="form-control"
                               id="default_quota"
                               name="default_quota"
                               value="1024"
                               min="1"
                               max="10240"
                               step="1">
                        <div class="form-text">
                            このドメインの新規ユーザーに割り当てるデフォルト容量
                        </div>
                    </div>

                    <!-- Enabled -->
                    <div class="mb-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input"
                                   type="checkbox"
                                   id="enabled"
                                   name="enabled"
                                   value="true"
                                   checked>
                            <label class="form-check-label" for="enabled">
                                <i class="bi bi-check-circle"></i> ドメインを有効化
                            </label>
                        </div>
                        <div class="form-text">
                            無効にすると、新規ユーザー作成時にこのドメインが選択できなくなります
                        </div>
                    </div>

                    <!-- Buttons -->
                    <div class="d-flex justify-content-between mt-4">
                        <a href="{{ url_for('domains.list') }}" class="btn btn-secondary">
                            <i class="bi bi-x-circle"></i> キャンセル
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-circle"></i> 作成
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

**ファイル3**: `templates/domains/edit.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ドメイン編集 - メールユーザー管理</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">

    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .content-card {
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 15px;
            border: none;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">メールユーザー管理</a>
            <div class="d-flex">
                <form method="POST" action="{{ url_for('auth.logout') }}">
                    <button type="submit" class="btn btn-outline-light">ログアウト</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card content-card">
            <div class="card-body p-4">
                <h2 class="mb-4"><i class="bi bi-pencil"></i> ドメイン編集</h2>

                <form method="POST" action="{{ url_for('domains.edit', domain_id=domain.id) }}">
                    <!-- Domain Name (readonly) -->
                    <div class="mb-3">
                        <label for="name" class="form-label">
                            <i class="bi bi-globe"></i> ドメイン名
                        </label>
                        <input type="text"
                               class="form-control"
                               id="name"
                               value="{{ domain.name }}"
                               readonly
                               disabled>
                        <div class="form-text">
                            ドメイン名は変更できません
                        </div>
                    </div>

                    <!-- Description -->
                    <div class="mb-3">
                        <label for="description" class="form-label">
                            <i class="bi bi-card-text"></i> 説明
                        </label>
                        <input type="text"
                               class="form-control"
                               id="description"
                               name="description"
                               value="{{ domain.description or '' }}"
                               maxlength="500">
                    </div>

                    <!-- Default Quota -->
                    <div class="mb-3">
                        <label for="default_quota" class="form-label">
                            <i class="bi bi-hdd"></i> デフォルト容量 (MB) <span class="text-danger">*</span>
                        </label>
                        <input type="number"
                               class="form-control"
                               id="default_quota"
                               name="default_quota"
                               value="{{ domain.default_quota }}"
                               min="1"
                               max="10240"
                               step="1"
                               required>
                    </div>

                    <!-- Enabled -->
                    <div class="mb-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input"
                                   type="checkbox"
                                   id="enabled"
                                   name="enabled"
                                   value="true"
                                   {% if domain.enabled %}checked{% endif %}>
                            <label class="form-check-label" for="enabled">
                                <i class="bi bi-check-circle"></i> ドメインを有効化
                            </label>
                        </div>
                    </div>

                    <!-- Domain Info -->
                    <div class="alert alert-info">
                        <h6><i class="bi bi-info-circle"></i> ドメイン情報</h6>
                        <ul class="mb-0">
                            <li><strong>ユーザー数:</strong> {{ domain.user_count() }}</li>
                            <li><strong>作成日:</strong> {{ domain.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</li>
                            <li><strong>最終更新:</strong> {{ domain.updated_at.strftime('%Y-%m-%d %H:%M:%S') }}</li>
                        </ul>
                    </div>

                    <!-- Buttons -->
                    <div class="d-flex justify-content-between mt-4">
                        <a href="{{ url_for('domains.list') }}" class="btn btn-secondary">
                            <i class="bi bi-x-circle"></i> キャンセル
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-circle"></i> 更新
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

#### ナビゲーション追加

**既存テンプレートにドメインリンクを追加**:

`templates/dashboard.html`, `templates/users/list.html`, `templates/users/create.html`, `templates/users/edit.html` など、ナビゲーションバーがあるテンプレートに以下を追加:

```html
<div class="navbar-nav me-auto">
    <a class="nav-link" href="{{ url_for('users.list') }}">ユーザー</a>
    <a class="nav-link" href="{{ url_for('domains.list') }}">ドメイン</a>
</div>
```

#### コンテナ再起動

```bash
docker compose restart usermgmt
docker logs mailserver-usermgmt --tail 20
```

---

### Phase 11-B-4: テスト・検証 (0.5時間)

#### テスト1: ドメイン作成

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.services import DomainService

app = create_app()
with app.app_context():
    domain = DomainService.create_domain(
        name='test.com',
        description='テストドメイン',
        default_quota=512,
        enabled=True,
        admin_ip='127.0.0.1'
    )
    print(f'✅ ドメイン作成成功: {domain.name}')
    print(f'   デフォルト容量: {domain.default_quota} MB')
    print(f'   有効: {domain.enabled}')
"
```

#### テスト2: ドメイン編集

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.services import DomainService

app = create_app()
with app.app_context():
    domains = DomainService.list_domains()
    test_domain = next((d for d in domains if d.name == 'test.com'), None)

    if test_domain:
        updated = DomainService.update_domain(
            domain_id=test_domain.id,
            description='更新されたテストドメイン',
            default_quota=1024,
            admin_ip='127.0.0.1'
        )
        print(f'✅ ドメイン更新成功: {updated.name}')
        print(f'   説明: {updated.description}')
        print(f'   デフォルト容量: {updated.default_quota} MB')
"
```

#### テスト3: ドメイン削除（ユーザー0）

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.services import DomainService

app = create_app()
with app.app_context():
    domains = DomainService.list_domains()
    test_domain = next((d for d in domains if d.name == 'test.com'), None)

    if test_domain and test_domain.user_count() == 0:
        DomainService.delete_domain(
            domain_id=test_domain.id,
            admin_ip='127.0.0.1'
        )
        print(f'✅ ドメイン削除成功: test.com')
    else:
        print('⚠️  ユーザーが存在するため削除できません')
"
```

#### テスト4: ドメイン削除制約（ユーザー存在）

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.services import DomainService

app = create_app()
with app.app_context():
    domains = DomainService.list_domains()
    kuma_domain = next((d for d in domains if d.name == 'kuma8088.com'), None)

    try:
        DomainService.delete_domain(
            domain_id=kuma_domain.id,
            admin_ip='127.0.0.1'
        )
        print('❌ 制約が機能していません！')
    except ValueError as e:
        print(f'✅ 制約が正常に機能: {str(e)}')
"
```

#### テスト5: 監査ログ確認

```bash
docker exec mailserver-usermgmt python -c "
from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    result = db.session.execute(db.text('''
        SELECT id, action, user_email, details, created_at
        FROM audit_logs
        WHERE user_email LIKE 'domain:%'
        ORDER BY created_at DESC
        LIMIT 10
    '''))

    print('ドメイン操作の監査ログ:')
    for row in result:
        print(f'[{row[0]}] {row[4]} - {row[1]} - {row[2]}')
        print(f'    details: {row[3]}')
        print()
"
```

---

## 📊 Phase 11 完了チェックリスト

### Phase 11-A 完了確認

- [ ] データベースマイグレーション実行完了
- [ ] `is_admin` カラム追加確認
- [ ] トリガー作成確認
- [ ] モデル更新完了
- [ ] デコレーター実装完了
- [ ] 全ルートに `@admin_required` 適用
- [ ] ログイン処理変更完了
- [ ] 管理者ログインテスト成功
- [ ] 通常ユーザーログイン拒否テスト成功
- [ ] 管理者1名制約テスト成功
- [ ] IMAPログインテスト成功（通常ユーザー）

### Phase 11-B 完了確認

- [ ] データベースマイグレーション実行完了
- [ ] `enabled` カラム追加確認
- [ ] モデル更新完了
- [ ] DomainService実装完了
- [ ] ドメインルート実装完了
- [ ] テンプレート作成完了
- [ ] ナビゲーション追加完了
- [ ] ドメイン作成テスト成功
- [ ] ドメイン編集テスト成功
- [ ] ドメイン削除テスト成功
- [ ] 削除制約テスト成功
- [ ] 監査ログ記録確認
- [ ] ユーザー作成画面で有効ドメインのみ表示確認

---

## 🔄 ロールバック手順

### Phase 11-A ロールバック

```bash
# データベースロールバック
docker exec -it mailserver-mariadb mysql \
  -u usermgmt \
  -p'SecureMailUserMgmt2024!' \
  mailserver_usermgmt \
  < /path/to/migrations/011_rollback.sql

# コード変更を元に戻す (Git使用)
git checkout HEAD -- app/models/user.py
git checkout HEAD -- app/decorators.py
git checkout HEAD -- app/routes/users.py
git checkout HEAD -- app/routes/auth.py
git checkout HEAD -- app/__init__.py

# コンテナ再起動
docker compose restart usermgmt
```

### Phase 11-B ロールバック

```bash
# データベースロールバック
docker exec -it mailserver-mariadb mysql \
  -u usermgmt \
  -p'SecureMailUserMgmt2024!' \
  mailserver_usermgmt \
  < /path/to/migrations/012_rollback.sql

# コード変更を元に戻す
git checkout HEAD -- app/models/domain.py
rm -f app/services/domain_service.py
rm -f app/routes/domains.py
rm -rf templates/domains/
git checkout HEAD -- app/routes/users.py
git checkout HEAD -- app/__init__.py

# コンテナ再起動
docker compose restart usermgmt
```

---

## 📝 次のステップ

Phase 11 完了後:
1. DEVELOPMENT.md を更新（Phase 11 完了マーク）
2. CHANGELOG.md に Phase 11 の変更内容を追記
3. USER_GUIDE.md を更新（ドメイン管理機能の追加）

---

**Phase 11 開発を開始する準備が整いました！**
