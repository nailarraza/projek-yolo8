// Pastikan library yang dibutuhkan sudah terinstal di Arduino IDE Anda
// (WiFi, ESPmDNS, WebServer, esp_camera)

#include "esp_camera.h"
#include <WiFi.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h" // Untuk httpd_resp_set_type, dll. jika menggunakan ESP-IDF style server
// Jika menggunakan library WebServer.h standar Arduino:
#include <WebServer.h>

// Ganti dengan kredensial WiFi Anda
const char* ssid = "Gopo Network";
const char* password = "sister23";

// Definisikan pin kamera sesuai dengan modul ESP32-CAM Anda
// Model AI-THINKER
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

WebServer server(80);

// --- Pengaturan untuk Kualitas Stream dan Capture ---
#define DEFAULT_STREAM_FRAMESIZE FRAMESIZE_VGA // Misalnya VGA (640x480) untuk streaming
#define DEFAULT_STREAM_QUALITY 12            // Kualitas JPEG untuk streaming (0-63, lebih tinggi = kualitas lebih rendah, ukuran lebih kecil)

#define CAPTURE_FRAMESIZE FRAMESIZE_UXGA     // Misalnya UXGA (1600x1200) untuk capture
#define CAPTURE_QUALITY 10                   // Kualitas JPEG untuk capture (0-63, lebih rendah = kualitas lebih tinggi)

// Variabel global untuk menyimpan pengaturan stream default
framesize_t streamFrameSize = DEFAULT_STREAM_FRAMESIZE;
int streamJpegQuality = DEFAULT_STREAM_QUALITY;

// Handler untuk mengambil foto berkualitas tinggi
void handleCapture() {
  camera_fb_t * fb = NULL;
  sensor_t * s = esp_camera_sensor_get();
  if (!s) {
    Serial.println("handleCapture: Gagal mendapatkan sensor kamera.");
    server.send(500, "text/plain", "Gagal mendapatkan sensor kamera");
    return;
  }

  Serial.println("handleCapture: Menerima permintaan untuk mengambil gambar...");

  // Simpan pengaturan stream saat ini
  framesize_t original_frame_size = s->status.framesize;
  int original_jpeg_quality = s->pixformat == PIXFORMAT_JPEG ? s->status.quality : streamJpegQuality;

  // Atur sensor untuk kualitas capture terbaik
  s->set_framesize(s, psramFound() ? CAPTURE_FRAMESIZE : FRAMESIZE_SVGA); // Sesuaikan jika tidak ada PSRAM
  s->set_quality(s, CAPTURE_QUALITY);
  Serial.printf("handleCapture: Sensor diatur ke framesize %d, quality %d untuk capture.\n", s->status.framesize, s->status.quality);

  fb = esp_camera_fb_get();
  
  // Kembalikan sensor ke pengaturan stream SEGERA setelah fb didapatkan
  s->set_framesize(s, original_frame_size);
  s->set_quality(s, original_jpeg_quality);
  Serial.printf("handleCapture: Sensor dikembalikan ke framesize %d, quality %d (pengaturan stream).\n", s->status.framesize, s->status.quality);

  if (!fb) {
    Serial.println("handleCapture: Pengambilan gambar dari kamera gagal (esp_camera_fb_get mengembalikan NULL).");
    server.send(500, "text/plain", "Gagal mengambil gambar dari kamera");
    return;
  }

  Serial.printf("handleCapture: Gambar berhasil diambil. Ukuran: %zu bytes, Format: %d\n", fb->len, fb->format);

  if (fb->format != PIXFORMAT_JPEG) {
    Serial.printf("handleCapture: Format frame yang diambil bukan JPEG (format: %d). Diharapkan: %d.\n", fb->format, PIXFORMAT_JPEG);
    esp_camera_fb_return(fb); // Kembalikan frame buffer
    server.send(500, "text/plain", "Format gambar yang diambil bukan JPEG");
    return;
  }

  // Periksa apakah client masih terhubung
  WiFiClient client = server.client();
  if (!client || !client.connected()) {
    Serial.println("handleCapture: Client terputus sebelum pemrosesan gambar.");
    esp_camera_fb_return(fb);
    // Tidak bisa mengirim response ke client yang sudah terputus
    return;
  }

  // Mengirim header HTTP secara eksplisit
  server.sendHeader("Access-Control-Allow-Origin", "*"); // Izinkan CORS
  server.setContentLength(fb->len);
  // Kirim status 200 OK dengan Content-Type. String kosong menandakan body akan dikirim terpisah.
  server.send(200, "image/jpeg", ""); 

  Serial.println("handleCapture: Header HTTP telah dikirim. Mencoba menulis data gambar ke client...");

  size_t sent_len = client.write(fb->buf, fb->len);

  if (sent_len == fb->len) {
    Serial.printf("handleCapture: Data gambar berhasil dikirim (%zu bytes).\n", sent_len);
  } else {
    Serial.printf("handleCapture: Gagal mengirim data gambar secara lengkap. Terkirim %zu dari %zu bytes.\n", sent_len, fb->len);
    // Client mungkin menutup koneksi saat transfer.
  }

  esp_camera_fb_return(fb); // Kembalikan frame buffer
  Serial.println("handleCapture: Frame buffer telah dikembalikan. Permintaan selesai diproses.");
}

// Handler untuk streaming MJPEG
void handleStream() {
  WiFiClient client = server.client();
  if (!client.connected()) {
    Serial.println("handleStream: Client terputus.");
    return;
  }

  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=--frame\r\n";
  response += "Access-Control-Allow-Origin: *\r\n"; // Izinkan CORS
  response += "\r\n";
  server.sendContent(response);

  Serial.println("handleStream: Memulai streaming MJPEG...");
  unsigned long lastFrameTime = 0;

  while (client.connected()) {
    // Batasi frame rate untuk tidak membebani ESP32 atau jaringan
    if (millis() - lastFrameTime < 100) { // Target sekitar 10 FPS (1000ms / 100ms = 10 FPS)
      delay(1); // Beri kesempatan task lain berjalan
      continue;
    }
    lastFrameTime = millis();

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("handleStream: Gagal mengambil frame untuk stream.");
      // Mungkin kirim pesan error ke client atau cukup skip frame ini
      delay(100); // Tunggu sebentar sebelum mencoba lagi
      continue;
    }

    response = "--frame\r\n";
    response += "Content-Type: image/jpeg\r\n";
    response += "Content-Length: " + String(fb->len) + "\r\n\r\n";
    server.sendContent(response);
    
    client.write(fb->buf, fb->len);
    server.sendContent("\r\n");
    
    esp_camera_fb_return(fb);
  }
  Serial.println("handleStream: Streaming MJPEG dihentikan, client terputus.");
}

void startCameraServer() {
  // Endpoint untuk capture foto
  server.on("/capture_image", HTTP_GET, handleCapture);
  server.on("/stream", HTTP_GET, handleStream); // Endpoint untuk streaming MJPEG

  server.begin();
  Serial.println("HTTP server started");
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector

  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

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
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG; // Untuk capture JPEG

  // Atur konfigurasi awal untuk STREAMING
  config.frame_size = streamFrameSize; 
  config.jpeg_quality = streamJpegQuality; 

  if (psramFound()) {
    config.fb_count = 2; // Gunakan 2 frame buffer jika ada PSRAM
    Serial.println("PSRAM ditemukan, menggunakan 2 frame buffer.");
  } else {
    // Jika tidak ada PSRAM, mungkin perlu frame size lebih kecil untuk capture
    // dan pastikan streamFrameSize juga tidak terlalu besar.
    // CAPTURE_FRAMESIZE akan disesuaikan di handleCapture jika tidak ada PSRAM.
    Serial.println("PSRAM tidak ditemukan, menggunakan 1 frame buffer. Kualitas capture mungkin terbatas.");
    config.fb_count = 1;
  }

  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  // Atur parameter sensor jika perlu (misalnya, flip, mirror, dll.)
  // s->set_vflip(s, 1); // flip it on screen
  // s->set_hmirror(s, 1); // mirror it on screen

  // WiFi connection
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");

  startCameraServer();
}

void loop() {
  server.handleClient();
  delay(2); // Sedikit delay untuk stabilitas
}
