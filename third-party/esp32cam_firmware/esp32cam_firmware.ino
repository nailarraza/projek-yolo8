// D:/projek-yolo8/third-party/esp32cam_firmware/esp32cam_firmware.ino

#include "esp_camera.h"
#include <WiFi.h>
#include "soc/soc.h"             // Disable brownout problems
#include "soc/rtc_cntl_reg.h"    // Disable brownout problems
#include "driver/rtc_io.h"
#include <WebServer.h>          // Untuk membuat web server sederhana
#include <WiFiClient.h>

// ===========================================
//      Pengaturan Model Kamera
// ===========================================
// Ganti model kamera jika perlu. Model yang umum adalah CAMERA_MODEL_AI_THINKER.
// Untuk kamera 5MP (seperti OV5640), pinout mungkin perlu disesuaikan.
// Pinout ini adalah untuk AI-THINKER. Jika Anda menggunakan board ESP32-CAM lain atau kamera OV5640 dengan pinout berbeda,
// Anda HARUS menyesuaikan pin-pin ini. Untuk ESP32-S3 dengan kamera terintegrasi, Anda WAJIB mendefinisikan pin sesuai board Anda.
//#define CAMERA_MODEL_AI_THINKER
//#define CAMERA_MODEL_M5STACK_PSRAM
//#define CAMERA_MODEL_M5STACK_V2_PSRAM
//#define CAMERA_MODEL_M5STACK_WIDE
//#define CAMERA_MODEL_M5STACK_ESP32CAM
//#define CAMERA_MODEL_WROVER_KIT
#define CAMERA_MODEL_ESP32S3_OV5640_INTEGRATED // Aktifkan ini untuk ESP32-S3 dengan OV5640 terintegrasi

#if defined(CAMERA_MODEL_AI_THINKER)
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27
  
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
  #error "Camera model not selected or defined"
#endif

// ================================================================================================
//      PENTING: Pengaturan Pin Kamera untuk ESP32-S3 dengan OV5640 Terintegrasi
// ================================================================================================
// **ANDA WAJIB MENGGANTI PIN-PIN DI BAWAH INI SESUAI DENGAN KONEKSI FISIK PADA BOARD ESP32-S3 ANDA!**
// Cek skematik board ESP32-S3 Anda untuk pinout kamera yang benar.
// Pin-pin berikut adalah CONTOH dan kemungkinan besar TIDAK AKAN BEKERJA tanpa penyesuaian.
#if defined(CAMERA_MODEL_ESP32S3_OV5640_INTEGRATED)
  #define PWDN_GPIO_NUM     -1 // GPIO untuk Power Down camera (-1 jika tidak digunakan atau dikontrol otomatis)
  #define RESET_GPIO_NUM    -1 // GPIO untuk Reset camera (-1 jika tidak digunakan atau terhubung ke RST ESP32)
  #define XCLK_GPIO_NUM     15 // CONTOH: GPIO untuk XCLK camera (misal: GPIO15)
  #define SIOD_GPIO_NUM     4  // CONTOH: GPIO untuk SCCB SDA (I2C Data) (misal: GPIO4)
  #define SIOC_GPIO_NUM     5  // CONTOH: GPIO untuk SCCB SCL (I2C Clock) (misal: GPIO5)
  
  #define Y9_GPIO_NUM       16 // CONTOH: D7 (misal: GPIO16)
  #define Y8_GPIO_NUM       17 // CONTOH: D6 (misal: GPIO17)
  #define Y7_GPIO_NUM       18 // CONTOH: D5 (misal: GPIO18)
  #define Y6_GPIO_NUM       12 // CONTOH: D4 (misal: GPIO12)
  #define Y5_GPIO_NUM       11 // CONTOH: D3 (misal: GPIO11)
  #define Y4_GPIO_NUM       10 // CONTOH: D2 (misal: GPIO10)
  #define Y3_GPIO_NUM       9  // CONTOH: D1 (misal: GPIO9)
  #define Y2_GPIO_NUM       8  // CONTOH: D0 (misal: GPIO8)
  #define VSYNC_GPIO_NUM    6  // CONTOH: VSYNC (misal: GPIO6)
  #define HREF_GPIO_NUM     7  // CONTOH: HREF (misal: GPIO7)
  #define PCLK_GPIO_NUM     13 // CONTOH: PCLK (misal: GPIO13)
#elif !defined(CAMERA_MODEL_AI_THINKER) // Tambahkan kondisi lain jika ada model lain
  #error "Camera model not selected"
#endif

// ===========================================
//      Pengaturan WiFi
// ===========================================
const char* ssid = "Gopo Network";         // Ganti dengan nama WiFi Anda
const char* password = "sister23"; // Ganti dengan password WiFi Anda

// ===========================================
//      Pengaturan Web Server
// ===========================================
WebServer server(80); // Server akan berjalan di port 80 (HTTP)
// Untuk stream, kita bisa menggunakan port berbeda jika port 80 sudah dipakai atau diblokir
// WebServer streamServer(81); // Contoh jika ingin stream di port 81

// LED Flash (jika ada dan ingin dikontrol)
// Ganti dengan GPIO yang terhubung ke LED Flash pada board ESP32-S3 Anda.
#define FLASH_GPIO_NUM -1 // Set ke -1 jika tidak ada LED flash atau tidak ingin digunakan. Contoh: 4 jika ada di GPIO4.
bool flashState = LOW;

// Fungsi untuk memulai server dan menangani permintaan
void startCameraServer();
void handleJpgStream(void);
void handleJpg(void);
void handleNotFound(void);

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector

  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

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
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000; // Frekuensi XCLK 20MHz
  config.pixel_format = PIXFORMAT_JPEG; // Format output JPEG untuk kualitas terbaik dan ukuran file terkecil
  
  // Jika PSRAM tersedia, gunakan untuk buffer yang lebih besar
  // Ini penting untuk resolusi tinggi
  if(psramFound()){
    Serial.println("PSRAM ditemukan! Menggunakan PSRAM untuk frame buffer.");
    config.frame_size = FRAMESIZE_UXGA; // UXGA=1600x1200. Baik untuk streaming dengan OV5640.
                                        // Untuk foto tunggal berkualitas tertinggi, Anda bisa coba FRAMESIZE_QSXGA (2592x1944),
                                        // tapi mungkin terlalu berat untuk streaming kontinu.
                                        // Coba juga: FRAMESIZE_SXGA (1280x1024), FRAMESIZE_XGA (1024x768)
    config.jpeg_quality = 10; // 0-63, lebih rendah = kualitas lebih tinggi, tapi ukuran lebih besar. 10-12 adalah kompromi yang baik.
    config.fb_count = 2;      // Gunakan 2 frame buffer jika PSRAM ada, atau 1 jika tidak.
                              // Dengan 8MB PSRAM pada N16R8, 2 sudah cukup. Anda bisa coba 3 jika perlu.
    config.fb_location = CAMERA_FB_IN_PSRAM; // Simpan frame buffer di PSRAM
  } else {
    config.frame_size = FRAMESIZE_SVGA; // SVGA=800x600. Jika tidak ada PSRAM, resolusi lebih rendah.
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM; // Simpan frame buffer di DRAM
  }

  // Inisialisasi Kamera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Inisialisasi kamera gagal dengan error 0x%x", err);
    // Lakukan restart jika gagal
    ESP.restart();
    return;
  }
  Serial.println("Inisialisasi kamera berhasil.");

  // Atur sensor jika perlu (misalnya flip, mirror, dll.)
  sensor_t * s = esp_camera_sensor_get();
  // s->set_vflip(s, 1);       // Flip gambar secara vertikal
  // s->set_hmirror(s, 1);     // Mirror gambar secara horizontal
  // s->set_brightness(s, 0);  // -2 to 2
  // s->set_contrast(s, 0);    // -2 to 2
  // s->set_saturation(s, 0);  // -2 to 2
  // s->set_special_effect(s, 0); // 0-6 (0 - no effect, 1 - negative, 2 - grayscale, 3 - reddish, 4 - greenish, 5 - bluish, 6 - sepia)


  // Inisialisasi LED Flash (jika ada)
  if (FLASH_GPIO_NUM != -1) {
    pinMode(FLASH_GPIO_NUM, OUTPUT);
    digitalWrite(FLASH_GPIO_NUM, flashState);
  }

  // Koneksi ke WiFi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false); // Nonaktifkan mode tidur WiFi untuk koneksi yang lebih stabil (konsumsi daya lebih tinggi)

  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi terhubung!");
  Serial.print("Alamat IP ESP32-CAM: http://");
  Serial.println(WiFi.localIP());

  // Mulai Web Server
  startCameraServer();
  Serial.println("Server kamera dimulai. Buka IP di atas di browser Anda.");
  Serial.println("Endpoint: /capture (untuk foto), /stream (untuk video stream)");
}

void loop() {
  server.handleClient(); // Tangani permintaan klien yang masuk
  // streamServer.handleClient(); // Jika menggunakan server stream terpisah
}

// Fungsi untuk memulai server dan mendefinisikan handler
void startCameraServer(){
  server.on("/", HTTP_GET, [](){
    String html = "<!DOCTYPE html><html><head><title>ESP32-S3 Kamera Server</title>";
    html += "<style>body{font-family: Arial, Helvetica, sans-serif; text-align: center;}</style>";
    html += "</head><body><h1>ESP32-S3 Kamera Server</h1>";
    html += "<p><a href='/capture'><button>Ambil Foto (Capture)</button></a></p>";
    html += "<p><a href='/stream'><button>Mulai Streaming Video</button></a></p>";
    
    if (FLASH_GPIO_NUM != -1) {
      html += "<p>Status LED Flash: <span id='flashStatus'>MATI</span> <button onclick='toggleFlash()'>Toggle Flash</button></p>";
    }
    
    html += "<h3>Live Stream:</h3>";
    html += "<img src='/stream' width='640' height='480' style='border: 1px solid black;'>"; // Embed stream langsung
    
    if (FLASH_GPIO_NUM != -1) {
      html += "<script>";
      html += "function toggleFlash(){fetch('/toggle-flash').then(res => res.text()).then(data => {document.getElementById('flashStatus').innerText = data;});}";
      html += "function updateFlashStatus(){fetch('/flash-status').then(res => res.text()).then(data => {document.getElementById('flashStatus').innerText = data;});}";
      html += "updateFlashStatus(); setInterval(updateFlashStatus, 2000);"; // Update status flash periodik
      html += "</script>";
    }
    html += "</body></html>";
    server.send(200, "text/html", html);
  });

  server.on("/capture", HTTP_GET, handleJpg);
  server.on("/stream", HTTP_GET, handleJpgStream);
  
  // Endpoint untuk mengontrol flash
  if (FLASH_GPIO_NUM != -1) {
    server.on("/toggle-flash", HTTP_GET, [](){
      flashState = !flashState;
      digitalWrite(FLASH_GPIO_NUM, flashState);
      server.send(200, "text/plain", flashState ? "NYALA" : "MATI");
    });
    server.on("/flash-status", HTTP_GET, [](){
      server.send(200, "text/plain", flashState ? "NYALA" : "MATI");
    });
  }

  server.onNotFound(handleNotFound);
  server.begin();
}

// Handler untuk mengambil satu frame foto (JPEG)
void handleJpg(){
  if (!server.client() || !server.client().connected()) {
    return; // Client sudah disconnect
  }
  WiFiClient client = server.client();

  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;

  // Ambil frame dari kamera
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Pengambilan frame kamera gagal");
    if (client.connected()) { // Hanya kirim response jika client masih ada
        server.send(500, "text/plain", "Gagal mengambil frame dari kamera.");
    }
    return;
  }
  Serial.printf("Frame diambil! Format: %d, Ukuran: %d, Lebar: %d, Tinggi: %d\n", fb->format, fb->len, fb->width, fb->height);

  // Kirim header HTTP
  bool headers_sent_ok = true;
  if (headers_sent_ok) headers_sent_ok = (client.print("HTTP/1.1 200 OK\r\n") > 0);
  if (headers_sent_ok) headers_sent_ok = (client.print("Content-Type: image/jpeg\r\n") > 0);
  if (headers_sent_ok) headers_sent_ok = (client.print("Content-Disposition: inline; filename=capture.jpg\r\n") > 0);
  if (headers_sent_ok) headers_sent_ok = (client.print("Content-Length: ") > 0);
  if (headers_sent_ok) headers_sent_ok = (client.print(fb->len) > 0);
  if (headers_sent_ok) headers_sent_ok = (client.print("\r\n\r\n") > 0);

  if (!headers_sent_ok) {
    Serial.println("Gagal mengirim header HTTP untuk capture.");
    esp_camera_fb_return(fb);
    return;
  }

  // Kirim data gambar JPEG
  if(client.write(fb->buf, fb->len) != fb->len){
    Serial.println("Gagal mengirim data gambar JPEG untuk capture.");
    // Header mungkin sudah terkirim sebagian, jadi tidak bisa send 500
  }

  // Kembalikan frame buffer ke kamera agar bisa digunakan lagi
  esp_camera_fb_return(fb);
  // Koneksi akan ditutup oleh client atau WebServer class
}


// Handler untuk streaming video (MJPEG)
void handleJpgStream(){
  WiFiClient client = server.client();
  if (!client || !client.connected()) {
    return;
  }
  
  // Kirim header awal untuk stream MJPEG
  if (client.print("HTTP/1.1 200 OK\r\n"
                   "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
                   "\r\n") == 0) {
    Serial.println("Gagal mengirim header stream");
    return;
  }
  Serial.println("Memulai stream MJPEG ke client.");

  // Loop untuk mengirim frame secara berkelanjutan
  while(client.connected()){ // Terus kirim selama client terhubung
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    
    // Ambil frame dari kamera
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Pengambilan frame kamera gagal untuk stream");
      // Mungkin kirim pesan error sebagai bagian dari stream atau skip frame
      // Untuk kesederhanaan, kita skip jika gagal
      delay(200); // Beri jeda lebih lama jika gagal ambil frame
      continue;
    }

    // Kirim boundary dan header untuk frame JPEG ini
    if (!client.connected()) { // Cek lagi sebelum kirim
      esp_camera_fb_return(fb);
      break;
    }
    if (client.printf("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len) == 0) {
      Serial.println("Gagal mengirim header frame JPEG");
      esp_camera_fb_return(fb); // Jangan lupa return buffer
      break; // Keluar dari loop jika client disconnect atau error
    }

    // Kirim data gambar JPEG
    if (client.write(fb->buf, fb->len) != (size_t)fb->len) {
      Serial.println("Gagal mengirim data frame JPEG");
      esp_camera_fb_return(fb);
      break; 
    }
    
    // Kirim CRLF setelah data gambar (penting untuk beberapa browser/client)
     if (client.print("\r\n") == 0) {
      Serial.println("Gagal mengirim CRLF setelah frame");
      esp_camera_fb_return(fb);
      break;
    }

    // Kembalikan frame buffer
    esp_camera_fb_return(fb);

    // Cek apakah client masih terhubung
    if (!client.connected()) {
      Serial.println("Client disconnected dari stream.");
      break;
    }
    
    delay(66); // Target ~15 FPS (1000ms / 15fps = 66.6ms). Sesuaikan sesuai kebutuhan.
               // Untuk UXGA, 10-15 FPS adalah target yang realistis dan tidak terlalu membebani.
               // delay(100) untuk ~10 FPS.
  }
  Serial.println("Stream MJPEG dihentikan.");
}

// Handler jika halaman tidak ditemukan (404)
void handleNotFound(){
  String message = "File Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET)?"GET":"POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i=0; i<server.args(); i++){
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
}
