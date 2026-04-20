import os
import requests
import random
import numpy as np
from log import logger
from langchain_huggingface import HuggingFaceEmbeddings

def _score_broll_relevance(keyword: str, video_description: str) -> float:
    """
    4. Cross-Modal B-Roll Scoring (Proxy via Text Embeddings)
    Membandingkan kesesuaian antara keyword dan deskripsi video dari API.
    """
    try:
        model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        v1 = np.array(model.embed_query(keyword))
        v2 = np.array(model.embed_query(video_description))
        # Cosine Similarity
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    except Exception:
        return 0.5

def download_broll(keyword: str, output_path: str) -> bool:
    """
    Mengunduh stock video dengan seleksi cerdas.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return False
        
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=10"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        videos = data.get("videos", [])
        if not videos:
            return False
            
        # 4. Cross-Modal Scoring: Pilih video yang paling relevan secara semantik
        scored_videos = []
        for v in videos:
            # Pexels tidak kasih deskripsi panjang, kita gunakan tags/url sebagai proksi
            tags = " ".join([t.get("name", "") for t in v.get("tags", [])])
            score = _score_broll_relevance(keyword, tags if tags else v.get("url", ""))
            scored_videos.append((score, v))
            
        scored_videos.sort(key=lambda x: x[0], reverse=True)
        best_video = scored_videos[0][1]
        
        video_files = best_video.get("video_files", [])
        if not video_files: return False
        
        best_file = min(video_files, key=lambda f: abs(f.get("width", 0) - 720))
        video_url = best_file["link"]
        
        r_vid = requests.get(video_url, stream=True, timeout=30)
        with open(output_path, 'wb') as f:
            for chunk in r_vid.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"✅ B-Roll terpilih (Score {scored_videos[0][0]:.2f}): {keyword}")
        return True
    except Exception as e:
        logger.error(f"❌ Gagal B-Roll: {e}")
        return False
