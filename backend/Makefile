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

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install fmt verify test help
