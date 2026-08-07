import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Asegurar la creación del directorio data para la base SQLite
os.makedirs(DATA_DIR, exist_ok=True)

# Asegurar la creación del directorio de subidas
os.makedirs(os.path.join(BASE_DIR, 'app', 'static', 'uploads'), exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sigh-muni-clave-secreta-desarrollo-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(DATA_DIR, 'sigh_muni.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Directorio de almacenamiento local para PDFs subidos o creados
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    
    # Configuraciones para la subida y procesamiento de PDFs
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Límite de 16 MB por archivo PDF
    ALLOWED_EXTENSIONS = {'pdf'}