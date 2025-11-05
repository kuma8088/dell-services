"""
User management routes

Provides CRUD endpoints for user management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.services import UserService, DomainService
from app.models import Domain
from sqlalchemy.exc import IntegrityError


# Create blueprint
bp = Blueprint('users', __name__, url_prefix='/users')


@bp.route('/')
@login_required
@admin_required
def list():
    """
    List all users

    GET /users
    GET /users?domain_id=1
    """
    domain_id = request.args.get('domain_id', type=int)

    try:
        users = UserService.list_users(domain_id=domain_id)
        domains = DomainService.list_domains()

        return render_template(
            'users/list.html',
            users=users,
            domains=domains,
            selected_domain_id=domain_id
        )
    except Exception as e:
        flash(f'ユーザ一覧の取得に失敗しました: {str(e)}', 'danger')
        return render_template('users/list.html', users=[], domains=[])


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """
    Create new user

    GET /users/new - Show create form
    POST /users/new - Create user
    """
    if request.method == 'GET':
        domains = DomainService.list_domains(enabled_only=True)
        return render_template('users/create.html', domains=domains)

    # POST request
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        domain_id = request.form.get('domain_id', type=int)
        quota = request.form.get('quota', 1024, type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Validation
        if not email:
            flash('メールアドレスは必須です。', 'warning')
            return redirect(url_for('users.create'))

        if not password:
            flash('パスワードは必須です。', 'warning')
            return redirect(url_for('users.create'))

        if not domain_id:
            flash('ドメインを選択してください。', 'warning')
            return redirect(url_for('users.create'))

        # Create user
        user = UserService.create_user(
            email=email,
            password=password,
            domain_id=domain_id,
            quota=quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ユーザ {user.email} を作成しました。', 'success')
        return redirect(url_for('users.list'))

    except ValueError as e:
        flash(f'ユーザ作成に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('users.create'))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('users.create'))


@bp.route('/<email>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(email):
    """
    Edit user

    GET /users/<email>/edit - Show edit form
    POST /users/<email>/edit - Update user
    """
    user = UserService.get_user_by_email(email)
    if not user:
        flash(f'ユーザ {email} が見つかりません。', 'danger')
        return redirect(url_for('users.list'))

    if request.method == 'GET':
        domains = DomainService.list_domains()
        return render_template('users/edit.html', user=user, domains=domains)

    # POST request
    try:
        quota = request.form.get('quota', type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Update user
        user = UserService.update_user(
            email=email,
            quota=quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ユーザ {user.email} を更新しました。', 'success')
        return redirect(url_for('users.list'))

    except ValueError as e:
        flash(f'ユーザ更新に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('users.edit', email=email))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('users.edit', email=email))


@bp.route('/<email>/delete', methods=['POST'])
@login_required
@admin_required
def delete(email):
    """
    Delete user

    POST /users/<email>/delete
    """
    try:
        UserService.delete_user(email, admin_ip=request.remote_addr)
        flash(f'ユーザ {email} を削除しました。', 'success')
    except ValueError as e:
        flash(f'ユーザ削除に失敗しました: {str(e)}', 'danger')
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')

    return redirect(url_for('users.list'))


@bp.route('/<email>/password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password(email):
    """
    Change user password

    GET /users/<email>/password - Show password change form
    POST /users/<email>/password - Change password
    """
    user = UserService.get_user_by_email(email)
    if not user:
        flash(f'ユーザ {email} が見つかりません。', 'danger')
        return redirect(url_for('users.list'))

    if request.method == 'GET':
        return render_template('users/password.html', user=user)

    # POST request
    try:
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not new_password:
            flash('新しいパスワードは必須です。', 'warning')
            return redirect(url_for('users.change_password', email=email))

        if new_password != confirm_password:
            flash('パスワードが一致しません。', 'warning')
            return redirect(url_for('users.change_password', email=email))

        # Change password
        UserService.change_password(
            email=email,
            new_password=new_password,
            admin_ip=request.remote_addr
        )

        flash(f'ユーザ {email} のパスワードを変更しました。', 'success')
        return redirect(url_for('users.list'))

    except ValueError as e:
        flash(f'パスワード変更に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('users.change_password', email=email))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('users.change_password', email=email))


@bp.route('/<email>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_status(email):
    """
    Toggle user enabled status

    POST /users/<email>/toggle
    """
    try:
        user = UserService.get_user_by_email(email)
        if not user:
            flash(f'ユーザ {email} が見つかりません。', 'danger')
            return redirect(url_for('users.list'))

        # Toggle status
        new_status = not user.enabled
        UserService.toggle_user_status(
            email=email,
            enabled=new_status,
            admin_ip=request.remote_addr
        )

        status_text = '有効化' if new_status else '無効化'
        flash(f'ユーザ {email} を{status_text}しました。', 'success')

    except ValueError as e:
        flash(f'ステータス変更に失敗しました: {str(e)}', 'danger')
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')

    return redirect(url_for('users.list'))
