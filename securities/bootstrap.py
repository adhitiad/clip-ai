"""Pasang semua scanner security ke securities/bin dan securities/uv-tools.

Jalankan dari root repo: uv run python securities/bootstrap.py
"""

from __future__ import annotations

import json
import platform
import shutil
import stat
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from lib.common import BIN_DIR, ROOT, SEC_ROOT, ensure_dirs, uv_tool_env

DOWNLOAD_DIR = SEC_ROOT / ".download"

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
SUFFIX = "exe" if IS_WINDOWS else ""


def target_name(name: str) -> str:
    return f"{name}.exe" if IS_WINDOWS else name


def asset_pattern(name: str) -> str:
    os_key = "windows" if IS_WINDOWS else ("linux" if SYSTEM == "Linux" else "darwin")
    patterns = {
        "trivy": {
            "windows": r"windows-64bit\.zip$",
            "linux": r"Linux-64bit\.tar\.gz$",
            "darwin": r"macOS-64bit\.tar\.gz$",
        },
        "gitleaks": {
            "windows": r"windows_x64\.zip$",
            "linux": r"linux_x64\.tar\.gz$",
            "darwin": r"darwin_x64\.tar\.gz$",
        },
        "betterleaks": {
            "windows": r"windows_x64\.zip$",
            "linux": r"linux_x64\.tar\.gz$",
            "darwin": r"darwin_x64\.tar\.gz$",
        },
        "osv-scanner": {
            "windows": r"windows_amd64\.exe$",
            "linux": r"linux_amd64$",
            "darwin": r"darwin_amd64$",
        },
        "hadolint": {
            "windows": r"windows-x86_64\.exe$",
            "linux": r"linux-x86_64$",
            "darwin": r"macos-x86_64$",
        },
        "nuclei": {
            "windows": r"windows_amd64\.zip$",
            "linux": r"linux_amd64\.zip$",
            "darwin": r"macOS_amd64\.zip$",
        },
    }
    # macOS assets sering memakai "macOS"/"darwin"; coba keduanya.
    if os_key == "darwin":
        return patterns[name].get("darwin", patterns[name]["darwin"])
    return patterns[name][os_key]


BINARY_TOOLS = {
    "trivy": "aquasecurity/trivy",
    "gitleaks": "gitleaks/gitleaks",
    "betterleaks": "betterleaks/betterleaks",
    "osv-scanner": "google/osv-scanner",
    "hadolint": "hadolint/hadolint",
    "nuclei": "projectdiscovery/nuclei",
}


def fetch_release(repo: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"User-Agent": "clip-ai-securities"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download(asset: dict[str, Any]) -> Path:
    target = DOWNLOAD_DIR / asset["name"]
    if target.is_file():
        return target
    request = urllib.request.Request(
        asset["browser_download_url"],
        headers={"User-Agent": "clip-ai-securities"},
    )
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        target.open("wb") as out,
    ):
        shutil.copyfileobj(response, out)
    return target


def install_binary(name: str, repo: str) -> None:
    destination = BIN_DIR / target_name(name)
    if destination.is_file():
        print(f"SKIP {name} — sudah ada")
        return

    import re

    release = fetch_release(repo)
    pattern = re.compile(asset_pattern(name), re.IGNORECASE)
    asset = next(
        (item for item in release["assets"] if pattern.search(item["name"])), None
    )
    if asset is None:
        raise SystemExit(
            f"Asset untuk {name} tidak ditemukan di {repo}: {release.get('tag_name')}"
        )

    archive = download(asset)
    if archive.suffix in {".zip", ".gz", ".tgz"}:
        extract_dir = DOWNLOAD_DIR / f"extract-{name}"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive) as tf:
                tf.extractall(extract_dir)
        candidates = [
            path
            for path in extract_dir.rglob("*")
            if path.is_file() and path.name in {name, f"{name}.exe"}
        ]
        if not candidates:
            raise SystemExit(f"Executable {name} tidak ada di arsip {archive.name}")
        shutil.copy2(candidates[0], destination)
    else:
        shutil.copy2(archive, destination)

    if not IS_WINDOWS:
        destination.chmod(destination.stat().st_mode | stat.S_IEXEC)
    print(f"OK {name} -> {destination}")


def main() -> int:
    ensure_dirs()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    for name, repo in BINARY_TOOLS.items():
        install_binary(name, repo)

    for tool in ("semgrep", "checkov"):
        print(f"Pasang {tool} via uv tool ke {BIN_DIR} ...")
        result = subprocess.run(
            ["uv", "tool", "install", tool],
            cwd=ROOT,
            env=uv_tool_env(),
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"Gagal memasang {tool} (exit {result.returncode})")

    print("\nSelesai. Isi securities/bin:")
    for path in sorted(BIN_DIR.iterdir()):
        if path.is_file():
            print(f"  {path.name} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
