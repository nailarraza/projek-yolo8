#include "esp_camera.h"
#include <WiFi.h>
#include "soc/soc.h"          // Disable brownout problems
#include "soc/rtc_cntl_reg.h" // Disable brownout problems
#include "driver/rtc_io.h"
#include <WebServer.h>        // Library WebServer standar
#include "FS.h"               // Untuk sistem file
#include "SD_MMC.h"           // Untuk interaksi dengan Kartu SD menggunakan slot MMC

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

// Variabel untuk nomor file foto
static int image_count = 0;

// Deklarasi fungsi
void startCameraServer();
void handleCapture();
void handleStream();
void handleRoot();
void initSDCard();     // Fungsi baru untuk inisialisasi SD Card
void savePhoto(camera_fb_t * fb); // Fungsi baru untuk menyimpan foto

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
  config.frame_size = FRAMESIZE_VGA;    // Resolusi awal untuk streaming
  config.jpeg_quality = 12;             // Kualitas JPEG (0-63)
  config.fb_count = 2;                  // Gunakan 2 frame buffer
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  // Inisialisasi Kamera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Inisialisasi Kamera GAGAL dengan error 0x%x", err);
    Serial.println("Pastikan model kamera (CAMERA_MODEL_AI_THINKER) sudah benar dan semua pin terhubung dengan baik.");
    Serial.println("Coba turunkan resolusi atau periksa catu daya.");
    return;
  }
  Serial.println("Inisialisasi Kamera BERHASIL.");

  // sensor_t * s = esp_camera_sensor_get();
  // Atur parameter kamera jika perlu (lihat kode asli Anda)

  // Inisialisasi Kartu SD
  initSDCard();

  // Koneksi WiFi
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
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

void initSDCard() {
  Serial.println("Inisialisasi Kartu SD...");
  // Gunakan mode 1-bit untuk kompatibilitas yang lebih luas.
  // Jika Anda yakin slot SD Anda mendukung mode 4-bit dan pin D1-D3 terhubung dengan benar,
  // Anda bisa mencoba `SD_MMC.begin("/sdcard", false)`
  if (!SD_MMC.begin("/sdcard", true)) {
    Serial.println("Inisialisasi Kartu SD GAGAL!");
    Serial.println(" - Pastikan kartu terpasang dengan benar.");
    Serial.println(" - Pastikan kartu diformat FAT32.");
    Serial.println(" - Untuk beberapa board, pin D3 (GPIO13) mungkin digunakan oleh flash LED. Mode 1-bit lebih aman.");
    return;
  }

  uint8_t cardType = SD_MMC.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("Tidak ada Kartu SD yang terpasang.");
    return;
  }

  Serial.print("Jenis Kartu SD: ");
  if (cardType == CARD_MMC) {
    Serial.println("MMC");
  } else if (cardType == CARD_SD) {
    Serial.println("SDSC");
  } else if (cardType == CARD_SDHC) {
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
  }

  uint64_t cardSize = SD_MMC.cardSize() / (1024 * 1024);
  Serial.printf("Ukuran Kartu SD: %lluMB\n", cardSize);
  Serial.printf("Total bytes: %lluMB\n", SD_MMC.totalBytes() / (1024 * 1024));
  Serial.printf("Used bytes: %lluMB\n", SD_MMC.usedBytes() / (1024 * 1024));
  Serial.println("Inisialisasi Kartu SD BERHASIL.");
}


void startCameraServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/stream", HTTP_GET, handleStream);
  server.on("/capture", HTTP_GET, handleCapture);
  server.begin();
  Serial.println("HTTP server dimulai.");
  Serial.print("Stream: http://"); Serial.print(WiFi.localIP()); Serial.println("/stream");
  Serial.print("Capture: http://"); Serial.print(WiFi.localIP()); Serial.println("/capture");
  Serial.println("Untuk menyimpan foto ke SD Card, akses endpoint /capture.");
}

void handleRoot() {
  String html = "<html><head><title>ESP32-CAM Server</title></head><body>";
  html += "<h1>ESP32-CAM Live Server</h1>";
  html += "<p><img src='/stream' width='640' height='480'></p>";
  html += "<p><a href='/capture' target='_blank'><button>Ambil dan Simpan Gambar</button></a></p>"; // Tombol diupdate
  html += "<p>Buka <a href='/stream'>/stream</a> untuk MJPEG stream.</p>";
  html += "<p>Buka <a href='/capture'>/capture</a> untuk mengambil satu gambar (juga disimpan ke SD jika SD Card terpasang).</p>";
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
  server.sendContent(response);

  unsigned long lastFrameTime = 0;
  const int delay_per_frame = 240; // (ms)

  while (client.connected()) {
    if (millis() - lastFrameTime < delay_per_frame) {
      delay(1);
      continue;
    }
    lastFrameTime = millis();

    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Stream: Pengambilan frame kamera gagal");
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

    if (!client.connected()) {
        Serial.println("Stream: Client disconnected after sending frame.");
        break;
    }
  }
  Serial.println("Stream: Sesi streaming berakhir.");
}

void savePhoto(camera_fb_t * fb) {
    if (SD_MMC.cardType() == CARD_NONE) {
        Serial.println("Simpan Foto: Tidak ada SD Card, foto tidak disimpan.");
        return;
    }

    fs::FS &fs = SD_MMC;
    char path[32];
    // Buat nama file unik, contoh: /photo_0001.jpg
    sprintf(path, "/photo_%04d.jpg", image_count++);
    
    Serial.printf("Simpan Foto: Mencoba menyimpan ke %s\n", path);

    File file = fs.open(path, FILE_WRITE);
    if (!file) {
        Serial.printf("Simpan Foto: Gagal membuka file %s untuk ditulis\n", path);
        return;
    } else {
        size_t bytes_written = file.write(fb->buf, fb->len);
        if (bytes_written == fb->len) {
            Serial.printf("Simpan Foto: Gambar berhasil disimpan ke %s (%u bytes)\n", path, bytes_written);
        } else {
            Serial.printf("Simpan Foto: Gagal menulis semua data ke %s. Tertulis %u dari %u bytes.\n", path, bytes_written, fb->len);
        }
        file.close();
    }
}

void handleCapture() {
  Serial.println("Capture: Permintaan diterima.");
  camera_fb_t * fb = NULL;

  // (Kode untuk mengubah resolusi capture bisa ditambahkan di sini jika perlu, lihat kode asli Anda)

  Serial.println("Capture: Mencoba mengambil frame (esp_camera_fb_get)...");
  unsigned long preCaptureTime = millis();
  fb = esp_camera_fb_get();
  unsigned long postCaptureTime = millis();
  Serial.printf("Capture: esp_camera_fb_get selesai dalam %lu ms.\n", postCaptureTime - preCaptureTime);

  if (!fb) {
    Serial.println("Capture: Pengambilan frame kamera GAGAL (fb adalah NULL).");
    server.send(500, "text/plain", "Gagal mengambil gambar dari kamera!");
    // (Kode untuk mengembalikan resolusi jika diubah, lihat kode asli Anda)
    return;
  }
  Serial.printf("Capture: Frame berhasil diambil. Ukuran: %u bytes, Lebar: %u, Tinggi: %u\n", fb->len, fb->width, fb->height);

  WiFiClient client = server.client();
  if (!client.connected()) {
    Serial.println("Capture: Client disconnected before sending response.");
    esp_camera_fb_return(fb);
    return;
  }

  Serial.println("Capture: Membangun dan mengirim header HTTP...");
  String responseHeaders = "HTTP/1.1 200 OK\r\n";
  responseHeaders += "Content-Type: image/jpeg\r\n";
  responseHeaders += "Content-Length: " + String(fb->len) + "\r\n";
  responseHeaders += "Connection: close\r\n";
  responseHeaders += "\r\n";
  
  // Send headers
  size_t headers_sent_len = client.print(responseHeaders);
  if (headers_sent_len != responseHeaders.length()) {
    Serial.printf("Capture: Gagal mengirim semua header HTTP. Terkirim %u dari %u\n", headers_sent_len, responseHeaders.length());
    esp_camera_fb_return(fb);
    // Client connection might be closed by WebServer or might need explicit client.stop() here.
    // For simplicity, let WebServer handle it upon handler return.
    return;
  }
  Serial.println("Capture: Header HTTP terkirim. Mengirim data gambar ke client...");
  
  unsigned long preWriteTime = millis();
  size_t bytes_sent = client.write((const char *)fb->buf, fb->len);
  unsigned long postWriteTime = millis();

  if (bytes_sent == fb->len) {
    Serial.printf("Capture: Data gambar (%u bytes) berhasil ditulis ke client dalam %lu ms.\n", bytes_sent, postWriteTime - preWriteTime);
  } else {
    Serial.printf("Capture: PERINGATAN! Hanya %u dari %u bytes yang ditulis ke client dalam %lu ms.\n", bytes_sent, fb->len, postWriteTime - preWriteTime);
  }
  // client.flush(); // Umumnya tidak diperlukan jika 'Connection: close' digunakan dan client.write bersifat blocking.
                     // WebServer akan menutup koneksi.

  // ---- SIMPAN FOTO KE SD CARD SETELAH MENGIRIM KE CLIENT ----
  Serial.println("Capture: Mencoba menyimpan foto ke SD Card setelah mengirim ke client...");
  savePhoto(fb); // Ini terjadi setelah client menerima data

  esp_camera_fb_return(fb);
  Serial.println("Capture: Frame buffer dikembalikan (esp_camera_fb_return).");
  Serial.println("Capture: Proses selesai, gambar berhasil dikirim ke client (dan dicoba simpan ke SD).");
}
