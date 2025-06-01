# Lokasi file: D:/projek-yolo8/config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+mysqlconnector://root:@localhost/projek_yolo8_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MODEL_PATH = os.path.join(basedir, 'models_yolo', 'model_oli_yolov8.pt') # Pastikan nama model sesuai
    
    GOOGLE_GEMINI_API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')

    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Konfigurasi ESP32-CAM
    ESP32_CAM_BASE_URL = os.environ.get('ESP32_CAM_IP') # Tanpa slash di akhir
    ESP32_CAM_CAPTURE_URL = f"{ESP32_CAM_BASE_URL}/capture"
    ESP32_CAM_STREAM_URL = f"{ESP32_CAM_BASE_URL}/stream"

# Pastikan folder upload ada (sudah ada di __init__.py, tapi bisa juga di sini sebagai fallback)
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)
