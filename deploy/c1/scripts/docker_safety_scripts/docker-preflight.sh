#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/opt/l9"
cd "$PROJECT_DIR"
ls docker-compose*.yml >/dev/null
[ -f .env ] || { echo "❌ .env missing"; exit 1; }
LEGACY=$(docker ps -a --format '{{.Names}}' | grep '^l9-' || true)
[ -z "$LEGACY" ] || { echo "❌ Legacy containers detected"; echo "$LEGACY"; exit 1; }
docker compose config >/dev/null
echo "✅ Preflight OK"
