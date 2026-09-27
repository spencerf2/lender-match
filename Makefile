# Run backend targets under backend/'s mise config (Python version and venv)
# rather than the one active in the caller's shell; skipped without mise
MISE_EXEC := $(if $(shell command -v mise),mise exec --,)

install: ## Install backend dependencies and set up the git hook
	cd backend && $(MISE_EXEC) $(MAKE) install
	$(MAKE) setup-hooks

fmt: ## Format and lint code
	cd backend && $(MISE_EXEC) $(MAKE) fmt

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.setup-hooks-done: scripts/setup-hooks.sh
	./scripts/setup-hooks.sh
	touch .setup-hooks-done

setup-hooks: .setup-hooks-done

.PHONY: install fmt help setup-hooks
