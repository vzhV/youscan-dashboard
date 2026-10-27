.DEFAULT_GOAL := help
PRE_COMMIT = PATH="$$(uv tool dir --bin):$$PATH" pre-commit

.PHONY: help dev-db dev-db-down install check

help: ## List available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  %-16s %s\n", $$1, $$2}'

dev-db: ## Start local Postgres (dashboard, dashboard_test, dashboard_e2e)
	docker compose up -d --wait db

dev-db-down: ## Stop local Postgres
	docker compose down

install: ## Install dependencies and pre-commit hooks
	@command -v pre-commit >/dev/null || uv tool install pre-commit
	$(PRE_COMMIT) install

check: ## Run every check CI runs
	$(PRE_COMMIT) run --all-files
