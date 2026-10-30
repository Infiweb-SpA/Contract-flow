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