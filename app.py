# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps # Untuk decorator login_required
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv # Untuk memuat variabel dari .env
import requests # <-- Tambahkan ini untuk mengambil gambar dari ESP32-CAM

# Inisialisasi Aplikasi Flask
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
load_dotenv() # Memuat variabel dari file .env

# Konfigurasi Google Gemini API
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("PERINGATAN: GOOGLE_GEMINI_API_KEY tidak ditemukan di .env. Fitur deskripsi Gemini tidak akan berfungsi.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Google Gemini API berhasil dikonfigurasi.")
    except Exception as e:
        print(f"Error saat mengkonfigurasi Gemini API: {e}")
        GEMINI_API_KEY = None

# Konfigurasi Aplikasi
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex()) # Ambil dari .env atau generate baru
app.config['UPLOAD_FOLDER'] = 'app/static/uploads' # Tambahkan konfigurasi folder upload
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Buat folder jika belum ada


# Konfigurasi Database MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_projek_yolo8") # Di README namanya projek_yolo8_db

# Dapatkan alamat IP ESP32-CAM dari environment variable
ESP32_CAM_BASE_IP = os.getenv("ESP32_CAM_IP")
# Verifikasi endpoint ini dari kode Arduino (.ino) Anda
ESP32_CAM_STREAM_PATH = "/stream" # Contoh, bisa berbeda
ESP32_CAM_CAPTURE_PATH = "/capture" # Contoh, bisa berbeda


@app.template_filter('date')
def custom_date_filter(value, fmt=None):
    if fmt == "Y":
        format_string = "%Y"
    elif fmt:
        format_string = fmt
    else:
        format_string = "%Y-%m-%d %H:%M:%S"

    if value == "now":
        return datetime.utcnow().strftime(format_string)
    if isinstance(value, datetime):
        return value.strftime(format_string)
    return value

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        flash(f"Kesalahan koneksi database: {err}", "danger")
        print(f"Database connection error: {err}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not email or not password or not confirm_password:
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok!', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        if not conn:
            return render_template('register.html', error_message="Tidak dapat terhubung ke database.")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Username atau Email sudah terdaftar.', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                           (username, email, hashed_password))
            conn.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Terjadi kesalahan saat registrasi: {err}', 'danger')
            conn.rollback()
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html', title="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        if not identifier or not password:
            flash('Username/Email dan Password wajib diisi!', 'danger')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if not conn:
            return render_template('login.html', error_message="Tidak dapat terhubung ke database.")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (identifier, identifier))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login gagal. Periksa kembali username/email dan password Anda.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', title="Login")

@app.route('/dashboard')
@login_required
def dashboard():
    esp32_stream_url = None
    if ESP32_CAM_BASE_IP:
        esp32_stream_url = f"{ESP32_CAM_BASE_IP}{ESP32_CAM_STREAM_PATH}"
    else:
        flash("Alamat IP ESP32-CAM belum dikonfigurasi di file .env.", "warning")

    return render_template('dashboard.html', 
                           title="Dashboard", 
                           username=session.get('username'),
                           esp32_cam_ip=ESP32_CAM_BASE_IP, # Untuk ditampilkan di teks
                           esp32_stream_url=esp32_stream_url) # Untuk <img> src

@app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect():
    if not ESP32_CAM_BASE_IP:
        flash("Alamat IP ESP32-CAM belum dikonfigurasi. Tidak dapat mengambil gambar.", "danger")
        return redirect(url_for('dashboard'))

    capture_url = f"{ESP32_CAM_BASE_IP}{ESP32_CAM_CAPTURE_PATH}"

    try:
        response = requests.get(capture_url, timeout=10) # Timeout 10 detik
        response.raise_for_status() # Akan raise error jika status code 4xx atau 5xx

        # Simpan gambar yang ditangkap
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"capture_{session['user_id']}_{timestamp_str}.jpg"
        # Path disimpan relatif terhadap static folder agar bisa diakses dari template
        relative_image_path = os.path.join('uploads', image_name)
        absolute_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)

        with open(absolute_image_path, 'wb') as f:
            f.write(response.content)

        flash(f"Gambar berhasil diambil: {image_name}", "success")

        # ---- MULAI LOGIKA DETEKSI YOLOv8 DI SINI ----
        # 1. Muat model YOLOv8 Anda (lihat README)
        #    model_path = os.path.join('models_yolo', 'nama_model_anda.pt') 
        #    model = YOLO(model_path) 
        # 2. Lakukan prediksi pada `absolute_image_path`
        #    results = model(absolute_image_path)
        # 3. Proses `results` untuk mendapatkan kelas, confidence, bounding box
        #    detected_class = "Oli Baik" # Contoh
        #    confidence_score = 0.95 # Contoh
        # 4. Simpan hasil deteksi ke database (tabel `detections`)
        #    conn = get_db_connection()
        #    cursor = conn.cursor()
        #    sql = "INSERT INTO detections (user_id, image_name, image_path, detection_class, confidence_score, generative_description) VALUES (%s, %s, %s, %s, %s, %s)"
        #    # generative_description bisa didapatkan dari Gemini API
        #    val = (session['user_id'], image_name, relative_image_path, detected_class, confidence_score, "Deskripsi dari Gemini...")
        #    cursor.execute(sql, val)
        #    conn.commit()
        #    detection_id = cursor.lastrowid
        #    cursor.close()
        #    conn.close()
        # 5. Redirect ke halaman hasil dengan membawa ID deteksi
        #    return redirect(url_for('hasil', detection_id=detection_id))
        # ---- AKHIR LOGIKA DETEKSI ----

        # Placeholder karena deteksi belum diimplementasikan sepenuhnya:
        flash('Gambar berhasil ditangkap, tetapi fitur deteksi YOLOv8 belum diimplementasikan sepenuhnya di rute ini.', 'info')
        # Untuk sementara, tampilkan gambar yang ditangkap di halaman hasil (dummy)
        # Anda perlu membuat objek `detection` dummy atau mengambil dari DB jika sudah disimpan
        dummy_detection_data = {
            'id': 0, # Ganti dengan ID dari database jika sudah ada
            'timestamp': datetime.now(),
            'image_name': image_name,
            'image_path': relative_image_path, # path relatif dari static
            'detection_class': "Belum Terdeteksi",
            'confidence_score': 0.0,
            'generative_description': 'Silakan implementasikan deteksi YOLOv8 dan integrasi Gemini API.'
        }
        return render_template('hasil.html', title="Hasil Deteksi (Placeholder)", detection=dummy_detection_data, username=session.get('username'))

    except requests.exceptions.RequestException as e:
        flash(f"Gagal mengambil gambar dari ESP32-CAM: {e}", "danger")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}", "danger")
        return redirect(url_for('dashboard'))


@app.route('/hasil') # Bisa juga '/hasil/<int:detection_id>' jika mengambil dari DB
@login_required
def hasil():
    # Jika menggunakan detection_id dari URL:
    # detection_id = request.args.get('detection_id')
    # Ambil data deteksi dari database berdasarkan detection_id dan user_id
    # detection_data = get_detection_from_db(detection_id, session['user_id'])
    # Jika tidak ada, tampilkan pesan error atau redirect

    # Untuk contoh ini, kita asumsikan data deteksi mungkin tidak ada jika diakses langsung
    # atau jika '/capture_and_detect' belum menyiapkan datanya.
    # Pada implementasi nyata, halaman ini akan menerima `detection_id`
    # dan memuat data dari database.

    # Placeholder data jika tidak ada data deteksi yang dikirim dari rute sebelumnya
    # Ini hanya akan ditampilkan jika pengguna menavigasi ke /hasil secara langsung
    # tanpa melalui proses deteksi.
    placeholder_detection = {
        'timestamp': datetime.now(),
        'image_name': 'N/A',
        'image_path': None, # Tidak ada gambar jika diakses langsung
        'detection_class': 'N/A',
        'confidence_score': None,
        'generative_description': 'Tidak ada data deteksi. Silakan lakukan deteksi dari dashboard.'
    }
    # Cek apakah ada data deteksi yang dikirim melalui argumen (misalnya dari contoh di capture_and_detect)
    # Ini bukan cara yang ideal untuk passing data antar request, lebih baik pakai ID dan DB.
    detection_arg = request.args.get('detection') 
    if detection_arg: # Ini hanya untuk demo, sebaiknya ambil dari DB
         # Logika untuk mengubah string kembali ke dictionary jika perlu, atau idealnya ambil dari DB via ID
        pass

    return render_template('hasil.html', title="Hasil Deteksi", username=session.get('username'), detection=placeholder_detection)


@app.route('/histori')
@login_required
def histori():
    detections_history = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Ambil hanya histori milik user yang sedang login, urutkan dari terbaru
        cursor.execute("SELECT * FROM detections WHERE user_id = %s ORDER BY timestamp DESC", (session['user_id'],))
        detections_history = cursor.fetchall()
        cursor.close()
        conn.close()
    else:
        flash("Tidak dapat memuat histori, masalah koneksi database.", "warning")

    return render_template('histori.html', title="Histori Deteksi", username=session.get('username'), detections=detections_history)

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', title="Halaman Tidak Ditemukan"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', title="Kesalahan Server"), 500


if __name__ == '__main__':
    # Pastikan host 0.0.0.0 agar bisa diakses dari jaringan lokal oleh ESP32-CAM (jika perlu komunikasi balik)
    # dan oleh Anda dari perangkat lain di jaringan yang sama untuk testing.
    app.run(debug=True, host='0.0.0.0', port=5000)