# saathi-api

FastAPI modular monolith for Saathi (see `docs/` at the repo root for the approved specs:
blueprint, architecture, db-schema, api-contract, cicd-docker, deploy-ops).

## Quick start

```bash
cd apps/api
uv sync                              # Python 3.12, installs dev tools too
cp .env.example .env                 # fill DATABASE_URL, SUPABASE_*, ENCRYPTION_PEPPER; LLM_MOCK=true for offline
uv run alembic upgrade head          # needs Postgres 16 + pgvector (infra/docker-compose.yml)
uv run uvicorn saathi_api.main:app --reload --port 8000
```

Quality gates (same as CI):

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov=saathi_api
TEST_DATABASE_URL=postgresql://saathi:saathi@localhost:5432/saathi_test uv run pytest -m integration
```

## Layout

```
src/saathi_api/
  main.py            app factory: middleware (request id, security headers, CORS allowlist, gzip),
                     error envelope handlers, routers under /api/v1, /health + /ready at root
  deps.py            composition root: process singletons + per-request service providers
  core/              config, logging, errors, schemas (envelope), db, security (Supabase JWT),
                     crypto (AES-256-GCM + HKDF), resilience (retry, circuit breaker),
                     rate_limit, pagination, http_client, middleware, health
  modules/<name>/    router.py -> service.py -> repository.py ; schemas.py ; models.py
    assistant  SSE turn orchestration, conversations
    llm        Token Factory backend + mock, router, Nano -> Super escalation, cost recording
    privacy    Indian PII masker (reversible placeholders), privacy events
    memory     encrypted memories + pgvector recall
    approvals  pending actions, Idempotency-Key approve/reject, audit log
    budget     llm_usage, per-user + global daily caps
    skills     registry + daily-brief, reminders, email-triage, calendar, bills; /demo/reset
    voice      STT/TTS adapter interfaces (browser in v0.1)
    users      /me profile + settings
  seed/demo/         fictional Indian demo inbox, calendar, bills (relative dates)
migrations/          Alembic (0001 = db-schema v0.1, HNSW index, RLS policies)
tests/unit           DB-free tests (in-memory repos in tests/fakes.py, mock LLM)
tests/integration    real Postgres (skipped unless TEST_DATABASE_URL is set)
```

## SSE turn

`POST /api/v1/assistant/turns` streams `meta`, `privacy`, `tool`, `pending_action`, `token`,
`done` (or `error`). Budget, auth, validation and unknown-conversation errors are returned as
the JSON error envelope before the stream opens.
