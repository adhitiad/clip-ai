# Docker — stack lokal (RabbitMQ + PostgreSQL 19)

Stack **lokal saja** (tanpa deploy ke server/VPS). Terkait: [`RABBITMQ.md`](RABBITMQ.md), [`RUNBOOK.md`](RUNBOOK.md), [`TASKS.md`](TASKS.md).

## Service

| Service | Image | Port host |
| --- | --- | --- |
| `db` | `postgres:19.0-alpine3.24` | `${PG_PORT_HOST:-5433}` |
| `rabbitmq` | `rabbitmq:4-management-alpine` | `${RABBITMQ_PORT_HOST:-5672}`, UI `${RABBITMQ_UI_PORT_HOST:-15672}` |
| `api` | build dari `Dockerfile` | `${API_PORT_HOST:-8000}` |
| `worker` | build dari `Dockerfile` (Taskiq fallback, `--workers ${TASKIQ_WORKERS:-6}`) | — |
| `render-worker` | build dari `Dockerfile.render-worker` (antrean `shorts-render`) | — |
| `frontend` | build dari `frontend/Dockerfile` (Node + `srvx`) | `3000` |

**Redis & Celery sudah dihapus** — tidak ada service/volume/env lama lagi.

## Variabel penting

```powershell
RABBITMQ_URL=amqp://guest:guest@localhost:5672//
PG_PORT_HOST=5433
RABBITMQ_PORT_HOST=5672
RABBITMQ_UI_PORT_HOST=15672
```

Di dalam jaringan Docker, API/worker memakai `amqp://guest:guest@rabbitmq:5672//` (di-set di `docker-compose.yml`).

## Menjalankan

**Docker dijalankan pemilik repo** — agent tidak menjalankan/rebuild container.

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f api worker
```

Worker antrean utama (AMQP) berjalan sebagai service `render-worker` di compose. Untuk PC lain, pakai `docker-compose.worker.yml` + `.env.worker` (lihat [`RABBITMQ.md`](RABBITMQ.md)). Untuk debugging, entrypoint yang sama bisa dijalankan dari host:

```powershell
cd frontend
bun --bun run worker:render
```

## Volume

| Volume | Isi |
| --- | --- |
| `pgdata` | data PostgreSQL |
| `rabbitdata` | data RabbitMQ |
| `output` | MP4 + `manifest.json` |
| `temp` | file render sementara |
| `download` | video sumber dari auto-discover topic (gitignored & dockerignored) |

## Healthcheck

- DB: `pg_isready`
- RabbitMQ: `rabbitmq-diagnostics -q ping`
- API: `GET /health/live` lewat `scripts/container_health.py`
- Worker/render-worker: liveness proses lewat script yang sama
- Frontend: `GET /health/live` lewat healthcheck image

Semua image memakai user non-root (`app` untuk API/worker/render-worker,
`node` untuk frontend) dan folder runtime (`temp/`, `output/`, `download/`,
`logs/`) sudah di-chown saat build agar tetap bisa ditulis. `RABBITMQ_URL`
internal wajib diambil dari `RABBITMQ_URL_INTERNAL` di `.env`, tidak ada
kredensial hardcode di `docker-compose.yml`.
