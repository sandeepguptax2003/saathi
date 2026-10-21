-- Saathi: Row Level Security for every table in docs/db-schema.md.
-- Run AFTER `alembic upgrade head` (tables are created by Alembic, not here).
-- Idempotent: drops and recreates every policy it owns. Missing tables are skipped with a NOTICE.
--
-- Rule: a row is visible/writable only when its owner column equals auth.uid().
--   users           -> id = auth.uid()          (row id IS the auth user id)
--   everything else -> user_id = auth.uid()
-- audit_logs is append-only: SELECT + INSERT policies only, UPDATE/DELETE/TRUNCATE revoked
-- and blocked by trigger (see bottom).
--
-- The FastAPI service connects with a privileged role and enforces ownership in code too;
-- these policies are the second wall (and the only wall for any direct Supabase Data API call).

begin;

-- 1) Owner-scoped tables with full CRUD for their owner ------------------------------------
do $$
declare
  t text;
  owner_col text;
  crud_tables text[] := array[
    'users', 'conversations', 'messages', 'memories', 'pending_actions',
    'privacy_events', 'llm_usage', 'reminders', 'skill_runs'
  ];
begin
  foreach t in array crud_tables loop
    if to_regclass(format('public.%I', t)) is null then
      raise notice 'RLS: table public.% not found, skipped (run migrations first)', t;
      continue;
    end if;

    owner_col := case when t = 'users' then 'id' else 'user_id' end;

    execute format('alter table public.%I enable row level security', t);

    execute format('drop policy if exists %I on public.%I', t || '_select_own', t);
    execute format('drop policy if exists %I on public.%I', t || '_insert_own', t);
    execute format('drop policy if exists %I on public.%I', t || '_update_own', t);
    execute format('drop policy if exists %I on public.%I', t || '_delete_own', t);

    execute format(
      'create policy %I on public.%I for select to authenticated using (%I = auth.uid())',
      t || '_select_own', t, owner_col);
    execute format(
      'create policy %I on public.%I for insert to authenticated with check (%I = auth.uid())',
      t || '_insert_own', t, owner_col);
    execute format(
      'create policy %I on public.%I for update to authenticated using (%I = auth.uid()) with check (%I = auth.uid())',
      t || '_update_own', t, owner_col, owner_col);
    execute format(
      'create policy %I on public.%I for delete to authenticated using (%I = auth.uid())',
      t || '_delete_own', t, owner_col);

    -- Anonymous (no JWT) gets nothing. Supabase "anonymous sign-in" users carry the
    -- `authenticated` role with is_anonymous=true, so the demo still works.
    execute format('revoke all on public.%I from anon', t);
  end loop;
end
$$;

-- 2) audit_logs: append-only ---------------------------------------------------------------
do $$
begin
  if to_regclass('public.audit_logs') is null then
    raise notice 'RLS: table public.audit_logs not found, skipped (run migrations first)';
    return;
  end if;

  alter table public.audit_logs enable row level security;

  drop policy if exists audit_logs_select_own on public.audit_logs;
  drop policy if exists audit_logs_insert_own on public.audit_logs;

  create policy audit_logs_select_own on public.audit_logs
    for select to authenticated using (user_id = auth.uid());
  create policy audit_logs_insert_own on public.audit_logs
    for insert to authenticated with check (user_id = auth.uid());
  -- No UPDATE or DELETE policy on purpose.

  revoke all on public.audit_logs from anon;
  revoke update, delete, truncate on public.audit_logs from authenticated;
end
$$;

-- Trigger guard: blocks UPDATE/DELETE/TRUNCATE for every role, including the table owner.
-- Escape hatch for retention jobs / account erasure only, inside one transaction:
--   set local saathi.audit_purge = 'on';
create or replace function public.audit_logs_block_mutation() returns trigger
language plpgsql
as $$
begin
  if coalesce(current_setting('saathi.audit_purge', true), '') = 'on' then
    return coalesce(old, new);
  end if;
  raise exception 'audit_logs is append-only (% blocked)', tg_op
    using errcode = 'insufficient_privilege';
end
$$;

do $$
begin
  if to_regclass('public.audit_logs') is null then
    return;
  end if;
  drop trigger if exists audit_logs_no_update_delete on public.audit_logs;
  drop trigger if exists audit_logs_no_truncate on public.audit_logs;
  create trigger audit_logs_no_update_delete
    before update or delete on public.audit_logs
    for each row execute function public.audit_logs_block_mutation();
  create trigger audit_logs_no_truncate
    before truncate on public.audit_logs
    for each statement execute function public.audit_logs_block_mutation();
end
$$;

-- 3) alembic_version: internal, never readable through the Data API ----------------------
do $$
begin
  if to_regclass('public.alembic_version') is not null then
    alter table public.alembic_version enable row level security;  -- no policies = deny all
    revoke all on public.alembic_version from anon, authenticated;
  end if;
end
$$;

commit;
