"""
Mail User Service

Business logic for mail user management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.mail_user import MailUser
from app.models.mail_domain import MailDomain
from app.services.mail_domain_service import MailDomainService
from app.services.audit_service import AuditService
from passlib.hash import sha512_crypt
from typing import Optional
from fastapi import HTTPException, status
import os


class MailUserService:
    """Service for managing mail users"""

    def __init__(self, db: Session):
        self.db = db
        self.domain_service = MailDomainService(db)
        self.audit_service = AuditService(db)

    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA512-CRYPT (Dovecot compatible)

        Args:
            password: Plain text password

        Returns:
            str: SHA512-CRYPT hash
        """
        return sha512_crypt.hash(password)

    def _generate_maildir(self, email: str) -> str:
        """
        Generate maildir path for user

        Args:
            email: User email address

        Returns:
            str: Maildir path (e.g., /var/mail/vmail/example.com/user/)
        """
        local_part, domain = email.split("@")
        return f"/var/mail/vmail/{domain}/{local_part}/"

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        domain_id: Optional[int] = None,
        enabled_only: bool = False
    ) -> tuple[list[dict], int]:
        """
        Get list of users with pagination and filtering

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            domain_id: Filter by domain ID (optional)
            enabled_only: Only return enabled users

        Returns:
            tuple: (list of user dicts, total count)
        """
        query = self.db.query(MailUser).join(MailDomain)

        if domain_id:
            query = query.filter(MailUser.domain_id == domain_id)

        if enabled_only:
            query = query.filter(MailUser.enabled == True)

        total = query.count()

        users = query.order_by(MailUser.email).offset(skip).limit(limit).all()

        # Format results
        result = []
        for user in users:
            result.append({
                "id": user.id,
                "email": user.email,
                "domain_id": user.domain_id,
                "domain_name": user.domain.name,
                "quota": user.quota,
                "enabled": user.enabled,
                "is_admin": user.is_admin,
                "created_at": user.created_at
            })

        return result, total

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            dict: User data, or None if not found
        """
        user = self.db.query(MailUser).filter(MailUser.id == user_id).first()

        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "domain_id": user.domain_id,
            "domain_name": user.domain.name,
            "quota": user.quota,
            "enabled": user.enabled,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        }

    def get_user_by_email(self, email: str) -> Optional[MailUser]:
        """
        Get user by email address

        Args:
            email: User email address

        Returns:
            MailUser: User object, or None if not found
        """
        return self.db.query(MailUser).filter(MailUser.email == email).first()

    def create_user(
        self,
        email: str,
        password: str,
        domain_id: int,
        admin_ip: str,
        quota: int = 1024,
        enabled: bool = True
    ) -> MailUser:
        """
        Create a new mail user

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            domain_id: Domain ID
            admin_ip: IP address of admin creating the user
            quota: Quota in MB
            enabled: Whether account is active

        Returns:
            MailUser: Created user

        Raises:
            HTTPException: If user already exists or domain not found
        """
        # Check if user already exists
        existing = self.get_user_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{email}' already exists"
            )

        # Validate domain exists and is enabled
        domain = self.db.query(MailDomain).filter(MailDomain.id == domain_id).first()
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain with ID {domain_id} not found"
            )

        if not domain.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain '{domain.name}' is disabled"
            )

        # Validate email domain matches
        email_domain = email.split("@")[1]
        if email_domain != domain.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email domain '{email_domain}' does not match domain '{domain.name}'"
            )

        # Hash password
        password_hash = self._hash_password(password)

        # Generate maildir
        maildir = self._generate_maildir(email)

        # Create user
        user = MailUser(
            email=email,
            domain_id=domain_id,
            password_hash=password_hash,
            maildir=maildir,
            quota=quota,
            uid=5000,  # Standard mail user UID
            gid=5000,  # Standard mail user GID
            enabled=enabled,
            is_admin=False  # Regular users are not admins by default
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log audit
        self.audit_service.log_audit(
            action="user_create",
            user_email=email,
            admin_ip=admin_ip,
            details={
                "user_id": user.id,
                "domain_id": domain_id,
                "domain_name": domain.name,
                "quota": quota,
                "enabled": enabled
            }
        )

        return user

    def update_user(
        self,
        user_id: int,
        admin_ip: str,
        quota: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> MailUser:
        """
        Update user settings

        Args:
            user_id: User ID
            admin_ip: IP address of admin performing update
            quota: New quota in MB (optional)
            enabled: New enabled status (optional)

        Returns:
            MailUser: Updated user

        Raises:
            HTTPException: If user not found
        """
        user = self.db.query(MailUser).filter(MailUser.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Track changes for audit log
        changes = {}

        if quota is not None:
            changes["quota"] = {"old": user.quota, "new": quota}
            user.quota = quota

        if enabled is not None:
            changes["enabled"] = {"old": user.enabled, "new": enabled}
            user.enabled = enabled

        self.db.commit()
        self.db.refresh(user)

        # Log audit
        if changes:
            self.audit_service.log_audit(
                action="user_update",
                user_email=user.email,
                admin_ip=admin_ip,
                details={
                    "user_id": user.id,
                    "changes": changes
                }
            )

        return user

    def change_password(
        self,
        user_id: int,
        new_password: str,
        admin_ip: str
    ) -> MailUser:
        """
        Change user password

        Args:
            user_id: User ID
            new_password: New plain text password (will be hashed)
            admin_ip: IP address of admin performing change

        Returns:
            MailUser: Updated user

        Raises:
            HTTPException: If user not found
        """
        user = self.db.query(MailUser).filter(MailUser.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Hash new password
        user.password_hash = self._hash_password(new_password)

        self.db.commit()
        self.db.refresh(user)

        # Log audit (don't include password in details)
        self.audit_service.log_audit(
            action="password_change",
            user_email=user.email,
            admin_ip=admin_ip,
            details={
                "user_id": user.id
            }
        )

        return user

    def delete_user(self, user_id: int, admin_ip: str) -> None:
        """
        Delete a user

        Args:
            user_id: User ID
            admin_ip: IP address of admin performing deletion

        Raises:
            HTTPException: If user not found
        """
        user = self.db.query(MailUser).filter(MailUser.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        user_email = user.email
        domain_id = user.domain_id

        # Delete user
        self.db.delete(user)
        self.db.commit()

        # Log audit
        self.audit_service.log_audit(
            action="user_delete",
            user_email=user_email,
            admin_ip=admin_ip,
            details={
                "user_id": user_id,
                "domain_id": domain_id
            }
        )
