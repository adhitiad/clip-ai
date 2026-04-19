"""
utils/rss_google.py
====================
Modul untuk mengambil dan memproses Google Trends RSS Feed &
YouTube RSS Feed untuk keperluan:
  1. Menyarankan niche konten viral
  2. Mencari video YouTube berdasarkan niche
"""

import re
import time
import random
import feedparser
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, urlencode
from typing import Optional
import sys

# Fix encoding untuk Windows CMD
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Google Trends RSS (per negara, bisa diubah)
GOOGLE_TRENDS_URLS = {
    "id": "https://trends.google.com/trending/rss?geo=ID",  # Indonesia
    "us": "https://trends.google.com/trending/rss?geo=US",  # USA
    "gb": "https://trends.google.com/trending/rss?geo=GB",  # UK
    "in": "https://trends.google.com/trending/rss?geo=IN",  # India
    "ca": "https://trends.google.com/trending/rss?geo=CA",  # Canada
    "au": "https://trends.google.com/trending/rss?geo=AU",  # Australia
    "de": "https://trends.google.com/trending/rss?geo=DE",  # Germany
    "fr": "https://trends.google.com/trending/rss?geo=FR",  # France
    "jp": "https://trends.google.com/trending/rss?geo=JP",  # Japan
    "kr": "https://trends.google.com/trending/rss?geo=KR",  # South Korea
    "cn": "https://trends.google.com/trending/rss?geo=CN",  # China
    "tw": "https://trends.google.com/trending/rss?geo=TW",  # Taiwan
    "my": "https://trends.google.com/trending/rss?geo=MY",  # Malaysia
    "sg": "https://trends.google.com/trending/rss?geo=SG",  # Singapore
    "global": "https://trends.google.com/trending/rss?geo=",  # Global
}

# YouTube RSS per channel / search (yt-dlp lebih baik, tapi ini lightweight)
YT_CHANNEL_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# Google tidak buka RSS search resmi, pakai media rss dengan query workaround
YT_SEARCH_RSS = (
    "https://www.youtube.com/feeds/videos.xml?search={query}"  # unofficial, sering 404
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
}


# ─── HELPER ───────────────────────────────────────────────────────────────────


def _fetch_rss_feedparser(url: str) -> list:
    """
    Gunakan feedparser untuk parsing RSS — menangani namespace secara otomatis.
    Returns list of entries.
    """
    try:
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as e:
        print(f"[RSS] RSS fetch error dari {url}: {e}")
        return []


def _fetch_rss_xml(url: str, timeout: int = 10) -> Optional[ET.Element]:
    """Ambil dan parse XML secara manual (fallback)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        return root
    except requests.RequestException as e:
        print(f"[RSS] Gagal fetch {url}: {e}")
        return None
    except ET.ParseError as e:
        print(f"[RSS] XML parse error dari {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GOOGLE TRENDS NICHE SUGGESTION
# ═══════════════════════════════════════════════════════════════════════════════


def get_trending_topics(geo: str = "id", max_items: int = 20) -> list[dict]:
    """
    Ambil topik trending dari Google Trends RSS menggunakan feedparser.

    Returns:
        list of dict: [{"title": str, "approx_traffic": str, "news_items": list}]
    """
    url = GOOGLE_TRENDS_URLS.get(geo, GOOGLE_TRENDS_URLS["id"])
    print(f"[RSS] Mengambil Google Trends untuk geo='{geo.upper()}'...")

    entries = _fetch_rss_feedparser(url)
    if not entries:
        return []

    results = []
    for entry in entries[:max_items]:
        title = entry.get("title", "Unknown")
        # Google Trends RSS custom tags
        traffic = entry.get("ht_approx_traffic", entry.get("approx_traffic", "N/A"))

        # Berita terkait
        news_list = []
        news_items = entry.get("ht_news_item", [])
        if isinstance(news_items, list):
            for n in news_items[:3]:
                news_list.append(
                    {
                        "title": n.get("ht_news_item_title", n.get("title", "")),
                        "url": n.get("ht_news_item_url", n.get("url", "")),
                    }
                )

        results.append(
            {
                "title": str(title).strip(),
                "approx_traffic": str(traffic).strip(),
                "news_items": news_list,
            }
        )

    return results


def analyze_niches_with_ai(
    trending_topics: list[dict], groq_api_key: str
) -> list[dict]:
    """
    Gunakan AI (Groq/LLaMA) untuk menganalisis topik trending dan merekomendasikan
    niche konten TikTok/YouTube Shorts yang cocok.

    Returns:
        list of dict: [{"niche": str, "topic": str, "hook_idea": str, "score": int}]
    """
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import JsonOutputParser

    if not trending_topics:
        return []

    # Format ringkas topik untuk prompt
    topics_text = "\n".join(
        [
            f"- {t['title']} (traffic: {t['approx_traffic']})"
            for t in trending_topics[:15]
        ]
    )

    llm = ChatGroq(api_key=groq_api_key, model_name="llama3-8b-8192", temperature=0.7)
    parser = JsonOutputParser()

    prompt = PromptTemplate.from_template(
        """Kamu adalah ahli strategi konten viral TikTok dan YouTube Shorts.
Berikut adalah topik trending Google hari ini:

{topics}

Berdasarkan topik trending di atas, rekomendasikan 5 niche konten terbaik yang bisa diolah menjadi klip pendek viral.
Untuk setiap niche, berikan:
- "niche": nama niche (misal: "Berita Politik", "Hiburan Artis", "Teknologi AI")
- "topic": topik spesifik dari list trending di atas yang relevan  
- "hook_idea": ide hook/pembuka konten yang menarik (max 1 kalimat)
- "search_query": query pencarian YouTube yang disarankan (dalam bahasa Inggris agar dapat lebih banyak konten)
- "viral_score": skor potensi viral 1-10 (angka saja)

Jawab HANYA dalam format JSON array, tanpa penjelasan tambahan:
[
  {{"niche": "...", "topic": "...", "hook_idea": "...", "search_query": "...", "viral_score": 8}},
  ...
]"""
    )

    chain = prompt | llm | parser

    try:
        result = chain.invoke({"topics": topics_text})
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        print(f"[RSS] AI niche analysis error: {e}")
        # Fallback: return raw topics sebagai niche sederhana
        return [
            {
                "niche": t["title"],
                "topic": t["title"],
                "hook_idea": f"Viral: {t['title']}",
                "search_query": t["title"],
                "viral_score": 5,
            }
            for t in trending_topics[:5]
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. YOUTUBE VIDEO FINDER VIA RSS
# ═══════════════════════════════════════════════════════════════════════════════


def search_youtube_videos_rss(query: str, max_results: int = 10) -> list[dict]:
    """
    Cari video YouTube menggunakan pendekatan RSS + ytdl metadata ringan.
    Strategi:
      1. Coba YouTube RSS search (unofficial, sering tidak tersedia)
      2. Fallback: gunakan yt-dlp dalam mode ringan (no download) untuk search

    Returns:
        list of dict: [{"title", "url", "channel", "duration", "view_count", "thumbnail"}]
    """
    print(f"[RSS] Mencari video YouTube untuk query: '{query}'")

    # Strategi 1: yt-dlp search (most reliable, no API key needed)
    results = _search_via_ytdlp(query, max_results)
    if results:
        return results

    # Strategi 2: YouTube RSS channel search workaround
    return _search_via_youtube_rss(query, max_results)


def _search_via_ytdlp(query: str, max_results: int = 10) -> list[dict]:
    """Gunakan yt-dlp untuk search YouTube tanpa download (extract_info only)."""
    try:
        import yt_dlp

        search_url = f"ytsearch{max_results}:{query}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,  # Jangan download, hanya metadata
            "skip_download": True,
        }

        results = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get("entries", []) if info else []

            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get("id", "")
                results.append(
                    {
                        "title": entry.get("title", "Untitled"),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "channel": entry.get(
                            "channel", entry.get("uploader", "Unknown")
                        ),
                        "duration": entry.get("duration"),  # seconds
                        "view_count": entry.get("view_count"),
                        "thumbnail": entry.get(
                            "thumbnail",
                            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                        ),
                        "source": "yt-dlp",
                    }
                )

        return results

    except Exception as e:
        print(f"[RSS] yt-dlp search gagal: {e}")
        return []


def _search_via_youtube_rss(query: str, max_results: int = 10) -> list[dict]:
    """
    Fallback: Ambil RSS dari channel YouTube terkenal yang relevan.
    Karena YouTube tidak punya search RSS publik, kita pakai channel besar
    dan filter judulnya.
    """
    # Channel besar yang sering muncul di trending (bisa dikustomisasi)
    BIG_CHANNELS = [
        "UCupvZG-5ko_eiXAX-kEqhMQ",  # CNN Indonesia
        "UCt7fwAhXDy3oNFTAzF2o8Pw",  # Kompas TV
        "UC0C-w0YjGpqDXGB8IHb662A",  # CNBC Indonesia
    ]

    results = []
    for channel_id in BIG_CHANNELS[:2]:
        url = YT_CHANNEL_RSS.format(channel_id=channel_id)
        entries = _fetch_rss_feedparser(url)
        if not entries:
            continue

        for entry in entries:
            title = entry.get("title", "")

            # Filter sederhana apakah judul mengandung kata kunci query
            if query.lower() not in title.lower():
                continue

            video_url = entry.get("link", "")
            media = entry.get("media_thumbnail", [])
            thumb = media[0].get("url", "") if media else ""

            results.append(
                {
                    "title": title,
                    "url": video_url,
                    "channel": entry.get("author", "Unknown"),
                    "duration": None,
                    "view_count": None,
                    "thumbnail": thumb,
                    "source": "rss-channel",
                }
            )

            if len(results) >= max_results:
                break

        time.sleep(0.3)  # Sopan ke server

    return results[:max_results]
