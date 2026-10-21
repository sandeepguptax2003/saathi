# infra/supabase

SQL applied to Supabase (prod) and to the local/CI Postgres. Tables themselves come from Alembic (`apps/api/migrations`).

| File | Where | When |
|---|---|---|
| `00_local_auth_stub.sql` | local + CI only, **never Supabase** | auto, on first `docker compose up` (initdb) |
| `01_extensions.sql` | everywhere | before the first migration (auto locally) |
| `02_rls_policies.sql` | everywhere | after `alembic upgrade head`, and after any migration that adds a table |
| `03_verify_rls.sql` | everywhere | any time, read-only check |

Supabase: paste 01 then 02 into the SQL editor (or `psql "$SUPABASE_DB_URL" -f ...`). Locally: `make rls`.

Recommended Supabase setting: the web app only talks to the FastAPI service, so turn off the Data API for the `public` schema (Project Settings -> API -> Exposed schemas) or keep it limited. RLS still applies either way.
