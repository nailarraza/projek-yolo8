-- Membuat Tabel Users
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL, -- Akan menyimpan password yang sudah di-hash
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Membuat Tabel Detections
CREATE TABLE `detections` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `image_name` VARCHAR(255) NOT NULL,
  `image_path` VARCHAR(255) NOT NULL,
  `detection_class` VARCHAR(100),
  `confidence_score` FLOAT,
  `generative_description` TEXT,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Keterangan Tambahan:
-- ON DELETE CASCADE: Jika seorang user dihapus, semua data deteksi terkait user tersebut juga akan dihapus.
-- ON UPDATE CASCADE: Jika id user di tabel users berubah, user_id di tabel detections juga akan terupdate.