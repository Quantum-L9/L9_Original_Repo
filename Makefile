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

.PHONY: help dev test smoke lint deploy rollback logs clean ci-validate ci-spec ci-code docker-setup architecture-reports

# Configuration
VPS_HOST := 157.180.73.53
VPS_USER := admin
VPS_PATH := /opt/l9
COMPOSE_PROJECT := l9

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
	@echo "$(YELLOW)Docker:$(NC)"
	@echo "  make docker-setup  Setup Docker environment (.env from template)"
	@echo "  make smoke         Run Docker smoke test (pre-commit)"
	@echo "  make docker-up     Start Docker stack locally"
	@echo "  make docker-down   Stop Docker stack"
	@echo "  make docker-logs   Tail Docker logs"
	@echo "  make docker-clean  Remove all L9 Docker resources"
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
	@python -m pytest tests/ -v --tb=short

test-fast:
	@echo "$(GREEN)Running fast tests (no slow markers)...$(NC)"
	@python -m pytest tests/ -v --tb=short -m "not slow"

test-smoke:
	@echo "$(GREEN)Running smoke tests only...$(NC)"
	@python -m pytest tests/docker/test_stack_smoke.py -v --tb=short

lint:
	@echo "$(GREEN)Running ruff linter...$(NC)"
	@python -m ruff check . --fix || true
	@python -m ruff format . || true

typecheck:
	@echo "$(GREEN)Running mypy type checker...$(NC)"
	@python -m mypy api/ core/ memory/ --ignore-missing-imports || true

# =============================================================================
# Docker (Local)
# =============================================================================

smoke:
	@echo "$(GREEN)Running Docker smoke test...$(NC)"
	@./scripts/precommit_docker_smoke.sh

docker-setup:
	@echo "$(GREEN)Setting up Docker environment...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from .env.docker template...$(NC)"; \
		cp .env.docker .env; \
		echo "$(RED)IMPORTANT: Edit .env and replace placeholder values!$(NC)"; \
	else \
		echo "$(YELLOW).env already exists. To reset: rm .env && make docker-setup$(NC)"; \
	fi
	@chmod +x scripts/setup-docker-env.sh 2>/dev/null || true
	@echo "$(GREEN)Run ./scripts/setup-docker-env.sh for interactive setup$(NC)"

docker-up:
	@echo "$(GREEN)Starting Docker stack...$(NC)"
	@docker compose up -d
	@echo "$(GREEN)Waiting for services to be healthy...$(NC)"
	@sleep 5
	@docker compose ps

docker-down:
	@echo "$(YELLOW)Stopping Docker stack...$(NC)"
	@docker compose down

docker-logs:
	@docker compose logs -f --tail=100

docker-clean:
	@echo "$(RED)Removing all L9 Docker resources...$(NC)"
	@docker compose down -v --remove-orphans
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

vps-logs:
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose logs -f --tail=100"

vps-status:
	@echo "$(GREEN)VPS Service Status:$(NC)"
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose ps && echo '' && curl -sf http://localhost:8000/health || echo 'API not responding'"

# =============================================================================
# Database
# =============================================================================

migrate:
	@echo "$(GREEN)Running migrations on VPS...$(NC)"
	@ssh $(VPS_USER)@$(VPS_HOST) "cd $(VPS_PATH) && docker compose exec -T l9-api python -c 'from memory.migration_runner import run_migrations; import asyncio; asyncio.run(run_migrations())'"

migrate-local:
	@echo "$(GREEN)Running migrations locally...$(NC)"
	@python -c "from memory.migration_runner import run_migrations; import asyncio; asyncio.run(run_migrations())"

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

cursor-start:
	@./scripts/cursor-start-session
