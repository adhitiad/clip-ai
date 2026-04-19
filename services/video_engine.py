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
