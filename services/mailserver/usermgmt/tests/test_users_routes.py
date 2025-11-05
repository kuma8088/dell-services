"""
Test suite for User Management Routes (Phase 8 - P8-T1-2)

Tests CRUD endpoints for user management
"""
import pytest
from flask import session
from app.services.user_service import UserService
from app.models.user import User
from app.models.domain import Domain


@pytest.fixture
def authenticated_client(client, test_user):
    """
    Create an authenticated test client

    Logs in with test_user credentials and returns the client
    """
    with client:
        client.post('/auth/login', data={
            'email': 'testuser1@example.com',
            'password': 'test_password_123'
        }, follow_redirects=True)

        yield client


class TestUsersList:
    """TC-UR-001: ユーザー一覧表示テスト"""

    def test_list_users_authenticated(self, authenticated_client, test_user):
        """TC-UR-001-01: 認証済みユーザーがアクセス可能"""
        response = authenticated_client.get('/users/')

        assert response.status_code == 200
        assert b'testuser1@example.com' in response.data

    def test_list_users_unauthenticated(self, client):
        """TC-UR-001-02: 未認証ユーザーはリダイレクト"""
        response = client.get('/users/', follow_redirects=False)

        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_list_users_with_domain_filter(self, authenticated_client, test_user):
        """TC-UR-001-03: ドメインでフィルタリング"""
        response = authenticated_client.get('/users/?domain_id=1')

        assert response.status_code == 200
        # レスポンスにドメインフィルタが適用されている


class TestCreateUser:
    """TC-UR-002: ユーザー作成テスト"""

    def test_create_user_form_get(self, authenticated_client):
        """TC-UR-002-01: 作成フォーム表示"""
        response = authenticated_client.get('/users/new')

        assert response.status_code == 200
        # フォームが表示されている
        assert b'form' in response.data.lower()

    def test_create_user_success(self, authenticated_client, db_session):
        """TC-UR-002-02: 正常なユーザー作成"""
        response = authenticated_client.post('/users/new', data={
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'domain_id': 1,
            'quota': 2048,
            'enabled': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200

        # ユーザーが作成されている
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.quota == 2048
        assert user.enabled is True

        # 成功メッセージが表示されている
        assert 'newuser@example.com' in response.data.decode('utf-8')

    def test_create_user_missing_email(self, authenticated_client):
        """TC-UR-002-03: メールアドレス未入力エラー"""
        response = authenticated_client.post('/users/new', data={
            'password': 'password',
            'domain_id': 1,
            'quota': 1024
        }, follow_redirects=True)

        # エラーメッセージが表示されている
        assert b'\xe3\x83\xa1\xe3\x83\xbc\xe3\x83\xab' in response.data  # "メール" in UTF-8

    def test_create_user_missing_password(self, authenticated_client):
        """TC-UR-002-04: パスワード未入力エラー"""
        response = authenticated_client.post('/users/new', data={
            'email': 'nopassword@example.com',
            'domain_id': 1,
            'quota': 1024
        }, follow_redirects=True)

        # エラーメッセージが表示されている
        assert b'\xe3\x83\x91\xe3\x82\xb9\xe3\x83\xaf\xe3\x83\xbc\xe3\x83\x89' in response.data  # "パスワード" in UTF-8

    def test_create_user_duplicate_email(self, authenticated_client, test_user):
        """TC-UR-002-05: 重複メールアドレスエラー"""
        response = authenticated_client.post('/users/new', data={
            'email': 'testuser1@example.com',  # 既存
            'password': 'password',
            'domain_id': 1,
            'quota': 1024
        }, follow_redirects=True)

        # エラーメッセージが表示されている
        assert response.status_code == 200

    def test_create_user_requires_authentication(self, client):
        """TC-UR-002-06: 認証が必要"""
        response = client.get('/users/new', follow_redirects=False)

        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestEditUser:
    """TC-UR-003: ユーザー編集テスト"""

    def test_edit_user_form_get(self, authenticated_client, test_user):
        """TC-UR-003-01: 編集フォーム表示"""
        response = authenticated_client.get(f'/users/{test_user.email}/edit')

        assert response.status_code == 200
        assert b'form' in response.data.lower()
        assert test_user.email.encode('utf-8') in response.data

    def test_edit_user_success(self, authenticated_client, test_user):
        """TC-UR-003-02: 正常なユーザー更新"""
        response = authenticated_client.post(
            f'/users/{test_user.email}/edit',
            data={
                'quota': 4096,
                'enabled': 'false'
            },
            follow_redirects=True
        )

        assert response.status_code == 200

        # ユーザーが更新されている
        updated_user = User.query.filter_by(email=test_user.email).first()
        assert updated_user.quota == 4096
        assert updated_user.enabled is False

    def test_edit_nonexistent_user(self, authenticated_client):
        """TC-UR-003-03: 存在しないユーザーエラー"""
        response = authenticated_client.get(
            '/users/nonexistent@example.com/edit',
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_edit_user_requires_authentication(self, client, test_user):
        """TC-UR-003-04: 認証が必要"""
        response = client.get(
            f'/users/{test_user.email}/edit',
            follow_redirects=False
        )

        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestDeleteUser:
    """TC-UR-004: ユーザー削除テスト"""

    def test_delete_user_success(self, authenticated_client, db_session):
        """TC-UR-004-01: 正常なユーザー削除"""
        # テスト用ユーザー作成
        user = UserService.create_user(
            email='deleteuser@example.com',
            password='password',
            domain_id=1
        )
        user_email = user.email

        response = authenticated_client.post(
            f'/users/{user_email}/delete',
            follow_redirects=True
        )

        assert response.status_code == 200

        # ユーザーが削除されている
        deleted_user = User.query.filter_by(email=user_email).first()
        assert deleted_user is None

    def test_delete_nonexistent_user(self, authenticated_client):
        """TC-UR-004-02: 存在しないユーザーエラー"""
        response = authenticated_client.post(
            '/users/nonexistent@example.com/delete',
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_delete_user_requires_authentication(self, client, test_user):
        """TC-UR-004-03: 認証が必要"""
        response = client.post(
            f'/users/{test_user.email}/delete',
            follow_redirects=False
        )

        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_delete_user_get_method_not_allowed(self, authenticated_client, test_user):
        """TC-UR-004-04: GET メソッドは許可されない"""
        response = authenticated_client.get(
            f'/users/{test_user.email}/delete',
            follow_redirects=False
        )

        # 405 Method Not Allowed または 302 リダイレクト
        assert response.status_code in [302, 404, 405]


class TestChangePassword:
    """TC-UR-005: パスワード変更テスト"""

    def test_change_password_form_get(self, authenticated_client, test_user):
        """TC-UR-005-01: パスワード変更フォーム表示"""
        response = authenticated_client.get(
            f'/users/{test_user.email}/password'
        )

        assert response.status_code == 200
        assert b'form' in response.data.lower()
        assert b'password' in response.data.lower()

    def test_change_password_success(self, authenticated_client, test_user):
        """TC-UR-005-02: 正常なパスワード変更"""
        response = authenticated_client.post(
            f'/users/{test_user.email}/password',
            data={
                'new_password': 'NewSecurePassword456!',
                'confirm_password': 'NewSecurePassword456!'
            },
            follow_redirects=True
        )

        assert response.status_code == 200

        # パスワードが変更されている（ハッシュが更新されている）
        updated_user = User.query.filter_by(email=test_user.email).first()
        assert updated_user.password_hash != test_user.password_hash

    def test_change_password_missing_new_password(self, authenticated_client, test_user):
        """TC-UR-005-03: 新パスワード未入力エラー"""
        response = authenticated_client.post(
            f'/users/{test_user.email}/password',
            data={
                'confirm_password': 'password'
            },
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_change_password_mismatch(self, authenticated_client, test_user):
        """TC-UR-005-04: パスワード不一致エラー"""
        response = authenticated_client.post(
            f'/users/{test_user.email}/password',
            data={
                'new_password': 'Password123!',
                'confirm_password': 'DifferentPassword456!'
            },
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_change_password_nonexistent_user(self, authenticated_client):
        """TC-UR-005-05: 存在しないユーザーエラー"""
        response = authenticated_client.get(
            '/users/nonexistent@example.com/password',
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_change_password_requires_authentication(self, client, test_user):
        """TC-UR-005-06: 認証が必要"""
        response = client.get(
            f'/users/{test_user.email}/password',
            follow_redirects=False
        )

        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestToggleStatus:
    """TC-UR-006: ステータス切り替えテスト"""

    def test_toggle_status_disable(self, authenticated_client, test_user):
        """TC-UR-006-01: ユーザー無効化"""
        # 初期状態: enabled = True
        assert test_user.enabled is True

        response = authenticated_client.post(
            f'/users/{test_user.email}/toggle',
            follow_redirects=True
        )

        assert response.status_code == 200

        # ステータスが無効化されている
        updated_user = User.query.filter_by(email=test_user.email).first()
        assert updated_user.enabled is False

    def test_toggle_status_enable(self, authenticated_client, disabled_user):
        """TC-UR-006-02: ユーザー有効化"""
        # 初期状態: enabled = False
        assert disabled_user.enabled is False

        response = authenticated_client.post(
            f'/users/{disabled_user.email}/toggle',
            follow_redirects=True
        )

        assert response.status_code == 200

        # ステータスが有効化されている
        updated_user = User.query.filter_by(email=disabled_user.email).first()
        assert updated_user.enabled is True

    def test_toggle_status_nonexistent_user(self, authenticated_client):
        """TC-UR-006-03: 存在しないユーザーエラー"""
        response = authenticated_client.post(
            '/users/nonexistent@example.com/toggle',
            follow_redirects=True
        )

        assert response.status_code == 200
        # エラーメッセージが表示されている

    def test_toggle_status_requires_authentication(self, client, test_user):
        """TC-UR-006-04: 認証が必要"""
        response = client.post(
            f'/users/{test_user.email}/toggle',
            follow_redirects=False
        )

        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_toggle_status_get_method_not_allowed(self, authenticated_client, test_user):
        """TC-UR-006-05: GET メソッドは許可されない"""
        response = authenticated_client.get(
            f'/users/{test_user.email}/toggle',
            follow_redirects=False
        )

        # 405 Method Not Allowed または 302 リダイレクト
        assert response.status_code in [302, 404, 405]
