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

// Handler untuk streaming (asumsi sudah ada dan berfungsi)
// void handleStream(); // Anda mungkin sudah punya implementasi ini

// Handler untuk mengambil foto berkualitas tinggi
void handleCapture() {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;

  // Atur sensor untuk kualitas terbaik sebelum capture (opsional, bisa di-tuning)
  // sensor_t * s = esp_camera_sensor_get();
  // s->set_framesize(s, FRAMESIZE_UXGA); // Contoh: UXGA (1600x1200)
  // s->set_quality(s, 10); // Kualitas JPEG (0-63, lower is higher quality)

  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    server.send(500, "text/plain", "Failed to capture image");
    return;
  }

  server.setContentLength(fb->len);
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Access-Control-Allow-Origin", "*"); // Izinkan CORS jika Flask di domain/port berbeda
  WiFiClient client = server.client();
  client.write(fb->buf, fb->len);

  esp_camera_fb_return(fb); // Kembalikan frame buffer

  // Kembalikan sensor ke pengaturan streaming jika diubah
  // s->set_framesize(s, FRAMESIZE_QVGA); // Sesuaikan dengan setting stream Anda
  // s->set_quality(s, 12);
}


void startCameraServer() {
  // Endpoint untuk capture foto
  server.on("/capture_image", HTTP_GET, handleCapture);

  // Endpoint untuk streaming (contoh, Anda mungkin punya yang lebih kompleks)
  // server.on("/stream", HTTP_GET, handleStream); // Aktifkan jika Anda punya handler stream

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

  // Frame size untuk capture awal, bisa diubah nanti
  // Jika RAM terbatas, mulai dengan ukuran lebih kecil
  // Untuk kualitas terbaik, gunakan UXGA, SXGA, XGA, SVGA
  // Untuk streaming, biasanya lebih kecil seperti QVGA, CIF, VGA
  if (psramFound()) {
    config.frame_size = FRAMESIZE_UXGA; // (1600x1200)
    config.jpeg_quality = 10; //0-63 lower number means higher quality
    config.fb_count = 2; // Gunakan 2 frame buffer jika ada PSRAM
  } else {
    config.frame_size = FRAMESIZE_SVGA; // (800x600)
    config.jpeg_quality = 12;
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
