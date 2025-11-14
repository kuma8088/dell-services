"""
Mail User Model

SQLAlchemy ORM model for the existing 'users' table in mailserver_usermgmt database.
This model maps to the existing Flask usermgmt table structure.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MailUser(Base):
    """
    Mail User Model

    Maps to the existing 'users' table in mailserver_usermgmt database.
    This table stores mail user credentials and configuration.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    password_hash = Column(String(255), nullable=False, comment="SHA512-CRYPT hash for Dovecot authentication")
    maildir = Column(String(500), nullable=False, comment="Mail directory path (e.g., /var/mail/vmail/example.com/user/)")
    quota = Column(Integer, default=1024, comment="Quota in MB")
    uid = Column(Integer, default=5000, comment="Unix UID for mail storage")
    gid = Column(Integer, default=5000, comment="Unix GID for mail storage")
    enabled = Column(Boolean, default=True, nullable=False, comment="Whether account is active")
    is_admin = Column(Boolean, default=False, nullable=False, comment="Whether user is domain admin")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    domain = relationship("MailDomain", back_populates="users")

    def __repr__(self):
        return f"<MailUser(id={self.id}, email='{self.email}', enabled={self.enabled})>"
