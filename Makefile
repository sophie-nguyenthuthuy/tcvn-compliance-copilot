# =========================================================================
# TCVN Compliance Copilot — developer task runner
# =========================================================================
SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
.DEFAULT_GOAL  := help

COMPOSE        ?= docker compose
API_DIR        := apps/api
WEB_DIR        := apps/web

# ---- meta ----------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---- bootstrap -----------------------------------------------------------
.PHONY: bootstrap
bootstrap: ## Build images, run migrations, seed corpus (one-shot first-run)
	$(COMPOSE) build
	$(COMPOSE) up -d postgres redis minio
	$(COMPOSE) run --rm api alembic upgrade head
	$(COMPOSE) run --rm api python -m tcvn_copilot.rag.ingest --bootstrap

# ---- lifecycle -----------------------------------------------------------
.PHONY: up down restart logs ps
up: ## Start the full stack in the background
	$(COMPOSE) up -d

down: ## Stop the stack
	$(COMPOSE) down

restart: down up ## Restart everything

logs: ## Tail logs (Ctrl-C to exit)
	$(COMPOSE) logs -f --tail=200

ps: ## Show container status
	$(COMPOSE) ps

# ---- backend -------------------------------------------------------------
.PHONY: api-shell api-migrate api-revision worker-shell
api-shell: ## Open a shell inside the API container
	$(COMPOSE) exec api bash

api-migrate: ## Apply pending alembic migrations
	$(COMPOSE) exec api alembic upgrade head

api-revision: ## Create a new alembic revision (use MSG="...")
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(MSG)"

worker-shell: ## Open a shell inside the Celery worker
	$(COMPOSE) exec worker bash

# ---- corpus --------------------------------------------------------------
.PHONY: corpus-ingest corpus-validate
corpus-ingest: ## Re-ingest the full standards corpus
	$(COMPOSE) exec api python -m tcvn_copilot.rag.ingest --all

corpus-validate: ## Validate corpus manifest (hashes, clause IDs)
	$(COMPOSE) exec api python -m tcvn_copilot.rag.ingest --validate-only

# ---- testing -------------------------------------------------------------
.PHONY: test test-unit test-int test-e2e test-web
test: test-unit test-int test-web ## Run all non-e2e tests

test-unit: ## Backend unit tests
	cd $(API_DIR) && uv run pytest tests/unit -v

test-int: ## Backend integration tests (requires postgres + redis)
	cd $(API_DIR) && uv run pytest tests/integration -v

test-web: ## Frontend tests
	cd $(WEB_DIR) && pnpm test

test-e2e: ## End-to-end tests (requires `make up`)
	cd tests/e2e && pnpm exec playwright test

# ---- code quality --------------------------------------------------------
.PHONY: lint format typecheck
lint: ## Run all linters
	cd $(API_DIR) && uv run ruff check .
	cd $(API_DIR) && uv run ruff format --check .
	cd $(WEB_DIR) && pnpm lint

format: ## Auto-format code
	cd $(API_DIR) && uv run ruff format .
	cd $(API_DIR) && uv run ruff check --fix .
	cd $(WEB_DIR) && pnpm format

typecheck: ## Run static type checkers
	cd $(API_DIR) && uv run mypy src
	cd $(WEB_DIR) && pnpm typecheck

# ---- security ------------------------------------------------------------
.PHONY: audit secret-scan
audit: ## Run dependency vulnerability scans
	cd $(API_DIR) && uv run pip-audit
	cd $(WEB_DIR) && pnpm audit --prod

secret-scan: ## Scan for accidentally committed secrets
	gitleaks detect --no-banner --redact

# ---- cleanup -------------------------------------------------------------
.PHONY: clean nuke
clean: ## Remove caches and build artifacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) -prune -exec rm -rf {} +
	find . -type d \( -name .next -o -name .turbo -o -name dist -o -name build \) -prune -exec rm -rf {} +

nuke: down ## Stop stack AND wipe all volumes (DESTRUCTIVE)
	$(COMPOSE) down -v
