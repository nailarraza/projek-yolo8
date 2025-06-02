-- Pastikan Anda menggunakan database yang benar
-- USE db_projek_yolo8;

-- Tabel untuk menyimpan informasi pengguna
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel untuk menyimpan riwayat deteksi
CREATE TABLE IF NOT EXISTS detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_name VARCHAR(255) NOT NULL,
    image_path VARCHAR(255) NOT NULL, -- Path relatif dari folder static/uploads atau semacamnya
    detection_class VARCHAR(100),
    confidence_score FLOAT,
    generative_description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indeks tambahan untuk performa query (opsional tapi direkomendasikan)
CREATE INDEX IF NOT EXISTS idx_user_id ON detections(user_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp);
