import re
import os
from groq import Groq

# Kamus kata kasar sederhana untuk contoh (bisa diisi lebih banyak)
PROFANITY_LIST = ["fuck", "shit", "bitch", "asshole", "damn", "crap", "bastard"]

def censor_text_and_get_ranges(segments: list) -> tuple:
    """
    Menganalisis segments dari Whisper verbose_json.
    Menyensor teks kasarnya dan mengembalikan list rentang waktu audio (start, end) 
    untuk dibisukan oleh FFmpeg (Bleeping).
    Returns: (censored_segments, mute_ranges_in_seconds)
    """
    mute_ranges = []
    
    for segment in segments:
        original_text = segment.get("text", "")
        # Pisahkan kata-kata untuk dicek
        words = original_text.split()
        censored_words = []
        for word in words:
            clean_word = re.sub(r'[^a-zA-Z0-9]', '', word.lower())
            if clean_word in PROFANITY_LIST:
                # Sensor kata (misal: sh*t)
                censored_word = word[0] + "*" * (len(word) - 2) + word[-1] if len(word) > 2 else "**"
                censored_words.append(censored_word)
                
                # Asumsikan durasi kata mengambil seluruh segmen (karena whisper tak selalu sedia word-level)
                # Opsi: Jika pakai whisper word-level timestamp, kita bisa mute kata spesifik.
                # Disini kita bisukan seluruh segment yang mengandung kata kotor.
                start_t = segment.get("start", 0)
                end_t = segment.get("end", 0)
                mute_ranges.append((start_t, end_t))
            else:
                censored_words.append(word)
                
        segment["text"] = " ".join(censored_words)
        
    return segments, mute_ranges

def calculate_viral_score(hook_data: dict) -> dict:
    """
    Menghitung skor probabilitas viral pre-render menggunakan Llama 3
    dari Groq untuk memastikan kualitas klip.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    prompt = f"""
    Evaluasi potensi VIRAL dari klip video pendek (TikTok/Shorts) berikut dari skala 1-100:
    Judul: {hook_data.get('title_en', hook_data.get('title_id', ''))}
    Narasi Hook: {hook_data.get('desc_en', hook_data.get('desc_id', ''))}
    
    Kriteria Viralitas:
    1. Hook emosional
    2. Kepastian retensi penonton 3 detik pertama
    3. Relevansi/Kontroversi
    
    Return pure JSON: {{"viral_score": int_0_to_100, "reason": "alasan singkat"}}
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            response_format={"type": "json_object"}
        )
        import json
        result = json.loads(response.choices[0].message.content)
        hook_data["viral_score"] = result.get("viral_score", 50)
        hook_data["viral_reason"] = result.get("reason", "")
    except Exception as e:
        hook_data["viral_score"] = 50 # Default safe fallback
        hook_data["viral_reason"] = "Failed to calculate: " + str(e)
        
    return hook_data
