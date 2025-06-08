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
import base64 # Untuk decode base64 image dari client
import time # Digunakan dalam fungsi capture_single_frame_from_stream_cv2
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
CAMERA_REQUEST_TIMEOUT = int(os.getenv("CAMERA_REQUEST_TIMEOUT", "60"))
CAMERA_VERIFY_TIMEOUT = int(os.getenv("CAMERA_VERIFY_TIMEOUT", "30")) # Timeout untuk verifikasi koneksi IP

# CAMERA_STREAM_PATH dan CAMERA_CAPTURE_PATH diatur secara eksplisit
# untuk memastikan kesesuaian dengan endpoint yang tetap di firmware ESP32-CAM.
CAMERA_STREAM_PATH = "/stream" # Untuk live view di dashboard/uji_kamera
CAMERA_CAPTURE_PATH = "/stream" # Default ke /stream, bisa diubah jika ada endpoint snapshot khusus seperti /capture
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

    # Verifikasi bisa menggunakan stream path atau capture path.
    # Stream path lebih baik untuk verifikasi "keaktifan" kamera.
    verify_url = f"{base_url}{CAMERA_STREAM_PATH}" 
    print(f"Verifying camera connection to: {verify_url} with timeout {CAMERA_VERIFY_TIMEOUT}s")

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
                         print(f"Verification successful for {ip_address}. Received initial data from stream.")
                         return True, "Koneksi stream berhasil diverifikasi."
                     else:
                             print(f"Verification failed for {ip_address}: Stream responded with 200 OK but no initial data was received (empty stream or connection closed prematurely).")
                             return False, "Koneksi stream berhasil dibuka (200 OK), tetapi tidak ada data stream awal yang diterima. Pastikan kamera mengirimkan data."
                 except requests.exceptions.RequestException as e:
                      print(f"Verification error for {ip_address}: Failed to read initial data chunk from stream - {e}")
                      return False, f"Koneksi stream berhasil, tetapi gagal membaca data stream awal: {e}"
            else:
                print(f"Verification failed for {ip_address}: Stream endpoint responded with status code {response.status_code}")
                return False, f"Server stream merespons dengan status code: {response.status_code}"
    except requests.exceptions.Timeout:
        print(f"Verification failed for {ip_address}: Timeout after {CAMERA_VERIFY_TIMEOUT}s on stream endpoint.")
        return False, f"Timeout saat mencoba terhubung ke stream setelah {CAMERA_VERIFY_TIMEOUT} detik."
    except requests.exceptions.RequestException as e:
        print(f"Verification failed for {ip_address}: Connection Error on stream endpoint - {e}")
        return False, f"Gagal terhubung ke stream: {e}"
    except Exception as e:
        print(f"Verification failed for {ip_address}: Unexpected Error on stream endpoint - {e}")
        return False, f"Terjadi kesalahan tak terduga saat verifikasi stream: {e}"

print(f"  Path Stream Kamera (untuk live view): {CAMERA_STREAM_PATH}")
print(f"  Path Capture Kamera (untuk deteksi): {CAMERA_CAPTURE_PATH}")
print(f"  Timeout Request Kamera: {CAMERA_REQUEST_TIMEOUT} detik")
print(f"  Timeout Verifikasi Kamera: {CAMERA_VERIFY_TIMEOUT} detik")
print(f"  PENTING: Pastikan 'Path Capture' ({CAMERA_CAPTURE_PATH}) dan 'Path Stream' ({CAMERA_STREAM_PATH}) sesuai dengan endpoint di firmware ESP32-CAM Anda.")

def capture_single_frame_from_http_endpoint(capture_url: str, 
                                            timeout: int = 10) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mengambil satu frame gambar dari HTTP endpoint (misalnya, ESP32-CAM /capture_image).
    Mengembalikan (frame_numpy_array, error_message).
    """
    try:
        print(f"Mencoba mengambil gambar dari HTTP endpoint: {capture_url} dengan timeout {timeout}s")
        response = requests.get(capture_url, timeout=timeout)
        response.raise_for_status()  # Akan raise HTTPError untuk status code 4xx/5xx

        content_type = response.headers.get('content-type', '').lower()
        if 'image' not in content_type:
            print(f"Peringatan: Content-Type dari {capture_url} adalah '{content_type}', diharapkan mengandung 'image'. Tetap mencoba memproses.")
        
        image_bytes = response.content
        if not image_bytes:
            return None, f"Tidak ada data gambar yang diterima dari {capture_url}."

        image_np = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        if image_np is None:
            return None, f"Gagal mendekode data gambar dari {capture_url}. Pastikan endpoint mengembalikan format gambar yang valid (JPEG, PNG, dll)."
        
        print(f"Gambar berhasil diambil dan didekode dari {capture_url}")
        return image_np, None

    except requests.exceptions.Timeout:
        error_msg = f"Timeout ({timeout}s) saat mencoba mengambil gambar dari {capture_url}."
        print(error_msg)
        return None, error_msg
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error saat mengambil gambar dari {capture_url}: {http_err} (Status: {http_err.response.status_code if http_err.response else 'N/A'})"
        print(error_msg)
        return None, error_msg
    except requests.exceptions.RequestException as req_err:
        error_msg = f"Kesalahan koneksi saat mengambil gambar dari {capture_url}: {req_err}"
        print(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Kesalahan tak terduga saat mengambil gambar dari {capture_url}: {str(e)}"
        print(error_msg)
        return None, error_msg

# Fungsi capture_single_frame_from_stream_cv2 dipertahankan jika diperlukan di masa depan,
# tetapi tidak lagi digunakan oleh capture_and_detect atau api_capture_and_process.

def capture_single_frame_from_stream_cv2(stream_url: str, 
                                         read_frame_timeout: int = 10, 
                                         open_stream_timeout_sec: int = 60) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mengambil satu frame dari network stream menggunakan OpenCV.
    Mengembalikan (frame_numpy_array, error_message).
    `read_frame_timeout` adalah timeout (detik) untuk loop pembacaan frame setelah stream dibuka.
    `open_stream_timeout_sec` adalah timeout (detik) yang disarankan untuk FFmpeg saat membuka stream.
    """
    cap = None
    original_ffmpeg_options = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
    # FFmpeg timeout options (timeout, rw_timeout) adalah dalam mikrodetik.
    ffmpeg_timeout_us = str(open_stream_timeout_sec * 1000 * 1000) 
    
    # Opsi 'timeout' untuk koneksi TCP, 'rw_timeout' untuk operasi baca/tulis setelah terkoneksi.
    # Format: "key1;value1|key2;value2"
    # Mengatur timeout koneksi dan read/write ke open_stream_timeout_sec detik.
    ffmpeg_options_to_set = f"timeout;{ffmpeg_timeout_us}|rw_timeout;{ffmpeg_timeout_us}"
    
    print(f"Mengatur OPENCV_FFMPEG_CAPTURE_OPTIONS sementara ke: {ffmpeg_options_to_set} untuk stream: {stream_url}")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ffmpeg_options_to_set

    cap = None # Initialize cap here for the finally block
    try:
        max_open_attempts = 3
        attempt_delay_sec = 1.5  # Tingkatkan delay antar percobaan menjadi 1.5 detik

        for attempt in range(max_open_attempts):
            print(f"Mencoba membuka stream dengan OpenCV: {stream_url} (Attempt {attempt + 1}/{max_open_attempts})")
            # Menggunakan cv2.CAP_FFMPEG secara eksplisit untuk memastikan backend yang benar
            # dan agar OPENCV_FFMPEG_CAPTURE_OPTIONS lebih mungkin diterapkan.
            current_cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
            
            if current_cap.isOpened():
                cap = current_cap # Assign to the outer scope cap
                print(f"Stream berhasil dibuka pada attempt {attempt + 1}")
                break
            else:
                print(f"Gagal membuka stream pada attempt {attempt + 1} (cap.isOpened() false). Menunggu {attempt_delay_sec}s sebelum mencoba lagi...")
                if current_cap is not None: # Release if VideoCapture object was created but not opened
                    current_cap.release()
                if attempt < max_open_attempts - 1: # Don't sleep on the last attempt
                    time.sleep(attempt_delay_sec)
        
        if cap is None or not cap.isOpened(): # Check after all attempts
            error_msg = (f"Gagal membuka stream kamera di {stream_url} setelah {max_open_attempts} percobaan. "
                         "Pastikan kamera aktif, stream URL benar, dan tidak ada klien lain yang menggunakan stream secara eksklusif (misalnya, tab browser lain atau aplikasi lain). "
                         "Jika Anda baru saja menghentikan stream di browser, tunggu beberapa saat sebelum mencoba lagi.")
            print(error_msg)
            return None, error_msg

        start_time = time.time()
        frame: Optional[np.ndarray] = None
        ret = False
        # Mencoba membaca beberapa frame untuk mendapatkan yang terbaru, membuang yang lama jika ada buffer.
        # Untuk beberapa stream, frame pertama mungkin lama atau butuh waktu untuk tiba.
        for i in range(5): # Coba ambil hingga 5 frame, ambil yang terakhir berhasil
            if time.time() - start_time > read_frame_timeout:
                error_msg = f"Timeout ({read_frame_timeout}s) saat menunggu frame dari {stream_url} setelah berhasil dibuka (percobaan ke-{i+1})."
                print(error_msg)
                # Jangan return di sini dulu, biarkan cap.release() di finally
                break 
            
            temp_ret, temp_frame = cap.read()
            if temp_ret and temp_frame is not None:
                ret = True
                frame = temp_frame
                print(f"Frame berhasil dibaca pada percobaan ke-{i+1} dari {stream_url}")
            else:
                print(f"Gagal membaca frame pada percobaan ke-{i+1} dari {stream_url}. ret={temp_ret}")
                time.sleep(0.2) # Jeda singkat jika read gagal
        
        if not ret or frame is None:
            return None, f"Gagal membaca frame dari stream {stream_url} setelah beberapa percobaan."
        return frame, None
    except Exception as e:
        return None, f"Error saat menggunakan cv2.VideoCapture untuk {stream_url}: {str(e)}"
    finally:
        # Kembalikan OPENCV_FFMPEG_CAPTURE_OPTIONS ke nilai semula
        if original_ffmpeg_options is None:
            if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ:
                del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
                print(f"OPENCV_FFMPEG_CAPTURE_OPTIONS dihapus (kembali ke default system) untuk stream: {stream_url}")
        else:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = original_ffmpeg_options
            print(f"OPENCV_FFMPEG_CAPTURE_OPTIONS dikembalikan ke: {original_ffmpeg_options} untuk stream: {stream_url}")

        if cap is not None:
            print(f"Melepaskan VideoCapture untuk {stream_url}")
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
                # Mengganti flash generik dengan pesan selamat datang yang lebih spesifik
                flash(f"Selamat datang, {user['username']}!", 'success')
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
        # Mengganti model lama 'gemini-pro-vision' dengan model yang lebih baru dan disarankan.
        # 'gemini-1.5-flash-latest' adalah pilihan yang baik untuk kecepatan dan biaya.
        model_gemini = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Pastikan file ada sebelum mencoba mengunggah
        if not os.path.exists(image_path_for_gemini):
            print(f"GEMINI ERROR: File gambar tidak ditemukan di path: {image_path_for_gemini}")
            return f"Gagal menghasilkan deskripsi: File gambar sumber tidak ditemukan ({os.path.basename(image_path_for_gemini)})."

        image_input = genai.upload_file(image_path_for_gemini)
        prompt = (
            f"Analisis gambar ini yang diduga menunjukkan kondisi oli sepeda motor. "
            f"Model deteksi objek mengidentifikasi area/objek utama sebagai '{detected_class_name}'.\n\n"
            f"Berdasarkan visual pada gambar dan identifikasi '{detected_class_name}', jelaskan kondisi kualitas oli tersebut. "
            f"Berikan juga rekomendasi perawatan atau penggantian oli yang relevan, serta saran umum terkait penggunaan oli tersebut "
            f"untuk menjaga performa mesin sepeda motor.\n\n"
            f"PENTING: Jawaban harus terdiri dari maksimal 3 paragraf. Setiap paragraf tidak boleh lebih dari 6 kalimat. "
            f"Gunakan bahasa yang jelas dan ringkas."
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

def _process_image_data_and_save_detection(
    original_image_np: np.ndarray, 
    user_id: int, 
    upload_folder: str, 
    yolo_model: Optional[YOLO],
    gemini_api_key_present: bool
) -> Tuple[bool, str, Optional[int]]:
    """
    Memproses gambar NumPy, melakukan deteksi YOLO, menyimpan gambar, 
    mendapatkan deskripsi Gemini, dan menyimpan hasil ke database.

    Mengembalikan: (success_status, message_or_error, detection_id_if_success)
    """
    if yolo_model is None:
        return False, "Model YOLO tidak dimuat.", None

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
        print(f"Gambar asli dari browser disimpan di: {absolute_original_image_path}")

        print("Melakukan deteksi YOLO pada frame (in-memory) yang diterima dari browser.")
        results = yolo_model(original_image_np, verbose=False)

        detected_class_name = "Tidak Terdeteksi"
        confidence_score_str = "0.00%"
        generative_desc = "Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan."

        # Tentukan gambar mana yang akan disimpan ke annotated_path (bisa gambar asli jika tidak ada deteksi/error plot)
        image_to_save_for_annotated_path = original_image_np
        log_prefix_for_annotated_save = "Gambar asli (sebagai fallback untuk anotasi)"

        if results and results[0].boxes:
            first_detection_box = results[0].boxes[0] 
            class_id = int(first_detection_box.cls[0].item())
            detected_class_name = yolo_model.names.get(class_id, f"Unknown Class {class_id}")
            confidence_score_val = float(first_detection_box.conf[0].item())
            confidence_score_str = f"{confidence_score_val*100:.2f}%"
            print(f"Deteksi: {detected_class_name} dengan akurasi: {confidence_score_str}")

            try:
                plotted_image_np = results[0].plot()
                image_to_save_for_annotated_path = plotted_image_np
                log_prefix_for_annotated_save = "Gambar teranotasi"
            except Exception as plot_err:
                print(f"Error saat membuat gambar anotasi: {plot_err}. Menggunakan gambar asli untuk path anotasi.")
                # image_to_save_for_annotated_path tetap original_image_np
        else:
            print("Tidak ada objek yang terdeteksi oleh YOLO. Menggunakan gambar asli untuk path anotasi.")
            # image_to_save_for_annotated_path tetap original_image_np

        # Simpan gambar yang dipilih (asli atau teranotasi) ke path anotasi dan periksa keberhasilannya
        if not cv2.imwrite(absolute_annotated_image_path, image_to_save_for_annotated_path):
            error_msg = f"KRITIS: Gagal menyimpan {log_prefix_for_annotated_save.lower()} ke {absolute_annotated_image_path}."
            print(error_msg)
            return False, error_msg, None # Penting: jangan buat entri DB jika penyimpanan ini gagal.
        print(f"{log_prefix_for_annotated_save} berhasil disimpan di: {absolute_annotated_image_path}")

        if gemini_api_key_present and detected_class_name != "Tidak Terdeteksi": # Hanya panggil Gemini jika ada deteksi
            generative_desc = get_gemini_description(absolute_original_image_path, detected_class_name)
        elif not gemini_api_key_present:
            generative_desc = "Fitur deskripsi Gemini tidak aktif (API Key tidak ditemukan)."

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
                   detected_class_name, 
                   confidence_score_str, 
                   generative_desc, 
                   current_timestamp)
            cursor.execute(sql, val)
            db_conn.commit()
            detection_id = cursor.lastrowid
            return True, "Deteksi berhasil diproses dan disimpan.", detection_id
        except mysql.connector.Error as err:
            print(f"Gagal menyimpan hasil deteksi ke database: {err}")
            if db_conn and db_conn.is_connected(): db_conn.rollback()
            return False, f"Gagal menyimpan hasil deteksi ke database: {err}", None
        finally:
            if cursor: cursor.close()
            if db_conn and db_conn.is_connected(): db_conn.close()

    except Exception as e:
        print(f"Kesalahan tak terduga saat memproses gambar: {e}")
        return False, f"Terjadi kesalahan tak terduga saat memproses gambar: {e}", None

@app.route('/process_browser_capture', methods=['POST'])
@login_required
def process_browser_capture() -> Union[FlaskResponse, Tuple[Dict[str, Any], int]]:
    if not model_yolo:
        return {"status": "error", "message": "Model YOLO tidak berhasil dimuat."}, 503

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
            model_yolo, 
            bool(GEMINI_API_KEY)
        )

        if success and detection_id is not None:
            return {"status": "success", "redirect_url": url_for('hasil', detection_id=detection_id), "message": message}, 200
        else:
            return {"status": "error", "message": message or "Gagal memproses gambar."}, 500

    except Exception as e:
        print(f"Error di /process_browser_capture: {e}")
        return {"status": "error", "message": f"Kesalahan server internal: {str(e)}"}, 500

@app.route('/get_snapshot_for_canvas')
@login_required
def get_snapshot_for_canvas() -> Union[FlaskResponse, Tuple[Dict[str, Any], int]]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return {"status": "error", "message": "IP Kamera tidak dikonfigurasi."}, 400

    # Meskipun tidak digunakan langsung untuk snapshot, ini bisa jadi indikasi sistem belum siap
    # if not model_yolo:
    #     return {"status": "error", "message": "Model YOLO tidak siap."}, 503

    # Tentukan URL dan metode capture berdasarkan apakah CAMERA_CAPTURE_PATH adalah stream atau bukan
    # Ini penting untuk menghindari timeout pada /stream jika menggunakan requests.get().content
    # Kita asumsikan jika CAMERA_CAPTURE_PATH sama dengan CAMERA_STREAM_PATH, itu adalah MJPEG stream.
    capture_path_to_use = CAMERA_CAPTURE_PATH
    snapshot_url = f"{camera_base_ip}{capture_path_to_use}"
    print(f"Snapshot for Canvas: Mencoba mengambil gambar dari {snapshot_url}")

    if capture_path_to_use == CAMERA_STREAM_PATH:
        print(f"Snapshot for Canvas: Menggunakan OpenCV untuk mengambil frame dari stream URL: {snapshot_url}")
        # Sesuaikan timeout untuk OpenCV jika perlu, misal open_stream_timeout_sec=15, read_frame_timeout=10
        image_np, error_msg = capture_single_frame_from_stream_cv2(
            snapshot_url, open_stream_timeout_sec=20, read_frame_timeout=10 
        )
    else: # Asumsikan ini adalah endpoint snapshot statis
        image_np, error_msg = capture_single_frame_from_http_endpoint(
            snapshot_url, timeout=CAMERA_REQUEST_TIMEOUT # Timeout 60s mungkin terlalu lama untuk snapshot
        )
    if error_msg or image_np is None:
        print(f"Snapshot for Canvas: Error - {error_msg}")
        return {"status": "error", "message": error_msg or "Gagal mengambil snapshot dari kamera."}, 502

    try:
        is_success, buffer = cv2.imencode(".jpg", image_np)
        if not is_success:
            return {"status": "error", "message": "Gagal meng-encode snapshot ke JPEG."}, 500
        
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{image_base64}"
        
        return {"status": "success", "image_data_url": image_data_url}, 200
    except Exception as e:
        print(f"Snapshot for Canvas: Error encoding image - {str(e)}")
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
def api_capture_and_process() -> Union[FlaskResponse, Tuple[Dict[str, str], int]]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return {"error": "Alamat IP Kamera belum dikonfigurasi."}, 503

    if not model_yolo:
        return {"error": "Model YOLO tidak berhasil dimuat."}, 503

    # Tentukan URL dan metode capture
    capture_path_to_use = CAMERA_CAPTURE_PATH
    single_image_capture_url: str = f"{camera_base_ip}{capture_path_to_use}"
    print(f"API Capture: Mencoba mengambil gambar dari URL = {single_image_capture_url}")

    try:
        img_np: Optional[np.ndarray] = None
        error_msg: Optional[str] = None

        if capture_path_to_use == CAMERA_STREAM_PATH:
            print(f"API Capture: Menggunakan OpenCV untuk mengambil frame dari stream URL: {single_image_capture_url}")
            img_np, error_msg = capture_single_frame_from_stream_cv2(
                single_image_capture_url, open_stream_timeout_sec=20, read_frame_timeout=10
            )
        else: # Asumsikan endpoint snapshot statis
            img_np, error_msg = capture_single_frame_from_http_endpoint(
                single_image_capture_url, timeout=CAMERA_REQUEST_TIMEOUT)
        if error_msg or img_np is None:
            print(f"API Error capture_single_frame_from_http_endpoint ({single_image_capture_url}): {error_msg}")
            return {"error": f"Gagal mengambil gambar dari kamera ({CAMERA_CAPTURE_PATH}): {error_msg}"}, 502

        try:
            # img_np sudah merupakan array NumPy (BGR) dari capture_single_frame_from_http_endpoint
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

    # Error dari capture_single_frame_from_stream_cv2 sudah ditangani di atas
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

@app.route('/hapus_deteksi/<int:detection_id>', methods=['GET']) # Sebaiknya POST untuk aksi destruktif, tapi GET sesuai link di HTML
@login_required
def hapus_deteksi(detection_id: int) -> FlaskResponse:
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
                       (detection_id, session['user_id']))
        detection = cursor.fetchone()

        if not detection:
            flash('Riwayat deteksi tidak ditemukan atau Anda tidak memiliki izin untuk menghapusnya.', 'warning')
            return redirect(url_for('histori'))

        # 2. Hapus file gambar terkait
        image_name_from_db = detection['image_name'] # Ini adalah nama file anotasi, misal: "capture_USERID_TIMESTAMP_annotated.jpg"
        
        # Path ke file anotasi
        annotated_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name_from_db)

        # Path ke file original (berdasarkan konvensi penamaan)
        # "capture_USERID_TIMESTAMP_annotated.jpg" -> "capture_USERID_TIMESTAMP_original.jpg"
        original_image_filename = None
        if image_name_from_db.endswith("_annotated.jpg"):
            base_filename = image_name_from_db[:-len("_annotated.jpg")] # Hapus "_annotated.jpg"
            original_image_filename = f"{base_filename}_original.jpg"
            original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], original_image_filename)

            if os.path.exists(original_image_path):
                os.remove(original_image_path)
                print(f"File original dihapus: {original_image_path}")
            else:
                print(f"File original tidak ditemukan (tidak dihapus): {original_image_path}")

        if os.path.exists(annotated_image_path):
            os.remove(annotated_image_path)
            print(f"File anotasi dihapus: {annotated_image_path}")
        else:
            print(f"File anotasi tidak ditemukan (tidak dihapus): {annotated_image_path}")

        # 3. Hapus record dari database
        cursor.execute("DELETE FROM detections WHERE id = %s AND user_id = %s", 
                       (detection_id, session['user_id']))
        conn.commit()

        flash('Riwayat deteksi berhasil dihapus.', 'success')

    except mysql.connector.Error as err:
        flash(f'Gagal menghapus riwayat deteksi: {err}', 'danger')
        if conn and conn.is_connected(): conn.rollback()
    except OSError as e: # Untuk error saat menghapus file
        flash(f'Gagal menghapus file gambar terkait: {e}', 'danger')
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    return redirect(url_for('histori'))

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
