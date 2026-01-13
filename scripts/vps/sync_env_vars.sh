#!/bin/bash
# =============================================================================
# L9 Environment Variable Sync
# Adds missing variables from .env.example to .env (with safe defaults)
# Run after git pull to ensure all new variables are present
# Compatible with bash 3.x (macOS) and bash 4.x+ (Linux)
#
# Usage:
#   ./sync_env_vars.sh           # Normal mode - add missing vars
#   ./sync_env_vars.sh --quiet   # Quiet mode - minimal output for hooks
#   ./sync_env_vars.sh --dry-run # Show what would be added
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
QUIET=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet|-q) QUIET=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) shift ;;
    esac
done

log() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

log_always() {
    echo -e "$1"
}

if [ "$QUIET" = false ]; then
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  L9 Environment Variable Sync                                  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
fi

# Determine paths
if [ -f "/opt/l9/.env" ]; then
    ENV_FILE="/opt/l9/.env"
    EXAMPLE_FILE="/opt/l9/.env.example"
elif [ -f "$REPO_ROOT/.env" ]; then
    ENV_FILE="$REPO_ROOT/.env"
    EXAMPLE_FILE="$REPO_ROOT/.env.example"
else
    log "${RED}❌ ERROR: No .env file found${NC}"
    exit 1
fi

if [ ! -f "$EXAMPLE_FILE" ]; then
    log "${RED}❌ ERROR: .env.example not found${NC}"
    exit 1
fi

log "📄 Target: ${BLUE}$ENV_FILE${NC}"
log "📋 Source: ${BLUE}$EXAMPLE_FILE${NC}"
log ""

# Create temp file with existing variable names
EXISTING_FILE=$(mktemp)
grep -E "^[A-Z][A-Z0-9_]*=" "$ENV_FILE" 2>/dev/null | cut -d= -f1 | sort -u > "$EXISTING_FILE"
EXISTING_COUNT=$(wc -l < "$EXISTING_FILE" | tr -d ' ')

log "Found ${GREEN}${EXISTING_COUNT}${NC} existing variables in .env"
log ""

# Find missing variables
MISSING_FILE=$(mktemp)
MISSING_LINES_FILE=$(mktemp)

while IFS= read -r line; do
    # Skip comments and empty lines
    case "$line" in
        \#*|"") continue ;;
    esac
    
    # Extract variable name
    var_name=$(echo "$line" | grep -oE "^[A-Z][A-Z0-9_]*" || true)
    if [ -n "$var_name" ]; then
        # Check if exists
        if ! grep -q "^${var_name}$" "$EXISTING_FILE"; then
            echo "$var_name" >> "$MISSING_FILE"
            echo "$line" >> "$MISSING_LINES_FILE"
        fi
    fi
done < "$EXAMPLE_FILE"

MISSING_COUNT=$(wc -l < "$MISSING_FILE" 2>/dev/null | tr -d ' ')

if [ "$MISSING_COUNT" -eq 0 ] || [ ! -s "$MISSING_FILE" ]; then
    if [ "$QUIET" = true ]; then
        echo -e "${GREEN}✅ Env vars: all present${NC}"
    else
        echo -e "${GREEN}✅ All variables already present! Nothing to add.${NC}"
    fi
    rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"
    exit 0
fi

# Show missing (even in quiet mode, this is important)
if [ "$QUIET" = true ]; then
    log_always "${YELLOW}⚠️  Env vars: ${MISSING_COUNT} missing - adding...${NC}"
else
    log_always "${YELLOW}Found ${MISSING_COUNT} missing variables:${NC}"
    while read -r var; do
        log_always "  - $var"
    done < "$MISSING_FILE"
    log_always ""
fi

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log_always "${YELLOW}DRY RUN - Would add these lines to $ENV_FILE:${NC}"
    log_always "─────────────────────────────────────────────────────────────────"
    log_always ""
    log_always "# === Added by sync_env_vars.sh $(date +%Y-%m-%d) ==="
    cat "$MISSING_LINES_FILE"
    log_always ""
    log_always "${YELLOW}Run without --dry-run to actually add them.${NC}"
    rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"
    exit 0
fi

# Add missing variables
log "${BLUE}Adding missing variables to $ENV_FILE...${NC}"
log ""

{
    echo ""
    echo "# === Added by sync_env_vars.sh $(date +%Y-%m-%d) ==="
    cat "$MISSING_LINES_FILE"
} >> "$ENV_FILE"

if [ "$QUIET" = true ]; then
    log_always "${GREEN}✅ Added ${MISSING_COUNT} env vars${NC}"
else
    log_always "${GREEN}✅ Added ${MISSING_COUNT} variables to .env${NC}"
    log_always ""
    log_always "${BLUE}Variables added:${NC}"
    while read -r var; do
        log_always "  ${GREEN}+ $var${NC}"
    done < "$MISSING_FILE"
    log_always ""
fi

# Cleanup
rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"

# Warn about secrets (skip in quiet mode)
if [ "$QUIET" = false ]; then
    echo -e "${YELLOW}⚠️  IMPORTANT: Review and update any placeholder values:${NC}"
    echo "   - Variables with 'YOUR_' need real values"
    echo "   - Variables with 'replace_me' need real values"
    echo "   - API keys need your actual keys"
    echo ""
    echo -e "Run ${BLUE}./scripts/verify_vps_env.sh${NC} to check all variables."
fi
