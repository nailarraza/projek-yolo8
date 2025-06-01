# Lokasi file: D:/projek-yolo8/app/utils.py

from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from flask import current_app, jsonify # Tambahkan jsonify
import os
import requests
from io import BytesIO
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabel global untuk model agar tidak di-load setiap kali request
yolo_model = None

def load_yolo_model():
    """Memuat model YOLOv8 dari path yang dikonfigurasi."""
    global yolo_model
    if yolo_model is None:
        model_path = current_app.config['MODEL_PATH']
        if not os.path.exists(model_path):
            logger.error(f"File model tidak ditemukan di: {model_path}")
            raise FileNotFoundError(f"Model YOLO tidak ditemukan di {model_path}")
        try:
            yolo_model = YOLO(model_path)
            logger.info(f"Model YOLO berhasil dimuat dari: {model_path}")
        except Exception as e:
            logger.error(f"Error saat memuat model YOLO: {e}")
            raise e
    return yolo_model

def perform_detection(image_pil, model):
    """
    Melakukan deteksi objek pada gambar PIL menggunakan model YOLO.
    :param image_pil: Objek PIL Image.
    :param model: Model YOLO yang sudah dimuat.
    :return: Hasil deteksi dari YOLO.
    """
    try:
        results = model(image_pil, verbose=False) # verbose=False agar tidak banyak print dari yolo
        logger.info("Deteksi YOLO berhasil dilakukan.")
        return results
    except Exception as e:
        logger.error(f"Error saat melakukan deteksi YOLO: {e}")
        raise e

def draw_bounding_boxes(image_pil, results, output_path, class_names=None):
    """
    Menggambar bounding box pada gambar berdasarkan hasil deteksi YOLO.
    Menyimpan gambar hasil ke output_path.
    :param image_pil: Objek PIL Image asli.
    :param results: Hasil deteksi dari YOLO (objek Results dari ultralytics).
    :param output_path: Path untuk menyimpan gambar dengan bounding box.
    :param class_names: List atau dict nama kelas (opsional, jika model tidak menyediakannya).
    :return: Path ke gambar yang sudah digambar bounding boxnya dan informasi deteksi utama.
    """
    if not results or not results[0].boxes:
        logger.info("Tidak ada objek terdeteksi.")
        image_pil.save(output_path) # Simpan gambar asli jika tidak ada deteksi
        return output_path, None, None # path, kelas, skor

    draw = ImageDraw.Draw(image_pil)
    
    # Coba dapatkan font, jika gagal gunakan default
    try:
        font = ImageFont.truetype("arial.ttf", 20) # Anda mungkin perlu path font yang benar atau font lain
    except IOError:
        font = ImageFont.load_default()
        logger.warning("Font arial.ttf tidak ditemukan, menggunakan font default.")

    # Asumsi kita mengambil deteksi dengan confidence tertinggi sebagai hasil utama
    # atau deteksi pertama jika hanya ada satu.
    # Anda mungkin perlu logika lebih kompleks jika ada banyak objek.
    
    best_detection = None # Untuk menyimpan informasi deteksi utama
    highest_confidence = 0.0

    for result in results: # Iterasi melalui batch hasil (biasanya hanya 1 jika input 1 gambar)
        for box in result.boxes:
            xyxy = box.xyxy[0].tolist()  # Koordinat bounding box [x1, y1, x2, y2]
            conf = box.conf[0].item()    # Skor kepercayaan
            cls_id = int(box.cls[0].item()) # ID kelas

            # Dapatkan nama kelas
            current_class_name = "Unknown"
            if result.names: # Jika model memiliki nama kelas internal
                current_class_name = result.names[cls_id]
            elif class_names and cls_id < len(class_names): # Jika kita menyediakan daftar nama kelas
                current_class_name = class_names[cls_id]
            
            label = f"{current_class_name}: {conf:.2f}"

            # Warna bounding box (misalnya, merah)
            box_color = "red"
            if current_class_name.lower() == "oli baik": # Contoh pewarnaan berbeda
                box_color = "green"
            elif current_class_name.lower() == "oli perlu diganti":
                box_color = "orange"

            draw.rectangle(xyxy, outline=box_color, width=3)
            
            # Hitung posisi teks agar tidak keluar gambar
            text_x, text_y = int(xyxy[0]), int(xyxy[1]) - 25
            if text_y < 0: # Jika teks akan keluar di atas, letakkan di bawah box
                text_y = int(xyxy[3]) + 5
            
            # Latar belakang untuk teks agar lebih mudah dibaca
            text_bbox = draw.textbbox((text_x, text_y), label, font=font)
            draw.rectangle(text_bbox, fill=box_color)
            draw.text((text_x, text_y), label, fill="white", font=font)

            logger.info(f"Objek terdeteksi: {label} di {xyxy}")

            if conf > highest_confidence:
                highest_confidence = conf
                best_detection = {
                    "class_name": current_class_name,
                    "confidence": conf,
                    "box": xyxy
                }
    
    try:
        image_pil.save(output_path)
        logger.info(f"Gambar dengan bounding box disimpan di: {output_path}")
    except Exception as e:
        logger.error(f"Gagal menyimpan gambar dengan bounding box: {e}")
        raise e

    if best_detection:
        return output_path, best_detection["class_name"], best_detection["confidence"]
    return output_path, None, None


def get_gemini_description(detection_class, confidence_score):
    """
    Menghasilkan deskripsi generatif menggunakan Google Gemini API.
    :param detection_class: Kelas yang terdeteksi (misalnya, "Oli Baik").
    :param confidence_score: Skor kepercayaan deteksi.
    :return: String deskripsi generatif atau None jika error.
    """
    api_key = current_app.config.get('GOOGLE_GEMINI_API_KEY')
    if not api_key:
        logger.error("GOOGLE_GEMINI_API_KEY tidak ditemukan dalam konfigurasi.")
        return "Deskripsi tidak tersedia (API Key tidak dikonfigurasi)."

    try:
        genai.configure(api_key=api_key)
        
        # Pemilihan model Gemini
        # Untuk tugas teks sederhana, 'gemini-pro' atau 'gemini-1.0-pro' biasanya cukup.
        # Jika Anda memerlukan kemampuan multimodal (teks+gambar), modelnya berbeda (mis. 'gemini-pro-vision')
        # tapi untuk deskripsi berdasarkan kelas & skor, model teks sudah cukup.
        # Pastikan model yang Anda pilih tersedia dan sesuai dengan API key Anda.
        # Untuk daftar model: for m in genai.list_models(): print(m.name)
        
        # Menggunakan model gemini-2.0-flash seperti instruksi
        model_name = "gemini-2.0-flash" # atau "models/gemini-1.0-pro" atau "models/gemini-pro"
        
        # Cek apakah model ada
        # available_models = [m.name for m in genai.list_models()]
        # if model_name not in available_models and f"models/{model_name}" not in available_models:
        #     logger.warning(f"Model Gemini '{model_name}' mungkin tidak tersedia. Menggunakan 'gemini-1.0-pro' sebagai fallback.")
        #     model_name = "models/gemini-1.0-pro" # Fallback jika gemini-2.0-flash tidak ada

        model = genai.GenerativeModel(model_name)

        if detection_class and confidence_score is not None:
            prompt = (
                f"Anda adalah seorang ahli mesin otomotif. Berikan deskripsi singkat dan saran terkait kualitas oli motor "
                f"berdasarkan hasil deteksi berikut:\n"
                f"Kelas Kualitas Oli: {detection_class}\n"
                f"Tingkat Kepercayaan Deteksi: {confidence_score*100:.2f}%\n\n"
                f"Deskripsi harus informatif, mudah dipahami oleh pengguna awam, dan memberikan rekomendasi tindakan jika perlu. "
                f"Gunakan bahasa Indonesia yang baik dan benar. Panjang deskripsi sekitar 2-3 kalimat."
            )
        else:
            prompt = (
                "Anda adalah seorang ahli mesin otomotif. Sistem deteksi kualitas oli tidak menemukan hasil yang jelas. "
                "Berikan saran umum kepada pengguna tentang cara memeriksa kualitas oli secara manual atau kapan sebaiknya oli diganti. "
                "Gunakan bahasa Indonesia yang baik dan benar. Panjang deskripsi sekitar 2-3 kalimat."
            )

        logger.info(f"Mengirim prompt ke Gemini: {prompt}")
        
        # Menggunakan generateContent sesuai instruksi baru
        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}
        
        # API URL dari instruksi (menggunakan v1beta)
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status() # Akan raise error jika status HTTP bukan 2xx
        
        result_json = response.json()
        
        if (result_json.get('candidates') and 
            result_json['candidates'][0].get('content') and
            result_json['candidates'][0]['content'].get('parts') and
            result_json['candidates'][0]['content']['parts'][0].get('text')):
            
            description = result_json['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Deskripsi dari Gemini diterima: {description}")
            return description.strip()
        else:
            logger.error(f"Struktur respons Gemini tidak sesuai harapan: {result_json}")
            return "Deskripsi generatif tidak dapat dibuat saat ini (respons API tidak valid)."

    except requests.exceptions.RequestException as e:
        logger.error(f"Error koneksi saat menghubungi Gemini API: {e}")
        if e.response is not None:
            logger.error(f"Detail error Gemini API (RequestException): {e.response.text}")
        return f"Deskripsi generatif tidak dapat dibuat (error koneksi: {e})."
    except Exception as e:
        logger.error(f"Error saat menghasilkan deskripsi Gemini: {e}")
        # Coba log detail error jika ada dari API
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Detail error Gemini API: {e.response.text}")
        return f"Deskripsi generatif tidak dapat dibuat (error: {e})."


def capture_image_from_esp32():
    """Mengambil gambar dari ESP32-CAM."""
    capture_url = current_app.config.get('ESP32_CAM_CAPTURE_URL')
    if not capture_url:
        logger.error("URL capture ESP32-CAM tidak dikonfigurasi.")
        return None
    
    try:
        # Tambahkan timeout untuk menghindari hanging jika ESP32 tidak responsif
        response = requests.get(capture_url, timeout=10) # Timeout 10 detik
        response.raise_for_status()  # Akan raise error jika status HTTP bukan 2xx
        
        # Cek content type, pastikan itu gambar
        if 'image/jpeg' not in response.headers.get('Content-Type', '').lower():
            logger.error(f"Respons dari ESP32 bukan JPEG. Content-Type: {response.headers.get('Content-Type')}")
            return None

        image_bytes = response.content
        image_pil = Image.open(BytesIO(image_bytes))
        logger.info("Gambar berhasil diambil dari ESP32-CAM.")
        return image_pil
    except requests.exceptions.Timeout:
        logger.error(f"Timeout saat mencoba mengambil gambar dari ESP32-CAM di {capture_url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat mengambil gambar dari ESP32-CAM: {e}")
        return None
    except Exception as e:
        logger.error(f"Error tidak terduga saat memproses gambar dari ESP32: {e}")
        return None

