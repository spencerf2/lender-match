install: ## Install dependencies exactly as pinned in pnpm-lock.yaml
	pnpm install --frozen-lockfile

dev: ## Start the Vite dev server on port 5173
	pnpm dev

build: ## Typecheck and build the production bundle into dist/
	pnpm build

test: ## Run the Vitest suite once
	pnpm test

typecheck: ## Typecheck with tsc
	pnpm typecheck

verify: ## Typecheck, then test, then build
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) build

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install dev build test typecheck verify help
