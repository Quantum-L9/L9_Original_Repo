#!/usr/bin/env bash
# =============================================================================
# L9 C1 Compose Deploy (ADR-0089)
# =============================================================================
# Usage: Run from C1 repo clone (e.g. /opt/l9). Expects:
#   - docker-compose.yml, docker-compose.prod.yml (symlinks to repo root or copies)
#   - .env.c1 (secrets, gitignored)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$REPO_ROOT"

ENV_FILE="${ENV_FILE:-.env.c1}"
# NO MISSING VARIABLES TOLERATED - fail before compose
REPO_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/check_compose_env.sh" "$ENV_FILE"

echo "L9 C1 deploy: $REPO_ROOT"
git pull origin main

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" up -d --remove-orphans
docker system prune -f

echo "Done."
