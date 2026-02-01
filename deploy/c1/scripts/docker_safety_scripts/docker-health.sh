#!/usr/bin/env bash
set -euo pipefail
BAD=$(docker compose ps --format json | jq -r '.[] | select(.Health != null and .Health != "healthy") | .Name')
[ -z "$BAD" ] || { echo "❌ Unhealthy services:"; echo "$BAD"; exit 1; }
echo "✅ All services healthy"
