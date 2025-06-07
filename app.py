# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response as FlaskResponse # Mengganti nama Response agar tidak bentrok
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from functools import wraps # Untuk decorator login_required
from datetime import datetime
import google.generativeai as genai
from typing import Optional, Dict, Any, Tuple, Union, Callable # Import tipe yang dibutuhkan
from dotenv import load_dotenv # Untuk memuat variabel dari .env
import requests 
from ultralytics import YOLO # Pastikan ultralytics terinstal
import cv2 # Untuk pemrosesan gambar (konversi ke byte, penyimpanan gambar anotasi)
import numpy as np # Untuk konversi byte gambar ke array NumPy
# from PIL import Image # Opsional: Uncomment jika ingin validasi gambar lebih lanjut dengan Pillow


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
        GEMINI_API_KEY = None # Nonaktifkan jika konfigurasi gagal

# Konfigurasi Aplikasi
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Muat Model YOLOv8 sekali saat aplikasi dimulai
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', os.path.join('models_yolo', 'best.pt'))
model_yolo: Optional[YOLO] = None # Inisialisasi dengan tipe
try:
    if os.path.exists(MODEL_PATH):
        model_yolo = YOLO(MODEL_PATH)
        print(f"Model YOLO berhasil dimuat dari {MODEL_PATH}")
    else:
        print(f"Error: File model YOLO tidak ditemukan di path: {MODEL_PATH}")
except Exception as e:
    print(f"Error saat memuat model YOLO dari {MODEL_PATH}: {e}")
    model_yolo = None

# Konfigurasi Database MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_projek_yolo8")

# Konfigurasi Kamera
DEFAULT_CAMERA_IP_FROM_ENV = os.getenv("ESP32_CAM_IP") # IP dari .env sebagai fallback (string IP atau hostname)
CAMERA_REQUEST_TIMEOUT = int(os.getenv("CAMERA_REQUEST_TIMEOUT", "300"))
CAMERA_VERIFY_TIMEOUT = int(os.getenv("CAMERA_VERIFY_TIMEOUT", "30")) # Timeout untuk verifikasi koneksi IP

# CAMERA_STREAM_PATH dan CAMERA_CAPTURE_PATH diatur secara eksplisit
# untuk memastikan kesesuaian dengan endpoint yang tetap di firmware ESP32-CAM.
CAMERA_STREAM_PATH = "/stream"
CAMERA_CAPTURE_PATH = "/capture_image"
# untuk memastikan kesesuaian dengan endpoint yang tetap di firmware ESP32-CAM.

def get_camera_base_ip() -> Optional[str]:
    """Mendapatkan IP dasar kamera dari session, fallback ke .env."""
    # Prioritaskan IP dari session jika ada
    camera_ip_session = session.get('esp32_cam_ip')
    if camera_ip_session:
        if not camera_ip_session.startswith(('http://', 'https://')):
            return f"http://{camera_ip_session}"
        return camera_ip_session

    # Jika tidak ada di session, gunakan dari .env
    if DEFAULT_CAMERA_IP_FROM_ENV:
        if not DEFAULT_CAMERA_IP_FROM_ENV.startswith(('http://', 'https://')):
            return f"http://{DEFAULT_CAMERA_IP_FROM_ENV}"
        return DEFAULT_CAMERA_IP_FROM_ENV
    return None

if not DEFAULT_CAMERA_IP_FROM_ENV:
    print("PERINGATAN: ESP32_CAM_IP (atau IP Kamera) tidak diatur di .env sebagai fallback. Fitur kamera hanya akan berfungsi jika IP diinput manual oleh user.")
else:
    print(f"Konfigurasi Kamera Default dari .env:")
    print(f"  IP Dasar Kamera (fallback): {DEFAULT_CAMERA_IP_FROM_ENV}")
    
def verify_camera_connection(ip_address: str) -> Tuple[bool, str]:
    """
    Verifikasi koneksi ke stream kamera pada alamat IP yang diberikan.
    Mengembalikan tuple (status: bool, pesan: str).
    """
    if not ip_address:
        return False, "Alamat IP kosong."

    # Pastikan format URL dasar
    if not ip_address.startswith(('http://', 'https://')):
        base_url = f"http://{ip_address}"
    else:
        base_url = ip_address

    stream_url = f"{base_url}{CAMERA_STREAM_PATH}"
    print(f"Verifying camera connection to: {stream_url} with timeout {CAMERA_VERIFY_TIMEOUT}s")

    try:
        # Menggunakan GET dengan stream=True dan close untuk memastikan koneksi stream bisa dibuka
        with requests.get(stream_url, timeout=CAMERA_VERIFY_TIMEOUT, stream=True) as response:
            # Check if we got a successful response status code (2xx)
            # For MJPEG stream, the initial headers are sent with 200 OK.
            if response.status_code == 200:
                 # Attempt to read a small amount of data to confirm stream is active
                 try:
                     chunk = next(response.iter_content(chunk_size=1024), None)
                     if chunk is not None:
                         print(f"Verification successful for {ip_address}. Received initial data.")
                         return True, "Koneksi berhasil diverifikasi."
                     else:
                         print(f"Verification warning for {ip_address}: Received 200 OK but no initial data chunk.")
                         return False, "Koneksi berhasil, tetapi tidak ada data stream awal yang diterima."
                 except requests.exceptions.RequestException as e:
                      print(f"Verification error for {ip_address}: Failed to read initial data chunk - {e}")
                      return False, f"Koneksi berhasil, tetapi gagal membaca data stream awal: {e}"
            else:
                print(f"Verification failed for {ip_address}: Received status code {response.status_code}")
                return False, f"Server merespons dengan status code: {response.status_code}"
    except requests.exceptions.Timeout:
        print(f"Verification failed for {ip_address}: Timeout after {CAMERA_VERIFY_TIMEOUT}s")
        return False, f"Timeout saat mencoba terhubung setelah {CAMERA_VERIFY_TIMEOUT} detik."
    except requests.exceptions.RequestException as e:
        print(f"Verification failed for {ip_address}: Connection Error - {e}")
        return False, f"Gagal terhubung: {e}"
    except Exception as e:
        print(f"Verification failed for {ip_address}: Unexpected Error - {e}")
        return False, f"Terjadi kesalahan tak terduga saat verifikasi: {e}"

print(f"  Path Stream Kamera: {CAMERA_STREAM_PATH}")
print(f"  Path Capture Kamera: {CAMERA_CAPTURE_PATH}")
print(f"  Timeout Request Kamera: {CAMERA_REQUEST_TIMEOUT} detik")
print(f"  Timeout Verifikasi Kamera: {CAMERA_VERIFY_TIMEOUT} detik")
print(f"  PENTING: Pastikan 'Path Capture' ({CAMERA_CAPTURE_PATH}) sesuai dengan endpoint di firmware ESP32-CAM Anda.")

@app.template_filter('date')
def custom_date_filter(value: Union[str, datetime], fmt: Optional[str] = None) -> str:
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
    if isinstance(value, str): # Tambahan untuk menangani string tanggal dari DB
        try:
            dt_obj = datetime.fromisoformat(value)
            return dt_obj.strftime(format_string)
        except ValueError:
            pass # Jika gagal parse, kembalikan string asli
    return str(value)
 
def get_db_connection() -> Optional[mysql.connector.MySQLConnection]:
    try: 
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=10 # Tambahkan timeout koneksi DB
        )
        return conn
    except mysql.connector.Error as err:
        flash(f"Kesalahan koneksi database: {err}", "danger")
        print(f"Database connection error: {err}")
        return None

def login_required(f: Callable) -> Callable:
    @wraps(f) # type: ignore
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if 'user_id' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
 
@app.route('/')
def index() -> FlaskResponse:
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
 
@app.route('/register', methods=['GET', 'POST'])
def register() -> Union[str, FlaskResponse]:
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([username, email, password, confirm_password]):
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok!', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        if not conn:
            return render_template('register.html', title="Register", error_message="Tidak dapat terhubung ke database.")

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Username atau Email sudah terdaftar.', 'warning')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                           (username, email, hashed_password))
            conn.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Terjadi kesalahan saat registrasi: {err}', 'danger')
            if conn.is_connected(): conn.rollback()
            return redirect(url_for('register'))
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()

    return render_template('register.html', title="Register")
 
@app.route('/login', methods=['GET', 'POST'])
def login() -> Union[str, FlaskResponse]:
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash('Username/Email dan Password wajib diisi!', 'danger')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if not conn:
            return render_template('login.html', title="Login", error_message="Tidak dapat terhubung ke database.")

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (identifier, identifier))
            user = cursor.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login berhasil!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Login gagal. Periksa kembali username/email dan password Anda.', 'danger')
                return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Terjadi kesalahan saat login: {err}', 'danger')
            return redirect(url_for('login'))
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
            
    return render_template('login.html', title="Login")
 
@app.route('/dashboard')
@login_required
def dashboard() -> str:
    camera_base_ip = get_camera_base_ip()
    esp32_stream_url = None

    if camera_base_ip:
        esp32_stream_url = f"{camera_base_ip}{CAMERA_STREAM_PATH}"
        print(f"Dashboard: URL Stream Kamera = {esp32_stream_url}")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi. Silakan masukkan IP Kamera untuk mengaktifkan fitur kamera.", "warning")

    return render_template('dashboard.html', 
                           title="Dashboard", 
                           username=session.get('username'),
                           current_cam_ip=session.get('esp32_cam_ip', DEFAULT_CAMERA_IP_FROM_ENV or ""), # Untuk ditampilkan di form
                           esp32_stream_url=esp32_stream_url,
                           camera_configured=(camera_base_ip is not None))
 
@app.route('/update_cam_ip', methods=['POST'])
@login_required
def update_cam_ip() -> FlaskResponse:
    new_cam_ip = request.form.get('esp32_cam_ip', '').strip()
    
    if new_cam_ip:
        # Validasi sederhana (bisa lebih kompleks jika perlu, misal regex IP)
        # Cek format dasar IP (contoh: 1.1.1.1 minimal 7 karakter) atau hostname (mengandung titik atau strip)
        if not (('.' in new_cam_ip and len(new_cam_ip) >= 7) or ('-' in new_cam_ip and len(new_cam_ip) > 1)): # Hostname bisa pendek jika hanya satu kata
             flash('Format Alamat IP Kamera tidak valid.', 'danger')
             return redirect(url_for('dashboard'))

        is_verified, verify_message = verify_camera_connection(new_cam_ip)
        
        if is_verified:
            session['esp32_cam_ip'] = new_cam_ip
            flash(f'Alamat IP Kamera berhasil diperbarui dan diverifikasi: {new_cam_ip}', 'success')
            print(f"User {session.get('username')} memperbarui IP Kamera ke: {new_cam_ip} (Verifikasi Berhasil)")
        else:
            # Simpan IP meskipun verifikasi gagal, tapi beri peringatan
            session['esp32_cam_ip'] = new_cam_ip # Simpan input user
            flash(f'Alamat IP Kamera diperbarui menjadi: {new_cam_ip}. PERINGATAN: Verifikasi koneksi gagal - {verify_message}', 'warning')
            print(f"User {session.get('username')} memperbarui IP Kamera ke: {new_cam_ip} (Verifikasi GAGAL: {verify_message})")
    else:
        # Jika input kosong, hapus dari session agar kembali ke default .env (jika ada)
        session.pop('esp32_cam_ip', None)
        flash('Alamat IP Kamera dihapus dari sesi ini. Menggunakan default (jika ada).', 'info')
        print(f"User {session.get('username')} menghapus IP Kamera dari sesi.")
    return redirect(url_for('dashboard'))


def get_gemini_description(image_path_for_gemini: str, detected_class_name: str) -> str:
    if not GEMINI_API_KEY or not genai:
        print("Gemini API tidak dikonfigurasi. Mengembalikan deskripsi default.")
        return "Deskripsi generatif tidak tersedia karena API Gemini tidak dikonfigurasi."
    try:
        model_gemini = genai.GenerativeModel('gemini-pro-vision')
        
        # Pastikan file ada sebelum mencoba mengunggah
        if not os.path.exists(image_path_for_gemini):
            print(f"GEMINI ERROR: File gambar tidak ditemukan di path: {image_path_for_gemini}")
            return f"Gagal menghasilkan deskripsi: File gambar sumber tidak ditemukan ({os.path.basename(image_path_for_gemini)})."

        image_input = genai.upload_file(image_path_for_gemini)
        prompt = (
            f"Analisis gambar ini yang diduga menunjukkan kondisi oli sepeda motor. "
            f"Model deteksi objek mengidentifikasi area/objek utama sebagai '{detected_class_name}'. "
            f"Berdasarkan visual pada gambar dan identifikasi '{detected_class_name}', jelaskan secara detail kondisi kualitas oli tersebut. "
            f"Berikan juga rekomendasi perawatan atau penggantian oli yang relevan, serta saran umum terkait penggunaan oli tersebut "
            f"untuk menjaga performa mesin sepeda motor."
        )
        response = model_gemini.generate_content([prompt, image_input])
        # Hapus file yang diunggah ke Gemini setelah digunakan jika perlu (opsional)
        # genai.delete_file(image_input.name) 
        return response.text if response.text else "Tidak ada teks yang dihasilkan oleh Gemini."
    except Exception as e:
        print(f"Error saat menghubungi Gemini API: {e}")
        if "google.api_core.exceptions.NotFound: 404" in str(e) and "Requested entity was not found" in str(e):
            print(f"GEMINI ERROR: Pastikan file gambar ada di path: {image_path_for_gemini} dan dapat diakses oleh Gemini API.")
        return f"Gagal menghasilkan deskripsi dari Gemini: {e}"

@app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect() -> FlaskResponse:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        flash("Alamat IP Kamera belum dikonfigurasi. Tidak dapat mengambil gambar.", "danger")
        return redirect(url_for('dashboard'))

    if not model_yolo:
        flash("Model YOLO tidak berhasil dimuat atau tidak ditemukan. Fitur deteksi tidak tersedia.", "danger")
        return redirect(url_for('dashboard'))
    capture_url = f"{camera_base_ip}{CAMERA_CAPTURE_PATH}"
    print(f"Capture & Detect: Mencoba mengambil gambar dari URL = {capture_url}")

    request_headers = {'Connection': 'close'}
    try:
        response = requests.get(capture_url, headers=request_headers, timeout=CAMERA_REQUEST_TIMEOUT)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type')
        if not content_type or not content_type.startswith('image/'):
            error_message = f"Konten dari ESP32-CAM bukan gambar (Content-Type: {content_type}). URL: {capture_url}"
            flash(error_message, "danger")
            print(f"Error: {error_message}. Response text (first 200 chars): {response.text[:200]}")
            return redirect(url_for('dashboard'))

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_image_name = f"capture_{session['user_id']}_{timestamp_str}"
        
        original_image_filename = f"{base_image_name}_original.jpg"
        absolute_original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], original_image_filename)
        
        annotated_image_filename = f"{base_image_name}_annotated.jpg"
        absolute_annotated_image_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_image_filename)
        relative_annotated_image_path = os.path.join('uploads', annotated_image_filename) # Untuk DB dan template

        with open(absolute_original_image_path, 'wb') as f:
            f.write(response.content)
        print(f"Gambar asli disimpan di: {absolute_original_image_path}")
        flash(f"Gambar asli berhasil diambil dari kamera.", "info")

        results = model_yolo(absolute_original_image_path, verbose=False)

        detected_class_name = "Tidak Terdeteksi"
        confidence_score_str = "0.00%"
        generative_desc = "Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan."
        
        # Default ke gambar asli jika tidak ada deteksi atau error anotasi
        cv2.imwrite(absolute_annotated_image_path, cv2.imread(absolute_original_image_path)) # Salin asli ke anotasi
        print(f"Default: Gambar asli disalin ke path anotasi: {absolute_annotated_image_path}")

        if results and results[0].boxes:
            # results[0].boxes adalah objek Boxes.
            # Jika Anda ingin deteksi dengan skor tertinggi, Anda bisa mengiterasi atau memastikan urutannya.
            # Untuk kesederhanaan, kita ambil deteksi pertama yang dikembalikan.
            # Objek Boxes memiliki atribut seperti .cls, .conf, .xyxy, dll.
            # Setiap atribut ini adalah tensor. Kita ambil elemen pertama [0] dari tensor tersebut.
            first_detection_box = results[0].boxes[0] 
            class_id = int(first_detection_box.cls[0].item())
            detected_class_name = model_yolo.names.get(class_id, f"Unknown Class {class_id}") # Lebih deskriptif jika nama tidak ada
            confidence_score_val = float(first_detection_box.conf[0].item())
            confidence_score_str = f"{confidence_score_val*100:.2f}%"
            
            flash(f"Deteksi: {detected_class_name} dengan akurasi: {confidence_score_str}", "info")

            try:
                annotated_image_np = results[0].plot() # Menghasilkan array NumPy (BGR)
                cv2.imwrite(absolute_annotated_image_path, annotated_image_np)
                print(f"Gambar teranotasi disimpan di: {absolute_annotated_image_path}")
                flash(f"Gambar hasil deteksi disimpan sebagai: {annotated_image_filename}", "success")
            except Exception as plot_err:
                print(f"Error saat membuat atau menyimpan gambar anotasi: {plot_err}. Menggunakan gambar asli.")
                flash(f"Error saat membuat anotasi: {plot_err}. Menampilkan gambar asli.", "warning")
                # Gambar asli sudah disalin ke path anotasi sebelumnya

            if GEMINI_API_KEY:
                generative_desc = get_gemini_description(absolute_original_image_path, detected_class_name)
            else:
                generative_desc = "Fitur deskripsi Gemini tidak aktif (API Key tidak ditemukan)."
        else:
            flash("Tidak ada objek yang terdeteksi oleh YOLO.", "warning")
            # Gambar asli sudah disalin ke path anotasi, jadi tidak perlu tindakan khusus di sini

        db_conn = None
        cursor = None
        try:
            db_conn = get_db_connection()
            if not db_conn: return redirect(url_for('dashboard'))
            
            cursor = db_conn.cursor()
            sql = "INSERT INTO detections (user_id, image_name, image_path, detection_class, confidence_score, generative_description, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            current_timestamp = datetime.now()
            val = (session['user_id'], 
                   annotated_image_filename, 
                   relative_annotated_image_path, 
                   detected_class_name, 
                   confidence_score_str, 
                   generative_desc, 
                   current_timestamp)
            cursor.execute(sql, val)
            db_conn.commit()
            detection_id = cursor.lastrowid
            return redirect(url_for('hasil', detection_id=detection_id))
        except mysql.connector.Error as err:
            flash(f"Gagal menyimpan hasil deteksi ke database: {err}", "danger")
            if db_conn and db_conn.is_connected(): db_conn.rollback()
            return redirect(url_for('dashboard'))
        finally:
            if cursor: cursor.close()
            if db_conn and db_conn.is_connected(): db_conn.close()

    except requests.exceptions.Timeout:
        flash(f"Timeout saat mengambil gambar dari ESP32-CAM ({capture_url}) setelah {CAMERA_REQUEST_TIMEOUT} detik.", "danger")
        return redirect(url_for('dashboard'))
    except requests.exceptions.RequestException as e:
        flash(f"Gagal mengambil gambar dari ESP32-CAM: {e}", "danger")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Terjadi kesalahan tak terduga: {e}", "danger")
        print(f"Kesalahan tak terduga di capture_and_detect: {e}")
        return redirect(url_for('dashboard'))

@app.route('/uji_kamera')
@login_required
def uji_kamera_page() -> str:
    camera_base_ip = get_camera_base_ip()
    stream_url_for_template = None
    display_ip_for_template = "Kamera tidak dikonfigurasi"

    if camera_base_ip:
        stream_url_for_template = f"{camera_base_ip}{CAMERA_STREAM_PATH}"
        display_ip_for_template = camera_base_ip.replace("http://", "").replace("https://", "") # Tampilkan IP bersih
    else:
        flash("Alamat IP Kamera belum dikonfigurasi. Stream tidak akan tampil.", "warning")

    return render_template('index.html',
                           title="Uji Capture Kamera",
                           username=session.get('username'),
                           esp32_stream_url_from_flask=stream_url_for_template,
                           esp32_display_ip_from_flask=display_ip_for_template)

@app.route('/api/capture_and_process', methods=['POST'])
@login_required
def api_capture_and_process() -> Union[FlaskResponse, Tuple[Dict[str, str], int]]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return {"error": "Alamat IP Kamera belum dikonfigurasi."}, 503

    if not model_yolo:
        return {"error": "Model YOLO tidak berhasil dimuat."}, 503

    capture_url: str = f"{camera_base_ip}{CAMERA_CAPTURE_PATH}"
    print(f"API Capture: Mencoba mengambil gambar dari URL = {capture_url}")

    request_headers = {'Connection': 'close'}
    try:
        response_cam = requests.get(capture_url, headers=request_headers, timeout=CAMERA_REQUEST_TIMEOUT)
        response_cam.raise_for_status()

        content_type = response_cam.headers.get('Content-Type')
        if not content_type or not content_type.startswith('image/'):
            error_msg = f"Konten dari kamera bukan gambar (Content-Type: {content_type}). URL: {capture_url}"
            print(f"API Error: {error_msg}")
            return {"error": error_msg}, 502

        image_bytes = response_cam.content
        try:
            # Decode byte gambar ke array NumPy (BGR)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_np is None:
                print("API Error: Gagal men-decode gambar dari bytes yang diterima dari kamera.")
                return {"error": "Gagal memproses gambar dari kamera (decode error)."}, 500

            # Lakukan inferensi YOLO pada array NumPy
            results = model_yolo(img_np, verbose=False)
            # results[0].plot() mengembalikan NumPy array (BGR) dari gambar dengan deteksi.
            # Jika tidak ada deteksi, ia akan mengembalikan gambar asli.
            annotated_image_bgr_np = results[0].plot() 

            # Konversi array NumPy (BGR) ke format JPEG bytes
            encode_success, image_buffer = cv2.imencode('.jpg', annotated_image_bgr_np)
            if not encode_success:
                print("API Error: Gagal meng-encode gambar hasil anotasi ke JPEG.")
                return {"error": "Gagal memproses gambar hasil anotasi."}, 500
            
            processed_image_bytes = image_buffer.tobytes()
            return FlaskResponse(processed_image_bytes, mimetype='image/jpeg')

        except Exception as yolo_err:
            # Tangani error spesifik dari YOLO atau pemrosesan gambar jika ada
            print(f"API Error saat pemrosesan YOLO: {yolo_err}")
            return {"error": f"Error saat pemrosesan YOLO: {str(yolo_err)}"}, 500
            
    except requests.exceptions.Timeout:
        return {"error": f"Timeout saat menghubungi kamera di {capture_url} setelah {CAMERA_REQUEST_TIMEOUT} detik."}, 504
    except requests.exceptions.RequestException as e:
        return {"error": f"Error koneksi ke kamera: {str(e)}"}, 502
    except Exception as e:
        print(f"API Error internal: {e}")
        return {"error": f"Terjadi kesalahan internal server: {str(e)}"}, 500

@app.route('/hasil/<int:detection_id>')
@login_required
def hasil(detection_id: int) -> Union[str, FlaskResponse]:
    detection_data: Optional[Dict[str, Any]] = None
    conn = get_db_connection()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections WHERE id = %s AND user_id = %s", (detection_id, session['user_id']))
            detection_data = cursor.fetchone()
        except mysql.connector.Error as err:
            flash(f"Error saat mengambil data deteksi: {err}", "danger")
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()

    if not detection_data:
        flash("Data deteksi tidak ditemukan atau Anda tidak memiliki akses.", "warning")
        return redirect(url_for('dashboard'))

    return render_template('hasil.html', title="Hasil Deteksi", username=session.get('username'), detection=detection_data)

@app.route('/histori')
@login_required
def histori() -> str:
    detections_history: list = []
    conn = get_db_connection()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections WHERE user_id = %s ORDER BY timestamp DESC", (session['user_id'],))
            detections_history = cursor.fetchall()
        except mysql.connector.Error as err:
            flash(f"Error saat memuat histori: {err}", "danger")
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()
    else:
        # Pesan flash sudah ditangani oleh get_db_connection jika koneksi gagal
        pass

    return render_template('histori.html', title="Histori Deteksi", username=session.get('username'), detections=detections_history)

@app.route('/logout')
@login_required
def logout() -> FlaskResponse:
    session.clear() # Membersihkan semua data session
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

@app.errorhandler(400)
def bad_request(e: Any) -> Tuple[str, int]:
    return render_template('errors/400.html', title="Permintaan Buruk"), 400

@app.errorhandler(401)
def unauthorized(e: Any) -> Tuple[str, int]:
    # Jika error ini terjadi, mungkin pengguna mencoba mengakses sesuatu tanpa login
    # atau session mereka tidak valid. Mengarahkan ke login bisa jadi opsi.
    flash("Anda perlu login untuk mengakses sumber daya ini atau sesi Anda tidak valid.", "warning")
    # return redirect(url_for('login')) # Opsi: redirect ke login
    return render_template('errors/401.html', title="Tidak Diotorisasi"), 401

@app.errorhandler(404)
def page_not_found(e: Any) -> Tuple[str, int]:
    return render_template('errors/404.html', title="Halaman Tidak Ditemukan"), 404

@app.errorhandler(403)
def forbidden(e: Any) -> Tuple[str, int]:
    return render_template('errors/403.html', title="Terlarang"), 403

@app.errorhandler(405)
def method_not_allowed(e: Any) -> Tuple[str, int]:
    return render_template('errors/405.html', title="Metode Tidak Diizinkan"), 405

@app.errorhandler(500)
def internal_server_error(e: Any) -> Tuple[str, int]:
    # Log error internal server
    print(f"Internal Server Error: {e}")
    return render_template('errors/500.html', title="Kesalahan Server"), 500
 
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
