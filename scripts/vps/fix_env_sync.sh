#!/bin/bash
# =============================================================================
# L9 VPS Env Sync Fix (Wrapper)
# Calls canonical fix_env_sync.sh from deployment directory
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CANONICAL_SCRIPT="$REPO_ROOT/scripts/deployment/fix_env_sync.sh"

if [[ -f "$CANONICAL_SCRIPT" ]]; then
    exec bash "$CANONICAL_SCRIPT" "$@"
else
    echo "❌ ERROR: Canonical script not found: $CANONICAL_SCRIPT"
    exit 1
fi
