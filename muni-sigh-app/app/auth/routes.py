# app/auth/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app import db
from app.models.user import User
from app.auth.forms import LoginForm, ChangePasswordForm, ChangeEmailForm
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


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    password_form = ChangePasswordForm()
    email_form = ChangeEmailForm()
    return render_template('auth/profile.html', user=user,
                           password_form=password_form, email_form=email_form)


@auth_bp.route('/profile/notifications', methods=['POST'])
@login_required
def profile_notifications():
    user = get_current_user()
    enabled = request.form.get('receive_email_notifications') == '1'
    user.receive_email_notifications = 1 if enabled else 0
    db.session.commit()
    flash('Preferencia de notificaciones actualizada.', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    user = get_current_user()
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not user.check_password(form.current_password.data):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('auth.profile'))
        if form.current_password.data == form.new_password.data:
            flash('La nueva contraseña no puede ser igual a la actual.', 'warning')
            return redirect(url_for('auth.profile'))
        user.set_password(form.new_password.data)
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('USER_PASSWORD_CHANGE', 'user', user.id,
                       {'user_id': user.id})
        except Exception:
            pass
        flash('Contraseña actualizada correctamente.', 'success')
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(err, 'danger')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile/change-email', methods=['POST'])
@login_required
def change_email():
    user = get_current_user()
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if not user.check_password(form.current_password.data):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('auth.profile'))
        new_email = form.new_email.data.strip().lower()
        if new_email == (user.email or '').lower():
            flash('El nuevo correo es igual al actual.', 'warning')
            return redirect(url_for('auth.profile'))
        existing = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing:
            flash('Ya existe un usuario con ese correo electrónico.', 'danger')
            return redirect(url_for('auth.profile'))
        old_email = user.email
        user.email = new_email
        db.session.commit()
        try:
            from app.services.audit_service import log_action
            log_action('USER_EMAIL_CHANGE', 'user', user.id,
                       {'from': old_email, 'to': new_email})
        except Exception:
            pass
        flash('Correo electrónico actualizado correctamente.', 'success')
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(err, 'danger')
    return redirect(url_for('auth.profile'))