# Lokasi file: D:/projek-yolo8/app/__init__.py

import os
from flask import Flask, current_app # Tambahkan current_app untuk logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config # Asumsi config.py ada di root project atau PYTHONPATH

# Import utilitas untuk memuat model YOLO
# Pastikan path import ini sesuai dengan struktur proyek Anda
# Contoh: from .utils.yolo_loader import load_yolo_model as init_yolo_model
# Jika utils.py ada di dalam direktori 'app'
from app.utils import load_yolo_model as init_yolo_model

# Inisialisasi ekstensi di luar factory agar bisa diimpor oleh modul lain jika diperlukan
# Namun, mereka akan dikonfigurasi dengan aplikasi di dalam factory
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()

# Konfigurasi Flask-Login
login_manager.login_view = 'login'  # Mengarahkan ke route 'login' di routes.py utama
login_manager.login_message = "Silakan login untuk mengakses halaman ini." # Pesan yang lebih deskriptif
login_manager.login_message_category = 'info'  # Kategori pesan flash

def create_app(config_class=Config):
    """
    Factory function untuk membuat dan mengkonfigurasi aplikasi Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi ekstensi dengan aplikasi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Pastikan folder UPLOAD_FOLDER ada dan dapat diakses
    # Ini penting untuk penanganan file upload
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder)
                app.logger.info(f"Folder '{upload_folder}' telah berhasil dibuat.")
            except OSError as e:
                app.logger.error(f"Gagal membuat folder '{upload_folder}': {e}")
                # Pertimbangkan apakah aplikasi harus gagal start jika folder tidak bisa dibuat
                # raise e 
        else:
            app.logger.info(f"Folder '{upload_folder}' sudah ada.")
    else:
        app.logger.warning("Peringatan: UPLOAD_FOLDER tidak terkonfigurasi. Fitur upload mungkin tidak berfungsi.")

    # Registrasi Blueprint (opsional, bisa tetap digunakan untuk bagian lain dari aplikasi)
    # Contoh:
    # from app.main.routes import main_bp # Jika punya blueprint untuk rute utama
    # app.register_blueprint(main_bp)
    #
    # Jika Anda memiliki blueprint lain, daftarkan di sini.
    # Untuk rute otentikasi, kita asumsikan ada di routes.py utama.

    with app.app_context():
        # Import model agar dikenali oleh Flask-Migrate dan SQLAlchemy
        from . import models  # models.py harus ada di dalam direktori 'app'

        # Import dan daftarkan rute utama aplikasi
        # Pastikan routes.py ada di dalam direktori 'app' dan tidak menyebabkan circular import
        # File ini akan berisi rute 'login' dan rute lainnya.
        from . import routes 
        
        # Memuat model YOLO saat aplikasi dimulai
        # Ini adalah operasi yang mungkin memakan waktu, jadi logging penting
        if app.config.get('LOAD_YOLO_ON_STARTUP', True): # Tambahkan konfigurasi untuk mengontrol pemuatan
            try:
                app.logger.info("Mencoba memuat model YOLO saat aplikasi dimulai...")
                init_yolo_model()  # Panggil fungsi untuk memuat model
                app.logger.info("Model YOLO berhasil dimuat dan siap digunakan.")
            except Exception as e:
                app.logger.error(f"Gagal memuat model YOLO saat aplikasi dimulai: {e}")
                # Anda bisa memutuskan apakah aplikasi harus gagal start atau lanjut tanpa model.
                # Jika model krusial, lebih baik hentikan aplikasi:
                # raise RuntimeError(f"Tidak dapat memuat model YOLO: {e}")
        else:
            app.logger.info("Pemuatan model YOLO saat startup dilewati sesuai konfigurasi.")
            
    @app.shell_context_processor
    def make_shell_context():
        """
        Menambahkan variabel ke dalam konteks shell Flask untuk kemudahan debugging.
        Akses dengan `flask shell`.
        """
        # Pastikan models.User ada atau ganti dengan model User Anda yang sebenarnya
        # Jika models.py belum memiliki User, Anda bisa menghapusnya dari sini sementara
        # atau pastikan model User sudah didefinisikan.
        user_model = getattr(models, 'User', None) 
        context = {'db': db}
        if user_model:
            context['User'] = user_model
        return context

    return app
