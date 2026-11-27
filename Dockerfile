# Clip AI — API + Worker image
FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.11 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/tmp/uv-cache \
    HOME=/app \
    PYTHONUNBUFFERED=1

# mediapipe menarik opencv-contrib-python yang butuh library GUI/X11.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libxcb1 libxext6 libgl1 libglib2.0-0 libsm6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependensi dari lockfile (cache lebih baik dengan copy dulu).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Fallback: pastikan sinkron jika ada perubahan source setelah layer cache.
RUN uv sync --frozen --no-dev

# Non-root user untuk CKV_DOCKER_3. Folder runtime harus bisa ditulis.
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p temp output logs download /tmp/uv-cache \
    && chown -R app:app /app /tmp/uv-cache
USER 100:101

COPY scripts/container_health.py /app/scripts/container_health.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "/app/scripts/container_health.py"]

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
