# Longevity Health Analytics Platform — developer commands.
# CI uses the same targets as local development (see .github/workflows/ci.yml).
#
# SAFETY: everything here is local/dev and synthetic-data-only. `make db-down`
# intentionally does NOT pass `-v`, so it never destroys local volumes by accident.

SHELL := /bin/bash
.DEFAULT_GOAL := help

API_DIR := apps/api
WORKER_DIR := apps/worker
WEB_DIR := apps/web
COMPOSE := docker compose
PSQL := $(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres

# uv runs the API toolchain in apps/api/.venv (created by `make bootstrap`).
UV := uv
API_RUN := cd $(API_DIR) && $(UV) run

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- Setup -------------------------------------------------------------------

.PHONY: bootstrap
bootstrap: ## Install pinned dependencies and prepare local config
	@test -f .env.local || (cp .env.example .env.local && echo "created .env.local from .env.example")
	pnpm install
	cd $(API_DIR) && $(UV) sync
	cd $(WORKER_DIR) && $(UV) sync
	@echo "bootstrap complete"

# ---- Local infrastructure ----------------------------------------------------

.PHONY: db-up
db-up: ## Start Postgres, Redis, and MinIO (local infra)
	$(COMPOSE) up -d postgres redis minio minio-init
	@$(MAKE) db-wait

.PHONY: db-wait
db-wait: ## Wait for Postgres to become healthy
	@echo "waiting for postgres..."
	@for i in $$(seq 1 30); do \
	  if $(COMPOSE) exec -T postgres pg_isready -U postgres -d hadp >/dev/null 2>&1; then \
	    echo "postgres ready"; exit 0; fi; sleep 1; done; \
	echo "postgres did not become ready" && exit 1

.PHONY: db-down
db-down: ## Stop infra containers (keeps volumes; never use -v here)
	$(COMPOSE) down

.PHONY: db-init
db-init: db-wait ## Create the non-superuser app role + test databases
	@$(PSQL) -d hadp -c "DO \$$\$$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='hadp_app') THEN CREATE ROLE hadp_app LOGIN PASSWORD 'hadp_app' NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END \$$\$$;"
	@$(PSQL) -d hadp -tc "SELECT 1 FROM pg_database WHERE datname='hadp_test'" | grep -q 1 || $(PSQL) -d hadp -c "CREATE DATABASE hadp_test OWNER postgres"
	@echo "db-init complete (role hadp_app + database hadp_test)"

# ---- Migrations & data -------------------------------------------------------

.PHONY: migrate
migrate: ## Apply migrations to the dev database
	$(API_RUN) alembic upgrade head

.PHONY: migrate-test
migrate-test: ## Apply migrations to the test database
	$(API_RUN) env DATABASE_URL="$${TEST_DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:55433/hadp_test}" alembic upgrade head

.PHONY: seed
seed: ## Load the synthetic data set (synthetic-labeled; no real PII)
	$(API_RUN) python -m hadp_api.scripts.seed

# ---- Quality gates -----------------------------------------------------------

.PHONY: format
format: ## Format all supported languages
	pnpm format
	cd $(API_DIR) && $(UV) run ruff format .

.PHONY: format-check
format-check: ## Check formatting without writing
	pnpm format:check
	cd $(API_DIR) && $(UV) run ruff format --check .

.PHONY: lint
lint: ## Static linting (TS + Python)
	pnpm lint
	cd $(API_DIR) && $(UV) run ruff check .

.PHONY: typecheck
typecheck: ## TypeScript + Python type checks
	pnpm typecheck
	cd $(API_DIR) && $(UV) run mypy src

.PHONY: test
test: ## Unit and integration tests (requires infra up + test DB migrated)
	cd $(API_DIR) && $(UV) run pytest
	pnpm test

.PHONY: test-db
test-db: db-up db-init migrate-test ## Provision infra + test DB, then run DB-backed tests
	cd $(API_DIR) && $(UV) run pytest

.PHONY: test-e2e
test-e2e: ## Playwright end-to-end tests (best-effort; requires servers running)
	cd $(WEB_DIR) && pnpm test:e2e

.PHONY: secret-scan
secret-scan: ## Scan working tree for secrets (no-op with a warning if gitleaks is absent)
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-git --config .gitleaks.toml --redact || echo "gitleaks not installed — skipping local secret scan (CI enforces it)"

.PHONY: check
check: format-check lint typecheck test ## format-check + lint + typecheck + test

# ---- Code generation ---------------------------------------------------------

.PHONY: openapi
openapi: ## Export the OpenAPI document from the FastAPI app
	$(API_RUN) python -m hadp_api.scripts.export_openapi

.PHONY: gen-client
gen-client: openapi ## Regenerate the typed TypeScript API client from OpenAPI
	pnpm gen:client

# ---- Dev servers -------------------------------------------------------------

.PHONY: api-dev
api-dev: ## Run the FastAPI dev server
	$(API_RUN) uvicorn hadp_api.main:app --reload --port 8000

.PHONY: web-dev
web-dev: ## Run the Next.js dev server
	cd $(WEB_DIR) && pnpm dev

.PHONY: web-build
web-build: ## Production build of the web app
	cd $(WEB_DIR) && pnpm build

.PHONY: smoke
smoke: ## Live happy-path smoke over HTTP (requires API on :8000 + seeded dev DB)
	$(API_RUN) python ../../scripts/smoke_api.py

.PHONY: worker-dev
worker-dev: ## Run the background worker
	cd $(WORKER_DIR) && $(UV) run python -m hadp_worker.main

.PHONY: dev
dev: db-up ## Start infra (then run api-dev / web-dev / worker-dev in separate shells)
	@echo "infra up. In separate shells: 'make api-dev', 'make web-dev', 'make worker-dev'"
