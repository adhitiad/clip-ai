import ffmpeg
import cv2
import os
import mediapipe as mp
from log import logger

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
        # Fallback to gta or center crop
        return "gta", int((width - (height * 9 / 16)) / 2)

    centers_x.sort()
    clusters = []
    current_cluster = [centers_x[0]]
    for x in centers_x[1:]:
        if x - current_cluster[-1] < width * 0.15: # 15% distance horizontal
            current_cluster.append(x)
        else:
            clusters.append(current_cluster)
            current_cluster = [x]
    clusters.append(current_cluster)

    # Filter outlier clusters (but lower threshold because we only sample 20 frames)
    valid_clusters = [c for c in clusters if len(c) >= int((frame_count/step) * 0.1)]

    # Limit crop boundaries
    crop_w = height * 9 / 16
    half_crop_w = crop_w / 2

    def clamp_x(x):
        if x - half_crop_w < 0: return half_crop_w
        elif x + half_crop_w > width: return width - half_crop_w
        return x

    if len(valid_clusters) == 0:
        return "gta", int((width - (height * 9 / 16)) / 2)
    elif len(valid_clusters) == 1:
        avg_x = sum(valid_clusters[0]) / len(valid_clusters[0])
        return "crop", int(clamp_x(avg_x) - half_crop_w)
    else:
        # Sort desc by members
        valid_clusters.sort(key=len, reverse=True)
        top_2 = valid_clusters[:2]
        top_2.sort(key=lambda c: sum(c)/len(c)) # Left to right (person 1, person 2)
        c1 = sum(top_2[0])/len(top_2[0])
        c2 = sum(top_2[1])/len(top_2[1])
        return "split", [int(clamp_x(c1) - half_crop_w), int(clamp_x(c2) - half_crop_w)]

def detect_active_speaker(video_path: str, split_x: list):
    """
    Melacak pergerakan bibir menggunakan MediaPipe FaceMesh
    Merespon string ekspresi FFmpeg untuk `enable` pada masing-masing pembicara.
    """
    mp_face_mesh = mp.solutions.face_mesh
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1: fps = 30
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    # Kita akan melakukan sampling 3 frame per detik untuk efisiensi
    frame_step = max(1, int(fps / 3)) 
    
    speaker_0_active_times = []
    speaker_1_active_times = []
    
    with mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, min_detection_confidence=0.3) as face_mesh:
        frame_idx = 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret: break
            
            time_sec = frame_idx / fps
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            s0_lip_dist = 0
            s1_lip_dist = 0
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Titik bibir dalam (upper 13, lower 14)
                    upper_lip = face_landmarks.landmark[13]
                    lower_lip = face_landmarks.landmark[14]
                    dist = abs(upper_lip.y - lower_lip.y)
                    
                    x_center = face_landmarks.landmark[1].x * width
                    
                    # Bandingkan apakah ini milik cluster/split X yang pertama atau kedua
                    # smart_x[0] adalah x kiri (orang 1), smart_x[1] adalah x kanan (orang 2)
                    dist_to_0 = abs(x_center - split_x[0])
                    dist_to_1 = abs(x_center - split_x[1])
                    
                    if dist_to_0 < dist_to_1:
                        s0_lip_dist = dist
                    else:
                        s1_lip_dist = dist
            
            # Ambang batas mulut terbuka (perlu disesuaikan secara empiris, misal 0.01 relative to face)
            # Sistem relatif sederhana: siapa yang lebih lebar dan melebihi 0.005
            if s0_lip_dist > s1_lip_dist and s0_lip_dist > 0.005:
                speaker_0_active_times.append(time_sec)
            elif s1_lip_dist > s0_lip_dist and s1_lip_dist > 0.005:
                speaker_1_active_times.append(time_sec)
                
            frame_idx += frame_step
            
    cap.release()
    
    def smooth_and_format_expr(times):
        if not times: return "0"
        # Kelompokkan ke rentang [start, end]
        ranges = []
        start = times[0]
        prev = times[0]
        
        for t in times[1:]:
            if t - prev > 1.5:  # Jika jarak > 1.5 detik, buat rentang baru
                ranges.append((start, prev + 0.5))
                start = t
            prev = t
        ranges.append((start, prev + 0.5))
        
        expr_list = [f"between(t,{r[0]},{r[1]})" for r in ranges]
        return "+".join(expr_list) if expr_list else "0"

    expr_0 = smooth_and_format_expr(speaker_0_active_times)
    expr_1 = smooth_and_format_expr(speaker_1_active_times)
    
    # Berikan fallback jika tidak ada ekspresi
    if expr_0 == "0": expr_0 = "between(t,-1,-1)"
    if expr_1 == "0": expr_1 = "between(t,-1,-1)"
    
    return expr_0, expr_1

def crop_to_vertical_cpu(input_video: str, output_video: str, start_time: int, end_time: int):
    # Potong video master menjadi klip pendek terlebih dahulu (SANGAT CEPAT)
    temp_clip = "temp/clip_raw.mp4"
    (
        ffmpeg.input(input_video, ss=start_time, to=end_time)
        .output(temp_clip, c="copy")
        .run(overwrite_output=True, quiet=True)
    )

    mode, smart_x = analyze_video_layout(temp_clip)
    # Simplify for raw cropper, just use first x if it's a split screen
    if mode == "split": smart_x = smart_x[0]
    crop_x = str(smart_x) if isinstance(smart_x, int) and smart_x > 0 else "iw/2-ow/2"

    (
        ffmpeg.input(temp_clip)
        .filter("crop", w="ih*9/16", h="ih", x=crop_x, y=0)
        .filter("scale", 720, 1280)
        .output(output_video, vcodec="libx264", preset="veryfast", crf=28)
        .run(overwrite_output=True, quiet=True)
    )
    return output_video

def process_clip(video_url: str, clip_metadata: dict, index: int, download_func):
    """
    Menerima metadata dari AI, mengunduh potongannya, lalu merender ke format 9:16 menggunakan AI Tracking.
    """
    start_time = clip_metadata.get("start_time", 0)
    end_time = clip_metadata.get("end_time", 0)

    raw_title = clip_metadata.get("title_id", f"Clip_{index}")
    safe_title = (
        "".join([c for c in raw_title if c.isalnum() or c == " "])
        .rstrip()
        .replace(" ", "_")
    )

    temp_landscape = f"temp/raw_{index}_{start_time}.mp4"
    final_vertical = f"temp/FINAL_{safe_title}.mp4"

    logger.info(f"[Tahap 1] Mengunduh bahan baku klip: {safe_title}...")
    downloaded_file = download_func(video_url, start_time, end_time, temp_landscape)

    if not downloaded_file or not os.path.exists(temp_landscape):
        logger.error(f"❌ Gagal mengunduh bahan untuk klip {index}.")
        return

    logger.info(f"[Tahap 2] Auto-Captioning & MediaPipe AI Tracking...")
    try:
        # INTELLIGENT CONTINUOUS LEARNING: Gunakan MediaPipe untuk deteksi fokus
        mode, smart_x = analyze_video_layout(temp_landscape)
        # Akan ditangani sesuai mode di bagian filter graph Nanti

        # TAHAP 2A: Ekstrak audio dari segmen
        temp_audio = f"temp/audio_{index}.mp3"
        logger.info("  -> Ekstrak audio untuk transkripsi Whisper...")
        (
            ffmpeg.input(temp_landscape)
            .output(temp_audio, acodec="libmp3lame", qscale=2)
            .run(overwrite_output=True, quiet=True)
        )

        # TAHAP 2B: Generate SRT dari Audio menggunakan Whisper (dan dapatkan mute ranges untuk kata kasar)
        logger.info("  -> Generating timecoded subtitles via LLM & Censor checks...")
        from utils.captioning import generate_srt_from_audio
        temp_srt = f"temp/sub_{index}.srt"
        from utils.captioning import generate_srt_from_audio
        temp_srt_path, mute_ranges = generate_srt_from_audio(temp_audio, temp_srt)

        # TAHAP 2B.2: Unduh B-Roll jika ada
        broll_query = clip_metadata.get("broll_query", "")
        broll_path = ""
        if broll_query:
            from utils.broll import download_broll
            logger.info(f"  -> Mendownload B-Roll untuk query: {broll_query}")
            # The download_broll function handles network errors nicely and returns boolean
            if download_broll(broll_query, f"temp/broll_{index}.mp4"):
                broll_path = f"temp/broll_{index}.mp4"

        # TAHAP 2C: Menyusun filter graph untuk 3 Varian (A/B Testing Generation)
        logger.info("  -> Mengeksekusi FFmpeg CPU Render (Complex Filter) untuk 3 Varian A/B Testing...")
        srt_filter_path = temp_srt.replace('\\', '/')
        safe_title_display = raw_title.replace("'", "").replace(":", " ")
        style = "FontName=Arial,FontSize=20,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=90"

        # Deteksi Speaker Diarization secara dinamis jika mode split
        expr_0, expr_1 = "0", "0"
        if mode == "split" and isinstance(smart_x, list) and len(smart_x) == 2:
            logger.info("  -> Menjalankan FaceMesh Lip Tracking untuk Diarization...")
            expr_0, expr_1 = detect_active_speaker(temp_landscape, smart_x)

        import random
        broll_options = ["assets/gta.mp4", "assets/subway.mp4", "assets/slime.mp4"]
        valid_brolls = [b for b in broll_options if os.path.exists(b)]
        
        final_video_outputs = []

        for variant in ["var1", "var2", "var3"]:
            final_vertical = f"temp/FINAL_{safe_title}_{variant}.mp4"
            logger.info(f"  -> Rendering Varian: {variant}...")
            
            # Setup Konfigurasi Varian
            v_style = style
            v_broll = broll_path
            v_bg_broll = "assets/gta.mp4"
            v_bgm = "assets/lofi.mp3"
            v_hue = False
            v_pitch = False
            
            if variant == "var1":
                pass # Default: Pexels B-Roll + Lofi Ducking
            elif variant == "var2":
                # Phonk + Hue Rotation + Pop Bold Subtitles + Tidak ada Pexels
                v_bgm = "assets/phonk.mp3" if os.path.exists("assets/phonk.mp3") else "assets/lofi.mp3"
                v_hue = True
                v_broll = None
                v_style = "FontName=Arial,FontSize=28,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=1,Outline=3,Shadow=0,MarginV=120"
            elif variant == "var3":
                # Variasi Slime/Subway + Pitch Shifted Audio + Anti Shadowban
                if valid_brolls:
                    v_bg_broll = random.choice(valid_brolls)
                v_bgm = "assets/phonk.mp3" if os.path.exists("assets/phonk.mp3") else None
                v_pitch = True
                v_broll = None

            # STREAM INPUTS
            stream = ffmpeg.input(temp_landscape)
            audio_main = stream.audio

            # SENSOR AUDIO BLEEP
            if mute_ranges:
                enable_expr = "+".join([f"between(t,{start},{end})" for start, end in mute_ranges])
                audio_main = audio_main.filter('volume', enable=enable_expr, volume=0)

            # ANTI-SHADOWBAN PITCH SHIFTING
            if v_pitch:
                audio_main = audio_main.filter("asetrate", "44100*1.05").filter("aresample", "44100")

            # VISUAL LAYOUT
            if mode == "crop":
                crop_x = str(smart_x) if isinstance(smart_x, int) and smart_x > 0 else "iw/2-ow/2"
                video_stream = stream.filter("crop", w="ih*9/16", h="ih", x=crop_x, y=0).filter("scale", 720, 1280)
            elif mode == "split" and isinstance(smart_x, list) and len(smart_x) == 2:
                # Podcast split screen dengan SPEAKER DIARIZATION (Zoom In pada Pembicara Aktif)
                top_norm = stream.filter("crop", w="ih*9/16", h="ih", x=smart_x[0], y=0).filter("scale", 720, 1280)
                top_zoom = top_norm.filter("scale", 792, 1408).filter("crop", w=720, h=1280) # 1.1x Zoom
                top = ffmpeg.filter([top_norm, top_zoom], "overlay", enable=expr_0).filter("crop", w=720, h=640, x=0, y=320)
                
                bot_norm = stream.filter("crop", w="ih*9/16", h="ih", x=smart_x[1], y=0).filter("scale", 720, 1280)
                bot_zoom = bot_norm.filter("scale", 792, 1408).filter("crop", w=720, h=1280) # 1.1x Zoom
                bot = ffmpeg.filter([bot_norm, bot_zoom], "overlay", enable=expr_1).filter("crop", w=720, h=640, x=0, y=320)
                
                video_stream = ffmpeg.filter([top, bot], "vstack")
            else: # "gta" mode
                crop_x = "iw/2-ow/2"
                video_stream = stream.filter("crop", w="ih*9/16", h="ih", x=crop_x, y=0).filter("scale", 720, 1280)
                if os.path.exists(v_bg_broll):
                    gta_stream = ffmpeg.input(v_bg_broll).filter("scale", 720, 640)
                    if v_hue:
                        gta_stream = gta_stream.filter("hue", h=str(random.randint(0, 360)))
                    v_main_top = video_stream.filter("crop", w=720, h=640, x=0, y=0)
                    video_stream = ffmpeg.filter([v_main_top, gta_stream], "vstack")

            # B-ROLL OVERLAY (0 - 3s)
            if v_broll and os.path.exists(v_broll):
                broll_stream = ffmpeg.input(v_broll).filter("crop", w="ih*9/16", h="ih").filter("scale", 720, 1280).filter("fade", t="out", st=2.5, d=0.5)
                video_stream = ffmpeg.filter([video_stream, broll_stream], "overlay", enable="between(t,0,3)")

            # TITLE OVERLAY
            video_stream = video_stream.filter(
                "drawtext",
                text=safe_title_display,
                fontsize=40,
                fontcolor="white",
                box=1,
                boxcolor="black@0.6",
                boxborderw=15,
                x="(w-text_w)/2",
                y=180,
                fontfile="C:/Windows/Fonts/arialbd.ttf"
            )
            
            # SUBTITLE HARDCODE
            video_stream = video_stream.filter("subtitles", srt_filter_path, force_style=v_style)

            # AUDIO MIXING (Ducking & SFX)
            inputs_audio = [audio_main]
            if v_bgm and os.path.exists(v_bgm):
                bgm = ffmpeg.input(v_bgm).filter("volume", 0.05) 
                inputs_audio.append(bgm)
            if os.path.exists("assets/pop.mp3"):
                sfx = ffmpeg.input("assets/pop.mp3").filter("adelay", "300|300").filter("volume", 1.5)
                inputs_audio.append(sfx)
                
            if len(inputs_audio) > 1:
                audio_out = ffmpeg.filter(inputs_audio, 'amix', inputs=len(inputs_audio), duration='first', dropout_transition=2)
            else:
                audio_out = audio_main

            # OUTPUT AKHIR
            (
                ffmpeg.output(
                    video_stream,
                    audio_out,
                    final_vertical,
                    vcodec="libx264",
                    preset="veryfast", 
                    crf=28,
                )
                .run(overwrite_output=True, quiet=True)
            )
            final_video_outputs.append(final_vertical)

        # Bersihkan temp file
        if os.path.exists(temp_landscape):
            os.remove(temp_landscape)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if os.path.exists(temp_srt):
            os.remove(temp_srt)

        logger.info(f"✅ KLIP SELESAI DIRENDER DENGAN SMART CROP & CAPTIONS: {final_vertical}")

    except ffmpeg.Error as e:
        logger.error(f"❌ FFmpeg Error pada klip {index}: {e.stderr.decode('utf-8') if e.stderr else str(e)}")
        
    return final_video_outputs
