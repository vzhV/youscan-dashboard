.DEFAULT_GOAL := help
PRE_COMMIT = PATH="$$(uv tool dir --bin):$$PATH" pre-commit
REQUIRED_NODE_MAJOR = $(shell cat .nvmrc)
# Codegen: one export command and one openapi-typescript invocation (the `gen:api` package script) shared by both targets.
OPENAPI_EXPORT = cd backend && DATABASE_URL=postgresql+psycopg://unused/unused uv run --frozen python -m app.openapi_export
SCHEMA_TYPES = frontend/src/shared/api/schema.d.ts

.PHONY: help dev dev-db dev-db-down migrate seed install lint format typecheck test check node-check \
	backend-install backend-lint backend-format backend-typecheck backend-test backend-test-e2e backend-dev \
	frontend-install frontend-eslint frontend-lint frontend-format frontend-typecheck frontend-test frontend-build frontend-dev gen-api gen-api-check

help: ## List available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-20s %s\n", $$1, $$2}'

dev-db: ## Start local Postgres (dashboard, dashboard_test, dashboard_e2e)
	docker compose up -d --wait db

dev-db-down: ## Stop local Postgres
	docker compose down

migrate: ## Apply Alembic migrations to DATABASE_URL (or MIGRATIONS_DATABASE_URL)
	cd backend && uv run --frozen alembic upgrade head

seed: ## Import the sample files into DATABASE_URL (refuses a non-empty board)
	cd backend && uv run --frozen python -m app.cli seed

dev: ## Run backend (:8000) and frontend (Vite) together
	$(MAKE) -j2 backend-dev frontend-dev

install: backend-install frontend-install ## Install dependencies and pre-commit hooks
	@command -v pre-commit >/dev/null || uv tool install pre-commit
	$(PRE_COMMIT) install

lint: backend-lint frontend-lint ## Lint all code
format: backend-format frontend-format ## Format all code
typecheck: backend-typecheck frontend-typecheck ## Type-check all code
test: backend-test frontend-test ## Run unit and integration tests with coverage

check: backend-lint backend-typecheck backend-test frontend-lint frontend-typecheck frontend-test frontend-build gen-api-check ## Run every check CI runs
	$(PRE_COMMIT) run --all-files

backend-install: ## Install backend dependencies and create backend/.env if missing
	cd backend && uv sync --locked
	test -f backend/.env || cp backend/.env.example backend/.env

backend-lint: ## Ruff and import-linter on the backend
	cd backend && uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen lint-imports

backend-format: ## Format the backend with Ruff
	cd backend && uv run --frozen ruff check --fix . && uv run --frozen ruff format .

backend-typecheck: ## mypy --strict on the backend
	cd backend && uv run --frozen mypy app tests migrations

backend-test: ## Backend unit, integration and e2e tests with coverage gate
	cd backend && uv run --frozen pytest tests/unit tests/integration tests/e2e --cov=app --cov-report=term-missing

backend-test-e2e: ## Backend e2e tests (CLI against the test database)
	cd backend && uv run --frozen pytest tests/e2e

backend-dev: ## Run the backend with auto-reload on :8000
	cd backend && uv run --frozen uvicorn app.main:app --reload --port 8000

gen-api: node-check ## Regenerate frontend/src/shared/api/schema.d.ts from the backend OpenAPI schema
	$(OPENAPI_EXPORT) ../frontend/openapi.json
	cd frontend && pnpm --silent gen:api openapi.json -o $(CURDIR)/$(SCHEMA_TYPES)

gen-api-check: node-check ## Fail if the committed schema.d.ts differs from a fresh generation (writes nothing in the repo)
	@tmp=$$(mktemp -d) && trap 'rm -rf "$$tmp"' EXIT && \
		($(OPENAPI_EXPORT) "$$tmp/openapi.json") && \
		(cd frontend && pnpm --silent gen:api "$$tmp/openapi.json" -o "$$tmp/schema.d.ts" >/dev/null) && \
		{ cmp -s "$$tmp/schema.d.ts" $(SCHEMA_TYPES) || { echo "schema.d.ts is stale; run make gen-api"; exit 1; }; }

node-check:
	@node -e 'process.exit(process.versions.node.split(".")[0] === "$(REQUIRED_NODE_MAJOR)" ? 0 : 1)' || { echo "Node $(REQUIRED_NODE_MAJOR) is required (see .nvmrc). Run 'nvm use' and retry."; exit 1; }

frontend-install: node-check ## Install frontend dependencies from the lockfile
	cd frontend && pnpm install --frozen-lockfile

frontend-eslint: node-check ## ESLint only on the frontend
	cd frontend && pnpm lint

frontend-lint: node-check ## ESLint and Prettier check on the frontend
	cd frontend && pnpm lint && pnpm format:check

frontend-format: node-check ## Format the frontend with Prettier
	cd frontend && pnpm format

frontend-typecheck: node-check ## tsc --noEmit on the frontend
	cd frontend && pnpm typecheck

frontend-test: node-check ## Frontend unit and integration tests with coverage gate
	cd frontend && pnpm test

frontend-build: node-check ## Production build of the frontend
	cd frontend && pnpm build

frontend-dev: node-check ## Run the Vite dev server (proxies /api to the backend)
	cd frontend && pnpm dev
