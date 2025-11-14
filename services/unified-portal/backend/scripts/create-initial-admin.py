#!/usr/bin/env python3
"""
Script: create-initial-admin.py
Purpose: Create the initial admin user for Unified Portal
Usage: python3 create-initial-admin.py
Date: 2025-11-14
"""

import sys
import os
from pathlib import Path
from getpass import getpass

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_initial_admin():
    """Create the initial admin user."""
    print("=" * 60)
    print("Unified Portal - Initial Admin User Creation")
    print("=" * 60)
    print()

    # Get database credentials from environment
    db_host = os.getenv("DB_HOST", "172.20.0.60")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "usermgmt")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME", "unified_portal")

    if not db_password:
        print("ERROR: DB_PASSWORD environment variable not set")
        print()
        print("Please set DB_PASSWORD before running this script:")
        print("  export DB_PASSWORD='your-database-password'")
        sys.exit(1)

    # Collect admin user information
    print("Enter admin user details:")
    print()

    username = input("Username (default: admin): ").strip() or "admin"
    email = input("Email: ").strip()

    while not email:
        print("Email is required")
        email = input("Email: ").strip()

    full_name = input("Full name (optional): ").strip() or None

    password = getpass("Password: ")
    password_confirm = getpass("Confirm password: ")

    if password != password_confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters")
        sys.exit(1)

    is_superuser_input = input("Is superuser? (y/N): ").strip().lower()
    is_superuser = is_superuser_input in ["y", "yes"]

    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Username: {username}")
    print(f"  Email: {email}")
    print(f"  Full name: {full_name or '(not set)'}")
    print(f"  Superuser: {is_superuser}")
    print("=" * 60)
    print()

    confirm = input("Create this user? (y/N): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Cancelled")
        sys.exit(0)

    # Hash password
    print()
    print("Hashing password...")
    password_hash = hash_password(password)

    # Connect to database
    print("Connecting to database...")
    database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    try:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if user already exists
        result = session.execute(
            text("SELECT id FROM admin_users WHERE username = :username OR email = :email"),
            {"username": username, "email": email}
        )
        existing_user = result.fetchone()

        if existing_user:
            print(f"ERROR: User with username '{username}' or email '{email}' already exists")
            session.close()
            sys.exit(1)

        # Insert admin user
        print("Creating admin user...")
        session.execute(
            text("""
                INSERT INTO admin_users (username, email, password_hash, full_name, is_active, is_superuser)
                VALUES (:username, :email, :password_hash, :full_name, :is_active, :is_superuser)
            """),
            {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "is_active": True,
                "is_superuser": is_superuser,
            }
        )
        session.commit()

        print()
        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print()
        print("You can now login to the Unified Portal:")
        print(f"  URL: https://admin.kuma8088.com/login")
        print(f"  Username: {username}")
        print(f"  Password: (the password you entered)")
        print()

        session.close()

    except Exception as e:
        print(f"ERROR: Failed to create admin user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_initial_admin()
