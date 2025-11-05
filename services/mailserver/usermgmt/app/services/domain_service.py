"""
Domain Service - Business logic for domain management operations

Handles CRUD operations for domains with audit logging
"""
import json
from app.database import db
from app.models import Domain, AuditLog
from sqlalchemy.exc import IntegrityError
from typing import List, Optional


class DomainService:
    """
    Domain management service with audit logging

    Provides methods for:
    - Listing domains
    - Creating domains
    - Updating domains
    - Deleting domains
    - Toggling domain status
    """

    @staticmethod
    def list_domains(enabled_only: bool = False) -> List[Domain]:
        """
        List all domains, optionally filtered by enabled status

        Args:
            enabled_only: If True, only return enabled domains

        Returns:
            List of Domain objects

        Examples:
            >>> DomainService.list_domains()  # All domains
            >>> DomainService.list_domains(enabled_only=True)  # Only enabled
        """
        query = Domain.query

        if enabled_only:
            query = query.filter_by(enabled=True)

        return query.order_by(Domain.name).all()

    @staticmethod
    def create_domain(
        name: str,
        description: str = '',
        default_quota: int = 1024,
        enabled: bool = True,
        admin_ip: str = 'system'
    ) -> Domain:
        """
        Create a new domain

        Args:
            name: Domain name (e.g., example.com)
            description: Optional domain description
            default_quota: Default quota for new users in MB (default: 1024)
            enabled: Whether domain is enabled (default: True)
            admin_ip: Who performed this action (for audit log)

        Returns:
            Created Domain object

        Raises:
            ValueError: If domain name already exists or invalid

        Examples:
            >>> DomainService.create_domain(
            ...     name='example.com',
            ...     description='Example domain',
            ...     default_quota=2048
            ... )
        """
        # Validate domain name
        if not name or not name.strip():
            raise ValueError("ドメイン名は必須です")

        # Check if domain already exists
        existing_domain = Domain.query.filter_by(name=name).first()
        if existing_domain:
            raise ValueError("このドメイン名は既に存在します")

        # Validate quota
        if default_quota < 1 or default_quota > 10240:
            raise ValueError("デフォルトクォータは1～10240MBの範囲で設定してください")

        # Create domain
        domain = Domain(
            name=name.strip(),
            description=description.strip() if description else '',
            default_quota=default_quota,
            enabled=enabled
        )

        try:
            db.session.add(domain)
            db.session.commit()

            # Log audit
            DomainService.log_audit(
                action='create',
                domain_name=name,
                admin_ip=admin_ip,
                details=json.dumps({
                    "message": "Domain created",
                    "default_quota_mb": default_quota,
                    "enabled": enabled
                })
            )

            return domain

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"データベース整合性エラー: {str(e)}")

    @staticmethod
    def get_domain_by_id(domain_id: int) -> Optional[Domain]:
        """
        Get domain by ID

        Args:
            domain_id: Domain ID

        Returns:
            Domain object if found, None otherwise

        Examples:
            >>> domain = DomainService.get_domain_by_id(1)
            >>> if domain:
            ...     print(domain.name)
        """
        return Domain.query.get(domain_id)

    @staticmethod
    def get_domain_by_name(name: str) -> Optional[Domain]:
        """
        Get domain by name

        Args:
            name: Domain name

        Returns:
            Domain object if found, None otherwise

        Examples:
            >>> domain = DomainService.get_domain_by_name('example.com')
            >>> if domain:
            ...     print(domain.id)
        """
        return Domain.query.filter_by(name=name).first()

    @staticmethod
    def update_domain(
        domain_id: int,
        admin_ip: str = 'system',
        **kwargs
    ) -> Domain:
        """
        Update domain attributes

        Args:
            domain_id: Domain ID
            admin_ip: Who performed this action (for audit log)
            **kwargs: Attributes to update (description, default_quota, enabled)

        Returns:
            Updated Domain object

        Raises:
            ValueError: If domain not found or name change attempted

        Examples:
            >>> DomainService.update_domain(
            ...     domain_id=1,
            ...     description='Updated description',
            ...     default_quota=2048
            ... )
        """
        # Prevent name changes
        if 'name' in kwargs:
            raise ValueError("ドメイン名は変更できません")

        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # Track changes for audit log
        changes = []

        # Update allowed attributes
        allowed_attrs = ['description', 'default_quota', 'enabled']
        for attr, value in kwargs.items():
            if attr in allowed_attrs and hasattr(domain, attr):
                old_value = getattr(domain, attr)
                if old_value != value:
                    setattr(domain, attr, value)
                    changes.append(f"{attr}: {old_value} → {value}")

        if changes:
            try:
                db.session.commit()

                # Log audit
                DomainService.log_audit(
                    action='update',
                    domain_name=domain.name,
                    admin_ip=admin_ip,
                    details=json.dumps({
                        "message": "Domain updated",
                        "changes": changes
                    })
                )

            except IntegrityError as e:
                db.session.rollback()
                raise ValueError(f"データベース整合性エラー: {str(e)}")

        return domain

    @staticmethod
    def delete_domain(domain_id: int, admin_ip: str = 'system') -> None:
        """
        Delete domain (only if no users exist)

        Args:
            domain_id: Domain ID
            admin_ip: Who performed this action (for audit log)

        Raises:
            ValueError: If domain not found or has users

        Examples:
            >>> DomainService.delete_domain(domain_id=2)
        """
        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        # Check if domain has users
        if domain.user_count() > 0:
            raise ValueError(
                f"このドメインには {domain.user_count()} 人のユーザが存在するため削除できません。"
                "先にすべてのユーザを削除してください。"
            )

        domain_name = domain.name

        try:
            db.session.delete(domain)
            db.session.commit()

            # Log audit
            DomainService.log_audit(
                action='delete',
                domain_name=domain_name,
                admin_ip=admin_ip,
                details=json.dumps({"message": "Domain deleted"})
            )

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"データベース整合性エラー: {str(e)}")

    @staticmethod
    def toggle_domain_status(
        domain_id: int,
        enabled: bool,
        admin_ip: str = 'system'
    ) -> Domain:
        """
        Enable or disable domain

        Args:
            domain_id: Domain ID
            enabled: True to enable, False to disable
            admin_ip: Who performed this action (for audit log)

        Returns:
            Updated Domain object

        Raises:
            ValueError: If domain not found

        Examples:
            >>> DomainService.toggle_domain_status(domain_id=1, enabled=False)
        """
        domain = Domain.query.get(domain_id)
        if not domain:
            raise ValueError("ドメインが見つかりません")

        domain.enabled = enabled

        try:
            db.session.commit()

            # Log audit
            DomainService.log_audit(
                action='update',
                domain_name=domain.name,
                admin_ip=admin_ip,
                details=json.dumps({
                    "message": "Domain status toggled",
                    "enabled": enabled
                })
            )

            return domain

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"データベース整合性エラー: {str(e)}")

    @staticmethod
    def log_audit(
        action: str,
        domain_name: str,
        admin_ip: str,
        details: str = ''
    ) -> AuditLog:
        """
        Create audit log entry for domain operations

        Args:
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            domain_name: Affected domain name
            admin_ip: Who performed the action
            details: Additional details (JSON string)

        Returns:
            Created AuditLog object

        Examples:
            >>> DomainService.log_audit(
            ...     action='create',
            ...     domain_name='example.com',
            ...     admin_ip='admin@example.com',
            ...     details='{"message": "Domain created"}'
            ... )
        """
        audit_log = AuditLog(
            action=f"domain_{action}",
            user_email=f"domain:{domain_name}",  # Use domain: prefix to distinguish
            admin_ip=admin_ip,
            details=details
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log
