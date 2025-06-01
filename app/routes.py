# Lokasi file: D:/projek-yolo8/app/routes.py

from flask import render_template, url_for, flash, redirect, request, current_app, jsonify
from app import db, bcrypt, create_app # Hapus create_app jika tidak digunakan langsung di sini
from app.forms import RegistrationForm, LoginForm
from app.models import User, Detection # Pastikan Detection diimport
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime # Untuk _footer.html

# Dapatkan instance aplikasi saat ini
# Ini lebih baik daripada mengimpor 'app' secara langsung jika menggunakan application factory
# Namun, karena kita tidak menggunakan Blueprint, kita perlu cara untuk mendapatkan 'app'
# Solusi: Gunakan current_app dari Flask, atau daftarkan rute dalam fungsi create_app

# Jika Anda tidak menggunakan blueprint, Anda perlu instance 'app' untuk decorator @app.route
# Salah satu cara adalah dengan mengimpor 'app' dari __init__ jika Anda tidak menggunakan factory
# atau memodifikasi create_app untuk mendaftarkan rute.

# Untuk pendekatan non-blueprint dengan app factory, rute biasanya didefinisikan
# dan kemudian diimpor ke dalam create_app.
# Kita akan menggunakan current_app jika memungkinkan, atau perlu penyesuaian.

# Mari kita asumsikan kita akan mengimpor 'routes' ke dalam 'create_app'
# sehingga 'app' context tersedia.
# Untuk sementara, kita akan coba definisikan rute seolah-olah 'app' sudah ada.
# Ini akan berfungsi jika 'from app import routes' ada di 'create_app' *setelah* app dibuat.

# Mendapatkan app instance dari create_app untuk decorator rute
# Ini adalah cara yang sedikit berbeda jika tidak menggunakan blueprint
# Biasanya, blueprint yang di-register ke app.
# Karena permintaan adalah *tanpa* blueprint, kita akan definisikan rute
# dan pastikan modul ini diimpor dalam `create_app` setelah `app` dibuat.

# Untuk akses ke 'app' context seperti app.route, kita perlu instance aplikasi.
# Kita akan mengimpor 'app' dari modul utama jika tidak menggunakan blueprint.
# Namun, ini bisa menyebabkan circular import jika 'app' juga mengimpor 'routes'.

# Solusi yang lebih bersih tanpa blueprint adalah dengan membuat instance Flask
# di __init__.py dan mengimpornya di sini.
# app = Flask(__name__) # Ini akan membuat instance baru, bukan yang dari factory. JANGAN LAKUKAN INI.

# Mari kita coba cara standar dengan mengimpor modul ini ke create_app
# dan Flask akan menangani routingnya.

@current_app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@current_app.route("/")
@current_app.route("/home")
def home():
    return render_template('dashboard.html', title='Home') # Arahkan ke dashboard jika sudah login, atau halaman landing jika belum

@current_app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Akun Anda telah berhasil dibuat! Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@current_app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login berhasil!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login gagal. Periksa kembali email dan password Anda.', 'danger')
    return render_template('login.html', title='Login', form=form)

@current_app.route("/logout")
def logout():
    logout_user()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('login'))

@current_app.route("/dashboard")
@login_required
def dashboard():
    # Di sini nanti kita bisa tambahkan logika untuk mengambil data ESP32-CAM
    return render_template('dashboard.html', title='Dashboard')

@current_app.route("/hasil_deteksi/<int:detection_id>") # Atau hanya /hasil jika hasil sementara
@login_required
def view_detection_result(detection_id):
    detection = Detection.query.get_or_404(detection_id)
    # Pastikan hanya user yang bersangkutan yang bisa melihat hasilnya (opsional, tergantung kebutuhan)
    if detection.detector.id != current_user.id:
        flash('Anda tidak memiliki izin untuk melihat hasil deteksi ini.', 'danger')
        return redirect(url_for('history'))
        
    # Untuk menampilkan di halaman hasil.html, kita perlu mengirim data ke template
    # atau memuatnya dengan JavaScript jika hasil disimpan sementara dan diambil via API.
    # Untuk saat ini, kita akan render template dengan data deteksi.
    return render_template('hasil.html', title='Hasil Deteksi', detection=detection)


@current_app.route("/histori")
@login_required
def history():
    # Ambil semua deteksi milik pengguna yang sedang login, urutkan dari yang terbaru
    user_detections = Detection.query.filter_by(user_id=current_user.id)\
                                     .order_by(Detection.timestamp.desc())\
                                     .all()
    return render_template('histori.html', title='Histori Deteksi', detections=user_detections)

# Rute untuk placeholder stream kamera (akan diimplementasikan lebih lanjut di Tahap 8)
@current_app.route('/video_feed')
@login_required
def video_feed():
    # Fungsi ini akan menghasilkan stream MJPEG dari ESP32-CAM
    # Untuk sekarang, ini hanya placeholder
    # return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Video feed placeholder" # Ganti dengan implementasi sebenarnya nanti

# Rute untuk menangkap gambar (akan diimplementasikan lebih lanjut di Tahap 8)
@current_app.route('/capture_image', methods=['POST'])
@login_required
def capture_image():
    # Logika untuk mengambil gambar dari ESP32-CAM, menyimpan, memproses dengan YOLO,
    # mendapatkan deskripsi dari Gemini, dan menyimpan ke database.
    # Ini akan menjadi rute API yang dipanggil dari JavaScript di dashboard.
    # Untuk sekarang, hanya placeholder.
    # ...
    # data_hasil = {
    #     'image_url': url_for('static', filename=f'uploads/{nama_file_gambar_hasil}'),
    #     'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
    #     'class': 'Contoh Kelas',
    #     'confidence': 0.95,
    #     'description': 'Ini adalah deskripsi generatif contoh.'
    # }
    # return jsonify(success=True, data=data_hasil)
    return jsonify(success=False, message="Fitur capture belum diimplementasikan.")
