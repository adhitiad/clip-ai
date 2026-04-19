import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_transcript_and_hooks(audio_path: str):
    # 1. Transkripsi dengan Whisper via Groq (File max 25MB, potong jika perlu)
    with open(audio_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",  # Penting: agar dapat timestamps!
        )

    # 2. Kirim transkrip ke Llama 3 untuk dicari "Hook" nya
    prompt = f"""
    Ini adalah transkrip video bola: {transcription.text}
    Berikan 3 segmen aksi paling seru berdurasi 30-60 detik.
    Output HANYA dalam bentuk array JSON dengan format:
    [{{"start_time": detik_mulai, "end_time": detik_selesai, "title": "Judul Viral", "desc": "Deskripsi + hashtag"}}]
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-70b-8192",
        response_format={"type": "json_object"},
    )

    # Kembalikan JSON siap pakai
    import json

    return json.loads(chat_completion.choices[0].message.content)
