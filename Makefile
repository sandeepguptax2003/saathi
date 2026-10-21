# Saathi monorepo tasks. Run `make help`.
# Needs: docker (compose v2.24+), uv, pnpm (corepack), and optionally pre-commit.

SHELL := /bin/bash
.DEFAULT_GOAL := help

-include .env
export

API_DIR   := apps/api
WEB_DIR   := apps/web
COMPOSE   := docker compose -f infra/docker-compose.yml $(if $(wildcard .env),--env-file .env,)
DB_PORT   ?= 5432
API_URL   ?= http://localhost:8000
# Local compose DB only (credentials are local placeholders, not secrets).
LOCAL_DATABASE_URL := postgresql+asyncpg://saathi:saathi_local_only@localhost:$(DB_PORT)/saathi

.PHONY: help setup dev up down logs ps reset-db migrate rls seed test test-api test-web e2e \
        lint lint-api lint-web fmt types docker-build clean

help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install deps for both apps + git hooks
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && corepack enable && pnpm install
	@command -v pre-commit >/dev/null && pre-commit install || echo "pre-commit not installed (pipx install pre-commit)"
	@test -f $(API_DIR)/.env || { test -f $(API_DIR)/.env.example && cp $(API_DIR)/.env.example $(API_DIR)/.env && echo "created $(API_DIR)/.env from template"; } || true
	@test -f $(WEB_DIR)/.env.local || { test -f $(WEB_DIR)/.env.example && cp $(WEB_DIR)/.env.example $(WEB_DIR)/.env.local && echo "created $(WEB_DIR)/.env.local from template"; } || true

dev: ## Start db + api (hot reload) + web (pnpm dev)
	$(COMPOSE) up --build

up: ## Same as dev, detached
	$(COMPOSE) up --build -d

down: ## Stop the stack (keeps DB volume)
	$(COMPOSE) down

logs: ## Tail logs
	$(COMPOSE) logs -f --tail=200

ps: ## Show containers
	$(COMPOSE) ps

reset-db: ## Destroy the local DB volume and start fresh
	$(COMPOSE) down -v

migrate: ## Alembic upgrade head on the LOCAL compose DB, then apply RLS
	$(COMPOSE) up -d --wait db
	cd $(API_DIR) && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run alembic upgrade head
	$(MAKE) rls

rls: ## Apply infra/supabase/02_rls_policies.sql to the local DB
	$(COMPOSE) exec -T db psql -U saathi -d saathi -v ON_ERROR_STOP=1 -f - < infra/supabase/02_rls_policies.sql
	$(COMPOSE) exec -T db psql -U saathi -d saathi -f - < infra/supabase/03_verify_rls.sql

seed: ## Load demo inbox / calendar / bills into the LOCAL DB
	cd $(API_DIR) && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run python -m saathi_api.seed

test: test-api test-web ## Run all unit/integration tests

test-api: ## pytest with coverage (needs local DB: make up)
	cd $(API_DIR) && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run pytest --cov=saathi_api --cov-report=term-missing

test-web: ## vitest
	cd $(WEB_DIR) && pnpm exec vitest run

e2e: ## Playwright against a running stack (make up first)
	cd $(WEB_DIR) && E2E_TELEMETRY_DISABLED=1 pnpm exec playwright test

lint: lint-api lint-web ## Lint + typecheck everything
	@command -v pre-commit >/dev/null && pre-commit run gitleaks --all-files || true

lint-api:
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src

lint-web:
	cd $(WEB_DIR) && pnpm exec eslint . --max-warnings=0 && pnpm exec prettier --check . && pnpm exec tsc --noEmit

fmt: ## Auto-format both apps
	cd $(API_DIR) && uv run ruff check --fix . && uv run ruff format .
	cd $(WEB_DIR) && pnpm exec prettier --write . && pnpm exec eslint . --fix

types: ## Regenerate apps/web/src/types/api.ts from the running API's OpenAPI
	cd $(WEB_DIR) && pnpm dlx openapi-typescript $(API_URL)/openapi.json -o src/types/api.ts
	cd $(WEB_DIR) && pnpm exec prettier --write src/types/api.ts

docker-build: ## Build the production API image (same as CI / Render)
	docker build -t saathi-api:local $(API_DIR)
	@docker image ls saathi-api:local --format 'saathi-api:local {{.Size}}'

clean: ## Remove caches and build output
	rm -rf $(API_DIR)/.pytest_cache $(API_DIR)/.mypy_cache $(API_DIR)/.ruff_cache $(API_DIR)/htmlcov $(API_DIR)/.coverage
	rm -rf $(WEB_DIR)/.next $(WEB_DIR)/playwright-report $(WEB_DIR)/test-results
