// Contoh Firmware ESP32-CAM untuk Streaming dan Capture
// Pastikan Anda memilih board "AI Thinker ESP32-CAM" di Arduino IDE
// dan sesuaikan model kamera jika perlu (misalnya CAMERA_MODEL_WROVER_KIT, dll.)

#include "esp_camera.h"
#include <WiFi.h>
#include "soc/soc.h"             // Disable brownout problems
#include "soc/rtc_cntl_reg.h"    // Disable brownout problems
#include "driver/rtc_io.h"
#include <WebServer.h> // Gunakan WebServer standar

// Ganti dengan kredensial WiFi Anda
const char* ssid = "Gopo Network";
const char* password = "sister23";

// Definisikan model kamera Anda
#define CAMERA_MODEL_AI_THINKER // Model paling umum

// Pin definitions for CAMERA_MODEL_AI_THINKER
#if defined(CAMERA_MODEL_AI_THINKER)
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1 // -1 = not used
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26 // SDA
  #define SIOC_GPIO_NUM     27 // SCL
  #define Y9_GPIO_NUM       35 // D7
  #define Y8_GPIO_NUM       34 // D6
  #define Y7_GPIO_NUM       39 // D5
  #define Y6_GPIO_NUM       36 // D4
  #define Y5_GPIO_NUM       21 // D3
  #define Y4_GPIO_NUM       19 // D2
  #define Y3_GPIO_NUM       18 // D1
  #define Y2_GPIO_NUM        5 // D0
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22
#else
  #error "Camera model not selected or pins not defined for selected model"
#endif

WebServer server(80);

// Handler untuk stream MJPEG
void handleStream() {
  WiFiClient client = server.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n";
  response += "\r\n";
  server.sendContent(response);

  camera_fb_t * fb = NULL;
  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      // esp_camera_fb_return(fb); // Kembalikan buffer jika error
      // break; // Hentikan loop jika gagal terus menerus
      delay(100); // Coba lagi setelah jeda singkat
      continue;
    }

    if (!client.connected()) {
      Serial.println("Client disconnected from stream");
      esp_camera_fb_return(fb);
      break;
    }
    
    client.print("--frame\r\n");
    client.print("Content-Type: image/jpeg\r\n");
    client.print("Content-Length: ");
    client.print(fb->len);
    client.print("\r\n\r\n");
    client.write(fb->buf, fb->len);
    client.print("\r\n");
    
    esp_camera_fb_return(fb); // Penting untuk melepaskan buffer frame

    if (!client.connected()) {
      Serial.println("Client disconnected during stream write");
      break;
    }
    // Tambahkan delay untuk mengurangi beban CPU dan potensi overheat, terutama pada resolusi tinggi.
    // Nilai 100 menghasilkan ~10 FPS. Nilai 150 ~6-7 FPS. Nilai 200 ~5 FPS.
    // FPS yang lebih rendah berarti lebih sedikit panas.
    // Coba nilai antara 200-250ms jika 150ms masih menghasilkan panas berlebih.
    // Untuk frame rate lebih lancar, kita kurangi delay ini.
    // Misalnya, 100ms untuk ~10 FPS, 66ms untuk ~15 FPS.
    // Perhatikan potensi peningkatan panas.
    delay(100); // Dikurangi dari 200ms untuk meningkatkan FPS. Sesuaikan jika terlalu panas.
  }
}

void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  Serial.println("Menghubungkan ke WiFi...");
  WiFi.begin(ssid, password);

  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - startTime > 20000) { // Timeout 20 detik
      Serial.println("\nWiFi gagal terhubung. Mencoba lagi dalam 10 detik...");
      // Bisa ditambahkan logika restart ESP jika gagal berkali-kali
      delay(10000);
      startTime = millis(); // Reset timeout untuk percobaan berikutnya
      // WiFi.begin(ssid, password); // Atau cukup biarkan loop utama yang memanggil lagi
    }
  }
  Serial.println("\nWiFi terhubung!");
  Serial.print("Alamat IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); //disable brownout detector

  Serial.begin(115200);
  // Menurunkan frekuensi CPU dapat membantu mengurangi panas secara signifikan.
  // Frekuensi default biasanya 240MHz atau 160MHz. Coba set ke 160MHz atau bahkan 80MHz.
  // PERHATIAN: Penurunan frekuensi CPU yang terlalu drastis dapat mempengaruhi kinerja kamera.
  // Uji dengan hati-hati. Jika kamera gagal init atau stream tidak stabil, kembalikan ke default atau coba nilai yang lebih tinggi.
  // Mengatur frekuensi CPU ke 80MHz dapat secara signifikan mengurangi panas.
  // Jika mengalami masalah stabilitas atau kinerja kamera menurun drastis setelah meningkatkan resolusi/kualitas gambar,
  // coba naikkan frekuensi CPU ke 160MHz atau bahkan 240MHz.
  // PERHATIAN: Menaikkan frekuensi CPU akan meningkatkan panas.
  // setCpuFrequencyMhz(80); // Sebelumnya 80MHz untuk pengurangan panas.
  setCpuFrequencyMhz(160); // Dinaikkan ke 160MHz untuk performa lebih baik.
                           // Opsi lain: 240MHz untuk performa maksimal, tapi panas lebih tinggi.
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
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000; // Dinaikkan ke 20MHz untuk frame rate dan kualitas gambar yang lebih baik.
                                  // Untuk kualitas gambar yang lebih baik, terutama pada resolusi tinggi,
                                  // Anda bisa mencoba menaikkan nilai ini ke 16000000 (16MHz) atau 20000000 (20MHz).
                                  // PERHATIAN: Menaikkan frekuensi XCLK dapat meningkatkan kualitas gambar dan frame rate
                                  // namun juga akan meningkatkan konsumsi daya dan panas.
                                  // Sebelumnya 10000000 (10MHz).
  config.pixel_format = PIXFORMAT_JPEG; // PIXFORMAT_RGB565, PIXFORMAT_YUV422
  
  // Frame size - pilih yang sesuai, resolusi tinggi butuh PSRAM dan bisa lebih lambat
  // Untuk Kamera 5MP (seperti OV5640), gunakan FRAMESIZE_QSXGA atau resolusi tinggi lainnya.
  // Pastikan modul ESP32-CAM Anda memiliki PSRAM yang cukup.
  // Untuk deteksi objek dengan YOLOv8, resolusi seperti 640x480 (VGA) seringkali merupakan pilihan yang baik.
  // Ini memberikan keseimbangan antara detail, kecepatan pemrosesan, dan ukuran data.
  // Model YOLOv8 sering dilatih pada input persegi (misalnya 640x640). Gambar 640x480 dapat
  // di-padding atau di-crop agar sesuai dengan input model YOLO.
  // config.frame_size = FRAMESIZE_QSXGA; // (2560x1920) - Resolusi sangat tinggi, menghasilkan panas signifikan.
  // config.frame_size = FRAMESIZE_UXGA; // (1600x1200) // Resolusi sebelumnya.
  // config.frame_size = FRAMESIZE_SXGA; // (1280x1024) // Resolusi tinggi, FPS lebih rendah.
  // config.frame_size = FRAMESIZE_SVGA; // (800x600) // Opsi jika VGA kurang detail.
   config.frame_size = FRAMESIZE_VGA; // (640x480) // Direkomendasikan untuk YOLOv8, keseimbangan panas/performa, dan FPS lebih baik.
                                     // Opsi lain: FRAMESIZE_SVGA (800x600) jika detail lebih tinggi diperlukan
                                     // dan model YOLO Anda mendukungnya.
                                     // Perhatikan potensi peningkatan panas dan penurunan FPS pada resolusi lebih tinggi.
  // config.frame_size = FRAMESIZE_CIF;  // (352x288)
  // config.frame_size = FRAMESIZE_QVGA; // (320x240)
  // CATATAN: Untuk mengurangi panas secara drastis, pilih resolusi yang lebih rendah seperti SVGA atau VGA.

  config.jpeg_quality = 20; // Kualitas JPEG. Rentang nilai: 0-63. Angka LEBIH RENDAH berarti kualitas LEBIH TINGGI.
                            // Rentang nilai: 0-63. Angka LEBIH RENDAH berarti kualitas LEBIH TINGGI dan kompresi LEBIH KECIL.
                            // Nilai 10-12 memberikan kualitas baik.
                            // PERHATIAN: Kualitas yang lebih tinggi (nilai lebih rendah) akan menghasilkan
                            // ukuran file gambar yang lebih besar dan meningkatkan beban pemrosesan,
                            // yang dapat meningkatkan panas dan menurunkan FPS.
                            // Sebelumnya: 25. Disesuaikan menjadi 15 untuk kualitas lebih baik pada resolusi VGA.
  config.fb_count = 1;      // Jika PSRAM lebih banyak, bisa > 1. Untuk stream, 1 atau 2 cukup.
  config.fb_location = CAMERA_FB_IN_PSRAM; // Gunakan PSRAM untuk frame buffer
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;


  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Dapatkan pointer ke sensor untuk penyesuaian spesifik jika diperlukan
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) { // Pastikan sensor pointer valid
    Serial.printf("Sensor PID: 0x%02x, Version: 0x%02x\n", s->id.PID, s->id.VER); // Cetak info sensor
    if (s->id.PID == OV5640_PID || s->id.PID == OV3660_PID) { // Tambahkan OV3660 jika relevan, atau sesuaikan
      Serial.printf("%s sensor detected. Applying specific settings.\n", (s->id.PID == OV5640_PID) ? "OV5640" : "OV3660");
      // Penyesuaian untuk sensor OV5640 (5MP). Aktifkan dan sesuaikan nilai sesuai kebutuhan.
      s->set_vflip(s, 0);       // Vertikal flip: 0 = normal (tidak terbalik atas-bawah), 1 = flipped
      s->set_hmirror(s, 0);     // Horizontal mirror: 0 = normal (tidak terbalik kiri-kanan, standar untuk deteksi objek), 1 = mirrored (seperti kamera depan)
                                  // Untuk YOLOv8, umumnya lebih baik menggunakan hmirror=0 (non-mirrored).
      // s->set_brightness(s, 0);  // Kecerahan: -2 (gelap) hingga 2 (terang), default 0
      // s->set_contrast(s, 0);    // Kontras: -2 hingga 2, default 0
      s->set_denoise(s, 0);     // Nonaktifkan fitur denoise internal sensor (sebelumnya 1).
                                  // Denoise bisa menambah beban pemrosesan.
                                  // Efek samping: gambar mungkin sedikit lebih noisy.
      s->set_saturation(s, 0); // Saturasi: -2 (grayscale) hingga 2 (sangat jenuh), default 0.
                                  // Coba -1 untuk mengurangi intensitas noise warna (misal ungu).
                                  // Efek samping: warna keseluruhan jadi kurang cerah/vibrant.
      
      // Pengaturan otomatis untuk kualitas gambar yang lebih baik dan stabil
      s->set_whitebal(s, 1);    // White Balance otomatis: 0 = mati, 1 = nyala (REKOMENDASI: 1)
      s->set_awb_gain(s, 1);    // Auto White Balance Gain: 0 = mati, 1 = nyala (REKOMENDASI: 1)
      // s->set_wb_mode(s, 0);     // Mode White Balance: 0 (auto), 1 (sunny), 2 (cloudy), 3 (office), 4 (home)

      s->set_exposure_ctrl(s, 1); // Aktifkan kontrol eksposur otomatis (AEC) (REKOMENDASI: 1)
      s->set_ae_level(s, 0);      // Sesuaikan target level kecerahan untuk Auto Exposure: -2 (lebih gelap) hingga 2 (lebih terang).
                                  // Default adalah 0. Jika gambar cenderung terlalu gelap, coba naikkan ke 1.
                                  // Jika terlalu terang, turunkan ke -1. Ini membantu "auto brightness".

      // s->set_aec_value(s, 300);   // Sesuaikan nilai AEC (Auto Exposure Control) jika perlu (0-1200)
      s->set_gain_ctrl(s, 1);     // Aktifkan kontrol gain otomatis (AGC) (REKOMENDASI: 1)
      // s->set_agc_gain(s, 0);      // Set AGC gain (0-30)
      s->set_gainceiling(s, GAINCEILING_8X); // Batas atas AGC gain. Sebelumnya GAINCEILING_16X.
                                             // Menurunkan gain ceiling (misal ke _8X, _4X) dapat mengurangi noise,
                                             // namun gambar akan lebih gelap di kondisi kurang cahaya.
                                             // Jika gambar terlalu gelap di kondisi minim cahaya dan Anda bisa mentolerir sedikit noise,
                                             // Anda bisa menaikkan ini ke GAINCEILING_16X.
    } else {
      Serial.printf("Sensor is NOT OV5640 (PID: 0x%x). No OV5640-specific settings applied.\n", s->id.PID);
    }
  }
  // drop down frame size for higher initial frame rate
  // s->set_framesize(s, FRAMESIZE_QVGA);


  // WiFi connection
  WiFi.mode(WIFI_STA); // Set mode WiFi ke Station
  WiFi.setAutoReconnect(true); // Aktifkan fitur auto-reconnect bawaan ESP32

  connectToWiFi(); // Panggil fungsi untuk koneksi awal

  // Loop tambahan untuk memastikan koneksi awal berhasil sebelum melanjutkan setup server
  // Ini penting agar server tidak dimulai jika WiFi belum siap.
  unsigned long initialWifiConnectTimeout = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - initialWifiConnectTimeout > 30000) { // Timeout 30 detik untuk koneksi awal
      Serial.println("\nTidak dapat terhubung ke WiFi setelah 30 detik. Periksa kredensial atau jaringan. Restart dalam 10 detik...");
      delay(10000);
      ESP.restart();
    }
  }

  Serial.print("\nCamera Stream Siap! Akses: http://");
  Serial.println(WiFi.localIP());

  // Setup rute server
  server.on("/stream", HTTP_GET, handleStream);
  
  server.on("/", HTTP_GET, [](){
    server.send(200, "text/html", 
      "<!DOCTYPE html><html><head><title>ESP32-CAM</title></head><body>"
      "<h1>ESP32-CAM Server</h1>"
      "<p><a href='/stream'>Stream MJPEG</a></p>"
      "<p><a href='/capture'>Capture Single JPEG</a></p>" // Link ke endpoint capture baru
      "</body></html>");
  });

  // Rute baru untuk mengambil satu gambar JPEG
  server.on("/capture", HTTP_GET, handleCapture);

  server.begin();
  Serial.println("HTTP server started");
  Serial.println("Akses /stream untuk MJPEG video stream.");
  Serial.println("Akses /capture untuk mengambil satu gambar JPEG.");
}

// Handler untuk capture satu frame JPEG
void handleCapture() {
  camera_fb_t * fb = NULL;
  
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Gagal mengambil gambar dari kamera");
    server.send(500, "text/plain", "Gagal mengambil gambar");
    return;
  }

  server.setContentLength(fb->len);
  server.sendHeader("Content-Disposition", "inline; filename=capture.jpg"); // Opsional: menyarankan nama file saat diunduh
  server.send(200, "image/jpeg", ""); // Kirim header HTTP
  WiFiClient client = server.client(); // Dapatkan objek client setelah send() atau sendHeader()
  client.write(fb->buf, fb->len); // Kirim data gambar
  
  esp_camera_fb_return(fb); // Kembalikan buffer frame agar memori bisa digunakan lagi
}

void loop() {
  // Cek status koneksi WiFi secara berkala
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Koneksi WiFi terputus. Mencoba menghubungkan kembali...");
    // WiFi.disconnect(true); // Opsional: putuskan koneksi lama sebelum mencoba lagi
    // delay(100);
    WiFi.begin(ssid, password); // Coba hubungkan kembali
    unsigned long reconnectAttemptTime = millis();
    while(WiFi.status() != WL_CONNECTED && millis() - reconnectAttemptTime < 15000) { // Coba selama 15 detik
        delay(500);
        Serial.print(".");
    }
    if(WiFi.status() == WL_CONNECTED) {
        Serial.println("\nBerhasil terhubung kembali ke WiFi.");
        Serial.print("Alamat IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nGagal terhubung kembali ke WiFi. Akan dicoba lagi nanti.");
    }
  }
  server.handleClient();
}
