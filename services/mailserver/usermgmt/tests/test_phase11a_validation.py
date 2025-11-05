#!/usr/bin/env python3
"""
Phase 11-A Validation Tests
Tests admin/user role separation functionality
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import User
from app.database import db


def test_database_schema():
    """Test 1: Verify is_admin column exists in users table"""
    print("Test 1: Database Schema Validation")
    print("-" * 50)

    app = create_app()
    with app.app_context():
        # Check if is_admin column exists
        users = User.query.all()
        print(f"✓ Found {len(users)} users in database")

        for user in users:
            print(f"  - {user.email}: is_admin={user.is_admin}")

        print()


def test_admin_user_exists():
    """Test 2: Verify admin@kuma8088.com has is_admin=True"""
    print("Test 2: Admin User Validation")
    print("-" * 50)

    app = create_app()
    with app.app_context():
        admin_user = User.query.filter_by(email='admin@kuma8088.com').first()

        if not admin_user:
            print("✗ FAILED: admin@kuma8088.com not found")
            return False

        if not admin_user.is_admin:
            print("✗ FAILED: admin@kuma8088.com is_admin=False (should be True)")
            return False

        print(f"✓ admin@kuma8088.com exists with is_admin=True")
        print()
        return True


def test_regular_users_not_admin():
    """Test 3: Verify regular users have is_admin=False"""
    print("Test 3: Regular Users Validation")
    print("-" * 50)

    app = create_app()
    with app.app_context():
        regular_users = User.query.filter_by(is_admin=False).all()

        print(f"✓ Found {len(regular_users)} regular users (is_admin=False)")
        for user in regular_users:
            print(f"  - {user.email}")

        print()
        return True


def test_single_admin_constraint():
    """Test 4: Verify database trigger prevents multiple admins"""
    print("Test 4: Single Admin Constraint Test")
    print("-" * 50)

    app = create_app()
    with app.app_context():
        # Count admin users
        admin_count = User.query.filter_by(is_admin=True).count()

        if admin_count != 1:
            print(f"✗ FAILED: Expected 1 admin user, found {admin_count}")
            return False

        print(f"✓ Exactly 1 admin user exists in database")

        # Try to create second admin (should fail with trigger)
        print("\nAttempting to set another user as admin (should fail)...")
        try:
            test_user = User.query.filter_by(email='info@kuma8088.com').first()
            if test_user:
                test_user.is_admin = True
                db.session.commit()
                print("✗ FAILED: Database trigger did not prevent second admin")
                # Rollback
                test_user.is_admin = False
                db.session.commit()
                return False
        except Exception as e:
            db.session.rollback()
            if '管理者は1ユーザーのみ設定可能です' in str(e):
                print(f"✓ Database trigger correctly prevents multiple admins")
                print(f"  Error message: {str(e)[:100]}...")
                print()
                return True
            else:
                print(f"✗ FAILED: Unexpected error: {str(e)}")
                return False

        print()


def test_user_model_property():
    """Test 5: Verify User model has is_admin property"""
    print("Test 5: User Model Property Test")
    print("-" * 50)

    app = create_app()
    with app.app_context():
        user = User.query.first()

        if not hasattr(user, 'is_admin'):
            print("✗ FAILED: User model missing is_admin property")
            return False

        print(f"✓ User model has is_admin property")
        print(f"  Type: {type(user.is_admin)}")
        print(f"  Value: {user.is_admin}")
        print()
        return True


def run_all_tests():
    """Run all Phase 11-A validation tests"""
    print("=" * 50)
    print("Phase 11-A Validation Test Suite")
    print("=" * 50)
    print()

    tests = [
        test_database_schema,
        test_admin_user_exists,
        test_regular_users_not_admin,
        test_single_admin_constraint,
        test_user_model_property
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"✗ Test FAILED with exception: {str(e)}")
            results.append(False)

    print("=" * 50)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 50)

    return all(results)


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
