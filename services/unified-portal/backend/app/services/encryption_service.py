"""Encryption service for sensitive data."""
from __future__ import annotations

import base64
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    The encryption key is loaded from configuration.
    """

    def __init__(self):
        """Initialize encryption service."""
        # Get encryption key from settings
        key = settings.encryption_key

        # Ensure key is properly formatted
        if not key:
            raise ValueError("Encryption key not configured")

        # If key is not base64-encoded, encode it
        try:
            base64.urlsafe_b64decode(key)
            self.key = key.encode() if isinstance(key, str) else key
        except Exception:
            # Generate a proper Fernet key from the provided string
            self.key = base64.urlsafe_b64encode(key.encode().ljust(32)[:32])

        self.cipher = Fernet(self.key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64-encoded)
        """
        try:
            plaintext_bytes = plaintext.encode("utf-8")
            encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted: Encrypted string (base64-encoded)

        Returns:
            Decrypted plaintext string
        """
        try:
            encrypted_bytes = encrypted.encode("utf-8")
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or corrupted data")
            raise ValueError("Failed to decrypt data: Invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key
        """
        return Fernet.generate_key().decode("utf-8")


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get encryption service singleton.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
