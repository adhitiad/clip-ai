import os
import yt_dlp
import webvtt
from log import logger


def check_and_get_youtube_subs(video_url: str, lang: str = "id"):
    """
    Mencoba mengambil subtitle dari YouTube.
    Mengembalikan teks transkrip jika berhasil, atau None jika gagal.
    """
    logger.info(f"Mencari subtitle bawaan YouTube untuk bahasa: {lang}...")

    # Konfigurasi yt-dlp KHUSUS untuk menarik subtitle tanpa mengunduh video
    ydl_opts = {
        "skip_download": True,  # JANGAN unduh videonya dulu
        "writesubtitles": True,  # Ambil subtitle manual (jika ada)
        "writeautomaticsub": True,  # Ambil auto-generated subtitle (jika tidak ada manual)
        "subtitleslangs": [lang],  # Target bahasa (id = Indonesia, en = Inggris)
        "subtitlesformat": "vtt",  # Format paling mudah di-parsing
        "outtmpl": "temp/transcript_%(id)s.%(ext)s",  # Format nama file
        "quiet": True,  # Matikan log panjang yt-dlp
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_id = info.get("id")

            # yt-dlp akan menyimpan file dengan nama lang.vtt (misal: id.vtt)
            # Kita perlu mengecek apakah file tersebut benar-benar terunduh
            vtt_path = f"temp/transcript_{video_id}.{lang}.vtt"

            if os.path.exists(vtt_path):
                logger.info("Subtitle ditemukan! Memproses secara lokal...")
                return parse_vtt_to_transcript(vtt_path)
            else:
                logger.warning("Tidak ada subtitle YouTube yang tersedia.")
                return None

    except Exception as e:
        logger.error(f"Error saat mengekstrak subtitle: {e}")
        return None


def parse_vtt_to_transcript(vtt_path: str) -> str:
    """
    Mengubah file .vtt mentah menjadi string bersih berformat:
    [00:10] Teks...
    [00:15] Teks selanjutnya...
    """
    transcript_lines = []

    # Baca file VTT
    for caption in webvtt.read(vtt_path):
        # Format waktu VTT biasanya 00:01:23.450. Kita ambil HH:MM:SS saja.
        start_time = caption.start.split(".")[0]
        text = caption.text.strip().replace("\n", " ")

        # Hindari memasukkan baris kosong
        if text:
            transcript_lines.append(f"[{start_time}] {text}")

    # Hapus file .vtt setelah selesai dibaca agar folder temp/ tetap bersih
    os.remove(vtt_path)

    # Gabungkan menjadi satu string panjang yang siap dikirim ke LangChain
    return "\n".join(transcript_lines)


def download_audio_only(video_url: str) -> str:
    """
    Mengunduh file audio saja dalam format m4a/mp3 untuk dikirim ke Groq Whisper.
    """
    print("Mengunduh audio dari YouTube...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "temp/audio_%(id)s.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        # yt-dlp dengan postprocessor m4a akan mengubah ekstensi file
        return f"temp/audio_{info['id']}.m4a"


# Tambahkan fungsi ini di utils/youtube.py


def download_video_segment(
    video_url: str, start_time: int, end_time: int, output_path: str
):
    """
    Mengunduh HANYA segmen waktu yang dibutuhkan menggunakan yt-dlp & FFmpeg.
    Sangat hemat kuota dan waktu untuk video panjang.
    """
    print(f"Mengunduh segmen video dari detik ke-{start_time} hingga {end_time}...")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
        "external_downloader": "ffmpeg",
        "external_downloader_args": {
            # Memerintahkan FFmpeg untuk memotong langsung dari URL stream
            "ffmpeg_i": ["-ss", str(start_time), "-to", str(end_time)]
        },
        "quiet": True,
        "noprogress": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_path
    except Exception as e:
        print(f"Error saat mengunduh segmen video: {e}")
        return None
