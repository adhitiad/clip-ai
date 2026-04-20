import ffmpeg
import cv2
import os
import mediapipe as mp
import random
from log import logger
from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip
from services.viral_predictor import select_best_hook_variant

def analyze_video_layout(video_path: str):
    """Menggunakan MediaPipe untuk mendeteksi wajah/pose dan menentukan mode layout: 'crop', 'split', atau 'gta'."""
    mp_face_detection = mp.solutions.face_detection
    cap = cv2.VideoCapture(video_path)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if width == 0 or height == 0:
        return "crop", 0
        
    centers_x = []
    
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3) as face_detection:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            frame_count = 300
        step = max(1, frame_count // 20)
        
        for i in range(0, frame_count, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break
            
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(image)
            
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    x_center = bbox.xmin + (bbox.width / 2)
                    centers_x.append(x_center * width)
                    
    cap.release()
    
    if not centers_x:
        return "gta", int((width - (height * 9 / 16)) / 2)

    centers_x.sort()
    clusters = []
    current_cluster = [centers_x[0]]
    for x in centers_x[1:]:
        if x - current_cluster[-1] < width * 0.15:
            current_cluster.append(x)
        else:
            clusters.append(current_cluster)
            current_cluster = [x]
    clusters.append(current_cluster)

    valid_clusters = [c for c in clusters if len(c) >= int((len(centers_x)) * 0.1)]

    crop_w = height * 9 / 16
    half_crop_w = crop_w / 2

    def clamp_x(x):
        if x - half_crop_w < 0: return half_crop_w
        elif x + half_crop_w > width: return width - half_crop_w
        return x

    if not valid_clusters:
        return "gta", int((width - (height * 9 / 16)) / 2)
    elif len(valid_clusters) == 1:
        avg_x = sum(valid_clusters[0]) / len(valid_clusters[0])
        return "crop", int(clamp_x(avg_x) - half_crop_w)
    else:
        valid_clusters.sort(key=len, reverse=True)
        top_2 = valid_clusters[:2]
        top_2.sort(key=lambda c: sum(c)/len(c))
        c1 = sum(top_2[0])/len(top_2[0])
        c2 = sum(top_2[1])/len(top_2[1])
        return "split", [int(clamp_x(c1) - half_crop_w), int(clamp_x(c2) - half_crop_w)]

def detect_active_speaker(video_path: str, split_x: list):
    """Melacak pergerakan bibir menggunakan FaceMesh untuk Speaker Diarization."""
    mp_face_mesh = mp.solutions.face_mesh
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_step = max(1, int(fps / 3)) 
    
    s0_times, s1_times = [], []
    
    with mp_face_mesh.FaceMesh(max_num_faces=2, min_detection_confidence=0.3) as face_mesh:
        frame_idx = 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret: break
            
            time_sec = frame_idx / fps
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                for landmarks in results.multi_face_landmarks:
                    dist = abs(landmarks.landmark[13].y - landmarks.landmark[14].y)
                    xc = landmarks.landmark[1].x * width
                    if abs(xc - split_x[0]) < abs(xc - split_x[1]):
                        if dist > 0.005: s0_times.append(time_sec)
                    else:
                        if dist > 0.005: s1_times.append(time_sec)
            frame_idx += frame_step
    cap.release()

    def format_expr(times):
        if not times: return "between(t,-1,-1)"
        ranges = []
        start = times[0]
        prev = times[0]
        for t in times[1:]:
            if t - prev > 1.5:
                ranges.append((start, prev + 0.5))
                start = t
            prev = t
        ranges.append((start, prev + 0.5))
        return "+".join([f"between(t,{r[0]},{r[1]})" for r in ranges])

    return format_expr(s0_times), format_expr(s1_times)

def generate_dynamic_subtitles(words, video_width, video_height):
    """7. AI-Powered Dynamic Captions Highlighting."""
    clips = []
    styles = ["bold_yellow", "clean_white", "modern_glass"]
    best_style_meta = select_best_hook_variant({"title_id": "subtitle_style"}, styles)
    style = best_style_meta["title_en"]

    for i, word in enumerate(words):
        color = 'yellow' if len(word['text']) > 6 or i % 5 == 0 else 'white'
        fontsize = 75 if "glass" in style else 70
        
        txt = TextClip(
            word['text'].upper(),
            fontsize=fontsize,
            color=color,
            stroke_color='black',
            stroke_width=2,
            font='Arial-Bold',
            method='caption',
            size=(video_width*0.8, None)
        ).set_start(word['start']).set_duration(max(0.1, word['end'] - word['start'])).set_position(('center', video_height*0.7))
        clips.append(txt)
    return clips

def process_clip(video_url: str, clip_metadata: dict, index: int, download_func):
    """Pipeline render utama dengan A/B Testing, Dynamic Captions, dan B-Roll."""
    start_time = clip_metadata.get("start_time", 0)
    end_time = clip_metadata.get("end_time", 0)
    raw_title = clip_metadata.get("title_id", f"Clip_{index}")
    safe_title = "".join([c for c in raw_title if c.isalnum() or c == " "]).strip().replace(" ", "_")

    temp_landscape = f"temp/raw_{index}.mp4"
    temp_audio = f"temp/audio_{index}.mp3"
    temp_vertical_v1 = f"temp/v1_{index}.mp4"
    final_variant_output = f"output/FINAL_{safe_title}.mp4"

    logger.info(f"🚀 Render Klip {index}: {raw_title}")
    
    if not download_func(video_url, start_time, end_time, temp_landscape):
        return None

    # Step Audio & Transcribe
    (ffmpeg.input(temp_landscape).output(temp_audio, acodec="libmp3lame", qscale=2).run(quiet=True, overwrite_output=True))
    
    # Generate Subtitles data (JSON format word-by-word)
    from utils.captioning import get_word_level_transcription
    words = get_word_level_transcription(temp_audio)

    # Analyze Layout
    mode, smart_x = analyze_video_layout(temp_landscape)
    expr0, expr1 = "0", "0"
    if mode == "split":
        expr0, expr1 = detect_active_speaker(temp_landscape, smart_x)

    # 1. Produce Base Vertical via FFmpeg (FAST)
    v_stream = ffmpeg.input(temp_landscape)
    if mode == "crop":
        v_stream = v_stream.filter("crop", w="ih*9/16", h="ih", x=smart_x, y=0).filter("scale", 720, 1280)
    elif mode == "split":
        t0 = v_stream.filter("crop", w="ih*9/16", h="ih", x=smart_x[0], y=0).filter("scale", 720, 640)
        t1 = v_stream.filter("crop", w="ih*9/16", h="ih", x=smart_x[1], y=0).filter("scale", 720, 640)
        v_stream = ffmpeg.filter([t0, t1], "vstack")
    else:
        v_stream = v_stream.filter("crop", w="ih*9/16", h="ih", x="iw/2-ow/2", y=0).filter("scale", 720, 1280)

    # Render base vertical
    (ffmpeg.output(v_stream, temp_vertical_v1, vcodec="libx264", preset="ultrafast").run(quiet=True, overwrite_output=True))

    # 2. Add Dynamic Captions via MoviePy (PREMIUM LOOK)
    video_clip = VideoFileClip(temp_vertical_v1).set_audio(AudioFileClip(temp_audio))
    subtitle_clips = generate_dynamic_subtitles(words, video_clip.w, video_clip.h)
    
    # B-Roll Hook (3 seconds)
    if index == 0: # Hanya hook awal
        from utils.broll import download_broll
        broll_path = f"temp/broll_{index}.mp4"
        if download_broll(clip_metadata.get("broll_query", "motivation"), broll_path):
            broll = VideoFileClip(broll_path).resize(height=1280).crop(x_center=video_clip.w/2, width=720).set_duration(3).fadeout(0.5)
            video_clip = CompositeVideoClip([video_clip, broll.set_start(0)])

    final = CompositeVideoClip([video_clip] + subtitle_clips)
    final.write_videofile(final_variant_output, codec="libx264", audio_codec="aac", fps=30, logger=None)

    # Cleanup
    for f in [temp_landscape, temp_audio, temp_vertical_v1]:
        if os.path.exists(f): os.remove(f)

    return final_variant_output
