"""Admin user database model."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class AdminUser(Base):
    """Admin user model.

    Represents administrators who can manage the unified portal.
    Passwords are stored as bcrypt hashes.
    """

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="Admin username")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="Admin email address")
    password_hash = Column(String(255), nullable=False, comment="Bcrypt password hash")
    full_name = Column(String(100), nullable=True, comment="Admin full name")
    is_active = Column(Boolean, default=True, nullable=False, comment="Account active status")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="Superuser privileges")
    last_login = Column(DateTime, nullable=True, comment="Last login timestamp")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<AdminUser(id={self.id}, username='{self.username}', email='{self.email}', is_active={self.is_active})>"
