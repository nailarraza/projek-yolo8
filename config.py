# Lokasi file: D:/projek-yolo8/config.py
import os
from dotenv import load_dotenv

# Tentukan path ke direktori root proyek
basedir = os.path.abspath(os.path.dirname(__file__))

# Muat variabel lingkungan dari file .env
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess' # Akan kita generate nanti

    # Konfigurasi Database MySQL
    # Format: mysql+mysqlconnector://user:password@host/database_name
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+mysqlconnector://root:@localhost/projek_yolo8_db' # Sesuaikan jika user/password MySQL Anda berbeda
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Konfigurasi Model YOLO
    MODEL_PATH = os.path.join(basedir, 'models_yolo', 'model_oli_yolov8.pt') # Ganti 'model_oli_yolov8.pt' jika nama model Anda berbeda

    # Konfigurasi Google Gemini API
    GOOGLE_GEMINI_API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')

    # Konfigurasi Upload Gambar
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Pastikan folder upload ada
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)
