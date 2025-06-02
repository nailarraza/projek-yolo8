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
// Anda HARUS menyesuaikan pin-pin ini.
#define CAMERA_MODEL_AI_THINKER
//#define CAMERA_MODEL_M5STACK_PSRAM
//#define CAMERA_MODEL_M5STACK_V2_PSRAM
//#define CAMERA_MODEL_M5STACK_WIDE
//#define CAMERA_MODEL_M5STACK_ESP32CAM
//#define CAMERA_MODEL_WROVER_KIT

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
  #error "Camera model not selected"
#endif

// ===========================================
//      Pengaturan WiFi
// ===========================================
const char* ssid = "NAMA_WIFI_ANDA";         // Ganti dengan nama WiFi Anda
const char* password = "PASSWORD_WIFI_ANDA"; // Ganti dengan password WiFi Anda

// ===========================================
//      Pengaturan Web Server
// ===========================================
WebServer server(80); // Server akan berjalan di port 80 (HTTP)
// Untuk stream, kita bisa menggunakan port berbeda jika port 80 sudah dipakai atau diblokir
// WebServer streamServer(81); // Contoh jika ingin stream di port 81

// LED Flash (jika ada dan ingin dikontrol)
// Biasanya GPIO 4 untuk AI-Thinker
#define FLASH_GPIO_NUM 4
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
    config.frame_size = FRAMESIZE_UXGA; // UXGA=1600x1200. Untuk OV5640 bisa lebih tinggi (QSXGA 2592x1944)
                                        // Namun, UXGA sudah cukup besar dan mungkin lebih stabil untuk streaming.
                                        // Coba juga: FRAMESIZE_SXGA (1280x1024), FRAMESIZE_XGA (1024x768)
                                        // Untuk 5MP (OV5640), Anda mungkin perlu bereksperimen dengan FRAMESIZE_QSXGA
                                        // jika memori dan stabilitas memungkinkan. Mulai dengan UXGA atau SXGA dulu.
    config.jpeg_quality = 10; // 0-63, lebih rendah = kualitas lebih tinggi, tapi ukuran lebih besar. 10-12 adalah kompromi yang baik.
    config.fb_count = 2;      // Gunakan 2 frame buffer jika PSRAM ada, atau 1 jika tidak.
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
  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, flashState);

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
    // Halaman index sederhana
    server.send(200, "text/html", 
      "<!DOCTYPE html><html><head><title>ESP32-CAM Server</title></head><body>"
      "<h1>Server Kamera ESP32-CAM</h1>"
      "<p><a href='/capture'>Ambil Foto (Capture)</a></p>"
      "<p><a href='/stream'>Mulai Streaming Video</a></p>"
      "<p>Status LED Flash: <span id='flashStatus'>MATI</span> <button onclick='toggleFlash()'>Toggle Flash</button></p>"
      "<img src='/stream' width='640' height='480'>" // Embed stream langsung
      "<script>"
      "function toggleFlash(){fetch('/toggle-flash').then(res => res.text()).then(data => {document.getElementById('flashStatus').innerText = data;});}"
      "setInterval(function(){fetch('/flash-status').then(res => res.text()).then(data => {document.getElementById('flashStatus').innerText = data;});},1000);"
      "</script>"
      "</body></html>");
  });

  server.on("/capture", HTTP_GET, handleJpg);
  server.on("/stream", HTTP_GET, handleJpgStream);
  
  // Endpoint untuk mengontrol flash
  server.on("/toggle-flash", HTTP_GET, [](){
    flashState = !flashState;
    digitalWrite(FLASH_GPIO_NUM, flashState);
    server.send(200, "text/plain", flashState ? "NYALA" : "MATI");
  });
  server.on("/flash-status", HTTP_GET, [](){
    server.send(200, "text/plain", flashState ? "NYALA" : "MATI");
  });

  server.onNotFound(handleNotFound);
  server.begin();
}

// Handler untuk mengambil satu frame foto (JPEG)
void handleJpg(){
  WiFiClient client = server.client();

  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;

  // Ambil frame dari kamera
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Pengambilan frame kamera gagal");
    server.send(500, "text/plain", "Gagal mengambil frame dari kamera.");
    return;
  }
  Serial.printf("Frame diambil! Format: %d, Ukuran: %d, Lebar: %d, Tinggi: %d\n", fb->format, fb->len, fb->width, fb->height);


  // Kirim header HTTP
  if(res == ESP_OK){
    res = client.write("HTTP/1.1 200 OK\r\n") ? ESP_OK : ESP_FAIL;
  }
  if(res == ESP_OK){
    res = client.write("Content-Type: image/jpeg\r\n") ? ESP_OK : ESP_FAIL;
  }
  if(res == ESP_OK){
    res = client.write("Content-Disposition: inline; filename=capture.jpg\r\n") ? ESP_OK : ESP_FAIL;
  }
  if(res == ESP_OK){
    char len_str[16];
    sprintf(len_str, "%d", fb->len);
    res = client.write("Content-Length: ") ? ESP_OK : ESP_FAIL;
    res = client.write(len_str) ? ESP_OK : ESP_FAIL;
    res = client.write("\r\n") ? ESP_OK : ESP_FAIL;
  }
  if(res == ESP_OK){
    res = client.write("\r\n") ? ESP_OK : ESP_FAIL;
  }
  
  // Kirim data gambar JPEG
  if(res == ESP_OK){
    res = client.write(fb->buf, fb->len) ? ESP_OK : ESP_FAIL;
  }

  // Kembalikan frame buffer ke kamera agar bisa digunakan lagi
  esp_camera_fb_return(fb);

  if(res != ESP_OK){
    Serial.println("Gagal mengirim response gambar.");
    // Tidak bisa send 500 di sini karena header mungkin sudah terkirim sebagian
  }
  // Koneksi akan ditutup oleh client atau WebServer class
}


// Handler untuk streaming video (MJPEG)
void handleJpgStream(){
  WiFiClient client = server.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n";
  response += "\r\n";
  
  // Kirim header awal untuk stream MJPEG
  if (client.write((const uint8_t*)response.c_str(), response.length()) != response.length()) {
    Serial.println("Gagal mengirim header stream");
    return;
  }
  Serial.println("Memulai stream MJPEG...");

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
      delay(100); // Beri jeda sedikit sebelum mencoba lagi
      continue;
    }

    // Kirim boundary dan header untuk frame JPEG ini
    response = "--frame\r\n";
    response += "Content-Type: image/jpeg\r\n";
    response += "Content-Length: " + String(fb->len) + "\r\n";
    response += "\r\n";
    
    if (client.write((const uint8_t*)response.c_str(), response.length()) != response.length()) {
      Serial.println("Gagal mengirim header frame JPEG");
      esp_camera_fb_return(fb); // Jangan lupa return buffer
      break; // Keluar dari loop jika client disconnect atau error
    }

    // Kirim data gambar JPEG
    if (client.write(fb->buf, fb->len) != fb->len) {
      Serial.println("Gagal mengirim data frame JPEG");
      esp_camera_fb_return(fb);
      break; 
    }
    
    // Kirim CRLF setelah data gambar
     if (client.write((const uint8_t*)"\r\n", 2) != 2) {
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
    
    delay(10); // Sedikit delay untuk stabilitas, bisa disesuaikan
               // Terlalu kecil bisa membebani ESP32, terlalu besar membuat stream patah-patah
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
