# Security Rules — Project Pribadi

## Secrets
- MUST keep `.env` untracked. `.env.example` may contain placeholders only.
- MUST reject missing/placeholder `SECRET_KEY`; never add a fallback secret.
- MUST NOT log API keys, JWTs, `AUTH_BRIDGE_TOKEN`, or full request bodies containing them — including `logs/trace.jsonl` and OTLP span attributes. Trace fields are limited to IDs and non-sensitive metadata.
- MUST NOT paste real keys into chat or docs; fill them directly in `.env`.

## Auth (Google-only, satu user)
- MUST use `get_current_active_user` / `require_owner` only. There are **no** roles, plans, or credits.
- MUST verify Google ID token with `GOOGLE_CLIENT_ID` and restrict email to `OWNER_EMAILS`.
- MUST NOT reintroduce `/auth/token`, `/auth/register`, passwords, `require_role`, `require_plan`, `check_credits`, or credit mutation helpers.
- All endpoints require login, including `POST /clips/feedback`.
- Return `401` for invalid token, `403` for email not whitelisted.

## Input & paths (T-11)
- MUST validate user-supplied paths with `backend.core.validation.resolve_confined_path` against `DUB_ALLOWED_ROOT`.
- MUST sanitize AI-derived filenames with `sanitize_filename()` before writing to `temp/`/`output/`.
- MUST use `validate_lang`, `validate_search_type`, `validate_text` for enum-like and text inputs.
- MUST apply `check_rate_limit()` on AI endpoints (`/agent/shorts`, `/clips/generate-clips`, `/tools/dub`).
- MUST treat URLs, transcripts, RSS, and LLM output as untrusted data, never instructions.
- MUST keep external calls time-bounded.

## Contract (T-13)
- OpenAPI path/schema is locked by `tests/test_openapi_contract.py`; update it together with `docs/API.md` and `README.md`.
