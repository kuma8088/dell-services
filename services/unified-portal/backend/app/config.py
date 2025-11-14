"""Configuration management for unified portal backend."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Unified Portal Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database - Unified Portal (main database)
    database_url: str = "mysql+pymysql://usermgmt:password@172.20.0.60:3306/unified_portal"

    # Database - Mailserver User Management
    mailserver_database_url: str = "mysql+pymysql://usermgmt:password@172.20.0.60:3306/mailserver_usermgmt"
    mailserver_db_host: str = "172.20.0.60"
    mailserver_db_port: int = 3306

    # Database - Blog System (MariaDB for WordPress)
    blog_database_url: str = "mysql+pymysql://root:password@blog-mariadb:3306/mysql"
    blog_db_host: str = "blog-mariadb"
    blog_db_port: int = 3306
    blog_db_user: str = "root"
    blog_db_password: str = "password"

    # Encryption (Fernet symmetric encryption for database credentials)
    encryption_key: str = "change-this-to-a-valid-fernet-key-in-production"

    # JWT
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Admin Authentication
    admin_username: str = "admin"
    admin_password: str = "change-this-password-in-production"

    # CORS
    cors_origins: List[str] = [
        "http://172.20.0.91:5173",
        "http://localhost:5173",
        "http://172.20.0.92:80",
    ]

    # Docker
    docker_host: str = "unix:///var/run/docker.sock"

    # Cloudflare API
    cloudflare_api_token: str = ""

    # SMTP Email Settings (for password reset, welcome emails, etc.)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"

    # Frontend URL (for password reset links, etc.)
    frontend_url: str = "http://localhost:5173"

    # Logging
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
