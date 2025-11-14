"""
Mail Domain Model

SQLAlchemy ORM model for the existing 'domains' table in mailserver_usermgmt database.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MailDomain(Base):
    """
    Mail Domain Model

    Maps to the existing 'domains' table in mailserver_usermgmt database.
    This table stores email domains managed by the mail server.
    """
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True, comment="Domain name (e.g., example.com)")
    description = Column(String(500), comment="Optional description")
    default_quota = Column(Integer, default=1024, comment="Default quota for new users in MB")
    enabled = Column(Boolean, default=True, nullable=False, comment="Whether domain is active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("MailUser", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MailDomain(id={self.id}, name='{self.name}', enabled={self.enabled})>"
