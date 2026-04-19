"""
utils/exa_search.py
===================
Wrapper util untuk Exa Search SDK.
"""

import os
from typing import Any

from exa_py import Exa


def _read_attr(obj: Any, field: str, default: Any = None) -> Any:
    """Aman membaca field dari object SDK atau dict."""
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _read_any(obj: Any, fields: tuple[str, ...], default: Any = None) -> Any:
    """Ambil field pertama yang tersedia dari beberapa kandidat nama."""
    for field in fields:
        value = _read_attr(obj, field, None)
        if value is not None:
            return value
    return default


def search_news_with_exa(query: str, num_results: int = 10, search_type: str = "auto") -> list[dict]:
    """
    Cari berita/artikel web via Exa dan kembalikan format list yang konsisten.
    """
    api_key = os.getenv("EXA_API_KEY", "").strip()
    if not api_key:
        raise ValueError("EXA_API_KEY belum dikonfigurasi.")

    exa = Exa(api_key=api_key)
    response = exa.search(
        query,
        num_results=num_results,
        type=search_type,
        contents={"highlights": True},
    )

    raw_results = _read_attr(response, "results", []) or []
    normalized: list[dict] = []

    for item in raw_results:
        highlights = _read_attr(item, "highlights", []) or []
        normalized.append(
            {
                "title": _read_any(item, ("title",), ""),
                "url": _read_any(item, ("url", "id"), ""),
                "published_date": _read_any(item, ("published_date", "publishedDate")),
                "author": _read_attr(item, "author"),
                "highlights": highlights if isinstance(highlights, list) else [str(highlights)],
            }
        )

    return normalized
