"""
Audit Log model for mailserver usermgmt application
"""
from app.database import db
from datetime import datetime


class AuditLog(db.Model):
    """
    Audit Log model for tracking user management operations

    Records all CREATE, UPDATE, DELETE, and PASSWORD_CHANGE actions
    """
    __tablename__ = 'audit_logs'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Action type (ENUM: create, update, delete, password_change)
    action = db.Column(db.Enum('create', 'update', 'delete', 'password_change', name='action_enum'), nullable=False, index=True)

    # Affected user email
    user_email = db.Column(db.String(255), nullable=False, index=True)

    # IP address of admin who performed the action
    admin_ip = db.Column(db.String(45), nullable=True)

    # Additional details (JSON or text)
    details = db.Column(db.Text, nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        """String representation of AuditLog"""
        return f'<AuditLog {self.action} on {self.user_email} from {self.admin_ip}>'
