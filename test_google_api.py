import google.generativeai as genai
import os
from dotenv import load_dotenv

# Muat variabel dari .env
load_dotenv()

API_KEY = os.getenv('GOOGLE_API_KEY')

if not API_KEY:
    print("Error: GOOGLE_API_KEY tidak ditemukan di file .env atau environment.")
else:
    try:
        genai.configure(api_key=API_KEY)
        # Coba list model untuk memverifikasi koneksi dan API key
        print("Mencoba mengambil daftar model dari Google Generative AI...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model yang tersedia: {m.name}")
        print("\nKoneksi ke Google Generative AI berhasil dan API Key valid!")
        # Pilih model yang sesuai, misalnya 'gemini-1.5-flash' atau 'gemini-pro'
        # model = genai.GenerativeModel('gemini-1.5-flash-latest') # atau 'gemini-pro'
        # response = model.generate_content("Sebutkan satu fakta menarik tentang Indonesia.")
        # print(f"\nContoh respons dari model: {response.text}")

    except Exception as e:
        print(f"Terjadi kesalahan saat mencoba terhubung ke Google Generative AI: {e}")
        print("Pastikan API Key Anda benar dan layanan Generative AI API diaktifkan untuk proyek Anda di Google Cloud Console.")