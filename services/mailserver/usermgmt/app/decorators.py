"""Authorization decorators for route protection."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import abort, flash, redirect, url_for
from flask_login import current_user

F = TypeVar('F', bound=Callable[..., Any])


def admin_required(func: F) -> F:
    """Ensure the current user holds administrator privileges."""

    @wraps(func)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Check if user is authenticated (should be enforced by @login_required, but double-check)
        if not current_user.is_authenticated:
            flash('このページにアクセスするにはログインが必要です。', 'warning')
            return redirect(url_for('auth.login'))

        # Check if user is admin
        if not current_user.is_admin:
            flash('管理者権限が必要です。', 'danger')
            abort(403)

        # User is authenticated and admin, proceed
        return func(*args, **kwargs)

    return cast(F, decorated_function)
