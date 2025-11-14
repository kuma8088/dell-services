"""Email sending service."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Service for sending emails via SMTP.

    Supports HTML and plain text emails with configurable SMTP settings.
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_from: str | None = None,
    ):
        """Initialize email service.

        Args:
            smtp_host: SMTP server host (defaults to settings)
            smtp_port: SMTP server port (defaults to settings)
            smtp_user: SMTP username (defaults to settings)
            smtp_password: SMTP password (defaults to settings)
            smtp_from: From email address (defaults to settings)
        """
        self.smtp_host = smtp_host or getattr(settings, "smtp_host", "localhost")
        self.smtp_port = smtp_port or getattr(settings, "smtp_port", 587)
        self.smtp_user = smtp_user or getattr(settings, "smtp_user", "")
        self.smtp_password = smtp_password or getattr(settings, "smtp_password", "")
        self.smtp_from = smtp_from or getattr(settings, "smtp_from", "noreply@example.com")

    def send_email(
        self,
        to: str | List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send an email.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            from_email: From email address (defaults to smtp_from)

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Prepare recipients
            recipients = [to] if isinstance(to, str) else to

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or self.smtp_from
            msg["To"] = ", ".join(recipients)

            # Attach plain text body
            msg.attach(MIMEText(body_text, "plain"))

            # Attach HTML body if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()

                # Authenticate if credentials provided
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent to {recipients}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_password_reset_email(
        self, to: str, username: str, reset_token: str, reset_url_base: str
    ) -> bool:
        """Send a password reset email.

        Args:
            to: Recipient email address
            username: Admin username
            reset_token: Password reset token
            reset_url_base: Base URL for reset page (e.g., https://admin.example.com/reset-password)

        Returns:
            True if email was sent successfully, False otherwise
        """
        reset_url = f"{reset_url_base}?token={reset_token}"

        subject = "Password Reset Request - Unified Portal"

        body_text = f"""
Hello {username},

You have requested to reset your password for the Unified Portal.

Please click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
Unified Portal Team
        """.strip()

        body_html = f"""
<html>
<body>
    <h2>Password Reset Request</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>You have requested to reset your password for the Unified Portal.</p>
    <p>Please click the button below to reset your password:</p>
    <p>
        <a href="{reset_url}"
           style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link in your browser:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p><em>This link will expire in 1 hour.</em></p>
    <p>If you did not request this password reset, please ignore this email.</p>
    <br>
    <p>Best regards,<br>Unified Portal Team</p>
</body>
</html>
        """.strip()

        return self.send_email(to, subject, body_text, body_html)

    def send_welcome_email(self, to: str, username: str, initial_password: str) -> bool:
        """Send a welcome email to a new admin user.

        Args:
            to: Recipient email address
            username: Admin username
            initial_password: Initial password

        Returns:
            True if email was sent successfully, False otherwise
        """
        subject = "Welcome to Unified Portal"

        body_text = f"""
Hello {username},

Welcome to the Unified Portal!

Your account has been created with the following credentials:

Username: {username}
Password: {initial_password}

For security reasons, please change your password after your first login.

Login URL: https://admin.example.com/login

Best regards,
Unified Portal Team
        """.strip()

        body_html = f"""
<html>
<body>
    <h2>Welcome to Unified Portal</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>Welcome to the Unified Portal! Your account has been created.</p>
    <h3>Login Credentials</h3>
    <ul>
        <li><strong>Username:</strong> {username}</li>
        <li><strong>Password:</strong> <code>{initial_password}</code></li>
    </ul>
    <p><em>For security reasons, please change your password after your first login.</em></p>
    <p>
        <a href="https://admin.example.com/login"
           style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
            Login Now
        </a>
    </p>
    <br>
    <p>Best regards,<br>Unified Portal Team</p>
</body>
</html>
        """.strip()

        return self.send_email(to, subject, body_text, body_html)


def get_email_service() -> EmailService:
    """Get email service instance.

    Returns:
        EmailService instance
    """
    return EmailService()
