"""Access logger per-request ke MongoDB (Atlas/eksternal, via MONGODB_URL).

Mencatat identitas: ip, email, jenis user, device id/name, browser, TCP, HTTP
version, method, path, status, user-agent. Klasifikasi heuristik transparan:

- ``user``    ✅ — JWT valid / email terdaftar di OWNER_EMAILS.
- ``**``      ⚠️ — anonim, request sukses, IP dikenal.
- ``**``      ✅ — anonim, endpoint publik sehat (health/docs).
- ``hacker``  ❌ — IP asing DAN auth gagal / user-agent mencurigakan.
- ``user``    ❌ — user dikenal tapi ada anomali (auth gagal setelah sukses).
- ``error``   🛑 — status >= 500 (server error).

Tidak pernah menyimpan token/JWT/secret — hanya hash 8 karakter untuk
korelasi. Koneksi Mongo gagal → fungsi diam (access log tidak menggagalkan API).
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from datetime import datetime, timezone

from backend.core.mongo import collection as mongo_collection
from backend.core.mongo import enabled as mongo_enabled

COLLECTION = "access_logs"
KNOWN_IPS = "known_ips"

# In-memory failure counter per IP untuk heuristik (dijaga agar ringan).
_fail_counts: dict[str, list[float]] = {}
_fail_lock = threading.Lock()
FAIL_WINDOW_SECONDS = 300
FAIL_THRESHOLD = 3

PUBLIC_PATHS = {"/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json"}
SUSPICIOUS_UA = re.compile(
    r"sqlmap|nikto|nmap|masscan|acunetix|nessus|zgrab|scanner|python-requests|"
    r"curl|wget|go-http-client|httpie|postmanruntime",
    re.IGNORECASE,
)


def _get_collection(name: str):
    return mongo_collection(name)


def is_enabled() -> bool:
    return mongo_enabled()


def _sha(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:8]


def _client_ip(request) -> str:
    """IP klien: utamakan x-forwarded-for yang sudah di-inject server."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return getattr(getattr(request, "client", None), "host", "") or ""


def _parse_user_agent(ua: str, device_id: str = "") -> tuple[str, str, str]:
    """Return (browser, device_name, device_id_hash)."""
    browser = "unknown"
    patterns = [
        (r"Edg/[\d.]+", "Edge"),
        (r"OPR/[\d.]+", "Opera"),
        (r"Firefox/[\d.]+", "Firefox"),
        (r"Chrome/[\d.]+", "Chrome"),
        (r"Safari/[\d.]+", "Safari"),
    ]
    for pattern, name in patterns:
        if re.search(pattern, ua, re.IGNORECASE):
            browser = name
            break

    device = "desktop"
    if re.search(r"iPhone|iPad|Android|Mobile", ua, re.IGNORECASE):
        device = "mobile"
    if "Windows" in ua:
        device_name = "Windows"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        device_name = "macOS"
    elif "Linux" in ua:
        device_name = "Linux"
    elif "Android" in ua:
        device_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        device_name = "iOS"
    else:
        device_name = device

    return browser, device_name, _sha(device_id or ua)


def _decode_identity(request) -> tuple[str, str]:
    """Decode JWT Bearer tanpa memvalidasi expire ketat (audit only)."""
    auth = request.headers.get("authorization", "").strip()
    if not auth.lower().startswith("bearer "):
        return "", ""
    token = auth[7:].strip()
    if not token:
        return "", ""
    try:
        import jwt

        secret = os.getenv("SECRET_KEY", "").strip()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        email = str(payload.get("sub") or payload.get("email") or "").strip()
        return email, _sha(token)
    except Exception:
        return "", _sha(token)


def _is_known_ip(ip: str) -> bool:
    coll = _get_collection(KNOWN_IPS)
    if coll is None or not ip:
        return False
    try:
        return coll.find_one({"ip": ip}) is not None
    except Exception:
        return False


def _mark_known_ip(ip: str, email: str) -> None:
    coll = _get_collection(KNOWN_IPS)
    if coll is None or not ip:
        return
    try:
        coll.update_one(
            {"ip": ip},
            {
                "$set": {
                    "ip": ip,
                    "email": email,
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                },
                "$inc": {"seen": 1},
            },
            upsert=True,
        )
    except Exception:
        pass


def _record_failure(ip: str) -> int:
    now = time.time()
    with _fail_lock:
        times = [t for t in _fail_counts.get(ip, []) if now - t < FAIL_WINDOW_SECONDS]
        times.append(now)
        _fail_counts[ip] = times
        return len(times)


def _classify(
    request,
    status: int,
    email: str,
    ip: str,
    ua: str,
) -> tuple[str, str, str]:
    """Return (level, actor, flag).

    level: info | error
    actor: user | ** | hacker | error
    flag: ✅ | ⚠️ | ❌ | 🛑
    """
    if status >= 500:
        return "error", "**", "🛑"

    known = _is_known_ip(ip)
    suspicious_ua = bool(SUSPICIOUS_UA.search(ua or ""))
    auth_failed = status in (401, 403) or (
        request.url.path in ("/auth/google", "/auth/bridge") and status >= 400
    )
    failures = _record_failure(ip) if auth_failed else 0

    if email:
        _mark_known_ip(ip, email)
        if auth_failed or failures >= FAIL_THRESHOLD:
            return "info", "user", "❌"
        return "info", "user", "✅"

    if auth_failed and (not known or suspicious_ua or failures >= FAIL_THRESHOLD):
        return "info", "hacker", "❌"

    if request.url.path in PUBLIC_PATHS and status < 400:
        return "info", "**", "✅"

    if known and status < 400:
        return "info", "**", "⚠️"

    return "info", "**", "⚠️"


def log_request(request, response, traceparent: str = "", request_id: str = "") -> dict:
    """Catat satu request. Dipanggil middleware; gagal Mongo tidak melempar."""
    ip = _client_ip(request)
    ua = request.headers.get("user-agent", "")
    email, token_hash = _decode_identity(request)
    device_id = request.headers.get("x-device-id", "").strip()
    browser, device_name, device_hash = _parse_user_agent(ua, device_id)
    level, actor, flag = _classify(request, response.status_code, email, ip, ua)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "actor": actor,
        "flag": flag,
        "ip": ip,
        "email": email,
        "user_type": "owner" if email else "anonymous",
        "device_id": device_hash,
        "device_name": device_name,
        "browser": browser,
        "http_version": request.scope.get("http_version", "1.1"),
        "scheme": request.url.scheme,
        "tcp": {
            "client_host": ip,
            "client_port": getattr(getattr(request, "client", None), "port", None),
            "server_host": request.url.hostname,
            "server_port": request.url.port,
        },
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "user_agent": ua[:500],
        "request_id": request_id,
        "traceparent": traceparent,
        "token_hash": token_hash,
    }

    coll = _get_collection(COLLECTION)
    if coll is not None:
        try:
            coll.insert_one(record)
        except Exception:
            pass

    return record


def read_logs(limit: int = 100, only_flagged: bool = False) -> list[dict]:
    """Baca log terbaru dari Mongo untuk endpoint /ops/access-log."""
    coll = _get_collection(COLLECTION)
    if coll is None:
        return []
    query: dict = {}
    if only_flagged:
        query = {"flag": {"$in": ["❌", "🛑", "⚠️"]}}
    try:
        cursor = coll.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception:
        return []


def format_line(record: dict) -> str:
    """Format baris sesuai permintaan: level - actor - tgl jam - keterangan - flag."""
    ts = record.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        tanggal = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        tanggal = ts
    keterangan = (
        f"{record.get('method', '')} {record.get('path', '')} "
        f"{record.get('status', '')} ip={record.get('ip', '')} "
        f"browser={record.get('browser', '')} http={record.get('http_version', '')}"
    )
    return (
        f"{record.get('level', 'info')} - {record.get('actor', '**')} - "
        f"{tanggal} - {keterangan} - flag {record.get('flag', '⚠️')}"
    )
