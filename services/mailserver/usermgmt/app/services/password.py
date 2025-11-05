"""
Password hashing and verification service using SHA512-CRYPT

This module provides Dovecot-compatible password hashing using SHA512-CRYPT algorithm.
The hash format is: {SHA512-CRYPT}$6$salt$hash
"""
import secrets
import string
from passlib.hash import sha512_crypt


def hash_password(password: str) -> str:
    """
    Hash a password using SHA512-CRYPT algorithm (Dovecot compatible)

    Args:
        password (str): Plain text password to hash

    Returns:
        str: Hashed password in format {SHA512-CRYPT}$6$salt$hash

    Raises:
        ValueError: If password is None
        TypeError: If password is not a string

    Example:
        >>> hashed = hash_password('mypassword123')
        >>> hashed.startswith('{SHA512-CRYPT}')
        True
    """
    if password is None:
        raise ValueError("Password cannot be None")

    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    # Generate SHA512-CRYPT hash with automatic salt generation
    # Rounds: 5000 (Dovecot standard)
    # Setting rounds explicitly to avoid implicit rounds parameter in hash
    hash_value = sha512_crypt.using(rounds=5000).hash(password)

    # Add Dovecot-compatible prefix
    return f"{{SHA512-CRYPT}}{hash_value}"


def verify_password(password: str, hash: str) -> bool:
    """
    Verify a password against a SHA512-CRYPT hash

    Args:
        password (str): Plain text password to verify
        hash (str): Hashed password in format {SHA512-CRYPT}$6$salt$hash

    Returns:
        bool: True if password matches hash, False otherwise

    Raises:
        ValueError: If password or hash is None
        TypeError: If password or hash is not a string

    Example:
        >>> hashed = hash_password('mypassword123')
        >>> verify_password('mypassword123', hashed)
        True
        >>> verify_password('wrongpassword', hashed)
        False
    """
    if password is None:
        raise ValueError("Password cannot be None")

    if hash is None:
        raise ValueError("Hash cannot be None")

    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    if not isinstance(hash, str):
        raise TypeError("Hash must be a string")

    # Handle invalid hash formats gracefully
    if not hash:
        return False

    # Remove Dovecot prefix if present
    hash_value = hash.replace('{SHA512-CRYPT}', '')

    # Verify using passlib
    try:
        return sha512_crypt.verify(password, hash_value)
    except (ValueError, TypeError):
        # Invalid hash format or other errors
        return False


def generate_random_password(length: int = 16) -> str:
    """
    Generate a secure random password

    Args:
        length (int): Length of the password to generate (default: 16)

    Returns:
        str: Random password containing uppercase, lowercase, digits, and symbols

    Raises:
        ValueError: If length is less than 4

    Example:
        >>> password = generate_random_password(16)
        >>> len(password)
        16
        >>> any(c.isupper() for c in password)
        True
        >>> any(c.islower() for c in password)
        True
        >>> any(c.isdigit() for c in password)
        True
    """
    if length < 4:
        raise ValueError("Password length must be at least 4 characters")

    # Character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = string.punctuation

    # Ensure at least one character from each set
    password_chars = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]

    # Fill remaining length with random characters from all sets
    all_chars = uppercase + lowercase + digits + symbols
    password_chars.extend(secrets.choice(all_chars) for _ in range(length - 4))

    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)
