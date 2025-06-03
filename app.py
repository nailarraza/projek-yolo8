# D:/projek-yolo8/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response as FlaskResponse # Mengganti nama Response agar tidak bentrok
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from functools import wraps # Untuk decorator login_required
from datetime import datetime
import google.generativeai as genai
from typing import Optional, Dict, Any, Tuple, Union # Import tipe yang dibutuhkan
from dotenv import load_dotenv # Untuk memuat variabel dari .env
import requests # <-- Tambahkan ini untuk mengambil gambar dari ESP32-CAM
from ultralytics import YOLO # Pastikan ultralytics terinstal
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
        GEMINI_API_KEY = None

# Konfigurasi Aplikasi
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex()) # Ambil dari .env atau generate baru
app.config['UPLOAD_FOLDER'] = 'app/static/uploads' # Tambahkan konfigurasi folder upload
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Buat folder jika belum ada

# Muat Model YOLOv8 sekali saat aplikasi dimulai
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', os.path.join('models_yolo', 'best.pt'))
try:
    model_yolo = YOLO(MODEL_PATH)
    print(f"Model YOLO berhasil dimuat dari {MODEL_PATH}")
except Exception as e:
    print(f"Error saat memuat model YOLO: {e}")
    model_yolo = None

# Konfigurasi Database MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_projek_yolo8") # Di README namanya projek_yolo8_db

# Konfigurasi Kamera (ESP32-CAM atau DroidCam)
# Nama variabel dipertahankan sebagai ESP32_CAM_* untuk konsistensi dengan kode yang ada,
# namun konfigurasi di .env dapat diubah untuk DroidCam atau sumber kamera IP lainnya.
RAW_CAMERA_IP = os.getenv("ESP32_CAM_IP")
CAMERA_BASE_IP = None # Akan diisi setelah pemeriksaan skema
CAMERA_REQUEST_TIMEOUT = int(os.getenv("CAMERA_REQUEST_TIMEOUT", "30")) # Default timeout 30 detik untuk request ke kamera

if RAW_CAMERA_IP:
    if not RAW_CAMERA_IP.startswith(('http://', 'https://')):
        CAMERA_BASE_IP = f"http://{RAW_CAMERA_IP}"
        print(f"INFO: Skema 'http://' ditambahkan secara otomatis ke ESP32_CAM_IP. IP Kamera efektif: {CAMERA_BASE_IP}")
    else:
        CAMERA_BASE_IP = RAW_CAMERA_IP
else:
    # Jika RAW_CAMERA_IP tidak ada, CAMERA_BASE_IP juga tidak akan ada.
    # Pesan peringatan akan dicetak nanti jika CAMERA_BASE_IP masih None.
    pass


CAMERA_STREAM_PATH = os.getenv("ESP32_CAM_STREAM_PATH", "/stream")
CAMERA_CAPTURE_PATH = os.getenv("ESP32_CAM_CAPTURE_PATH", "/capture")

if not CAMERA_BASE_IP:
    print("PERINGATAN: ESP32_CAM_IP (atau IP Kamera) tidak diatur di .env. Fitur kamera tidak akan berfungsi.")
else:
    print(f"Konfigurasi Kamera:")
    print(f"  IP Dasar Kamera: {CAMERA_BASE_IP}")
    print(f"  Path Stream: {CAMERA_STREAM_PATH}")
    print(f"  Path Capture: {CAMERA_CAPTURE_PATH}")
    print(f"  Timeout Request Kamera: {CAMERA_REQUEST_TIMEOUT} detik")
    print(f"  PENTING: Pastikan 'Path Capture' ({CAMERA_CAPTURE_PATH}) di atas SESUAI dengan endpoint di firmware ESP32-CAM Anda (misalnya, '/capture_image' jika menggunakan firmware yang disarankan). Atur ESP32_CAM_CAPTURE_PATH di file .env jika perlu.")

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
    return value
 
def get_db_connection() -> Optional[mysql.connector.MySQLConnection]:
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

def login_required(f: callable) -> callable:
    @wraps(f)
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
def login() -> Union[str, FlaskResponse]:
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
def dashboard() -> str:
    esp32_stream_url = None
    if CAMERA_BASE_IP:
        esp32_stream_url = f"{CAMERA_BASE_IP}{CAMERA_STREAM_PATH}"
        print(f"Dashboard: URL Stream Kamera = {esp32_stream_url}")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi di file .env.", "warning")

    return render_template('dashboard.html', 
                           title="Dashboard", 
                           username=session.get('username'),
                           esp32_cam_ip=CAMERA_BASE_IP, # Untuk ditampilkan di teks
                           esp32_stream_url=esp32_stream_url) # Untuk <img> src
 
def get_gemini_description(image_path_for_gemini: str, detected_class_name: str) -> str:
    """
    Fungsi untuk mendapatkan deskripsi dari Google Gemini API.
    """
    if not GEMINI_API_KEY or not genai:
        print("Gemini API tidak dikonfigurasi. Mengembalikan deskripsi default.")
        return "Deskripsi generatif tidak tersedia saat ini."
    try:
        model_gemini = genai.GenerativeModel('gemini-pro-vision') # atau model lain yang sesuai
        image_input = genai.upload_file(image_path_for_gemini) # Pastikan path ini bisa diakses
        prompt = f"Jelaskan kondisi oli berdasarkan gambar ini. Hasil deteksi menunjukkan bahwa ini adalah '{detected_class_name}'. Berikan penjelasan singkat dan saran jika ada."
        response = model_gemini.generate_content([prompt, image_input])
        return response.text if response.text else "Tidak ada teks yang dihasilkan oleh Gemini."
    except Exception as e:
        print(f"Error saat menghubungi Gemini API: {e}")
        # Cek apakah error karena file tidak ditemukan atau masalah API
        if "google.api_core.exceptions.NotFound: 404" in str(e) and "Requested entity was not found" in str(e):
            print(f"Pastikan file gambar ada di path: {image_path_for_gemini} dan dapat diakses oleh Gemini API.")
        return f"Gagal menghasilkan deskripsi dari Gemini: {e}"

@app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect() -> FlaskResponse:
    if not CAMERA_BASE_IP:
        flash("Alamat IP Kamera belum dikonfigurasi. Tidak dapat mengambil gambar.", "danger")
        return redirect(url_for('dashboard'))

    if not model_yolo:
        flash("Model YOLO tidak berhasil dimuat. Fitur deteksi tidak tersedia.", "danger")
        return redirect(url_for('dashboard'))

    capture_url = f"{CAMERA_BASE_IP}{CAMERA_CAPTURE_PATH}"
    print(f"Capture & Detect: Mencoba mengambil gambar dari URL = {capture_url}")

    request_headers = {'Connection': 'close'} # Tambahkan header ini
    try:
        response = requests.get(capture_url, headers=request_headers, timeout=CAMERA_REQUEST_TIMEOUT)
        response.raise_for_status() # Akan raise error jika status code 4xx atau 5xx
        # Validasi Content-Type dari respons ESP32-CAM
        content_type = response.headers.get('Content-Type')
        if not content_type or not content_type.startswith('image/'):
            error_message = f"Konten yang diterima dari ESP32-CAM bukan gambar (Content-Type: {content_type}). Pastikan URL capture ({capture_url}) sudah benar dan ESP32-CAM mengirimkan gambar."
            flash(error_message, "danger")
            print(f"Error: {error_message}. Response text (first 500 chars): {response.text[:500]}")
            print(f"Pastikan ESP32_CAM_CAPTURE_PATH di .env (saat ini '{CAMERA_CAPTURE_PATH}') sesuai dengan endpoint di firmware ESP32-CAM.")
            return redirect(url_for('dashboard'))
        # Simpan gambar yang ditangkap
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"capture_{session['user_id']}_{timestamp_str}.jpg"
        # Path disimpan relatif terhadap static folder agar bisa diakses dari template
        relative_image_path = os.path.join('uploads', image_name)
        absolute_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)

        with open(absolute_image_path, 'wb') as f:
            f.write(response.content)

        # Opsional: Validasi lebih lanjut menggunakan Pillow bahwa file yang disimpan adalah gambar valid
        # try:
        #     img = Image.open(absolute_image_path)
        #     img.verify() # Memverifikasi header gambar
        #     # Untuk beberapa format, file perlu dibuka kembali setelah verify
        #     # img = Image.open(absolute_image_path)
        #     # img.load() # Memuat data gambar sepenuhnya
        # except Exception as img_err:
        #     flash(f"File gambar yang disimpan ({image_name}) tampaknya tidak valid atau rusak: {img_err}", "danger")
        #     print(f"Error saat memverifikasi file gambar {absolute_image_path}: {img_err}")
        #     return redirect(url_for('dashboard'))

        flash(f"Gambar berhasil diambil dan disimpan sebagai: {image_name}", "success")

        # ---- LOGIKA DETEKSI YOLOv8 ----
        results = model_yolo(absolute_image_path) # Gunakan model yang sudah dimuat

        detected_class_name = "Tidak Terdeteksi"
        confidence_score = 0.0
        generative_desc = "Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan."

        if results and results[0].boxes: # results adalah list, ambil elemen pertama
            # Asumsikan deteksi dengan confidence tertinggi adalah yang paling relevan
            # Atau, jika Anda memiliki logika khusus untuk memilih deteksi
            top_detection = results[0].boxes[0] # Ambil deteksi pertama (biasanya yang paling confident)
            
            # Dapatkan nama kelas dari model.names
            # results[0].names adalah dictionary seperti {0: 'Oli Baik', 1: 'Oli Buruk'}
            class_id = int(top_detection.cls[0].item()) # .cls adalah tensor, ambil itemnya
            detected_class_name = model_yolo.names[class_id] if model_yolo.names else f"Kelas {class_id}"
            
            confidence_score = float(top_detection.conf[0].item()) # .conf adalah tensor, ambil itemnya
            
            flash(f"Deteksi: {detected_class_name} dengan confidence: {confidence_score:.2f}", "info")

            # Dapatkan deskripsi dari Gemini API jika API key tersedia
            if GEMINI_API_KEY:
                # Untuk Gemini, path file harus absolut dan dapat diakses oleh proses yang menjalankan Gemini API.
                # Jika Gemini API dijalankan di cloud, Anda mungkin perlu mengunggah gambar ke cloud storage
                # atau memastikan path lokal dapat diakses. Untuk penggunaan lokal:
                generative_desc = get_gemini_description(absolute_image_path, detected_class_name)
            else:
                generative_desc = "Fitur deskripsi Gemini tidak aktif. API Key tidak ditemukan."
        else:
            flash("Tidak ada objek yang terdeteksi oleh YOLO.", "warning")

        # Simpan hasil deteksi ke database
        db_conn = None
        cursor = None
        try:
            db_conn = get_db_connection()
            if not db_conn:
                # Pesan flash sudah ditangani oleh get_db_connection
                return redirect(url_for('dashboard'))
            # Jika koneksi gagal, kita sudah flash message di get_db_connection
            # Mungkin redirect ke dashboard atau halaman error khusus
            
            cursor = db_conn.cursor()
            sql = "INSERT INTO detections (user_id, image_name, image_path, detection_class, confidence_score, generative_description, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            current_timestamp = datetime.now()
            val = (session['user_id'], image_name, relative_image_path, detected_class_name, confidence_score, generative_desc, current_timestamp)
            cursor.execute(sql, val)
            db_conn.commit()
            detection_id = cursor.lastrowid
            return redirect(url_for('hasil', detection_id=detection_id))
        except mysql.connector.Error as err:
            flash(f"Gagal menyimpan hasil deteksi ke database: {err}", "danger")
            if db_conn and db_conn.is_connected(): 
                db_conn.rollback()
            return redirect(url_for('dashboard'))
        finally:
            if cursor: 
                cursor.close()
            if db_conn and db_conn.is_connected():
                db_conn.close()

    except requests.exceptions.RequestException as e:
        flash(f"Gagal mengambil gambar dari ESP32-CAM: {e}", "danger")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}", "danger")
        return redirect(url_for('dashboard'))

# --- Route untuk halaman uji kamera (index.html) ---
@app.route('/uji_kamera')
@login_required # Anda bisa menghapus ini jika halaman uji tidak memerlukan login
def uji_kamera_page() -> str:
    """
    Route untuk me-render halaman uji kamera (index.html).
    Halaman ini akan menggunakan endpoint /api/capture_and_process.
    """
    stream_url_for_template = None
    display_ip_for_template = "Kamera tidak dikonfigurasi"

    if CAMERA_BASE_IP:
        stream_url_for_template = f"{CAMERA_BASE_IP}{CAMERA_STREAM_PATH}"
        display_ip_for_template = CAMERA_BASE_IP
        print(f"Uji Kamera Page: URL Stream = {stream_url_for_template}")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi di file .env. Stream tidak akan tampil.", "warning")

    return render_template('index.html',
                           title="Uji Capture Kamera",
                           username=session.get('username'),
                           esp32_stream_url_from_flask=stream_url_for_template,
                           esp32_display_ip_from_flask=display_ip_for_template)

# --- API Endpoint untuk capture dan proses (digunakan oleh index.html) ---
@app.route('/api/capture_and_process', methods=['POST'])
@login_required # Anda bisa menghapus ini jika tidak memerlukan login untuk API ini
def api_capture_and_process() -> Union[FlaskResponse, Tuple[Dict[str, str], int]]:
    """
    API endpoint untuk mengambil gambar dari kamera, memprosesnya (misalnya dengan YOLO),
    dan mengembalikan gambar hasil proses atau data JSON.
    Endpoint ini TIDAK melakukan redirect, melainkan mengembalikan respons langsung.
    """
    if not CAMERA_BASE_IP:
        return {"error": "Alamat IP Kamera belum dikonfigurasi."}, 503

    if not model_yolo: # Asumsi model_yolo sudah dimuat global
        return {"error": "Model YOLO tidak berhasil dimuat."}, 503

    capture_url: str = f"{CAMERA_BASE_IP}{CAMERA_CAPTURE_PATH}"
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

        # ---- LOGIKA DETEKSI YOLOv8 (Sederhana) ----
        # Untuk contoh ini, kita akan langsung mengembalikan gambar yang diterima dari kamera.
        # Anda bisa menambahkan logika deteksi YOLO di sini jika diperlukan,
        # dan kemudian mengembalikan gambar yang sudah dianotasi.
        # Misalnya: results = model_yolo(image_bytes) -> proses results -> annotated_image_bytes
        # return Response(annotated_image_bytes, mimetype='image/jpeg')

        return FlaskResponse(image_bytes, mimetype=content_type) # Mengembalikan gambar asli dari kamera
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
    conn: Optional[mysql.connector.MySQLConnection] = get_db_connection()
    if conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Pastikan hanya user yang bersangkutan yang bisa melihat hasilnya
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

    # Pastikan 'timestamp' adalah objek datetime jika akan diformat di template
    if detection_data and isinstance(detection_data.get('timestamp'), str):
        try:
            detection_data['timestamp'] = datetime.fromisoformat(detection_data['timestamp'])
        except ValueError:
            # Handle jika format string tidak sesuai, atau biarkan sebagai string
            pass 

    return render_template('hasil.html', title="Hasil Deteksi", username=session.get('username'), detection=detection_data)


@app.route('/histori')
@login_required
def histori() -> str:
    detections_history: list = []
    conn: Optional[mysql.connector.MySQLConnection] = get_db_connection()
    cursor: Optional[mysql.connector.cursor.MySQLCursorDict] = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Ambil hanya histori milik user yang sedang login, urutkan dari terbaru
            cursor.execute("SELECT * FROM detections WHERE user_id = %s ORDER BY timestamp DESC", (session['user_id'],))
            detections_history = cursor.fetchall()
        except mysql.connector.Error as err:
            flash(f"Error saat memuat histori: {err}", "danger")
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()
    else:
        flash("Tidak dapat memuat histori, masalah koneksi database.", "warning") # Pesan ini mungkin sudah di-flash oleh get_db_connection

    return render_template('histori.html', title="Histori Deteksi", username=session.get('username'), detections=detections_history)

@app.route('/logout')
@login_required
def logout() -> FlaskResponse:
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e: Any) -> Tuple[str, int]:
    return render_template('errors/404.html', title="Halaman Tidak Ditemukan"), 404

@app.errorhandler(500)
def internal_server_error(e: Any) -> Tuple[str, int]:
    return render_template('errors/500.html', title="Kesalahan Server"), 500
 

if __name__ == '__main__':
    # Pastikan host 0.0.0.0 agar bisa diakses dari jaringan lokal oleh ESP32-CAM (jika perlu komunikasi balik)
    # dan oleh Anda dari perangkat lain di jaringan yang sama untuk testing.
    app.run(debug=True, host='0.0.0.0', port=5000)