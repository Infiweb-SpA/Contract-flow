# app/auth/utils.py
from functools import wraps
from flask import session, redirect, url_for, flash, request, g
from app.models.user import User

def login_required(f):
    """Decorador que exige estar autenticado para acceder a la ruta."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta sección.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Decorador que exige tener al menos uno de los roles autorizados."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('user_role')
            if user_role != 'SUPERADMIN' and user_role not in allowed_roles:
                flash('No tienes permisos suficientes para acceder a este módulo.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(*permission_names):
    """Decorador que exige tener al menos uno de los permisos asignados al rol del usuario.
    
    Complementa a @role_required: verifica si el rol del usuario (session['user_role'])
    tiene alguno de los permisos solicitados en la tabla role_permissions.
    
    Ejemplo de uso:
        @permission_required('create_contract')
        @permission_required('edit_decree', 'delete_decree')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))

            user_role = session.get('user_role')

            # SUPERADMIN siempre tiene todos los permisos
            if user_role == 'SUPERADMIN':
                return f(*args, **kwargs)

            # Consultar permisos asignados al rol del usuario
            from app.models.permission import RolePermission, Permission
            user_permissions = set(
                p.name for p in Permission.query.join(RolePermission, Permission.id == RolePermission.permission_id)
                .filter(RolePermission.role_name == user_role).all()
            )

            if not any(perm in user_permissions for perm in permission_names):
                flash('No tienes el permiso necesario para esta acción.', 'danger')
                return redirect(url_for('dashboard.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Obtiene el objeto del usuario actual en la sesión activa."""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None