"""
Mailserver Pydantic Schemas

Request and response schemas for mailserver API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ============================================================================
# User Schemas
# ============================================================================

class UserCreateRequest(BaseModel):
    """Request schema for creating a new mail user"""
    email: EmailStr
    password: str = Field(min_length=8, description="User password (minimum 8 characters)")
    domain_id: int = Field(gt=0, description="Domain ID")
    quota: int = Field(default=1024, ge=100, le=10000, description="Quota in MB")
    enabled: bool = True


class UserUpdateRequest(BaseModel):
    """Request schema for updating a mail user"""
    quota: Optional[int] = Field(None, ge=100, le=10000, description="Quota in MB")
    enabled: Optional[bool] = None


class PasswordChangeRequest(BaseModel):
    """Request schema for changing user password"""
    new_password: str = Field(min_length=8, description="New password (minimum 8 characters)")


class UserResponse(BaseModel):
    """Response schema for mail user"""
    id: int
    email: str
    domain_id: int
    domain_name: str  # Joined from domain table
    quota: int
    enabled: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy ORM mode (Pydantic v2)


class UserListResponse(BaseModel):
    """Response schema for user list with pagination"""
    users: list[UserResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# Domain Schemas
# ============================================================================

class DomainCreateRequest(BaseModel):
    """Request schema for creating a new domain"""
    name: str = Field(min_length=3, max_length=255, description="Domain name (e.g., example.com)")
    description: Optional[str] = Field(None, max_length=500)
    default_quota: int = Field(default=1024, ge=100, le=10000, description="Default quota for new users in MB")
    enabled: bool = True


class DomainUpdateRequest(BaseModel):
    """Request schema for updating a domain"""
    description: Optional[str] = Field(None, max_length=500)
    default_quota: Optional[int] = Field(None, ge=100, le=10000)
    enabled: Optional[bool] = None


class DomainResponse(BaseModel):
    """Response schema for mail domain"""
    id: int
    name: str
    description: Optional[str]
    default_quota: int
    enabled: bool
    user_count: int  # Calculated field
    total_quota_used: int  # Calculated field
    created_at: datetime

    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """Response schema for domain list"""
    domains: list[DomainResponse]
    total: int


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Response schema for audit log entry"""
    id: int
    action: str
    user_email: str
    admin_ip: str
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response schema for audit log list with pagination"""
    logs: list[AuditLogResponse]
    total: int
    skip: int
    limit: int
