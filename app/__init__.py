# Lokasi file: D:/projek-yolo8/app/__init__.py

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os

# Inisialisasi ekstensi
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login' # Halaman yang dituju jika user belum login dan mencoba akses halaman terproteksi
login_manager.login_message_category = 'info' # Kategori pesan flash untuk login_required
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi ekstensi dengan aplikasi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Pastikan folder UPLOAD_FOLDER ada
    # Ini dipindahkan dari config.py agar bisa diakses oleh app factory
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder and not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"Folder '{upload_folder}' telah dibuat.")
    elif not upload_folder:
        print("Peringatan: UPLOAD_FOLDER tidak terkonfigurasi.")


    # Import dan daftarkan blueprint atau rute di sini
    # Karena kita tidak menggunakan Blueprint, kita akan import rute langsung
    # Hindari circular imports dengan import di dalam fungsi atau di akhir file
    from app import routes, models # models perlu diimport agar dikenali oleh Flask-Migrate

    return app
