# ADR 0002: Supabase Postgres + pgvector as the only datastore

- Status: Accepted (2026-10-21)
- Deciders: Sandeep Gupta
- Supersedes: the SQLite memory store in architecture draft v0.1

## Context
We need relational data (users, conversations, approvals, usage), vector search for memory recall, authentication including anonymous "Try demo" sessions, and per-user isolation. Everything must be free through judging (Dec 15) and close to Indian users.

## Decision
- **Supabase free tier** in `ap-south-1` (Mumbai): Postgres 16, pgvector, Auth (Google, magic link, anonymous), Storage for the audio cache.
- Schema managed by **Alembic** in `apps/api/migrations`; one migration per change, never edit an applied one.
- **Row Level Security on every table** with `user_id = auth.uid()` (`users.id = auth.uid()`), defined in `infra/supabase/02_rls_policies.sql`. `audit_logs` is append-only.
- Embeddings: `Qwen/Qwen3-Embedding-8B` truncated to **1024 dims** in a `vector(1024)` column with an HNSW index (pgvector HNSW supports up to 2000 dims for `vector`).
- Local dev and CI use the same engine: `pgvector/pgvector:pg16` in Docker, plus a small `auth.uid()` stub so RLS can be tested.

## Consequences
- ✅ One datastore for rows, vectors, and auth; RLS gives defence in depth.
- ✅ Same SQL behaviour locally, in CI, and in production.
- ⚠️ Free projects pause after about a week of inactivity; the keep-alive pings `/health`, which touches the DB (stack decision), and deploys check `/ready`.
- ⚠️ 500 MB limit: store masked text and counts only, no raw audio in Postgres.
- ⚠️ Plaintext embeddings next to encrypted content are a deliberate trade-off (see SECURITY.md).

## Alternatives considered
- **SQLite + per-user file encryption**: simple, but no pgvector, no shared auth, and behaviour differs from production.
- **Neon + separate auth provider**: two vendors to wire up for the same result.
- **Dedicated vector DB**: an extra service and network hop for a small dataset.
