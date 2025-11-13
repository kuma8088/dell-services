"""Authentication router for login and token management."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth import Token, authenticate_user, create_access_token, get_current_user
from app.config import get_settings

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
