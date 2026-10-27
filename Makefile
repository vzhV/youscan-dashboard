.DEFAULT_GOAL := help
PRE_COMMIT = PATH="$$(uv tool dir --bin):$$PATH" pre-commit

.PHONY: help dev-db dev-db-down install lint format typecheck test check \
	backend-install backend-lint backend-format backend-typecheck backend-test backend-dev

help: ## List available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-16s %s\n", $$1, $$2}'

dev-db: ## Start local Postgres (dashboard, dashboard_test, dashboard_e2e)
	docker compose up -d --wait db

dev-db-down: ## Stop local Postgres
	docker compose down

install: backend-install ## Install dependencies and pre-commit hooks
	@command -v pre-commit >/dev/null || uv tool install pre-commit
	$(PRE_COMMIT) install

lint: backend-lint ## Lint all code
format: backend-format ## Format all code
typecheck: backend-typecheck ## Type-check all code
test: backend-test ## Run unit and integration tests with coverage

check: backend-lint backend-typecheck backend-test ## Run every check CI runs
	$(PRE_COMMIT) run --all-files

backend-install: ## Install backend dependencies and create backend/.env if missing
	cd backend && uv sync --locked
	test -f backend/.env || cp backend/.env.example backend/.env

backend-lint: ## Ruff and import-linter on the backend
	cd backend && uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen lint-imports

backend-format: ## Format the backend with Ruff
	cd backend && uv run --frozen ruff check --fix . && uv run --frozen ruff format .

backend-typecheck: ## mypy --strict on the backend
	cd backend && uv run --frozen mypy app tests

backend-test: ## Backend unit and integration tests with coverage gate
	cd backend && uv run --frozen pytest tests/unit tests/integration --cov=app --cov-report=term-missing

backend-dev: ## Run the backend with auto-reload on :8000
	cd backend && uv run --frozen uvicorn app.main:app --reload --port 8000
