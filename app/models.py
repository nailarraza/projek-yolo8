from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    """Callback untuk memuat user berdasarkan ID untuk Flask-Login."""
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Model untuk tabel User."""
    __tablename__ = 'User' # Eksplisit mendefinisikan nama tabel

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) # Diperpanjang untuk hash yang lebih kuat
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Menggunakan datetime.utcnow untuk konsistensi zona waktu

    # Relasi ke tabel Deteksi
    detections = db.relationship('Deteksi', backref='detector', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        """Membuat hash password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Memverifikasi password dengan hash yang tersimpan."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Deteksi(db.Model):
    """Model untuk tabel Deteksi."""
    __tablename__ = 'Deteksi' # Eksplisit mendefinisikan nama tabel

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    image_name = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    detection_class = db.Column(db.String(100))
    confidence_score = db.Column(db.Float) # Menggunakan Float untuk skor kepercayaan
    generative_description = db.Column(db.Text)

    def __repr__(self):
        return f'<Deteksi {self.id} oleh User {self.user_id} - {self.detection_class}>'
