import os
from dotenv import load_dotenv

# Tentukan path ke direktori root proyek
basedir = os.path.abspath(os.path.dirname(__file__))

# Muat variabel lingkungan dari file .env
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Set Flask configuration variables from .env file."""

    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess' # Default jika tidak ada di .env
    FLASK_APP = os.environ.get('FLASK_APP')
    FLASK_ENV = os.environ.get('FLASK_ENV')
    DEBUG = os.environ.get('DEBUG') == 'True'

    # Database Config (Contoh untuk MySQL)
    # Format: mysql+pymysql://user:password@host/dbname
    # Kita akan menggunakan SQLAlchemy nanti, jadi format URI-nya akan seperti ini.
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_NAME = os.environ.get('DB_NAME')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Menonaktifkan fitur Flask-SQLAlchemy yang tidak dibutuhkan dan memakan resource

    # Google API Key
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

    # ESP32-CAM IP Address
    ESP32_CAM_IP = os.environ.get('ESP32_CAM_IP')

    # Path untuk menyimpan gambar yang diunggah/ditangkap
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads') # Kita akan buat folder 'uploads' nanti
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
