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
    delay(150); // Naikkan dari 100. Coba 150 atau 200 jika masih panas.
  }
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); //disable brownout detector

  Serial.begin(115200);
  // Menurunkan frekuensi CPU dapat membantu mengurangi panas secara signifikan.
  // Frekuensi default biasanya 240MHz atau 160MHz. Coba set ke 160MHz atau bahkan 80MHz.
  // PERHATIAN: Penurunan frekuensi CPU yang terlalu drastis dapat mempengaruhi kinerja kamera.
  // Uji dengan hati-hati. Jika kamera gagal init atau stream tidak stabil, kembalikan ke default atau coba nilai yang lebih tinggi.
  // setCpuFrequencyMhz(160); // Aktifkan baris ini untuk mencoba 160MHz.
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
  config.xclk_freq_hz = 16000000; // Turunkan dari 20MHz ke 16MHz.
                                  // PENTING: Jika ESP32-CAM masih sangat panas setelah penyesuaian lain,
                                  // coba turunkan nilai ini lebih lanjut ke 10000000 (10MHz).
                                  // Ini dapat mengurangi panas secara signifikan, namun mungkin
                                  // mempengaruhi frame rate maksimum atau kompatibilitas dengan beberapa sensor.
  config.pixel_format = PIXFORMAT_JPEG; // PIXFORMAT_RGB565, PIXFORMAT_YUV422
  
  // Frame size - pilih yang sesuai, resolusi tinggi butuh PSRAM dan bisa lebih lambat
  // Untuk Kamera 5MP (seperti OV5640), gunakan FRAMESIZE_QSXGA atau resolusi tinggi lainnya.
  // Pastikan modul ESP32-CAM Anda memiliki PSRAM yang cukup.
  // Pilihan saat ini adalah XGA (1024x768).
  // config.frame_size = FRAMESIZE_QSXGA; // (2560x1920) - Resolusi sangat tinggi, menghasilkan panas signifikan.
  // config.frame_size = FRAMESIZE_UXGA; // (1600x1200) // Resolusi sebelumnya.
  // config.frame_size = FRAMESIZE_SXGA; // (1280x1024)
  // config.frame_size = FRAMESIZE_XGA;  // (1024x768) // Pilihan yang lebih seimbang untuk mengurangi panas.
  config.frame_size = FRAMESIZE_SVGA; // (800x600) // Turunkan dari XGA ke SVGA untuk mengurangi panas lebih lanjut.
  // config.frame_size = FRAMESIZE_VGA;  // (640x480)
  // config.frame_size = FRAMESIZE_CIF;  // (352x288)
  // config.frame_size = FRAMESIZE_QVGA; // (320x240)
  // Jika masih buram atau ada masalah, coba turunkan lagi ke SXGA atau XGA.
  // CATATAN: Untuk mengurangi panas secara drastis, pilih resolusi yang lebih rendah seperti SVGA atau VGA.

  config.jpeg_quality = 20; // Naikkan dari 15 ke 20 (atau bahkan 25).
                            // 0-63, angka lebih RENDAH berarti kualitas LEBIH TINGGI.
                            // Nilai 10-12 memberikan kualitas baik.
                            // Menaikkan nilai ini ke 15-20 akan MENGURANGI ukuran file JPEG
                            // dan beban pemrosesan, sehingga MEMBANTU MENGURANGI PANAS.
                            // Kualitas gambar akan sedikit menurun.
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
    if (s->id.PID == OV5640_PID) {
      Serial.println("OV5640 sensor detected.");
      // Penyesuaian untuk sensor OV5640 (5MP). Aktifkan dan sesuaikan nilai sesuai kebutuhan.
      s->set_vflip(s, 0);       // Vertikal flip: 0 = normal (tidak terbalik atas-bawah), 1 = flipped
      s->set_hmirror(s, 0);     // Horizontal mirror: 0 = normal (tidak terbalik kiri-kanan, seperti kamera belakang), 1 = mirrored (seperti kamera depan)
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
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("Camera Stream Ready! Go to: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");


  // Setup server routes
  server.on("/stream", HTTP_GET, handleStream);
  
  server.on("/", HTTP_GET, [](){
    server.send(200, "text/html", 
      "<!DOCTYPE html><html><head><title>ESP32-CAM</title></head><body>"
      "<h1>ESP32-CAM Server</h1>"
      "<p><a href='/stream'>Stream</a></p>"
      "</body></html>");
  });

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
