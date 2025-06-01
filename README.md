# Sistem Deteksi Kualitas Oli Motor

Proyek ini adalah aplikasi web berbasis Flask yang dirancang untuk mendeteksi kualitas oli motor menggunakan model deteksi objek YOLOv8, dengan input gambar dari ESP32-CAM. Aplikasi ini juga memanfaatkan Google Gemini API untuk menghasilkan deskripsi generatif berdasarkan hasil deteksi.

## Kotributor dan Inisiator
- [Nailar Raza]
- [Angga Prasetyo, S.T., M.Kom]

## Teknologi yang Digunakan

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
* **Database:** MySQL (via XAMPP/MariaDB)
* **Model Deteksi Objek:** YOLOv8 (`.pt`)
* **Perangkat Keras Kamera:** ESP32-CAM (dengan _firmware custom_ Arduino)
* **AI Generatif:** Google Gemini API
* **Manajemen Lingkungan & Dependensi:** Virtual Environment (venv), pip, `requirements.txt`
* **Kontrol Versi:** Git & GitHub
* **ORM & Migrasi DB:** Flask-SQLAlchemy, Flask-Migrate
* **Formulir Web:** Flask-WTF
* **Manajemen Sesi & Keamanan:** Flask-Login, Flask-Bcrypt
* **Lainnya:** python-dotenv, Pillow, OpenCV-Python, Ultralytics, Requests

## Fitur Utama

* **Autentikasi Pengguna:** Sistem registrasi dan login pengguna yang aman.
* **Pengambilan Gambar Real-time:** Integrasi dengan ESP32-CAM untuk menangkap gambar sampel oli secara nirkabel.
* **Deteksi Kualitas Oli:** Menggunakan model YOLOv8 yang telah dilatih untuk mengklasifikasikan kualitas oli dari gambar.
* **Deskripsi Generatif:** Menghasilkan deskripsi dan saran berdasarkan hasil deteksi menggunakan Google Gemini API.
* **Visualisasi Hasil:** Menampilkan gambar hasil deteksi dengan _bounding box_ dan informasi detail (kelas, skor kepercayaan, deskripsi).
* **Riwayat Deteksi:** Menyimpan dan menampilkan riwayat deteksi untuk setiap pengguna.
* **Antarmuka Responsif:** Tampilan yang dapat menyesuaikan diri dengan berbagai ukuran layar (desktop dan mobile) menggunakan Bootstrap.
* **Mode Gelap (Dark Mode):** Pilihan tema tampilan untuk kenyamanan pengguna.



## Prasyarat

Sebelum memulai, pastikan Anda telah menginstal perangkat lunak berikut:
* [XAMPP](https://www.apachefriends.org/index.html) (dengan Apache dan MySQL berjalan)
* [Visual Studio Code](https://code.visualstudio.com/) (atau editor kode pilihan Anda)
* [Arduino IDE](https://www.arduino.cc/en/software) (dengan dukungan board ESP32)
* [Python](https://www.python.org/downloads/) (versi 3.8 atau lebih tinggi)
* [Git](https://git-scm.com/downloads)
* [Git LFS](https://git-lfs.github.com/) (jika file model `.pt` Anda besar, >50MB)

## Setup dan Instalasi

1.  **Clone Repositori:**
    ```bash
    git clone [https://github.com/usernameAnda/projek-yolo8.git](https://github.com/usernameAnda/projek-yolo8.git)
    cd projek-yolo8
    ```
    *(Ganti `usernameAnda/projek-yolo8.git` dengan URL repositori Anda)*

2.  **Setup Git LFS (Jika Menggunakan):**
    Jika model YOLO Anda besar dan Anda menggunakan Git LFS:
    ```bash
    git lfs install
    git lfs pull
    ```

3.  **Buat dan Aktifkan Virtual Environment:**
    ```bash
    python -m venv venv
    ```
    * Untuk Windows (PowerShell):
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
    * Untuk macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Install Dependensi Python:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Setup ESP32-CAM:**
    * Buka `esp32_code/esp32_cam_capture.ino` di Arduino IDE.
    * Ubah `ssid` dan `password` WiFi sesuai dengan jaringan Anda.
    * Upload _sketch_ ke ESP32-CAM Anda (pastikan GPIO0 terhubung ke GND saat proses upload).
    * Setelah berhasil, lepaskan GPIO0 dari GND, tekan tombol reset pada ESP32-CAM, dan buka Serial Monitor untuk mendapatkan alamat IP ESP32-CAM. Catat alamat IP ini.

6.  **Setup Database MySQL:**
    * Pastikan layanan MySQL dari XAMPP berjalan.
    * Buka phpMyAdmin (`http://localhost/phpmyadmin/`).
    * Buat database baru dengan nama `projek_yolo8_db` (gunakan _collation_ `utf8mb4_unicode_ci`).
    * Inisialisasi dan terapkan migrasi database:
        ```powershell
        # Pastikan venv aktif dan Anda berada di root folder proyek
        $env:FLASK_APP = "run.py" # Untuk PowerShell
        # export FLASK_APP=run.py # Untuk bash/zsh
        
        flask db init  # Hanya jika folder 'migrations' belum ada dan belum pernah dijalankan
        flask db migrate -m "Initial database setup for users and detections"
        flask db upgrade
        ```

7.  **Konfigurasi Variabel Lingkungan:**
    * Buat file bernama `.env` di _root folder_ proyek (`D:/projek-yolo8/.env`).
    * Salin konten dari contoh di bawah dan sesuaikan nilainya:
        ```env
        # Isi dari file .env
        SECRET_KEY="HASIL_GENERATE_SECRET_KEY_ANDA" # Generate menggunakan: python -c "import secrets; print(secrets.token_hex(32))"
        DATABASE_URL="mysql+mysqlconnector://root:PASSWORD_DB_ANDA@localhost/projek_yolo8_db" # Sesuaikan user & password DB jika perlu
        GOOGLE_GEMINI_API_KEY="API_KEY_GEMINI_ANDA"
        ESP32_CAM_IP="http://ALAMAT_IP_ESP32_ANDA" # Contoh: [http://192.168.1.101](http://192.168.1.101)

        # Catatan untuk DATABASE_URL:
        # Jika MySQL Anda di XAMPP menggunakan user 'root' tanpa password (default):
        # DATABASE_URL="mysql+mysqlconnector://root:@localhost/projek_yolo8_db"
        ```
    * **PENTING:** Jangan _commit_ file `.env` Anda ke Git. File ini sudah ada di `.gitignore`.

8.  **Tempatkan Model YOLOv8:**
    * Letakkan file model YOLOv8 Anda (misalnya, `model_oli_yolov8.pt`) ke dalam folder `D:/projek-yolo8/models_yolo/`.
    * Pastikan nama file model di `config.py` (variabel `MODEL_PATH`) sesuai dengan nama file model Anda.

## Menjalankan Aplikasi

1.  Pastikan layanan Apache dan MySQL di XAMPP sudah berjalan.
2.  Pastikan ESP32-CAM Anda menyala, terhubung ke WiFi, dan alamat IP-nya sudah benar di file `.env`.
3.  Pastikan _virtual environment_ Anda sudah aktif dan Anda berada di direktori _root_ proyek (`D:/projek-yolo8`).
4.  Jalankan server Flask:
    ```powershell
    # Pastikan $env:FLASK_APP = "run.py" sudah di-set
    flask run
    ```
5.  Buka _browser web_ Anda dan navigasi ke `http://127.0.0.1:5000/`.

## Panduan Penggunaan Singkat

1.  **Registrasi:** Jika Anda pengguna baru, klik _link_ "Register" atau "Daftar di sini" dan isi formulir untuk membuat akun.
2.  **Login:** Masuk menggunakan email dan _password_ yang telah terdaftar.
3.  **Dashboard:**
    * Anda akan melihat _stream_ video langsung dari ESP32-CAM.
    * Arahkan kamera ESP32-CAM ke sampel oli motor yang ingin diuji.
    * Klik tombol "Tangkap Gambar & Deteksi".
4.  **Hasil Deteksi:**
    * Setelah proses selesai, Anda akan diarahkan ke halaman hasil.
    * Di sini Anda akan melihat gambar oli dengan _bounding box_ (jika ada deteksi), kelas kualitas oli, skor kepercayaan, dan deskripsi generatif dari Gemini API.
5.  **Histori Deteksi:**
    * Akses halaman "Histori" dari _navbar_ untuk melihat riwayat semua deteksi yang telah Anda lakukan.
    * Anda dapat mengklik "Lihat Hasil" pada setiap entri untuk melihat detailnya kembali.
6.  **Mode Gelap:** Gunakan tombol _toggle_ di _navbar_ untuk mengubah tema tampilan antara mode terang dan gelap.
7.  **Logout:** Klik _link_ "Logout" untuk keluar dari aplikasi.

---

Semoga berhasil menjalankan dan mengembangkan proyek ini lebih lanjut! Jika ada pertanyaan atau masalah, silakan buka _issue_ di repositori ini.
