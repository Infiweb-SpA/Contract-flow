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
            if user_role not in allowed_roles and 'SUPERADMIN' not in allowed_roles and user_role != 'SUPERADMIN':
                flash('No tienes permisos suficientes para acceder a este módulo.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Obtiene el objeto del usuario actual en la sesión activa."""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None