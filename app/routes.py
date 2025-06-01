from flask import Blueprint, render_template, url_for, flash, redirect, request, current_app
from flask_login import login_user, current_user, logout_user, login_required
from app import db # , bcrypt # Jika menggunakan bcrypt langsung
from app.models import User, Deteksi
from app.forms import LoginForm, RegistrationForm
# Untuk password hashing, kita akan menggunakan metode di model User
import os
from werkzeug.utils import secure_filename # Untuk mengamankan nama file upload
# Import library YOLO dan Google API akan dilakukan nanti saat implementasi backend

# Membuat Blueprint
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

# --- Rute Autentikasi (auth_bp) ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data) # Menggunakan metode set_password dari model
            db.session.add(user)
            db.session.commit()
            flash('Akun Anda berhasil dibuat! Silakan login.', 'success')
            current_app.logger.info(f"User baru terdaftar: {form.username.data}")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat membuat akun: {e}', 'danger')
            current_app.logger.error(f"Error registrasi user {form.username.data}: {e}")
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.email == form.email_or_username.data) | (User.username == form.email_or_username.data)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login berhasil!', 'success')
            current_app.logger.info(f"User login berhasil: {user.username}")
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Login gagal. Periksa kembali email/username dan password Anda.', 'danger')
            current_app.logger.warning(f"Login gagal untuk: {form.email_or_username.data}")
    return render_template('auth/login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    current_app.logger.info(f"User logout: {current_user.username if current_user else 'Unknown'}") # current_user mungkin sudah None
    return redirect(url_for('auth.login'))

# --- Rute Utama (main_bp) ---
@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Logika untuk dashboard (misalnya, menampilkan stream ESP32-CAM) akan ditambahkan nanti
    return render_template('dashboard.html', title='Dashboard')

@main_bp.route('/hasil_deteksi/<int:deteksi_id>') # Atau berdasarkan parameter lain
@login_required
def hasil_deteksi(deteksi_id):
    # Logika untuk menampilkan hasil deteksi spesifik
    detection_result = Deteksi.query.get_or_404(deteksi_id)
    # Pastikan hanya user yang bersangkutan yang bisa melihat detailnya (jika diperlukan)
    if detection_result.detector != current_user:
         flash('Anda tidak memiliki izin untuk melihat hasil deteksi ini.', 'danger')
         return redirect(url_for('main.histori'))
    return render_template('hasil_deteksi.html', title='Hasil Deteksi', result=detection_result)

@main_bp.route('/histori')
@login_required
def histori():
    page = request.args.get('page', 1, type=int)
    # Mengambil data deteksi milik user yang sedang login, diurutkan dari terbaru
    user_detections = Deteksi.query.filter_by(user_id=current_user.id)\
                                .order_by(Deteksi.timestamp.desc())\
                                .paginate(page=page, per_page=10) # 10 item per halaman
    return render_template('histori.html', title='Histori Deteksi', detections=user_detections)

@main_bp.route('/tentang')
def tentang_aplikasi():
    return render_template('tentang.html', title='Tentang Aplikasi')

# Rute untuk tangkap gambar dan proses deteksi akan ditambahkan di tahap backend
@main_bp.route('/capture_and_detect', methods=['POST'])
@login_required
def capture_and_detect():
    # Placeholder untuk logika tangkap gambar dari ESP32, deteksi YOLO, dan simpan hasil
    # Ini akan diimplementasikan secara detail di Tahap 8 (Backend)
    flash('Fitur tangkap dan deteksi belum diimplementasikan.', 'info')
    return redirect(url_for('main.dashboard'))