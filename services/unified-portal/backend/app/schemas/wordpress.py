"""WordPress Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class WordPressSiteBase(BaseModel):
    """Base WordPress site schema."""

    site_name: str = Field(..., min_length=1, max_length=100, description="Site identifier (e.g., kuma8088-main)")
    domain: str = Field(..., min_length=1, max_length=255, description="Site domain (e.g., kuma8088.com)")
    database_name: str = Field(..., min_length=1, max_length=100, description="MariaDB database name")
    php_version: str = Field(..., pattern=r"^\d+\.\d+$", description="PHP version (e.g., 7.4, 8.0, 8.1, 8.2)")


class WordPressSiteCreate(WordPressSiteBase):
    """Schema for creating a WordPress site."""

    admin_user: str = Field(..., min_length=1, description="WordPress admin username")
    admin_password: str = Field(..., min_length=8, description="WordPress admin password")
    admin_email: str = Field(..., description="WordPress admin email")
    title: Optional[str] = Field(None, description="Site title (defaults to domain)")

    @validator("php_version")
    def validate_php_version(cls, v):
        """Validate PHP version format."""
        valid_versions = ["7.4", "8.0", "8.1", "8.2"]
        if v not in valid_versions:
            raise ValueError(f"PHP version must be one of: {', '.join(valid_versions)}")
        return v


class WordPressSiteUpdate(BaseModel):
    """Schema for updating a WordPress site."""

    php_version: Optional[str] = Field(None, pattern=r"^\d+\.\d+$", description="PHP version")
    enabled: Optional[bool] = Field(None, description="Site enabled status")

    @validator("php_version")
    def validate_php_version(cls, v):
        """Validate PHP version format."""
        if v is not None:
            valid_versions = ["7.4", "8.0", "8.1", "8.2"]
            if v not in valid_versions:
                raise ValueError(f"PHP version must be one of: {', '.join(valid_versions)}")
        return v


class WordPressSiteResponse(WordPressSiteBase):
    """Schema for WordPress site response."""

    id: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class WordPressSiteStats(BaseModel):
    """Schema for WordPress site statistics."""

    post_count: int = Field(0, description="Number of posts")
    page_count: int = Field(0, description="Number of pages")
    plugin_count: int = Field(0, description="Number of plugins")
    theme_count: int = Field(0, description="Number of themes")
    user_count: int = Field(0, description="Number of users")
    db_size_mb: float = Field(0.0, description="Database size in MB")


class WordPressSiteWithStats(WordPressSiteResponse):
    """Schema for WordPress site with statistics."""

    stats: Optional[WordPressSiteStats] = None


class WordPressCacheOperation(BaseModel):
    """Schema for WordPress cache operations."""

    cache_type: str = Field(..., pattern=r"^(object|transient|all)$", description="Cache type to clear")


class WordPressPluginOperation(BaseModel):
    """Schema for WordPress plugin operations."""

    plugin_slug: str = Field(..., min_length=1, description="Plugin slug")
    action: str = Field(..., pattern=r"^(activate|deactivate|update|install|delete)$", description="Plugin action")


class WordPressThemeOperation(BaseModel):
    """Schema for WordPress theme operations."""

    theme_slug: str = Field(..., min_length=1, description="Theme slug")
    action: str = Field(..., pattern=r"^(activate|update|install|delete)$", description="Theme action")
