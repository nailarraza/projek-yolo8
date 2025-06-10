# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response as FlaskResponse # Mengganti nama Response agar tidak bentrok
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from functools import wraps # Untuk decorator login_required
from datetime import datetime
import google.generativeai as genai
from typing import Optional, Dict, Any, Tuple, Union, Callable, cast # Import tipe yang dibutuhkan
from dotenv import load_dotenv # Untuk memuat variabel dari .env
import requests
from ultralytics import YOLO # Pastikan ultralytics terinstal
import cv2 # Untuk pemrosesan gambar (konversi ke byte, penyimpanan gambar anotasi)
import base64 # Untuk decode base64 image dari client
import time # Digunakan dalam fungsi capture_single_frame_from_stream_cv2
import numpy as np # Untuk konversi byte gambar ke array NumPy
import threading # Untuk Lock pada modifikasi environment variable OpenCV
# from PIL import Image # Opsional: Uncomment jika ingin validasi gambar lebih lanjut dengan Pillow
from werkzeug.wrappers import Response as WerkzeugResponse # Untuk type hinting redirect()
from mysql.connector.connection import MySQLConnection
from mysql.connector.pooling import PooledMySQLConnection # Tambahkan import ini
from mysql.connector.abstracts import MySQLConnectionAbstract # Untuk type hinting koneksi DB


# Inisialisasi Aplikasi Flask
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
load_dotenv() # Memuat variabel dari file .env

# Konfigurasi Google Gemini API
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GEMINI_API_KEY:
    app.logger.warning("GOOGLE_GEMINI_API_KEY tidak ditemukan di .env. Fitur deskripsi Gemini tidak akan berfungsi.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY) # type: ignore
        app.logger.info("Google Gemini API berhasil dikonfigurasi.")
    except Exception as e:
        app.logger.error(f"Error saat mengkonfigurasi Gemini API: {e}")
        GEMINI_API_KEY = None # Nonaktifkan jika konfigurasi gagal

# Konfigurasi Aplikasi
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Muat Model YOLOv8 sekali saat aplikasi dimulai
# Model untuk deteksi Oli
MODEL_PATH_OIL = os.getenv('YOLO_MODEL_OIL_PATH', os.getenv('YOLO_MODEL_PATH', os.path.join('models_yolo', 'best.pt'))) # Fallback ke YOLO_MODEL_PATH
model_yolo_oil: Optional[YOLO] = None
try:
    if os.path.exists(MODEL_PATH_OIL):
        model_yolo_oil = YOLO(MODEL_PATH_OIL) # type: ignore
        app.logger.info(f"Model YOLO untuk OLI berhasil dimuat dari {MODEL_PATH_OIL}")
    else:
        app.logger.error(f"Error: File model YOLO untuk OLI tidak ditemukan di path: {MODEL_PATH_OIL}")
except Exception as e:
    app.logger.error(f"Error saat memuat model YOLO untuk OLI dari {MODEL_PATH_OIL}: {e}")
    model_yolo_oil = None

# Model untuk deteksi Manusia
MODEL_PATH_HUMAN = os.getenv('YOLO_MODEL_HUMAN_PATH', os.path.join('models_yolo', 'best2.pt'))
model_yolo_human: Optional[YOLO] = None
try:
    if os.path.exists(MODEL_PATH_HUMAN):
        model_yolo_human = YOLO(MODEL_PATH_HUMAN) # type: ignore
        app.logger.info(f"Model YOLO untuk MANUSIA berhasil dimuat dari {MODEL_PATH_HUMAN}")
    else:
        app.logger.error(f"Error: File model YOLO untuk MANUSIA tidak ditemukan di path: {MODEL_PATH_HUMAN}")
except Exception as e:
    app.logger.error(f"Error saat memuat model YOLO untuk MANUSIA dari {MODEL_PATH_HUMAN}: {e}")
    model_yolo_human = None

# Model untuk deteksi Merek dan Warna Motor
MODEL_PATH_MOTORCYCLE = os.getenv('YOLO_MODEL_MOTORCYCLE_PATH', os.path.join('models_yolo', 'best3.pt'))
model_yolo_motorcycle: Optional[YOLO] = None
try:
    if os.path.exists(MODEL_PATH_MOTORCYCLE):
        model_yolo_motorcycle = YOLO(MODEL_PATH_MOTORCYCLE) # type: ignore
        app.logger.info(f"Model YOLO untuk MEREK/WARNA MOTOR berhasil dimuat dari {MODEL_PATH_MOTORCYCLE}")
    else:
        app.logger.error(f"Error: File model YOLO untuk MEREK/WARNA MOTOR tidak ditemukan di path: {MODEL_PATH_MOTORCYCLE}")
except Exception as e:
    app.logger.error(f"Error saat memuat model YOLO untuk MEREK/WARNA MOTOR dari {MODEL_PATH_MOTORCYCLE}: {e}")
    model_yolo_motorcycle = None

# Konfigurasi Database MySQL
# Langsung definisikan kredensial database di sini
DB_HOST = "localhost"  # Ganti dengan host database Anda jika berbeda
DB_USER = "root"       # Ganti dengan username database Anda
DB_PASSWORD = ""       # Ganti dengan password database Anda (kosongkan jika tidak ada password untuk root)
DB_NAME = "db_projek_yolo8" # Ganti dengan nama database Anda

# Konfigurasi Kamera
CAMERA_REQUEST_TIMEOUT = int(os.getenv("CAMERA_REQUEST_TIMEOUT", "60"))
CAMERA_VERIFY_TIMEOUT = int(os.getenv("CAMERA_VERIFY_TIMEOUT", "30")) # Timeout untuk verifikasi koneksi IP

# CAMERA_STREAM_PATH dan CAMERA_CAPTURE_PATH diatur secara eksplisit
# untuk memastikan kesesuaian dengan endpoint yang tetap di firmware ESP32-CAM.
CAMERA_STREAM_PATH = "/stream" # Untuk live view di dashboard/uji_kamera
CAMERA_CAPTURE_PATH = "/stream" # Default ke /stream, bisa diubah jika ada endpoint snapshot khusus seperti /capture atau path gambar statis

def get_camera_base_ip() -> Optional[str]:
    """Mendapatkan IP dasar kamera dari session."""
    camera_ip = session.get('esp32_cam_ip')
    if camera_ip:
        # Pastikan format URL dasar
        if not camera_ip.startswith(('http://', 'https://')):
            return f"http://{camera_ip}"
        return camera_ip
    return None

# Tidak ada lagi fallback dari .env, jadi logging ini tidak relevan lagi.
# app.logger.info("Fitur kamera hanya akan berfungsi jika IP diinput manual oleh user melalui dashboard.")

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

    # Verifikasi bisa menggunakan stream path atau capture path.
    # Stream path lebih baik untuk verifikasi "keaktifan" kamera.
    verify_url = f"{base_url}{CAMERA_STREAM_PATH}"
    app.logger.info(f"Verifying camera connection to: {verify_url} with timeout {CAMERA_VERIFY_TIMEOUT}s")

    try:
        # Menggunakan GET dengan stream=True dan close untuk memastikan koneksi stream bisa dibuka
        with requests.get(verify_url, timeout=CAMERA_VERIFY_TIMEOUT, stream=True) as response:
            # Check if we got a successful response status code (2xx)
            # For MJPEG stream, the initial headers are sent with 200 OK.
            if response.status_code == 200:
                 # Attempt to read a small amount of data to confirm stream is active
                 try:
                     chunk = next(response.iter_content(chunk_size=1024), None)
                     if chunk is not None:
                         app.logger.info(f"Verification successful for {ip_address}. Received initial data from stream.")
                         return True, "Koneksi stream berhasil diverifikasi."
                     else:
                             app.logger.warning(f"Verification failed for {ip_address}: Stream responded with 200 OK but no initial data was received (empty stream or connection closed prematurely).")
                             return False, "Koneksi stream berhasil dibuka (200 OK), tetapi tidak ada data stream awal yang diterima. Pastikan kamera mengirimkan data."
                 except requests.exceptions.RequestException as e:
                      app.logger.error(f"Verification error for {ip_address}: Failed to read initial data chunk from stream - {e}")
                      return False, f"Koneksi stream berhasil, tetapi gagal membaca data stream awal: {e}"
            else:
                app.logger.warning(f"Verification failed for {ip_address}: Stream endpoint responded with status code {response.status_code}")
                return False, f"Server stream merespons dengan status code: {response.status_code}"
    except requests.exceptions.Timeout:
        app.logger.warning(f"Verification failed for {ip_address}: Timeout after {CAMERA_VERIFY_TIMEOUT}s on stream endpoint.")
        return False, f"Timeout saat mencoba terhubung ke stream setelah {CAMERA_VERIFY_TIMEOUT} detik."
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Verification failed for {ip_address}: Connection Error on stream endpoint - {e}")
        return False, f"Gagal terhubung ke stream: {e}"
    except Exception as e:
        app.logger.error(f"Verification failed for {ip_address}: Unexpected Error on stream endpoint - {e}")
        return False, f"Terjadi kesalahan tak terduga saat verifikasi stream: {e}"

app.logger.info(f"  Path Stream Kamera (untuk live view): {CAMERA_STREAM_PATH}")
app.logger.info(f"  Path Capture Kamera (untuk deteksi): {CAMERA_CAPTURE_PATH}")
app.logger.info(f"  Timeout Request Kamera: {CAMERA_REQUEST_TIMEOUT} detik")
app.logger.info(f"  Timeout Verifikasi Kamera: {CAMERA_VERIFY_TIMEOUT} detik")
app.logger.info(f"  PENTING: Pastikan 'Path Capture' ({CAMERA_CAPTURE_PATH}) dan 'Path Stream' ({CAMERA_STREAM_PATH}) sesuai dengan endpoint di firmware ESP32-CAM Anda.")

def capture_single_frame_from_http_endpoint(capture_url: str,
                                            timeout: int = 10) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mengambil satu frame gambar dari HTTP endpoint (misalnya, ESP32-CAM /capture_image).
    Mengembalikan (frame_numpy_array, error_message).
    """
    try:
        app.logger.info(f"Mencoba mengambil gambar dari HTTP endpoint: {capture_url} dengan timeout {timeout}s")
        response = requests.get(capture_url, timeout=timeout)
        response.raise_for_status()  # Akan raise HTTPError untuk status code 4xx/5xx

        content_type = response.headers.get('content-type', '').lower()
        if 'image' not in content_type:
            app.logger.warning(f"Content-Type dari {capture_url} adalah '{content_type}', diharapkan mengandung 'image'. Tetap mencoba memproses.")

        image_bytes = response.content
        if not image_bytes:
            return None, f"Tidak ada data gambar yang diterima dari {capture_url}."

        image_np = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

        if image_np is None:
            return None, f"Gagal mendekode data gambar dari {capture_url}. Pastikan endpoint mengembalikan format gambar yang valid (JPEG, PNG, dll)."

        app.logger.info(f"Gambar berhasil diambil dan didekode dari {capture_url}")
        return image_np, None

    except requests.exceptions.Timeout:
        error_msg = f"Timeout ({timeout}s) saat mencoba mengambil gambar dari {capture_url}."
        app.logger.warning(error_msg)
        return None, error_msg
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error saat mengambil gambar dari {capture_url}: {http_err} (Status: {http_err.response.status_code if http_err.response else 'N/A'})"
        app.logger.error(error_msg)
        return None, error_msg
    except requests.exceptions.RequestException as req_err:
        error_msg = f"Kesalahan koneksi saat mengambil gambar dari {capture_url}: {req_err}"
        app.logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Kesalahan tak terduga saat mengambil gambar dari {capture_url}: {str(e)}"
        app.logger.error(error_msg)
        return None, error_msg

# Fungsi capture_single_frame_from_stream_cv2 dipertahankan jika diperlukan di masa depan,
# tetapi tidak lagi digunakan oleh capture_and_detect atau api_capture_and_process.

# Global lock untuk sinkronisasi akses ke OPENCV_FFMPEG_CAPTURE_OPTIONS
opencv_ffmpeg_options_lock = threading.Lock()

def capture_single_frame_from_stream_cv2(stream_url: str,
                                         read_frame_timeout: int = 10,
                                         open_stream_timeout_sec: int = 60) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mengambil satu frame dari network stream menggunakan OpenCV.
    Fungsi ini memodifikasi environment variable OPENCV_FFMPEG_CAPTURE_OPTIONS secara sementara
    dan menggunakan threading.Lock untuk memastikan thread-safety.
    """

    ffmpeg_timeout_us = str(open_stream_timeout_sec * 1000 * 1000)
    ffmpeg_options_to_set = f"timeout;{ffmpeg_timeout_us}|rw_timeout;{ffmpeg_timeout_us}"

    cap: Optional[cv2.VideoCapture] = None
    original_ffmpeg_options_env: Optional[str] = None
    stream_opened_successfully = False

    with opencv_ffmpeg_options_lock:
        original_ffmpeg_options_env = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
        app.logger.debug(f"Setting OPENCV_FFMPEG_CAPTURE_OPTIONS temporarily to: {ffmpeg_options_to_set} for stream: {stream_url}")
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ffmpeg_options_to_set

        # This inner try/finally ensures env var is restored even if VideoCapture init fails badly
        try:
            max_open_attempts = 3
            attempt_delay_sec = 1.5

            for attempt in range(max_open_attempts):
                app.logger.info(f"Attempting to open stream with OpenCV: {stream_url} (Attempt {attempt + 1}/{max_open_attempts})")
                # cv2.VideoCapture reads OPENCV_FFMPEG_CAPTURE_OPTIONS at the time of this call
                current_attempt_cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

                if current_attempt_cap.isOpened():
                    cap = current_attempt_cap # Assign to outer scope variable for use after lock
                    stream_opened_successfully = True
                    app.logger.info(f"Stream successfully opened on attempt {attempt + 1}")
                    break
                else:
                    app.logger.warning(f"Failed to open stream on attempt {attempt + 1} (cap.isOpened() false). Waiting {attempt_delay_sec}s before retrying...")
                    current_attempt_cap.release() # Release the failed attempt
                    if attempt < max_open_attempts - 1:
                        time.sleep(attempt_delay_sec)
        finally:
            # Restore OPENCV_FFMPEG_CAPTURE_OPTIONS
            if original_ffmpeg_options_env is None:
                if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ: # Check to prevent KeyError
                    del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
                    app.logger.debug(f"OPENCV_FFMPEG_CAPTURE_OPTIONS removed (restored to system default) for stream: {stream_url}")
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = original_ffmpeg_options_env
                app.logger.debug(f"OPENCV_FFMPEG_CAPTURE_OPTIONS restored to: {original_ffmpeg_options_env} for stream: {stream_url}")
        # Lock is released here

    if not stream_opened_successfully or cap is None:
            error_msg = (f"Gagal membuka stream kamera di {stream_url} setelah {max_open_attempts} percobaan. "
                         "Pastikan kamera aktif, stream URL benar, dan tidak ada klien lain yang menggunakan stream secara eksklusif (misalnya, tab browser lain atau aplikasi lain). "
                         "Jika Anda baru saja menghentikan stream di browser, tunggu beberapa saat sebelum mencoba lagi.")
            app.logger.error(error_msg)
            return None, error_msg

    # If stream was opened, 'cap' is now a valid VideoCapture object. Proceed to read frames.
    try:
        start_time = time.time()
        frame: Optional[np.ndarray] = None
        ret = False
        # Mencoba membaca beberapa frame untuk mendapatkan yang terbaru, membuang yang lama jika ada buffer.
        # Untuk beberapa stream, frame pertama mungkin lama atau butuh waktu untuk tiba.
        for i in range(2): # Coba ambil hingga 2 frame, ambil yang terakhir berhasil
            if time.time() - start_time > read_frame_timeout:
                error_msg_read = f"Timeout ({read_frame_timeout}s) waiting for frame from {stream_url} after open (attempt {i+1})."
                app.logger.warning(error_msg_read)
                break

            temp_ret, temp_frame = cap.read()
            if temp_ret and temp_frame is not None:
                ret = True
                frame = temp_frame
                app.logger.debug(f"Frame successfully read on attempt {i+1} from {stream_url}")
                # Consider breaking here if one good frame is enough, or continue to get the latest.
                # Current logic takes the last good frame from 5 attempts.
            else:
                app.logger.warning(f"Failed to read frame on attempt {i+1} from {stream_url}. ret={temp_ret}")
                time.sleep(0.2) # Jeda singkat jika read gagal

        if not ret or frame is None:
            app.logger.error(f"Gagal membaca frame dari stream {stream_url} setelah beberapa percobaan pasca pembukaan stream.")
            return None, f"Gagal membaca frame dari stream {stream_url} setelah beberapa percobaan."
        return frame, None
    finally: # This 'finally' now correctly pairs with the 'try' above
        if cap is not None: # This 'cap' is the one successfully opened
            app.logger.info(f"Releasing VideoCapture for {stream_url}")
            cap.release()
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

def get_db_connection() -> Optional[Union[MySQLConnection, MySQLConnectionAbstract, PooledMySQLConnection]]:
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
        app.logger.error(f"Database connection error: {err}")
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
def index() -> WerkzeugResponse:
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register() -> Union[str, WerkzeugResponse]:
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
            existing_user: Optional[Dict[str, Any]] = cursor.fetchone() # type: ignore[assignment]

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
def login() -> Union[str, WerkzeugResponse]:
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
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s OR email = %s", (identifier, identifier))
            user: Optional[Dict[str, Any]] = cursor.fetchone() # type: ignore[assignment]

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                # Mengganti flash generik dengan pesan selamat datang yang lebih spesifik
                flash(f"Selamat datang, {str(user['username'])}!", 'success')
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
        app.logger.info(f"Dashboard: URL Stream Kamera = {esp32_stream_url}")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi. Silakan masukkan IP Kamera untuk mengaktifkan fitur kamera.", "warning")

    return render_template('dashboard.html',
                           title="Dashboard",
                           username=session.get('username'),
                           current_cam_ip=session.get('esp32_cam_ip', ""), # Untuk ditampilkan di form, fallback ke string kosong
                           esp32_stream_url=esp32_stream_url,
                           camera_configured=(camera_base_ip is not None))

@app.route('/update_cam_ip', methods=['POST'])
@login_required
def update_cam_ip() -> WerkzeugResponse:
    new_cam_ip = request.form.get('esp32_cam_ip', '').strip()

    if new_cam_ip:
        # Validasi sederhana: minimal ada satu titik (untuk IP) atau panjang tertentu untuk hostname
        # Ini adalah validasi yang sangat dasar.
        is_potentially_valid_ip_or_hostname = '.' in new_cam_ip or len(new_cam_ip) > 3 # Contoh sederhana
        if not is_potentially_valid_ip_or_hostname:
             flash('Format Alamat IP Kamera tidak valid.', 'danger')
             return redirect(url_for('dashboard'))

        is_verified, verify_message = verify_camera_connection(new_cam_ip)

        if is_verified:
            session['esp32_cam_ip'] = new_cam_ip # Simpan IP yang sudah diverifikasi
            flash(f'Alamat IP Kamera berhasil diperbarui dan diverifikasi: {new_cam_ip}', 'success')
            app.logger.info(f"User {session.get('username')} memperbarui IP Kamera ke: {new_cam_ip} (Verifikasi Berhasil)")
        else:
            # Simpan IP input pengguna meskipun verifikasi gagal, tapi beri peringatan jelas
            session['esp32_cam_ip'] = new_cam_ip # Simpan input user
            flash(f'Alamat IP Kamera diperbarui menjadi: {new_cam_ip}. PERINGATAN: Verifikasi koneksi gagal - {verify_message}', 'warning')
            app.logger.warning(f"User {session.get('username')} memperbarui IP Kamera ke: {new_cam_ip} (Verifikasi GAGAL: {verify_message})")
    else:
        # Jika input kosong, hapus IP dari session.
        session.pop('esp32_cam_ip', None)
        flash('Alamat IP Kamera telah dihapus dari sesi ini.', 'info')
        app.logger.info(f"User {session.get('username')} menghapus IP Kamera dari sesi.")
    return redirect(url_for('dashboard'))


def get_gemini_description(image_path_for_gemini: str, detected_class_name: str) -> str:
    if not GEMINI_API_KEY or not genai:
        app.logger.warning("Gemini API tidak dikonfigurasi. Mengembalikan deskripsi default.")
        return "Deskripsi generatif tidak tersedia karena API Gemini tidak dikonfigurasi atau terjadi kesalahan."
    try:
        # Mengganti model lama 'gemini-pro-vision' dengan model yang lebih baru dan disarankan.
        # 'gemini-1.5-flash-latest' adalah pilihan yang baik untuk kecepatan dan biaya.
        model_gemini = genai.GenerativeModel('gemini-1.5-flash-latest') # type: ignore

        # Pastikan file ada sebelum mencoba mengunggah
        if not os.path.exists(image_path_for_gemini):
            app.logger.error(f"GEMINI ERROR: File gambar tidak ditemukan di path: {image_path_for_gemini}")
            return f"Gagal menghasilkan deskripsi: File gambar sumber tidak ditemukan ({os.path.basename(image_path_for_gemini)})."

        image_input = genai.upload_file(image_path_for_gemini) # type: ignore
        prompt = (
            f"Analisis gambar ini. Model deteksi objek mengidentifikasi objek/area utama sebagai '{detected_class_name}'.\n\n"
            f"Berdasarkan visual pada gambar dan identifikasi '{detected_class_name}':\n"
            f"1. Jelaskan secara umum objek yang terlihat pada gambar dan konteksnya.\n"
            f"2. Jika '{detected_class_name}' terkait dengan kondisi oli sepeda motor (misalnya kelas seperti 'Oli Baik', 'Oli Buruk', atau nama merek oli), berikan analisis singkat mengenai kualitas oli tersebut dan saran perawatan atau penggantian yang relevan.\n"
            f"3. Jika '{detected_class_name}' adalah 'manusia' atau 'person', atau terkait dengan aktivitas manusia, deskripsikan apa yang mungkin dilakukan orang tersebut atau situasi yang terlihat.\n"
            f"4. Jika '{detected_class_name}' terkait dengan merek atau warna sepeda motor (misalnya 'Honda', 'Yamaha', 'Merah', 'Biru'), deskripsikan merek atau warna tersebut. Jika memungkinkan, sebutkan juga kemungkinan model motor jika terlihat jelas dari gambar.\n"
            f"5. Jika '{detected_class_name}' bukan salah satu di atas, berikan deskripsi umum yang paling relevan untuk objek tersebut berdasarkan visual gambar.\n\n"
            f"PENTING: Jawaban harus terstruktur, jelas, dan ringkas, terdiri dari maksimal 3 paragraf. Setiap paragraf tidak boleh lebih dari 8 kalimat."
        )

        response = model_gemini.generate_content([prompt, image_input])
        # Hapus file yang diunggah ke Gemini setelah digunakan jika perlu (opsional, tergantung kebijakan)
        # genai.delete_file(image_input.name)
        return response.text if response.text else "Tidak ada teks yang dihasilkan oleh Gemini."
    except Exception as e:
        app.logger.error(f"Error saat menghubungi Gemini API: {e}")
        if "google.api_core.exceptions.NotFound: 404" in str(e) and "Requested entity was not found" in str(e):
            app.logger.error(f"GEMINI ERROR: Pastikan file gambar ada di path: {image_path_for_gemini} dan dapat diakses oleh Gemini API.")
        return f"Gagal menghasilkan deskripsi dari Gemini: {e}"

def _process_image_data_and_save_detection(
    original_image_np: np.ndarray,
    user_id: int,
    upload_folder: str,
    gemini_api_key_present: bool
) -> Tuple[bool, str, Optional[int]]:
    """
    Memproses gambar NumPy, melakukan deteksi YOLO, menyimpan gambar,
    mendapatkan deskripsi Gemini, dan menyimpan hasil ke database.
    Menggunakan model global model_yolo_oil, model_yolo_human, dan model_yolo_motorcycle.
    Mengembalikan: (success_status, message_or_error, detection_id_if_success)
    """
    if model_yolo_oil is None and model_yolo_human is None and model_yolo_motorcycle is None:
        return False, "Tidak ada model YOLO yang dimuat.", None

    try:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_image_name = f"capture_{user_id}_{timestamp_str}"

        original_image_filename = f"{base_image_name}_original.jpg"
        absolute_original_image_path = os.path.join(upload_folder, original_image_filename)

        annotated_image_filename = f"{base_image_name}_annotated.jpg"
        absolute_annotated_image_path = os.path.join(upload_folder, annotated_image_filename)
        # Pastikan path relatif menggunakan forward slashes untuk kompatibilitas URL
        # Ini penting karena path ini disimpan ke DB dan digunakan oleh url_for.
        relative_annotated_image_path = f"uploads/{annotated_image_filename}"

        save_success = cv2.imwrite(absolute_original_image_path, original_image_np)
        if not save_success:
            return False, "Gagal menyimpan gambar asli.", None
        app.logger.info(f"Gambar asli dari browser disimpan di: {absolute_original_image_path}")

        annotated_image_to_save = original_image_np.copy()
        all_detection_details = [] # Untuk menyimpan string seperti "ClassName: Confidence% (Type)"
        all_detected_class_names = [] # Untuk menyimpan hanya ClassName
        class_for_gemini_description: Optional[str] = None # Variabel untuk kelas yang akan dideskripsikan Gemini

        # Initialize db_detected_class_name and db_confidence_score_str with defaults.
        # These will be overwritten if detections are found.
        db_detected_class_name: str = "Tidak ada objek terdeteksi"
        db_confidence_score_str: str =""

        # Deteksi Oli
        if model_yolo_oil:
            app.logger.info("Melakukan deteksi OLI...")
            results_oil = model_yolo_oil(original_image_np, verbose=False)
            if results_oil and results_oil[0].boxes:
                # Eksplisit menampilkan confidence (akurasi) dan label
                annotated_image_to_save = results_oil[0].plot(
                    img=annotated_image_to_save,
                    conf=True, labels=True)
                app.logger.info(f"Deteksi OLI ditemukan: {len(results_oil[0].boxes)} objek.")
                for i, box in enumerate(results_oil[0].boxes):
                    class_id = int(box.cls[0].item())
                    class_name = model_yolo_oil.names.get(class_id, f"UnknownOilClass{class_id}")
                    confidence = float(box.conf[0].item())
                    all_detection_details.append(f"{class_name}: {confidence*100:.2f}% (Oli)")
                    all_detected_class_names.append(class_name) # Tambahkan ke daftar semua kelas
                    if i == 0 and not class_for_gemini_description: # Prioritaskan oli pertama untuk Gemini
                        class_for_gemini_description = class_name
            else:
                app.logger.info("Tidak ada OLI yang terdeteksi.")
        else:
            app.logger.warning("Model deteksi OLI tidak dimuat.")

        # Deteksi Manusia
        if model_yolo_human:
            app.logger.info("Melakukan deteksi MANUSIA...")
            results_human = model_yolo_human(original_image_np, verbose=False) # Selalu gunakan original_image_np untuk input model
            if results_human and results_human[0].boxes:
                # Eksplisit menampilkan confidence (akurasi) dan label
                annotated_image_to_save = results_human[0].plot(
                    img=annotated_image_to_save,
                    conf=True, labels=True)
                app.logger.info(f"Deteksi MANUSIA ditemukan: {len(results_human[0].boxes)} objek.")
                for i, box in enumerate(results_human[0].boxes): # Tambahkan 'i' untuk konsistensi
                    class_id = int(box.cls[0].item())
                    class_name = model_yolo_human.names.get(class_id, f"UnknownHumanClass{class_id}")
                    confidence = float(box.conf[0].item())
                    all_detection_details.append(f"{class_name}: {confidence*100:.2f}% (Manusia)")
                    all_detected_class_names.append(class_name) # Tambahkan ke daftar semua kelas
                    if i == 0 and not class_for_gemini_description: # Jika oli tidak diprioritaskan, ambil manusia pertama
                        class_for_gemini_description = class_name
            else:
                app.logger.info("Tidak ada MANUSIA yang terdeteksi.")
        else:
            app.logger.warning("Model deteksi MANUSIA tidak dimuat.")

        # Deteksi Merek dan Warna Motor
        if model_yolo_motorcycle:
            app.logger.info("Melakukan deteksi MEREK/WARNA MOTOR...")
            results_motorcycle = model_yolo_motorcycle(original_image_np, verbose=False) # Selalu gunakan original_image_np untuk input model
            if results_motorcycle and results_motorcycle[0].boxes:
                # Eksplisit menampilkan confidence (akurasi) dan label
                annotated_image_to_save = results_motorcycle[0].plot(
                    img=annotated_image_to_save,
                    conf=True, labels=True)
                app.logger.info(f"Deteksi MEREK/WARNA MOTOR ditemukan: {len(results_motorcycle[0].boxes)} objek.")
                for i, box in enumerate(results_motorcycle[0].boxes):
                    class_id = int(box.cls[0].item())
                    class_name = model_yolo_motorcycle.names.get(class_id, f"UnknownMotorcycleClass{class_id}")
                    confidence = float(box.conf[0].item())
                    all_detection_details.append(f"{class_name}: {confidence*100:.2f}% (Motor)")
                    all_detected_class_names.append(class_name) # Tambahkan ke daftar semua kelas
                    if i == 0 and not class_for_gemini_description: # Jika oli/manusia tidak diprioritaskan, ambil motor pertama
                        class_for_gemini_description = class_name
            else:
                app.logger.info("Tidak ada MEREK/WARNA MOTOR yang terdeteksi.")
        else:
            app.logger.warning("Model deteksi MEREK/WARNA MOTOR tidak dimuat.")

        if all_detected_class_names:
            db_detected_class_name = ", ".join(sorted(list(set(all_detected_class_names))))
            # Only update confidence string if there are actual details.
            # This ensures that if all_detection_details somehow ends up empty
            # (despite all_detected_class_names being populated), we use the default "N/A".
            if all_detection_details:
                db_confidence_score_str = ", ".join(all_detection_details)

        # Simpan gambar yang dipilih (asli atau teranotasi) ke path anotasi
        log_prefix_for_annotated_save = "Gambar teranotasi (gabungan)" if all_detection_details else "Gambar asli (tidak ada deteksi)"
        if not cv2.imwrite(absolute_annotated_image_path, annotated_image_to_save):
            error_msg = f"KRITIS: Gagal menyimpan {log_prefix_for_annotated_save.lower()} ke {absolute_annotated_image_path}."
            app.logger.critical(error_msg)
            return False, error_msg, None
        app.logger.info(f"{log_prefix_for_annotated_save} berhasil disimpan di: {absolute_annotated_image_path}")

        # Deskripsi Gemini (prioritas oli, kemudian manusia, kemudian motor)
        generative_desc = "Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan."
        if gemini_api_key_present and class_for_gemini_description:
            app.logger.info(f"Meminta deskripsi Gemini untuk kelas: {class_for_gemini_description}")
            generative_desc = get_gemini_description(absolute_original_image_path, class_for_gemini_description)
        elif not gemini_api_key_present:
            generative_desc = "Fitur deskripsi Gemini tidak aktif (API Key tidak ditemukan atau error konfigurasi)."
        elif gemini_api_key_present and not class_for_gemini_description and all_detection_details: # Ada deteksi lain, tapi bukan prioritas
            generative_desc = "Deskripsi Gemini tidak dihasilkan (tidak ada objek prioritas (oli/manusia/motor) yang terdeteksi sebagai fokus utama untuk analisis, namun objek lain mungkin terdeteksi)."
        elif gemini_api_key_present and not all_detection_details: # Tidak ada deteksi sama sekali
             generative_desc = "Deskripsi Gemini tidak dihasilkan (tidak ada objek yang terdeteksi)."

        db_conn = None
        cursor = None
        try:
            db_conn = get_db_connection()
            if not db_conn:
                return False, "Gagal terhubung ke database untuk menyimpan deteksi.", None

            cursor = db_conn.cursor()
            sql = "INSERT INTO detections (user_id, image_name, image_path, detection_class, confidence_score, generative_description, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            current_timestamp = datetime.now()
            val = (user_id,
                   annotated_image_filename,
                   relative_annotated_image_path,
                   db_detected_class_name,
                   db_confidence_score_str,
                   generative_desc,
                   current_timestamp)
            cursor.execute(sql, val)
            db_conn.commit()
            detection_id = cursor.lastrowid
            return True, "Deteksi berhasil diproses dan disimpan.", detection_id
        except mysql.connector.Error as db_err:
            app.logger.error(f"Gagal menyimpan hasil deteksi ke database: {db_err}")
            if db_conn and db_conn.is_connected(): db_conn.rollback()
            return False, f"Gagal menyimpan hasil deteksi ke database: {db_err}", None
        finally:
            if cursor: cursor.close()
            if db_conn and db_conn.is_connected(): db_conn.close()

    except Exception as e:
        app.logger.error(f"Kesalahan tak terduga saat memproses gambar: {e}", exc_info=True)
        return False, f"Terjadi kesalahan tak terduga saat memproses gambar: {e}", None

@app.route('/process_browser_capture', methods=['POST'])
@login_required
def process_browser_capture() -> Tuple[Dict[str, Any], int]:
    if not model_yolo_oil and not model_yolo_human and not model_yolo_motorcycle: # Cek apakah setidaknya satu model dimuat
        return {"status": "error", "message": "Tidak ada model YOLO yang berhasil dimuat."}, 503

    data = request.get_json()
    if not data or 'image_data_url' not in data:
        return {"status": "error", "message": "Data gambar tidak ditemukan dalam permintaan."}, 400

    image_data_url = data['image_data_url']

    try:
        # Pisahkan header dari data base64
        # Format data URL: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
        header, encoded_data = image_data_url.split(',', 1)
        image_bytes = base64.b64decode(encoded_data)
        image_np = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

        if image_np is None:
            return {"status": "error", "message": "Gagal mendekode data gambar dari base64."}, 400

        user_id = session['user_id']

        success, message, detection_id = _process_image_data_and_save_detection(
            image_np,
            user_id,
            app.config['UPLOAD_FOLDER'],
            bool(GEMINI_API_KEY)
        )

        if success and detection_id is not None:
            return {"status": "success", "redirect_url": url_for('hasil', detection_id=detection_id), "message": message}, 200
        else:
            return {"status": "error", "message": message or "Gagal memproses gambar."}, 500

    except Exception as e:
        app.logger.error(f"Error di /process_browser_capture: {e}", exc_info=True)
        return {"status": "error", "message": f"Kesalahan server internal: {str(e)}"}, 500

@app.route('/get_snapshot_for_canvas')
@login_required
def get_snapshot_for_canvas() -> Tuple[Dict[str, Any], int]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return {"status": "error", "message": "IP Kamera tidak dikonfigurasi."}, 400

    # Tidak perlu cek model YOLO di sini karena ini hanya untuk mengambil snapshot mentah
    # Pengecekan model dilakukan saat pemrosesan.

    # Tentukan URL dan metode capture berdasarkan apakah CAMERA_CAPTURE_PATH adalah stream atau bukan
    # Ini penting untuk menghindari timeout pada /stream jika menggunakan requests.get().content
    # Kita asumsikan jika CAMERA_CAPTURE_PATH sama dengan CAMERA_STREAM_PATH, itu adalah MJPEG stream.
    capture_path_to_use = str(CAMERA_CAPTURE_PATH) # Ensure it's a string
    snapshot_url = f"{camera_base_ip}{capture_path_to_use}"
    app.logger.info(f"Snapshot for Canvas: Mencoba mengambil gambar dari {snapshot_url}")

    if capture_path_to_use == CAMERA_STREAM_PATH:
        app.logger.info(f"Snapshot for Canvas: Menggunakan OpenCV untuk mengambil frame dari stream URL: {snapshot_url}")
        # Sesuaikan timeout untuk OpenCV jika perlu, misal open_stream_timeout_sec=15, read_frame_timeout=10
        image_np, error_msg = capture_single_frame_from_stream_cv2(
            snapshot_url, open_stream_timeout_sec=20, read_frame_timeout=10
        )
    else: # Asumsikan ini adalah endpoint snapshot statis
        image_np, error_msg = capture_single_frame_from_http_endpoint(
            snapshot_url, timeout=CAMERA_REQUEST_TIMEOUT # Timeout 60s mungkin terlalu lama untuk snapshot
        )
    if error_msg or image_np is None:
        app.logger.error(f"Snapshot for Canvas: Error - {error_msg}")
        return {"status": "error", "message": error_msg or "Gagal mengambil snapshot dari kamera."}, 502

    try:
        is_success, buffer = cv2.imencode(".jpg", image_np)
        if not is_success:
            return {"status": "error", "message": "Gagal meng-encode snapshot ke JPEG."}, 500

        image_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        return {"status": "success", "image_data_url": image_data_url}, 200
    except Exception as e:
        app.logger.error(f"Snapshot for Canvas: Error encoding image - {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Kesalahan saat memproses snapshot: {str(e)}"}, 500

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
def api_capture_and_process() -> Union[FlaskResponse, WerkzeugResponse, Tuple[Dict[str, Any], int]]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return {"error": "Alamat IP Kamera belum dikonfigurasi."}, 503

    if not model_yolo_oil and not model_yolo_human and not model_yolo_motorcycle:
        return {"error": "Tidak ada model YOLO yang berhasil dimuat."}, 503

    # Tentukan URL dan metode capture
    capture_path_to_use = str(CAMERA_CAPTURE_PATH) # Ensure it's a string
    single_image_capture_url: str = f"{camera_base_ip}{capture_path_to_use}"
    app.logger.info(f"API Capture: Mencoba mengambil gambar dari URL = {single_image_capture_url}")

    try:
        img_np: Optional[np.ndarray] = None
        error_msg: Optional[str] = None

        if capture_path_to_use == CAMERA_STREAM_PATH:
            app.logger.info(f"API Capture: Menggunakan OpenCV untuk mengambil frame dari stream URL: {single_image_capture_url}")
            img_np, error_msg = capture_single_frame_from_stream_cv2(
                single_image_capture_url, open_stream_timeout_sec=20, read_frame_timeout=10
            )
        else: # Asumsikan endpoint snapshot statis
            img_np, error_msg = capture_single_frame_from_http_endpoint(
                single_image_capture_url, timeout=CAMERA_REQUEST_TIMEOUT)

        if error_msg or img_np is None:
            app.logger.error(f"API Error capturing frame from ({single_image_capture_url}): {error_msg}")
            return {"error": f"Gagal mengambil gambar dari kamera ({CAMERA_CAPTURE_PATH}): {error_msg}"}, 502

        try:
            annotated_image_bgr_np = img_np.copy() # Mulai dengan gambar asli

            # Proses dengan model oli jika ada
            if model_yolo_oil:
                results_oil = model_yolo_oil(img_np, verbose=False)
                if results_oil and results_oil[0].boxes:
                    # Eksplisit menampilkan confidence (akurasi) dan label
                    annotated_image_bgr_np = results_oil[0].plot(
                        img=annotated_image_bgr_np,
                        conf=True, labels=True)

            # Proses dengan model manusia jika ada
            if model_yolo_human:
                results_human = model_yolo_human(img_np, verbose=False) # Gunakan img_np asli untuk input model
                if results_human and results_human[0].boxes:
                    # Eksplisit menampilkan confidence (akurasi) dan label
                    annotated_image_bgr_np = results_human[0].plot(
                        img=annotated_image_bgr_np,
                        conf=True, labels=True)

            # Proses dengan model merek/warna motor jika ada
            if model_yolo_motorcycle:
                results_motorcycle = model_yolo_motorcycle(img_np, verbose=False) # Gunakan img_np asli untuk input model
                if results_motorcycle and results_motorcycle[0].boxes:
                    # Eksplisit menampilkan confidence (akurasi) dan label
                    annotated_image_bgr_np = results_motorcycle[0].plot(
                        img=annotated_image_bgr_np,
                        conf=True, labels=True)


            # Konversi array NumPy (BGR) ke format JPEG bytes
            encode_success, image_buffer = cv2.imencode('.jpg', annotated_image_bgr_np)
            if not encode_success:
                app.logger.error("API Error: Gagal meng-encode gambar hasil anotasi ke JPEG.")
                return {"error": "Gagal memproses gambar hasil anotasi."}, 500

            processed_image_bytes = image_buffer.tobytes()
            return FlaskResponse(processed_image_bytes, mimetype='image/jpeg')

        except Exception as yolo_err:
            app.logger.error(f"API Error saat pemrosesan YOLO: {yolo_err}", exc_info=True)
            return {"error": f"Error saat pemrosesan YOLO: {str(yolo_err)}"}, 500

    # Error dari capture_single_frame_from_stream_cv2 sudah ditangani di atas
    # Error dari capture_single_frame_from_http_endpoint juga sudah ditangani
    except Exception as e:
        app.logger.error(f"API Error internal: {e}", exc_info=True)
        return {"error": f"Terjadi kesalahan internal server: {str(e)}"}, 500

@app.route('/hasil/<int:detection_id>')
@login_required
def hasil(detection_id: int) -> Union[str, WerkzeugResponse]:
    detection_data: Optional[Dict[str, Any]] = None
    conn = get_db_connection()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections WHERE id = %s AND user_id = %s", (detection_id, session['user_id']))
            detection_data = cursor.fetchone() # type: ignore[assignment]
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

@app.route('/hapus_deteksi/<int:detection_id>', methods=['GET']) # Sebaiknya POST untuk aksi destruktif, tapi GET digunakan sesuai link di HTML
@login_required
def hapus_deteksi(detection_id: int) -> WerkzeugResponse:
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            # get_db_connection sudah flash message jika gagal
            return redirect(url_for('histori'))

        cursor = conn.cursor(dictionary=True)

        # 1. Ambil detail deteksi untuk mendapatkan nama file gambar
        cursor.execute("SELECT image_name FROM detections WHERE id = %s AND user_id = %s",
                       (detection_id, session['user_id'])) # type: ignore[assignment]
        detection_row: Optional[Dict[str, Any]] = cursor.fetchone() # type: ignore[assignment]

        if not detection_row:
            flash('Riwayat deteksi tidak ditemukan atau Anda tidak memiliki izin untuk menghapusnya.', 'warning')
            return redirect(url_for('histori'))

        # 2. Hapus file gambar terkait
        image_name_from_db = str(detection_row['image_name']) # Ini adalah nama file anotasi

        # Path absolut ke file anotasi
        annotated_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name_from_db)

        # Path absolut ke file original (berdasarkan konvensi penamaan)
        # "capture_USERID_TIMESTAMP_annotated.jpg" -> "capture_USERID_TIMESTAMP_original.jpg"
        original_image_filename = None
        if image_name_from_db.endswith("_annotated.jpg"):
            base_filename = image_name_from_db[:-len("_annotated.jpg")] # Menghapus "_annotated.jpg" untuk mendapatkan nama dasar
            original_image_filename = f"{base_filename}_original.jpg"
            original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], original_image_filename)

            if os.path.exists(original_image_path):
                os.remove(original_image_path)
                app.logger.info(f"File original dihapus: {original_image_path}")
            else:
                app.logger.warning(f"File original tidak ditemukan (tidak jadi dihapus): {original_image_path}")

        if os.path.exists(annotated_image_path):
            os.remove(annotated_image_path)
            app.logger.info(f"File anotasi dihapus: {annotated_image_path}")
        else:
            app.logger.warning(f"File anotasi tidak ditemukan (tidak jadi dihapus): {annotated_image_path}")

        # 3. Hapus record dari database (setelah file berhasil/gagal dihapus)
        cursor.execute("DELETE FROM detections WHERE id = %s AND user_id = %s",
                       (detection_id, session['user_id']))
        conn.commit()

        flash('Riwayat deteksi berhasil dihapus.', 'success')

    except mysql.connector.Error as err:
        app.logger.error(f'Gagal menghapus riwayat deteksi dari DB: {err}')
        flash(f'Gagal menghapus riwayat deteksi: {err}', 'danger')
        if conn and conn.is_connected(): conn.rollback()
    except OSError as e: # Menangani error saat operasi file (misal: os.remove)
        app.logger.error(f'Gagal menghapus file gambar terkait: {e}')
        flash(f'Gagal menghapus file gambar terkait: {e}. Data dari database mungkin masih ada atau sudah terhapus.', 'danger')
        # Jika terjadi error saat menghapus file, idealnya transaksi DB juga di-rollback
        # Namun, karena conn.commit() ada setelah operasi file, jika OSError terjadi,
        # commit DB tidak akan tercapai. Jadi, data DB aman (tidak terhapus jika file gagal dihapus).
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return redirect(url_for('histori'))

@app.route('/logout')
@login_required
def logout() -> WerkzeugResponse:
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
    app.logger.error(f"Internal Server Error: {e}", exc_info=True)
    return render_template('errors/500.html', title="Kesalahan Server"), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    