"""Database configuration and initialization utilities."""
from __future__ import annotations

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()


def init_db(app: Flask) -> None:
    """Initialize database bindings for the provided Flask application."""
    db.init_app(app)

    with app.app_context():
        # Import models to register them
        from app.models import User

        # Create tables if they don't exist
        # Note: In production, use migrations (Alembic)
        db.create_all()
