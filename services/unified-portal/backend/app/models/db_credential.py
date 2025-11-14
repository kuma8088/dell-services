"""Database credential database model."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class DBCredential(Base):
    """Database credential model.

    Stores encrypted database credentials for WordPress and other systems.
    Passwords are encrypted using Fernet symmetric encryption.
    """

    __tablename__ = "db_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    database_name = Column(String(100), unique=True, nullable=False, index=True, comment="Database name")
    username = Column(String(100), nullable=False, comment="Database username")
    password_encrypted = Column(String(500), nullable=False, comment="Fernet-encrypted password")
    host = Column(String(255), nullable=False, comment="Database host (e.g., 172.20.0.30)")
    port = Column(Integer, nullable=False, comment="Database port (e.g., 3306)")
    target_system = Column(String(50), nullable=False, index=True, comment="Target system (blog, mailserver)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<DBCredential(id={self.id}, database_name='{self.database_name}', username='{self.username}', target_system='{self.target_system}')>"
