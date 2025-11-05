"""
Authentication routes for login/logout functionality

Provides secure authentication endpoints with CSRF protection,
session management, and password verification.
"""
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required
from urllib.parse import urlparse, urljoin
from app.database import db
from app.models.user import User
from app.services.password import verify_password


# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def is_safe_url(target):
    """
    Check if the redirect target is safe (prevents open redirect vulnerabilities)

    Args:
        target (str): Target URL to validate

    Returns:
        bool: True if URL is safe (relative or same-host), False otherwise

    Example:
        >>> is_safe_url('/dashboard')
        True
        >>> is_safe_url('http://malicious.com')
        False
    """
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    # Ensure URL has no scheme/netloc or matches the current host
    return test_url.scheme in ('http', 'https', '') and \
           (ref_url.netloc == test_url.netloc or test_url.netloc == '')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login endpoint

    GET:  Display login form
    POST: Process login credentials and create session

    Form Parameters:
        email (str): User email address
        password (str): Plain text password

    Returns:
        GET:  Rendered login template
        POST: Redirect to dashboard or 'next' parameter on success
              Re-display login form on failure
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Validation
        if not email or not password:
            flash('メールアドレスとパスワードを入力してください。', 'error')
            return render_template('login.html'), 200

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists
        if not user:
            flash('メールアドレスまたはパスワードが正しくありません。', 'error')
            return render_template('login.html'), 200

        # Verify password
        if not verify_password(password, user.password_hash):
            flash('メールアドレスまたはパスワードが正しくありません。', 'error')
            return render_template('login.html'), 200

        # Check if user is enabled
        if not user.enabled:
            flash('アカウントが無効です。管理者にお問い合わせください。', 'error')
            return render_template('login.html'), 200

        # Check if user is admin (only admin users can access admin panel)
        if not user.is_admin:
            flash('管理者アカウントでログインしてください。', 'error')
            return render_template('login.html'), 200

        # Login successful - create session
        login_user(user, remember=True)

        # Handle 'next' parameter for redirect
        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)

        # Default redirect to dashboard
        return redirect(url_for('dashboard'))

    # GET request - display login form
    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout endpoint

    Destroys the current user session and redirects to login page.
    Requires active authentication (enforced by @login_required).

    Returns:
        Redirect to login page
    """
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))
