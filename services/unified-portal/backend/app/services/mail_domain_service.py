"""
Mail Domain Service

Business logic for mail domain management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.mail_domain import MailDomain
from app.models.mail_user import MailUser
from app.services.audit_service import AuditService
from typing import Optional
from fastapi import HTTPException, status


class MailDomainService:
    """Service for managing mail domains"""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def list_domains(
        self,
        skip: int = 0,
        limit: int = 100,
        enabled_only: bool = False
    ) -> tuple[list[dict], int]:
        """
        Get list of domains with calculated statistics

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            enabled_only: Only return enabled domains

        Returns:
            tuple: (list of domain dicts with stats, total count)
        """
        query = self.db.query(MailDomain)

        if enabled_only:
            query = query.filter(MailDomain.enabled == True)

        total = query.count()

        domains = query.order_by(MailDomain.name).offset(skip).limit(limit).all()

        # Calculate statistics for each domain
        result = []
        for domain in domains:
            # Count users in this domain
            user_count = self.db.query(func.count(MailUser.id)).filter(
                MailUser.domain_id == domain.id
            ).scalar()

            # Sum total quota used
            total_quota = self.db.query(func.sum(MailUser.quota)).filter(
                MailUser.domain_id == domain.id
            ).scalar() or 0

            result.append({
                "id": domain.id,
                "name": domain.name,
                "description": domain.description,
                "default_quota": domain.default_quota,
                "enabled": domain.enabled,
                "user_count": user_count,
                "total_quota_used": total_quota,
                "created_at": domain.created_at
            })

        return result, total

    def get_domain_by_id(self, domain_id: int) -> Optional[dict]:
        """
        Get domain by ID with statistics

        Args:
            domain_id: Domain ID

        Returns:
            dict: Domain data with statistics, or None if not found
        """
        domain = self.db.query(MailDomain).filter(MailDomain.id == domain_id).first()

        if not domain:
            return None

        # Calculate statistics
        user_count = self.db.query(func.count(MailUser.id)).filter(
            MailUser.domain_id == domain.id
        ).scalar()

        total_quota = self.db.query(func.sum(MailUser.quota)).filter(
            MailUser.domain_id == domain.id
        ).scalar() or 0

        return {
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "default_quota": domain.default_quota,
            "enabled": domain.enabled,
            "user_count": user_count,
            "total_quota_used": total_quota,
            "created_at": domain.created_at
        }

    def get_domain_by_name(self, domain_name: str) -> Optional[MailDomain]:
        """
        Get domain by name

        Args:
            domain_name: Domain name (e.g., example.com)

        Returns:
            MailDomain: Domain object, or None if not found
        """
        return self.db.query(MailDomain).filter(MailDomain.name == domain_name).first()

    def create_domain(
        self,
        name: str,
        admin_ip: str,
        description: Optional[str] = None,
        default_quota: int = 1024,
        enabled: bool = True
    ) -> MailDomain:
        """
        Create a new mail domain

        Args:
            name: Domain name (e.g., example.com)
            admin_ip: IP address of admin creating the domain
            description: Optional description
            default_quota: Default quota for new users in MB
            enabled: Whether domain is active

        Returns:
            MailDomain: Created domain

        Raises:
            HTTPException: If domain already exists
        """
        # Check if domain already exists
        existing = self.get_domain_by_name(name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain '{name}' already exists"
            )

        # Create domain
        domain = MailDomain(
            name=name,
            description=description,
            default_quota=default_quota,
            enabled=enabled
        )

        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)

        # Log audit
        self.audit_service.log_audit(
            action="domain_create",
            user_email=f"domain:{name}",
            admin_ip=admin_ip,
            details={
                "domain_id": domain.id,
                "domain_name": name,
                "default_quota": default_quota,
                "enabled": enabled
            }
        )

        return domain

    def update_domain(
        self,
        domain_id: int,
        admin_ip: str,
        description: Optional[str] = None,
        default_quota: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> MailDomain:
        """
        Update domain settings

        Args:
            domain_id: Domain ID
            admin_ip: IP address of admin performing update
            description: New description (optional)
            default_quota: New default quota (optional)
            enabled: New enabled status (optional)

        Returns:
            MailDomain: Updated domain

        Raises:
            HTTPException: If domain not found
        """
        domain = self.db.query(MailDomain).filter(MailDomain.id == domain_id).first()

        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain with ID {domain_id} not found"
            )

        # Track changes for audit log
        changes = {}

        if description is not None:
            changes["description"] = {"old": domain.description, "new": description}
            domain.description = description

        if default_quota is not None:
            changes["default_quota"] = {"old": domain.default_quota, "new": default_quota}
            domain.default_quota = default_quota

        if enabled is not None:
            changes["enabled"] = {"old": domain.enabled, "new": enabled}
            domain.enabled = enabled

        self.db.commit()
        self.db.refresh(domain)

        # Log audit
        if changes:
            self.audit_service.log_audit(
                action="domain_update",
                user_email=f"domain:{domain.name}",
                admin_ip=admin_ip,
                details={
                    "domain_id": domain.id,
                    "domain_name": domain.name,
                    "changes": changes
                }
            )

        return domain

    def delete_domain(self, domain_id: int, admin_ip: str) -> None:
        """
        Delete a domain

        Args:
            domain_id: Domain ID
            admin_ip: IP address of admin performing deletion

        Raises:
            HTTPException: If domain not found or has existing users
        """
        domain = self.db.query(MailDomain).filter(MailDomain.id == domain_id).first()

        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain with ID {domain_id} not found"
            )

        # Check if domain has users
        user_count = self.db.query(func.count(MailUser.id)).filter(
            MailUser.domain_id == domain.id
        ).scalar()

        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete domain '{domain.name}': {user_count} user(s) exist. Delete users first."
            )

        domain_name = domain.name

        # Delete domain
        self.db.delete(domain)
        self.db.commit()

        # Log audit
        self.audit_service.log_audit(
            action="domain_delete",
            user_email=f"domain:{domain_name}",
            admin_ip=admin_ip,
            details={
                "domain_id": domain_id,
                "domain_name": domain_name
            }
        )
