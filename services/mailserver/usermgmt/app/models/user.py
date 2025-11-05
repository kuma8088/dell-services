"""
User model for mailserver usermgmt application

Implements Flask-Login UserMixin for authentication support
"""
from flask_login import UserMixin
from app.database import db
from datetime import datetime


class User(UserMixin, db.Model):
    """
    User model representing email users in the mailserver

    Inherits from Flask-Login's UserMixin to provide:
    - is_authenticated
    - is_active (based on enabled field)
    - is_anonymous
    - get_id()
    """
    __tablename__ = 'users'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # User identification
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Domain relationship
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)

    # Authentication
    password_hash = db.Column(db.String(255), nullable=False)

    # Mail settings
    maildir = db.Column(db.String(500), nullable=False)
    quota = db.Column(db.Integer, default=1024)  # MB
    uid = db.Column(db.Integer, default=5000)
    gid = db.Column(db.Integer, default=5000)

    # Status
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        """String representation of User"""
        return f'<User {self.email}>'

    @property
    def is_active(self):
        """
        Override Flask-Login's is_active to use enabled field

        Returns:
            bool: True if user is enabled, False otherwise
        """
        return self.enabled

    def get_id(self):
        """
        Override Flask-Login's get_id to return user ID as string

        Required by Flask-Login for session management

        Returns:
            str: User ID as string
        """
        return str(self.id)
