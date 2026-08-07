# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    rut_or_email = StringField('RUT o Correo Electrónico', validators=[
        DataRequired(message='Ingrese su RUT o correo electrónico.')
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message='Ingrese su contraseña.')
    ])
    remember = BooleanField('Recordar sesión')
    submit = SubmitField('Iniciar Sesión')