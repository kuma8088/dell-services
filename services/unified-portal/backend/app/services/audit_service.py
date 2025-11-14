"""
Audit Service

Business logic for audit logging.
"""
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Optional
import json


class AuditService:
    """Service for managing audit logs"""

    def __init__(self, db: Session):
        self.db = db

    def log_audit(
        self,
        action: str,
        user_email: str,
        admin_ip: str,
        details: Optional[dict] = None
    ) -> AuditLog:
        """
        Create an audit log entry

        Args:
            action: Action type (e.g., 'create', 'update', 'delete', 'password_change')
            user_email: Email of affected user
            admin_ip: IP address of admin performing action
            details: Additional details as dictionary (will be JSON serialized)

        Returns:
            AuditLog: Created audit log entry
        """
        audit_log = AuditLog(
            action=action,
            user_email=user_email,
            admin_ip=admin_ip,
            details=json.dumps(details) if details else None
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def get_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        user_email: Optional[str] = None,
        action: Optional[str] = None
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs with optional filtering

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            user_email: Filter by user email (optional)
            action: Filter by action type (optional)

        Returns:
            tuple: (list of AuditLog, total count)
        """
        query = self.db.query(AuditLog)

        # Apply filters
        if user_email:
            query = query.filter(AuditLog.user_email == user_email)
        if action:
            query = query.filter(AuditLog.action == action)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

        return logs, total
