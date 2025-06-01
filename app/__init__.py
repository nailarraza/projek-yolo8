from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os
import logging # Untuk logging

# Inisialisasi ekstensi
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Rute yang akan diarahkan jika pengguna belum login & mencoba akses halaman terproteksi
login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
login_manager.login_message_category = 'info' # Kategori pesan flash Bootstrap

# Setup logging dasar
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi ekstensi dengan aplikasi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Pastikan folder UPLOAD_FOLDER ada, jika tidak, buat folder tersebut
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    if not os.path.exists(upload_folder):
        try:
            os.makedirs(upload_folder)
            app.logger.info(f"Folder uploads berhasil dibuat di {upload_folder}")
        except OSError as e:
            app.logger.error(f"Gagal membuat folder uploads di {upload_folder}: {e}")
    app.config['UPLOAD_FOLDER'] = upload_folder # Simpan path absolutnya

    # Registrasi Blueprint
    # Kita akan membuat blueprint untuk autentikasi (auth) dan fitur utama (main)
    from app.routes import auth_bp, main_bp # Akan dibuat nanti
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp) # Tanpa prefix untuk rute utama

    # Rute untuk favicon (opsional tapi baik untuk menghindari error 404)
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                           'favicon.ico', mimetype='image/vnd.microsoft.icon')

    app.logger.info("Aplikasi Flask berhasil dibuat dan dikonfigurasi.")
    return app