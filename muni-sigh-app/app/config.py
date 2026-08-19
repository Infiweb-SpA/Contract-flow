# app/config.py
import os

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
    MUNICIPALITY_NAME = os.environ.get('MUNICIPALITY_NAME') or 'Ilustre Municipalidad de Freire'
    MUNICIPALITY_SHORT = os.environ.get('MUNICIPALITY_SHORT') or 'Municipalidad de Freire'
    MUNICIPALITY_RUT = os.environ.get('MUNICIPALITY_RUT') or '69.190.900-K'
    MUNICIPALITY_ADDRESS = os.environ.get('MUNICIPALITY_ADDRESS') or 'Pedro Camalá N° 85, Freire'
    MUNICIPALITY_REGION = os.environ.get('MUNICIPALITY_REGION') or 'Región de La Araucanía'
    MUNICIPALITY_PHONE = os.environ.get('MUNICIPALITY_PHONE') or '(45) 2 334 500'
    MUNICIPALITY_EMAIL = os.environ.get('MUNICIPALITY_EMAIL') or 'personalmunicipal@munifreire.cl'
    MUNICIPALITY_UNIT_NAME = os.environ.get('MUNICIPALITY_UNIT_NAME') or 'Unidad de Personal Municipal'

    # ── Representante Legal (Alcalde) ──
    MAYOR_NAME = os.environ.get('MAYOR_NAME') or 'José Antonio Colihuil Binimélis'
    MAYOR_RUT = os.environ.get('MAYOR_RUT') or '13.965.066-2'