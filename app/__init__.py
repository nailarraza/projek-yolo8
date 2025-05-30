from flask import Flask
from config import Config
# Impor ekstensi Flask lainnya akan ditambahkan di sini nanti (misal: SQLAlchemy, Migrate, LoginManager)

# Pastikan folder upload ada
import os
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Inisialisasi ekstensi Flask di sini (misal: db.init_app(app))

    # Daftarkan Blueprint di sini
    # Contoh:
    # from app.main import bp as main_bp
    # app.register_blueprint(main_bp)

    # from app.auth import bp as auth_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')

    # Placeholder untuk rute sederhana, akan dipindahkan ke routes.py
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app

