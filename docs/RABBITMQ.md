# RabbitMQ — broker & antrean (tanpa Redis)

RabbitMQ menggantikan peran Redis sepenuhnya:

- **Primary queue**: antrean `shorts-render` dipakai worker frontend (`frontend/workers/render-worker.ts`, AMQP via `amqplib`).
- **Fallback**: worker Taskiq memakai broker AMQP yang sama; hasil disimpan di tabel PostgreSQL `task_results` + cache memori.

## Konfigurasi

| Env | Default | Dipakai |
| --- | --- | --- |
| `RABBITMQ_URL` | `amqp://clipai:<password>@IP_BROKER:5672/clip-ai` | proses di host (dev/test), bukan container; isi `IP_BROKER` dengan IP LAN mesin broker |
| `RABBITMQ_URL_INTERNAL` | `amqp://clipai:clipai@rabbitmq:5672/clip-ai` | api, worker, render-worker, frontend (jaringan Docker) |
| `RABBITMQ_USER` | `clipai` | user broker yang dibuat Compose (bukan `guest`) |
| `RABBITMQ_PASSWORD` | wajib diisi | password user broker, harus URL-safe |
| `RABBITMQ_VHOST` | `clip-ai` | vhost khusus aplikasi |
| `RABBITMQ_BIND_IP` | `127.0.0.1` | IP yang boleh mendengar AMQP (5672) |
| `RABBITMQ_UI_BIND_IP` | `127.0.0.1` | IP yang boleh membuka management UI (15672) |

Resolver Python: `backend/core/rabbitmq_config.py`. URL wajib diawali `amqp://` atau `amqps://`. `guest` sengaja tidak dipakai untuk antar-PC; hanya fallback lokal.

```powershell
uv run python -c "from backend.core.rabbitmq_config import get_rabbitmq_settings, check_connection; s=get_rabbitmq_settings(); print(s.masked_url(), check_connection())"
```

## Docker

`docker-compose.yml` menyediakan service `rabbitmq` (`rabbitmq:4-management-alpine`):

- AMQP: `RABBITMQ_BIND_IP:RABBITMQ_PORT_HOST -> 5672`
- Management UI: `RABBITMQ_UI_BIND_IP:RABBITMQ_UI_PORT_HOST -> 15672`
- User/vhost default dibuat dari `RABBITMQ_USER` / `RABBITMQ_PASSWORD` / `RABBITMQ_VHOST`
- Healthcheck: `rabbitmq-diagnostics -q ping`

Keduanya **default terikat ke `127.0.0.1`**, jadi tidak terlihat dari jaringan. Bila worker di PC lain, ubah `RABBITMQ_BIND_IP` ke IP LAN mesin broker (mis. `192.168.1.10`); biarkan `RABBITMQ_UI_BIND_IP=127.0.0.1` karena UI tidak perlu diakses jarak jauh.

Saat ini `RABBITMQ_URL` di `.env` dan `frontend/.env.local` menunjuk ke `10.10.8.160:5672/clip-ai` dengan user `clipai` (IP aktif di `Ethernet 2`, gateway `10.10.0.1`; `192.168.100.3` adalah adapter yang **Media disconnected**). `RABBITMQ_BIND_IP=10.10.8.160` sudah diterapkan dan container `rabbitmq` di-recreate; port `5672` di IP tersebut sudah terbuka. Management UI tetap `127.0.0.1:15672`. Container api/worker/frontend tidak terpengaruh karena Compose menimpa `RABBITMQ_URL` dengan host `rabbitmq` di jaringan internal.

User worker least-privilege sudah dibuat, masing-masing hanya boleh `configure/write/read` pada `^shorts-render.*$` di vhost `clip-ai` (tanpa tag management):

| User | File env untuk PC tujuan |
| --- | --- |
| `worker_kantor1` | `.env.worker.kantor1` |
| `worker_kantor2` | `.env.worker.kantor2` |
| `worker_rumah` | `.env.worker.rumah` |

Salin file yang sesuai ke PC tujuan sebagai `.env.worker`, lalu jalankan `docker compose -f docker-compose.worker.yml up -d --build`. File `.env.worker.*` gitignored — jangan commit. Connectivity dari file worker sudah diverifikasi: `check_connection() -> ok: True`.

**Docker dijalankan pemilik repo** — agent tidak menjalankan/rebuild container.

## Antrean `shorts-render`

- Message: `{video_url, topic, platform, clips, brief, trend_terms, lang, request_id, traceparent}`, `persistent: true`.
- Worker: `prefetch(1)`, ack setelah render sukses, `nack(..., false, false)` saat gagal (tanpa retry tak hingga).
- **Retry bounded**: `SmartRetryMiddleware` — maksimal **2 retry**, delay 3 detik + jitter + backoff eksponensial (maks 30 detik). Task id tetap sama; `attempts` tercatat di `task_results`.
- **Dead-letter queue**: `shorts-render-dlq` (durable) menampung task yang gagal setelah retry habis; lihat `GET /ops/queue`.
- Render dijalankan via `uv run python backend/scripts/render_job.py` (payload JSON dari stdin, hasil JSON ke stdout).
- **Intelegensi konten** (`backend/services/content_intelligence.py`) dijalankan worker sebelum render:
  1. `content.video_analysis` — transkrip/audio + LLM menghasilkan timing klip asli dari `video_url`.
  2. `content.plan_merge` — copy brief (hook/judul/caption/hashtag) + `trend_terms` digabung ke klip.
  3. `content.viral_score` — `predict_viral_score` rule-based dilampirkan per klip.
  4. `rabbitmq.render` — render akhir via `render_pipeline.py`.
- Idempoten: `backend/services/render_cache.py` melewati render bila hash input sama & file masih ada.

## Fallback

Bila RabbitMQ tidak tersedia saat `createShorts`, server fn otomatis memanggil `POST /agent/shorts` dengan `render_video=true` agar Taskiq yang mengantre. UI menampilkan `queue: "taskiq"` pada respons.

Render **multi-sumber** (>1 `video_urls`) selalu memakai Taskiq: tiap klip dianalisis dari videonya masing-masing, lalu `render_pipeline.py` menggabungkan bagian-bagian itu menjadi satu MP4 (`output/MIX_*.mp4`). Antrean AMQP tetap untuk satu video sumber.

## Topologi multi-PC (broker pusat, worker portabel)

Satu broker RabbitMQ di satu PC menjadi pusat. Worker di PC lain hanya butuh
`RABBITMQ_URL` + image `Dockerfile.render-worker`; tidak perlu Postgres, API, atau frontend.

```mermaid
sequenceDiagram
    participant UI as TanStack Start (Bun)
    participant API as Backend FastAPI
    participant MQ as RabbitMQ shorts-render
    participant R1 as Worker kantor PC-1
    participant R2 as Worker kantor PC-2
    participant R3 as Worker rumah

    UI->>API: POST /agent/shorts {render_video:true}
    API->>MQ: publish job (persistent, request_id, traceparent)
    MQ-->>R1: job A (prefetch 1)
    MQ-->>R2: job B
    MQ-->>R3: job C
    R1->>R1: analisis + skor + render
    R2->>R2: render job B
    R3->>R3: render job C
    R1-->>MQ: ack / nack
    UI->>API: GET /tasks/{task_id} untuk progres
    API-->>UI: status + progress
```

### 1. PC broker (pusat)

```powershell
# .env di PC broker
RABBITMQ_BIND_IP=192.168.1.10        # IP LAN PC broker; JANGAN 0.0.0.0
RABBITMQ_UI_BIND_IP=127.0.0.1        # UI tidak perlu diakses jarak jauh
RABBITMQ_USER=clipai
RABBITMQ_PASSWORD=<password-acak-url-safe-32+>
RABBITMQ_VHOST=clip-ai
RABBITMQ_URL_INTERNAL=amqp://clipai:<password>@rabbitmq:5672/clip-ai
```

Lalu di PC broker:

```powershell
docker compose up -d --build rabbitmq
```

Jika broker lama masih punya job tertunda di vhost `/`, habiskan/purge sebelum
berpindah ke `clip-ai` (job lama tidak otomatis dipindah):

```powershell
docker compose exec rabbitmq rabbitmqctl purge_queue -p / shorts-render
```

Pastikan vhost/user ada (aman dijalankan walau sudah dibuat entrypoint):

```powershell
docker compose exec rabbitmq rabbitmqctl add_vhost clip-ai
docker compose exec rabbitmq rabbitmqctl set_permissions -p clip-ai clipai ".*" ".*" ".*"
```

Buat **satu user per lokasi** dengan hak least-privilege (hanya queue render):

```powershell
docker compose exec rabbitmq rabbitmqctl add_user worker_kantor1 <password-unik>
docker compose exec rabbitmq rabbitmqctl set_permissions -p clip-ai worker_kantor1 "^shorts-render.*$" "^shorts-render.*$" "^shorts-render.*$"
docker compose exec rabbitmq rabbitmqctl set_user_tags worker_kantor1 management
```

Artinya: user itu hanya boleh `configure/write/read` resource yang namanya diawali
`shorts-render`. Ia tidak bisa membuat vhost, user, atau queue lain. Ulangi dengan
nama user berbeda untuk PC-2 dan PC rumah.

Firewall (router/Windows): izinkan **TCP 5672 hanya dari IP worker yang kamu daftarkan**.
Management UI `15672` tetap terikat `127.0.0.1`. Jangan pernah memakai `guest` untuk
koneksi lintas PC — user itu hanya untuk loopback.

### 2. PC worker (boleh dipindah-pindah)

```powershell
Copy-Item .env.worker.example .env.worker
# isi: RABBITMQ_URL=amqp://worker_kantor1:<password>@192.168.1.10:5672/clip-ai
docker compose -f docker-compose.worker.yml up -d --build
```

`docker-compose.worker.yml` hanya menjalankan `render-worker` dengan volume lokal
`output/` dan `temp/`. Untuk memindahkan worker, cukup salin repo + `.env.worker`
ke PC baru, isi ulang IP/password bila perlu, lalu jalankan perintah yang sama.
Tidak ada IP atau kredensial yang di-hardcode di kode.

Verifikasi dari PC worker:

```powershell
docker compose -f docker-compose.worker.yml logs render-worker
# harus muncul: RabbitMQ render worker siap (shorts-render)
```

### 3. Fallback Taskiq (opsional)

Bila ingin fallback di mesin lain, jalankan worker Taskiq dengan url yang sama.
Worker ini menulis hasil ke Postgres, jadi PC tersebut juga butuh `DATABASE_URL`
yang boleh diakses dari jaringan (sebaiknya tetap di PC broker/API).

```powershell
$w = uv run python scripts/worker_count.py
$env:RABBITMQ_URL = 'amqp://worker_kantor1:<password>@192.168.1.10:5672/clip-ai'
uv run taskiq worker workers.worker:broker --workers $w --ack-type when_saved
```

### 4. Performa & kapasitas

- `prefetch(1)` membuat tiap worker mengambil **satu job** sekali jadi; menambah PC
  menaikkan throughput render secara linier sampai broker/CPU/video source jadi bottleneck.
- Render adalah beban CPU + FFmpeg heavy. Gunakan 1 worker per PC kecuali PC punya
  banyak core fisik; jumlah worker Taskiq dihitung otomatis oleh `scripts/worker_count.py`.
- Pantau kedalaman antrean dan DLQ lewat `GET /ops/queue`; bila antrean menumpuk,
  tambahkan worker, bukan menaikkan `prefetch`.
- Pesan `persistent: true` dan queue `durable`, jadi job tidak hilang saat worker PC mati.

`GET /tasks/{task_id}` saat ini diisi oleh result backend Taskiq. Untuk jalur RabbitMQ langsung, hasil render tercatat di log trace dan ack antrean. Penulisan hasil `shorts-render` ke `task_results` bisa ditambahkan sebagai perbaikan berikutnya.

## Test

```powershell
uv run pytest tests/test_rabbitmq_config.py tests/test_render_cache.py tests/test_task_results.py -q
cd frontend && bun --bun run test:e2e
cd frontend && bun --bun run test:a11y
```
