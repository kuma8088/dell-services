"""
Mailserver API Router

REST API endpoints for mail user and domain management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_mailserver_db
from app.services.mail_user_service import MailUserService
from app.services.mail_domain_service import MailDomainService
from app.services.audit_service import AuditService
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


router = APIRouter(prefix="/api/mailserver", tags=["mailserver"])


def get_admin_ip(request: Request) -> str:
    """
    Get admin IP address from request

    Args:
        request: FastAPI request object

    Returns:
        str: Admin IP address
    """
    # Try to get real IP from X-Forwarded-For header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


# ============================================================================
# User Endpoints
# ============================================================================

@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 100,
    domain_id: Optional[int] = None,
    enabled_only: bool = False,
    db: Session = Depends(get_mailserver_db)
):
    """
    List mail users with pagination and filtering

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        domain_id: Filter by domain ID (optional)
        enabled_only: Only return enabled users
        db: Database session

    Returns:
        UserListResponse: List of users with pagination info
    """
    service = MailUserService(db)
    users, total = service.list_users(
        skip=skip,
        limit=limit,
        domain_id=domain_id,
        enabled_only=enabled_only
    )

    return UserListResponse(
        users=users,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_mailserver_db)):
    """
    Get user by ID

    Args:
        user_id: User ID
        db: Database session

    Returns:
        UserResponse: User details

    Raises:
        HTTPException: If user not found
    """
    service = MailUserService(db)
    user = service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return UserResponse(**user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Create a new mail user

    Args:
        request: User creation request
        http_request: HTTP request object (for IP logging)
        db: Database session

    Returns:
        UserResponse: Created user

    Raises:
        HTTPException: If user already exists or domain not found
    """
    service = MailUserService(db)
    admin_ip = get_admin_ip(http_request)

    user = service.create_user(
        email=request.email,
        password=request.password,
        domain_id=request.domain_id,
        admin_ip=admin_ip,
        quota=request.quota,
        enabled=request.enabled
    )

    # Convert to response format
    user_dict = service.get_user_by_id(user.id)
    return UserResponse(**user_dict)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Update user settings

    Args:
        user_id: User ID
        request: User update request
        http_request: HTTP request object (for IP logging)
        db: Database session

    Returns:
        UserResponse: Updated user

    Raises:
        HTTPException: If user not found
    """
    service = MailUserService(db)
    admin_ip = get_admin_ip(http_request)

    user = service.update_user(
        user_id=user_id,
        admin_ip=admin_ip,
        quota=request.quota,
        enabled=request.enabled
    )

    # Convert to response format
    user_dict = service.get_user_by_id(user.id)
    return UserResponse(**user_dict)


@router.post("/users/{user_id}/password", response_model=UserResponse)
def change_password(
    user_id: int,
    request: PasswordChangeRequest,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Change user password

    Args:
        user_id: User ID
        request: Password change request
        http_request: HTTP request object (for IP logging)
        db: Database session

    Returns:
        UserResponse: Updated user

    Raises:
        HTTPException: If user not found
    """
    service = MailUserService(db)
    admin_ip = get_admin_ip(http_request)

    user = service.change_password(
        user_id=user_id,
        new_password=request.new_password,
        admin_ip=admin_ip
    )

    # Convert to response format
    user_dict = service.get_user_by_id(user.id)
    return UserResponse(**user_dict)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Delete a user

    Args:
        user_id: User ID
        http_request: HTTP request object (for IP logging)
        db: Database session

    Raises:
        HTTPException: If user not found
    """
    service = MailUserService(db)
    admin_ip = get_admin_ip(http_request)

    service.delete_user(user_id=user_id, admin_ip=admin_ip)


# ============================================================================
# Domain Endpoints
# ============================================================================

@router.get("/domains", response_model=DomainListResponse)
def list_domains(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_mailserver_db)
):
    """
    List mail domains with statistics

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        enabled_only: Only return enabled domains
        db: Database session

    Returns:
        DomainListResponse: List of domains
    """
    service = MailDomainService(db)
    domains, total = service.list_domains(
        skip=skip,
        limit=limit,
        enabled_only=enabled_only
    )

    return DomainListResponse(
        domains=domains,
        total=total
    )


@router.get("/domains/{domain_id}", response_model=DomainResponse)
def get_domain(domain_id: int, db: Session = Depends(get_mailserver_db)):
    """
    Get domain by ID

    Args:
        domain_id: Domain ID
        db: Database session

    Returns:
        DomainResponse: Domain details

    Raises:
        HTTPException: If domain not found
    """
    service = MailDomainService(db)
    domain = service.get_domain_by_id(domain_id)

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with ID {domain_id} not found"
        )

    return DomainResponse(**domain)


@router.post("/domains", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def create_domain(
    request: DomainCreateRequest,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Create a new mail domain

    Args:
        request: Domain creation request
        http_request: HTTP request object (for IP logging)
        db: Database session

    Returns:
        DomainResponse: Created domain

    Raises:
        HTTPException: If domain already exists
    """
    service = MailDomainService(db)
    admin_ip = get_admin_ip(http_request)

    domain = service.create_domain(
        name=request.name,
        admin_ip=admin_ip,
        description=request.description,
        default_quota=request.default_quota,
        enabled=request.enabled
    )

    # Convert to response format
    domain_dict = service.get_domain_by_id(domain.id)
    return DomainResponse(**domain_dict)


@router.patch("/domains/{domain_id}", response_model=DomainResponse)
def update_domain(
    domain_id: int,
    request: DomainUpdateRequest,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Update domain settings

    Args:
        domain_id: Domain ID
        request: Domain update request
        http_request: HTTP request object (for IP logging)
        db: Database session

    Returns:
        DomainResponse: Updated domain

    Raises:
        HTTPException: If domain not found
    """
    service = MailDomainService(db)
    admin_ip = get_admin_ip(http_request)

    domain = service.update_domain(
        domain_id=domain_id,
        admin_ip=admin_ip,
        description=request.description,
        default_quota=request.default_quota,
        enabled=request.enabled
    )

    # Convert to response format
    domain_dict = service.get_domain_by_id(domain.id)
    return DomainResponse(**domain_dict)


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(
    domain_id: int,
    http_request: Request,
    db: Session = Depends(get_mailserver_db)
):
    """
    Delete a domain

    Args:
        domain_id: Domain ID
        http_request: HTTP request object (for IP logging)
        db: Database session

    Raises:
        HTTPException: If domain not found or has existing users
    """
    service = MailDomainService(db)
    admin_ip = get_admin_ip(http_request)

    service.delete_domain(domain_id=domain_id, admin_ip=admin_ip)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_email: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_mailserver_db)
):
    """
    List audit logs with filtering

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        user_email: Filter by user email (optional)
        action: Filter by action type (optional)
        db: Database session

    Returns:
        AuditLogListResponse: List of audit logs with pagination info
    """
    service = AuditService(db)
    logs, total = service.get_logs(
        skip=skip,
        limit=limit,
        user_email=user_email,
        action=action
    )

    return AuditLogListResponse(
        logs=logs,
        total=total,
        skip=skip,
        limit=limit
    )
