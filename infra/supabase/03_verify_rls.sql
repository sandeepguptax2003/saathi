-- Sanity check, safe to run anywhere: lists every public table and whether RLS is on.
-- Expect rls_enabled = true for all 10 Saathi tables, and audit_logs with 2 policies (select, insert).
select c.relname                                  as table_name,
       c.relrowsecurity                           as rls_enabled,
       count(p.polname)                           as policy_count,
       string_agg(p.polname, ', ' order by p.polname) as policies
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
left join pg_policy p on p.polrelid = c.oid
where c.relkind = 'r'
group by c.relname, c.relrowsecurity
order by c.relname;
