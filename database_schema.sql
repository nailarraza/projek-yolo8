-- Pastikan Anda sudah memilih database 'db_projek_yolo8'
-- atau tambahkan `USE db_projek_yolo8;` di awal jika menjalankan sebagai skrip utuh.


USE db_projek_yolo8;
-- Membuat Tabel User
CREATE TABLE `User` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(80) UNIQUE NOT NULL,
    `email` VARCHAR(120) UNIQUE NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Membuat Tabel Deteksi
CREATE TABLE `Deteksi` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `image_name` VARCHAR(255) NOT NULL,
    `image_path` VARCHAR(255) NOT NULL,
    `detection_class` VARCHAR(100),
    `confidence_score` DECIMAL(5,4),
    `generative_description` TEXT,
    FOREIGN KEY (`user_id`) REFERENCES `User`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;