# Lokasi file: D:/projek-yolo8/run.py

from app import create_app, db # Tambahkan db
from app.models import User, Detection # Tambahkan import model
from flask_migrate import MigrateCommand # Seharusnya tidak perlu, Migrate sudah dihandle di __init__

app = create_app()

# Konfigurasi Flask-Migrate (jika belum di __init__)
# migrate = Migrate(app, db) # Ini sudah ada di create_app

# Tambahkan shell context processor untuk kemudahan debugging
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Detection': Detection}

if __name__ == '__main__':
    # Pastikan UPLOAD_FOLDER dibuat sebelum aplikasi dijalankan (jika belum oleh create_app)
    # Ini sudah ditangani di dalam create_app
    # upload_dir = app.config.get('UPLOAD_FOLDER')
    # if upload_dir and not os.path.exists(upload_dir):
    #     os.makedirs(upload_dir)

    app.run(debug=True)
