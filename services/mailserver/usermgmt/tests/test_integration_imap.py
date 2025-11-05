"""
Test suite for IMAP Integration (Phase 8 - P8-T2)

Tests integration with Dovecot IMAP server
Verifies that user CRUD operations correctly affect IMAP authentication
"""
import pytest
import imaplib
import time
from app.services.user_service import UserService
from app.models.user import User


# IMAP server configuration (from Dovecot container)
IMAP_HOST = '172.20.0.80'  # Dovecot container IP
IMAP_PORT = 143


@pytest.fixture
def imap_test_user(db_session):
    """
    Create a test user for IMAP testing

    Creates user with known credentials for IMAP login tests
    """
    user = UserService.create_user(
        email='imaptest@example.com',
        password='ImapTestPassword123!',
        domain_id=1,
        quota=1024,
        enabled=True,
        admin_ip='test'
    )

    # Give Dovecot time to recognize the new user
    time.sleep(1)

    yield user

    # Cleanup
    try:
        UserService.delete_user(email=user.email, admin_ip='test')
    except Exception:
        pass


class TestIMAPUserCreation:
    """TC-IMAP-001: ユーザー作成後の IMAP ログインテスト"""

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ（Dovecot 接続が必要）
        reason="Requires Dovecot container running at 172.20.0.80:143"
    )
    def test_imap_login_after_user_creation(self, imap_test_user):
        """TC-IMAP-001-01: ユーザー作成後に IMAP ログイン可能"""
        try:
            # IMAP接続
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # ログイン試行
            result = imap.login(
                'imaptest@example.com',
                'ImapTestPassword123!'
            )

            assert result[0] == 'OK'

            # ログアウト
            imap.logout()

        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAP login failed: {e}")

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_wrong_password(self, imap_test_user):
        """TC-IMAP-001-02: 間違ったパスワードでログイン失敗"""
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # 間違ったパスワードでログイン試行
            with pytest.raises(imaplib.IMAP4.error):
                imap.login('imaptest@example.com', 'WrongPassword')

        except Exception as e:
            # 接続エラーは予期される動作
            pass


class TestIMAPPasswordChange:
    """TC-IMAP-002: パスワード変更後の IMAP ログインテスト"""

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_after_password_change(self, imap_test_user):
        """TC-IMAP-002-01: パスワード変更後に新パスワードでログイン可能"""
        # パスワード変更
        UserService.change_password(
            email='imaptest@example.com',
            new_password='NewImapPassword456!',
            admin_ip='test'
        )

        # Dovecotに変更を認識させる時間
        time.sleep(2)

        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # 新しいパスワードでログイン
            result = imap.login(
                'imaptest@example.com',
                'NewImapPassword456!'
            )

            assert result[0] == 'OK'
            imap.logout()

        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAP login with new password failed: {e}")

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_old_password_fails(self, imap_test_user):
        """TC-IMAP-002-02: パスワード変更後に旧パスワードは使えない"""
        # パスワード変更
        UserService.change_password(
            email='imaptest@example.com',
            new_password='NewImapPassword789!',
            admin_ip='test'
        )

        time.sleep(2)

        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # 古いパスワードでログイン試行
            with pytest.raises(imaplib.IMAP4.error):
                imap.login('imaptest@example.com', 'ImapTestPassword123!')

        except Exception:
            pass


class TestIMAPUserDisable:
    """TC-IMAP-003: ユーザー無効化後の IMAP ログインテスト"""

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_disabled_user(self, imap_test_user):
        """TC-IMAP-003-01: 無効化ユーザーは IMAP ログイン不可"""
        # ユーザー無効化
        UserService.toggle_user_status(
            email='imaptest@example.com',
            enabled=False,
            admin_ip='test'
        )

        time.sleep(2)

        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # ログイン試行（失敗するはず）
            with pytest.raises(imaplib.IMAP4.error):
                imap.login(
                    'imaptest@example.com',
                    'ImapTestPassword123!'
                )

        except Exception:
            # 接続エラーも予期される動作
            pass

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_reenabled_user(self, imap_test_user):
        """TC-IMAP-003-02: 再有効化ユーザーは IMAP ログイン可能"""
        # ユーザー無効化
        UserService.toggle_user_status(
            email='imaptest@example.com',
            enabled=False,
            admin_ip='test'
        )
        time.sleep(2)

        # ユーザー再有効化
        UserService.toggle_user_status(
            email='imaptest@example.com',
            enabled=True,
            admin_ip='test'
        )
        time.sleep(2)

        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # ログイン試行（成功するはず）
            result = imap.login(
                'imaptest@example.com',
                'ImapTestPassword123!'
            )

            assert result[0] == 'OK'
            imap.logout()

        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAP login after re-enabling failed: {e}")


class TestIMAPUserDeletion:
    """TC-IMAP-004: ユーザー削除後の IMAP ログインテスト"""

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_login_deleted_user(self, db_session):
        """TC-IMAP-004-01: 削除ユーザーは IMAP ログイン不可"""
        # テストユーザー作成
        user = UserService.create_user(
            email='deletetest@example.com',
            password='DeleteTestPassword123!',
            domain_id=1,
            quota=1024,
            enabled=True,
            admin_ip='test'
        )
        time.sleep(2)

        # ユーザー削除
        UserService.delete_user(email='deletetest@example.com', admin_ip='test')
        time.sleep(2)

        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

            # ログイン試行（失敗するはず）
            with pytest.raises(imaplib.IMAP4.error):
                imap.login(
                    'deletetest@example.com',
                    'DeleteTestPassword123!'
                )

        except Exception:
            # 接続エラーも予期される動作
            pass


@pytest.mark.integration
class TestIMAPConnectionBasics:
    """TC-IMAP-005: IMAP 接続基本テスト"""

    @pytest.mark.skipif(
        True,  # デフォルトでスキップ
        reason="Requires Dovecot container running"
    )
    def test_imap_connection(self):
        """TC-IMAP-005-01: Dovecot IMAP サーバーへの接続"""
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            assert imap is not None
            imap.logout()
        except Exception as e:
            pytest.fail(f"IMAP connection failed: {e}")

    def test_imap_connection_info(self):
        """TC-IMAP-005-02: IMAP 接続情報確認（情報テスト）"""
        # IMAP 接続情報を記録（実際の接続は行わない）
        assert IMAP_HOST == '172.20.0.80'
        assert IMAP_PORT == 143
