// Lokasi file: D:/projek-yolo8/esp32_code/esp32_cam_capture.ino

#include "esp_camera.h"
#include "WiFi.h"
#include "ESPAsyncWebServer.h"
#include "soc/soc.h"             // Untuk mengatasi brownout detector
#include "soc/rtc_cntl_reg.h"    // Untuk mengatasi brownout detector
#include "driver/rtc_io.h"
#include <StringArray.h> // Mungkin tidak diperlukan, tergantung versi ESPAsyncWebServer

// Ganti dengan kredensial WiFi Anda
const char* ssid = "NAMA_WIFI_ANDA";
const char* password = "PASSWORD_WIFI_ANDA";

// Definisi Pin untuk Modul Kamera AI-THINKER
// Pastikan ini sesuai dengan modul ESP32-CAM Anda.
// Untuk modul lain, pin mungkin berbeda.
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1 // -1 jika tidak digunakan
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

AsyncWebServer server(80); // Web server berjalan di port 80

void setup_camera() {
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
    config.pixel_format = PIXFORMAT_JPEG; // Format output JPEG

    // Pengaturan Kualitas Gambar
    // Untuk kamera 5MP (misalnya OV5640), Anda mungkin perlu FRAMESIZE yang lebih besar.
    // Untuk OV2640 (2MP) yang umum di ESP32-CAM AI Thinker:
    // FRAMESIZE_UXGA (1600x1200) untuk kualitas tertinggi foto
    // FRAMESIZE_SVGA (800x600) atau FRAMESIZE_VGA (640x480) untuk streaming yang lebih lancar
    
    // Pilih resolusi awal. Bisa diubah nanti.
    // Jika Anda memiliki kamera 5MP dan library mendukungnya, Anda bisa coba FRAMESIZE_QSXGA (2560x1920)
    // atau sejenisnya, tapi pastikan ESP32 mampu menanganinya.
    // Untuk proyek ini, kualitas baik untuk deteksi penting.
    config.frame_size = FRAMESIZE_UXGA; // (1600x1200) Kualitas tinggi untuk deteksi
    config.jpeg_quality = 10; // Kualitas JPEG (0-63), semakin rendah semakin tinggi kualitasnya
    config.fb_count = 2; // Jumlah frame buffer. Jika > 1, bisa untuk streaming. Untuk foto, 1 atau 2 cukup.
    // Jika menggunakan PSRAM, fb_location bisa diatur ke CAMERA_FB_IN_PSRAM
    // Jika tidak, CAMERA_FB_IN_DRAM
    #if CONFIG_IDF_TARGET_ESP32S3
        config.fb_location = CAMERA_FB_IN_PSRAM; // Untuk ESP32-S3
        config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    #else
        config.fb_location = CAMERA_FB_IN_DRAM; // Untuk ESP32 standar
        config.grab_mode = CAMERA_GRAB_LATEST;
    #endif


    // Inisialisasi kamera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Inisialisasi kamera gagal dengan error 0x%x\n", err);
        // Coba restart ESP jika gagal
        ESP.restart();
        return;
    }
    Serial.println("Inisialisasi kamera berhasil.");

    // Pengaturan tambahan untuk sensor kamera (opsional, bisa disesuaikan)
    sensor_t * s = esp_camera_sensor_get();
    if (s->id.PID == OV3660_PID) { // Contoh jika sensor OV3660 terdeteksi
        s->set_vflip(s, 1); // flip it on content creators camera
        s->set_brightness(s, 1); // up the brightness just a bit
        s->set_saturation(s, -2); // lower the saturation
    }
    // Untuk OV2640 atau OV5640, Anda bisa menambahkan pengaturan spesifik di sini jika perlu
    // s->set_framesize(s, FRAMESIZE_UXGA); // Atur resolusi lagi jika perlu
}

void setup() {
    // Nonaktifkan brownout detector untuk stabilitas pada beberapa modul ESP32-CAM
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 

    Serial.begin(115200);
    Serial.println("Booting ESP32-CAM...");

    // Koneksi ke WiFi
    WiFi.begin(ssid, password);
    Serial.print("Menghubungkan ke WiFi: ");
    Serial.println(ssid);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nKoneksi WiFi berhasil!");
    Serial.print("Alamat IP ESP32-CAM: ");
    Serial.println(WiFi.localIP());

    // Inisialisasi kamera
    setup_camera();

    // Handler untuk mengambil foto
    server.on("/capture", HTTP_GET, [](AsyncWebServerRequest *request){
        camera_fb_t * fb = NULL;
        esp_err_t res = ESP_OK;
        
        fb = esp_camera_fb_get(); // Ambil frame dari buffer kamera
        if (!fb) {
            Serial.println("Gagal mengambil frame dari kamera");
            request->send(500, "text/plain", "Gagal mengambil frame");
            return;
        }

        // Kirim gambar sebagai respons HTTP
        request->send_P(200, "image/jpeg", (const uint8_t *)fb->buf, fb->len);
        
        esp_camera_fb_return(fb); // Kembalikan frame buffer agar bisa digunakan lagi
        Serial.println("Foto berhasil diambil dan dikirim.");
    });

    // Handler untuk streaming video
    server.on("/stream", HTTP_GET, [](AsyncWebServerRequest *request){
        // Set resolusi yang lebih kecil untuk streaming agar lebih lancar
        sensor_t * s = esp_camera_sensor_get();
        s->set_framesize(s, FRAMESIZE_VGA); // 640x480, atau CIF (352x288) untuk lebih cepat

        AsyncWebServerResponse *response = request->beginResponseStream("multipart/x-mixed-replace;boundary=frame");
        response->addHeader("Access-Control-Allow-Origin", "*"); // Izinkan akses dari domain lain (opsional)
        
        camera_fb_t * fb = NULL;
        while(true){
            fb = esp_camera_fb_get();
            if (!fb) {
                Serial.println("Gagal mengambil frame untuk stream");
                // Mungkin koneksi terputus, hentikan loop
                break; 
            }
            
            if(!response->write( (const uint8_t *)fb->buf, fb->len)){
                 Serial.println("Gagal mengirim frame stream");
                 esp_camera_fb_return(fb);
                 break; // Hentikan jika gagal mengirim
            }
            esp_camera_fb_return(fb);

            // Cek apakah client masih terhubung
            if(!request->client()->connected()){
                Serial.println("Client stream terputus.");
                break;
            }
            delay(66); // Delay kecil untuk frame rate sekitar 15 FPS (1000ms / 15fps ~ 66ms)
                       // Sesuaikan delay ini untuk frame rate yang diinginkan dan kemampuan ESP32
        }
        // Setelah loop selesai (misalnya client disconnect), kirim respons akhir
        request->send(response); 
        
        // Kembalikan resolusi ke default untuk capture jika perlu
        s->set_framesize(s, FRAMESIZE_UXGA); 
    });

    // Mulai server
    server.begin();
    Serial.println("HTTP server dimulai. Buka IP di browser untuk testing.");
    Serial.println("Endpoint capture: /capture");
    Serial.println("Endpoint stream: /stream");
}

void loop() {
    // Tidak ada yang perlu dilakukan di loop utama karena server berjalan secara asynchronous
    delay(1000); // Delay kecil agar tidak membebani CPU jika ada proses lain
}