"""Database Pydantic schemas."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, validator


# Allowed charsets and collations (whitelist)
ALLOWED_CHARSETS = ["utf8", "utf8mb4", "latin1", "ascii"]
ALLOWED_COLLATIONS = [
    "utf8_general_ci",
    "utf8_unicode_ci",
    "utf8mb4_general_ci",
    "utf8mb4_unicode_ci",
    "latin1_swedish_ci",
    "ascii_general_ci",
]


class DatabaseBase(BaseModel):
    """Base database schema."""

    database_name: str = Field(..., min_length=1, max_length=64, description="Database name (alphanumeric, underscore only)")
    charset: str = Field("utf8mb4", description="Database character set")
    collation: str = Field("utf8mb4_unicode_ci", description="Database collation")

    @validator("database_name")
    def validate_database_name(cls, v):
        """Validate database name to prevent SQL injection.

        Only allows alphanumeric characters and underscores.
        Must start with a letter or underscore.
        """
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Database name must start with letter/underscore and contain only alphanumeric characters and underscores"
            )
        return v

    @validator("charset")
    def validate_charset(cls, v):
        """Validate charset against whitelist."""
        if v not in ALLOWED_CHARSETS:
            raise ValueError(f"Charset must be one of: {', '.join(ALLOWED_CHARSETS)}")
        return v

    @validator("collation")
    def validate_collation(cls, v):
        """Validate collation against whitelist."""
        if v not in ALLOWED_COLLATIONS:
            raise ValueError(f"Collation must be one of: {', '.join(ALLOWED_COLLATIONS)}")
        return v


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

    username: str = Field(..., min_length=1, max_length=32, description="Database username (alphanumeric, underscore only)")
    host: str = Field("%", description="Allowed host (% for any, localhost, IP, etc.)")

    @validator("username")
    def validate_username(cls, v):
        """Validate username to prevent SQL injection.

        Only allows alphanumeric characters and underscores.
        Must start with a letter or underscore.
        """
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Username must start with letter/underscore and contain only alphanumeric characters and underscores"
            )
        return v

    @validator("host")
    def validate_host(cls, v):
        """Validate host to prevent SQL injection.

        Allows: %, localhost, IP addresses, hostnames with dots/hyphens
        """
        if v == "%" or v == "localhost":
            return v

        # Validate IP address (basic)
        if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", v):
            return v

        # Validate hostname (basic)
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$", v):
            return v

        raise ValueError("Invalid host format. Use %, localhost, IP address, or valid hostname")



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

    @validator("username")
    def validate_username(cls, v):
        """Validate username."""
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Invalid username format")
        return v

    @validator("database_name")
    def validate_database_name(cls, v):
        """Validate database name."""
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Invalid database name format")
        return v

    @validator("privileges")
    def validate_privileges(cls, v):
        """Validate privileges against whitelist."""
        allowed_privileges = [
            "ALL",
            "ALL PRIVILEGES",
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "DROP",
            "INDEX",
            "ALTER",
            "CREATE TEMPORARY TABLES",
            "LOCK TABLES",
            "EXECUTE",
            "CREATE VIEW",
            "SHOW VIEW",
            "CREATE ROUTINE",
            "ALTER ROUTINE",
            "EVENT",
            "TRIGGER",
        ]

        for privilege in v:
            if privilege.upper() not in allowed_privileges:
                raise ValueError(f"Invalid privilege: {privilege}. Must be one of: {', '.join(allowed_privileges)}")

        return [p.upper() for p in v]


class DatabaseQueryExecute(BaseModel):
    """Schema for executing database queries.

    WARNING: Direct SQL execution is dangerous. This should only be accessible
    to superadmin users and should be used with extreme caution.
    """

    query: str = Field(..., min_length=1, description="SQL query to execute")
    target_system: Literal["blog", "mailserver"] = Field(..., description="Target system")
    database_name: str = Field(..., description="Database to query")

    @validator("database_name")
    def validate_database_name(cls, v):
        """Validate database name."""
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Invalid database name format")
        return v


class DatabaseQueryResult(BaseModel):
    """Schema for database query results."""

    success: bool
    rows_affected: Optional[int] = None
    results: Optional[list[dict]] = None
    error: Optional[str] = None
