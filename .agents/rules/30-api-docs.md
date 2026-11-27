# API and Documentation Rules

## Contract changes

- MUST update `docs/API.md` and the API table in `README.md` in the same change as any route, schema, auth dependency, or status-code change.
- MUST keep `backend/README.md` accurate for module/router changes.
- MUST update the `frontend/` consumer when a backend contract changes; `docs/API.md` is the shared contract between the Python API and the TanStack Start app.
- MUST NOT silently rename or remove a public endpoint. Add a new route and deprecate the old one unless the user approves a break.
- MUST use explicit Pydantic request/response models for new endpoints; avoid untyped `dict` payloads.
- MUST keep route prefixes and tags consistent with the existing routers.

## README accuracy

- MUST verify commands before documenting them. Do not copy stale commands from old docs.
- MUST document the actual entrypoints: `uvicorn backend.main:app`, `taskiq worker workers.worker:broker`, `python -m backend.scripts.*`.
- MUST document `frontend/` as a TanStack Start app managed with bun; do not imply it is absent or that npm/pnpm/yarn are used.
- MUST update `docs/CI_CD.md` when workflows, issue templates, or discussion templates change.
- MUST update `docs/RABBITMQ.md` and `.env.example` when RabbitMQ env handling changes.
- MUST keep setup instructions on `uv`; never document `pip install -r requirements.txt` as the primary path.
- MUST distinguish implemented behavior from mocks/roadmap (Stripe, publisher); the frontend is implemented, not a roadmap item.

## Model, data, and personal-mode docs

- MUST describe viral scoring as rule-based (`rule_based_score`, numpy/pandas, `@dataclass`); there is **no ML model, training, or `.pkl` artifact**. Do not document cold-start model training.
- MUST document personal mode: one Google user, no roles/plans/credits/billing. Alembic and Docker Compose exist; Docker execution is user-owned (`00-core.md`).
- MUST update `docs/OBSERVABILITY.md` when trace/log/OTLP behavior changes.
