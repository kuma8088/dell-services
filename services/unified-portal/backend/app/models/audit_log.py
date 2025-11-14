"""
Audit Log Model

SQLAlchemy ORM model for the existing 'audit_logs' table in mailserver_usermgmt database.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    """
    Audit Log Model

    Maps to the existing 'audit_logs' table in mailserver_usermgmt database.
    This table stores audit trail of all administrative actions.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False, comment="Action type (e.g., 'create', 'update', 'delete')")
    user_email = Column(String(255), nullable=False, index=True, comment="Email of affected user")
    admin_ip = Column(String(100), nullable=False, comment="IP address of admin performing action")
    details = Column(Text, comment="Additional details in JSON format")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_email='{self.user_email}')>"
