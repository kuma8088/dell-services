"""WordPress site database model."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class WordPressSite(Base):
    """WordPress site model.

    Represents a WordPress installation managed by the unified portal.
    Each site has its own database, domain, and PHP version configuration.
    """

    __tablename__ = "wordpress_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(100), unique=True, nullable=False, index=True, comment="Site identifier (e.g., kuma8088-main)")
    domain = Column(String(255), unique=True, nullable=False, index=True, comment="Site domain (e.g., kuma8088.com)")
    database_name = Column(String(100), nullable=False, comment="MariaDB database name")
    php_version = Column(String(10), nullable=False, index=True, comment="PHP version (e.g., 7.4, 8.0, 8.1, 8.2)")
    enabled = Column(Boolean, default=True, nullable=False, comment="Site enabled status")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<WordPressSite(id={self.id}, site_name='{self.site_name}', domain='{self.domain}', php_version='{self.php_version}')>"
