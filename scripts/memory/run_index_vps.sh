#!/bin/bash
# L9 Index Command - VPS Version
# Runs at session start to sync repo structure to VPS memory

set -e

REPO_DIR="/Users/ib-mac/Projects/L9"
cd "$REPO_DIR" || exit 1

echo "📝 L9 Index: Exporting repository indexes..."
python3 tools/export_repo_indexes.py

echo ""
echo "🔗 L9 Index: Loading to VPS Neo4j + Memory..."
python3 scripts/load_indexes_to_neo4j_vps.py

echo ""
echo "✅ Index complete: Repo structure synced to VPS memory"
echo ""
echo "📊 Note: VPS memory audit runs automatically after index load"
