# app/config.py
import os

# Cargar variables de entorno desde .env (sin dependencias externas)
try:
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(_env_path):
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith('#') or '=' not in _line:
                    continue
                _key, _val = _line.split('=', 1)
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _key not in os.environ:
                    os.environ[_key] = _val
except Exception:
    pass

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Seguridad y Base de Datos ──
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-contract-flow-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'data', 'contract_flow.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Paths ──
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # ── Datos Institucionales (Municipalidad) ──
    # Estas variables se inyectan en todas las plantillas vía context_processor.
    # Para desplegar en otra municipalidad, solo cambiar estos valores.
    MUNICIPALITY_NAME = os.environ.get('MUNICIPALITY_NAME') or 'Ilustre Municipalidad de Cunco'
    MUNICIPALITY_SHORT = os.environ.get('MUNICIPALITY_SHORT') or 'Municipalidad de Cunco'
    MUNICIPALITY_RUT = os.environ.get('MUNICIPALITY_RUT') or '69.191.000-8'
    MUNICIPALITY_ADDRESS = os.environ.get('MUNICIPALITY_ADDRESS') or 'Pedro Aguirre Cerda 600, Cunco.'
    MUNICIPALITY_REGION = os.environ.get('MUNICIPALITY_REGION') or 'Región de La Araucanía'
    MUNICIPALITY_PHONE = os.environ.get('MUNICIPALITY_PHONE') or ' +56 45 2200101'
    MUNICIPALITY_EMAIL = os.environ.get('MUNICIPALITY_EMAIL') or 'consulta@municipalidaddecunco.cl'
    MUNICIPALITY_UNIT_NAME = os.environ.get('MUNICIPALITY_UNIT_NAME') or 'Unidad de Personal Municipal'

    # ── Representante Legal (Alcalde) ──
    MAYOR_NAME = os.environ.get('MAYOR_NAME') or 'Cristian Moraga Lagos'
    MAYOR_RUT = os.environ.get('MAYOR_RUT') or '15.260.138-7'

    # ── Correo (Resend) ──
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
    RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL') or 'onboarding@resend.dev'
    RESEND_FROM_NAME = os.environ.get('RESEND_FROM_NAME') or 'Contract Flow - Municipalidad'

    # ── OTP (código de un solo uso) ──
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES') or 10)
    OTP_MAX_ATTEMPTS = int(os.environ.get('OTP_MAX_ATTEMPTS') or 5)
    OTP_LENGTH = int(os.environ.get('OTP_LENGTH') or 6)