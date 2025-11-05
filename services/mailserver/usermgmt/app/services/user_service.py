"""
User Service - Business logic for user management operations

Handles CRUD operations for users with audit logging
"""
import json
from app.database import db
from app.models import User, Domain, AuditLog
from app.services.password import hash_password
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any


class UserService:
    """
    User management service with audit logging

    Provides methods for:
    - Listing users
    - Creating users
    - Updating users
    - Deleting users
    - Changing passwords
    - Toggling user status
    """

    @staticmethod
    def list_users(domain_id: Optional[int] = None) -> List[User]:
        """
        List all users, optionally filtered by domain

        Args:
            domain_id: Optional domain ID to filter users

        Returns:
            List of User objects

        Examples:
            >>> UserService.list_users()  # All users
            >>> UserService.list_users(domain_id=1)  # Users in domain 1
        """
        query = User.query

        if domain_id is not None:
            query = query.filter_by(domain_id=domain_id)

        return query.order_by(User.email).all()

    @staticmethod
    def create_user(
        email: str,
        password: str,
        domain_id: int,
        quota: int = 1024,
        enabled: bool = True,
        admin_ip: str = 'system'
    ) -> User:
        """
        Create a new user with automatic maildir generation

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            domain_id: Domain ID
            quota: Mailbox quota in MB (default: 1024)
            enabled: Whether user is enabled (default: True)
            admin_ip: Who performed this action (for audit log)

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists or domain not found

        Examples:
            >>> UserService.create_user(
            ...     email='user@example.com',
            ...     password='SecurePass123!',
            ...     domain_id=1
            ... )
        """
        # Validate domain exists
        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("Domain not found")

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise ValueError("Email address already exists")

        # Extract username and domain from email
        try:
            username, domain_name = email.split('@')
        except ValueError:
            raise ValueError("Invalid email format")

        # Generate maildir path
        maildir = f"/var/mail/vmail/{domain_name}/{username}/"

        # Hash password with SHA512-CRYPT
        password_hash = hash_password(password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            domain_id=domain_id,
            maildir=maildir,
            quota=quota,
            uid=5000,
            gid=5000,
            enabled=enabled
        )

        try:
            db.session.add(user)
            db.session.commit()

            # Log audit
            UserService.log_audit(
                action='create',
                user_email=email,
                admin_ip=admin_ip,
                details=json.dumps({"message": "User created", "quota_mb": quota})
            )

            return user

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get user by email address

        Args:
            email: User email address

        Returns:
            User object if found, None otherwise

        Examples:
            >>> user = UserService.get_user_by_email('test@example.com')
            >>> if user:
            ...     print(user.email)
        """
        return User.query.filter_by(email=email).first()

    @staticmethod
    def update_user(
        email: str,
        admin_ip: str = 'system',
        **kwargs
    ) -> User:
        """
        Update user attributes

        Args:
            email: User email address
            admin_ip: Who performed this action (for audit log)
            **kwargs: Attributes to update (quota, enabled, etc.)

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found or email change attempted

        Examples:
            >>> UserService.update_user(
            ...     email='test@example.com',
            ...     quota=2048,
            ...     enabled=False
            ... )
        """
        # Prevent email changes
        if 'email' in kwargs or 'new_email' in kwargs:
            raise ValueError("Email address cannot be changed")

        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")

        # Track changes for audit log
        changes = []

        # Update allowed attributes
        allowed_attrs = ['quota', 'enabled', 'uid', 'gid']
        for attr, value in kwargs.items():
            if attr in allowed_attrs and hasattr(user, attr):
                old_value = getattr(user, attr)
                if old_value != value:
                    setattr(user, attr, value)
                    changes.append(f"{attr}: {old_value} → {value}")

        if changes:
            try:
                db.session.commit()

                # Log audit
                UserService.log_audit(
                    action='update',
                    user_email=email,
                    admin_ip=admin_ip,
                    details=json.dumps({"message": "User updated", "changes": changes})
                )

            except IntegrityError as e:
                db.session.rollback()
                raise ValueError(f"Database integrity error: {str(e)}")

        return user

    @staticmethod
    def delete_user(email: str, admin_ip: str = 'system') -> None:
        """
        Delete user

        Args:
            email: User email address
            admin_ip: Who performed this action (for audit log)

        Raises:
            ValueError: If user not found

        Examples:
            >>> UserService.delete_user('olduser@example.com')
        """
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")

        try:
            db.session.delete(user)
            db.session.commit()

            # Log audit
            UserService.log_audit(
                action='delete',
                user_email=email,
                admin_ip=admin_ip,
                details='{"message": "User account deleted"}'
            )

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")

    @staticmethod
    def toggle_user_status(
        email: str,
        enabled: bool,
        admin_ip: str = 'system'
    ) -> User:
        """
        Enable or disable user

        Args:
            email: User email address
            enabled: True to enable, False to disable
            admin_ip: Who performed this action (for audit log)

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found

        Examples:
            >>> UserService.toggle_user_status('test@example.com', False)
        """
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")

        user.enabled = enabled

        try:
            db.session.commit()

            # Log audit
            action = 'update'  # Toggle status is an update operation
            UserService.log_audit(
                action=action,
                user_email=email,
                admin_ip=admin_ip,
                details=json.dumps({"message": "User status toggled", "enabled": enabled})
            )

            return user

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")

    @staticmethod
    def change_password(
        email: str,
        new_password: str,
        admin_ip: str = 'system'
    ) -> User:
        """
        Change user password

        Args:
            email: User email address
            new_password: New plain text password (will be hashed)
            admin_ip: Who performed this action (for audit log)

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found

        Examples:
            >>> UserService.change_password(
            ...     email='test@example.com',
            ...     new_password='NewSecurePass456!'
            ... )
        """
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")

        # Hash new password
        user.password_hash = hash_password(new_password)

        try:
            db.session.commit()

            # Log audit
            UserService.log_audit(
                action='password_change',
                user_email=email,
                admin_ip=admin_ip,
                details='{"message": "Password changed"}'
            )

            return user

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")

    @staticmethod
    def log_audit(
        action: str,
        user_email: str,
        admin_ip: str,
        details: str = ''
    ) -> AuditLog:
        """
        Create audit log entry

        Args:
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            user_email: Affected user email
            admin_ip: Who performed the action
            details: Additional details

        Returns:
            Created AuditLog object

        Examples:
            >>> UserService.log_audit(
            ...     action='create',
            ...     user_email='newuser@example.com',
            ...     admin_ip='admin@example.com',
            ...     details='User created with quota 1024MB'
            ... )
        """
        audit_log = AuditLog(
            action=action,
            user_email=user_email,
            admin_ip=admin_ip,
            details=details
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log
