"""Database Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DatabaseBase(BaseModel):
    """Base database schema."""

    database_name: str = Field(..., min_length=1, max_length=100, description="Database name")
    charset: str = Field("utf8mb4", description="Database character set")
    collation: str = Field("utf8mb4_unicode_ci", description="Database collation")


class DatabaseCreate(DatabaseBase):
    """Schema for creating a database."""

    target_system: Literal["blog", "mailserver"] = Field(..., description="Target system (blog or mailserver)")
    create_user: bool = Field(True, description="Create dedicated database user")
    username: Optional[str] = Field(None, min_length=1, max_length=100, description="Database username (defaults to database_name)")
    password: Optional[str] = Field(None, min_length=8, description="Database password (auto-generated if not provided)")


class DatabaseResponse(DatabaseBase):
    """Schema for database response."""

    size_mb: float = Field(0.0, description="Database size in MB")
    table_count: int = Field(0, description="Number of tables")
    created_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class DatabaseUserBase(BaseModel):
    """Base database user schema."""

    username: str = Field(..., min_length=1, max_length=100, description="Database username")
    host: str = Field("%", description="Allowed host (% for any, localhost, IP, etc.)")


class DatabaseUserCreate(DatabaseUserBase):
    """Schema for creating a database user."""

    password: str = Field(..., min_length=8, description="Database password")
    target_system: Literal["blog", "mailserver"] = Field(..., description="Target system")


class DatabaseUserUpdate(BaseModel):
    """Schema for updating a database user."""

    password: Optional[str] = Field(None, min_length=8, description="New password")


class DatabaseUserResponse(DatabaseUserBase):
    """Schema for database user response."""

    privileges: list[str] = Field(default_factory=list, description="List of granted privileges")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DatabasePrivilegeGrant(BaseModel):
    """Schema for granting database privileges."""

    username: str = Field(..., description="Database username")
    database_name: str = Field(..., description="Database name")
    privileges: list[str] = Field(..., description="Privileges to grant (e.g., ['SELECT', 'INSERT', 'UPDATE', 'DELETE'])")
    target_system: Literal["blog", "mailserver"] = Field(..., description="Target system")


class DatabaseQueryExecute(BaseModel):
    """Schema for executing database queries."""

    query: str = Field(..., min_length=1, description="SQL query to execute")
    target_system: Literal["blog", "mailserver"] = Field(..., description="Target system")
    database_name: str = Field(..., description="Database to query")


class DatabaseQueryResult(BaseModel):
    """Schema for database query results."""

    success: bool
    rows_affected: Optional[int] = None
    results: Optional[list[dict]] = None
    error: Optional[str] = None
