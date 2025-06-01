// Nama File: esp32_cam_code.ino
// Lokasi: D:/projek-yolo8/esp32_cam_code/esp32_cam_code.ino

#include "esp_camera.h"
#include "WiFi.h"
#include "WebServer.h" // Menggunakan WebServer standar untuk kesederhanaan

// ===========================================
//      Pengaturan Model Kamera AI-THINKER
// ===========================================
// Pastikan definisi pin ini sesuai dengan modul ESP32-CAM Anda.
// Untuk modul AI-Thinker standar (biasanya dengan kamera OV2640 atau OV3660).
// Jika Anda menggunakan kamera 5MP (seperti OV5640) dan modulnya memiliki pinout berbeda,
// Anda mungkin perlu membuat definisi custom atau mencari model yang sesuai.
// Untuk saat ini, kita menggunakan CAMERA_MODEL_AI_THINKER yang umum.
#define CAMERA_MODEL_AI_THINKER
// #define CAMERA_MODEL_M5STACK_PSRAM // Contoh model lain
// #define CAMERA_MODEL_WROVER_KIT // Contoh model lain

#if defined(CAMERA_MODEL_AI_THINKER)
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1 // NC
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26 // SDA
  #define SIOC_GPIO_NUM     27 // SCL
  
  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22
#else
  #error "Model kamera tidak dikenal. Silakan pilih model yang sesuai atau definisikan pin secara manual."
#endif


// ===========================================
//      Konfigurasi WiFi
// ===========================================
// Ganti dengan kredensial WiFi Anda
const char* ssid = "NAMA_WIFI_ANDA";         // << GANTI INI
const char* password = "PASSWORD_WIFI_ANDA"; // << GANTI INI

// Objek WebServer akan berjalan di port 80
WebServer server(80);

// Fungsi untuk menangani permintaan pengambilan gambar
void handleCapture();
// Fungsi untuk menangani halaman root (opsional, bisa menampilkan status)
void handleRoot();

void setup() {
  Serial.begin(115200);
  Serial.println("\nESP32-CAM Booting...");

  // Konfigurasi Kamera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM; // Sebelumnya SIOD_GPIO_NUM
  config.pin_sccb_scl = SIOC_GPIO_NUM; // Sebelumnya SIOC_GPIO_NUM
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000; // Frekuensi XCLK 20MHz
  config.pixel_format = PIXFORMAT_JPEG; // Format output JPEG untuk ukuran file lebih kecil

  // Pengaturan kualitas gambar dan resolusi
  // Jika PSRAM tersedia, gunakan untuk buffer yang lebih besar dan kualitas gambar lebih baik
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA; // Resolusi: UXGA (1600x1200). Cocok untuk 2MP.
                                       // Untuk 5MP (misalnya OV5640), Anda mungkin bisa menggunakan FRAMESIZE_QSXGA (2592x1944)
                                       // atau resolusi lain yang didukung kamera dan memiliki cukup memori.
                                       // Coba dengan resolusi lebih rendah dulu jika ada masalah:
                                       // FRAMESIZE_SVGA (800x600), FRAMESIZE_XGA (1024x768)
    config.jpeg_quality = 10;          // Kualitas JPEG (0-63, lebih rendah = kualitas lebih tinggi, ukuran lebih besar)
    config.fb_count = 2;               // Jumlah frame buffer (2 jika PSRAM cukup)
    config.grab_mode = CAMERA_GRAB_LATEST; // Ambil frame terbaru
  } else {
    config.frame_size = FRAMESIZE_SVGA; // Resolusi lebih rendah jika tidak ada PSRAM
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  // Inisialisasi Kamera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Inisialisasi kamera gagal dengan error 0x%x\n", err);
    // Restart ESP jika kamera gagal
    ESP.restart();
    return;
  }
  Serial.println("Inisialisasi kamera berhasil.");

  // Sesuaikan sensor kamera jika diperlukan (misal: flip, mirror)
  // sensor_t * s = esp_camera_sensor_get();
  // s->set_vflip(s, 1); // flip gambar secara vertikal
  // s->set_hmirror(s, 1); // mirror gambar secara horizontal


  // Koneksi ke WiFi
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) { // Coba selama ~15 detik
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nTerhubung ke WiFi!");
    Serial.print("Alamat IP ESP32-CAM: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nGagal terhubung ke WiFi. Restart dalam 5 detik...");
    delay(5000);
    ESP.restart();
  }

  // Mulai Web Server dan definisikan handler
  server.on("/", HTTP_GET, handleRoot);
  server.on("/capture", HTTP_GET, handleCapture);
  // Anda bisa menambahkan endpoint lain, misalnya /stream untuk video streaming

  server.begin();
  Serial.println("HTTP server dimulai. Akses /capture untuk mengambil gambar.");
}

void loop() {
  // Handle permintaan client
  server.handleClient();
  delay(10); // Sedikit delay untuk stabilitas
}

// Fungsi untuk menangani halaman root
void handleRoot() {
  String html = "<html><head><title>ESP32-CAM Server</title></head><body>";
  html += "<h1>ESP32-CAM Server</h1>";
  html += "<p>Selamat datang! Ini adalah server web ESP32-CAM.</p>";
  html += "<p>Untuk mengambil gambar, akses endpoint: <a href='/capture'>/capture</a></p>";
  html += "<p>Status Kamera: OK</p>";
  html += "<p>Alamat IP: " + WiFi.localIP().toString() + "</p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

// Fungsi untuk menangani permintaan pengambilan gambar
void handleCapture() {
  Serial.println("Permintaan /capture diterima.");
  camera_fb_t * fb = NULL; // Frame buffer
  esp_err_t res = ESP_OK;

  fb = esp_camera_fb_get(); // Mengambil frame dari kamera
  if (!fb) {
    Serial.println("Gagal mengambil frame dari kamera!");
    server.send(500, "text/plain", "Gagal mengambil frame dari kamera");
    // Jika gagal, coba restart kamera atau ESP. Untuk sekarang kirim error.
    // esp_camera_fb_return(fb); // Kembalikan buffer jika sudah terlanjur diambil
    // ESP.restart(); // Atau restart ESP
    return;
  }

  // Mengirim gambar sebagai response HTTP
  // Set header Content-Type ke image/jpeg
  server.setContentLength(fb->len);
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Access-Control-Allow-Origin", "*"); // Izinkan CORS jika diakses dari domain lain (Flask dev server)
  WiFiClient client = server.client();
  client.write(fb->buf, fb->len); // Kirim buffer gambar

  esp_camera_fb_return(fb); // Kembalikan frame buffer setelah dikirim

  Serial.println("Gambar berhasil dikirim.");
}

