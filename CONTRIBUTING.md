# Contributing to Saathi

Thanks for helping! Saathi is a hackathon project, so the bar is: small PRs, green CI, no personal data anywhere.

## Setup

```bash
make setup     # uv sync, pnpm install, pre-commit install, env templates
make dev       # db + api + web
make migrate && make seed
```

Requirements: Docker (Compose v2.24+), uv, Node 22 + corepack, pre-commit (`pipx install pre-commit`).

## Workflow

1. Branch from `main`: `feat/<short-name>`, `fix/<short-name>`, or `chore/<short-name>`.
2. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat(memory): add semantic recall`, `fix(privacy): mask IFSC`.
3. Open a PR. The **PR title** is checked and becomes the squash-merge commit.
4. CI must be green and `@sandeepguptax2003` must approve. `main` allows squash merges only, linear history, no force push.
5. Releases are cut by release-please from the commit history (`vX.Y.Z` tags, `CHANGELOG.md`).

## Code standards

**API (`apps/api`)**
- Python 3.12, `ruff` (lint + format), `mypy --strict`.
- Module layout: `router.py → service.py → repository.py`, plus `schemas.py` (Pydantic, camelCase out) and `models.py` (SQLAlchemy). Modules talk via services, never another module's tables.
- Every new table: one Alembic migration (never edit an applied one) **and** an entry in `infra/supabase/02_rls_policies.sql`.
- Coverage ≥ 80% on `core/`, `modules/privacy`, `modules/approvals`, `modules/budget`.

**Web (`apps/web`)**
- TypeScript strict, ESLint, Prettier. Components PascalCase, hooks `useXxx.ts`, one component per file.
- API types come from OpenAPI: run `make types` after any API change and commit `src/types/api.ts`.

**Both**
- Errors use the shared shape `{error: {code, message, requestId}}`.
- Never log prompts, raw user text, or secrets. Log request IDs.
- Anything with a side effect goes through the approval gate.

## Privacy rules for contributors

- Use demo data only in tests, fixtures, screenshots, and issues. Fake numbers should be obviously fake.
- Never commit `.env` files or keys. gitleaks runs in pre-commit and CI.
- New PII type? Add a masker pattern **and** tests with positive and negative cases.

## Architecture decisions

Big changes get an ADR in `docs/adr/` (copy the format of `0001-modular-monolith.md`).
