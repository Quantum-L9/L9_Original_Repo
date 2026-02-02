#!/usr/bin/env bash
set -euo pipefail

# Directory of this script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[deploy] Starting L9 deploy from $ROOT_DIR"

# Pull latest images (if using images) or build if you have Dockerfiles
if [ -f "docker-compose.yml" ] || [ -f "compose.yaml" ]; then
  echo "[deploy] Bringing up Docker stack"
  if [ -f "compose.yaml" ]; then
    docker compose -f compose.yaml up -d --build
  else
    docker compose -f docker-compose.yml up -d --build
  fi
else
  echo "[deploy] No compose file found; implement service startup here"
  exit 1
fi

echo "[deploy] L9 deploy completed successfully"
