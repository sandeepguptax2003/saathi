# @saathi/web

Next.js 15 (App Router) frontend for Saathi: landing page, voice console, memory, approvals,
privacy and settings. Deployed on Vercel; talks to the FastAPI service in `apps/api`.

## Stack

TypeScript (strict, `noUncheckedIndexedAccess`) · Tailwind v4 · shadcn/ui (Radix) · Serwist PWA ·
TanStack Query · Zod · React Hook Form · Framer Motion · Sonner · Supabase JS (Google, magic link,
anonymous demo) · Vitest + Testing Library · Playwright.

## Quick start

```bash
cd apps/web
cp .env.example .env.local     # fill NEXT_PUBLIC_* values (browser-safe only)
pnpm install
pnpm dev                       # http://localhost:3000
```

Build and `next dev` refuse to run when `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL` or
`NEXT_PUBLIC_SUPABASE_ANON_KEY` is missing (`src/lib/env.schema.ts`).

## Scripts

| Script                                               | What it does                                                                                                                                                       |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `pnpm lint` / `pnpm format:check` / `pnpm typecheck` | ESLint (0 warnings), Prettier, `tsc --noEmit`                                                                                                                      |
| `pnpm test`                                          | Vitest unit tests (`tests/unit`)                                                                                                                                   |
| `pnpm build`                                         | Production build (also bundles the Serwist service worker to `public/sw.js`)                                                                                       |
| `pnpm test:e2e`                                      | Playwright against `next start` on :3100 (run `pnpm build` first). API is mocked with `page.route`. `E2E_BASE_URL=https://… pnpm test:e2e` targets a deployed URL. |
| `pnpm gen:types`                                     | Writes `src/types/api.generated.ts` from OpenAPI (`--input file`, `$OPENAPI_URL`, or `$NEXT_PUBLIC_API_URL/openapi.json`)                                          |
| `pnpm check:types`                                   | CI: fails if the generated types are stale                                                                                                                         |

## Layout

```
src/
  app/                 (marketing)/ landing · (app)/ console, memory, approvals, privacy, settings
                       ~offline/ PWA fallback · sw.ts service worker · providers.tsx
  components/ui/       shadcn primitives (button, card, dialog, alert-dialog, input, …)
  components/common/   Modal, ConfirmDialog, Loader, Skeletons, Pagination (cursor), EmptyState,
                       ErrorState, ErrorBoundary, WakingSaathi, ThemeToggle, LocaleToggle
  components/layout/   AppShell (cold-start gate), AppHeader, PageHeader
  features/<name>/     api/ + hooks/ + components/ per feature: chat, voice, approvals, memory,
                       privacy, budget, settings, auth, health, marketing
  lib/                 api client (envelope, X-Request-ID, Idempotency-Key, SSE), env, supabase,
                       i18n (en/hi dictionaries), query-client, ids, utils
  types/               api.ts (domain types, placeholder) · api.generated.ts (openapi-typescript)
  styles/globals.css   Tailwind v4 theme tokens, dark mode
```

## Conventions

- API paths are relative to `/api/v1`; `GET /health` is at the API root.
- Every request sends `X-Request-ID`; errors surface `requestId` in the UI.
- Approve/reject send `Idempotency-Key`, minted once per user decision and reused on retry.
- The service worker never caches `/api/*` or `/health` (personal, streamed data).
- Voice: Web Speech recognition (hi-IN / en-IN) when available, text input always; replies spoken
  with the best local `speechSynthesis` voice for the locale.
