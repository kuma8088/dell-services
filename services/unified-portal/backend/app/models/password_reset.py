"""Password reset token database model."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class PasswordReset(Base):
    """Password reset token model.

    Stores time-limited tokens for password reset operations.
    Tokens expire after a configurable duration (e.g., 1 hour).
    """

    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="Associated admin user ID")
    token = Column(String(255), unique=True, nullable=False, index=True, comment="Reset token (UUID or random string)")
    expires_at = Column(DateTime, nullable=False, comment="Token expiration timestamp")
    used = Column(DateTime, nullable=True, comment="Token usage timestamp (null if unused)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """String representation."""
        return f"<PasswordReset(id={self.id}, admin_user_id={self.admin_user_id}, token='{self.token[:10]}...', expires_at={self.expires_at})>"

    def is_expired(self) -> bool:
        """Check if token is expired.

        Returns:
            True if token has expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at

    def is_used(self) -> bool:
        """Check if token has been used.

        Returns:
            True if token has been used, False otherwise
        """
        return self.used is not None
