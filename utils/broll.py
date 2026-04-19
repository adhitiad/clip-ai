import os
import requests
import random
from log import logger

def download_broll(keyword: str, output_path: str) -> bool:
    """
    Mengunduh stock video vertikal dari Pexels API berdasarkan keyword transkrip
    sebagai B-Roll Hook selama 3 detik pertama klip.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        logger.warning("PEXELS_API_KEY tidak ada. B-Roll injection dilewati.")
        return False
        
    headers = {"Authorization": api_key}
    # Mencari video vertikal (portrait) kecil/medium, cocok untuk Tiktok
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=5"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("videos"):
            logger.warning(f"Tidak ada video Pexels ditemukan untuk keyword: {keyword}")
            return False
            
        # Pilih video acak dari hasil top 5
        video_item = random.choice(data["videos"])
        
        # Temukan video files format MP4 yang paling ringan/sesuai
        video_files = video_item.get("video_files", [])
        if not video_files: return False
        
        # Sortir file berdadasarkan lebar mendekati 720
        best_file = min(video_files, key=lambda f: abs(f.get("width", 0) - 720))
        video_url = best_file["link"]
        
        # Download ke output_path
        r_vid = requests.get(video_url, stream=True, timeout=30)
        r_vid.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r_vid.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"✅ Berhasil mengunduh B-Roll Pexels: {keyword}")
        return True
    except Exception as e:
        logger.error(f"❌ Gagal mengunduh B-Roll: {e}")
        return False
