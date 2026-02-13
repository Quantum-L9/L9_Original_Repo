#!/bin/bash
# =============================================================================
# L9 Secrets Verification and Sync Script
# =============================================================================
# Compares local .env files against AWS Secrets Manager and syncs missing secrets.
#
# Usage:
#   ./verify_and_sync_aws_secrets.sh              # Verify only (dry-run)
#   ./verify_and_sync_aws_secrets.sh --sync       # Sync missing to AWS
#   ./verify_and_sync_aws_secrets.sh --list-aws   # List all AWS secrets
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions
#   - secretsmanager:GetSecretValue, secretsmanager:ListSecrets
#   - secretsmanager:CreateSecret, secretsmanager:PutSecretValue (for --sync)
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PREFIX="${AWS_SECRETS_PREFIX:-l9}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
log_success() { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
log_warn() { printf "${YELLOW}[MISSING]${NC} %s\n" "$1"; }
log_error() { printf "${RED}[ERROR]${NC} %s\n" "$1"; }
log_header() { printf "\n${CYAN}═══════════════════════════════════════════════════════════${NC}\n"; printf "${CYAN}  %s${NC}\n" "$1"; printf "${CYAN}═══════════════════════════════════════════════════════════${NC}\n\n"; }

# Options
SYNC_MODE=false
LIST_AWS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --sync)
            SYNC_MODE=true
            shift
            ;;
        --list-aws)
            LIST_AWS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--sync] [--list-aws]"
            echo ""
            echo "Options:"
            echo "  --sync      Sync missing secrets from .env to AWS"
            echo "  --list-aws  List all secrets currently in AWS"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# ENV FILES TO CHECK
# =============================================================================
declare -a ENV_FILES=(
    "$REPO_ROOT/.env"
    "$REPO_ROOT/.env.vps"
    "$REPO_ROOT/.env.docker"
    "$REPO_ROOT/mcp_memory/.env"
)

# =============================================================================
# NON-SECRET CONFIG (should NOT go to AWS)
# =============================================================================
declare -a NON_SECRETS=(
    "L9_SECRETS_PROVIDER"
    "AWS_REGION"
    "AWS_SECRETS_PREFIX"
    "AWS_SECRETS_CACHE_TTL"
    "AWS_SECRETS_FALLBACK_TO_ENV"
    "LOG_LEVEL"
    "DEBUG"
    "ENVIRONMENT"
    "MCPMEMORYENABLED"
    "C1_HOST"
    "VPS_HOST"
    "POSTGRES_USER"
    "POSTGRES_DB"
    "NEO4J_USER"
    "REDIS_HOST"
    "REDIS_PORT"
    "NEO4J_HOST"
    "NEO4J_PORT"
    "POSTGRES_HOST"
    "POSTGRES_PORT"
    "API_HOST"
    "API_PORT"
    "MCP_MEMORY_PORT"
    "EMBEDDING_PROVIDER"
    "EMBEDDING_MODEL"
    "LLM_MODEL"
    "LLM_PROVIDER"
)

# =============================================================================
# FUNCTIONS
# =============================================================================

# Get all secrets from AWS
get_aws_secrets() {
    aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --filters "Key=name,Values=${AWS_PREFIX}/" \
        --query 'SecretList[].Name' \
        --output text 2>/dev/null | tr '\t' '\n' | sed "s|${AWS_PREFIX}/||g" | sort
}

# Check if secret exists in AWS
secret_exists_in_aws() {
    local name="$1"
    aws secretsmanager describe-secret \
        --region "$AWS_REGION" \
        --secret-id "${AWS_PREFIX}/${name}" \
        &>/dev/null
}

# Create or update secret in AWS
sync_secret_to_aws() {
    local name="$1"
    local value="$2"

    if secret_exists_in_aws "$name"; then
        aws secretsmanager put-secret-value \
            --region "$AWS_REGION" \
            --secret-id "${AWS_PREFIX}/${name}" \
            --secret-string "$value" \
            &>/dev/null
        echo "updated"
    else
        aws secretsmanager create-secret \
            --region "$AWS_REGION" \
            --name "${AWS_PREFIX}/${name}" \
            --secret-string "$value" \
            --tags "Key=Application,Value=L9" "Key=ManagedBy,Value=verify_and_sync_secrets" \
            &>/dev/null
        echo "created"
    fi
}

# Check if variable is a non-secret config
is_non_secret() {
    local var="$1"
    for ns in "${NON_SECRETS[@]}"; do
        if [[ "$var" == "$ns" ]]; then
            return 0
        fi
    done
    return 1
}

# =============================================================================
# MAIN
# =============================================================================

# List AWS secrets mode
if $LIST_AWS; then
    log_header "AWS Secrets Manager Contents (${AWS_PREFIX}/*)"

    secrets=$(get_aws_secrets)
    if [[ -z "$secrets" ]]; then
        log_warn "No secrets found with prefix '${AWS_PREFIX}/'"
    else
        count=0
        while IFS= read -r secret; do
            if [[ -n "$secret" ]]; then
                log_success "$secret"
                ((count++))
            fi
        done <<< "$secrets"
        echo ""
        log_info "Total: $count secrets in AWS"
    fi
    exit 0
fi

# Verification mode
log_header "L9 Secrets Verification"
log_info "AWS Region: $AWS_REGION"
log_info "AWS Prefix: $AWS_PREFIX"
log_info "Sync Mode: $SYNC_MODE"

# Get current AWS secrets
log_header "Step 1: Fetching AWS Secrets"
AWS_SECRETS=$(get_aws_secrets)
AWS_COUNT=$(echo "$AWS_SECRETS" | grep -c . || echo 0)
log_info "Found $AWS_COUNT secrets in AWS Secrets Manager"

# Collect all env variables from all files
log_header "Step 2: Scanning Local .env Files"
declare -A ALL_ENV_VARS
declare -A VAR_SOURCE

for env_file in "${ENV_FILES[@]}"; do
    if [[ -f "$env_file" ]]; then
        rel_path="${env_file#$REPO_ROOT/}"
        log_info "Reading: $rel_path"

        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue

            # Clean key (remove export prefix if present)
            key=$(echo "$key" | sed 's/^export //')

            # Store variable and its source
            ALL_ENV_VARS["$key"]="$value"
            VAR_SOURCE["$key"]="$rel_path"
        done < <(grep -v '^#' "$env_file" 2>/dev/null | grep '=' || true)
    else
        rel_path="${env_file#$REPO_ROOT/}"
        log_warn "Not found: $rel_path"
    fi
done

echo ""
log_info "Total unique variables found: ${#ALL_ENV_VARS[@]}"

# Compare and report
log_header "Step 3: Comparison Results"

MISSING_IN_AWS=()
IN_AWS=()
SKIPPED_NON_SECRET=()

for var in "${!ALL_ENV_VARS[@]}"; do
    # Skip non-secrets
    if is_non_secret "$var"; then
        SKIPPED_NON_SECRET+=("$var")
        continue
    fi

    # Check if in AWS
    if echo "$AWS_SECRETS" | grep -q "^${var}$"; then
        IN_AWS+=("$var")
    else
        MISSING_IN_AWS+=("$var")
    fi
done

# Sort arrays for consistent output
IFS=$'\n' IN_AWS=($(sort <<<"${IN_AWS[*]}")); unset IFS
IFS=$'\n' MISSING_IN_AWS=($(sort <<<"${MISSING_IN_AWS[*]}")); unset IFS
IFS=$'\n' SKIPPED_NON_SECRET=($(sort <<<"${SKIPPED_NON_SECRET[*]}")); unset IFS

# Report: In AWS
echo -e "${GREEN}✅ Already in AWS (${#IN_AWS[@]}):${NC}"
for var in "${IN_AWS[@]}"; do
    echo "   $var"
done

echo ""

# Report: Missing from AWS
echo -e "${YELLOW}⚠️  Missing from AWS (${#MISSING_IN_AWS[@]}):${NC}"
for var in "${MISSING_IN_AWS[@]}"; do
    source="${VAR_SOURCE[$var]:-unknown}"
    echo "   $var (from $source)"
done

echo ""

# Report: Skipped (non-secrets)
echo -e "${BLUE}ℹ️  Skipped non-secrets (${#SKIPPED_NON_SECRET[@]}):${NC}"
for var in "${SKIPPED_NON_SECRET[@]}"; do
    echo "   $var"
done

# Sync mode
if $SYNC_MODE && [[ ${#MISSING_IN_AWS[@]} -gt 0 ]]; then
    log_header "Step 4: Syncing Missing Secrets to AWS"

    for var in "${MISSING_IN_AWS[@]}"; do
        value="${ALL_ENV_VARS[$var]}"

        # Skip empty values
        if [[ -z "$value" ]]; then
            log_warn "Skipping $var (empty value)"
            continue
        fi

        # Skip placeholder values
        if [[ "$value" == "your-"* ]] || [[ "$value" == "changeme"* ]] || [[ "$value" == "placeholder"* ]]; then
            log_warn "Skipping $var (placeholder value)"
            continue
        fi

        log_info "Syncing: $var"
        result=$(sync_secret_to_aws "$var" "$value")
        log_success "$var → AWS ($result)"
    done
fi

# Summary
log_header "Summary"
echo "  In AWS:        ${#IN_AWS[@]}"
echo "  Missing:       ${#MISSING_IN_AWS[@]}"
echo "  Non-secrets:   ${#SKIPPED_NON_SECRET[@]}"
echo ""

if [[ ${#MISSING_IN_AWS[@]} -gt 0 ]] && ! $SYNC_MODE; then
    echo -e "${YELLOW}Run with --sync to add missing secrets to AWS${NC}"
    echo ""
    echo "  $0 --sync"
    echo ""
fi

# Exit with error if missing secrets (useful for CI)
if [[ ${#MISSING_IN_AWS[@]} -gt 0 ]]; then
    exit 1
fi

exit 0
