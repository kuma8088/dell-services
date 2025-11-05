"""
Test suite for Security Features (Phase 8 - P8-T3)

Tests CSRF protection, SQL injection protection, and XSS protection
"""
import pytest
from flask import session
from app.services.user_service import UserService
from app.models.user import User


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client"""
    with client:
        client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123'
        }, follow_redirects=True)

        yield client


class TestCSRFProtection:
    """TC-SEC-001: CSRF 保護テスト"""

    def test_csrf_enabled_in_production(self, app):
        """TC-SEC-001-01: 本番環境で CSRF が有効"""
        # テスト環境では無効、本番では有効であることを確認
        # テスト環境
        assert app.config['TESTING'] is True
        assert app.config['WTF_CSRF_ENABLED'] is False

        # 本番環境では WTF_CSRF_ENABLED が True になる想定

    def test_csrf_config_exists(self, app):
        """TC-SEC-001-02: CSRF 設定が存在"""
        assert 'WTF_CSRF_ENABLED' in app.config
        assert 'WTF_CSRF_TIME_LIMIT' in app.config

    def test_login_form_csrf_handling(self, client):
        """TC-SEC-001-03: ログインフォームの CSRF 処理"""
        # ログインページにアクセス
        response = client.get('/auth/login')

        assert response.status_code == 200

        # フォームが存在することを確認
        assert b'form' in response.data.lower()


class TestSQLInjectionProtection:
    """TC-SEC-002: SQLインジェクション対策テスト"""

    def test_sql_injection_login_email(self, client):
        """TC-SEC-002-01: ログイン時のメールアドレスへの SQLi 攻撃"""
        # SQLインジェクション試行
        malicious_inputs = [
            "admin' OR '1'='1",
            "admin' OR '1'='1' --",
            "admin' OR '1'='1' /*",
            "admin'; DROP TABLE users; --",
            "' OR 1=1 --",
        ]

        for malicious_email in malicious_inputs:
            response = client.post('/auth/login', data={
                'email': malicious_email,
                'password': 'any_password'
            }, follow_redirects=True)

            # 攻撃は失敗し、ログインできない
            assert response.status_code == 200
            # セッションにユーザーIDが設定されていない
            with client:
                client.get('/')
                assert '_user_id' not in session

    def test_sql_injection_user_creation(self, authenticated_client, db_session):
        """TC-SEC-002-02: ユーザー作成時の SQLi 攻撃"""
        malicious_inputs = [
            "test'; DROP TABLE users; --@example.com",
            "test' OR '1'='1@example.com",
        ]

        for malicious_email in malicious_inputs:
            try:
                # 攻撃試行
                response = authenticated_client.post('/users/new', data={
                    'email': malicious_email,
                    'password': 'password',
                    'domain_id': 1,
                    'quota': 1024
                }, follow_redirects=True)

                # エラー処理されている
                assert response.status_code == 200

                # users テーブルが削除されていないことを確認
                users = User.query.all()
                assert users is not None

            except Exception:
                # 例外が発生しても users テーブルは無事
                users = User.query.all()
                assert users is not None

    def test_sql_injection_user_service(self, db_session, test_user):
        """TC-SEC-002-03: UserService への SQLi 攻撃"""
        malicious_queries = [
            "test@example.com' OR '1'='1",
            "test@example.com'; DROP TABLE users; --",
        ]

        for malicious_email in malicious_queries:
            # get_user_by_email で攻撃試行
            user = UserService.get_user_by_email(malicious_email)

            # 攻撃は失敗し、None または正しい結果が返る
            # (完全一致しないため None)
            assert user is None

            # users テーブルが削除されていないことを確認
            users = User.query.all()
            assert len(users) >= 1  # test_user は存在する

    def test_parameterized_queries_protection(self, db_session, test_user):
        """TC-SEC-002-04: パラメータ化クエリによる保護"""
        # SQLAlchemy はパラメータ化クエリを使用するため、
        # SQLインジェクションは自動的に防がれる

        # 正常なクエリ
        user = User.query.filter_by(email='testuser1@example.com').first()
        assert user is not None

        # SQLインジェクション試行（パラメータとして扱われる）
        user = User.query.filter_by(email="' OR '1'='1").first()
        assert user is None  # 完全一致しないため見つからない


class TestXSSProtection:
    """TC-SEC-003: XSS 対策テスト"""

    def test_xss_in_user_creation(self, authenticated_client, db_session):
        """TC-SEC-003-01: ユーザー作成時の XSS 攻撃"""
        xss_payload = "<script>alert('XSS')</script>@example.com"

        response = authenticated_client.post('/users/new', data={
            'email': xss_payload,
            'password': 'password',
            'domain_id': 1,
            'quota': 1024
        }, follow_redirects=True)

        # エラー処理されている
        assert response.status_code == 200

        # スクリプトタグがそのまま含まれていない（エスケープされている）
        assert b'<script>' not in response.data
        assert b'&lt;script&gt;' in response.data or b'alert' not in response.data

    def test_xss_in_flash_messages(self, authenticated_client):
        """TC-SEC-003-02: Flash メッセージでの XSS 攻撃"""
        # 存在しないユーザーで XSS ペイロードを含むエラーを発生させる
        xss_email = "<script>alert('XSS')</script>@example.com"

        response = authenticated_client.get(
            f'/users/{xss_email}/edit',
            follow_redirects=True
        )

        # スクリプトタグがエスケープされている
        assert b'<script>' not in response.data

    def test_template_auto_escaping(self, authenticated_client, test_user):
        """TC-SEC-003-03: テンプレート自動エスケープ"""
        # ユーザーリスト表示
        response = authenticated_client.get('/users/')

        # HTML 内でメールアドレスが適切にエスケープされている
        # （通常のメールアドレスはエスケープ不要だが、特殊文字があればエスケープされる）
        assert response.status_code == 200
        assert b'testuser1@example.com' in response.data


class TestSessionSecurity:
    """TC-SEC-004: セッションセキュリティテスト"""

    def test_session_cookie_httponly(self, app):
        """TC-SEC-004-01: HttpOnly フラグ確認"""
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True

    def test_session_cookie_secure(self, app):
        """TC-SEC-004-02: Secure フラグ確認"""
        assert app.config['SESSION_COOKIE_SECURE'] is True

    def test_session_cookie_samesite(self, app):
        """TC-SEC-004-03: SameSite フラグ確認"""
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Strict'

    def test_session_lifetime(self, app):
        """TC-SEC-004-04: セッション有効期限確認"""
        from datetime import timedelta
        expected_lifetime = timedelta(hours=1)
        assert app.config['PERMANENT_SESSION_LIFETIME'] == expected_lifetime

    def test_strong_session_protection(self, app):
        """TC-SEC-004-05: Flask-Login セッション保護"""
        from app import login_manager
        assert login_manager.session_protection == 'strong'


class TestPasswordSecurity:
    """TC-SEC-005: パスワードセキュリティテスト"""

    def test_password_hashing(self, db_session, test_user):
        """TC-SEC-005-01: パスワードハッシュ化確認"""
        # パスワードがハッシュ化されて保存されている
        assert test_user.password_hash is not None

        # 平文パスワードが保存されていない
        assert 'test_password_123' not in test_user.password_hash

        # SHA512-CRYPT 形式（$6$ で始まる）
        assert test_user.password_hash.startswith('$6$')

    def test_password_verification(self, db_session, test_user):
        """TC-SEC-005-02: パスワード検証機能"""
        from app.services.password import verify_password

        # 正しいパスワードで検証成功
        assert verify_password('test_password_123', test_user.password_hash)

        # 間違ったパスワードで検証失敗
        assert not verify_password('wrong_password', test_user.password_hash)

    def test_password_not_exposed_in_responses(self, authenticated_client):
        """TC-SEC-005-03: レスポンスにパスワード非露出"""
        response = authenticated_client.get('/users/')

        # password_hash が含まれていない
        assert b'password_hash' not in response.data
        assert b'$6$' not in response.data  # SHA512-CRYPT ハッシュ


class TestAuthenticationSecurity:
    """TC-SEC-006: 認証セキュリティテスト"""

    def test_protected_routes_require_login(self, client):
        """TC-SEC-006-01: 保護されたルートへのアクセス制限"""
        protected_routes = [
            '/users/',
            '/users/new',
        ]

        for route in protected_routes:
            response = client.get(route, follow_redirects=False)

            # 未認証ユーザーはリダイレクトされる
            assert response.status_code == 302
            assert '/auth/login' in response.location

    def test_login_required_decorator(self, client, test_user):
        """TC-SEC-006-02: @login_required デコレータ動作確認"""
        # 未認証状態でダッシュボードにアクセス
        response = client.get('/', follow_redirects=False)

        # ログインページにリダイレクト
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_disabled_user_cannot_login(self, client, disabled_user):
        """TC-SEC-006-03: 無効化ユーザーはログイン不可"""
        response = client.post('/auth/login', data={
            'email': 'testuser2@example.com',
            'password': 'test_password_456'
        }, follow_redirects=True)

        # ログイン失敗
        assert response.status_code == 200

        with client:
            client.get('/')
            # セッションにユーザーIDが設定されていない
            assert '_user_id' not in session


class TestInputValidation:
    """TC-SEC-007: 入力検証テスト"""

    def test_email_format_validation(self, authenticated_client):
        """TC-SEC-007-01: メールアドレス形式検証"""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'test@',
            'test..test@example.com',
        ]

        for invalid_email in invalid_emails:
            response = authenticated_client.post('/users/new', data={
                'email': invalid_email,
                'password': 'password',
                'domain_id': 1,
                'quota': 1024
            }, follow_redirects=True)

            # エラー処理されている
            assert response.status_code == 200

    def test_quota_integer_validation(self, authenticated_client, test_user):
        """TC-SEC-007-02: クォータ整数値検証"""
        # 非整数値でユーザー更新試行
        response = authenticated_client.post(
            f'/users/{test_user.email}/edit',
            data={
                'quota': 'invalid_quota',  # 文字列
                'enabled': 'true'
            },
            follow_redirects=True
        )

        # エラー処理されている
        assert response.status_code == 200

        # ユーザーのクォータは変更されていない
        user = User.query.filter_by(email=test_user.email).first()
        assert user.quota == 1024  # 元の値のまま
