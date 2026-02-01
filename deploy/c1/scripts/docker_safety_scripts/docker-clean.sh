#!/usr/bin/env bash
set -euo pipefail
docker compose down --remove-orphans
echo "✅ Containers stopped, volumes preserved"
