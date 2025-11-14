"""
Pydantic Schemas

This package contains all Pydantic schemas for request/response validation.
"""
from app.schemas.mailserver import (
    UserCreateRequest,
    UserUpdateRequest,
    PasswordChangeRequest,
    UserResponse,
    UserListResponse,
    DomainCreateRequest,
    DomainUpdateRequest,
    DomainResponse,
    DomainListResponse,
    AuditLogResponse,
    AuditLogListResponse,
)

__all__ = [
    # User schemas
    "UserCreateRequest",
    "UserUpdateRequest",
    "PasswordChangeRequest",
    "UserResponse",
    "UserListResponse",
    # Domain schemas
    "DomainCreateRequest",
    "DomainUpdateRequest",
    "DomainResponse",
    "DomainListResponse",
    # Audit log schemas
    "AuditLogResponse",
    "AuditLogListResponse",
]
