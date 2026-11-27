# Observability — trace API → RabbitMQ → render

Trace memakai header W3C **`traceparent`** (`00-<trace_id>-<span_id>-01`) dan log JSON terstruktur. `X-Request-ID` (UUIDv7) tetap dipakai sebagai ID bisnis.

## Alur

1. FastAPI middleware (`backend/main.py`) membuat/merespons `traceparent` untuk tiap request dan mencatat `http.request`.
2. `POST /agent/shorts`, `/clips/generate-clips`, `/niche/analyze-and-queue` meneruskan `traceparent` ke task Taskiq (argumen terakhir `process_all_clips_task`).
3. Server fn `createShorts` meneruskan trace ke pesan RabbitMQ; worker AMQP melanjutkan span `rabbitmq.job.*` dan memanggil `backend/scripts/render_job.py` dengan env `TRACEPARENT`.
4. Fallback Taskiq melanjutkan span `taskiq.render`.
5. Worker RabbitMQ menambah span `content.video_analysis`, `content.plan_merge`, `content.viral_score`, lalu `rabbitmq.render` (lihat [`RABBITMQ.md`](RABBITMQ.md)).

## Export

- **Default (tanpa `MONGODB_URL`)**: `logs/trace.jsonl` + console worker. `logs/audit.jsonl` dipakai `backend/core/audit.py`.
- **Bila `MONGODB_URL` diset**: trace → koleksi `trace_logs`, audit → `audit_logs`, access log → `access_logs` + `known_ips`, hasil task → `task_results`, semuanya di database `MONGODB_DB`. File JSONL/PostgreSQL tetap dipakai sebagai fallback bila koneksi Mongo gagal. Endpoint `/ops/traces` dan `/ops/audit` membaca Mongo lebih dulu, lalu file.
- **Rotasi**: kedua file JSONL diputar berdasarkan ukuran oleh `backend/core/rotating_jsonl.py` → `trace.jsonl.1`, `.2`, … `.N`. Batas default 5 MiB dengan 3 backup; override lewat `LOG_MAX_BYTES` dan `LOG_BACKUPS`. Penulisan aman antar-thread.
- **Redaksi**: key yang mengandung `token`, `secret`, `password`, `api_key`, `authorization`, `credential`, atau `private_key` ditulis sebagai `***` (juga di dalam dict/list bersarang).
- **OTLP opsional**: set `OTEL_EXPORTER_OTLP_ENDPOINT` (mis. `http://localhost:4318`) → span dikirim ke `/v1/traces` (best-effort, timeout 1 detik).

Field log: `timestamp`, `event`, `trace_id`, `span_id`, `parent_span_id`, `request_id`, `span`, plus atribut (`provider`, `queue`, `cached`, `duration_ms`, dll).

## Modul

| Path | Peran |
| --- | --- |
| `backend/core/telemetry.py` | `start_trace`, `span`, `log_event`, OTLP exporter |
| `backend/core/rotating_jsonl.py` | Penulis JSONL dengan rotasi ukuran + redaksi secret |
| `frontend/src/server/telemetry.ts` | Versi TS untuk server fn & worker AMQP |
| `backend/scripts/render_job.py` | CLI render yang melanjutkan span dari `TRACEPARENT` |
| `backend/services/render_pipeline.py` | Pipeline render bersama (Taskiq + CLI) |

## Test

```powershell
uv run pytest tests/test_telemetry.py tests/test_log_rotation.py tests/test_render_job.py -q
```

## Catatan

- Karena project pribadi satu user, trace **tidak mengandung data sensitif** (tidak ada API key/JWT yang dicatat).
- File `logs/` gitignored.
