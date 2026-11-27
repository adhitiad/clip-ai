"""Pendapatan platform (read-only): YouTube, TikTok, Meta Reels.

Tidak ada pembayaran, saldo, atau bookkeeping — hanya ringkasan dari API
platform. Adapter TikTok/Meta sengaja ``available=False`` karena API publik
mereka tidak mengekspos pendapatan creator; titik integrasinya disiapkan di
sini supaya mudah diisi bila API resmi tersedia.
"""

import os
from datetime import datetime, timedelta, timezone

import requests

from backend.core.models import RevenueSnapshot
from backend.log import logger
from backend.utils.youtube_token import load_token, valid_access_token

ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
MONETARY_SCOPE = "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"


def _period(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=max(7, days) - 1)
    return start.isoformat(), end.isoformat()


def _snapshot(
    platform: str,
    start: str,
    end: str,
    *,
    available: bool,
    status: str,
    amount: float | None,
    currency: str | None,
    source: str,
    note: str,
) -> RevenueSnapshot:
    return RevenueSnapshot(
        platform=platform,
        available=available,
        status=status,
        amount=amount,
        currency=currency,
        period_start=start,
        period_end=end,
        source=source,
        note=note,
    )


def youtube_revenue(days: int = 28) -> RevenueSnapshot:
    """Ambil `estimatedRevenue` channel via YouTube Analytics API v2."""
    start, end = _period(days)

    def skip(reason: str, note: str) -> RevenueSnapshot:
        return _snapshot(
            "youtube",
            start,
            end,
            available=False,
            status=reason,
            amount=None,
            currency=None,
            source="youtube-analytics/v2",
            note=note,
        )

    token_data = load_token()
    if not token_data:
        return skip(
            "oauth_belum_terhubung",
            "Token YouTube belum ada. Jalankan OAuth lalu setujui scope analytics-monetary.",
        )
    if MONETARY_SCOPE not in str(token_data.get("scope", "")):
        return skip(
            "scope_kurang",
            "Token lama belum punya scope yt-analytics-monetary.readonly. Ulangi OAuth.",
        )
    access = valid_access_token()
    if not access:
        return skip("token_tidak_valid", "Refresh token gagal; ulangi OAuth YouTube.")

    try:
        response = requests.get(
            ANALYTICS_URL,
            params={
                "ids": "channel==MINE",
                "startDate": start,
                "endDate": end,
                "metrics": "estimatedRevenue",
            },
            headers={"Authorization": f"Bearer {access}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.warning(f"[Revenue] YouTube request gagal: {type(exc).__name__}")
        return _snapshot(
            "youtube",
            start,
            end,
            available=False,
            status="network_error",
            amount=None,
            currency=None,
            source="youtube-analytics/v2",
            note="Gagal menghubungi YouTube Analytics.",
        )

    if response.status_code in (401, 403):
        return skip(
            "akses_ditolak",
            "Channel tidak mengizinkan data monetisasi (butuh channel monetized / content owner).",
        )
    if response.status_code == 400:
        return skip(
            "metrik_tidak_tersedia",
            "estimatedRevenue tidak tersedia untuk channel ini (biasanya bukan content owner).",
        )
    if response.status_code != 200:
        return skip("api_error", f"YouTube Analytics HTTP {response.status_code}.")

    try:
        rows = response.json().get("rows") or []
        amount = float(rows[0][0]) if rows and rows[0] else 0.0
    except ValueError, TypeError, IndexError:
        return skip("format_tidak_dikenal", "Respons Analytics tidak bisa dibaca.")
    return _snapshot(
        "youtube",
        start,
        end,
        available=True,
        status="ok",
        amount=round(amount, 2),
        currency="USD",
        source="youtube-analytics/v2",
        note="estimatedRevenue (USD) dari channel==MINE.",
    )


def tiktok_revenue(days: int = 28) -> RevenueSnapshot:
    """Placeholder: TikTok tidak punya API pendapatan creator publik."""
    start, end = _period(days)
    has_token = bool(os.getenv("TIKTOK_ACCESS_TOKEN", "").strip())
    return _snapshot(
        "tiktok",
        start,
        end,
        available=False,
        status="endpoint_tidak_tersedia" if has_token else "kredensial_kosong",
        amount=None,
        currency=None,
        source="tiktok-adapter",
        note=(
            "API publik TikTok tidak mengekspos pendapatan creator. "
            "Adapter ini siap diisi bila TikTok Business API menyediakan metrik pendapatan."
        ),
    )


def meta_reels_revenue(days: int = 28) -> RevenueSnapshot:
    """Placeholder: Graph API tidak mengekspos payout Reels."""
    start, end = _period(days)
    has_token = bool(os.getenv("META_ACCESS_TOKEN", "").strip())
    return _snapshot(
        "meta_reels",
        start,
        end,
        available=False,
        status="endpoint_tidak_tersedia" if has_token else "kredensial_kosong",
        amount=None,
        currency=None,
        source="meta-graph-adapter",
        note=(
            "Graph API tidak menyediakan metrik pendapatan Reels; "
            "payout hanya tersedia di Meta Business Suite. Adapter siap diperluas."
        ),
    )


ADAPTERS = {
    "youtube": youtube_revenue,
    "tiktok": tiktok_revenue,
    "meta_reels": meta_reels_revenue,
}


def collect_revenue(days: int = 28) -> list[RevenueSnapshot]:
    """Jalankan semua adapter; satu gagal tidak menggagalkan yang lain."""
    snapshots: list[RevenueSnapshot] = []
    for platform, adapter in ADAPTERS.items():
        try:
            snapshots.append(adapter(days))
        except Exception as exc:
            start, end = _period(days)
            snapshots.append(
                _snapshot(
                    platform,
                    start,
                    end,
                    available=False,
                    status="adapter_error",
                    amount=None,
                    currency=None,
                    source=f"{platform}-adapter",
                    note=f"Adapter gagal: {type(exc).__name__}.",
                )
            )
    return snapshots


def total_available(snapshots: list[RevenueSnapshot], currency: str = "USD") -> float:
    """Jumlahkan hanya snapshot tersedia dengan mata uang sama."""
    values = [
        snapshot.amount
        for snapshot in snapshots
        if snapshot.available
        and snapshot.currency == currency
        and snapshot.amount is not None
    ]
    return round(sum(values), 2)
