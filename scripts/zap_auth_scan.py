"""ZAP scan terautentikasi terhadap instance SQLite terisolasi.

Scan #4: buktikan endpoint pribadi merespons setelah login, tanpa menyentuh
database asli. Alur:

1. buat `temp/zap_scan.db`, seed owner dari `OWNER_EMAILS`;
2. jalankan uvicorn lokal dengan `DATABASE_URL` SQLite tersebut;
3. ambil JWT lewat `POST /auth/bridge` (bukan password);
4. generate plan ZAP yang menyuntikkan `Authorization: Bearer ...`, memakai
   OpenAPI yang sudah difilter, dan menjalankan guard ASGI read-only;
5. jalankan ZAP, ringkas alert dari `zap-report-auth.json`.

Jalankan dari root repo: ``uv run python scripts/zap_auth_scan.py``.
Butuh Java + ZAP; override path JAR lewat ``ZAP_JAR``. Untuk CI tanpa ZAP lokal,
set ``ZAP_DOCKER=1`` supaya memakai image ``ghcr.io/zaproxy/zaproxy:stable``
(dengan Docker network host — cocok untuk runner Linux).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMP_DIR = ROOT / "temp"
DB_PATH = TEMP_DIR / "zap_scan.db"
PLAN_PATH = TEMP_DIR / "zap-scan-auth.yaml"
SERVER_LOG = TEMP_DIR / "zap-auth-server.log"
REPORT_MD = ROOT / "zap-report-auth.md"
REPORT_JSON = ROOT / "zap-report-auth.json"
ACCESS_LOG = TEMP_DIR / "zap-access.log"
BLOCK_LOG = TEMP_DIR / "zap-blocked.log"
SAFE_OPENAPI = TEMP_DIR / "zap-safe-openapi.json"
DEFAULT_ZAP_JAR = Path(r"C:\Program Files\ZAP\Zed Attack Proxy\zap-2.17.0.jar")
PORT = int(os.getenv("ZAP_SCAN_PORT", "8011"))
BASE_URL = f"http://127.0.0.1:{PORT}"
BASE_PATTERN = re.escape(BASE_URL)

# Hanya GET read-only: tanpa AI berbiaya, tanpa render, tanpa hapus data.
SAFE_PATHS = {
    "/auth/me",
    "/clips",
    "/clips/{clip_id}",
    "/ops/tasks",
    "/ops/queue",
    "/ops/workers",
    "/ops/cache",
    "/ops/traces",
    "/ops/export",
    "/ops/audit",
    "/settings/me",
    "/settings/owner",
    "/tasks/{task_id}",
    "/tools/providers",
    "/tools/platforms",
    "/tools/calibration",
    "/tools/model-status",
    "/dashboard/overview",
    "/dashboard/history",
    "/dashboard/profile",
    "/dashboard/stats",
    "/dashboard/health",
    "/youtube/scheduler/status",
}


def _owner_email() -> str:
    emails = [
        email.strip().lower()
        for email in os.getenv("OWNER_EMAILS", "").split(",")
        if email.strip()
    ]
    if not emails:
        raise SystemExit("OWNER_EMAILS kosong; isi satu email owner di .env.")
    return emails[0]


def _sqlite_url() -> str:
    return f"sqlite:///{DB_PATH.as_posix()}"


def seed_owner(email: str) -> None:
    """Buat tabel SQLite terisolasi + satu user owner (tanpa menyentuh DB asli)."""
    from backend.models.user import User
    from backend.utils.db import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == email).first():
            db.add(
                User(
                    email=email,
                    username=email.split("@")[0],
                    hashed_password="GOOGLE_OAUTH",
                    referral_code="ZAPSCAN01",
                )
            )
            db.commit()
    finally:
        db.close()


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["DATABASE_URL"] = _sqlite_url()
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "zap_safe_app:app",
            "--app-dir",
            "scripts",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdout=SERVER_LOG.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )


def wait_ready(process: subprocess.Popen, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit(
                f"Server berhenti (exit {process.returncode}); lihat {SERVER_LOG}."
            )
        try:
            response = httpx.get(f"{BASE_URL}/openapi.json", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise SystemExit(f"Server tidak siap dalam {timeout:.0f} detik.")


def bridge_token(email: str, bridge: str) -> str:
    response = httpx.post(
        f"{BASE_URL}/auth/bridge",
        json={"email": email, "bridge_token": bridge},
        timeout=10.0,
    )
    if response.status_code != 200:
        raise SystemExit(f"Bridge gagal ({response.status_code}): {response.text}")
    return response.json()["access_token"]


def check_auth(token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    paths = ("/auth/me", "/clips", "/ops/tasks", "/tools/providers", "/settings/me")
    for path in paths:
        status = httpx.get(f"{BASE_URL}{path}", headers=headers).status_code
        print(f"  login  {path:24} -> {status}")
        if status != 200:
            raise SystemExit(f"Endpoint login {path} mengembalikan {status}.")
    anonymous = httpx.get(f"{BASE_URL}/clips").status_code
    print(f"  anonim /clips                   -> {anonymous}")
    if anonymous not in (401, 403):
        raise SystemExit("Tanpa token seharusnya 401/403.")


def write_safe_openapi() -> None:
    """Spec OpenAPI hanya berisi GET read-only; mencegah import endpoint mahal."""
    source = ROOT / "docs" / "openapi.json"
    if not source.is_file():
        raise SystemExit("docs/openapi.json tidak ada; regenerate snapshot dulu.")
    spec = json.loads(source.read_text(encoding="utf-8"))
    paths = {
        path: {"get": operations["get"]}
        for path, operations in spec.get("paths", {}).items()
        if path in SAFE_PATHS and "get" in operations
    }
    missing = SAFE_PATHS - set(paths)
    if missing:
        raise SystemExit(f"Path aman tidak ada di OpenAPI: {sorted(missing)}")
    safe = {
        key: spec[key]
        for key in ("openapi", "info", "components", "security", "tags")
        if key in spec
    }
    safe["paths"] = paths
    SAFE_OPENAPI.write_text(json.dumps(safe, indent=2), encoding="utf-8")


def write_plan(token: str) -> None:
    # ZAP mem-resolve path relatif terhadap file plan, bukan cwd. Pakai absolut.
    if zap_docker_mode():
        api_file = "/zap/wrk/temp/zap-safe-openapi.json"
        report_md = "/zap/wrk/zap-report-auth.md"
        report_json = "/zap/wrk/zap-report-auth.json"
    else:
        api_file = str(SAFE_OPENAPI)
        report_md = str(REPORT_MD)
        report_json = str(REPORT_JSON)
    plan = f"""\
env:
  contexts:
    - name: clip-ai-auth
      urls:
        - {BASE_URL}
      includePaths:
        - '^{BASE_PATTERN}/.*$'
      excludePaths:
        - '^{BASE_PATTERN}/$'
  parameters:
    failOnError: true
    failOnWarning: false
    progressToStdout: true
    maxDuration: 900

jobs:
  - type: openapi
    parameters:
      apiFile: {api_file}
      context: clip-ai-auth
      targetUrl: {BASE_URL}

  - type: replacer
    parameters:
      deleteAllRules: false
    rules:
      - description: Bearer JWT
        url: ''
        matchType: req_header
        matchString: Authorization
        matchRegex: false
        replacementString: 'Bearer {token}'

  - type: activeScan
    parameters:
      context: clip-ai-auth
      maxScanDurationInMins: 10
      maxRuleDurationInMins: 2

  - type: passiveScan-wait
    parameters:
      maxDuration: 5

  - type: report
    parameters:
      template: traditional-md
      reportFile: {report_md}
      reportTitle: Clip AI - ZAP Scan (authenticated)

  - type: report
    parameters:
      template: traditional-json
      reportFile: {report_json}
      reportTitle: Clip AI - ZAP Scan (authenticated)
"""
    PLAN_PATH.write_text(plan, encoding="utf-8")


def zap_docker_mode() -> bool:
    return os.getenv("ZAP_DOCKER", "").strip().lower() in {"1", "true", "yes"}


def zap_jar() -> Path:
    override = os.getenv("ZAP_JAR", "").strip()
    jar = Path(override) if override else DEFAULT_ZAP_JAR
    if not jar.is_file():
        raise SystemExit(f"ZAP jar tidak ditemukan: {jar} (set ZAP_JAR).")
    return jar


def zap_command() -> list[str]:
    if zap_docker_mode():
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "-v",
            f"{ROOT}:/zap/wrk:rw",
            "-w",
            "/zap/wrk",
            "ghcr.io/zaproxy/zaproxy:stable",
            "zap.sh",
            "-cmd",
            "-autorun",
            str(PLAN_PATH.relative_to(ROOT)),
        ]
    return [
        "java",
        "-Xmx1g",
        "-jar",
        str(zap_jar()),
        "-cmd",
        "-autorun",
        str(PLAN_PATH),
    ]


def run_zap(token: str) -> None:
    result = subprocess.run(
        zap_command(),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    # ZAP mencetak nilai replacer (JWT) ke stdout — redaksi sebelum tampil.
    for stream in (result.stdout, result.stderr):
        safe = (
            (stream or "")
            .replace(f"Bearer {token}", "Bearer ***")
            .replace(token, "***")
            .strip()
        )
        if safe:
            print(safe[-1500:])
    # ZAP mengembalikan 2 saat ada warning meski laporan berhasil dibuat.
    if result.returncode not in (0, 2):
        raise SystemExit(f"ZAP gagal (exit {result.returncode}).")
    if not REPORT_JSON.is_file() or not REPORT_MD.is_file():
        raise SystemExit("ZAP selesai tetapi laporan tidak terbentuk.")


def summarize() -> dict:
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    sites = data.get("site", [])
    if isinstance(sites, dict):
        sites = [sites]
    risks = {"3": "High", "2": "Medium", "1": "Low", "0": "Info"}
    counts = {label: 0 for label in risks.values()}
    alerts = 0
    for site in sites:
        for alert in site.get("alerts", []):
            alerts += 1
            counts[risks.get(str(alert.get("riskcode", "0")), "Info")] += 1
    print(
        "ZAP selesai: "
        + ", ".join(f"{label}={value}" for label, value in counts.items())
        + f" (total {alerts} alert)"
    )
    print(f"  laporan: {REPORT_MD.name}, {REPORT_JSON.name}")
    return {"alerts": alerts, **counts}


def summarize_access_log() -> None:
    """Buktikan ZAP benar-benar login: hitung status 2xx vs 401/403."""
    if not ACCESS_LOG.exists():
        print("  access log: tidak ada (lewati).")
        return
    statuses: dict[str, int] = {}
    total = 0
    auth_failures = 0
    for line in ACCESS_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.rsplit(" ", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        total += 1
        status = parts[1]
        statuses[status] = statuses.get(status, 0) + 1
        if status in {"401", "403"}:
            auth_failures += 1
    print(
        f"  access log: {total} request, 401/403={auth_failures}, "
        f"status={dict(sorted(statuses.items()))}"
    )
    if total and auth_failures == total:
        raise SystemExit("Semua request ZAP ditolak; header Authorization gagal.")


def summarize_blocked() -> None:
    if not BLOCK_LOG.exists():
        print("  guard: 0 request diblokir.")
        return
    lines = [
        line for line in BLOCK_LOG.read_text(encoding="utf-8").splitlines() if line
    ]
    counts: dict[str, int] = {}
    for line in lines:
        counts[line] = counts.get(line, 0) + 1
    print(f"  guard: {len(lines)} request diblokir ({len(counts)} unik)")
    for line, count in sorted(counts.items(), key=lambda item: -item[1])[:5]:
        print(f"    {count}x {line}")


def main() -> int:
    from backend.core.env import load_env

    load_env("backend")
    email = _owner_email()
    bridge = os.getenv("AUTH_BRIDGE_TOKEN", "").strip()
    if not bridge:
        raise SystemExit("AUTH_BRIDGE_TOKEN kosong; isi di .env.")
    if not zap_docker_mode():
        zap_jar()

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    for path in (ACCESS_LOG, BLOCK_LOG):
        path.unlink(missing_ok=True)
    os.environ["DATABASE_URL"] = _sqlite_url()
    seed_owner(email)
    print(f"Isolated DB: {DB_PATH} (owner={email})")

    process = start_server()
    try:
        wait_ready(process)
        token = bridge_token(email, bridge)
        print("Auth bridge OK; cek endpoint read-only:")
        check_auth(token)
        write_safe_openapi()
        write_plan(token)
        print(f"Plan: {PLAN_PATH.name}; menjalankan ZAP...")
        run_zap(token)
        summarize()
        summarize_access_log()
        summarize_blocked()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
