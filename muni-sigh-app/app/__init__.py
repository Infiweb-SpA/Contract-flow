# app/__init__.py
import os
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Crear carpeta de subidas de PDFs si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Habilitar llaves foráneas explícitamente en SQLite
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    # ── Context Processor: Datos Institucionales ──────────────────────
    # Inyecta variables de municipalidad en TODAS las plantillas Jinja2.
    # Accesibles como {{ g.municipio_nombre }}, {{ g.mayor_name }}, etc.
    @app.before_request
    def load_municipal_globals():
        g.municipio_nombre = app.config.get('MUNICIPALITY_NAME', 'SIGH-MUNI')
        g.municipio_corto = app.config.get('MUNICIPALITY_SHORT', 'Municipalidad')
        g.municipio_rut = app.config.get('MUNICIPALITY_RUT', '')
        g.municipio_direccion = app.config.get('MUNICIPALITY_ADDRESS', '')
        g.municipio_region = app.config.get('MUNICIPALITY_REGION', '')
        g.municipio_telefono = app.config.get('MUNICIPALITY_PHONE', '')
        g.municipio_email = app.config.get('MUNICIPALITY_EMAIL', '')
        g.municipio_unidad = app.config.get('MUNICIPALITY_UNIT_NAME', '')
        g.mayor_name = app.config.get('MAYOR_NAME', '')
        g.mayor_rut = app.config.get('MAYOR_RUT', '')

    # Importación deferred de Blueprints
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes import register_routes
    register_routes(app)

    return app