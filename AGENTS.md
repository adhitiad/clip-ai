# AGENTS.md — Clip AI

Compact operating guide for agents. **Read `.agents/rules/*.md` first; those rules are binding.** This file covers the non-obvious wiring; root/backend docs cover setup in prose.

## Non-negotiables

- Run every Python command from the **repo root** with **uv**. Python is pinned to **3.14.x** (`.python-version`, `requires-python`).
- `pyproject.toml` + `uv.lock` are the dependency source of truth. `backend/requirements.txt` is legacy; never edit or `pip install` it.
- Run `uv run python scripts/gate.py` before calling Python work done. Run the frontend gate from `frontend/` before calling frontend work done.
- **Docker is owned by the user.** DO NOT run `docker compose up/down/build/restart`, `docker build`, or `docker compose exec`. Edit Docker files only when asked, then tell the user to run them. Never claim container status you did not observe from the user.
- `frontend/` is a TanStack Start app managed with bun/bunx. Run frontend commands from `frontend/` with `bun`/`bunx`; never npm/pnpm/yarn or a TS gate in `scripts/gate.py`.
- Never commit `.env`, `models/*.pkl`, `temp/`, `output/`, `logs/`, media, or secrets.
- **RabbitMQ only**: no Redis/BullMQ/ioredis anywhere (`REDIS_*`, `UPSTASH_*`, `redis`, `bullmq`). `shorts-render` is the primary queue; Taskiq worker is fallback via `RABBITMQ_URL` + PostgreSQL `task_results`. See `.agents/rules/25-queue.md`.
- Propagate W3C `traceparent` API → queue → worker; never log secrets/tokens into `logs/trace.jsonl` or OTLP span fields.
- Do not weaken auth/lint/tests to make a check pass.

## Commands

| Task | Command (from root) |
| --- | --- |
| Install/sync | `uv sync` |
| API dev server | `uv run uvicorn backend.main:app --reload --port 8000` |
| Taskiq worker | `$w = uv run python scripts/worker_count.py; uv run taskiq worker workers.worker:broker --workers $w --ack-type when_saved` |
| Full Python gate | `uv run python scripts/gate.py` |
| All tests | `uv run pytest -q` |
| One test | `uv run pytest tests/test_file.py::test_name -q` |
| Seed demo users | `uv run python -m backend.scripts.seed_db --reset` |

Frontend commands run from `frontend/` (bun is the only package manager):

| Task | Command (from `frontend/`) |
| --- | --- |
| Install/sync | `bun install` |
| Dev server | `bun --bun run dev` (port 3000) |
| Build / regenerate routes | `bun --bun run build` / `bun --bun run generate-routes` |
| Typecheck | `bun --bun run typecheck` (`tsc --noEmit`) |
| Lint | `bun --bun run lint` (eslint) |
| Format check / write | `bun --bun run check` / `bun --bun run format` (prettier) |
| Unit tests | `bun --bun run test` (vitest) |
| E2E tests | `bun --bun run test:e2e` (playwright) |
| RabbitMQ render worker | `bun --bun run worker:render` (host, antrean `shorts-render`) |
| Intent skills | `bunx --no-install --package @tanstack/intent intent list` |

`scripts/worker_count.py` memilih jumlah worker genap dari inti fisik (1/2/4/6/8…); override via `TASKIQ_WORKERS`.

## Entrypoints and Layout

- API: `backend/main.py` → `backend.main:app`. Lifespan calls `init_db()`, `init_vector_store()`, checks RabbitMQ, creates `temp/`, `models/`, `output/`, `logs/`.
- Worker: `workers/worker.py` → `workers.worker:broker` (Taskiq). Single task `process_all_clips_task`; worker count from physical cores (`backend/core/worker_count.py`); heavy imports are intentionally inside the task.
- HTTP routers: `backend/routes/{auth,bridge,agent,clips,niche,tasks,tools,dashboard,ops,settings,youtube}.py` (tanpa `billing`).
- Shorts agent: `POST /agent/shorts` + UI `/shorts` → brief via `core/agent.py:plan_shorts`, opsional antre render via `workers.worker:process_all_clips_task`. Tanpa training model. UI memakai `AUTH_BRIDGE_TOKEN` (server-only) → `POST /auth/bridge` (hidden) untuk JWT backend. Setiap respons memakai `X-Request-ID` (UUIDv7) yang diteruskan ke worker.
- Core: `backend/core/{auth,security,ai_pipeline,env}.py`.
- Services: `backend/services/{viral_predictor,video_engine,dubbing,vector_store,model_discovery}.py`.
- Agent core: `backend/core/agent.py` (few-shot context + `agent_llm` LangChain discovery).
- Utils: `backend/utils/{db,youtube,rss_google,captioning,broll,exa_search,groq_ai,...}.py`.
- DB models: `backend/models/`. Scripts: `backend/scripts/`. Tests: `tests/`. Contract: `docs/API.md`.

## Critical Wiring Facts

### CWD and imports

- Imports are `backend.*` and `workers.*`; `python backend/main.py` fails. Use `uvicorn backend.main:app`.
- Runtime paths are relative to CWD: `temp/`, `output/`, `logs/`, `assets/`. Always start from root. Tidak ada direktori `models/` (tanpa artefak model).
- The old `from backend.worker import ...` path was broken; use `from workers.worker import process_all_clips_task`.

### Environment

- `backend/core/env.py` loads: **process env → component `.env` → root `.env`** (process wins).
- API/scripts: `load_env("backend")` reads `backend/.env` then root `.env`.
- Worker: `load_env("workers")` reads `workers/.env` then root `.env`.
- RabbitMQ: `backend/core/rabbitmq_config.py` resolves `RABBITMQ_URL` from `.env`; worker/API/dashboard use it. See `docs/RABBITMQ.md`.
- `SECRET_KEY` must be set and cannot be a known placeholder, or `backend.core.auth` raises at import.
- Three separate paths: **LLM** `services/model_discovery.py` (`AGENT_PROVIDER`/`AGENT_MODEL`), **TTS** `services/tts.py` (`TTS_PROVIDER`), **STT** `core/transcription.py` (`STT_PROVIDER`). Voice providers stay registered but are tagged `PROVIDER_KIND='tts'`; never call `init_chat_model()` for them. See `docs/VOICE.md`.
- All text AI goes through LangChain `get_text_model()` — no vendor hardcoding. Set `AGENT_PROVIDER` + `AGENT_MODEL` (openai, gemini, anthropic, openroute, cloudflare, grok, meta/muse, glm, minmax, kimi, deepseek, mistral, ollama, **nvidia/NIM**, dll) + that provider's key. Default: `nvidia` / `nvidia/nemotron-3.5-super-vl-120b-a12b` (gratis, `NVIDIA_API_KEY` nvapi-...). Interactive picker: `uv run python scripts/select_agent_model.py` (live search + select + manual `provider/model`, gratis didahulukan, saves to `.env`).
- Transcription is REST-based: **Camb AI batch STT (CAMB_API_KEY)** → OpenAI Whisper → Groq Whisper → VTT/manual. TTS: Cartesia → Camb AI → gTTS (never ElevenLabs). Pexels/Pinecone/Ollama keys only enable optional features; vector embeddings are local via Ollama.

### Database

- PostgreSQL via SQLAlchemy. **Alembic** manages schema changes (`uv run alembic upgrade head`, reads `DATABASE_URL` via `backend/core/env.py`); revision `0001_initial` creates all 7 tables and upgrade is idempotent.
- `init_db()` only calls `Base.metadata.create_all` for runtime — no ad-hoc `ALTER TABLE`/enum patching at runtime anymore.
- A new model **must be registered in `_import_models()` in `backend/utils/db.py`** so it appears in `Base.metadata` (used by both `create_all` and Alembic).
- Gate uses real PostgreSQL (`DATABASE_URL` from `GATE_DATABASE_URL`, default `clip_ai` local). Standalone pytest stays hermetic SQLite via `tests/conftest.py`. `backend/test_system.py` is a manual PostgreSQL smoke, not pytest.

### Auth (personal mode)

- **Personal project**: one user only. **Google-only auth** via `POST /auth/google` (`GOOGLE_CLIENT_ID`, whitelist `OWNER_EMAILS`) issuing an HS256 Bearer JWT. No passwords, roles, plans, credits, or billing. Never reintroduce `require_role`/`require_plan`/`check_credits`/`consume_credits_atomic`/`refund_credits_atomic`.
- Use `get_current_active_user` / `require_owner` only. Do not hand-roll role/plan/credit checks.
- All endpoints require login (Google JWT), including `POST /clips/feedback`.

### Viral scoring (no model)

- `backend/services/viral_predictor.py` is rule-based only: `rule_based_score()` returns 1–10. No `.pkl`, no training data, no `train_model`, no `RETRAIN_EVERY`.
- `predict_viral_score(..., threshold=...)` overrides the per-niche threshold; keep this contract when editing `/tools/viral-score`.
- Feature vector order is positional (10 values). If you add/reorder features, update `rule_based_score`, tests, and `/tools/viral-score` mapping together.
- `GET /tools/model-status` reports `enabled: false`; `POST /tools/feedback` is analytics-only. Tidak ada endpoint retrain.

### Rendering and external services

- FFmpeg/FFprobe must be on `PATH`. Video engine uses MoviePy 2 API (`with_start`, `with_duration`, `resized`, `cropped`, `with_audio`) plus MediaPipe/OpenCV layout detection.
- `output/` is required before rendering; lifespan creates it for API. Standalone render scripts must create it too.
- B-Roll needs Pexels; transcription uses Whisper via REST; dubbing uses Cartesia → Camb AI → gTTS; Exa needs `EXA_API_KEY`.
- RabbitMQ is the primary queue (`shorts-render`, `amqplib`) and Taskiq fallback broker (`RABBITMQ_URL`); task results persist in PostgreSQL `task_results` with in-memory cache. Broker/DB startup failures are logged, not fatal.

### Frontend

- `frontend/` is a TanStack Start app: React + Vite, file-based routing (`src/routes/`), bun/bunx as the only package manager. See `.agents/rules/40-frontend.md` and `frontend/AGENTS.md`.
- Server-only code lives in `createServerFn` / server routes; never leak secrets to the client via `VITE_`. Auth is Better Auth; env is T3Env; UI is Tailwind + shadcn/ui (mobile-first); i18n is Paraglide.
- `src/routeTree.gen.ts` and `src/paraglide/` are generated — do not hand-edit. Regenerate with `bun --bun run generate-routes` or a dev/build.
- Frontend gate (`bun --bun run lint`, `check`, `typecheck`, `test`, `test:e2e`, `build`) is separate from `scripts/gate.py`. Before substantial frontend edits, check Intent skills via `bunx --no-install --package @tanstack/intent intent list`.

## ID & UUID

- Semua ID/referral baru memakai `uuid.uuid7()` (stdlib di Python 3.14). Jangan pakai `uuid4` untuk kode baru.

## Gate Details

`scripts/gate.py` runs with dummy secrets but **real PostgreSQL**:

1. `ruff check backend workers scripts tests`
2. `ruff format --check backend workers scripts tests`
3. `compileall` on the same targets
4. `docs/openapi sync` (`tests/test_docs_openapi_sync.py`: snapshot OpenAPI, `docs/API.md`, `.env.example`)
5. PostgreSQL ping (`SELECT 1`) via `DATABASE_URL`
6. `pytest -q`
7. import `backend.main`
8. import `workers.worker`

Default `DATABASE_URL`: `postgresql://postgres:password@localhost:5432/clip_ai`. Override with `GATE_DATABASE_URL` (used by GitHub Actions `services.postgres`). Standalone pytest stays hermetic SQLite via `tests/conftest.py`. Config lives in `pyproject.toml`; never use real keys in gate.

## Docs Contract

- Any route/schema/auth/status-code change: update `docs/API.md` **and** the API table in `README.md`.
- Module/router changes: update `backend/README.md`. Worker behavior: `workers/README.md`. Queue/broker: `docs/RABBITMQ.md`. Trace/log/OTLP: `docs/OBSERVABILITY.md`.
- Do not document `pip install` as the primary path; setup is `uv sync` + `uv run`.
- State mocks/roadmap honestly: Stripe billing and auto-publish are not implemented. Alembic and Docker Compose exist; Docker execution is user-owned. CI/CD lives in `.github/workflows/` (see `docs/CI_CD.md`).
