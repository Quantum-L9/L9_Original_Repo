#!/usr/bin/env bash
set -euo pipefail
OUT="backup_$(date +%Y%m%d_%H%M).tgz"
docker run --rm \
  -v postgres_data:/postgres \
  -v neo4j_data:/neo4j \
  -v redis_data:/redis \
  -v grafana_data:/grafana \
  -v "$PWD":/backup \
  alpine sh -c "tar czf /backup/$OUT /postgres /neo4j /redis /grafana"
echo "📦 Backup written to $OUT"
