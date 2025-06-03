#include "esp_camera.h"
#include <WiFi.h>
#include "soc/soc.h"             // Disable brownout problems
#include "soc/rtc_cntl_reg.h"  // Disable brownout problems
#include "driver/rtc_io.h"
#include <WebServer.h>          // Library WebServer standar

// Ganti dengan kredensial WiFi kamu
const char* ssid = "Gopo Network";
const char* password = "sister23";

// Pin definition for CAMERA_MODEL_AI_THINKER
// Sesuaikan pin ini jika kamu menggunakan model ESP32-CAM yang berbeda
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

WebServer server(80); // Port server HTTP (default 80)

// Deklarasi fungsi
void startCameraServer();
void handleCapture();
void handleStream();
void handleRoot();

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
  config.pixel_format = PIXFORMAT_JPEG; // Format JPEG untuk streaming

  // Pengaturan Resolusi dan Kualitas:
  // Untuk kamera 5MP, resolusi awal bisa diatur lebih rendah untuk stabilitas streaming.
  // Pilihan resolusi: FRAMESIZE_QVGA (320x240), FRAMESIZE_CIF (352x288), FRAMESIZE_VGA (640x480),
  // FRAMESIZE_SVGA (800x600), FRAMESIZE_XGA (1024x768), FRAMESIZE_SXGA (1280x1024), FRAMESIZE_UXGA (1600x1200)
  // Untuk streaming, FRAMESIZE_VGA atau FRAMESIZE_SVGA biasanya cukup.
  // Untuk capture 5MP, gunakan FRAMESIZE_QXGA (2048x1536) atau lebih tinggi jika didukung,
  // namun ini akan lambat dan membutuhkan banyak memori. Uji kestabilan.
  // Mulai dengan resolusi rendah untuk streaming (misalnya FRAMESIZE_VGA).
  config.frame_size = FRAMESIZE_VGA; // Resolusi awal untuk streaming
  config.jpeg_quality = 12; // Kualitas JPEG (0-63), semakin rendah semakin cepat tapi kualitas menurun
  config.fb_count = 2;      // Gunakan 2 frame buffer untuk streaming yang lebih lancar jika PSRAM tersedia.
                            // Ini membantu mengurangi error "fb_get(): Failed to get the frame on time!".
                            // Jika PSRAM tidak ada atau terbatas, kembali ke 1.
  config.fb_location = CAMERA_FB_IN_PSRAM; // Alokasikan frame buffer di PSRAM
  config.grab_mode = CAMERA_GRAB_LATEST;   // Ambil frame terbaru, buang yang lama jika buffer penuh.
                                           // Baik untuk streaming agar latensi rendah.

  // Inisialisasi Kamera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Inisialisasi Kamera GAGAL dengan error 0x%x", err);
    Serial.println("Pastikan model kamera (CAMERA_MODEL_AI_THINKER) sudah benar dan semua pin terhubung dengan baik.");
    Serial.println("Coba turunkan resolusi atau periksa catu daya.");
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  // Atur beberapa parameter kamera jika diperlukan (opsional, uncomment dan sesuaikan nilainya)
  // s->set_brightness(s, 0);     // -2 to 2
  // s->set_contrast(s, 0);       // -2 to 2
  // s->set_saturation(s, 0);     // -2 to 2
  // s->set_special_effect(s, 0); // 0 to 6 (0 - no effect)
  // s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
  // s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
  // s->set_wb_mode(s, 0);        // 0 to 4
  // s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
  // s->set_aec_value(s, 300);    // 0 to 1200
  // s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
  // s->set_agc_gain(s, 0);       // 0 to 30
  // s->set_gainceiling(s, (gainceiling_t)0); // 0 to 6
  // s->set_vflip(s, 0);          // 0 = disable , 1 = enable (untuk membalik gambar vertikal)
  // s->set_hmirror(s, 0);        // 0 = disable , 1 = enable (untuk membalik gambar horizontal)

  // Koneksi WiFi
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) { // Coba selama 15 detik
    delay(500);
    Serial.print(".");
    retries++;
  }
  Serial.println("");

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi terhubung!");
    Serial.print("Alamat IP ESP32-CAM: http://");
    Serial.println(WiFi.localIP());
    startCameraServer(); // Mulai server hanya jika WiFi terhubung
  } else {
    Serial.println("Gagal terhubung ke WiFi. Silakan cek kredensial atau sinyal WiFi.");
    Serial.println("Server tidak dimulai.");
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    server.handleClient();
  }
  delay(1); // Delay kecil untuk stabilitas
}

void startCameraServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/stream", HTTP_GET, handleStream);
  server.on("/capture", HTTP_GET, handleCapture);
  server.begin();
  Serial.println("HTTP server dimulai.");
  Serial.print("Stream: http://"); Serial.print(WiFi.localIP()); Serial.println("/stream");
  Serial.print("Capture: http://"); Serial.print(WiFi.localIP()); Serial.println("/capture");
}

void handleRoot() {
  String html = "<html><head><title>ESP32-CAM Server</title></head><body>";
  html += "<h1>ESP32-CAM Live Server</h1>";
  html += "<p><img src='/stream' width='640' height='480'></p>"; // Menampilkan stream langsung di root
  html += "<p><a href='/capture' target='_blank'><button>Ambil Gambar</button></a></p>";
  html += "<p>Buka <a href='/stream'>/stream</a> untuk MJPEG stream.</p>";
  html += "<p>Buka <a href='/capture'>/capture</a> untuk mengambil satu gambar.</p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleStream() {
  WiFiClient client = server.client();
  if (!client.connected()) {
    Serial.println("Stream: Client disconnected.");
    return;
  }

  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  server.sendContent(response); // Kirim header MJPEG

  unsigned long lastFrameTime = 0;
  // Targetkan sekitar 10-15 FPS untuk mengurangi beban dan panas. Sesuaikan delay_per_frame.
  // 1000ms / 10 FPS = 100ms delay. 1000ms / 15 FPS = ~66ms delay.
  const int delay_per_frame = 80; // (ms) -> sekitar 12.5 FPS. Naikkan jika panas.

  while (client.connected()) {
    if (millis() - lastFrameTime < delay_per_frame) {
      delay(1); // Tunggu sebentar jika belum waktunya kirim frame baru
      continue;
    }
    lastFrameTime = millis();

    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Stream: Pengambilan frame kamera gagal");
      // Jika sering terjadi, coba kurangi resolusi, jpeg_quality, atau naikkan fb_count jika memori cukup.
      // Bisa juga karena catu daya kurang stabil.
      // Kirim pesan error ke client agar tidak hang
      // server.sendContent("--frame\r\nContent-Type: text/plain\r\n\r\nError: Frame capture failed\r\n");
      // Untuk MJPEG, lebih baik skip frame yang error
      continue;
    }

    client.print("--frame\r\n");
    client.print("Content-Type: image/jpeg\r\n");
    client.print("Content-Length: ");
    client.print(fb->len);
    client.print("\r\n\r\n");
    client.write(fb->buf, fb->len);
    client.print("\r\n");

    esp_camera_fb_return(fb);

    if (!client.connected()) { // Cek lagi koneksi client setelah mengirim frame
        Serial.println("Stream: Client disconnected after sending frame.");
        break;
    }
  }
  Serial.println("Stream: Sesi streaming berakhir.");
}

void handleCapture() {
  Serial.println("Capture: Permintaan diterima.");
  camera_fb_t * fb = NULL;

  // Opsional: Jika ingin resolusi lebih tinggi khusus untuk capture.
  // Pastikan ESP32-CAM kamu stabil dengan resolusi tinggi ini dan punya cukup memori.
  // PENTING: Untuk debugging timeout, biarkan ini di-comment dulu untuk memastikan capture berjalan dengan resolusi streaming (VGA).
  // sensor_t * s = esp_camera_sensor_get();
  // Serial.println("Capture: Mencoba mengubah resolusi untuk capture...");
  // s->set_framesize(s, FRAMESIZE_UXGA); // Contoh: 1600x1200. Bisa juga FRAMESIZE_SXGA (1280x1024) atau XGA (1024x768)
  // delay(500); // Beri waktu kamera untuk menyesuaikan dengan resolusi baru

  Serial.println("Capture: Mencoba mengambil frame (esp_camera_fb_get)...");
  unsigned long preCaptureTime = millis();
  fb = esp_camera_fb_get();
  unsigned long postCaptureTime = millis();
  Serial.printf("Capture: esp_camera_fb_get selesai dalam %lu ms.\n", postCaptureTime - preCaptureTime);

  if (!fb) {
    Serial.println("Capture: Pengambilan frame kamera GAGAL (fb adalah NULL).");
    server.send(500, "text/plain", "Gagal mengambil gambar dari kamera!");
    // Jika resolusi diubah, kembalikan ke default di sini jika perlu
    // sensor_t * s_after_fail = esp_camera_sensor_get();
    // s_after_fail->set_framesize(s_after_fail, FRAMESIZE_VGA);
    // Serial.println("Capture: Resolusi dikembalikan ke VGA setelah gagal ambil frame.");
    return;
  }
  Serial.printf("Capture: Frame berhasil diambil. Ukuran: %u bytes, Lebar: %u, Tinggi: %u\n", fb->len, fb->width, fb->height);

  // Set header untuk memberitahu browser agar mengunduh file atau menampilkannya
  server.sendHeader("Content-Disposition", "inline; filename=capture.jpg"); // 'inline' akan coba menampilkan, 'attachment' akan langsung download

  // Kirim header HTTP dan data gambar
  server.setContentLength(fb->len);
  server.send(200, "image/jpeg", ""); // Kirim status 200 OK, tipe konten image/jpeg, dan body kosong untuk header
  Serial.println("Capture: Header HTTP terkirim. Mengirim data gambar...");
  
  unsigned long preWriteTime = millis();
  server.client().write((const char *)fb->buf, fb->len); // Kirim data gambar sebenarnya
  unsigned long postWriteTime = millis();
  Serial.printf("Capture: Data gambar terkirim ke client dalam %lu ms.\n", postWriteTime - preWriteTime);

  esp_camera_fb_return(fb); // Kembalikan frame buffer
  Serial.println("Capture: Frame buffer dikembalikan (esp_camera_fb_return).");

  // Opsional: Kembalikan resolusi ke setting awal untuk streaming jika diubah sebelumnya
  // PENTING: Jika Anda mengubah resolusi di atas, uncomment bagian ini juga.
  // sensor_t * s_after_capture = esp_camera_sensor_get();
  // s_after_capture->set_framesize(s_after_capture, FRAMESIZE_VGA);
  // delay(100);
  // Serial.println("Capture: Resolusi dikembalikan ke VGA (resolusi streaming).");

  Serial.println("Capture: Proses selesai, gambar berhasil dikirim ke client.");
}