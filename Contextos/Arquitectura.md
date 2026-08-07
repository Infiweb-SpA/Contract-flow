# ARQUITECTURA DE PROYECTO Y ESTRUCTURA DE CARPETAS (FLASK + SQLITE)

Esta estructura define la arquitectura modular del proyecto `SIGH-MUNI`. Está optimizada para desarrollo directo en el entorno global (sin `venv`), con persistencia SQLite y soporte para migraciones automáticas mediante Flask-Migrate (Alembic).

---

## 1. Arbol de Directorios del Proyecto

```text
muni-sigh-app/
├── app/                        # Aplicación principal
│   ├── __init__.py             # Application Factory (create_app) y setup de Flask-Migrate / SQLAlchemy
│   ├── config.py               # Configuración de entornos (Desarrollo, Producción Railway, SQLite DB path)
│   ├── models/                 # Modelos SQLAlchemy / SQLite
│   │   ├── __init__.py
│   │   ├── user.py             # Modelo de Usuarios, Roles y Departamentos
│   │   ├── provider.py         # Modelo de Prestadores de Servicio
│   │   ├── contract.py         # Modelo de Contratos y Funciones
│   │   ├── payment.py          # Modelo de Pagos Mensuales y Checklists
│   │   └── audit.py            # Modelo de Bitácora de Auditoría
│   ├── auth/                   # Módulo de Autenticación y Autorización
│   │   ├── __init__.py
│   │   ├── routes.py           # Rutas: Login, Logout, Perfil
│   │   ├── utils.py            # Decoradores de roles (@role_required) y hashing de contraseñas
│   │   └── forms.py            # Formularios de autenticación
│   ├── routes/                 # Módulos / Blueprints del Negocio
│   │   ├── __init__.py         # Registro central de Blueprints
│   │   ├── dashboard.py        # Módulo 01: Dashboard e Indicadores
│   │   ├── contract_builder.py # Módulo 02A: Armador / Creador de Contratos
│   │   ├── ocr_ingestion.py    # Módulo 02B: Ingestión de PDFs y Motor PaddleOCR
│   │   ├── split_view.py       # Módulo 03: Vista Dividida (Split View Editor vs PDF)
│   │   └── payments.py         # Módulo 04: Circuito de Aprobación de Pagos Mensuales
│   ├── services/               # Lógica de Negocio y Servicios Internos
│   │   ├── __init__.py
│   │   ├── ocr_service.py      # Servicio de procesamiento OCR (PaddleOCR / pdfplumber)
│   │   ├── pdf_generator.py    # Generador de borradores PDF para contratos creados
│   │   └── audit_service.py    # Servicio centralizado de registros de auditoría
│   ├── static/                 # Archivos Estáticos Frontend
│   │   ├── css/                # Tailwind CSS estático / compilado
│   │   ├── js/                 # scripts Alpine.js / Vanilla JS (Split-view, dynamic forms)
│   │   └── uploads/            # Carpeta local temporal para almacenamiento de PDFs
│   └── templates/              # Plantillas Jinja2
│       ├── base.html           # Layout base con Tailwind CSS
│       ├── auth/               # Templates de Login
│       │   └── login.html
│       ├── dashboard/          # Templates de Dashboard
│       │   └── index.html
│       ├── contracts/          # Templates de Creador, Carga y Split-View
│       │   ├── create.html     # Formulario Creador de Contratos
│       │   ├── upload.html     # Carga de PDFs
│       │   └── split_view.html # Visor Dividido
│       └── payments/           # Templates del Circuito de Pagos
│           └── review.html
├── migrations/                 # Carpeta auto-generada por Flask-Migrate (Alembic)
│   ├── env.py
│   ├── script.py.mwas
│   └── versions/               # Archivos de versión de las migraciones SQL
├── data/                       # Base de Datos SQLite Persistente
│   └── sigh_muni.db            # Archivo SQLite (Ignorado en `.gitignore` o en volumen Railway)
├── app.py                      # Punto de entrada para ejecutar la app (`python app.py`)
├── requirements.txt            # Dependencias del proyecto para despliegue en Railway
├── Procfile                    # Archivo de inicio para Railway / Gunicorn
└── README.md                   # Instrucciones del proyecto
```

---

## 2. Implementación del Punto de Entrada y Migraciones

### `app/__init__.py` (Application Factory y Setup de Migraciones)
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicialización de Extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registro del Blueprint de Autenticación
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Registro de Blueprints Modulares de Rutas
    from app.routes import register_routes
    register_routes(app)

    return app
```

### `app.py` (Punto de Entrada Principal)
```python
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    # Creación automática de tablas en desarrollo si no existen
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

## 3. Comandos para Trabajar con Migraciones en SQLite

Como el desarrollo se realiza directamente en la instalación global de Python (sin entorno virtual), los comandos de migración se ejecutan directamente en la terminal:

1. **Inicializar el repositorio de migraciones (Solo la primera vez):**
   ```bash
   flask db init
   ```

2. **Generar una nueva migración tras modificar los modelos en `app/models/`:**
   ```bash
   flask db migrate -m "Descripcion del cambio en modelos"
   ```

3. **Aplicar los cambios a la base de datos SQLite (`data/sigh_muni.db`):**
   ```bash
   flask db upgrade
   ```

4. **Revertir la última migración (si es necesario):**
   ```bash
   flask db downgrade
   ```