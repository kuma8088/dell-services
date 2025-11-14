"""Authentication router for login and token management."""
from __future__ import annotations

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import Token, authenticate_user, create_access_token, get_current_user
from app.config import get_settings
from app.database import get_db
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    PasswordResetRequest,
    PasswordResetVerify,
)
from app.services.admin_user_service import get_admin_user_service
from app.services.email_service import get_email_service
from app.services.password_reset_service import get_password_reset_service

settings = get_settings()

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class UserResponse(BaseModel):
    """User response model."""

    username: str


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest) -> Token:
    """Login endpoint - authenticate and return JWT token.

    Args:
        login_data: Username and password.

    Returns:
        Token: JWT access token.

    Raises:
        HTTPException: If authentication fails.
    """
    if not authenticate_user(login_data.username, login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": login_data.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token)


@router.post("/login/form", response_model=Token)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Login endpoint with OAuth2 form data (for Swagger UI).

    Args:
        form_data: OAuth2 password form data.

    Returns:
        Token: JWT access token.

    Raises:
        HTTPException: If authentication fails.
    """
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: str = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user.

    Args:
        current_user: Current user from JWT token.

    Returns:
        UserResponse: Current user information.
    """
    return UserResponse(username=current_user)


# ============================================================================
# Admin User Management Endpoints
# ============================================================================

@router.get("/users", response_model=List[AdminUserResponse])
def list_admin_users(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    List all admin users.

    Args:
        active_only: Only return active users
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of admin users
    """
    service = get_admin_user_service(db)
    users = service.list_users(active_only=active_only)
    return users


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get admin user by ID.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Admin user details

    Raises:
        HTTPException: If user not found
    """
    service = get_admin_user_service(db)
    user = service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

    return user


@router.post("/users", response_model=AdminUserResponse, status_code=201)
def create_admin_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Create a new admin user.

    Args:
        user_data: User creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created admin user

    Raises:
        HTTPException: If user creation fails
    """
    service = get_admin_user_service(db)

    try:
        user = service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            is_superuser=user_data.is_superuser,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_admin_user(
    user_id: int,
    user_update: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Update admin user.

    Args:
        user_id: User ID
        user_update: User update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated admin user

    Raises:
        HTTPException: If user not found or update fails
    """
    service = get_admin_user_service(db)

    try:
        user = service.update_user(user_id, user_update)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}", status_code=204)
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Delete admin user.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If user not found or deletion fails
    """
    service = get_admin_user_service(db)

    try:
        service.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Password Reset Endpoints
# ============================================================================

@router.post("/password-reset/request", status_code=200)
def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.

    Args:
        reset_request: Password reset request data (username or email)
        db: Database session

    Returns:
        Success message

    Note:
        Always returns success to prevent username enumeration attacks,
        even if user doesn't exist.
    """
    admin_service = get_admin_user_service(db)
    reset_service = get_password_reset_service(db)
    email_service = get_email_service()

    try:
        # Get user by email
        user = admin_service.get_user_by_email(reset_request.email)

        if user:
            # Create reset token
            reset = reset_service.create_reset_token(user.id)

            # Send reset email
            reset_url_base = f"{settings.frontend_url}/reset-password"
            email_service.send_password_reset_email(
                to=user.email,
                username=user.username,
                reset_token=reset.token,
                reset_url_base=reset_url_base,
            )
    except Exception:
        # Log error but don't expose to user
        pass

    # Always return success (security: prevent username enumeration)
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent.",
    }


@router.post("/password-reset/verify", status_code=200)
def verify_reset_token(
    verify_data: PasswordResetVerify,
    db: Session = Depends(get_db),
):
    """
    Verify password reset token.

    Args:
        verify_data: Token verification data
        db: Database session

    Returns:
        Token validity status

    Raises:
        HTTPException: If token is invalid or expired
    """
    reset_service = get_password_reset_service(db)

    reset = reset_service.verify_token(verify_data.token)

    if not reset:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        )

    return {"valid": True, "message": "Token is valid"}


@router.post("/password-reset/confirm", status_code=200)
def confirm_password_reset(
    reset_data: PasswordResetVerify,
    db: Session = Depends(get_db),
):
    """
    Confirm password reset with new password.

    Args:
        reset_data: Password reset confirmation data (token + new password)
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or password reset fails
    """
    reset_service = get_password_reset_service(db)

    try:
        success = reset_service.reset_password(reset_data.token, reset_data.new_password)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to reset password",
            )

        return {
            "success": True,
            "message": "Password has been reset successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
