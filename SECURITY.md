# Security Policy

> This document describes the intended security design. If code and this file disagree, treat it as a bug and open a private advisory.

## Reporting a vulnerability

Please **do not open a public issue**. Report privately through GitHub's
[security advisories](https://github.com/sandeepguptax2003/saathi/security/advisories/new)
or by email to the maintainer listed on the GitHub profile. Expect an acknowledgement within 72 hours.
Please use demo data in any proof of concept; never send real personal data.

Supported version: the latest release on `main`.

## Threat model

Saathi handles the most sensitive things a person says out loud: names, phone numbers, Aadhaar, PAN, UPI IDs, bank details, bills, and plans. The design assumes any third party that sees a prompt could keep it.

| Asset | Threat | Mitigation |
|---|---|---|
| Raw PII in speech/text | Leaks to the model provider or its logs | PII masker runs **before every** model call; only tokens like `<PHONE_1>` leave the API. Token map lives in request memory only |
| Stored memories, reminders, action payloads | DB dump, leaked backup, curious operator | AES-256-GCM application-level encryption; ciphertext + nonce stored; keys never in DB |
| Another user's data | Broken access control (IDOR) | Supabase JWT verified on every request; ownership enforced in every repository query; **RLS `user_id = auth.uid()` on every table** as a second wall |
| Side-effect actions (send / book / pay) | Prompt injection makes the model act on its own | Model can only **propose** a pending action. Execution requires an explicit user tap on `POST /pending-actions/{id}/approve` with an `Idempotency-Key`. Hosted demo actions are simulated |
| Approval history | Tampering to hide what happened | `audit_logs` is append-only: no UPDATE/DELETE policy, privileges revoked, trigger blocks UPDATE/DELETE/TRUNCATE for every role |
| Token Factory credits | Abuse / denial of wallet | Per-user and global daily caps, rate limits (30 turns/min/user), anonymous demo users limited, circuit breaker |
| Secrets (API keys, pepper, JWT secret) | Committed to git, leaked in logs | Only in Render / Vercel / GitHub encrypted env; gitleaks in pre-commit + CI; structured logs never include prompts or secrets |
| Browser | XSS stealing the session | Strict CSP, HSTS, no `dangerouslySetInnerHTML` on model output, service-role key never shipped to the browser, CORS allowlist |
| Supply chain | Malicious or vulnerable dependency | Lockfiles (`uv.lock`, `pnpm-lock.yaml`), Dependabot, pip-audit, pnpm audit, Trivy image scan (fail on HIGH/CRITICAL), CodeQL |

Out of scope for the hackathon build: a compromised API host (it holds the pepper and sees unmasked text in memory), a compromised user device, and side channels in the model provider.

## PII masking

- Detected entities: Indian mobile and landline numbers, email, Aadhaar, PAN, UPI IDs (`name@bank`), card numbers, bank account numbers, IFSC, and person names the user has stored in memory. Checksums (Verhoeff for Aadhaar, Luhn for cards) are used where they exist to cut false positives.
- Each match is replaced with a typed, numbered token (`<PHONE_1>`, `<AADHAAR_1>` …). The same value gets the same token within a turn, so the model can still reason ("send it to <PHONE_1>").
- Unmasking happens only in the API before the reply goes back to the user.
- What is stored: `messages.content_masked` holds **masked text only**; `privacy_events.entity_counts` holds **counts only** (`{"phone": 1}`), never values.
- Known limits: free-form identifiers with no pattern (a house address said casually, a nickname not in memory) can slip through. The privacy dashboard shows the user exactly what the model saw so misses are visible.

## Encryption

- Algorithm: AES-256-GCM with a fresh 96-bit random nonce per value; columns `*_ciphertext bytea` + `nonce bytea` + `key_version`.
- Keys: per-user data key = HKDF-SHA256 over the server `ENCRYPTION_PEPPER` and the user id, scoped by `key_version`. The pepper exists only in the API's runtime environment.
- Rotation: bump `key_version`, re-encrypt lazily on read/write; the Token Factory key and pepper are rotated after judging.
- In transit: TLS everywhere (Vercel, Render, Supabase, Token Factory).
- Deletion: memories are soft-deleted first (`deleted_at`) and hard-purged with `DELETE /memories/{id}?hard=true`.

## Embeddings trade-off

Semantic recall needs vectors, and vectors cannot be encrypted without losing similarity search. Saathi therefore stores `memories.embedding vector(1024)` **in plaintext** next to the encrypted content.

- What this means: an attacker with DB access cannot read a memory, but embeddings carry meaning. Inversion and attribute-inference attacks on embeddings are a known research area and can recover topics, sometimes phrases.
- How we reduce it: embeddings are computed on **masked** text, so identifiers never enter the vector; RLS restricts rows to their owner; vectors are deleted with the memory on hard purge; the embedding model runs on Token Factory under the same masking rules as chat.
- What we did not do (yet): client-side or homomorphic search, per-user random projection, or keeping vectors only in the browser. These are on the roadmap as an opt-in "maximum privacy" mode that turns semantic recall into keyword recall.

## Operational rules

- Row Level Security is enabled on every table (`infra/supabase/02_rls_policies.sql`); CI fails if any public table has RLS off.
- The API connects with a privileged role and enforces ownership in code; RLS protects any direct access through the Supabase Data API. We recommend disabling the Data API for the `public` schema because the web app never uses it.
- The Supabase service-role key is never used in the browser.
- Sentry runs with PII scrubbing enabled and never receives prompts.
