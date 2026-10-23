# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). From the first release onward this file is
maintained by release-please from Conventional Commit messages.

## [0.2.0](https://github.com/sandeepguptax2003/saathi/compare/v0.1.0...v0.2.0) (2026-10-23)


### Features

* **api:** verify Supabase asymmetric JWTs via JWKS; DATABASE_PASSWORD placeholder fill ([20bc24a](https://github.com/sandeepguptax2003/saathi/commit/20bc24a601dbfa59746c7909f5a94012b13a8a8f))


### Bug Fixes

* **api:** add seed entrypoint that validates demo fixtures ([585db69](https://github.com/sandeepguptax2003/saathi/commit/585db69efe7e0fea6c82b87526d1221a5e53c94d))

## [Unreleased]

### Added
- Monorepo scaffold: `apps/api` (FastAPI) and `apps/web` (Next.js) with shared Makefile.
- Local stack in `infra/docker-compose.yml` (Postgres 16 + pgvector, API hot reload, web dev server).
- Supabase SQL: pgvector extension, Row Level Security on every table, append-only audit log.
- Render Blueprint for the API (Docker, Singapore, `/health` check).
- GitHub Actions: CI (path-filtered API/web/e2e/security/docker jobs), deploy-api, keepalive, CodeQL, release-please; Dependabot.
- Docs: README, SECURITY (threat model, masking, encryption, embeddings trade-off), CONTRIBUTING, ADRs 0001–0003, demo script stub.
