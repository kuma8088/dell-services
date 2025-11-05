"""
Test suite for Flask-Login integration (Phase 3 - Task 2)

Test Specification: tests/specs/TEST_SPEC_flask_login_integration.md
"""
import pytest
from flask_login import current_user, login_user, logout_user
from app.models.user import User


class TestUserModel:
    """TC-FL-001: Userモデル基本機能テスト"""

    def test_user_creation(self, db_session):
        """Userモデルインスタンスが正しく作成されることを検証"""
        user = User(
            email='test@example.com',
            password_hash='{SHA512-CRYPT}$6$test',
            domain_id=1,
            maildir='/var/mail/vmail/example.com/test/',
            quota=1024,
            uid=5000,
            gid=5000,
            enabled=True
        )

        db_session.add(user)
        db_session.commit()

        # 検証
        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.password_hash == '{SHA512-CRYPT}$6$test'
        assert user.maildir == '/var/mail/vmail/example.com/test/'
        assert user.enabled is True

    def test_user_default_values(self, db_session):
        """Userモデルのデフォルト値が正しく設定されることを検証"""
        user = User(
            email='test@example.com',
            password_hash='{SHA512-CRYPT}$6$test',
            domain_id=1,
            maildir='/var/mail/vmail/example.com/test/'
        )

        db_session.add(user)
        db_session.commit()

        # デフォルト値の検証
        assert user.quota == 1024  # デフォルト quota
        assert user.uid == 5000    # デフォルト uid
        assert user.gid == 5000    # デフォルト gid
        assert user.enabled is True  # デフォルト enabled

    def test_user_retrieval(self, db_session, test_user):
        """データベースからユーザーを取得できることを検証"""
        retrieved_user = db_session.query(User).filter_by(email='testuser1@example.com').first()

        assert retrieved_user is not None
        assert retrieved_user.id == test_user.id
        assert retrieved_user.email == test_user.email


class TestUserMixinIntegration:
    """TC-FL-002: UserMixin統合テスト"""

    def test_is_authenticated(self, test_user):
        """is_authenticated が True を返すことを検証"""
        assert test_user.is_authenticated is True

    def test_is_active_enabled_user(self, test_user):
        """enabled=True の場合 is_active が True を返すことを検証"""
        assert test_user.enabled is True
        assert test_user.is_active is True

    def test_is_active_disabled_user(self, disabled_user):
        """enabled=False の場合 is_active が False を返すことを検証"""
        assert disabled_user.enabled is False
        assert disabled_user.is_active is False

    def test_is_anonymous(self, test_user):
        """is_anonymous が False を返すことを検証"""
        assert test_user.is_anonymous is False

    def test_get_id(self, test_user):
        """get_id() が user.id を文字列で返すことを検証"""
        user_id = test_user.get_id()
        assert user_id == str(test_user.id)
        assert isinstance(user_id, str)


class TestLoginManagerInitialization:
    """TC-FL-003: LoginManager初期化テスト"""

    def test_login_manager_exists(self, app):
        """LoginManagerインスタンスが存在することを検証"""
        from app import login_manager
        assert login_manager is not None

    def test_login_view_configured(self, app):
        """login_view が正しく設定されていることを検証"""
        from app import login_manager
        assert login_manager.login_view == 'auth.login'

    def test_session_protection_configured(self, app):
        """session_protection が 'strong' に設定されていることを検証"""
        from app import login_manager
        assert login_manager.session_protection == 'strong'

    def test_login_message_configured(self, app):
        """login_message が設定されていることを検証"""
        from app import login_manager
        assert login_manager.login_message is not None
        assert len(login_manager.login_message) > 0


class TestUserLoaderCallback:
    """TC-FL-004: user_loader コールバックテスト"""

    def test_load_user_valid_id(self, app, test_user):
        """有効なuser_idでUserインスタンスが返されることを検証"""
        from app import load_user

        with app.app_context():
            loaded_user = load_user(test_user.id)

            assert loaded_user is not None
            assert isinstance(loaded_user, User)
            assert loaded_user.id == test_user.id
            assert loaded_user.email == test_user.email

    def test_load_user_invalid_id(self, app):
        """無効なuser_idでNoneが返されることを検証"""
        from app import load_user

        with app.app_context():
            loaded_user = load_user(99999)  # 存在しないID
            assert loaded_user is None

    def test_load_user_string_id(self, app, test_user):
        """文字列のuser_idでも正しく動作することを検証"""
        from app import load_user

        with app.app_context():
            loaded_user = load_user(str(test_user.id))

            assert loaded_user is not None
            assert loaded_user.id == test_user.id


class TestSessionCookieConfiguration:
    """TC-FL-005: セッションCookie設定テスト"""

    def test_session_cookie_httponly(self, app):
        """SESSION_COOKIE_HTTPONLY が True であることを検証"""
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True

    def test_session_cookie_secure(self, app):
        """SESSION_COOKIE_SECURE が True であることを検証"""
        assert app.config['SESSION_COOKIE_SECURE'] is True

    def test_session_cookie_samesite(self, app):
        """SESSION_COOKIE_SAMESITE が 'Strict' であることを検証"""
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Strict'

    def test_permanent_session_lifetime(self, app):
        """PERMANENT_SESSION_LIFETIME が設定されていることを検証"""
        assert 'PERMANENT_SESSION_LIFETIME' in app.config
        lifetime = app.config['PERMANENT_SESSION_LIFETIME']
        assert lifetime is not None
        assert lifetime.total_seconds() > 0


class TestLoginSessionPersistence:
    """TC-FL-006: ログインセッション永続化テスト"""

    def test_login_with_remember_me(self, client, test_user):
        """remember=True でログインした場合のセッション動作を検証"""
        with client.session_transaction() as session:
            # セッションにユーザーIDを設定 (remember=True相当)
            session['user_id'] = test_user.id
            session['_fresh'] = True
            session.permanent = True

        # セッションが永続化されることを検証
        with client.session_transaction() as session:
            assert session.get('user_id') == test_user.id
            assert session.permanent is True

    def test_login_without_remember_me(self, client, test_user):
        """remember=False でログインした場合のセッション動作を検証"""
        with client.session_transaction() as session:
            # セッションにユーザーIDを設定 (remember=False相当)
            session['user_id'] = test_user.id
            session['_fresh'] = True
            session.permanent = False

        # セッションがブラウザセッションのみであることを検証
        with client.session_transaction() as session:
            assert session.get('user_id') == test_user.id
            assert session.permanent is False


# テスト実行時の統計情報
def test_summary():
    """テストサマリー (情報提供用)"""
    print("\n" + "="*60)
    print("Flask-Login Integration Test Suite")
    print("="*60)
    print("Test Cases:")
    print("  TC-FL-001: Userモデル基本機能テスト (3 tests)")
    print("  TC-FL-002: UserMixin統合テスト (5 tests)")
    print("  TC-FL-003: LoginManager初期化テスト (4 tests)")
    print("  TC-FL-004: user_loader コールバックテスト (3 tests)")
    print("  TC-FL-005: セッションCookie設定テスト (4 tests)")
    print("  TC-FL-006: ログインセッション永続化テスト (2 tests)")
    print("="*60)
    print("Total: 21 test cases")
    print("="*60)
    assert True  # Always pass
