# =============================================================================
# L9 Makefile - Unified Command Interface
# Version: 1.0.0
#
# Usage:
#   make help          - Show all available commands
#   make dev           - Start local development server
#   make test          - Run all tests
#   make smoke         - Run Docker smoke test
#   make deploy        - Deploy to VPS
#   make rollback      - Rollback to previous version
# =============================================================================

.PHONY: help dev test smoke lint deploy rollback logs clean ci-validate ci-spec ci-code docker-setup docker-env-check docker-up docker-up-prod docker-build-prod docker-down docker-logs docker-clean architecture-reports bug-detect validate-external-code try-run

# Configuration
VPS_HOST := 157.180.73.53
VPS_USER := admin
VPS_PATH := /opt/l9
COMPOSE_PROJECT_NAME ?= l9
# Hierarchical compose (ADR-0089): base + overlay, --env-file required (no missing vars tolerated)
COMPOSE_FILES_DEV := -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_FILES_PROD := -f docker-compose.yml -f docker-compose.prod.yml
ENV_FILE ?= .env
# Use python3 when python isn't in PATH (e.g. macOS homebrew)
PYTHON ?= python3

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# =============================================================================
# Help
# =============================================================================

help:
	@echo "$(GREEN)L9 Development & Deployment Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Local Development:$(NC)"
	@echo "  make dev           Start local dev server (requires venv + .env.local)"
	@echo "  make test          Run all pytest tests"
	@echo "  make test-fast     Run tests without slow markers"
	@echo "  make lint          Run linters (ruff)"
	@echo "  make typecheck     Run mypy type checking"
	@echo ""
	@echo "$(YELLOW)Docker (ADR-0089: base + dev/prod overlay, --env-file required):$(NC)"
	@echo "  make docker-setup     Setup .env from .env.template (no missing vars tolerated)"
	@echo "  make docker-up       Start dev stack (base + dev overlay)"
	@echo "  make docker-up-prod  Start prod stack (base + prod overlay)"
	@echo "  make docker-down     Stop dev stack"
	@echo "  make docker-logs     Tail dev stack logs"
	@echo "  make docker-build-prod  Build prod images (root Dockerfile, Dockerfile.mcp-memory)"
	@echo "  make docker-clean   Remove all L9 Docker resources"
	@echo "  make smoke          Run Docker smoke test (pre-commit)"
	@echo ""
	@echo "$(YELLOW)Deployment:$(NC)"
	@echo "  make deploy        Deploy to VPS (builds, syncs, restarts)"
	@echo "  make deploy-dry    Show what would be deployed (no changes)"
	@echo "  make rollback      Rollback to previous version on VPS"
	@echo "  make vps-logs      Tail VPS Docker logs"
	@echo "  make vps-status    Check VPS service status"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  make migrate       Run migrations on VPS"
	@echo "  make migrate-local Run migrations locally"
	@echo ""
	@echo "$(YELLOW)CI Validation (STRICT):$(NC)"
	@echo "  make ci-validate SPEC=x.yaml FILES='a.py b.py'  Run all CI gates"
	@echo "  make ci-spec SPEC=x.yaml                        Validate spec v2.5"
	@echo "  make ci-code SPEC=x.yaml FILES='a.py'           Validate code"
	@echo "  make ci-all-specs                               Validate ALL specs"
	@echo ""
	@echo "$(YELLOW)Cursor:$(NC)"
	@echo "  make cursor-start  Run Cursor session startup"
	@echo ""
	@echo "$(YELLOW)Reports:$(NC)"
	@echo "  make architecture-reports  Generate all architecture reports"
	@echo ""
	@echo "$(YELLOW)Validation:$(NC)"
	@echo "  make validate-external-code FILE=doc.md        Validate external AI code in markdown"
	@echo "  make validate-external-code FILE=\"--snippet 'code'\"  Validate a single snippet"
	@echo "  make try-run FILE=scripts/foo.py               Try-run a Python file (syntax+import+exec)"
	@echo "  make try-run FILE=scripts/foo.py MODE=--syntax-only   Syntax check only"
	@echo "  make try-run FILE=scripts/foo.py MODE=--import-only   Import check only"
	@echo "  make bug-detect                                Scan for config mismatches"
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@echo "  make clean         Clean Python cache and build artifacts"
	@echo "  make env-check     Validate environment variables"

# =============================================================================
# CI VALIDATION GATES (STRICT - NO FALLBACKS)
# =============================================================================

ci-validate:
	@echo "$(GREEN)Running ALL CI validation gates...$(NC)"
	@./services/research_factory/run_ci_gates.sh $(SPEC) $(FILES)

ci-spec:
	@echo "$(GREEN)Validating Module-Spec v2.5...$(NC)"
	@python3 services/research_factory/validate_spec_v25.py $(SPEC)

ci-code:
	@echo "$(GREEN)Validating generated code...$(NC)"
	@python3 services/research_factory/validate_codegen.py --spec $(SPEC) --files $(FILES)

ci-all-specs:
	@echo "$(GREEN)Validating ALL specs in repo...$(NC)"
	@python3 services/research_factory/validate_spec_v25.py --all

# =============================================================================
# Local Development
# =============================================================================

dev:
	@./scripts/dev_up.sh

test:
	@echo "$(GREEN)Running all tests...$(NC)"
	@$(PYTHON) -m pytest tests/ -v --tb=short

test-fast:
	@echo "$(GREEN)Running fast tests (no slow markers)...$(NC)"
	@$(PYTHON) -m pytest tests/ -v --tb=short -m "not slow"

test-smoke:
	@echo "$(GREEN)Running smoke tests only...$(NC)"
	@$(PYTHON) -m pytest tests/docker/test_stack_smoke.py -v --tb=short

lint:
	@echo "$(GREEN)Running ruff linter...$(NC)"
	@$(PYTHON) -m ruff check . --fix || true
	@$(PYTHON) -m ruff format . || true

typecheck:
	@echo "$(GREEN)Running mypy type checker...$(NC)"
	@$(PYTHON) -m mypy api/ core/ memory/ --ignore-missing-imports || true

# =============================================================================
# Docker (Local)
# =============================================================================

smoke:
	@echo "$(GREEN)Running Docker smoke test...$(NC)"
	@./scripts/precommit_docker_smoke.sh

docker-setup:
	@echo "$(GREEN)Setting up Docker environment (ADR-0089)...$(NC)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(YELLOW)Creating $(ENV_FILE) from .env.template...$(NC)"; \
		cp .env.template $(ENV_FILE); \
		echo "$(RED)IMPORTANT: Edit $(ENV_FILE) and set ALL required vars (POSTGRES_PASSWORD, NEO4J_PASSWORD, GRAFANA_PASSWORD, OPENAI_API_KEY, L9_API_KEY). NO MISSING VARIABLES TOLERATED.$(NC)"; \
	else \
		echo "$(YELLOW)$(ENV_FILE) already exists. To reset: rm $(ENV_FILE) && make docker-setup$(NC)"; \
	fi
	@chmod +x scripts/check_compose_env.sh 2>/dev/null || true
	@echo "$(GREEN)Validate: ./scripts/check_compose_env.sh $(ENV_FILE)$(NC)"

docker-env-check:
	@./scripts/check_compose_env.sh $(ENV_FILE)

docker-up: docker-env-check
	@echo "$(GREEN)Starting Docker stack (dev: base + dev overlay)...$(NC)"
	@docker compose $(COMPOSE_FILES_DEV) --env-file $(ENV_FILE) up -d
	@echo "$(GREEN)Waiting for services to be healthy...$(NC)"
	@sleep 5
	@docker compose $(COMPOSE_FILES_DEV) --env-file $(ENV_FILE) ps

docker-up-prod: docker-env-check
	@echo "$(GREEN)Starting Docker stack (prod: base + prod overlay)...$(NC)"
	@docker compose $(COMPOSE_FILES_PROD) --env-file $(ENV_FILE) up -d
	@sleep 5
	@docker compose $(COMPOSE_FILES_PROD) --env-file $(ENV_FILE) ps

docker-build-prod:
	@echo "$(GREEN)Building prod images (root Dockerfile, Dockerfile.mcp-memory)...$(NC)"
	@docker compose $(COMPOSE_FILES_PROD) --env-file $(ENV_FILE) build

docker-down:
	@echo "$(YELLOW)Stopping Docker stack (dev)...$(NC)"
	@docker compose $(COMPOSE_FILES_DEV) --env-file $(ENV_FILE) down

docker-logs:
	@docker compose $(COMPOSE_FILES_DEV) --env-file $(ENV_FILE) logs -f --tail=100

docker-clean:
	@echo "$(RED)Removing all L9 Docker resources...$(NC)"
	@docker compose $(COMPOSE_FILES_DEV) --env-file $(ENV_FILE) down -v --remove-orphans 2>/dev/null || true
	@docker compose $(COMPOSE_FILES_PROD) --env-file $(ENV_FILE) down -v --remove-orphans 2>/dev/null || true
	@docker system prune -f --filter "label=com.l9.*"

# =============================================================================
# Deployment
# =============================================================================

deploy: env-check ci-all-specs smoke
	@echo "$(GREEN)Deploying to VPS...$(NC)"
	@./scripts/10x_deploy.sh

deploy-dry:
	@echo "$(YELLOW)Dry run - showing what would be deployed...$(NC)"
	@rsync -avzn --delete \
		--exclude='.git' \
		--exclude='venv' \
		--exclude='__pycache__' \
		--exclude='.env*' \
		--exclude='*.pyc' \
		--exclude='.pytest_cache' \
		--exclude='.mypy_cache' \
		--exclude='.ruff_cache' \
		./ $(VPS_USER)@$(VPS_HOST):$(VPS_PATH)/

rollback:
	@echo "$(RED)Rolling back to previous version...$(NC)"
	@./scripts/rollback_vps.sh

# On VPS use prod overlay and .env.c1 (align with deploy/c1/deploy.sh)
VPS_ENV_FILE ?= .env.c1

vps-logs:
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose $(COMPOSE_FILES_PROD) --env-file $(VPS_ENV_FILE) logs -f --tail=100"

vps-status:
	@echo "$(GREEN)VPS Service Status:$(NC)"
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose $(COMPOSE_FILES_PROD) --env-file $(VPS_ENV_FILE) ps && echo '' && curl -sf http://localhost:8000/health || echo 'API not responding'"

# =============================================================================
# Database
# =============================================================================

migrate:
	@echo "$(GREEN)Running migrations on VPS...$(NC)"
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose $(COMPOSE_FILES_PROD) --env-file $(VPS_ENV_FILE) exec -T l9-api python -c 'from memory.migration_runner import run_migrations; import asyncio; asyncio.run(run_migrations())'"

migrate-local:
	@echo "$(GREEN)Running migrations locally...$(NC)"
	@$(PYTHON) -c "from memory.migration_runner import run_migrations; import asyncio; asyncio.run(run_migrations())"

# =============================================================================
# Utilities
# =============================================================================

clean:
	@echo "$(YELLOW)Cleaning Python cache...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Done.$(NC)"

env-check:
	@echo "$(GREEN)Checking environment variables...$(NC)"
	@./scripts/check_env.sh

# =============================================================================
# Architecture Reports
# =============================================================================

architecture-reports:
	@echo "$(GREEN)Generating architecture reports...$(NC)"
	@python3 -m tools.architecture_reports.main
	@echo "$(GREEN)Reports generated in reports/architecture/$(NC)"

# =============================================================================
# Cursor
# =============================================================================

# =============================================================================
# Bug Detection
# =============================================================================

bug-detect:
	@echo "$(GREEN)Scanning for configuration mismatches...$(NC)"
	@$(PYTHON) tools/bug_detection/find_config_mismatches.py
	@echo "$(GREEN)✅ Report: reports/bug_detection/config_mismatches.md$(NC)"

validate-external-code:  ## Validate external AI-generated code before integration
ifndef FILE
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make validate-external-code FILE=path/to/doc.md"
	@echo "  make validate-external-code FILE=\"--snippet 'from memory.foo import bar'\""
	@exit 1
endif
	@echo "$(GREEN)Validating external code against L9 repo...$(NC)"
	@$(PYTHON) tools/validation/validate_external_code.py $(FILE)

try-run:  ## Try-run a Python file: syntax + import + execute
ifndef FILE
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make try-run FILE=scripts/foo.py"
	@echo "  make try-run FILE=scripts/foo.py MODE=--syntax-only"
	@echo "  make try-run FILE=scripts/foo.py MODE=--import-only"
	@echo "  make try-run FILE=scripts/foo.py TIMEOUT=30"
	@exit 1
endif
	@$(PYTHON) tools/validation/try_run.py $(FILE) $(MODE) $(if $(TIMEOUT),--timeout $(TIMEOUT))

audit-exports:  ## Audit package __all__ vs imports (e.g. make audit-exports PACKAGE=memory)
	@$(PYTHON) tools/validation/audit_package_exports.py $(or $(PACKAGE),memory)

audit-all:  ## Audit ALL packages for export consistency → reports/audits/
	@$(PYTHON) tools/validation/audit_package_exports.py --all --report-dir reports/audits/ --consolidated reports/audits/CONSOLIDATED_AUDIT.md

audit-wiring:  ## Audit file wiring + API instantiation (e.g. make audit-wiring PACKAGE=memory)
	@$(PYTHON) tools/validation/audit_package_wiring.py $(or $(PACKAGE),memory)

audit-wiring-all:  ## Audit ALL packages for wiring + API → reports/audits/
	@$(PYTHON) tools/validation/audit_package_wiring.py --all --report-dir reports/audits/

audit-full:  ## Run ALL audit levels (A + B + C) across ALL packages
	@echo "=== Level A: Export Consistency ==="
	@$(PYTHON) tools/validation/audit_package_exports.py --all --report-dir reports/audits/ --consolidated reports/audits/CONSOLIDATED_AUDIT.md
	@echo ""
	@echo "=== Levels B + C: Wiring + API Instantiation ==="
	@$(PYTHON) tools/validation/audit_package_wiring.py --all --report-dir reports/audits/

triage:  ## Triage dead code for a package (e.g. make triage PACKAGE=memory)
	@$(PYTHON) tools/validation/triage_dead_code.py $(or $(PACKAGE),memory) --report reports/audits/$(or $(PACKAGE),memory)_triage.md

triage-all:  ## Triage dead code across ALL packages → reports/audits/TRIAGE_REPORT.md
	@$(PYTHON) tools/validation/triage_dead_code.py --all --report-dir reports/audits/ --report reports/audits/TRIAGE_REPORT.md

cursor-start:
	@./scripts/cursor-start-session
