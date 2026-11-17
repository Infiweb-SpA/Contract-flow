# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp

class LoginForm(FlaskForm):
    rut_or_email = StringField('RUT o Correo Electrónico', validators=[
        DataRequired(message='Ingrese su RUT o correo electrónico.')
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message='Ingrese su contraseña.')
    ])
    remember = BooleanField('Recordar sesión')
    submit = SubmitField('Iniciar Sesión')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña actual', validators=[
        DataRequired(message='Ingrese su contraseña actual.')
    ])
    new_password = PasswordField('Nueva contraseña', validators=[
        DataRequired(message='Ingrese la nueva contraseña.'),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.')
    ])
    confirm_password = PasswordField('Confirmar nueva contraseña', validators=[
        DataRequired(message='Confirme la nueva contraseña.'),
        EqualTo('new_password', message='Las contraseñas no coinciden.')
    ])
    submit_password = SubmitField('Cambiar contraseña')


class ChangeEmailForm(FlaskForm):
    new_email = StringField('Nuevo correo electrónico', validators=[
        DataRequired(message='Ingrese el nuevo correo electrónico.'),
        Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Ingrese un correo electrónico válido.')
    ])
    current_password = PasswordField('Contraseña actual', validators=[
        DataRequired(message='Ingrese su contraseña actual.')
    ])
    submit_email = SubmitField('Cambiar correo')