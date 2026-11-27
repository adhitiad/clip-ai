"""Baca token OAuth YouTube yang ditulis frontend (AES-256-GCM).

Token tidak pernah dikembalikan ke API/log. File asal:
``frontend/.data/youtube_tokens.json`` (gitignored), format sama dengan
``frontend/src/lib/youtube-token.ts``.
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path

import requests

from backend.core.env import load_env
from backend.log import logger

load_env("backend")

ROOT_DIR = Path(__file__).resolve().parents[2]
TOKEN_PATH = ROOT_DIR / "frontend" / ".data" / "youtube_tokens.json"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _secret() -> str:
    return os.getenv("YOUTUBE_TOKEN_ENCRYPTION_KEY", "").strip()


def load_token() -> dict | None:
    """Dekripsi token; return ``None`` bila tidak ada/timeout/rusak."""
    secret = _secret()
    if not secret or not TOKEN_PATH.is_file():
        return None
    try:
        payload = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
        encrypted = str(payload.get("encrypted", ""))
        iv_b64, tag_b64, data_b64 = encrypted.split(".")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = hashlib.sha256(secret.encode("utf-8")).digest()
        plain = AESGCM(key).decrypt(
            base64.b64decode(iv_b64),
            # Format frontend: iv.tag.encrypted; AESGCM Python butuh encrypted+tag.
            base64.b64decode(data_b64) + base64.b64decode(tag_b64),
            None,
        )
        token = json.loads(plain)
        return token if isinstance(token, dict) else None
    except Exception as exc:
        # Jangan sertakan isi token / secret di log.
        logger.warning(f"[YouTubeToken] Gagal membaca token: {type(exc).__name__}")
        return None


def valid_access_token() -> str | None:
    """Access token masih valid, atau refresh sekali (tanpa menulis file)."""
    token = load_token()
    if not token:
        return None
    access = str(token.get("access_token", "")).strip()
    if not access:
        return None

    expiry = token.get("expiry_date")
    if isinstance(expiry, (int, float)) and expiry > time.time() * 1000 + 60_000:
        return access

    refresh = str(token.get("refresh_token", "")).strip()
    client_id = os.getenv("YOUTUBE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET", "").strip()
    if not (refresh and client_id and client_secret):
        return access

    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        response.raise_for_status()
        return str(response.json().get("access_token", "")).strip() or None
    except requests.RequestException as exc:
        logger.warning(f"[YouTubeToken] Refresh gagal: {type(exc).__name__}")
        return None
