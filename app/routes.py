# Lokasi file: D:/projek-yolo8/app/routes.py

from flask import (
    render_template, url_for, flash, redirect, request, 
    current_app, jsonify, Response, session
)
from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm
from app.models import User, Detection
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
import os
import time
import uuid # Untuk nama file unik
from werkzeug.utils import secure_filename # Untuk mengamankan nama file

# Import fungsi utilitas
from app.utils import (
    load_yolo_model, perform_detection, draw_bounding_boxes, 
    get_gemini_description, capture_image_from_esp32
)
import requests # Untuk meneruskan stream

# Inisialisasi model YOLO saat aplikasi dimulai (atau saat request pertama ke endpoint terkait)
# Lebih baik di-load sekali saja. Kita bisa panggil load_yolo_model() di sini atau di __init__.py
# dalam app_context. Untuk sekarang, kita akan memastikannya dipanggil sebelum deteksi.
# Atau, fungsi load_yolo_model() sudah menangani pemuatan sekali pakai dengan variabel global.

@current_app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@current_app.route("/")
@current_app.route("/home")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Jika ada halaman landing sebelum login, tampilkan di sini
    return redirect(url_for('login')) 

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
    # URL untuk stream video dari Flask (yang akan meneruskan dari ESP32)
    video_stream_url = url_for('video_feed_flask')
    return render_template('dashboard.html', title='Dashboard', video_stream_url=video_stream_url)

# Rute untuk meneruskan stream dari ESP32-CAM
def stream_generator_from_esp():
    esp_stream_url = current_app.config.get('ESP32_CAM_STREAM_URL')
    if not esp_stream_url:
        current_app.logger.error("URL stream ESP32-CAM tidak dikonfigurasi.")
        # Bisa yield pesan error atau gambar statis
        # Untuk sekarang, kita biarkan kosong jika error
        return

    try:
        # Gunakan stream=True untuk requests agar tidak download semua sekaligus
        req = requests.get(esp_stream_url, stream=True, timeout=10) # Timeout 10 detik
        req.raise_for_status()
        
        current_app.logger.info(f"Meneruskan stream dari {esp_stream_url}")
        for chunk in req.iter_content(chunk_size=1024): # Baca per chunk
            if chunk:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + chunk + b'\r\n\r\n')
            else:
                current_app.logger.warning("Menerima chunk kosong dari stream ESP32.")
                break # Hentikan jika chunk kosong
        current_app.logger.info("Selesai meneruskan stream dari ESP32.")

    except requests.exceptions.Timeout:
        current_app.logger.error(f"Timeout saat mencoba koneksi ke stream ESP32 di {esp_stream_url}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error saat meneruskan stream dari ESP32: {e}")
    except Exception as e:
        current_app.logger.error(f"Error tidak terduga saat streaming: {e}")


@current_app.route('/video_feed_flask')
@login_required
def video_feed_flask():
    """Meneruskan stream video dari ESP32-CAM ke frontend."""
    return Response(stream_generator_from_esp(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@current_app.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect():
    current_app.logger.info("Proses capture_and_detect dimulai.")
    try:
        # 1. Muat model YOLO (jika belum)
        yolo_model = load_yolo_model()
        if not yolo_model: # Seharusnya sudah dihandle oleh exception di load_yolo_model
            return jsonify(success=False, message="Gagal memuat model deteksi."), 500

        # 2. Ambil gambar dari ESP32-CAM
        current_app.logger.info("Mencoba mengambil gambar dari ESP32-CAM...")
        image_pil = capture_image_from_esp32()
        if image_pil is None:
            current_app.logger.error("Gagal mengambil gambar dari ESP32-CAM.")
            return jsonify(success=False, message="Gagal mengambil gambar dari kamera. Pastikan ESP32-CAM aktif dan terhubung."), 500
        
        current_app.logger.info("Gambar berhasil diambil dari ESP32-CAM.")

        # Simpan gambar asli sementara untuk referensi
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8] # ID unik pendek
        
        original_image_name = f"original_{current_user.id}_{timestamp_str}_{unique_id}.jpg"
        original_image_path_relative = os.path.join('uploads', original_image_name) # Path relatif untuk URL
        original_image_path_full = os.path.join(current_app.config['UPLOAD_FOLDER'], original_image_name)
        
        try:
            image_pil.save(original_image_path_full)
            current_app.logger.info(f"Gambar asli disimpan di: {original_image_path_full}")
        except Exception as e:
            current_app.logger.error(f"Gagal menyimpan gambar asli: {e}")
            return jsonify(success=False, message=f"Gagal menyimpan gambar asli: {str(e)}"), 500

        # 3. Lakukan deteksi dengan YOLO
        current_app.logger.info("Melakukan deteksi YOLO...")
        detection_results_yolo = perform_detection(image_pil.copy(), yolo_model) # Kirim copy agar PIL asli tidak termodifikasi
        
        # 4. Gambar bounding box pada gambar
        detected_image_name = f"detected_{current_user.id}_{timestamp_str}_{unique_id}.jpg"
        detected_image_path_relative = os.path.join('uploads', detected_image_name)
        detected_image_path_full = os.path.join(current_app.config['UPLOAD_FOLDER'], detected_image_name)
        
        # Panggil draw_bounding_boxes
        # Asumsikan class_names ada di model.names jika modelnya dari ultralytics
        # Jika tidak, Anda perlu menyediakan class_names sendiri
        # class_names_list = ["Oli Baik", "Oli Perlu Diganti", "Oli Buruk"] # Contoh jika perlu
        
        _, detected_class, confidence_score = draw_bounding_boxes(
            image_pil.copy(), 
            detection_results_yolo, 
            detected_image_path_full
            # class_names=class_names_list # Aktifkan jika perlu
        )
        current_app.logger.info(f"Hasil deteksi: Kelas={detected_class}, Skor={confidence_score}")

        # 5. Dapatkan deskripsi generatif dari Gemini API
        current_app.logger.info("Mendapatkan deskripsi dari Gemini API...")
        if detected_class and confidence_score is not None:
            generative_desc = get_gemini_description(detected_class, confidence_score)
        else: # Jika tidak ada deteksi yang jelas
            generative_desc = get_gemini_description(None, None) 
        current_app.logger.info(f"Deskripsi Gemini: {generative_desc}")

        # 6. Simpan hasil deteksi ke database
        new_detection_record = Detection(
            user_id=current_user.id,
            timestamp=datetime.utcnow(),
            image_name=detected_image_name, # Simpan nama gambar yang sudah ada bounding box
            image_path=detected_image_path_relative, # Path relatif untuk diakses via URL
            detection_class=detected_class,
            confidence_score=confidence_score,
            generative_description=generative_desc
        )
        db.session.add(new_detection_record)
        db.session.commit()
        current_app.logger.info(f"Hasil deteksi disimpan ke database dengan ID: {new_detection_record.id}")

        # 7. Kirim respons ke frontend
        # Kita akan redirect ke halaman hasil dengan ID deteksi
        return jsonify(
            success=True, 
            message="Deteksi berhasil!",
            detection_id=new_detection_record.id,
            result_page_url=url_for('view_detection_result', detection_id=new_detection_record.id)
        )

    except FileNotFoundError as e: # Khusus untuk model tidak ditemukan
        current_app.logger.error(f"FileNotFoundError: {e}")
        return jsonify(success=False, message=str(e)), 500
    except requests.exceptions.ConnectionError as e:
        current_app.logger.error(f"ConnectionError: {e}")
        return jsonify(success=False, message="Gagal terhubung ke layanan eksternal (ESP32 atau Gemini). Periksa koneksi."), 503
    except Exception as e:
        current_app.logger.error(f"Error tidak terduga di capture_and_detect: {e}", exc_info=True)
        return jsonify(success=False, message=f"Terjadi error internal: {str(e)}"), 500


@current_app.route("/hasil_deteksi/<int:detection_id>")
@login_required
def view_detection_result(detection_id):
    detection = db.session.get(Detection, detection_id) # Cara baru untuk query by PK dengan SQLAlchemy 2.0+
    if not detection:
        flash('Hasil deteksi tidak ditemukan.', 'danger')
        return redirect(url_for('history'))
        
    if detection.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk melihat hasil deteksi ini.', 'danger')
        return redirect(url_for('history'))
        
    return render_template('hasil.html', title='Hasil Deteksi', detection=detection)


@current_app.route("/histori")
@login_required
def history():
    user_detections = Detection.query.filter_by(user_id=current_user.id)\
                                     .order_by(Detection.timestamp.desc())\
                                     .all()
    return render_template('histori.html', title='Histori Deteksi', detections=user_detections)