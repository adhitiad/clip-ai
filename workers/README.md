# Taskiq Worker

Worker menjalankan render klip di luar proses FastAPI. Broker: `workers.worker:broker` (Taskiq + RabbitMQ); task: `process_all_clips_task`.

## Menjalankan

Dari **root repo**:

```powershell
uv sync
$w = uv run python scripts/worker_count.py; uv run taskiq worker workers.worker:broker --workers $w --ack-type when_saved
```

- Jumlah worker dihitung dari inti fisik (`scripts/worker_count.py`): 1/2/4/6/8…; override lewat `TASKIQ_WORKERS`.
- RabbitMQ adalah broker (`RABBITMQ_URL`); hasil task disimpan di PostgreSQL `task_results` + cache memori. Redis tidak dipakai.
- Env: process env → `workers/.env` → root `.env`. Worker mengimpor `backend.*`, jadi CWD harus root repo.
- FFmpeg/FFprobe harus ada di `PATH`; folder `temp/`, `output/`, dan `download/` dibuat oleh API/worker saat dipakai.

Antrean utama ada di RabbitMQ (`shorts-render`) yang diproses worker AMQP di `frontend/workers/render-worker.ts`. Taskiq di sini adalah **fallback** bila worker AMQP tidak tersedia.

Task menerima `video_url`, `clips_metadata`, `lang`, opsional `request_id`, `traceparent`, dan `mix_sources` (default `false`), lalu memanggil `backend.services.render_pipeline.render_clips`. Bila `mix_sources=true`, tiap klip dirender dari `clip["source_url"]` masing-masing lalu digabung jadi satu `output/MIX_*.mp4` via FFmpeg concat. Import berat sengaja dilakukan di dalam task untuk menghindari inisialisasi MediaPipe/MoviePy saat worker start.

Setiap klip juga menghasilkan thumbnail dari frame tengah ke `download/thumbnails/<judul>_<index>.jpg` (lewat `video_engine._generate_thumbnail`), disajikan API lewat `GET /download/*`.

## Render idempoten

Sebelum render, worker menghitung hash dari `(video_url, clips_metadata, lang, versi engine, provider LLM/TTS/STT)` lewat `backend/services/render_cache.py`. `clips_metadata` ikut disimpan di manifest sehingga cache hit tetap bisa mengembalikan `thumbnails`. Bila entri di `output/manifest.json` masih cocok dan semua file MP4 ada, task langsung return `cached: true` tanpa render ulang. Hasil render baru dicatat dengan metadata ffprobe (durasi, codec, resolusi, ukuran) secara atomik.

Invalidasi cache: hapus `output/manifest.json` (atau file MP4 yang bersangkutan), atau naikkan `ENGINE_VERSION` bila pipeline render berubah.
