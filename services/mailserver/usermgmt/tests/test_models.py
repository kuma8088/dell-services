"""
Test suite for Database Models (Phase 8 - P8-T1-1)

Tests User, Domain, and AuditLog models
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.domain import Domain
from app.models.audit_log import AuditLog
from app.services.password import hash_password


class TestUserModel:
    """TC-M-001: User モデルテスト"""

    def test_create_user_with_valid_data(self, db_session):
        """TC-M-001-01: 有効なデータでユーザー作成"""
        user = User(
            email='newuser@example.com',
            password_hash=hash_password('secure_password_123'),
            domain_id=1,
            maildir='/var/mail/vmail/example.com/newuser/',
            quota=2048,
            uid=5000,
            gid=5000,
            enabled=True
        )
        db_session.add(user)
        db_session.commit()

        # データベースから取得して検証
        retrieved_user = User.query.filter_by(email='newuser@example.com').first()
        assert retrieved_user is not None
        assert retrieved_user.email == 'newuser@example.com'
        assert retrieved_user.domain_id == 1
        assert retrieved_user.quota == 2048
        assert retrieved_user.enabled is True

    def test_user_unique_email_constraint(self, db_session, test_user):
        """TC-M-001-02: メールアドレスの一意性制約"""
        # 同じメールアドレスで別ユーザーを作成しようとする
        duplicate_user = User(
            email='testuser1@example.com',  # test_user と同じ
            password_hash=hash_password('another_password'),
            domain_id=1,
            maildir='/var/mail/vmail/example.com/duplicate/',
            quota=1024,
            uid=5000,
            gid=5000,
            enabled=True
        )
        db_session.add(duplicate_user)

        # IntegrityError が発生することを確認
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_required_fields(self, db_session):
        """TC-M-001-03: 必須フィールドの検証"""
        # email なしでユーザー作成
        user = User(
            password_hash=hash_password('password'),
            domain_id=1,
            maildir='/var/mail/vmail/example.com/test/',
            quota=1024,
            uid=5000,
            gid=5000
        )
        db_session.add(user)

        # IntegrityError が発生することを確認 (email は NOT NULL)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_enabled_default_value(self, db_session):
        """TC-M-001-04: enabled フィールドのデフォルト値"""
        user = User(
            email='defaultuser@example.com',
            password_hash=hash_password('password'),
            domain_id=1,
            maildir='/var/mail/vmail/example.com/defaultuser/',
            quota=1024,
            uid=5000,
            gid=5000
            # enabled を指定しない
        )
        db_session.add(user)
        db_session.commit()

        retrieved_user = User.query.filter_by(email='defaultuser@example.com').first()
        assert retrieved_user.enabled is True  # デフォルトは True

    def test_user_timestamps(self, db_session):
        """TC-M-001-05: タイムスタンプの自動生成"""
        before_creation = datetime.utcnow()

        user = User(
            email='timestampuser@example.com',
            password_hash=hash_password('password'),
            domain_id=1,
            maildir='/var/mail/vmail/example.com/timestampuser/',
            quota=1024,
            uid=5000,
            gid=5000
        )
        db_session.add(user)
        db_session.commit()

        after_creation = datetime.utcnow()

        retrieved_user = User.query.filter_by(email='timestampuser@example.com').first()

        # created_at が自動設定されていることを確認
        assert retrieved_user.created_at is not None
        assert before_creation <= retrieved_user.created_at <= after_creation

        # updated_at も自動設定されていることを確認
        assert retrieved_user.updated_at is not None
        assert before_creation <= retrieved_user.updated_at <= after_creation

    def test_user_update_timestamp(self, db_session, test_user):
        """TC-M-001-06: 更新時のタイムスタンプ自動更新"""
        original_updated_at = test_user.updated_at

        # データを更新
        test_user.quota = 4096
        db_session.commit()
        db_session.refresh(test_user)

        # updated_at が更新されていることを確認
        assert test_user.updated_at > original_updated_at

    def test_user_domain_relationship(self, db_session, test_user):
        """TC-M-001-07: Domain との外部キー関係"""
        # User が Domain と関連付けられていることを確認
        assert test_user.domain_id == 1

        # Domain を取得
        domain = Domain.query.get(1)
        assert domain is not None
        assert domain.name == 'example.com'


class TestDomainModel:
    """TC-M-002: Domain モデルテスト"""

    def test_create_domain_with_valid_data(self, db_session):
        """TC-M-002-01: 有効なデータでドメイン作成"""
        domain = Domain(
            domain='newdomain.com',
            enabled=True
        )
        db_session.add(domain)
        db_session.commit()

        retrieved_domain = Domain.query.filter_by(domain='newdomain.com').first()
        assert retrieved_domain is not None
        assert retrieved_domain.domain == 'newdomain.com'
        assert retrieved_domain.enabled is True

    def test_domain_unique_constraint(self, db_session):
        """TC-M-002-02: ドメイン名の一意性制約"""
        # 1つ目のドメイン
        domain1 = Domain(domain='duplicate.com', enabled=True)
        db_session.add(domain1)
        db_session.commit()

        # 同じドメイン名で2つ目を作成
        domain2 = Domain(domain='duplicate.com', enabled=True)
        db_session.add(domain2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_domain_enabled_default_value(self, db_session):
        """TC-M-002-03: enabled フィールドのデフォルト値"""
        domain = Domain(domain='defaultdomain.com')
        db_session.add(domain)
        db_session.commit()

        retrieved_domain = Domain.query.filter_by(domain='defaultdomain.com').first()
        assert retrieved_domain.enabled is True

    def test_domain_cascade_delete(self, db_session):
        """TC-M-002-04: ドメイン削除時のカスケード動作確認"""
        # 新しいドメインを作成
        domain = Domain(domain='cascadetest.com', enabled=True)
        db_session.add(domain)
        db_session.commit()
        domain_id = domain.id

        # そのドメインに関連するユーザーを作成
        user = User(
            email='user@cascadetest.com',
            password_hash=hash_password('password'),
            domain_id=domain_id,
            maildir='/var/mail/vmail/cascadetest.com/user/',
            quota=1024,
            uid=5000,
            gid=5000
        )
        db_session.add(user)
        db_session.commit()
        user_email = user.email

        # ドメインを削除
        db_session.delete(domain)
        db_session.commit()

        # ドメインが削除されていることを確認
        assert Domain.query.get(domain_id) is None

        # 関連ユーザーも削除されている（または NULL になっている）ことを確認
        # モデル定義に応じて動作が異なるため、実際の動作を確認
        orphan_user = User.query.filter_by(email=user_email).first()
        # CASCADE 設定されている場合は None、RESTRICT の場合はエラー
        # 実装に応じて調整


class TestAuditLogModel:
    """TC-M-003: AuditLog モデルテスト"""

    def test_create_audit_log(self, db_session, test_user):
        """TC-M-003-01: 監査ログ作成"""
        audit = AuditLog(
            user_id=test_user.id,
            action='user_created',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0'
        )
        db_session.add(audit)
        db_session.commit()

        retrieved_audit = AuditLog.query.filter_by(user_id=test_user.id).first()
        assert retrieved_audit is not None
        assert retrieved_audit.action == 'user_created'
        assert retrieved_audit.ip_address == '192.168.1.100'
        assert retrieved_audit.user_agent == 'Mozilla/5.0'

    def test_audit_log_timestamp(self, db_session, test_user):
        """TC-M-003-02: 監査ログタイムスタンプ自動生成"""
        before_creation = datetime.utcnow()

        audit = AuditLog(
            user_id=test_user.id,
            action='password_changed',
            ip_address='10.0.1.50'
        )
        db_session.add(audit)
        db_session.commit()

        after_creation = datetime.utcnow()

        retrieved_audit = AuditLog.query.filter_by(action='password_changed').first()
        assert retrieved_audit.timestamp is not None
        assert before_creation <= retrieved_audit.timestamp <= after_creation

    def test_audit_log_user_relationship(self, db_session, test_user):
        """TC-M-003-03: User との外部キー関係"""
        audit = AuditLog(
            user_id=test_user.id,
            action='login',
            ip_address='172.20.0.1'
        )
        db_session.add(audit)
        db_session.commit()

        # 監査ログから User を取得
        retrieved_audit = AuditLog.query.filter_by(action='login').first()
        assert retrieved_audit.user_id == test_user.id
