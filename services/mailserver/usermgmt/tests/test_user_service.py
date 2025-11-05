"""
Test suite for User Service (Phase 8 - P8-T1-3)

Tests business logic for user management operations
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.services.user_service import UserService
from app.models.user import User
from app.models.domain import Domain
from app.models.audit_log import AuditLog
from app.services.password import verify_password


class TestUserServiceListUsers:
    """TC-US-001: list_users メソッドテスト"""

    def test_list_all_users(self, db_session, test_user, disabled_user):
        """TC-US-001-01: 全ユーザーリスト取得"""
        users = UserService.list_users()

        assert len(users) >= 2
        emails = [u.email for u in users]
        assert 'testuser1@example.com' in emails
        assert 'testuser2@example.com' in emails

    def test_list_users_by_domain(self, db_session, test_user):
        """TC-US-001-02: ドメインでフィルタリング"""
        # ドメイン1のユーザーのみ取得
        users = UserService.list_users(domain_id=1)

        assert len(users) >= 1
        # 全てドメイン1のユーザー
        for user in users:
            assert user.domain_id == 1

    def test_list_users_ordered_by_email(self, db_session):
        """TC-US-001-03: メールアドレスでソート確認"""
        # 複数ユーザー作成
        UserService.create_user('zuser@example.com', 'pass123', 1)
        UserService.create_user('auser@example.com', 'pass123', 1)

        users = UserService.list_users()
        emails = [u.email for u in users]

        # メールアドレスでソートされている
        assert emails == sorted(emails)


class TestUserServiceCreateUser:
    """TC-US-002: create_user メソッドテスト"""

    def test_create_user_success(self, db_session):
        """TC-US-002-01: 正常なユーザー作成"""
        user = UserService.create_user(
            email='newuser@example.com',
            password='SecurePassword123!',
            domain_id=1,
            quota=2048,
            enabled=True,
            admin_ip='192.168.1.100'
        )

        assert user is not None
        assert user.email == 'newuser@example.com'
        assert user.domain_id == 1
        assert user.quota == 2048
        assert user.enabled is True

        # パスワードハッシュが正しく設定されている
        assert user.password_hash is not None
        assert verify_password('SecurePassword123!', user.password_hash)

        # maildir が自動生成されている
        assert user.maildir == '/var/mail/vmail/example.com/newuser/'

        # uid/gid が設定されている
        assert user.uid == 5000
        assert user.gid == 5000

    def test_create_user_with_defaults(self, db_session):
        """TC-US-002-02: デフォルト値での作成"""
        user = UserService.create_user(
            email='defaultuser@example.com',
            password='password',
            domain_id=1
        )

        # デフォルト quota = 1024
        assert user.quota == 1024

        # デフォルト enabled = True
        assert user.enabled is True

    def test_create_user_duplicate_email(self, db_session, test_user):
        """TC-US-002-03: 重複メールアドレスエラー"""
        with pytest.raises(ValueError, match="Email address already exists"):
            UserService.create_user(
                email='testuser1@example.com',  # 既存
                password='password',
                domain_id=1
            )

    def test_create_user_invalid_domain(self, db_session):
        """TC-US-002-04: 存在しないドメインID"""
        with pytest.raises(ValueError, match="Domain not found"):
            UserService.create_user(
                email='user@invalid.com',
                password='password',
                domain_id=99999  # 存在しない
            )

    def test_create_user_invalid_email_format(self, db_session):
        """TC-US-002-05: 不正なメールアドレス形式"""
        with pytest.raises(ValueError, match="Invalid email format"):
            UserService.create_user(
                email='invalid-email-no-at-sign',
                password='password',
                domain_id=1
            )

    def test_create_user_audit_log(self, db_session):
        """TC-US-002-06: 監査ログ記録確認"""
        UserService.create_user(
            email='audituser@example.com',
            password='password',
            domain_id=1,
            admin_ip='10.0.1.50'
        )

        # 監査ログが作成されている
        audit_logs = AuditLog.query.filter_by(
            user_email='audituser@example.com'
        ).all()

        assert len(audit_logs) > 0
        latest_audit = audit_logs[-1]
        assert latest_audit.action == 'create'
        assert latest_audit.admin_ip == '10.0.1.50'


class TestUserServiceGetUserByEmail:
    """TC-US-003: get_user_by_email メソッドテスト"""

    def test_get_existing_user(self, db_session, test_user):
        """TC-US-003-01: 存在するユーザー取得"""
        user = UserService.get_user_by_email('testuser1@example.com')

        assert user is not None
        assert user.email == 'testuser1@example.com'

    def test_get_nonexistent_user(self, db_session):
        """TC-US-003-02: 存在しないユーザー"""
        user = UserService.get_user_by_email('nonexistent@example.com')

        assert user is None


class TestUserServiceUpdateUser:
    """TC-US-004: update_user メソッドテスト"""

    def test_update_user_quota(self, db_session, test_user):
        """TC-US-004-01: クォータ更新"""
        original_quota = test_user.quota

        updated_user = UserService.update_user(
            email='testuser1@example.com',
            quota=4096,
            admin_ip='192.168.1.100'
        )

        assert updated_user.quota == 4096
        assert updated_user.quota != original_quota

    def test_update_user_enabled_status(self, db_session, test_user):
        """TC-US-004-02: 有効/無効ステータス更新"""
        updated_user = UserService.update_user(
            email='testuser1@example.com',
            enabled=False
        )

        assert updated_user.enabled is False

    def test_update_user_multiple_fields(self, db_session, test_user):
        """TC-US-004-03: 複数フィールド同時更新"""
        updated_user = UserService.update_user(
            email='testuser1@example.com',
            quota=8192,
            enabled=False,
            uid=5001,
            gid=5001
        )

        assert updated_user.quota == 8192
        assert updated_user.enabled is False
        assert updated_user.uid == 5001
        assert updated_user.gid == 5001

    def test_update_user_prevent_email_change(self, db_session, test_user):
        """TC-US-004-04: メールアドレス変更禁止"""
        with pytest.raises(ValueError, match="Email address cannot be changed"):
            UserService.update_user(
                email='testuser1@example.com',
                new_email='newemail@example.com'
            )

    def test_update_nonexistent_user(self, db_session):
        """TC-US-004-05: 存在しないユーザー更新エラー"""
        with pytest.raises(ValueError, match="User not found"):
            UserService.update_user(
                email='nonexistent@example.com',
                quota=2048
            )

    def test_update_user_audit_log(self, db_session, test_user):
        """TC-US-004-06: 監査ログ記録確認"""
        UserService.update_user(
            email='testuser1@example.com',
            quota=3072,
            admin_ip='10.0.1.50'
        )

        # 監査ログが作成されている
        audit_logs = AuditLog.query.filter_by(
            user_email='testuser1@example.com'
        ).all()

        assert len(audit_logs) > 0
        latest_audit = audit_logs[-1]
        assert latest_audit.action == 'update'
        assert latest_audit.admin_ip == '10.0.1.50'


class TestUserServiceDeleteUser:
    """TC-US-005: delete_user メソッドテスト"""

    def test_delete_user_success(self, db_session):
        """TC-US-005-01: 正常なユーザー削除"""
        # ユーザー作成
        user = UserService.create_user(
            email='deleteuser@example.com',
            password='password',
            domain_id=1
        )
        user_email = user.email

        # 削除実行
        UserService.delete_user(email=user_email, admin_ip='192.168.1.100')

        # データベースから削除されている
        deleted_user = User.query.filter_by(email=user_email).first()
        assert deleted_user is None

    def test_delete_nonexistent_user(self, db_session):
        """TC-US-005-02: 存在しないユーザー削除エラー"""
        with pytest.raises(ValueError, match="User not found"):
            UserService.delete_user(email='nonexistent@example.com')

    def test_delete_user_audit_log(self, db_session):
        """TC-US-005-03: 監査ログ記録確認"""
        # ユーザー作成
        user = UserService.create_user(
            email='auditdeleteuser@example.com',
            password='password',
            domain_id=1
        )
        user_email = user.email

        # 削除実行
        UserService.delete_user(email=user_email, admin_ip='10.0.1.50')

        # 監査ログが作成されている
        audit_logs = AuditLog.query.filter_by(
            user_email=user_email
        ).all()

        # 作成ログと削除ログの2つ
        assert len(audit_logs) >= 2
        delete_log = [log for log in audit_logs if log.action == 'delete'][0]
        assert delete_log.admin_ip == '10.0.1.50'


class TestUserServiceToggleStatus:
    """TC-US-006: toggle_user_status メソッドテスト"""

    def test_disable_user(self, db_session, test_user):
        """TC-US-006-01: ユーザー無効化"""
        updated_user = UserService.toggle_user_status(
            email='testuser1@example.com',
            enabled=False,
            admin_ip='192.168.1.100'
        )

        assert updated_user.enabled is False

    def test_enable_user(self, db_session, disabled_user):
        """TC-US-006-02: ユーザー有効化"""
        updated_user = UserService.toggle_user_status(
            email='testuser2@example.com',
            enabled=True,
            admin_ip='192.168.1.100'
        )

        assert updated_user.enabled is True

    def test_toggle_nonexistent_user(self, db_session):
        """TC-US-006-03: 存在しないユーザーエラー"""
        with pytest.raises(ValueError, match="User not found"):
            UserService.toggle_user_status(
                email='nonexistent@example.com',
                enabled=False
            )


class TestUserServiceChangePassword:
    """TC-US-007: change_password メソッドテスト"""

    def test_change_password_success(self, db_session, test_user):
        """TC-US-007-01: パスワード変更成功"""
        original_hash = test_user.password_hash

        updated_user = UserService.change_password(
            email='testuser1@example.com',
            new_password='NewSecurePassword456!',
            admin_ip='192.168.1.100'
        )

        # パスワードハッシュが変更されている
        assert updated_user.password_hash != original_hash

        # 新しいパスワードで検証できる
        assert verify_password('NewSecurePassword456!', updated_user.password_hash)

        # 古いパスワードは使えない
        assert not verify_password('test_password_123', updated_user.password_hash)

    def test_change_password_nonexistent_user(self, db_session):
        """TC-US-007-02: 存在しないユーザーエラー"""
        with pytest.raises(ValueError, match="User not found"):
            UserService.change_password(
                email='nonexistent@example.com',
                new_password='newpassword'
            )

    def test_change_password_audit_log(self, db_session, test_user):
        """TC-US-007-03: 監査ログ記録確認"""
        UserService.change_password(
            email='testuser1@example.com',
            new_password='AnotherPassword789!',
            admin_ip='10.0.1.50'
        )

        # 監査ログが作成されている
        audit_logs = AuditLog.query.filter_by(
            user_email='testuser1@example.com'
        ).all()

        assert len(audit_logs) > 0
        password_change_logs = [
            log for log in audit_logs
            if log.action == 'password_change'
        ]
        assert len(password_change_logs) > 0
        latest_log = password_change_logs[-1]
        assert latest_log.admin_ip == '10.0.1.50'


class TestUserServiceLogAudit:
    """TC-US-008: log_audit メソッドテスト"""

    def test_create_audit_log(self, db_session):
        """TC-US-008-01: 監査ログ作成"""
        audit_log = UserService.log_audit(
            action='test_action',
            user_email='test@example.com',
            admin_ip='192.168.1.100',
            details='{"message": "Test audit log"}'
        )

        assert audit_log is not None
        assert audit_log.action == 'test_action'
        assert audit_log.user_email == 'test@example.com'
        assert audit_log.admin_ip == '192.168.1.100'
        assert audit_log.details == '{"message": "Test audit log"}'

        # タイムスタンプが自動設定されている
        assert audit_log.timestamp is not None

    def test_audit_log_persistence(self, db_session):
        """TC-US-008-02: 監査ログの永続化確認"""
        UserService.log_audit(
            action='persist_test',
            user_email='persist@example.com',
            admin_ip='10.0.1.1',
            details='Test persistence'
        )

        # データベースから取得できる
        saved_log = AuditLog.query.filter_by(action='persist_test').first()
        assert saved_log is not None
        assert saved_log.user_email == 'persist@example.com'
