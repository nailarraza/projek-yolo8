# cloud_app.py
import os, sys # Tambahkan sys untuk potensi modifikasi path jika dijalankan langsung
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response as FlaskResponse, jsonify
from werkzeug.wrappers import Response as WerkzeugResponse
from werkzeug.utils import secure_filename
from datetime import datetime
import base64
import numpy as np
import cv2
import mysql.connector
from pyngrok import ngrok, conf # Untuk menjalankan Ngrok dari sini
import getpass # Untuk input Ngrok token
from functools import wraps
from typing import Callable, Any, Union, Optional, Dict, Tuple

# --- Import logika inti dari app_run.py ---
# Asumsi main.ipynb telah menambahkan project_path ke sys.path
# dan app_run.py dapat diimpor.
# Model dan GEMINI_API_KEY akan dimuat saat app_run diimpor (jika di-set di env oleh main.ipynb)
from app_run import (
    generate_password_hash, check_password_hash,
    get_gemini_description, # Fungsi deskripsi Gemini
    model_yolo_oil,      # Model YOLO yang sudah dimuat dari app_run
    GEMINI_API_KEY,      # Kunci API Gemini yang sudah dimuat dari app_run
    verify_camera_connection, get_camera_base_ip,
    capture_single_frame_from_stream_cv2, capture_single_frame_from_http_endpoint,
    CAMERA_STREAM_PATH, CAMERA_CAPTURE_PATH, CAMERA_REQUEST_TIMEOUT, CAMERA_VERIFY_TIMEOUT
)

# Inisialisasi Aplikasi Flask untuk Cloud
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Konfigurasi dari environment variables (di-set oleh main.ipynb)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_cloud_secret_key')
app.config['UPLOAD_FOLDER'] = 'app/static/uploads' # Path relatif terhadap root proyek di Drive

# Kredensial Database dari environment variables (di-set oleh main.ipynb)
DB_HOST_CLOUD = os.getenv("DB_HOST_CLOUD", "localhost")
DB_USER_CLOUD = os.getenv("DB_USER_CLOUD", "root")
DB_PASSWORD_CLOUD = os.getenv("DB_PASSWORD_CLOUD", "")
DB_NAME_CLOUD = os.getenv("DB_NAME_CLOUD", "db_projek_yolo8")

def get_cloud_db_connection() -> Optional[mysql.connector.MySQLConnection]:
    try:
        conn = mysql.connector.connect(
            host=DB_HOST_CLOUD,
            user=DB_USER_CLOUD,
            password=DB_PASSWORD_CLOUD,
            database=DB_NAME_CLOUD,
            connect_timeout=10
        )
        return conn
    except mysql.connector.Error as err:
        app.logger.error(f"Cloud Database connection error: {err}")
        return None

def cloud_login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if 'user_id' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login_cloud')) # Rute login di cloud_app
        return f(*args, **kwargs)
    return decorated_function

# --- Logika Pemrosesan Gambar Khusus Cloud ---
# Ini adalah versi adaptasi dari _process_image_data_and_save_detection di app_run.py
# agar menggunakan koneksi DB cloud, logger & config dari cloud_app.
def _cloud_process_image_data_and_save_detection(
    original_image_np: np.ndarray,
    user_id: int,
    upload_folder_from_config: str, # Tambahkan parameter ini
    gemini_api_key_present_from_env: bool # Tambahkan parameter ini
) -> Tuple[bool, str, Optional[int]]:
    global model_yolo_oil # Menggunakan model yang diimpor dari app_run
    # GEMINI_API_KEY global dari app_run akan digunakan oleh get_gemini_description

    if not model_yolo_oil:
        app.logger.error("Model YOLO (Cloud) tidak dimuat atau tidak tersedia.")
        return False, "Model YOLO (Cloud) tidak dimuat.", None
    try:
        upload_folder = upload_folder_from_config # Gunakan parameter yang dioper
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_image_name = f"capture_{user_id}_{timestamp_str}"
        original_image_filename = f"{base_image_name}_original.jpg"
        absolute_original_image_path = os.path.join(upload_folder, original_image_filename)
        annotated_image_filename = f"{base_image_name}_annotated.jpg"
        absolute_annotated_image_path = os.path.join(upload_folder, annotated_image_filename)
        relative_annotated_image_path = f"uploads/{annotated_image_filename}" # Path untuk DB

        save_success = cv2.imwrite(absolute_original_image_path, original_image_np)
        if not save_success:
            app.logger.error(f"Gagal menyimpan gambar asli (Cloud) ke {absolute_original_image_path}")
            return False, "Gagal menyimpan gambar asli (Cloud).", None
        app.logger.info(f"Gambar asli (Cloud) disimpan di: {absolute_original_image_path}")

        annotated_image_to_save = original_image_np.copy()
        all_detection_details = []
        all_detected_class_names = []
        class_for_gemini_description: Optional[str] = None
        db_detected_class_name: str = "Tidak ada objek terdeteksi"
        db_confidence_score_str: str = ""

        app.logger.info("Melakukan deteksi OLI (Cloud)...")
        results_oil = model_yolo_oil(original_image_np, verbose=False)
        if results_oil and results_oil[0].boxes:
            annotated_image_to_save = results_oil[0].plot(img=annotated_image_to_save, conf=True, labels=True)
            app.logger.info(f"Deteksi OLI (Cloud) ditemukan: {len(results_oil[0].boxes)} objek.")
            for i, box in enumerate(results_oil[0].boxes):
                class_id = int(box.cls[0].item())
                class_name = model_yolo_oil.names.get(class_id, f"UnknownOilClass{class_id}")
                confidence = float(box.conf[0].item())
                all_detection_details.append(f"{class_name}: {confidence*100:.2f}% (Oli)")
                all_detected_class_names.append(class_name)
                if i == 0 and not class_for_gemini_description:
                    class_for_gemini_description = class_name
        else:
            app.logger.info("Tidak ada OLI yang terdeteksi (Cloud).")

        if all_detected_class_names:
            db_detected_class_name = ", ".join(sorted(list(set(all_detected_class_names))))
            if all_detection_details:
                db_confidence_score_str = ", ".join(all_detection_details)

        log_prefix_annotated = "Gambar teranotasi (Cloud)" if all_detection_details else "Gambar asli (Cloud, tidak ada deteksi)"
        if not cv2.imwrite(absolute_annotated_image_path, annotated_image_to_save):
            app.logger.critical(f"KRITIS (Cloud): Gagal menyimpan {log_prefix_annotated.lower()} ke {absolute_annotated_image_path}.")
            return False, f"Gagal menyimpan {log_prefix_annotated.lower()}.", None
        app.logger.info(f"{log_prefix_annotated} berhasil disimpan di: {absolute_annotated_image_path}")

        generative_desc = "Tidak ada objek yang terdeteksi atau model tidak dapat mengklasifikasikan (Cloud)."
        if gemini_api_key_present_from_env and class_for_gemini_description: # Gunakan parameter yang dioper
            app.logger.info(f"Meminta deskripsi Gemini (Cloud) untuk kelas: {class_for_gemini_description}")
            generative_desc = get_gemini_description(absolute_original_image_path, class_for_gemini_description)
        elif not gemini_api_key_present_from_env: # Gunakan parameter yang dioper
            generative_desc = "Fitur deskripsi Gemini tidak aktif (API Key tidak ditemukan atau error konfigurasi - Cloud)."
        # (Tambahkan logika lain untuk deskripsi Gemini jika ada deteksi lain tapi bukan prioritas)

        db_conn = None
        cursor = None
        try:
            db_conn = get_cloud_db_connection() # Menggunakan koneksi DB cloud
            if not db_conn:
                return False, "Gagal terhubung ke database untuk menyimpan deteksi (Cloud).", None
            cursor = db_conn.cursor()
            sql = "INSERT INTO detections (user_id, image_name, image_path, detection_class, confidence_score, generative_description, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            current_timestamp = datetime.now()
            val = (user_id, annotated_image_filename, relative_annotated_image_path, db_detected_class_name, db_confidence_score_str, generative_desc, current_timestamp)
            cursor.execute(sql, val)
            db_conn.commit()
            detection_id = cursor.lastrowid
            return True, "Deteksi berhasil diproses dan disimpan (Cloud).", detection_id
        except mysql.connector.Error as db_err:
            app.logger.error(f"Gagal menyimpan hasil deteksi ke database (Cloud): {db_err}")
            if db_conn and db_conn.is_connected(): db_conn.rollback()
            return False, f"Gagal menyimpan hasil deteksi ke database (Cloud): {db_err}", None
        finally:
            if cursor: cursor.close()
            if db_conn and db_conn.is_connected(): db_conn.close()
    except Exception as e:
        app.logger.error(f"Kesalahan tak terduga saat memproses gambar (Cloud): {e}", exc_info=True)
        return False, f"Terjadi kesalahan tak terduga saat memproses gambar (Cloud): {e}", None

# --- Rute-rute Aplikasi Cloud ---
@app.route('/')
def index_cloud() -> WerkzeugResponse:
    if 'user_id' in session:
        return redirect(url_for('dashboard_cloud'))
    return redirect(url_for('login_cloud'))

@app.route('/register', methods=['GET', 'POST'])
def register_cloud() -> Union[str, WerkzeugResponse]:
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([username, email, password, confirm_password]):
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('register_cloud'))
        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok!', 'danger')
            return redirect(url_for('register_cloud'))

        conn = get_cloud_db_connection()
        if not conn:
            return render_template('register.html', title="Register Cloud", error_message="Tidak dapat terhubung ke database cloud.")
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user: Optional[Dict[str, Any]] = cursor.fetchone()
            if existing_user:
                flash('Username atau Email sudah terdaftar.', 'warning')
                return redirect(url_for('register_cloud'))
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                           (username, email, hashed_password))
            conn.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login_cloud'))
        except mysql.connector.Error as err:
            flash(f'Terjadi kesalahan saat registrasi: {err}', 'danger')
            app.logger.error(f"Cloud registration error: {err}")
            if conn.is_connected(): conn.rollback()
            return redirect(url_for('register_cloud'))
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
    return render_template('register.html', title="Register Cloud")

@app.route('/login', methods=['GET', 'POST'])
def login_cloud() -> Union[str, WerkzeugResponse]:
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        if not identifier or not password:
            flash('Username/Email dan Password wajib diisi!', 'danger')
            return redirect(url_for('login_cloud'))
        conn = get_cloud_db_connection()
        if not conn:
            return render_template('login.html', title="Login Cloud", error_message="Tidak dapat terhubung ke database cloud.")
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s OR email = %s", (identifier, identifier))
            user: Optional[Dict[str, Any]] = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f"Selamat datang, {str(user['username'])}!", 'success')
                return redirect(url_for('dashboard_cloud'))
            else:
                flash('Login gagal. Periksa kembali username/email dan password Anda.', 'danger')
                return redirect(url_for('login_cloud'))
        except mysql.connector.Error as err:
            flash(f'Terjadi kesalahan saat login: {err}', 'danger')
            app.logger.error(f"Cloud login error: {err}")
            return redirect(url_for('login_cloud'))
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
    return render_template('login.html', title="Login Cloud")

@app.route('/dashboard')
@cloud_login_required
def dashboard_cloud() -> str:
    camera_base_ip = get_camera_base_ip() # Dari app_run, menggunakan session Flask
    esp32_stream_url = None
    if camera_base_ip:
        esp32_stream_url = f"{camera_base_ip}{CAMERA_STREAM_PATH}" # CAMERA_STREAM_PATH dari app_run
        app.logger.info(f"Cloud Dashboard: URL Stream Kamera = {esp32_stream_url}")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi (Cloud).", "warning")
    return render_template('dashboard.html',
                           title="Dashboard Cloud",
                           username=session.get('username'),
                           current_cam_ip=session.get('esp32_cam_ip', ""),
                           esp32_stream_url=esp32_stream_url,
                           camera_configured=(camera_base_ip is not None))

@app.route('/update_cam_ip', methods=['POST'])
@cloud_login_required
def update_cam_ip_cloud() -> WerkzeugResponse:
    new_cam_ip = request.form.get('esp32_cam_ip', '').strip()
    if new_cam_ip:
        is_potentially_valid_ip_or_hostname = '.' in new_cam_ip or len(new_cam_ip) > 3
        if not is_potentially_valid_ip_or_hostname:
             flash('Format Alamat IP Kamera tidak valid (Cloud).', 'danger')
             return redirect(url_for('dashboard_cloud'))
        # verify_camera_connection dari app_run. Menggunakan app.logger dari app_run.
        is_verified, verify_message = verify_camera_connection(new_cam_ip)
        if is_verified:
            session['esp32_cam_ip'] = new_cam_ip
            flash(f'Alamat IP Kamera berhasil diperbarui dan diverifikasi: {new_cam_ip} (Cloud)', 'success')
        else:
            session['esp32_cam_ip'] = new_cam_ip # Simpan meski gagal verifikasi
            flash(f'Alamat IP Kamera diperbarui: {new_cam_ip}. PERINGATAN: Verifikasi gagal - {verify_message} (Cloud)', 'warning')
    else:
        session.pop('esp32_cam_ip', None)
        flash('Alamat IP Kamera telah dihapus dari sesi ini (Cloud).', 'info')
    return redirect(url_for('dashboard_cloud'))

@app.route('/process_browser_capture', methods=['POST'])
@cloud_login_required
def process_browser_capture_cloud() -> Tuple[Dict[str, Any], int]:
    global model_yolo_oil # Dari app_run
    if not model_yolo_oil:
        return {"status": "error", "message": "Model YOLO untuk deteksi oli tidak berhasil dimuat (Cloud)."}, 503

    data = request.get_json()
    if not data or 'image_data_url' not in data:
        return {"status": "error", "message": "Data gambar tidak ditemukan dalam permintaan (Cloud)."}, 400
    image_data_url = data['image_data_url']
    try:
        _, encoded_data = image_data_url.split(',', 1)
        image_bytes = base64.b64decode(encoded_data)
        image_np = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image_np is None:
            return {"status": "error", "message": "Gagal mendekode data gambar dari base64 (Cloud)."}, 400

        user_id = session['user_id']
        success, message, detection_id = _cloud_process_image_data_and_save_detection(
            original_image_np=image_np,
            user_id=user_id,
            upload_folder_from_config=app.config['UPLOAD_FOLDER'], # Oper upload_folder
            gemini_api_key_present_from_env=bool(GEMINI_API_KEY) # Oper status GEMINI_API_KEY
        )
        if success and detection_id is not None:
            return {"status": "success", "redirect_url": url_for('hasil_cloud', detection_id=detection_id), "message": message}, 200
        else:
            app.logger.error(f"Cloud process_browser_capture error: {message}")
            return {"status": "error", "message": message or "Gagal memproses gambar (Cloud)."}, 500
    except Exception as e:
        app.logger.error(f"Error di /process_browser_capture (Cloud): {e}", exc_info=True)
        return {"status": "error", "message": f"Kesalahan server internal (Cloud): {str(e)}"}, 500

@app.route('/get_snapshot_for_canvas')
@cloud_login_required
def get_snapshot_for_canvas_cloud() -> Tuple[Dict[str, Any], int]:
    camera_base_ip = get_camera_base_ip() # Dari app_run
    if not camera_base_ip:
        return {"status": "error", "message": "IP Kamera tidak dikonfigurasi (Cloud)."}, 400

    capture_path = str(CAMERA_CAPTURE_PATH) # Dari app_run
    snapshot_url = f"{camera_base_ip}{capture_path}"
    app.logger.info(f"Cloud Snapshot for Canvas: Mencoba dari {snapshot_url}")
    image_np, error_msg = None, None

    if capture_path == CAMERA_STREAM_PATH: # Dari app_run
        image_np, error_msg = capture_single_frame_from_stream_cv2(snapshot_url, open_stream_timeout_sec=20, read_frame_timeout=10) # Dari app_run
    else:
        image_np, error_msg = capture_single_frame_from_http_endpoint(snapshot_url, timeout=CAMERA_REQUEST_TIMEOUT) # Dari app_run

    if error_msg or image_np is None:
        app.logger.error(f"Cloud Snapshot for Canvas: Error - {error_msg}")
        return {"status": "error", "message": error_msg or "Gagal mengambil snapshot (Cloud)."}, 502
    try:
        is_success, buffer = cv2.imencode(".jpg", image_np)
        if not is_success:
            return {"status": "error", "message": "Gagal meng-encode snapshot ke JPEG (Cloud)."}, 500
        image_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
        return {"status": "success", "image_data_url": f"data:image/jpeg;base64,{image_base64}"}, 200
    except Exception as e:
        app.logger.error(f"Cloud Snapshot for Canvas: Error encoding - {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Kesalahan saat memproses snapshot (Cloud): {str(e)}"}, 500

@app.route('/uji_kamera')
@cloud_login_required
def uji_kamera_page_cloud() -> str:
    camera_base_ip = get_camera_base_ip()
    stream_url_template = None
    display_ip_template = "Kamera tidak dikonfigurasi (Cloud)"
    if camera_base_ip:
        stream_url_template = f"{camera_base_ip}{CAMERA_STREAM_PATH}"
        display_ip_template = camera_base_ip.replace("http://", "").replace("https://", "")
    else:
        flash("Alamat IP Kamera belum dikonfigurasi. Stream tidak akan tampil (Cloud).", "warning")
    return render_template('index.html', # Asumsi menggunakan template yang sama
                           title="Uji Capture Kamera Cloud",
                           username=session.get('username'),
                           esp32_stream_url_from_flask=stream_url_template,
                           esp32_display_ip_from_flask=display_ip_template)

@app.route('/api/capture_and_process', methods=['POST'])
@cloud_login_required
def api_capture_and_process_cloud() -> Union[FlaskResponse, WerkzeugResponse, Tuple[Dict[str, Any], int]]:
    camera_base_ip = get_camera_base_ip()
    if not camera_base_ip:
        return jsonify({"error": "Alamat IP Kamera belum dikonfigurasi (Cloud)."}), 503
    global model_yolo_oil
    if not model_yolo_oil:
        return jsonify({"error": "Model YOLO untuk deteksi oli tidak berhasil dimuat (Cloud)."}), 503

    capture_path = str(CAMERA_CAPTURE_PATH)
    single_image_capture_url = f"{camera_base_ip}{capture_path}"
    app.logger.info(f"Cloud API Capture: Mencoba dari URL = {single_image_capture_url}")
    try:
        img_np, error_msg = None, None
        if capture_path == CAMERA_STREAM_PATH:
            img_np, error_msg = capture_single_frame_from_stream_cv2(single_image_capture_url, open_stream_timeout_sec=20, read_frame_timeout=10)
        else:
            img_np, error_msg = capture_single_frame_from_http_endpoint(single_image_capture_url, timeout=CAMERA_REQUEST_TIMEOUT)

        if error_msg or img_np is None:
            app.logger.error(f"Cloud API Error capturing frame: {error_msg}")
            return jsonify({"error": f"Gagal mengambil gambar ({CAMERA_CAPTURE_PATH}): {error_msg}"}), 502
        try:
            annotated_bgr_np = img_np.copy()
            if model_yolo_oil:
                results = model_yolo_oil(img_np, verbose=False)
                if results and results[0].boxes:
                    annotated_bgr_np = results[0].plot(img=annotated_bgr_np, conf=True, labels=True)
            encode_ok, img_buffer = cv2.imencode('.jpg', annotated_bgr_np)
            if not encode_ok:
                app.logger.error("Cloud API Error: Gagal encode gambar anotasi ke JPEG.")
                return jsonify({"error": "Gagal memproses gambar anotasi (Cloud)."}), 500
            return FlaskResponse(img_buffer.tobytes(), mimetype='image/jpeg')
        except Exception as yolo_err:
            app.logger.error(f"Cloud API Error pemrosesan YOLO: {yolo_err}", exc_info=True)
            return jsonify({"error": f"Error pemrosesan YOLO (Cloud): {str(yolo_err)}"}), 500
    except Exception as e:
        app.logger.error(f"Cloud API Error internal: {e}", exc_info=True)
        return jsonify({"error": f"Terjadi kesalahan internal server (Cloud): {str(e)}"}), 500

@app.route('/hasil/<int:detection_id>')
@cloud_login_required
def hasil_cloud(detection_id: int) -> Union[str, WerkzeugResponse]:
    detection_data: Optional[Dict[str, Any]] = None
    conn = get_cloud_db_connection()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections WHERE id = %s AND user_id = %s", (detection_id, session['user_id']))
            detection_data = cursor.fetchone()
        except mysql.connector.Error as err:
            flash(f"Error mengambil data deteksi (Cloud): {err}", "danger")
            app.logger.error(f"Cloud hasil error: {err}")
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()
    if not detection_data:
        flash("Data deteksi tidak ditemukan atau Anda tidak memiliki akses (Cloud).", "warning")
        return redirect(url_for('dashboard_cloud'))
    return render_template('hasil.html', title="Hasil Deteksi Cloud", username=session.get('username'), detection=detection_data)

@app.route('/histori')
@cloud_login_required
def histori_cloud() -> str:
    detections_hist: list = []
    conn = get_cloud_db_connection()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM detections WHERE user_id = %s ORDER BY timestamp DESC", (session['user_id'],))
            detections_hist = cursor.fetchall()
        except mysql.connector.Error as err:
            flash(f"Error memuat histori (Cloud): {err}", "danger")
            app.logger.error(f"Cloud histori error: {err}")
        finally:
            if cursor: cursor.close()
            if conn.is_connected(): conn.close()
    return render_template('histori.html', title="Histori Deteksi Cloud", username=session.get('username'), detections=detections_hist)

@app.route('/hapus_deteksi/<int:detection_id>', methods=['GET'])
@cloud_login_required
def hapus_deteksi_cloud(detection_id: int) -> WerkzeugResponse:
    conn = None
    cursor = None
    try:
        conn = get_cloud_db_connection()
        if not conn:
            return redirect(url_for('histori_cloud'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT image_name FROM detections WHERE id = %s AND user_id = %s", (detection_id, session['user_id']))
        row: Optional[Dict[str, Any]] = cursor.fetchone()
        if not row:
            flash('Riwayat deteksi tidak ditemukan atau Anda tidak memiliki izin (Cloud).', 'warning')
            return redirect(url_for('histori_cloud'))

        img_name_db = str(row['image_name'])
        # Path UPLOAD_FOLDER relatif terhadap root proyek di Drive
        annotated_img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name_db)
        if img_name_db.endswith("_annotated.jpg"):
            base_fn = img_name_db[:-len("_annotated.jpg")]
            original_img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_fn}_original.jpg")
            if os.path.exists(original_img_path):
                os.remove(original_img_path)
                app.logger.info(f"File original dihapus (Cloud): {original_img_path}")
        if os.path.exists(annotated_img_path):
            os.remove(annotated_img_path)
            app.logger.info(f"File anotasi dihapus (Cloud): {annotated_img_path}")

        cursor.execute("DELETE FROM detections WHERE id = %s AND user_id = %s", (detection_id, session['user_id']))
        conn.commit()
        flash('Riwayat deteksi berhasil dihapus (Cloud).', 'success')
    except mysql.connector.Error as err:
        app.logger.error(f'Gagal hapus riwayat DB (Cloud): {err}')
        flash(f'Gagal hapus riwayat deteksi (Cloud): {err}', 'danger')
        if conn and conn.is_connected(): conn.rollback()
    except OSError as e:
        app.logger.error(f'Gagal hapus file gambar (Cloud): {e}')
        flash(f'Gagal hapus file gambar (Cloud): {e}.', 'danger')
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return redirect(url_for('histori_cloud'))

@app.route('/logout')
@cloud_login_required
def logout_cloud() -> WerkzeugResponse:
    session.clear()
    flash('Anda telah logout (Cloud).', 'success')
    return redirect(url_for('login_cloud'))

# Error Handlers (contoh)
@app.errorhandler(404)
def page_not_found_cloud(e: Any) -> Tuple[str, int]:
    return render_template('errors/404.html', title="Halaman Tidak Ditemukan (Cloud)"), 404

@app.errorhandler(500)
def internal_server_error_cloud(e: Any) -> Tuple[str, int]:
    app.logger.error(f"Cloud Internal Server Error: {e}", exc_info=True)
    return render_template('errors/500.html', title="Kesalahan Server (Cloud)"), 500

# --- BAGIAN UNTUK MENJALANKAN APLIKASI FLASK DENGAN NGROK ---
if __name__ == '__main__':
    # Pastikan environment variables dari main.ipynb sudah di-set
    # dan app_run sudah diimpor oleh main.ipynb untuk inisialisasi model.
    # Jika script ini dijalankan langsung tanpa melalui main.ipynb,
    # pastikan variabel lingkungan (DB_HOST_CLOUD, dll.) dan model sudah siap.

    # Cek apakah kita berada di lingkungan Colab (opsional, untuk logging)
    IN_COLAB = 'google.colab' in sys.modules
    if IN_COLAB:
        print("Menjalankan cloud_app.py di lingkungan Google Colab.")
        # Asumsi main.ipynb sudah:
        # 1. Mount Drive
        # 2. os.chdir() ke project_path
        # 3. Menambahkan project_path ke sys.path
        # 4. Menginstal requirements.txt
        # 5. Set environment variables (DB, GEMINI_API_KEY, SECRET_KEY, YOLO_MODEL_OIL_PATH)
        # 6. Mengimpor app_run (yang memuat model YOLO dan GEMINI_API_KEY)
        print(f"  Current working directory: {os.getcwd()}")
        print(f"  Flask UPLOAD_FOLDER: {app.config.get('UPLOAD_FOLDER')}")
        if model_yolo_oil:
            print(f"  Model YOLO Oil terdeteksi: {type(model_yolo_oil)}")
        else:
            print("  PERINGATAN: Model YOLO Oil tidak terdeteksi. Pastikan main.ipynb telah mengimpor app_run.")
        if GEMINI_API_KEY:
            print("  Kunci API Gemini terdeteksi.")
        else:
            print("  PERINGATAN: Kunci API Gemini tidak terdeteksi.")

    print("\n--- PERSIAPAN NGROK (dari cloud_app.py) ---")
    conf.get_default().log_level = "ERROR" # Mengurangi verbosity Ngrok
    authtoken = os.getenv('NGROK_AUTHTOKEN') # Coba ambil dari env dulu
    if not authtoken:
        authtoken = getpass.getpass("Silakan masukkan Authtoken Ngrok Anda: ")

    if not authtoken:
        print("\nAuthtoken Ngrok tidak boleh kosong! Aplikasi tidak dapat dijalankan.")
    else:
        try:
            ngrok.set_auth_token(authtoken)
            public_url = ngrok.connect(5000, "http") # Port default Flask
            print("\n==============================================================")
            print("Aplikasi CLOUD Anda sekarang dapat diakses secara publik!")
            print(f"URL Publik: {public_url}")
            print("==============================================================")
            app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False)
        except Exception as e:
            print(f"\nTerjadi kesalahan saat memulai Ngrok atau Flask: {e}")
            print("Pastikan Authtoken Ngrok Anda benar dan port 5000 tidak digunakan proses lain.")
