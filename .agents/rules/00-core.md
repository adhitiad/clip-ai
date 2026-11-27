# Core Rules (binding)

These rules override convenience and default agent habits. Read `AGENTS.md` and every file in `.agents/rules/` before editing. If two rules conflict, follow the stricter one and mention the conflict.

## Working directory

- MUST run Python, uv, Taskiq, scripts, and tests from the repository root.
- MUST NOT `cd backend` or `cd workers` to run the app. Imports are `backend.*` / `workers.*` and many paths are CWD-relative.
- MUST run frontend commands from `frontend/` with `bun`/`bunx` (see `40-frontend.md`); MUST NOT use npm/pnpm/yarn there. The Python gate does not include the frontend.

## Toolchain

- MUST use `uv` for every Python install/run: `uv sync`, `uv run ...`, `uv add ...`.
- MUST keep `pyproject.toml` + `uv.lock` as the dependency source of truth. Do not run `pip`, `poetry`, or `conda`.
- MUST use Python 3.14.x as pinned by `.python-version` and `requires-python`. Do not relax to 3.11/3.12.
- MUST use `bun`/`bunx` for frontend commands; `frontend/bun.lock` is the frontend dependency source of truth. Do not run `npm`, `npx`, `pnpm`, or `yarn`.
- MUST run `uv run python scripts/gate.py` before declaring Python work complete.
- MUST run the frontend gate from `frontend/` (`bun --bun run lint`, `check`, `typecheck`, `test`, `test:e2e`, `build`) before declaring frontend work complete.
- MUST NOT add Redis or BullMQ to the stack. RabbitMQ is the only broker (`25-queue.md`).
- MUST NOT run, rebuild, start, stop, or recreate Docker containers (`docker compose up/down/build/restart`, `docker compose exec`, `docker build`). **The user owns Docker operations.** Edit `Dockerfile`/`docker-compose.yml` when needed, then tell the user to run them.
- MUST NOT claim a container is healthy/running unless the user reports it. Report code/gate results only.

## Scope and safety

- MUST keep changes scoped to the request. Do not refactor unrelated modules, rename public routes, or reformat the whole repo.
- MUST NOT delete or overwrite user changes, generated media, or uncommitted work without explicit confirmation.
- MUST NOT commit `.env`, API keys, `models/*.pkl`, `temp/`, `output/`, `logs/`, or media files.
- MUST update documentation when behavior or contracts change (see `30-api-docs.md`).
- MUST report commands run and any check that could not run. Never claim a gate passed without output.
