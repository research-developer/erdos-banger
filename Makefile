.DEFAULT_GOAL := help

UV ?= uv
RUN := $(UV) run

PYTEST_FAST_MARKERS := not requires_lean and not requires_network

.PHONY: help \
	sync sync-frozen \
	lock lock-check \
	format format-check \
	lint lint-fix \
	typecheck \
	test test-all cov \
	pre-commit hooks \
	smoke \
	ci

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\\n  make <target>\\n\\nTargets:\\n"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-16s %s\\n", $$1, $$2 }' $(MAKEFILE_LIST)

sync: ## Install dependencies
	$(UV) sync

sync-frozen: ## Install dependencies (frozen)
	$(UV) sync --frozen

lock: ## Update uv.lock
	$(UV) lock

lock-check: ## Verify uv.lock matches pyproject.toml
	$(UV) lock --check

format: ## Format code (ruff)
	$(RUN) ruff format .

format-check: ## Check formatting (ruff)
	$(RUN) ruff format . --check

lint: ## Lint (ruff)
	$(RUN) ruff check .

lint-fix: ## Lint and apply fixes (ruff)
	$(RUN) ruff check . --fix

typecheck: ## Type-check (mypy)
	$(RUN) mypy src/ tests/

test: ## Run tests (skip Lean + network)
	$(RUN) pytest -m "$(PYTEST_FAST_MARKERS)"

test-all: ## Run all tests
	$(RUN) pytest

cov: ## Coverage (skip Lean + network)
	$(RUN) pytest --cov=erdos --cov-fail-under=80 -m "$(PYTEST_FAST_MARKERS)"

pre-commit: ## Run all pre-commit hooks
	$(RUN) pre-commit run --all-files

hooks: ## Install git hooks (pre-commit)
	$(RUN) pre-commit install --install-hooks

smoke: ## Run CLI smoke test
	./scripts/smoke-test.sh

ci: format-check lint typecheck cov ## Run CI-equivalent checks
