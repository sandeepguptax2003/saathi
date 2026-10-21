# ADR 0001: Monorepo with a modular-monolith API

- Status: Accepted (2026-10-20)
- Deciders: Sandeep Gupta

## Context
Saathi is built by one developer in about ten days and must stay live on free tiers through December 2026. Voice latency matters: every network hop between internal services adds to time-to-first-word. Free hosting gives us one always-on backend service.

## Decision
- One Git repository with two deployable apps: `apps/web` (Next.js on Vercel) and `apps/api` (FastAPI on Render).
- The API is a **modular monolith**: one process, split into feature modules (`assistant`, `llm`, `privacy`, `memory`, `approvals`, `budget`, `skills`, `voice`, `users`).
- Inside a module: `router → service → repository`, with `schemas` (Pydantic I/O) and `models` (SQLAlchemy). Dependencies are injected with FastAPI `Depends`.
- Modules call each other only through service interfaces and never touch another module's tables.
- OpenAPI is the contract; web types are generated from it in the same PR.

## Consequences
- ✅ One deploy, one CI, one place for judges to read; API + UI change together.
- ✅ No inter-service network calls on the voice path.
- ✅ Clean seams let us extract a module later (e.g. a GPU voice worker) without a rewrite.
- ⚠️ A bug can take the whole API down; mitigated by tests, health checks, and fast rollback on Render.
- ⚠️ Boundaries are enforced by convention and review, not the network. Revisit with import-linter if the codebase grows.

## Alternatives considered
- **Microservices**: more deploys, more failure points, slower voice, and no free tier to host them.
- **Separate repos for web and API**: harder to keep the contract in sync; two CIs.
