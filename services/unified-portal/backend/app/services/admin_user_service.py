"""Admin user management service."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser

logger = logging.getLogger(__name__)


class AdminUserService:
    """Service for managing admin users.

    Handles user authentication, authorization, and CRUD operations.
    Passwords are hashed using bcrypt.
    """

    def __init__(self, db: Session):
        """Initialize admin user service.

        Args:
            db: Database session
        """
        self.db = db

    def list_users(self, active_only: bool = False) -> list[AdminUser]:
        """List all admin users.

        Args:
            active_only: Only return active users

        Returns:
            List of admin users
        """
        query = self.db.query(AdminUser)

        if active_only:
            query = query.filter(AdminUser.is_active == True)

        return query.order_by(AdminUser.created_at.desc()).all()

    def get_user(self, user_id: int) -> Optional[AdminUser]:
        """Get admin user by ID.

        Args:
            user_id: User ID

        Returns:
            Admin user or None if not found
        """
        return self.db.query(AdminUser).filter(AdminUser.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Get admin user by username.

        Args:
            username: Username

        Returns:
            Admin user or None if not found
        """
        return self.db.query(AdminUser).filter(AdminUser.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[AdminUser]:
        """Get admin user by email.

        Args:
            email: Email address

        Returns:
            Admin user or None if not found
        """
        return self.db.query(AdminUser).filter(AdminUser.email == email).first()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
    ) -> AdminUser:
        """Create a new admin user.

        Args:
            username: Username
            email: Email address
            password: Plain text password (will be hashed)
            full_name: Full name (optional)
            is_superuser: Superuser flag

        Returns:
            Created admin user

        Raises:
            ValueError: If user already exists or creation fails
        """
        # Check if username or email already exists
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        if self.get_user_by_email(email):
            raise ValueError(f"Email '{email}' already exists")

        try:
            # Hash password
            password_hash = self.hash_password(password)

            # Create user
            user = AdminUser(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                is_active=True,
                is_superuser=is_superuser,
            )

            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Admin user created: {username} ({email})")
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create admin user: {e}")
            raise ValueError(f"Failed to create admin user: {e}")

    def update_password(self, user_id: int, new_password: str) -> AdminUser:
        """Update user password.

        Args:
            user_id: User ID
            new_password: New plain text password

        Returns:
            Updated admin user

        Raises:
            ValueError: If user not found or update fails
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            user.password_hash = self.hash_password(new_password)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Password updated for user: {user.username}")
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update password: {e}")
            raise ValueError(f"Failed to update password: {e}")

    def update_user(self, user_id: int, user_update: dict) -> AdminUser:
        """Update an admin user.

        Args:
            user_id: User ID
            user_update: Dictionary of fields to update (email, password, is_active, is_superuser, full_name)

        Returns:
            Updated admin user

        Raises:
            ValueError: If user not found or update fails
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            # Update email if provided
            if hasattr(user_update, 'email') and user_update.email is not None:
                # Check if email is already used by another user
                existing = self.get_user_by_email(user_update.email)
                if existing and existing.id != user_id:
                    raise ValueError(f"Email '{user_update.email}' already exists")
                user.email = user_update.email

            # Update password if provided
            if hasattr(user_update, 'password') and user_update.password is not None:
                user.password_hash = self.hash_password(user_update.password)

            # Update full_name if provided
            if hasattr(user_update, 'full_name') and user_update.full_name is not None:
                user.full_name = user_update.full_name

            # Update is_active if provided
            if hasattr(user_update, 'is_active') and user_update.is_active is not None:
                user.is_active = user_update.is_active

            # Update is_superuser if provided
            if hasattr(user_update, 'is_superuser') and user_update.is_superuser is not None:
                user.is_superuser = user_update.is_superuser

            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Admin user updated: {user.username}")
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update user: {e}")
            raise ValueError(f"Failed to update user: {e}")

    def delete_user(self, user_id: int) -> None:
        """Delete an admin user (hard delete).

        Args:
            user_id: User ID

        Raises:
            ValueError: If user not found or deletion fails
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            self.db.delete(user)
            self.db.commit()

            logger.info(f"Admin user deleted: {user.username}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete user: {e}")
            raise ValueError(f"Failed to delete user: {e}")

    def deactivate_user(self, user_id: int) -> AdminUser:
        """Deactivate an admin user.

        Args:
            user_id: User ID

        Returns:
            Deactivated admin user

        Raises:
            ValueError: If user not found
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Admin user deactivated: {user.username}")
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to deactivate user: {e}")
            raise ValueError(f"Failed to deactivate user: {e}")

    def authenticate(self, username: str, password: str) -> Optional[AdminUser]:
        """Authenticate an admin user.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            Authenticated admin user or None if authentication fails
        """
        # Try username first, then email
        user = self.get_user_by_username(username) or self.get_user_by_email(username)

        if not user:
            logger.warning(f"Authentication failed: User '{username}' not found")
            return None

        if not user.is_active:
            logger.warning(f"Authentication failed: User '{username}' is inactive")
            return None

        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: Invalid password for '{username}'")
            return None

        # Update last login timestamp
        user.last_login = datetime.utcnow()
        self.db.commit()

        logger.info(f"User authenticated: {username}")
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Bcrypt password hash
        """
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password
            password_hash: Bcrypt password hash

        Returns:
            True if password matches, False otherwise
        """
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)


def get_admin_user_service(db: Session) -> AdminUserService:
    """Get admin user service instance.

    Args:
        db: Database session

    Returns:
        AdminUserService instance
    """
    return AdminUserService(db)
