"""
Domain model for mailserver usermgmt application
"""
from app.database import db
from datetime import datetime


class Domain(db.Model):
    """
    Domain model representing email domains

    Each domain can have multiple users
    """
    __tablename__ = 'domains'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Domain name (matches 'name' column in database)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Domain metadata
    description = db.Column(db.String(500), nullable=True)
    default_quota = db.Column(db.Integer, default=1024, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    users = db.relationship('User', backref='domain', lazy='dynamic')

    def user_count(self):
        """
        Get count of users in this domain

        Returns:
            int: Number of users associated with this domain

        Examples:
            >>> domain = Domain.query.first()
            >>> domain.user_count()
            5
        """
        return self.users.count()

    def __repr__(self):
        """String representation of Domain"""
        return f'<Domain {self.name}>'
