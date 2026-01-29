#!/usr/bin/env bash
set -euo pipefail
./scripts/docker-preflight.sh
./scripts/docker-clean.sh
docker compose build --no-cache
docker compose up -d
sleep 30
docker compose ps
