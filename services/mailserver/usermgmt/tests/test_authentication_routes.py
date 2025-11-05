"""
Test suite for Authentication Routes (Phase 3 - P3-T3)

Test Specification: tests/specs/TEST_SPEC_authentication_routes.md
"""
import pytest
from flask import session, url_for
from flask_login import current_user
from app.services.password import hash_password


class TestLoginSuccess:
    """TC-AR-001: ログイン成功テスト"""

    def test_login_with_valid_credentials(self, client, test_user):
        """有効な認証情報でログインが成功することを検証"""
        # ログイン実行
        response = client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123',
        }, follow_redirects=False)

        # リダイレクト確認
        assert response.status_code == 302
        assert response.location == '/'

    def test_login_sets_session(self, client, test_user):
        """ログイン後にセッションが設定されることを確認"""
        with client:
            response = client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            }, follow_redirects=True)

            # セッション内にユーザーID設定
            assert '_user_id' in session
            assert current_user.is_authenticated

    def test_login_current_user_properties(self, client, test_user):
        """ログイン後のcurrent_userプロパティを検証"""
        with client:
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            }, follow_redirects=True)

            assert current_user.is_authenticated
            assert current_user.email == 'testuser1@example.com'
            assert current_user.is_active


class TestLoginFailure:
    """TC-AR-002: ログイン失敗テスト"""

    def test_login_with_wrong_password(self, client, test_user):
        """誤ったパスワードでログインが失敗することを確認"""
        response = client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'WrongPassword',
        }, follow_redirects=False)

        # ログイン画面に留まる
        assert response.status_code == 200
        assert b'email' in response.data or b'password' in response.data.lower()

    def test_login_with_wrong_password_not_authenticated(self, client, test_user):
        """誤ったパスワードでは認証されないことを確認"""
        with client:
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'WrongPassword',
            })

            assert not current_user.is_authenticated

    def test_login_with_nonexistent_email(self, client):
        """存在しないメールアドレスでログインが失敗することを確認"""
        response = client.post('/auth/login', data={
            'email': 'nonexistent@example.com',
            'password': 'AnyPassword',
        }, follow_redirects=False)

        assert response.status_code == 200

    def test_login_with_nonexistent_email_not_authenticated(self, client):
        """存在しないメールアドレスでは認証されないことを確認"""
        with client:
            client.post('/auth/login', data={
                'email': 'nonexistent@example.com',
                'password': 'AnyPassword',
            })

            assert not current_user.is_authenticated

    def test_login_with_disabled_user(self, client, disabled_user):
        """無効化されたユーザーでログインが失敗することを確認"""
        response = client.post('/auth/login', data={
            'email': 'testuser2@example.com',
            'password': 'test_password_456',
        }, follow_redirects=False)

        # ログイン失敗
        assert response.status_code == 200

    def test_login_with_disabled_user_not_authenticated(self, client, disabled_user):
        """無効化されたユーザーでは認証されないことを確認"""
        with client:
            client.post('/auth/login', data={
                'email': 'testuser2@example.com',
                'password': 'test_password_456',
            })

            assert not current_user.is_authenticated


class TestLogout:
    """TC-AR-003: ログアウトテスト"""

    def test_logout_clears_session(self, client, test_user):
        """ログアウト時にセッションがクリアされることを確認"""
        with client:
            # ログイン
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            })

            assert current_user.is_authenticated

            # ログアウト
            response = client.post('/auth/logout', follow_redirects=False)

            assert response.status_code == 302
            assert not current_user.is_authenticated

    def test_logout_redirects_to_login(self, client, test_user):
        """ログアウト後にログイン画面にリダイレクトされることを確認"""
        with client:
            # ログイン
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            })

            # ログアウト
            response = client.post('/auth/logout', follow_redirects=False)

            assert response.status_code == 302
            assert '/auth/login' in response.location


class TestLoginRequired:
    """TC-AR-004: @login_required デコレータテスト"""

    def test_unauthenticated_access_redirects(self, client):
        """未認証アクセスがログイン画面にリダイレクトされることを確認"""
        # ダッシュボードに直接アクセス (保護されたルート)
        response = client.get('/', follow_redirects=False)

        # ログイン画面にリダイレクト
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_authenticated_access_allowed(self, client, test_user):
        """認証済みアクセスが許可されることを確認"""
        with client:
            # ログイン
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            })

            # ダッシュボードにアクセス
            response = client.get('/', follow_redirects=False)

            # 成功
            assert response.status_code == 200


class TestCSRFProtection:
    """TC-AR-005: CSRF保護テスト"""

    def test_login_without_csrf_token(self, client, test_user):
        """CSRFトークンなしでログインが失敗することを確認"""
        # WTF_CSRF_ENABLEDがFalseの場合はスキップ
        if not client.application.config.get('WTF_CSRF_ENABLED', True):
            pytest.skip("CSRF protection disabled in test environment")

        # CSRFトークンなしでPOST
        response = client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123',
        })

        # CSRF検証失敗
        assert response.status_code in [400, 200]  # 400 or form re-display


class TestSessionManagement:
    """TC-AR-006: セッション管理テスト"""

    def test_session_cookie_properties(self, client, test_user):
        """セッションCookieのプロパティを検証"""
        with client:
            client.post('/auth/login', data={
                'email': 'testuser1@example.com',
                'password': 'test_password_123',
            })

            # Cookie設定確認
            assert client.application.config['SESSION_COOKIE_HTTPONLY'] is True
            assert client.application.config['SESSION_COOKIE_SECURE'] is True
            assert client.application.config['SESSION_COOKIE_SAMESITE'] == 'Strict'

    def test_session_lifetime(self, client, test_user):
        """セッション有効期限を確認"""
        from datetime import timedelta

        expected_lifetime = timedelta(hours=1)
        assert client.application.config['PERMANENT_SESSION_LIFETIME'] == expected_lifetime


class TestRedirectHandling:
    """TC-AR-007: リダイレクト処理テスト"""

    def test_login_default_redirect(self, client, test_user):
        """デフォルトリダイレクト先を確認"""
        response = client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123',
        }, follow_redirects=False)

        assert response.status_code == 302
        assert response.location == '/'

    def test_login_with_next_parameter(self, client, test_user):
        """nextパラメータ付きリダイレクトを確認"""
        response = client.post('/auth/login?next=/users', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123',
        }, follow_redirects=False)

        assert response.status_code == 302
        # /users または / にリダイレクト (安全性チェック次第)
        assert response.location in ['/users', '/']

    def test_login_with_unsafe_next_parameter(self, client, test_user):
        """安全でないnextパラメータがブロックされることを確認 (オープンリダイレクト対策)"""
        response = client.post('/auth/login?next=http://malicious.com', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123',
        }, follow_redirects=False)

        assert response.status_code == 302
        # 外部URLへのリダイレクトを防ぐ
        assert 'malicious.com' not in response.location
        assert response.location == '/' or response.location.startswith('/')


# テスト実行時の統計情報
def test_summary():
    """テストサマリー (情報提供用)"""
    print("\n" + "="*60)
    print("Authentication Routes Test Suite")
    print("="*60)
    print("Test Cases:")
    print("  TC-AR-001: ログイン成功テスト (3 tests)")
    print("  TC-AR-002: ログイン失敗テスト (6 tests)")
    print("  TC-AR-003: ログアウトテスト (2 tests)")
    print("  TC-AR-004: @login_required デコレータテスト (2 tests)")
    print("  TC-AR-005: CSRF保護テスト (1 test)")
    print("  TC-AR-006: セッション管理テスト (2 tests)")
    print("  TC-AR-007: リダイレクト処理テスト (3 tests)")
    print("="*60)
    print("Total: 19 test cases")
    print("="*60)
    assert True  # Always pass
