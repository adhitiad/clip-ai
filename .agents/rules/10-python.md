# Python Rules

## Environment and dependencies

- MUST use `uv run` (not the global interpreter) for every command.
- MUST add/remove dependencies with `uv add` / `uv remove`; the lockfile must be updated in the same change.
- MUST NOT add packages already unused by the code. Before adding, confirm the import actually exists.
- `backend/requirements.txt` and `workers/requirements.txt` are legacy. Do not edit them; edit `pyproject.toml`.

## Imports and layout

- MUST import with the full package path: `from backend.services...`, `from workers.worker...`.
- MUST NOT add `sys.path` hacks except in standalone scripts that already need them.
- MUST run entrypoints as modules from root: `uvicorn backend.main:app`, `python -m backend.scripts.<name>`, `taskiq worker workers.worker:broker`.
- MUST load env through `backend.core.env.load_env`: `load_env("backend")` for API/scripts, `load_env("workers")` for worker. Do not call `load_dotenv` directly in new code.

## Paths and runtime

- MUST use paths relative to the repo root only when the process is guaranteed to start there; otherwise resolve from `Path(__file__)`.
- MUST create runtime directories (`temp/`, `models/`, `output/`, `logs/`) before writing.
- MUST use the project logger (`backend.log.logger`), not `print`, in application code.
- MUST keep MediaPipe/FFmpeg/MoviePy imports out of Taskiq startup when possible; keep heavy imports inside tasks.
- MUST use `async def` for Taskiq tasks and offload blocking CPU/DB work with `await asyncio.to_thread(...)`; never call sync `render_clips` or DB sessions directly on the event loop.
- MUST use `async def` for endpoints that `await` Taskiq `.kiq()` (`/agent/shorts`, `/ops/render`). Endpoints with only sync SQLAlchemy work may stay `def` (FastAPI runs them in its threadpool).
- MUST choose worker count from physical cores via `backend/core/worker_count.py` (even, min 2); allow `TASKIQ_WORKERS` override. Keep UTF-8 console handling and no POSIX-only path separators.

## Database

- MUST import every new SQLAlchemy model in `backend/utils/db.py` so `init_db()` sees it.
- MUST use Alembic for schema changes (`uv run alembic upgrade head`); keep migrations idempotent and register new models in `backend/utils/db.py`.
- MUST NOT reintroduce roles, plans, credits, or billing. Personal mode is one Google user only.
- MUST use `SessionLocal`/`get_db` and close sessions. Do not create ad-hoc engines in routes.

## Quality gate

- MUST run, in order: `uv run ruff check ...`, `uv run ruff format --check ...`, `uv run python -m compileall -q ...`, `uv run pytest -q`, then `uv run python scripts/gate.py` (which also runs `docs/openapi sync`).
- MUST add or update a test when fixing a contract, parser, scoring rule, queue/cache, trace, or auth behavior.
- MUST run a single focused test first when iterating: `uv run pytest tests/test_file.py::test_name -q`.
- MUST NOT weaken lint rules, delete failing tests, or add blanket `# noqa` to make the gate pass.
