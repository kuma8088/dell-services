"""
Flask application factory and configuration

Implements Flask-Login integration with secure session management
"""
import os
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask-Login
login_manager = LoginManager()

# Initialize database
from app.database import db


def create_app(config=None):
    """
    Application factory for creating Flask app instances

    Args:
        config (dict, optional): Configuration overrides

    Returns:
        Flask: Configured Flask application instance
    """
    import os
    # Get the base directory (project root)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(base_dir, 'templates')

    app = Flask(__name__, template_folder=template_dir)

    # Load configuration
    configure_app(app, config)

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    return app


def configure_app(app, config=None):
    """
    Configure Flask application

    Args:
        app: Flask application instance
        config (dict, optional): Configuration overrides
    """
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database configuration
    db_host = os.getenv('DB_HOST', '172.20.0.60')
    db_port = os.getenv('DB_PORT', '3306')
    db_name = os.getenv('DB_NAME', 'mailserver_usermgmt')
    db_user = os.getenv('DB_USER', 'usermgmt')
    db_password = os.getenv('DB_PASSWORD', '')

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False  # Set to True for SQL debugging

    # Session configuration (Security)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

    # WTF/CSRF configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit on CSRF tokens

    # Apply configuration overrides
    if config:
        app.config.update(config)


def init_extensions(app):
    """
    Initialize Flask extensions

    Args:
        app: Flask application instance
    """
    # Initialize database
    db.init_app(app)

    # Initialize Flask-Login
    init_login_manager(app)

    # Add context processor for current year
    @app.context_processor
    def inject_now():
        """Inject current datetime into all templates"""
        from datetime import datetime
        return {'now': datetime.now()}


def init_login_manager(app):
    """
    Initialize Flask-Login LoginManager

    Args:
        app: Flask application instance
    """
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        """
        Load user by ID for Flask-Login

        Args:
            user_id (str): User ID as string

        Returns:
            User: User instance or None if not found
        """
        from app.models.user import User

        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None


def register_blueprints(app):
    """
    Register Flask blueprints

    Args:
        app: Flask application instance
    """
    # Import and register auth blueprint
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Import and register users blueprint
    from app.routes.users import bp as users_bp
    app.register_blueprint(users_bp)

    # Import and register domains blueprint
    from app.routes.domains import bp as domains_bp
    app.register_blueprint(domains_bp)

    # Register health check route (for Docker healthcheck)
    from flask import render_template, jsonify
    from flask_login import login_required

    @app.route('/health')
    def health():
        """Health check endpoint for Docker healthcheck and monitoring"""
        return jsonify({
            'status': 'healthy',
            'service': 'mailserver-usermgmt',
            'version': '0.5.0'  # MVP完了 (Phase 5)
        }), 200

    # Register dashboard route (temporary, will move to separate blueprint later)
    @app.route('/')
    @login_required
    def dashboard():
        """Dashboard route (protected)"""
        return render_template('dashboard.html')


def load_user(user_id):
    """
    Load user by ID for Flask-Login (exposed for testing)

    Args:
        user_id (str): User ID as string

    Returns:
        User: User instance or None if not found
    """
    from app.models.user import User

    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None
