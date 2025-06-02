# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps # Untuk decorator login_required

# Inisialisasi Aplikasi Flask
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Konfigurasi Aplikasi
# Flask session memerlukan SECRET_KEY. Ini digunakan untuk mengamankan data session.
# Ganti dengan kunci acak yang kuat di lingkungan produksi.
app.config['SECRET_KEY'] = os.urandom(24).hex() # Menghasilkan kunci acak setiap kali server dimulai (untuk pengembangan)
# Untuk produksi, sebaiknya set sebagai environment variable atau string tetap yang aman.
# app.config['SECRET_KEY'] = 'your_very_secret_and_random_key_here'

# Konfigurasi Database MySQL
# Pastikan service MySQL Anda berjalan dan database 'db_projek_yolo8' sudah ada.
DB_HOST = "localhost"
DB_USER = "root"  # Ganti jika user MySQL Anda berbeda
DB_PASSWORD = ""  # Ganti jika password MySQL Anda berbeda
DB_NAME = "db_projek_yolo8"

# Fungsi untuk mendapatkan koneksi database
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
        print(f"Database connection error: {err}") # Untuk debugging di console server
        return None

# Decorator untuk memastikan pengguna sudah login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rute Aplikasi ---

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
            return render_template('register.html', error_message="Tidak dapat terhubung ke database.") # Atau halaman error khusus

        cursor = conn.cursor(dictionary=True) # dictionary=True agar hasil query bisa diakses seperti dict

        # Cek apakah username atau email sudah ada
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
            conn.rollback() # Batalkan transaksi jika ada error
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()
            
    return render_template('register.html', title="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'] # Bisa username atau email
        password = request.form['password']

        if not identifier or not password:
            flash('Username/Email dan Password wajib diisi!', 'danger')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if not conn:
            return render_template('login.html', error_message="Tidak dapat terhubung ke database.")

        cursor = conn.cursor(dictionary=True)
        
        # Coba cari berdasarkan username atau email
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
    # Di sini nanti akan ada logika untuk menampilkan feed kamera ESP32-CAM
    return render_template('dashboard.html', title="Dashboard", username=session.get('username'))

@app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect():
    # Logika untuk menangkap gambar dari ESP32-CAM dan melakukan deteksi YOLOv8
    # Akan diimplementasikan pada tahap selanjutnya
    flash('Fitur deteksi belum diimplementasikan.', 'info')
    return redirect(url_for('dashboard')) # Sementara redirect ke dashboard

@app.route('/hasil') # Seharusnya /hasil/<id_deteksi> atau semacamnya
@login_required
def hasil():
    # Menampilkan hasil deteksi spesifik
    # Akan diimplementasikan pada tahap selanjutnya
    return render_template('hasil.html', title="Hasil Deteksi", username=session.get('username'))

@app.route('/histori')
@login_required
def histori():
    # Menampilkan riwayat deteksi pengguna
    # Akan diimplementasikan pada tahap selanjutnya dengan query ke database
    detections_history = [] # Placeholder
    return render_template('histori.html', title="Histori Deteksi", username=session.get('username'), detections=detections_history)

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

# Error Handlers (Contoh Sederhana)
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', title="Halaman Tidak Ditemukan"), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Penting: Jangan tampilkan detail error internal ke pengguna di produksi
    return render_template('errors/500.html', title="Kesalahan Server"), 500


if __name__ == '__main__':
    # Pastikan folder untuk upload gambar (jika ada) sudah dibuat
    # if not os.path.exists('app/static/uploads'):
    #    os.makedirs('app/static/uploads')
    app.run(debug=True, host='0.0.0.0', port=5000) # debug=True untuk pengembangan