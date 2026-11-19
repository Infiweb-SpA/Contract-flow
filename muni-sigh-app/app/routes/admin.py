# -*- coding: utf-8 -*-
"""
Administración de roles y permisos granulares (RBAC).
Exclusivo para SUPERADMIN.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.auth.utils import login_required, role_required
from app.models import User, Role, Permission, RolePermission

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Roles base del sistema (no se pueden eliminar)
BASE_ROLES = {'SUPERADMIN', 'ADMIN_RRHH', 'JEFE_DEPTO', 'FINANZAS_CONTROL', 'AUDITOR', 'ALCALDE'}


def _role_permission_map():
    """Devuelve {nombre_rol: [nombres de permiso]} para todos los roles."""
    mapping = {}
    for rp in RolePermission.query.all():
        mapping.setdefault(rp.role_name, []).append(rp.permission.name)
    for role in Role.query.all():
        mapping.setdefault(role.name, [])
    # Incluye roles presentes en usuarios aunque falten en la tabla roles
    for (role_name,) in db.session.query(User.role).distinct().all():
        mapping.setdefault(role_name, [])
    return mapping


# =============================================================================
# ROLES
# =============================================================================
@admin_bp.route('/roles')
@login_required
@role_required('SUPERADMIN')
def roles():
    mapping = _role_permission_map()
    perm_labels = {p.name: (p.description or p.name) for p in Permission.query.all()}
    role_rows = []
    for role in Role.query.order_by(Role.name).all():
        role_rows.append({
            'name': role.name,
            'description': role.description,
            'is_base': bool(role.is_base),
            'permissions': sorted(mapping.get(role.name, [])),
        })
    # Roles existentes solo en usuarios (sin fila en `roles`)
    known = {r['name'] for r in role_rows}
    for role_name in sorted(mapping.keys()):
        if role_name not in known:
            role_rows.append({
                'name': role_name,
                'description': None,
                'is_base': role_name in BASE_ROLES,
                'permissions': sorted(mapping[role_name]),
            })
    return render_template('admin/roles.html', role_rows=role_rows,
                           perm_labels=perm_labels,
                           perm_count=Permission.query.count())


@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def create_role():
    if request.method == 'POST':
        name = (request.form.get('role_name') or '').strip().upper().replace(' ', '_')
        description = (request.form.get('description') or '').strip() or None

        if not name:
            flash('El nombre del rol es obligatorio.', 'danger')
            return redirect(url_for('admin.roles'))
        if Role.query.filter_by(name=name).first():
            flash(f'El rol "{name}" ya existe.', 'warning')
            return redirect(url_for('admin.roles'))

        db.session.add(Role(name=name, description=description, is_base=0))
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('ROLE_CREATE', 'role', None, {'name': name})
        except Exception:
            pass
        flash(f'Rol "{name}" creado correctamente.', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/create_role.html')


@admin_bp.route('/roles/<role_name>/assign', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def assign_permissions(role_name):
    if not Role.query.filter_by(name=role_name).first() and not User.query.filter_by(role=role_name).first():
        flash(f'El rol "{role_name}" no existe.', 'danger')
        return redirect(url_for('admin.roles'))

    if request.method == 'POST':
        selected = request.form.getlist('permission')
        valid_names = {p.name for p in Permission.query.all()}
        selected = [name for name in selected if name in valid_names]

        RolePermission.query.filter_by(role_name=role_name).delete()
        db.session.flush()
        perm_by_name = {p.name: p for p in Permission.query.filter(Permission.name.in_(selected)).all()}
        for name in selected:
            perm = perm_by_name.get(name)
            if perm:
                db.session.add(RolePermission(role_name=role_name, permission_id=perm.id))
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('ROLE_PERMISSIONS_UPDATE', 'role', None, {'role': role_name, 'permissions': selected})
        except Exception:
            pass
        flash(f'Permisos de "{role_name}" actualizados.', 'success')
        return redirect(url_for('admin.roles'))

    all_perms = Permission.query.order_by(Permission.module, Permission.name).all()
    assigned_names = {rp.permission.name for rp in RolePermission.query.filter_by(role_name=role_name).all()}
    return render_template('admin/assign_permissions.html',
                           role_name=role_name,
                           all_perms=all_perms,
                           assigned_names=assigned_names)


@admin_bp.route('/roles/<role_name>/delete', methods=['POST'])
@login_required
@role_required('SUPERADMIN')
def delete_role(role_name):
    role = Role.query.filter_by(name=role_name).first()
    if role_name in BASE_ROLES or (role and role.is_base):
        flash('Los roles base del sistema no se pueden eliminar.', 'danger')
        return redirect(url_for('admin.roles'))
    if User.query.filter_by(role=role_name).first():
        flash(f'No se puede eliminar "{role_name}": hay usuarios que lo tienen asignado.', 'danger')
        return redirect(url_for('admin.roles'))

    RolePermission.query.filter_by(role_name=role_name).delete()
    if role:
        db.session.delete(role)
    db.session.commit()
    try:
        from app.services.audit_service import log_action
        log_action('ROLE_DELETE', 'role', None, {'name': role_name})
    except Exception:
        pass
    flash(f'Rol "{role_name}" eliminado.', 'success')
    return redirect(url_for('admin.roles'))


# =============================================================================
# USUARIOS (gestión + contraseñas)
# =============================================================================
import secrets


def _generate_password(length=12):
    """Genera una contraseña legible: letras + dígitos (sin caracteres ambíguos)."""
    alphabet = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@admin_bp.route('/users')
@login_required
@role_required('SUPERADMIN')
def users():
    all_users = User.query.order_by(User.role, User.last_name).all()
    from app.models.user import Department
    departments = Department.query.order_by(Department.code).all()
    role_names = [r.name for r in Role.query.order_by(Role.name).all()]
    return render_template('admin/users.html',
                           users=all_users,
                           departments=departments,
                           role_names=role_names)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@role_required('SUPERADMIN')
def users_create():
    from app.models.user import Department

    rut = (request.form.get('rut') or '').strip().upper()
    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    role = (request.form.get('role') or '').strip()
    department_id = request.form.get('department_id', type=int)
    password_mode = request.form.get('password_mode', 'auto')
    manual_password = (request.form.get('password') or '').strip()

    if not all([rut, first_name, last_name, email, role]):
        flash('Complete todos los campos obligatorios.', 'danger')
        return redirect(url_for('admin.users'))
    if User.query.filter_by(email=email).first() or User.query.filter_by(rut=rut).first():
        flash('Ya existe un usuario con ese RUT o email.', 'danger')
        return redirect(url_for('admin.users'))

    if password_mode == 'manual':
        if len(manual_password) < 8:
            flash('La contraseña manual debe tener al menos 8 caracteres.', 'danger')
            return redirect(url_for('admin.users'))
        password = manual_password
    else:
        password = _generate_password()

    user = User(rut=rut, first_name=first_name, last_name=last_name, email=email,
                role=role, department_id=department_id if department_id else None,
                is_active=1)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    try:
        from app.services.audit_service import log_action
        log_action('USER_CREATE', 'user', user.id, {'rut': rut, 'role': role, 'email': email})
    except Exception:
        pass
    flash(f'Usuario {first_name} {last_name} creado.', 'success')
    return redirect(url_for('admin.users_password', user_id=user.id, generated=password))


@admin_bp.route('/users/<int:user_id>/password', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def users_password(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        password_mode = request.form.get('password_mode', 'auto')
        manual_password = (request.form.get('password') or '').strip()

        if password_mode == 'manual':
            if len(manual_password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
                return render_template('admin/users_password.html', user=user)
            password = manual_password
        else:
            password = _generate_password()

        user.set_password(password)
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('USER_PASSWORD_RESET', 'user', user.id, {'by_admin': True})
        except Exception:
            pass
        return render_template('admin/users_password.html', user=user,
                               new_password=password)

    generated = request.args.get('generated')
    return render_template('admin/users_password.html', user=user,
                           new_password=generated)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('SUPERADMIN')
def users_toggle(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = 0 if user.is_active else 1
    db.session.commit()
    try:
        from app.services.audit_service import log_action
        log_action('USER_TOGGLE', 'user', user.id, {'is_active': user.is_active})
    except Exception:
        pass
    flash(f'Usuario {"activado" if user.is_active else "desactivado"}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/notifications', methods=['POST'])
@login_required
@role_required('SUPERADMIN')
def users_notifications(user_id):
    user = User.query.get_or_404(user_id)
    user.receive_email_notifications = 0 if user.receive_email_notifications else 1
    db.session.commit()
    try:
        from app.services.audit_service import log_action
        log_action('USER_NOTIFICATION_PREF', 'user', user.id, {'receive_email_notifications': user.receive_email_notifications})
    except Exception:
        pass
    flash(f'Notificaciones {"activadas" if user.receive_email_notifications else "desactivadas"} para {user.full_name}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/notification-events', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def users_notification_events(user_id):
    from app.services.notification_service import NOTIFICATION_EVENTS, get_disabled_actions, set_disabled_actions
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        disabled = set()
        for action, _label, _mod in NOTIFICATION_EVENTS:
            # Si el checkbox NO está marcado, se desactiva
            if not request.form.get(f'evt_{action}'):
                disabled.add(action)
        set_disabled_actions(user, disabled)
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('USER_NOTIFICATION_PREF', 'user', user.id, {'disabled': sorted(disabled)})
        except Exception:
            pass
        flash(f'Preferencias de notificación actualizadas para {user.full_name}.', 'success')
        return redirect(url_for('admin.users'))

    disabled = get_disabled_actions(user)
    # Agrupar por módulo
    grouped = {}
    for action, label, module in NOTIFICATION_EVENTS:
        grouped.setdefault(module, []).append((action, label, action not in disabled))
    return render_template('admin/notification_events.html', user=user, grouped=grouped)


# =============================================================================
# PERMISOS
# =============================================================================
@admin_bp.route('/permissions')
@login_required
@role_required('SUPERADMIN')
def permissions():
    perms = Permission.query.order_by(Permission.module, Permission.name).all()
    return render_template('admin/permissions.html', permissions=perms)


@admin_bp.route('/permissions/create', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def create_permission():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip() or None
        module = (request.form.get('module') or 'general').strip()

        if not name:
            flash('El nombre del permiso es obligatorio.', 'danger')
            return redirect(url_for('admin.permissions'))
        if Permission.query.filter_by(name=name).first():
            flash(f'El permiso "{name}" ya existe.', 'warning')
            return redirect(url_for('admin.permissions'))

        db.session.add(Permission(name=name, description=description, module=module))
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('PERMISSION_CREATE', 'permission', None, {'name': name, 'module': module})
        except Exception:
            pass
        flash(f'Permiso "{name}" creado correctamente.', 'success')
        return redirect(url_for('admin.permissions'))

    return render_template('admin/create_permission.html')