-- Membuat Tabel Users
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password` VARCHAR(255) NOT NULL, -- Pastikan kata sandi di-hash sebelum disimpan
  `email` VARCHAR(100) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Diubah menjadi NOT NULL
  PRIMARY KEY (`id`),
  UNIQUE INDEX `username_UNIQUE` (`username` ASC), -- VISIBLE bisa dihilangkan karena default
  UNIQUE INDEX `email_UNIQUE` (`email` ASC)      -- VISIBLE bisa dihilangkan karena default
) ENGINE = InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; -- Menggunakan collation yang lebih modern jika MySQL 8.0+

-- Membuat Tabel Detections
CREATE TABLE `detections` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `image_name` VARCHAR(255) NOT NULL,
  `image_path` VARCHAR(255) NOT NULL,
  `detection_class` VARCHAR(50) NOT NULL,
  `confidence_score` FLOAT NULL, -- FLOAT cocok untuk skor kepercayaan
  `generative_description` TEXT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_detections_users_idx` (`user_id` ASC), -- VISIBLE bisa dihilangkan
  CONSTRAINT `fk_detections_users`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`)
    ON DELETE CASCADE  -- Jika user dihapus, deteksinya juga terhapus
    ON UPDATE NO ACTION -- Disarankan untuk tidak mengupdate Primary Key (users.id)
) ENGINE = InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; -- Menggunakan collation yang lebih modern jika MySQL 8.0+