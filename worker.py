import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Mengatur Redis sebagai Message Broker dan Backend Result
# Secara default menunjuk ke localhost jika environment variable tidak diset
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "clip_ai_worker",
    broker=redis_url,
    backend=redis_url
)

# Konfigurasi tambahan Celery (opsional)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1, # Penting untuk task rendering video berat agar tidak hoarding
    task_acks_late=True
)

@celery_app.task(bind=True, name="process_all_clips_task")
def process_all_clips_task(self, video_url: str, clips_metadata: list, lang: str):
    """
    Task rendering yang dijalankan oleh worker Celery secara asynchronous.
    Dipindahkan dari BackgroundTasks FastAPI agar web server tidak hang.
    """
    # Import lambat untuk mencegah circular/initialization error di worker
    from services.video_engine import process_clip
    import tempfile 
    from utils.youtube import download_video_segment

    from log import logger
    total_clips = len(clips_metadata)
    all_rendered_files = []
    
    for index, clip in enumerate(clips_metadata):
        logger.info(f"Celery Worker -> Persiapan render klip {index+1}/{total_clips}: {clip.get('title_en')} ({clip.get('start_time')}s - {clip.get('end_time')}s)")
        
        # Proses rendering
        variant_paths = process_clip(video_url, clip, index+1, download_video_segment)
        if variant_paths:
            all_rendered_files.extend(variant_paths)
            
        # Update progress jika perlu (bisa ditangkap oleh API nanti)
        self.update_state(state='PROGRESS', meta={'current': index+1, 'total': total_clips})
        
    return {
        "status": "success", 
        "rendered_clips_count": total_clips, 
        "total_variants_generated": len(all_rendered_files),
        "files": all_rendered_files
    }
