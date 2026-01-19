#!/bin/bash
# =============================================================================
# L9 VPS Environment Verification
# Wrapper script for VPS deployment - calls canonical deployment script
#
# Usage:
#   ./verify_vps_env.sh         # Full verification with details
#   ./verify_vps_env.sh --quick # Quick check - summary only (for hooks)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Canonical script location
CANONICAL_SCRIPT="$REPO_ROOT/scripts/deployment/verify_vps_env.sh"

if [[ -f "$CANONICAL_SCRIPT" ]]; then
    exec bash "$CANONICAL_SCRIPT" "$@"
else
    # Fallback: minimal verification for VPS
    
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
    
    QUICK=false
    [[ "$1" == "--quick" || "$1" == "-q" ]] && QUICK=true
    
    # Determine paths
    if [ -f "/opt/l9/.env" ]; then
        ENV_FILE="/opt/l9/.env"
        EXAMPLE_FILE="/opt/l9/.env.example"
    elif [ -f "$REPO_ROOT/.env" ]; then
        ENV_FILE="$REPO_ROOT/.env"
        EXAMPLE_FILE="$REPO_ROOT/.env.example"
    else
        echo -e "${RED}❌ ERROR: No .env file found${NC}"
        exit 1
    fi
    
    if [ ! -f "$EXAMPLE_FILE" ]; then
        echo -e "${RED}❌ ERROR: .env.example not found${NC}"
        exit 1
    fi
    
    # Source the .env
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check critical vars
    REQUIRED_VARS=(
        "MEMORY_DSN"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "OPENAI_API_KEY"
    )
    
    MISSING=()
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            MISSING+=("$var")
        fi
    done
    
    if [ ${#MISSING[@]} -eq 0 ]; then
        if [ "$QUICK" = true ]; then
            echo -e "${GREEN}✅ Env verify: all required vars set${NC}"
        else
            echo -e "${GREEN}✅ ALL REQUIRED VARIABLES SET${NC}"
        fi
        exit 0
    else
        echo -e "${RED}❌ Missing required vars: ${MISSING[*]}${NC}"
        exit 1
    fi
fi
