# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps # Untuk decorator login_required
from datetime import datetime # <<<<------ ADD THIS LINE TO IMPORT DATETIME
import google.generativeai as genai
from dotenv import load_dotenv # Untuk memuat variabel dari .env

# Inisialisasi Aplikasi Flask
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
load_dotenv() # Memuat variabel dari file .env

# Konfigurasi Google Gemini API
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("PERINGATAN: GOOGLE_GEMINI_API_KEY tidak ditemukan di .env. Fitur deskripsi Gemini tidak akan berfungsi.")
    # Anda bisa memutuskan untuk menghentikan aplikasi atau melanjutkan dengan fungsionalitas terbatas
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Google Gemini API berhasil dikonfigurasi.")
    except Exception as e:
        print(f"Error saat mengkonfigurasi Gemini API: {e}")
        GEMINI_API_KEY = None # Nonaktifkan jika konfigurasi gagal

# Konfigurasi Aplikasi
app.config['SECRET_KEY'] = os.urandom(24).hex()

# Konfigurasi Database MySQL
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "db_projek_yolo8"

# ++++ START OF ADDED CODE ++++
# Custom Jinja filter for date formatting
@app.template_filter('date')
def custom_date_filter(value, fmt=None):
    """
    Custom Jinja filter to format dates.
    Handles "now" to display current time, and maps "Y" to "%Y" for year.
    """
    if fmt == "Y":
        format_string = "%Y"  # Map "Y" to strftime's "%Y" for year
    elif fmt:
        format_string = fmt   # Allow other strftime format strings
    else:
        format_string = "%Y-%m-%d %H:%M:%S" # Default format

    if value == "now":
        # Using utcnow() for server-side consistency, or use now() for local time
        return datetime.utcnow().strftime(format_string)
    if isinstance(value, datetime): # Check if the value is already a datetime object
        return value.strftime(format_string)
    return value # Return value as is if not "now" or datetime object
# ++++ END OF ADDED CODE ++++

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
        print(f"Database connection error: {err}")
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
    return render_template('dashboard.html', title="Dashboard", username=session.get('username'))

@app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect():
    flash('Fitur deteksi belum diimplementasikan.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/hasil')
@login_required
def hasil():
    return render_template('hasil.html', title="Hasil Deteksi", username=session.get('username'))

@app.route('/histori')
@login_required
def histori():
    detections_history = []
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
    app.run(debug=True, host='0.0.0.0', port=5000)