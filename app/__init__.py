from flask import Flask
# from flask_sqlalchemy import SQLAlchemy # Akan diaktifkan nanti
# from flask_migrate import Migrate # Akan diaktifkan nanti
# from flask_login import LoginManager # Akan diaktifkan nanti
from config import Config
import os

# db = SQLAlchemy() # Akan diaktifkan nanti
# migrate = Migrate() # Akan diaktifkan nanti
# login_manager = LoginManager() # Akan diaktifkan nanti
# login_manager.login_view = 'auth.login' # Tentukan halaman login untuk @login_required
# login_manager.login_message_category = 'info' # Kategori pesan flash

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan folder UPLOAD_FOLDER ada, jika tidak, buat folder tersebut
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    app.config['UPLOAD_FOLDER'] = upload_folder # Simpan path absolutnya

    # db.init_app(app) # Akan diaktifkan nanti
    # migrate.init_app(app, db) # Akan diaktifkan nanti
    # login_manager.init_app(app) # Akan diaktifkan nanti

    # Registrasi Blueprint (jika menggunakan)
    # from app.auth.routes import auth_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')

    # from app.main.routes import main_bp
    # app.register_blueprint(main_bp)

    # Untuk saat ini, kita akan mendaftarkan rute langsung dari app.routes
    from app import routes, models # Pastikan models diimpor agar dikenali oleh Flask-Migrate nanti

    return app