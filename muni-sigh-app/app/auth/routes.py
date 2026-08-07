# app/auth/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app import db
from app.models.user import User
from app.auth.forms import LoginForm
from app.auth.utils import login_required, get_current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.rut_or_email.data.strip()
        password = form.password.data

        # Búsqueda por RUT o Email
        user = User.query.filter(
            (User.rut == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            if user.is_active != 1:
                flash('Su cuenta se encuentra desactivada. Contacte al administrador.', 'danger')
                return redirect(url_for('auth.login'))

            # Guardar datos en la sesión Flask
            session.clear()
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['user_role'] = user.role
            session['user_rut'] = user.rut

            flash(f'Bienvenido(a) al sistema, {user.first_name}.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Credenciales inválidas. Verifique su RUT/Correo y contraseña.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    return render_template('auth/profile.html', user=user)