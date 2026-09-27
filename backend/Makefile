install: ## Install dependencies into .venv
	poetry install

fmt: ## Format and lint code
	ruff check --fix
	ruff format

verify: ## Lint, check formatting, and typecheck
	ruff check
	ruff format --check
	pyright

test: ## Run unit tests
	poetry run pytest tests/ -v

schema: ## Write JSON Schemas for seed files to seeds/schema/
	poetry run python -m lender_match.cli schema

validate-seeds: ## Check that every seed file loads and passes the criterion check
	poetry run pytest tests/test_seed_files.py -q

migrate: ## Run alembic migrations
	@echo "Running migrations..."
	@poetry run alembic upgrade head

migration: ## Autogenerate a migration: make migration m="message"
	@if [ -z "$(m)" ]; then echo 'Usage: make migration m="message"'; exit 1; fi
	alembic revision --autogenerate -m "$(m)"

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install fmt verify test schema validate-seeds migrate migration help
