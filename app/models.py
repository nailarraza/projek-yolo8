# Lokasi file: D:/projek-yolo8/app/models.py

from datetime import datetime
from app import db, login_manager, bcrypt
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users' # Eksplisit mendefinisikan nama tabel

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # Password akan disimpan sebagai hash, jadi panjangnya harus cukup
    password_hash = db.Column(db.String(128), nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relasi ke tabel detections (satu user bisa memiliki banyak deteksi)
    detections = db.relationship('Detection', backref='detector', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Detection(db.Model):
    __tablename__ = 'detections' # Eksplisit mendefinisikan nama tabel

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    image_name = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    detection_class = db.Column(db.String(100))
    confidence_score = db.Column(db.Float)
    generative_description = db.Column(db.Text)

    def __repr__(self):
        return f"Detection('{self.image_name}', Class: '{self.detection_class}', Score: {self.confidence_score})"

