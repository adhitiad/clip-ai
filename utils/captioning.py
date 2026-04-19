import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt_from_audio(audio_path: str, srt_output_path: str):
    """
    Mengirim audio ke Groq Whisper untuk mendapatkan segmen dg timestamp,
    lalu mengubahnya menjadi format .srt standar.
    """
    with open(audio_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )
    
    # Kadang response berbentuk JSON string jika via Groq SDK, mari parse
    data = transcription
    if isinstance(data, str):
        data = json.loads(data)
    elif hasattr(data, 'model_dump'):
        data = data.model_dump()
        
    segments = data.get("segments", [])
    
    from utils.ai_extras import censor_text_and_get_ranges
    segments, mute_ranges = censor_text_and_get_ranges(segments)
    
    with open(srt_output_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            # Abaikan jika segment kosong
            if not text:
                continue
                
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{text}\n\n")
    
    return srt_output_path, mute_ranges
