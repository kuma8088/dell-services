"""
Domain management routes

Provides CRUD endpoints for domain management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.decorators import admin_required
from app.services import DomainService


# Create blueprint
bp = Blueprint('domains', __name__, url_prefix='/domains')


@bp.route('/')
@login_required
@admin_required
def list():
    """
    List all domains

    GET /domains
    """
    try:
        domains = DomainService.list_domains()

        return render_template(
            'domains/list.html',
            domains=domains
        )
    except Exception as e:
        flash(f'ドメイン一覧の取得に失敗しました: {str(e)}', 'danger')
        return render_template('domains/list.html', domains=[])


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """
    Create new domain

    GET /domains/new - Show create form
    POST /domains/new - Create domain
    """
    if request.method == 'GET':
        return render_template('domains/create.html')

    # POST request
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', 1024, type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Validation
        if not name:
            flash('ドメイン名は必須です。', 'warning')
            return redirect(url_for('domains.create'))

        # Create domain
        domain = DomainService.create_domain(
            name=name,
            description=description,
            default_quota=default_quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ドメイン {domain.name} を作成しました。', 'success')
        return redirect(url_for('domains.list'))

    except ValueError as e:
        flash(f'ドメイン作成に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('domains.create'))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('domains.create'))


@bp.route('/<int:domain_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(domain_id):
    """
    Edit domain

    GET /domains/<domain_id>/edit - Show edit form
    POST /domains/<domain_id>/edit - Update domain
    """
    domain = DomainService.get_domain_by_id(domain_id)
    if not domain:
        flash(f'ドメイン ID {domain_id} が見つかりません。', 'danger')
        return redirect(url_for('domains.list'))

    if request.method == 'GET':
        return render_template('domains/edit.html', domain=domain)

    # POST request
    try:
        description = request.form.get('description', '').strip()
        default_quota = request.form.get('default_quota', type=int)
        enabled = request.form.get('enabled', 'true') == 'true'

        # Update domain
        domain = DomainService.update_domain(
            domain_id=domain_id,
            description=description,
            default_quota=default_quota,
            enabled=enabled,
            admin_ip=request.remote_addr
        )

        flash(f'ドメイン {domain.name} を更新しました。', 'success')
        return redirect(url_for('domains.list'))

    except ValueError as e:
        flash(f'ドメイン更新に失敗しました: {str(e)}', 'danger')
        return redirect(url_for('domains.edit', domain_id=domain_id))
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('domains.edit', domain_id=domain_id))


@bp.route('/<int:domain_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(domain_id):
    """
    Delete domain

    POST /domains/<domain_id>/delete
    """
    domain = DomainService.get_domain_by_id(domain_id)
    if not domain:
        flash(f'ドメイン ID {domain_id} が見つかりません。', 'danger')
        return redirect(url_for('domains.list'))

    domain_name = domain.name

    try:
        DomainService.delete_domain(domain_id, admin_ip=request.remote_addr)
        flash(f'ドメイン {domain_name} を削除しました。', 'success')
    except ValueError as e:
        flash(f'ドメイン削除に失敗しました: {str(e)}', 'danger')
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')

    return redirect(url_for('domains.list'))


@bp.route('/<int:domain_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_status(domain_id):
    """
    Toggle domain enabled status

    POST /domains/<domain_id>/toggle
    """
    try:
        domain = DomainService.get_domain_by_id(domain_id)
        if not domain:
            flash(f'ドメイン ID {domain_id} が見つかりません。', 'danger')
            return redirect(url_for('domains.list'))

        # Toggle status
        new_status = not domain.enabled
        DomainService.toggle_domain_status(
            domain_id=domain_id,
            enabled=new_status,
            admin_ip=request.remote_addr
        )

        status_text = '有効化' if new_status else '無効化'
        flash(f'ドメイン {domain.name} を{status_text}しました。', 'success')

    except ValueError as e:
        flash(f'ステータス変更に失敗しました: {str(e)}', 'danger')
    except Exception as e:
        flash(f'予期しないエラーが発生しました: {str(e)}', 'danger')

    return redirect(url_for('domains.list'))
