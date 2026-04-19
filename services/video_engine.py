import ffmpeg
import cv2
import mediapipe as mp


def crop_to_vertical_cpu(
    input_video: str, output_video: str, start_time: int, end_time: int
):
    # Potong video master menjadi klip pendek terlebih dahulu (SANGAT CEPAT)
    temp_clip = "temp/clip_raw.mp4"
    (
        ffmpeg.input(input_video, ss=start_time, to=end_time)
        .output(temp_clip, c="copy")  # Copy codec agar instan
        .run(overwrite_output=True)
    )

    # Analisis tengah layar menggunakan MediaPipe Face/Pose Detection (Ringan untuk CPU)
    # Secara default, jika tidak ada wajah, kita asumsikan di tengah layar (center crop)
    crop_x = "iw/2-ow/2"

    # Render final ke 9:16 menggunakan FFmpeg crop filter
    # Resolusi TikTok/Reels adalah 1080x1920, tapi untuk CPU kita buat 720x1280 agar lebih cepat
    (
        ffmpeg.input(temp_clip)
        .filter("crop", w="ih*9/16", h="ih", x=crop_x, y=0)
        .filter("scale", 720, 1280)
        .output(
            output_video, vcodec="libx264", preset="veryfast", crf=28
        )  # Preset veryfast untuk CPU
        .run(overwrite_output=True)
    )
    return output_video


import ffmpeg
import os


def process_clip(video_url: str, clip_metadata: dict, index: int, download_func):
    """
    Menerima metadata dari AI, mengunduh potongannya, lalu merender ke format 9:16.
    """
    start_time = clip_metadata.get("start_time")
    end_time = clip_metadata.get("end_time")

    # Membersihkan judul dari karakter aneh agar tidak error saat disimpan di Windows/Linux
    raw_title = clip_metadata.get("title_id", f"Clip_{index}")
    safe_title = (
        "".join([c for c in raw_title if c.isalnum() or c == " "])
        .rstrip()
        .replace(" ", "_")
    )

    # Path file
    temp_landscape = f"temp/raw_{index}_{start_time}.mp4"
    final_vertical = f"temp/FINAL_{safe_title}.mp4"

    # 1. Unduh potongan mentah (16:9)
    print(f"[Tahap 1] Mengunduh bahan baku klip: {safe_title}...")
    downloaded_file = download_func(video_url, start_time, end_time, temp_landscape)

    if not downloaded_file or not os.path.exists(temp_landscape):
        print(f"❌ Gagal mengunduh bahan untuk klip {index}.")
        return

    # 2. Render ke Vertikal (Center Crop untuk efisiensi CPU)
    print(f"[Tahap 2] Memotong menjadi Vertikal (9:16) untuk TikTok/Reels...")
    crop_x = "iw/2-ow/2"

    try:
        (
            ffmpeg.input(temp_landscape)
            .filter("crop", w="ih*9/16", h="ih", x=crop_x, y=0)
            .filter("scale", 720, 1280)  # Resolusi ringan 720p untuk CPU lokal
            .output(
                final_vertical,
                vcodec="libx264",
                preset="veryfast",  # Preset dipercepat agar CPU tidak kepanasan
                crf=28,
            )
            .run(overwrite_output=True, quiet=True)
        )

        # 3. Pembersihan: Hapus file landscape mentah untuk menghemat storage
        if os.path.exists(temp_landscape):
            os.remove(temp_landscape)

        print(f"✅ KLIP SELESAI DIRENDER: {final_vertical}")

    except ffmpeg.Error as e:
        print(
            f"❌ FFmpeg Error pada klip {index}: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
        )
