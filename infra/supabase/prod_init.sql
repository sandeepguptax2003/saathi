-- GENERATED: 01_extensions.sql + `alembic upgrade head --sql` + 02_rls_policies.sql, for a fresh Supabase project.
-- Paste into the Supabase SQL editor once. Regenerate after new migrations; never edit by hand.
-- Saathi: required extensions. Idempotent; safe on Supabase and local Postgres.
-- Supabase convention keeps extensions in the "extensions" schema (on the default search_path);
-- plain local Postgres has no such schema, so fall back to public.

do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'extensions') then
    execute 'create extension if not exists vector with schema extensions';
    execute 'create extension if not exists pgcrypto with schema extensions';
  else
    execute 'create extension if not exists vector';
    execute 'create extension if not exists pgcrypto';
  end if;
end
$$;

-- gen_random_uuid() is built into Postgres 13+; pgcrypto is kept for digest() helpers only.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

create extension if not exists pgcrypto;

create extension if not exists vector;

do $$
        begin
          if not exists (select 1 from pg_roles where rolname = 'authenticated') then
            create role authenticated nologin;
          end if;
          if not exists (select 1 from pg_namespace where nspname = 'auth') then
            create schema auth;
            grant usage on schema auth to authenticated;
          end if;
          if not exists (
            select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname = 'auth' and p.proname = 'uid'
          ) then
            execute $f$
              create function auth.uid() returns uuid language sql stable as $body$
                select nullif(
                  coalesce(
                    current_setting('request.jwt.claim.sub', true),
                    current_setting('request.jwt.claims', true)::jsonb ->> 'sub'
                  ), '')::uuid
              $body$
            $f$;
          end if;
        end $$;;

CREATE TABLE users (
    id UUID NOT NULL, 
    display_name VARCHAR(120), 
    locale VARCHAR(10) DEFAULT 'hi-IN' NOT NULL, 
    timezone VARCHAR(64) DEFAULT 'Asia/Kolkata' NOT NULL, 
    voice_pref VARCHAR(64), 
    daily_budget_usd NUMERIC(10, 4), 
    is_demo BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(200), 
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_conversations PRIMARY KEY (id), 
    CONSTRAINT fk_conversations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversations_user_last_message ON conversations (user_id, last_message_at);

CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    conversation_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role VARCHAR(16) NOT NULL, 
    content_masked TEXT NOT NULL, 
    model VARCHAR(200), 
    tokens_in INTEGER, 
    tokens_out INTEGER, 
    latency_ms INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_messages PRIMARY KEY (id), 
    CONSTRAINT ck_messages_ck_messages_role_valid CHECK (role in ('user','assistant','system','tool')), 
    CONSTRAINT fk_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
    CONSTRAINT fk_messages_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_conversation_created ON messages (conversation_id, created_at);

CREATE TABLE memories (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    kind VARCHAR(16) NOT NULL, 
    content_ciphertext BYTEA NOT NULL, 
    nonce BYTEA NOT NULL, 
    key_version SMALLINT DEFAULT '1' NOT NULL, 
    embedding VECTOR(1024), 
    source VARCHAR(32), 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_memories PRIMARY KEY (id), 
    CONSTRAINT ck_memories_ck_memories_kind_valid CHECK (kind in ('fact','preference','person','note')), 
    CONSTRAINT fk_memories_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_memories_user_kind_created ON memories (user_id, kind, created_at);

create index ix_memories_embedding_hnsw on memories using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64);

CREATE TABLE pending_actions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    skill VARCHAR(64) NOT NULL, 
    action_type VARCHAR(64) NOT NULL, 
    payload_ciphertext BYTEA NOT NULL, 
    summary TEXT NOT NULL, 
    status VARCHAR(16) DEFAULT 'pending' NOT NULL, 
    idempotency_key VARCHAR(128), 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    decided_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_pending_actions PRIMARY KEY (id), 
    CONSTRAINT ck_pending_actions_ck_pending_actions_status_valid CHECK (status in ('pending','approved','rejected','expired','executed','failed')), 
    CONSTRAINT uq_pending_actions_idempotency_key UNIQUE (idempotency_key), 
    CONSTRAINT fk_pending_actions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_pending_actions_user_status_created ON pending_actions (user_id, status, created_at);

CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    actor VARCHAR(16) NOT NULL, 
    event VARCHAR(64) NOT NULL, 
    entity VARCHAR(64) NOT NULL, 
    entity_id UUID, 
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
    CONSTRAINT ck_audit_logs_ck_audit_logs_actor_valid CHECK (actor in ('user','system')), 
    CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_user_created ON audit_logs (user_id, created_at);

CREATE TABLE privacy_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    message_id UUID, 
    entity_counts JSONB DEFAULT '{}'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_privacy_events PRIMARY KEY (id), 
    CONSTRAINT fk_privacy_events_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_privacy_events_message_id_messages FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE SET NULL
);

CREATE INDEX ix_privacy_events_user_created ON privacy_events (user_id, created_at);

CREATE TABLE llm_usage (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    model VARCHAR(200) NOT NULL, 
    tokens_in INTEGER DEFAULT '0' NOT NULL, 
    tokens_out INTEGER DEFAULT '0' NOT NULL, 
    cost_usd NUMERIC(10, 6) DEFAULT '0' NOT NULL, 
    escalated BOOLEAN DEFAULT false NOT NULL, 
    request_id VARCHAR(128), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_llm_usage PRIMARY KEY (id), 
    CONSTRAINT fk_llm_usage_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_llm_usage_user_created ON llm_usage (user_id, created_at);

CREATE INDEX ix_llm_usage_created ON llm_usage (created_at);

CREATE TABLE reminders (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    text_ciphertext BYTEA NOT NULL, 
    nonce BYTEA NOT NULL, 
    key_version SMALLINT DEFAULT '1' NOT NULL, 
    due_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    status VARCHAR(16) DEFAULT 'pending' NOT NULL, 
    repeat_rule VARCHAR(128), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_reminders PRIMARY KEY (id), 
    CONSTRAINT ck_reminders_ck_reminders_status_valid CHECK (status in ('pending','done','cancelled')), 
    CONSTRAINT fk_reminders_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_reminders_user_status_due ON reminders (user_id, status, due_at);

CREATE TABLE skill_runs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    skill VARCHAR(64) NOT NULL, 
    status VARCHAR(16) NOT NULL, 
    duration_ms INTEGER DEFAULT '0' NOT NULL, 
    error_code VARCHAR(64), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_skill_runs PRIMARY KEY (id), 
    CONSTRAINT fk_skill_runs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_skill_runs_user_created ON skill_runs (user_id, created_at);

alter table users enable row level security;

grant select, insert on users to authenticated;

create policy users_select_own on users for select to authenticated using (id = auth.uid());

create policy users_insert_own on users for insert to authenticated with check (id = auth.uid());

grant update, delete on users to authenticated;

create policy users_update_own on users for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

create policy users_delete_own on users for delete to authenticated using (id = auth.uid());

alter table conversations enable row level security;

grant select, insert on conversations to authenticated;

create policy conversations_select_own on conversations for select to authenticated using (user_id = auth.uid());

create policy conversations_insert_own on conversations for insert to authenticated with check (user_id = auth.uid());

grant update, delete on conversations to authenticated;

create policy conversations_update_own on conversations for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy conversations_delete_own on conversations for delete to authenticated using (user_id = auth.uid());

alter table messages enable row level security;

grant select, insert on messages to authenticated;

create policy messages_select_own on messages for select to authenticated using (user_id = auth.uid());

create policy messages_insert_own on messages for insert to authenticated with check (user_id = auth.uid());

grant update, delete on messages to authenticated;

create policy messages_update_own on messages for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy messages_delete_own on messages for delete to authenticated using (user_id = auth.uid());

alter table memories enable row level security;

grant select, insert on memories to authenticated;

create policy memories_select_own on memories for select to authenticated using (user_id = auth.uid());

create policy memories_insert_own on memories for insert to authenticated with check (user_id = auth.uid());

grant update, delete on memories to authenticated;

create policy memories_update_own on memories for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy memories_delete_own on memories for delete to authenticated using (user_id = auth.uid());

alter table pending_actions enable row level security;

grant select, insert on pending_actions to authenticated;

create policy pending_actions_select_own on pending_actions for select to authenticated using (user_id = auth.uid());

create policy pending_actions_insert_own on pending_actions for insert to authenticated with check (user_id = auth.uid());

grant update, delete on pending_actions to authenticated;

create policy pending_actions_update_own on pending_actions for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy pending_actions_delete_own on pending_actions for delete to authenticated using (user_id = auth.uid());

alter table audit_logs enable row level security;

grant select, insert on audit_logs to authenticated;

create policy audit_logs_select_own on audit_logs for select to authenticated using (user_id = auth.uid());

create policy audit_logs_insert_own on audit_logs for insert to authenticated with check (user_id = auth.uid());

alter table privacy_events enable row level security;

grant select, insert on privacy_events to authenticated;

create policy privacy_events_select_own on privacy_events for select to authenticated using (user_id = auth.uid());

create policy privacy_events_insert_own on privacy_events for insert to authenticated with check (user_id = auth.uid());

grant update, delete on privacy_events to authenticated;

create policy privacy_events_update_own on privacy_events for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy privacy_events_delete_own on privacy_events for delete to authenticated using (user_id = auth.uid());

alter table llm_usage enable row level security;

grant select, insert on llm_usage to authenticated;

create policy llm_usage_select_own on llm_usage for select to authenticated using (user_id = auth.uid());

create policy llm_usage_insert_own on llm_usage for insert to authenticated with check (user_id = auth.uid());

grant update, delete on llm_usage to authenticated;

create policy llm_usage_update_own on llm_usage for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy llm_usage_delete_own on llm_usage for delete to authenticated using (user_id = auth.uid());

alter table reminders enable row level security;

grant select, insert on reminders to authenticated;

create policy reminders_select_own on reminders for select to authenticated using (user_id = auth.uid());

create policy reminders_insert_own on reminders for insert to authenticated with check (user_id = auth.uid());

grant update, delete on reminders to authenticated;

create policy reminders_update_own on reminders for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy reminders_delete_own on reminders for delete to authenticated using (user_id = auth.uid());

alter table skill_runs enable row level security;

grant select, insert on skill_runs to authenticated;

create policy skill_runs_select_own on skill_runs for select to authenticated using (user_id = auth.uid());

create policy skill_runs_insert_own on skill_runs for insert to authenticated with check (user_id = auth.uid());

grant update, delete on skill_runs to authenticated;

create policy skill_runs_update_own on skill_runs for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy skill_runs_delete_own on skill_runs for delete to authenticated using (user_id = auth.uid());

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

COMMIT;

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
