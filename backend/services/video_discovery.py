"""Otomatis cari video sumber dari topik/niche (YouTube + Exa + Tavily + Firecrawl + Selenium/BeautifulSoup).

Tidak memerlukan kunci API untuk YouTube (yt-dlp). Exa / Tavily / Firecrawl
dipakai bila kunci API-nya diset. Selenium + BeautifulSoup diisi bila browser
tersedia (mis. development); di container produksi biasanya dilewati dengan
anggun.

Semua video difilter durasi >= min_duration_seconds (default 240 detik / 4
menit) dan dibatasi 2-10 judul. Akhirnya AI (LangChain via AGENT_PROVIDER /
AGENT_MODEL) menilai relevansi + potensi penonton dan memilih paling layak.
"""

from __future__ import annotations

import os
import re
from typing import Any

from backend.log import logger
from backend.services.model_discovery import get_text_model
from backend.utils.exa_search import search_news_with_exa
from backend.utils.rss_google import search_youtube_videos_rss

# Rentang jumlah video sumber yang diizinkan pengguna.
MIN_VIDEOS = 2
MAX_VIDEOS = 10


def _is_long_enough(duration: Any, min_seconds: int) -> bool:
    """Durasi tak diketahui tetap diterima (bisa dicek nanti saat render)."""
    if duration is None:
        return True
    try:
        return int(duration) >= min_seconds
    except TypeError, ValueError:
        return True


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/"):
        url = "https://www.youtube.com" + url
    return url


def _looks_like_video_url(url: str) -> bool:
    low = url.lower()
    return (
        "youtube.com/watch" in low
        or "youtu.be/" in low
        or "youtube.com/shorts" in low
        or "tiktok.com/@" in low
        or "tiktok.com/v/" in low
        or "instagram.com/reel/" in low
        or "facebook.com/reel/" in low
        or "facebook.com/watch" in low
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. YouTube via yt-dlp (selalu, tanpa API key)
# ═══════════════════════════════════════════════════════════════════════════


def _search_youtube(topic: str, niche: str | None, limit: int) -> list[dict]:
    queries = []
    if niche and niche.strip():
        queries.append(f"{niche.strip()} {topic.strip()}")
    queries.append(topic.strip())
    queries.append(f"{topic.strip()} video")

    seen: set[str] = set()
    results: list[dict] = []
    for query in queries:
        if len(results) >= limit:
            break
        if not query:
            continue
        try:
            yt_results = search_youtube_videos_rss(query, max_results=limit * 2)
        except Exception as exc:
            logger.warning(f"[VideoDiscovery] YouTube search gagal: {exc}")
            yt_results = []

        for v in yt_results:
            url = _clean_url(v.get("url", ""))
            if not url or url in seen or not _looks_like_video_url(url):
                continue
            if not _is_long_enough(v.get("duration"), 240):
                continue
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "title": v.get("title", "Untitled"),
                    "duration": v.get("duration"),
                    "source": v.get("source", "youtube"),
                    "channel": v.get("channel"),
                    "thumbnail": v.get("thumbnail"),
                }
            )
            if len(results) >= limit:
                break
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 2. Exa web search (opsional, butuh EXA_API_KEY)
# ═══════════════════════════════════════════════════════════════════════════


def _search_exa(topic: str, niche: str | None, limit: int) -> list[dict]:
    api_key = os.getenv("EXA_API_KEY", "").strip()
    if not api_key:
        return []

    queries = []
    if niche and niche.strip():
        queries.append(f"{niche.strip()} {topic.strip()} youtube video")
    queries.append(f"{topic.strip()} youtube video")

    seen: set[str] = set()
    results: list[dict] = []
    for query in queries:
        if len(results) >= limit:
            break
        try:
            exa_results = search_news_with_exa(
                query, num_results=limit * 2, search_type="auto"
            )
        except Exception as exc:
            logger.debug(f"[VideoDiscovery] Exa search dilewati: {exc}")
            exa_results = []

        for item in exa_results:
            url = _clean_url(item.get("url", ""))
            if not url or url in seen or not _looks_like_video_url(url):
                continue
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "title": item.get("title", "Untitled"),
                    "duration": None,
                    "source": "exa",
                    "channel": item.get("author"),
                    "thumbnail": None,
                }
            )
            if len(results) >= limit:
                break
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 3. Tavily web search (opsional, butuh TAVILY_API_KEY)
# ═══════════════════════════════════════════════════════════════════════════


def _search_tavily(topic: str, niche: str | None, limit: int) -> list[dict]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        from tavily import TavilyClient
    except ImportError:
        logger.debug("[VideoDiscovery] tavily-python belum terpasang.")
        return []

    client = TavilyClient(api_key=api_key)
    queries = []
    if niche and niche.strip():
        queries.append(f"{niche.strip()} {topic.strip()} youtube video")
    queries.append(f"{topic.strip()} youtube video")

    seen: set[str] = set()
    results: list[dict] = []
    for query in queries:
        if len(results) >= limit:
            break
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=limit * 2,
                include_domains=["youtube.com", "youtu.be"],
            )
        except Exception as exc:
            logger.debug(f"[VideoDiscovery] Tavily search dilewati: {exc}")
            response = {"results": []}

        for item in response.get("results", []) or []:
            url = _clean_url(item.get("url", ""))
            if not url or url in seen or not _looks_like_video_url(url):
                continue
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "title": item.get("title", "Untitled"),
                    "duration": None,
                    "source": "tavily",
                    "channel": item.get("source"),
                    "thumbnail": None,
                }
            )
            if len(results) >= limit:
                break
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 4. Firecrawl web search / scrape (opsional, butuh FIRECRAWL_API_KEY)
# ═══════════════════════════════════════════════════════════════════════════


def _search_firecrawl(topic: str, niche: str | None, limit: int) -> list[dict]:
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        from firecrawl import FirecrawlApp
    except ImportError:
        logger.debug("[VideoDiscovery] firecrawl-py belum terpasang.")
        return []

    app = FirecrawlApp(api_key=api_key)
    queries = []
    if niche and niche.strip():
        queries.append(f"{niche.strip()} {topic.strip()} youtube video")
    queries.append(f"{topic.strip()} youtube video")

    seen: set[str] = set()
    results: list[dict] = []
    for query in queries:
        if len(results) >= limit:
            break
        try:
            response = app.search(
                query=query,
                limit=limit * 2,
                scrapeOptions={"formats": ["links"]},
            )
        except Exception as exc:
            logger.debug(f"[VideoDiscovery] Firecrawl search dilewati: {exc}")
            response = {"data": []}

        for item in response.get("data", []) or []:
            url = _clean_url(item.get("url", "") or item.get("link", ""))
            if not url or url in seen or not _looks_like_video_url(url):
                continue
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "title": item.get("title", "Untitled"),
                    "duration": None,
                    "source": "firecrawl",
                    "channel": None,
                    "thumbnail": None,
                }
            )
            if len(results) >= limit:
                break
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 5. Selenium + BeautifulSoup (opsional, butuh browser driver)
# ═══════════════════════════════════════════════════════════════════════════


def _search_selenium_bs4(topic: str, niche: str | None, limit: int) -> list[dict]:
    """Cari video lewat Google search halaman web + parse BeautifulSoup.

    Hanya berjalan bila Chrome/Chromium + chromedriver tersedia. Di
    container produksi biasanya tidak ada → dilewati dengan anggun.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        logger.debug("[VideoDiscovery] selenium belum terpasang.")
        return []

    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        logger.debug("[VideoDiscovery] webdriver-manager belum terpasang.")
        return []

    from bs4 import BeautifulSoup

    query = f"{niche + ' ' if niche and niche.strip() else ''}{topic} youtube video"
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = None
    seen: set[str] = set()
    results: list[dict] = []
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(
            "https://www.google.com/search?q="
            + re.sub(r"[^\w\s]", "", query).replace(" ", "+")
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        html = driver.page_source
    except Exception as exc:
        logger.debug(f"[VideoDiscovery] Selenium dilewati: {exc}")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if len(results) >= limit:
            break
        href = _clean_url(a["href"])
        if not href or href in seen or not _looks_like_video_url(href):
            continue
        text = a.get_text(" ", strip=True) or "Untitled"
        seen.add(href)
        results.append(
            {
                "url": href,
                "title": text[:200],
                "duration": None,
                "source": "selenium-bs4",
                "channel": None,
                "thumbnail": None,
            }
        )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 6. AI pilih paling relevan + potensi penonton (LangChain, AGENT_*)
# ═══════════════════════════════════════════════════════════════════════════


def _ai_select_videos(
    topic: str,
    niche: str | None,
    candidates: list[dict],
    max_select: int,
) -> list[dict]:
    """Gunakan LLM untuk menilai relevansi & potensi viral, pilih terbaik."""
    if not candidates:
        return []

    max_select = max(MIN_VIDEOS, min(MAX_VIDEOS, int(max_select or MAX_VIDEOS)))
    if len(candidates) <= max_select:
        return candidates

    try:
        from langchain_core.output_parsers import JsonOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_text_model(temperature=0.3)
        parser = JsonOutputParser()

        lines = []
        for idx, v in enumerate(candidates):
            lines.append(
                f"{idx}. {v.get('title', 'Untitled')} | {v.get('url')} | "
                f"sumber: {v.get('source', '?')} | durasi: {v.get('duration') or '?'} detik"
            )
        candidates_text = "\n".join(lines)

        niche_line = f"\n- Niche: {niche}" if niche and niche.strip() else ""

        prompt = PromptTemplate.from_template(
            """Kamu adalah kurator konten viral TikTok/Reels/Shorts.
Topik/niche pengguna: "{topic}"{niche_line}.

Tugas: pilih {max_select} video dari daftar bawah ini yang
1. paling relevan dengan topik,
2. durasi >= 4 menit (240 detik),
3. berpotensi menonton banyak dan mengundang subscribe/follow.

Daftar video kandidat:
{candidates_text}

Kembalikan HANYA JSON array indeks (0-based) yang dipilih, urutkan dari yang
paling direkomendasikan. Contoh: [3, 0, 7]
Jangan tambahkan penjelasan lain."""
        ).partial(
            topic=topic,
            niche_line=niche_line,
            max_select=max_select,
            candidates_text=candidates_text,
        )

        chain = prompt | llm | parser
        chosen = chain.invoke({})
        if not isinstance(chosen, list):
            return candidates[:max_select]

        ordered: list[dict] = []
        for idx in chosen:
            if isinstance(idx, int) and 0 <= idx < len(candidates):
                ordered.append(candidates[idx])
            if len(ordered) >= max_select:
                break
        return ordered or candidates[:max_select]
    except Exception as exc:
        logger.warning(f"[VideoDiscovery] AI seleksi gagal, pakai urutan asli: {exc}")
        return candidates[:max_select]


# ═══════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA
# ═══════════════════════════════════════════════════════════════════════════


def discover_videos_for_topic(
    topic: str,
    niche: str | None = None,
    max_videos: int = 5,
    min_duration_seconds: int = 240,
    ai_select: bool = True,
) -> list[dict]:
    """
    Cari video yang relevan dengan topik dari banyak sumber, lalu AI memilih.

    Sumber (urutan dicoba):
      1. YouTube via yt-dlp (selalu, tanpa API key)
      2. Exa (opsional, EXA_API_KEY)
      3. Tavily (opsional, TAVILY_API_KEY)
      4. Firecrawl (opsional, FIRECRAWL_API_KEY)
      5. Selenium + BeautifulSoup (opsional, butuh browser driver)

    Parameter:
      topic              — topik/niche dari user (WAJIB, kalau kosong → ValueError)
      niche              — niche tambahan opsional
      max_videos         — jumlah video yang diinginkan (diklampirkan 2-10)
      min_duration_seconds — durasi minimum tiap video (default 240 = 4 menit)
      ai_select          — pakai AI untuk pilih paling relevan (default True)

    Return:
      list dict: [{"url", "title", "duration", "source", "channel", "thumbnail"}]
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Topic/niche wajib diisi.")

    max_videos = max(MIN_VIDEOS, min(MAX_VIDEOS, int(max_videos or 5)))

    # Kumpulkan dari semua sumber yang tersedia.
    candidates: list[dict] = []
    seen: set[str] = set()

    def _add(item: dict) -> None:
        url = item.get("url")
        if (
            url
            and url not in seen
            and _is_long_enough(item.get("duration"), min_duration_seconds)
        ):
            seen.add(url)
            candidates.append(item)

    for search_fn in (
        _search_youtube,
        _search_exa,
        _search_tavily,
        _search_firecrawl,
        _search_selenium_bs4,
    ):
        if len(candidates) >= max_videos * 3:
            break
        try:
            for item in search_fn(topic, niche, max_videos * 3):
                _add(item)
        except Exception as exc:
            logger.warning(f"[VideoDiscovery] {search_fn.__name__} error: {exc}")

    if not candidates:
        return []

    # AI pilih paling relevan + potensi penonton.
    if ai_select and len(candidates) > max_videos:
        return _ai_select_videos(topic, niche, candidates, max_videos)

    return candidates[:max_videos]
