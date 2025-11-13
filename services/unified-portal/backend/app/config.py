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

    # Database
    database_url: str = "mysql+pymysql://usermgmt:password@172.20.0.60:3306/unified_portal"

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

    # Logging
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
