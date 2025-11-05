"""
Database configuration and initialization for usermgmt application
"""
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()


def init_db(app):
    """
    Initialize database with Flask app

    Args:
        app: Flask application instance
    """
    db.init_app(app)

    with app.app_context():
        # Import models to register them
        from app.models import User

        # Create tables if they don't exist
        # Note: In production, use migrations (Alembic)
        db.create_all()
