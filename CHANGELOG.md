# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). From the first release onward this file is
maintained by release-please from Conventional Commit messages.

## [Unreleased]

### Added
- Monorepo scaffold: `apps/api` (FastAPI) and `apps/web` (Next.js) with shared Makefile.
- Local stack in `infra/docker-compose.yml` (Postgres 16 + pgvector, API hot reload, web dev server).
- Supabase SQL: pgvector extension, Row Level Security on every table, append-only audit log.
- Render Blueprint for the API (Docker, Singapore, `/health` check).
- GitHub Actions: CI (path-filtered API/web/e2e/security/docker jobs), deploy-api, keepalive, CodeQL, release-please; Dependabot.
- Docs: README, SECURITY (threat model, masking, encryption, embeddings trade-off), CONTRIBUTING, ADRs 0001–0003, demo script stub.
