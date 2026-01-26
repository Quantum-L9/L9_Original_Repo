#!/bin/bash
# =============================================================================
# L9 Environment Variable Verification - COMPLETE
# Compares VPS .env against .env.example to find ALL missing variables
#
# Usage:
#   ./verify_vps_env.sh         # Full verification with details
#   ./verify_vps_env.sh --quick # Quick check - summary only (for hooks)
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
QUICK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick|-q) QUICK=true; shift ;;
        *) shift ;;
    esac
done

log() {
    if [ "$QUICK" = false ]; then
        echo -e "$1"
    fi
}

log_always() {
    echo -e "$1"
}

if [ "$QUICK" = false ]; then
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  L9 Environment Variable Verification (COMPLETE)               ║${NC}"
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
    log_always "${RED}❌ ERROR: No .env file found${NC}"
    exit 1
fi

if [ ! -f "$EXAMPLE_FILE" ]; then
    log_always "${RED}❌ ERROR: .env.example not found at $EXAMPLE_FILE${NC}"
    exit 1
fi

log "📄 Checking: ${BLUE}$ENV_FILE${NC}"
log "📋 Template: ${BLUE}$EXAMPLE_FILE${NC}"
log ""

# Source the .env file
set -a
source "$ENV_FILE"
set +a

# Track status
MISSING_REQUIRED=()
MISSING_OPTIONAL=()
SET_VARS=()

# =============================================================================
# Define required vs optional variables
# =============================================================================

# CRITICAL - system won't work without these
REQUIRED_VARS=(
    "MEMORY_DSN"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "POSTGRES_DB"
    "OPENAI_API_KEY"
)

# IMPORTANT - features may be degraded without these
IMPORTANT_VARS=(
    "DATABASE_URL"
    "L9_API_KEY"
    "L9_EXECUTOR_API_KEY"
    "PERPLEXITY_API_KEY"
    "REDIS_HOST"
    "REDIS_PORT"
    "NEO4J_URL"
    "NEO4J_USER"
    "NEO4J_PASSWORD"
    "NEO4J_URI"
    "MCP_API_KEY"
    "MCP_API_KEY_C"
    "MCP_API_KEY_L"
    "SLACK_SIGNING_SECRET"
    "SLACK_BOT_TOKEN"
    "EMBEDDING_PROVIDER"
    "EMBEDDING_MODEL"
    "OPENAI_MODEL"
    "LOG_LEVEL"
    "API_HOST"
    "API_PORT"
)

# =============================================================================
# Check each variable
# =============================================================================

check_var() {
    local var_name=$1
    local value="${!var_name}"
    local is_required=false
    local is_important=false

    # Check if required
    for req in "${REQUIRED_VARS[@]}"; do
        if [ "$req" = "$var_name" ]; then
            is_required=true
            break
        fi
    done

    # Check if important
    for imp in "${IMPORTANT_VARS[@]}"; do
        if [ "$imp" = "$var_name" ]; then
            is_important=true
            break
        fi
    done

    if [ -z "$value" ]; then
        if [ "$is_required" = true ]; then
            log "  ${RED}❌ $var_name${NC} - ${RED}REQUIRED, NOT SET${NC}"
            MISSING_REQUIRED+=("$var_name")
        elif [ "$is_important" = true ]; then
            log "  ${YELLOW}⚠️  $var_name${NC} - ${YELLOW}IMPORTANT, not set${NC}"
            MISSING_OPTIONAL+=("$var_name")
        else
            log "  ${YELLOW}○  $var_name${NC} - not set (optional)"
            MISSING_OPTIONAL+=("$var_name")
        fi
    else
        # Mask sensitive values
        if [[ "$var_name" == *"KEY"* ]] || [[ "$var_name" == *"PASSWORD"* ]] || [[ "$var_name" == *"TOKEN"* ]] || [[ "$var_name" == *"SECRET"* ]]; then
            if [ ${#value} -gt 12 ]; then
                masked="${value:0:4}...${value: -4}"
            else
                masked="****"
            fi
            log "  ${GREEN}✅ $var_name${NC}: $masked"
        else
            log "  ${GREEN}✅ $var_name${NC}: $value"
        fi
        SET_VARS+=("$var_name")
    fi
}

# =============================================================================
# Full mode: Check by category
# =============================================================================
if [ "$QUICK" = false ]; then
    log "${YELLOW}🔍 Scanning .env.example for all variables...${NC}"
    log ""

    # Category: Database
    log "${BLUE}🗄️  Database Configuration:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in MEMORY_DSN DATABASE_URL POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB; do
        check_var "$var"
    done
    log ""

    # Category: API Keys
    log "${BLUE}🔑 API Keys:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in OPENAI_API_KEY PERPLEXITY_API_KEY L9_API_KEY L9_EXECUTOR_API_KEY; do
        check_var "$var"
    done
    log ""

    # Category: External Services
    log "${BLUE}🌐 External Services:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in NEO4J_URL NEO4J_USER NEO4J_PASSWORD REDIS_HOST REDIS_PORT QDRANT_HOST QDRANT_PORT; do
        check_var "$var"
    done
    log ""

    # Category: Slack
    log "${BLUE}💬 Slack Configuration:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in SLACK_APP_ENABLED SLACK_SIGNING_SECRET SLACK_BOT_TOKEN; do
        check_var "$var"
    done
    log ""

    # Category: Twilio
    log "${BLUE}📱 Twilio Configuration:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in TWILIO_ENABLED TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_SMS_NUMBER TWILIO_WHATSAPP_NUMBER; do
        check_var "$var"
    done
    log ""

    # Category: Integration Toggles
    log "${BLUE}🔧 Integration Toggles:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in MAC_AGENT_ENABLED EMAIL_ENABLED EMAIL_AGENT_ENABLED WABA_ENABLED; do
        check_var "$var"
    done
    log ""

    # Category: Feature Flags (L9_*)
    log "${BLUE}🚩 Feature Flags:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in L9_OBSERVABILITY L9_ENABLE_LEGACY_SLACK_ROUTER L9_GRAPH_AGENT_STATE L9_GRAPH_WM_SYNC L9_TOOL_PATTERN_EXTRACTION L9_USE_KERNELS L9_NEW_AGENT_INIT L9_STAGE3_MODULES L9_STAGE4_CONSOLIDATION L9_CONSOLIDATION_INTERVAL_HOURS L9_EMAIL_MULTI_ACCOUNT; do
        check_var "$var"
    done
    log ""

    # Category: API Config
    log "${BLUE}⚙️  API Configuration:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in API_HOST API_PORT LOG_LEVEL; do
        check_var "$var"
    done
    log ""

    # Category: MCP (if used)
    log "${BLUE}🔐 MCP Configuration:${NC}"
    log "─────────────────────────────────────────────────────────────────"
    for var in MCP_API_KEY_C MCP_API_KEY_L MCP_ENABLED EMBEDDING_PROVIDER EMBEDDING_MODEL OPENAI_MODEL; do
        check_var "$var"
    done
    log ""
else
    # Quick mode: Check required and important, plus count total
    for var in "${REQUIRED_VARS[@]}"; do
        check_var "$var"
    done
    for var in "${IMPORTANT_VARS[@]}"; do
        check_var "$var"
    done

    # Also count total vars from .env.example vs .env
    TOTAL_EXAMPLE=$(grep -cE "^[A-Z_]+=" "$EXAMPLE_FILE" 2>/dev/null || echo "0")
    TOTAL_ENV=$(grep -cE "^[A-Z_]+=" "$ENV_FILE" 2>/dev/null || echo "0")
fi

# =============================================================================
# Summary
# =============================================================================

TOTAL_VARS=$((${#SET_VARS[@]} + ${#MISSING_REQUIRED[@]} + ${#MISSING_OPTIONAL[@]}))

if [ "$QUICK" = true ]; then
    # Quick summary with accurate totals
    TOTAL_EXAMPLE=$(grep -cE "^[A-Z_]+=" "$EXAMPLE_FILE" 2>/dev/null || echo "0")
    TOTAL_ENV=$(grep -cE "^[A-Z_]+=" "$ENV_FILE" 2>/dev/null || echo "0")

    if [ ${#MISSING_REQUIRED[@]} -eq 0 ]; then
        log_always "${GREEN}✅ Env verify: ${#SET_VARS[@]} core vars set (${TOTAL_ENV}/${TOTAL_EXAMPLE} total)${NC}"
    else
        log_always "${RED}❌ Env verify: ${#MISSING_REQUIRED[@]} REQUIRED vars missing!${NC}"
        for var in "${MISSING_REQUIRED[@]}"; do
            log_always "   - $var"
        done
    fi
else
    # Full summary
    log ""
    log_always "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"

    if [ ${#MISSING_REQUIRED[@]} -eq 0 ]; then
        log_always "${BLUE}║${NC}  ${GREEN}✅ ALL REQUIRED VARIABLES SET${NC}                                ${BLUE}║${NC}"
    else
        log_always "${BLUE}║${NC}  ${RED}❌ ${#MISSING_REQUIRED[@]} REQUIRED VARIABLES MISSING${NC}                           ${BLUE}║${NC}"
    fi

    log_always "${BLUE}║${NC}                                                                ${BLUE}║${NC}"
    log_always "${BLUE}║${NC}  Set: ${GREEN}${#SET_VARS[@]}${NC} | Missing Required: ${RED}${#MISSING_REQUIRED[@]}${NC} | Missing Optional: ${YELLOW}${#MISSING_OPTIONAL[@]}${NC}  ${BLUE}║${NC}"
    log_always "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    log ""

    # Show missing variables with copy-paste help
    if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
        log_always "${RED}🚨 REQUIRED VARIABLES - Add these to .env:${NC}"
        log_always "─────────────────────────────────────────────────────────────────"
        for var in "${MISSING_REQUIRED[@]}"; do
            default=$(grep "^$var=" "$EXAMPLE_FILE" | cut -d= -f2-)
            log_always "${RED}$var=${default:-YOUR_VALUE_HERE}${NC}"
        done
        log_always ""
    fi

    if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
        log_always "${YELLOW}⚠️  OPTIONAL VARIABLES - Consider adding:${NC}"
        log_always "─────────────────────────────────────────────────────────────────"
        for var in "${MISSING_OPTIONAL[@]}"; do
            default=$(grep "^$var=" "$EXAMPLE_FILE" | cut -d= -f2-)
            log_always "$var=${default:-}"
        done
        log_always ""
    fi

    # Generate patch command
    if [ ${#MISSING_REQUIRED[@]} -gt 0 ] || [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
        log_always "${BLUE}📝 Quick Add Command:${NC}"
        log_always "─────────────────────────────────────────────────────────────────"
        log_always "# Run this to append missing variables to .env:"
        log_always "cat >> $ENV_FILE << 'EOF'"
        log_always ""
        log_always "# === Added by verify_vps_env.sh $(date +%Y-%m-%d) ==="
        for var in "${MISSING_REQUIRED[@]}"; do
            default=$(grep "^$var=" "$EXAMPLE_FILE" | cut -d= -f2-)
            log_always "$var=${default:-FILL_THIS_IN}"
        done
        for var in "${MISSING_OPTIONAL[@]}"; do
            default=$(grep "^$var=" "$EXAMPLE_FILE" | cut -d= -f2-)
            log_always "$var=${default:-}"
        done
        log_always "EOF"
        log_always ""
    fi
fi

# Exit with error if required vars missing
if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
    exit 1
fi

if [ "$QUICK" = false ]; then
    log_always "${GREEN}✅ Environment verification complete!${NC}"
fi
