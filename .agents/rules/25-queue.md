# Queue, Broker, dan Observability Rules (binding)

## RabbitMQ_ONLY

- **MUST** use RabbitMQ as the only broker/queue. **MUST NOT** add Redis again — no `redis` Python package, no `bullmq`/`ioredis` npm package, no `REDIS_*`/`UPSTASH_*`/`REDISCLOUD_*` env keys, no Redis service/volume in `docker-compose.yml`, and no `backend/core/redis_config.py`.
- **MUST** resolve broker config from `RABBITMQ_URL` via `backend/core/rabbitmq_config.py`. URL must start with `amqp://` or `amqps://`.
- **MUST** use AMQP queue `shorts-render` as the **primary** render queue through `frontend/src/server/queue.ts` (`amqplib`, durable, persistent message, `prefetch(1)`).
- **MUST** keep Taskiq as **fallback** only: broker `RABBITMQ_URL` (`AioPikaBroker`), task `process_all_clips_task`. Results persist in PostgreSQL `task_results` with in-memory cache (`backend/core/task_results.py`). Never reintroduce Redis or Celery.
- **MUST** run the AMQP worker on the host with `cd frontend && bun --bun run worker:render`. Docker operations remain owned by the user (`00-core.md`).
- **MUST** keep `GET /dashboard/health` reporting `health.rabbitmq.ok` (not `health.redis`).

## Render pipeline & idempotency

- **MUST** route every render through `backend/services/render_pipeline.py:render_clips` (Taskiq *and* `backend/scripts/render_job.py`). Do not call `process_clip` directly from new entrypoints.
- **MUST** use `backend/services/render_cache.py` for hash-based skip + `output/manifest.json`. Do not bypass the cache or write the manifest non-atomically.
- **MUST** bump `ENGINE_VERSION` when the video engine changes, so stale cache entries are invalidated.

## Content intelligence

- **MUST** attach content intelligence to every render job: `topic`, `brief`, `trend_terms`, and `viral_threshold` are part of the RabbitMQ payload.
- **MUST** call `backend/services/content_intelligence.py` from `backend/scripts/render_job.py` in order: `analyze_video` → `apply_brief_to_clips` → `score_clips` → `render_clips`, each inside its own `span`.
- **MUST** treat trend keywords as untrusted data: sanitize control characters and cap length before putting them in clip descriptions; never treat them as instructions.
- **MUST NOT** replace real video-derived timing with brief-only timing when `video_url` is present; use analysis as the timing source and the brief as copy.
- **MUST** update `tests/test_content_intelligence.py` and `tests/test_render_job.py` when intelligence behavior changes.

## Trace & logs

- **MUST** propagate W3C `traceparent` across API → RabbitMQ/Taskiq → worker → `render_job.py`. FastAPI middleware creates/echoes it; `X-Request-ID` (UUIDv7) is the business ID.
- **MUST** use `backend/core/telemetry.py` (Python) and `frontend/src/server/telemetry.ts` (TS) for `start_trace`/`span`/`log_event`. Do not invent a second trace implementation.
- **MUST** write structured JSON to `logs/trace.jsonl`; OTLP export is optional via `OTEL_EXPORTER_OTLP_ENDPOINT` and must stay best-effort (never block a job).
- **MUST NOT** log API keys, JWTs, `AUTH_BRIDGE_TOKEN`, full request bodies, or user emails in trace fields. `request_id`/`trace_id` are allowed.

## Tests & docs

- **MUST** update `tests/test_rabbitmq_config.py`, `tests/test_render_cache.py`, `tests/test_telemetry.py`, and `tests/test_render_job.py` when queue/cache/trace behavior changes.
- **MUST** update `docs/RABBITMQ.md` and `docs/OBSERVABILITY.md` in the same change as queue/broker/trace behavior.
- **MUST** keep `tests/test_docs_openapi_sync.py` green: `docs/openapi.json`, `docs/API.md`, and `.env.example` must match the live app; `REDIS_*` keys are forbidden in `.env.example`.
