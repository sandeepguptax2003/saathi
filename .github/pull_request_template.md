<!-- PR title must follow Conventional Commits, e.g. "feat(memory): semantic recall" -->

## What
<!-- One or two lines: what changed and why. -->

## How to test
<!-- Commands or clicks a reviewer runs. -->

## Checklist
- [ ] `make lint test types` passes locally
- [ ] API contract unchanged, or `openapi.json` + `apps/web/src/types/api.ts` regenerated (`make types`)
- [ ] New table? Alembic migration added **and** `infra/supabase/02_rls_policies.sql` covers it
- [ ] No raw PII reaches a model call, log line, or DB column (masked text only)
- [ ] Side-effect actions go through the approval gate
- [ ] No secrets, keys, or real personal data in code, fixtures, or screenshots
- [ ] Docs / ADR / CHANGELOG updated if behaviour changed

## Screenshots / recordings
<!-- UI changes only. Use demo data. -->
