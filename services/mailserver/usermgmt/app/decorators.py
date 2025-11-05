"""
Authorization decorators for route protection

Provides decorators to restrict access based on user roles
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator to require admin privileges for a route

    Usage:
        @bp.route('/admin-only')
        @login_required
        @admin_required
        def admin_only_view():
            return "Admin content"

    Behavior:
        - If user not authenticated: redirect to login
        - If user not admin: flash error and return 403 Forbidden
        - If user is admin: proceed to route

    Args:
        f: The view function to decorate

    Returns:
        Decorated function that checks admin privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated (should be handled by @login_required, but double-check)
        if not current_user.is_authenticated:
            flash('このページにアクセスするにはログインが必要です。', 'warning')
            return redirect(url_for('auth.login'))

        # Check if user is admin
        if not current_user.is_admin:
            flash('管理者権限が必要です。', 'danger')
            abort(403)

        # User is authenticated and admin, proceed
        return f(*args, **kwargs)

    return decorated_function
