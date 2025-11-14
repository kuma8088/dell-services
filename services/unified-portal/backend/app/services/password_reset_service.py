"""Password reset service."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.password_reset import PasswordReset

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for password reset operations.

    Handles reset token generation, validation, and password reset execution.
    Tokens expire after a configurable duration (default: 1 hour).
    """

    def __init__(self, db: Session, token_expiry_hours: int = 1):
        """Initialize password reset service.

        Args:
            db: Database session
            token_expiry_hours: Token expiration time in hours
        """
        self.db = db
        self.token_expiry_hours = token_expiry_hours

    def create_reset_token(self, user_id: int) -> PasswordReset:
        """Create a password reset token for a user.

        Args:
            user_id: Admin user ID

        Returns:
            Created password reset token

        Raises:
            ValueError: If user not found or token creation fails
        """
        # Check if user exists
        user = self.db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            # Invalidate any existing unused tokens for this user
            self._invalidate_user_tokens(user_id)

            # Generate token
            token = self._generate_token()
            expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)

            # Create reset record
            reset = PasswordReset(
                admin_user_id=user_id,
                token=token,
                expires_at=expires_at,
            )

            self.db.add(reset)
            self.db.commit()
            self.db.refresh(reset)

            logger.info(f"Password reset token created for user {user_id}")
            return reset

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create reset token: {e}")
            raise ValueError(f"Failed to create reset token: {e}")

    def verify_token(self, token: str) -> Optional[PasswordReset]:
        """Verify a password reset token.

        Args:
            token: Reset token

        Returns:
            PasswordReset record if valid, None otherwise
        """
        reset = self.db.query(PasswordReset).filter(PasswordReset.token == token).first()

        if not reset:
            logger.warning(f"Invalid reset token: {token[:10]}...")
            return None

        if reset.is_expired():
            logger.warning(f"Expired reset token: {token[:10]}...")
            return None

        if reset.is_used():
            logger.warning(f"Already used reset token: {token[:10]}...")
            return None

        return reset

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a reset token.

        Args:
            token: Reset token
            new_password: New plain text password

        Returns:
            True if password was reset successfully, False otherwise

        Raises:
            ValueError: If token is invalid or password reset fails
        """
        reset = self.verify_token(token)
        if not reset:
            raise ValueError("Invalid or expired reset token")

        try:
            # Get user
            user = self.db.query(AdminUser).filter(AdminUser.id == reset.admin_user_id).first()
            if not user:
                raise ValueError("User not found")

            # Hash and update password
            from app.services.admin_user_service import AdminUserService

            user.password_hash = AdminUserService.hash_password(new_password)

            # Mark token as used
            reset.used = datetime.utcnow()

            self.db.commit()

            logger.info(f"Password reset successful for user {user.username}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset password: {e}")
            raise ValueError(f"Failed to reset password: {e}")

    def _invalidate_user_tokens(self, user_id: int) -> None:
        """Invalidate all unused tokens for a user.

        Args:
            user_id: User ID
        """
        self.db.query(PasswordReset).filter(
            PasswordReset.admin_user_id == user_id, PasswordReset.used.is_(None)
        ).update({"used": datetime.utcnow()})
        self.db.commit()

    @staticmethod
    def _generate_token(length: int = 64) -> str:
        """Generate a random reset token.

        Args:
            length: Token length in characters

        Returns:
            Random token
        """
        return secrets.token_urlsafe(length)


def get_password_reset_service(db: Session) -> PasswordResetService:
    """Get password reset service instance.

    Args:
        db: Database session

    Returns:
        PasswordResetService instance
    """
    return PasswordResetService(db)
