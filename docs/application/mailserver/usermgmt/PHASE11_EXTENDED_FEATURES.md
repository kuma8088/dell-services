# Phase 11: Extended機能追加設計書

**作成日**: 2025-11-05
**ステータス**: 設計中
**対象**: Extended追加機能（Phase 11）

---

## 📋 概要

Phase 10（本番リリース）完了後の拡張機能として、以下の2つの機能を追加します：

1. **管理者・ユーザー権限分離機能** (Phase 11-A)
2. **ドメイン管理機能** (Phase 11-B)

---

## 🎯 Phase 11-A: 管理者・ユーザー権限分離機能

### 要件

**現状の課題**:
- 全ての `users` テーブルのユーザーが管理画面にログイン可能
- 権限の区別がなく、誰でも全ユーザーを管理できる
- セキュリティリスク：メールユーザーが管理機能にアクセス可能

**目標**:
- **管理者 (admin)**: 1ユーザーのみ、全機能利用可能
- **通常ユーザー (user)**: 複数存在、管理者が自由に操作可能
- **権限識別**: `is_admin` フラグで管理者を識別
- **機能分離**: 管理者のみが管理画面にアクセス可能

### 権限モデル

| 機能 | 管理者 (admin) | 通常ユーザー (user) |
|------|----------------|---------------------|
| 管理画面ログイン | ✅ | ❌ |
| ダッシュボード閲覧 | ✅ | ❌ |
| ユーザー一覧 | ✅ | ❌ |
| ユーザー作成 | ✅ | ❌ |
| ユーザー編集 | ✅ | ❌ |
| ユーザー削除 | ✅ | ❌ |
| ユーザーパスワード変更 | ✅ | ❌ |
| 監査ログ閲覧 | ✅ | ❌ |
| ドメイン管理 | ✅ | ❌ |
| IMAP/SMTP メールアクセス | ✅ | ✅ |

### データベース設計

#### 1. `users` テーブル変更

**新規カラム追加**:
```sql
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;
```

**制約追加（管理者は1ユーザーのみ）**:
```sql
-- MySQL 8.0.13+ の場合
CREATE UNIQUE INDEX idx_users_single_admin ON users (is_admin) WHERE is_admin = TRUE;

-- MySQL 8.0.12 以前の場合はトリガーで制御
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
DELIMITER ;
```

**初期データ設定**:
```sql
UPDATE users SET is_admin = TRUE WHERE email = 'admin@kuma8088.com';
```

#### 2. マイグレーション後のテーブル構造

```
users
├── id (INT, PRIMARY KEY, AUTO_INCREMENT)
├── email (VARCHAR(255), UNIQUE, NOT NULL)
├── password_hash (VARCHAR(255), NOT NULL)
├── domain_id (INT, FOREIGN KEY -> domains.id)
├── maildir (VARCHAR(255), NOT NULL)
├── quota (INT, DEFAULT 1024)
├── uid (INT, DEFAULT 5000)
├── gid (INT, DEFAULT 5000)
├── enabled (BOOLEAN, DEFAULT TRUE)
├── is_admin (BOOLEAN, DEFAULT FALSE, NOT NULL)  ← 新規
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

INDEX: idx_users_single_admin (管理者は1ユーザーのみ)
```

### 実装設計

#### 1. モデル変更

**`app/models/user.py`**:
```python
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # ... existing columns ...

    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # 新規

    # ... existing methods ...
```

#### 2. 認可デコレーター

**`app/decorators.py` (新規)**:
```python
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user

def admin_required(f):
    """管理者権限が必要なルートを保護"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('管理者権限が必要です。', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
```

#### 3. ルート保護

**すべての管理機能に `@admin_required` デコレーターを適用**:
```python
from app.decorators import admin_required

@bp.route('/users')
@login_required
@admin_required  # 管理者のみ
def list_users():
    pass

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required  # 管理者のみ
def create_user():
    pass

# ... 他のルートも同様
```

#### 4. ログイン後のリダイレクト

**`app/routes/auth.py`**:
```python
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # ... 認証処理 ...

        login_user(user, remember=True)

        # 管理者のみログイン許可
        if user.is_admin:
            return redirect(url_for('dashboard'))
        else:
            flash('管理者のみログイン可能です。', 'error')
            logout_user()
            return redirect(url_for('auth.login'))

    return render_template('login.html')
```

### マイグレーション手順

#### Phase 11-A-1: データベースマイグレーション (0.5時間)

1. マイグレーションSQL作成
2. バックアップ取得
3. マイグレーション実行
4. 検証

#### Phase 11-A-2: バックエンド実装 (1時間)

1. モデル更新
2. デコレーター実装
3. ルート保護
4. ログイン処理変更

#### Phase 11-A-3: テスト・検証 (0.5時間)

1. 管理者ログインテスト
2. 通常ユーザーログイン拒否テスト
3. 権限保護テスト

**合計見積もり**: 2時間

---

## 🌐 Phase 11-B: ドメイン管理機能

### 要件

**現状の課題**:
- ドメインを追加・編集・削除する機能が存在しない
- 初期データとして `kuma8088.com` のみ存在
- 新しいドメインを追加するにはSQLで直接操作が必要

**目標**:
- **ドメイン一覧表示**: 登録されているドメインの一覧を表示
- **ドメイン追加**: 新しいドメインを追加
- **ドメイン編集**: 既存ドメインの説明やデフォルト容量を編集
- **ドメイン削除**: 不要なドメインを削除（ユーザーがいない場合のみ）
- **ドメイン有効化/無効化**: ドメインの利用可否を切り替え

### 機能詳細

#### 1. ドメイン一覧表示

**表示内容**:
- ドメイン名
- 説明
- デフォルト容量
- ユーザー数
- 有効/無効状態
- 作成日
- 操作ボタン（編集・削除・有効化/無効化）

**UI例**:
```
ドメイン一覧

+-------------+------------------+----------+----------+------+------------+----------+
| ドメイン名   | 説明              | 容量     | ユーザー数 | 状態  | 作成日      | 操作     |
+-------------+------------------+----------+----------+------+------------+----------+
| kuma8088.com| メインドメイン    | 1024 MB  | 5        | 有効  | 2025-11-01 | 編集 削除|
| example.com | テストドメイン    | 512 MB   | 0        | 無効  | 2025-11-05 | 編集 削除|
+-------------+------------------+----------+----------+------+------------+----------+

[+ 新規ドメイン追加]
```

#### 2. ドメイン追加

**入力フィールド**:
- ドメイン名（必須、一意制約）
- 説明（任意）
- デフォルト容量（MB、デフォルト: 1024）
- 有効/無効（デフォルト: 有効）

**バリデーション**:
- ドメイン名形式チェック（例: `example.com`）
- 重複チェック
- デフォルト容量範囲チェック（1～10240MB）

#### 3. ドメイン編集

**編集可能項目**:
- 説明
- デフォルト容量
- 有効/無効状態

**編集不可項目**:
- ドメイン名（作成後変更不可）

#### 4. ドメイン削除

**削除条件**:
- ❌ ユーザーが紐づいている場合は削除不可
- ✅ ユーザーが0の場合のみ削除可能

**削除時の確認**:
```
本当にドメイン "example.com" を削除しますか？
この操作は取り消せません。

[キャンセル] [削除]
```

#### 5. ドメイン有効化/無効化

**無効化の影響**:
- 新規ユーザー作成時にドメイン選択リストに表示されない
- 既存ユーザーには影響なし
- 管理者はドメイン一覧で確認可能

### データベース設計

#### 1. `domains` テーブル変更

**新規カラム追加**:
```sql
ALTER TABLE domains ADD COLUMN enabled BOOLEAN DEFAULT TRUE NOT NULL;
CREATE INDEX idx_domains_enabled ON domains (enabled);
```

**マイグレーション後のテーブル構造**:
```
domains
├── id (INT, PRIMARY KEY, AUTO_INCREMENT)
├── name (VARCHAR(255), UNIQUE, NOT NULL, INDEX)
├── description (VARCHAR(500), NULLABLE)
├── default_quota (INT, DEFAULT 1024, NOT NULL)
├── enabled (BOOLEAN, DEFAULT TRUE, NOT NULL)  ← 新規
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

INDEX: idx_domains_enabled (有効/無効フィルタ用)
```

#### 2. 制約

```sql
-- ユーザーが存在する場合は削除不可（外部キー制約）
ALTER TABLE users ADD CONSTRAINT fk_users_domain
    FOREIGN KEY (domain_id) REFERENCES domains(id)
    ON DELETE RESTRICT;
```

### 実装設計

#### 1. モデル変更

**`app/models/domain.py`**:
```python
class Domain(db.Model):
    __tablename__ = 'domains'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=True)
    default_quota = db.Column(db.Integer, default=1024, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)  # 新規
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = db.relationship('User', backref='domain', lazy='dynamic')

    def user_count(self):
        """このドメインのユーザー数を返す"""
        return self.users.count()

    def __repr__(self):
        return f'<Domain {self.name}>'
```

#### 2. ドメイン管理サービス

**`app/services/domain_service.py` (新規)**:
```python
"""
Domain Service - Business logic for domain management operations
"""
import json
from app.database import db
from app.models import Domain, AuditLog
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

class DomainService:
    """ドメイン管理サービス"""

    @staticmethod
    def list_domains(enabled_only: bool = False) -> List[Domain]:
        """
        ドメイン一覧取得

        Args:
            enabled_only: 有効なドメインのみ取得

        Returns:
            Domainオブジェクトのリスト
        """
        query = Domain.query
        if enabled_only:
            query = query.filter_by(enabled=True)
        return query.order_by(Domain.name).all()

    @staticmethod
    def create_domain(
        name: str,
        description: str = '',
        default_quota: int = 1024,
        enabled: bool = True,
        admin_ip: str = 'system'
    ) -> Domain:
        """
        ドメイン作成

        Args:
            name: ドメイン名
            description: 説明
            default_quota: デフォルト容量（MB）
            enabled: 有効/無効
            admin_ip: 管理者IP（監査ログ用）

        Returns:
            作成されたDomainオブジェクト

        Raises:
            ValueError: ドメイン名が既に存在する場合
        """
        # 重複チェック
        existing = Domain.query.filter_by(name=name).first()
        if existing:
            raise ValueError("このドメイン名は既に登録されています")

        domain = Domain(
            name=name,
            description=description,
            default_quota=default_quota,
            enabled=enabled
        )

        try:
            db.session.add(domain)
            db.session.commit()

            # 監査ログ
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
        ドメイン更新

        Args:
            domain_id: ドメインID
            admin_ip: 管理者IP（監査ログ用）
            **kwargs: 更新する属性

        Returns:
            更新されたDomainオブジェクト

        Raises:
            ValueError: ドメインが見つからない、またはドメイン名変更を試みた場合
        """
        # ドメイン名変更は禁止
        if 'name' in kwargs:
            raise ValueError("ドメイン名は変更できません")

        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # 変更追跡
        changes = []
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

                # 監査ログ
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
        ドメイン削除

        Args:
            domain_id: ドメインID
            admin_ip: 管理者IP（監査ログ用）

        Raises:
            ValueError: ドメインが見つからない、またはユーザーが存在する場合
        """
        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # ユーザーが存在する場合は削除不可
        if domain.user_count() > 0:
            raise ValueError(
                f"このドメインには {domain.user_count()} 人のユーザーが存在します。"
                "先にユーザーを削除してください。"
            )

        domain_name = domain.name

        try:
            db.session.delete(domain)
            db.session.commit()

            # 監査ログ
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
        監査ログ作成

        Args:
            action: アクション (create, update, delete)
            domain_name: ドメイン名
            admin_ip: 管理者IP
            details: 詳細（JSON形式）

        Returns:
            作成されたAuditLogオブジェクト
        """
        audit_log = AuditLog(
            action=action,
            user_email=f'domain:{domain_name}',  # ドメイン操作を識別
            admin_ip=admin_ip,
            details=details
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log
```

#### 3. ルート実装

**`app/routes/domains.py` (新規)**:
```python
"""
Domain management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.decorators import admin_required
from app.services.domain_service import DomainService

bp = Blueprint('domains', __name__, url_prefix='/domains')

@bp.route('/')
@login_required
@admin_required
def list():
    """ドメイン一覧"""
    domains = DomainService.list_domains()
    return render_template('domains/list.html', domains=domains)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """ドメイン作成"""
    if request.method == 'GET':
        return render_template('domains/create.html')

    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', 1024, type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

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

@bp.route('/<int:domain_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(domain_id):
    """ドメイン編集"""
    domain = DomainService.list_domains()
    domain = next((d for d in domain if d.id == domain_id), None)

    if not domain:
        flash('ドメインが見つかりません。', 'danger')
        return redirect(url_for('domains.list'))

    if request.method == 'GET':
        return render_template('domains/edit.html', domain=domain)

    try:
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        DomainService.update_domain(
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

@bp.route('/<int:domain_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(domain_id):
    """ドメイン削除"""
    try:
        DomainService.delete_domain(
            domain_id=domain_id,
            admin_ip=request.remote_addr
        )
        flash('ドメインを削除しました。', 'success')
    except ValueError as e:
        flash(f'ドメイン削除に失敗しました: {str(e)}', 'danger')

    return redirect(url_for('domains.list'))
```

### マイグレーション手順

#### Phase 11-B-1: データベースマイグレーション (0.5時間)

1. マイグレーションSQL作成
2. バックアップ取得
3. マイグレーション実行
4. 検証

#### Phase 11-B-2: バックエンド実装 (1.5時間)

1. モデル更新
2. DomainService実装
3. ルート実装

#### Phase 11-B-3: フロントエンド実装 (1時間)

1. ドメイン一覧画面
2. ドメイン作成画面
3. ドメイン編集画面
4. ナビゲーション追加

#### Phase 11-B-4: テスト・検証 (0.5時間)

1. ドメインCRUD操作テスト
2. 削除制約テスト
3. 監査ログ確認

**合計見積もり**: 3.5時間

---

## 📊 Phase 11 全体スケジュール

| フェーズ | 機能 | 見積もり | 依存関係 |
|---------|------|---------|---------|
| Phase 11-A | 管理者・ユーザー権限分離 | 2時間 | なし |
| Phase 11-B | ドメイン管理機能 | 3.5時間 | Phase 11-A 完了後 |
| **合計** | | **5.5時間** | |

---

## 🧪 統合テスト計画

### Phase 11-A テスト

**管理者機能**:
- ✅ 管理者でログイン → ダッシュボード表示
- ✅ 全機能アクセス可能
- ✅ ドメイン管理機能アクセス可能

**通常ユーザー機能**:
- ❌ 通常ユーザーでログイン試行 → 拒否
- ✅ IMAPログインは成功

**制約テスト**:
- ❌ 2人目の管理者作成試行 → エラー
- ✅ 管理者フラグの切り替え

### Phase 11-B テスト

**ドメイン作成**:
- ✅ 新規ドメイン作成成功
- ❌ 重複ドメイン名 → エラー
- ✅ 監査ログ記録

**ドメイン編集**:
- ✅ 説明・容量・状態変更成功
- ❌ ドメイン名変更試行 → エラー

**ドメイン削除**:
- ✅ ユーザー0のドメイン削除成功
- ❌ ユーザー存在するドメイン削除試行 → エラー

---

## 📝 実装優先順位

### 推奨実装順序

1. **Phase 11-A: 管理者・ユーザー権限分離** (先行実装)
   - セキュリティ強化が最優先
   - ドメイン管理機能の前提条件

2. **Phase 11-B: ドメイン管理機能** (Phase 11-A 完了後)
   - 管理者権限が必要
   - Phase 11-A のデコレーター活用

---

## 🚀 次のステップ

Phase 11 実装を開始する前に、以下を確認してください：

### Phase 11-A 確認事項

1. ✅ 通常ユーザーは管理画面にログイン不可でよいか？
2. ✅ 管理者変更は必要か？（管理画面で変更 vs SQL手動変更）
3. ✅ 監査ログに権限変更を記録するか？

### Phase 11-B 確認事項

1. ✅ ドメイン削除条件は「ユーザー0の場合のみ」でよいか？
2. ✅ ドメイン無効化時の既存ユーザーへの影響は「なし」でよいか？
3. ✅ ドメイン名は作成後変更不可でよいか？

---

**準備完了後、Phase 11-A から実装を開始します。**
