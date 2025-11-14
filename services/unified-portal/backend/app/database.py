"""Database connection and session management."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# ============================================================================
# Unified Portal Database (Main)
# ============================================================================

# Create SQLAlchemy engine for main database
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)

# Create session factory for main database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base (shared by all models)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get main database session.

    Yields:
        Session: SQLAlchemy database session for unified_portal database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Mailserver User Management Database
# ============================================================================

# Create SQLAlchemy engine for mailserver database
mailserver_engine = create_engine(
    settings.mailserver_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)

# Create session factory for mailserver database
MailServerSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=mailserver_engine
)


def get_mailserver_db() -> Generator[Session, None, None]:
    """Get mailserver database session.

    Yields:
        Session: SQLAlchemy database session for mailserver_usermgmt database.
    """
    db = MailServerSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Blog System Database (MariaDB for WordPress databases)
# ============================================================================

# Create SQLAlchemy engine for blog database
# This connects to the MariaDB instance that hosts WordPress databases
blog_engine = create_engine(
    settings.blog_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)

# Create session factory for blog database
BlogSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=blog_engine)


def get_blog_db() -> Generator[Session, None, None]:
    """Get blog database session.

    Yields:
        Session: SQLAlchemy database session for blog MariaDB instance.

    Note:
        This connection is used for managing WordPress databases (CREATE/DROP DATABASE,
        CREATE/DROP USER, GRANT privileges, etc.), not for querying WordPress tables.
    """
    db = BlogSessionLocal()
    try:
        yield db
    finally:
        db.close()
