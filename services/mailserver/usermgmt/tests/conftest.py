"""
Pytest configuration and fixtures for usermgmt tests
"""
import os
import sys
import pytest
from datetime import timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Try alternative path
    env_path_alt = '/opt/onprem-infra-system/project-root-infra/services/mailserver/.env'
    if os.path.exists(env_path_alt):
        load_dotenv(env_path_alt)

from app import create_app, db
from app.models.user import User
from app.models.domain import Domain


@pytest.fixture(scope='session')
def app():
    """Create and configure a test Flask application instance"""
    # Set testing environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DB_NAME'] = 'mailserver_usermgmt_test'

    # Get actual database password from environment
    # Force load from env file if not already set
    db_password = os.getenv('USERMGMT_DB_PASSWORD')
    if not db_password:
        db_password = os.getenv('DB_PASSWORD', '')

    # Set DB_PASSWORD environment variable for create_app to use
    if db_password:
        os.environ['DB_PASSWORD'] = db_password

    # Create app with testing config
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SQLALCHEMY_DATABASE_URI': f'mysql+pymysql://usermgmt:{db_password}@172.20.0.60:3306/mailserver_usermgmt_test?charset=utf8mb4',
        'SECRET_KEY': 'test-secret-key',
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_SAMESITE': 'Strict',
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=1)
    })

    # Create application context
    with app.app_context():
        # Create tables
        db.create_all()

        # Create test domain for foreign key constraints
        test_domain = Domain(
            name='example.com',
            description='Test domain for unit tests'
        )
        db.session.add(test_domain)
        db.session.commit()

        yield app

        # Cleanup
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app"""
    return app.test_client()


@pytest.fixture(scope='function', autouse=True)
def db_session(app):
    """Create a new database session for a test"""
    with app.app_context():
        yield db.session
        # Rollback any changes made during the test
        db.session.rollback()
        # Remove all data except the test domain
        User.query.delete()
        db.session.commit()


@pytest.fixture(scope='function')
def test_user(db_session):
    """Create a test user in the database"""
    from app.services.password import hash_password

    user = User(
        email='testuser1@example.com',
        password_hash=hash_password('test_password_123'),
        domain_id=1,
        maildir='/var/mail/vmail/example.com/testuser1/',
        quota=1024,
        uid=5000,
        gid=5000,
        enabled=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)  # Get the auto-generated ID
    return user


@pytest.fixture(scope='function')
def disabled_user(db_session):
    """Create a disabled test user in the database"""
    from app.services.password import hash_password

    user = User(
        email='testuser2@example.com',
        password_hash=hash_password('test_password_456'),
        domain_id=1,
        maildir='/var/mail/vmail/example.com/testuser2/',
        quota=1024,
        uid=5000,
        gid=5000,
        enabled=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
