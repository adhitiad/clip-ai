"""YouTube Data API v3 (server-side) untuk riset pasar publik.

Menggunakan YOUTUBE_DATA_API_KEY dari .env (via backend.core.env).
Bukan pengganti yt-dlp untuk download; ini hanya metadata/search.
"""

import os
from urllib.parse import urlencode

import requests

from backend.log import logger

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _api_key() -> str:
    return os.getenv("YOUTUBE_DATA_API_KEY", "").strip()


def search_videos(query: str, max_results: int = 10) -> list[dict]:
    """Cari video publik; kembalikan [{video_id,title,description,published_at}]."""
    key = _api_key()
    if not key:
        logger.warning("[YouTubeData] YOUTUBE_DATA_API_KEY kosong.")
        return []
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max(1, max_results), 50),
        "key": key,
    }
    try:
        response = requests.get(f"{YOUTUBE_SEARCH_URL}?{urlencode(params)}", timeout=15)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [
            {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"].get("title", ""),
                "description": item["snippet"].get("description", ""),
                "published_at": item["snippet"].get("publishedAt", ""),
            }
            for item in items
            if item.get("id", {}).get("videoId")
        ]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error(f"[YouTubeData] Search gagal: {exc}")
        return []


def get_video_details(video_ids: list[str]) -> list[dict]:
    """Ambil statistik/detail video berdasarkan ID."""
    key = _api_key()
    if not key or not video_ids:
        return []
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids[:50]),
        "key": key,
    }
    try:
        response = requests.get(f"{YOUTUBE_VIDEOS_URL}?{urlencode(params)}", timeout=15)
        response.raise_for_status()
        return response.json().get("items", [])
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"[YouTubeData] Detail gagal: {exc}")
        return []
