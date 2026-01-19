#!/bin/bash
# =============================================================================
# L9 VPS Environment Variable Sync
# Wrapper script for VPS deployment - calls canonical deployment script
#
# Usage:
#   ./sync_env_vars.sh           # Normal mode - add missing vars
#   ./sync_env_vars.sh --quiet   # Quiet mode - minimal output for hooks
#   ./sync_env_vars.sh --dry-run # Show what would be added
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Canonical script location
CANONICAL_SCRIPT="$REPO_ROOT/scripts/deployment/sync_env_vars.sh"

if [[ -f "$CANONICAL_SCRIPT" ]]; then
    exec bash "$CANONICAL_SCRIPT" "$@"
else
    # Fallback: inline implementation for VPS where deployment script might not exist
    
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
    
    # Determine paths - VPS primary
    if [ -f "/opt/l9/.env" ]; then
        ENV_FILE="/opt/l9/.env"
        EXAMPLE_FILE="/opt/l9/.env.example"
    elif [ -f "$REPO_ROOT/.env" ]; then
        ENV_FILE="$REPO_ROOT/.env"
        EXAMPLE_FILE="$REPO_ROOT/.env.example"
    else
        log_always "${RED}❌ ERROR: No .env file found${NC}"
        exit 1
    fi
    
    if [ ! -f "$EXAMPLE_FILE" ]; then
        log_always "${RED}❌ ERROR: .env.example not found${NC}"
        exit 1
    fi
    
    log "📄 Target: ${BLUE}$ENV_FILE${NC}"
    log "📋 Source: ${BLUE}$EXAMPLE_FILE${NC}"
    
    # Create temp file with existing variable names
    EXISTING_FILE=$(mktemp)
    grep -E "^[A-Z][A-Z0-9_]*=" "$ENV_FILE" 2>/dev/null | cut -d= -f1 | sort -u > "$EXISTING_FILE"
    
    # Find missing variables
    MISSING_FILE=$(mktemp)
    MISSING_LINES_FILE=$(mktemp)
    
    while IFS= read -r line; do
        case "$line" in
            \#*|"") continue ;;
        esac
        
        var_name=$(echo "$line" | grep -oE "^[A-Z][A-Z0-9_]*" || true)
        if [ -n "$var_name" ]; then
            if ! grep -q "^${var_name}$" "$EXISTING_FILE"; then
                echo "$var_name" >> "$MISSING_FILE"
                echo "$line" >> "$MISSING_LINES_FILE"
            fi
        fi
    done < "$EXAMPLE_FILE"
    
    MISSING_COUNT=$(wc -l < "$MISSING_FILE" 2>/dev/null | tr -d ' ')
    
    if [ "$MISSING_COUNT" -eq 0 ] || [ ! -s "$MISSING_FILE" ]; then
        log_always "${GREEN}✅ Env vars: all present${NC}"
        rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"
        exit 0
    fi
    
    if [ "$QUIET" = true ]; then
        log_always "${YELLOW}⚠️  Env vars: ${MISSING_COUNT} missing - adding...${NC}"
    else
        log_always "${YELLOW}Found ${MISSING_COUNT} missing variables${NC}"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_always "${YELLOW}DRY RUN - Would add:${NC}"
        cat "$MISSING_LINES_FILE"
        rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"
        exit 0
    fi
    
    # Add missing variables
    {
        echo ""
        echo "# === Added by sync_env_vars.sh $(date +%Y-%m-%d) ==="
        cat "$MISSING_LINES_FILE"
    } >> "$ENV_FILE"
    
    log_always "${GREEN}✅ Added ${MISSING_COUNT} env vars${NC}"
    
    rm -f "$EXISTING_FILE" "$MISSING_FILE" "$MISSING_LINES_FILE"
fi
