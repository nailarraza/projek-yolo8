from ultralytics import YOLO
import os

# Path ke model .pt Anda
MODEL_PATH = os.path.join('models_yolo', 'best.pt') # Pastikan nama file sesuai

if __name__ == '__main__':
    if not os.path.exists(MODEL_PATH):
        print(f"Error: File model tidak ditemukan di {MODEL_PATH}")
    else:
        try:
            print(f"Mencoba memuat model dari: {MODEL_PATH}")
            model = YOLO(MODEL_PATH)
            print("Model YOLOv8 berhasil dimuat!")
            print(f"Nama kelas: {model.names}") # Ini akan menampilkan kelas dari data.yaml Anda
            # Anda bisa mencoba melakukan prediksi pada gambar sampel di sini jika mau
            # results = model.predict('path/to/sample_image.jpg')
            # results[0].show() # Menampilkan gambar dengan deteksi
        except Exception as e:
            print(f"Gagal memuat model: {e}")