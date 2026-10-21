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
