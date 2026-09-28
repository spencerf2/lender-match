# Run backend targets under backend/'s mise config (Python version and venv)
# rather than the one active in the caller's shell; skipped without mise
MISE_EXEC := $(if $(shell command -v mise),mise exec --,)

install: ## Install backend and frontend dependencies and set up the git hook
	cd backend && $(MISE_EXEC) $(MAKE) install
	cd frontend && $(MAKE) install
	$(MAKE) setup-hooks

dev: ## Start Postgres and the backend container, then the frontend dev server in the foreground
	docker compose up -d --wait postgres backend
	cd frontend && $(MAKE) dev

fmt: ## Format and lint code
	cd backend && $(MISE_EXEC) $(MAKE) fmt

db-start: ## Start postgres container and wait until it accepts connections
	docker compose up -d --wait postgres

db-stop: ## Stop postgres container
	docker compose stop postgres

db-reset: ## Destroy postgres container and its data, recreate, re-run migrations
	docker compose down -v
	docker compose up -d --wait postgres
	cd backend && $(MISE_EXEC) $(MAKE) migrate

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.setup-hooks-done: scripts/setup-hooks.sh
	./scripts/setup-hooks.sh
	touch .setup-hooks-done

setup-hooks: .setup-hooks-done

.PHONY: install dev fmt db-start db-stop db-reset help setup-hooks
