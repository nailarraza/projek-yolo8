import os
from dotenv import load_dotenv

# Tentukan path ke direktori dasar proyek
basedir = os.path.abspath(os.path.dirname(__file__))
# Muat variabel lingkungan dari file .env
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Konfigurasi dasar aplikasi."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-this-super-secret-key'
    FLASK_APP = os.environ.get('FLASK_APP')
    FLASK_ENV = os.environ.get('FLASK_ENV')

    # Konfigurasi Database MySQL
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_NAME = os.environ.get('DB_NAME')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Menonaktifkan fitur Flask-SQLAlchemy yang tidak dibutuhkan dan memakan resource

    # Konfigurasi Google API
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

    # Konfigurasi ESP32-CAM
    ESP32_CAM_URL = os.environ.get('ESP32_CAM_URL')

    # Path untuk menyimpan gambar yang diunggah/ditangkap
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    # Pastikan folder uploads ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# Anda bisa menambahkan konfigurasi lain seperti DevelopmentConfig, ProductionConfig, TestingConfig jika diperlukan
# class DevelopmentConfig(Config):
#     DEBUG = True

# class ProductionConfig(Config):
#     DEBUG = False
