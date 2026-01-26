#!/bin/bash
# =============================================================================
# scripts/secrets/setup_secrets_manager.sh
# =============================================================================
#
# One-time setup script to create/update secrets in AWS Secrets Manager.
# Reads from .env or current shell environment and populates AWS.
#
# Usage:
#   ./scripts/secrets/setup_secrets_manager.sh [options]
#
# Options:
#   --env <environment>     Environment name (default: dev)
#   --service <service>     Service name for tagging (default: l9-core)
#   --region <region>       AWS region (default: us-east-1)
#   --prefix <prefix>       Secret name prefix (default: l9)
#   --env-file <file>       Path to .env file (default: .env)
#   --dry-run               Show what would be done without making changes
#
# Requirements:
#   - AWS CLI installed and configured (with secretsmanager permissions)
#   - .env file or shell environment with secrets set
#
# GMP: GMP-122, GMP-123 AWS Secrets Manager Integration
# Updated: 2026-01-25 - Added 20 secrets (comprehensive coverage)
# =============================================================================

set -e

# =============================================================================
# Configuration Defaults
# =============================================================================
ENV="${ENV:-dev}"
SERVICE="${SERVICE:-l9-core}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SECRET_PREFIX="${SECRET_PREFIX:-l9}"
ENV_FILE="${ENV_FILE:-.env}"
DRY_RUN=false

# =============================================================================
# Colors for Output
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --prefix)
            SECRET_PREFIX="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --env <environment>     Environment name (default: dev)"
            echo "  --service <service>     Service name for tagging (default: l9-core)"
            echo "  --region <region>       AWS region (default: us-east-1)"
            echo "  --prefix <prefix>       Secret name prefix (default: l9)"
            echo "  --env-file <file>       Path to .env file (default: .env)"
            echo "  --dry-run               Show what would be done without making changes"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Header
# =============================================================================
echo ""
echo "========================================"
echo "  AWS Secrets Manager Setup"
echo "========================================"
echo ""
log_info "Environment: $ENV"
log_info "Service: $SERVICE"
log_info "Region: $AWS_REGION"
log_info "Prefix: $SECRET_PREFIX"
log_info "Env File: $ENV_FILE"
if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN MODE - No changes will be made"
fi
echo ""

# =============================================================================
# Check AWS CLI
# =============================================================================
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    log_error "Run 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

log_info "AWS CLI configured ✓"

# =============================================================================
# Load Environment File
# =============================================================================
if [ -f "$ENV_FILE" ]; then
    log_info "Loading secrets from $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
else
    log_warn "No .env file found at $ENV_FILE - using current environment"
fi

# =============================================================================
# Create/Update Secret Function
# =============================================================================
create_or_update_secret() {
    local key=$1
    local value=$2
    local secret_name="${SECRET_PREFIX}/${key}"

    if [ -z "$value" ]; then
        log_warn "Skipping $key (empty value)"
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        log_debug "[DRY RUN] Would upsert: $secret_name"
        return
    fi

    log_info "Processing: $secret_name"

    # Check if secret exists
    if aws secretsmanager describe-secret \
        --region "$AWS_REGION" \
        --secret-id "$secret_name" \
        --no-cli-pager \
        > /dev/null 2>&1; then

        # Secret exists - update it
        aws secretsmanager put-secret-value \
            --region "$AWS_REGION" \
            --secret-id "$secret_name" \
            --secret-string "$value" \
            --no-cli-pager \
            > /dev/null 2>&1

        log_info "  ✓ Updated existing secret"
    else
        # Secret doesn't exist - create it
        aws secretsmanager create-secret \
            --region "$AWS_REGION" \
            --name "$secret_name" \
            --secret-string "$value" \
            --description "L9 secret: $key (managed by setup script)" \
            --tags \
                Key=env,Value="$ENV" \
                Key=service,Value="$SERVICE" \
                Key=managed-by,Value=l9-setup \
            --no-cli-pager \
            > /dev/null 2>&1

        log_info "  ✓ Created new secret"
    fi
}

# =============================================================================
# CRITICAL SECRETS - Core Infrastructure
# =============================================================================
echo ""
log_info "Creating/updating CRITICAL secrets (Infrastructure)..."
echo "----------------------------------------"

create_or_update_secret "DATABASE_URL" "$DATABASE_URL"
create_or_update_secret "MEMORY_DSN" "$MEMORY_DSN"
create_or_update_secret "NEO4J_PASSWORD" "$NEO4J_PASSWORD"
create_or_update_secret "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
create_or_update_secret "REDIS_PASSWORD" "$REDIS_PASSWORD"

# =============================================================================
# CRITICAL SECRETS - LLM API Keys
# =============================================================================
echo ""
log_info "Creating/updating CRITICAL secrets (LLM APIs)..."
echo "----------------------------------------"

create_or_update_secret "OPENAI_API_KEY" "$OPENAI_API_KEY"
create_or_update_secret "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
create_or_update_secret "PERPLEXITY_API_KEY" "$PERPLEXITY_API_KEY"
create_or_update_secret "GEMINI_API_KEY" "$GEMINI_API_KEY"

# =============================================================================
# CRITICAL SECRETS - Authentication
# =============================================================================
echo ""
log_info "Creating/updating CRITICAL secrets (Auth)..."
echo "----------------------------------------"

create_or_update_secret "MCP_API_KEY" "$MCP_API_KEY"
create_or_update_secret "MCP_API_KEY_C" "$MCP_API_KEY_C"
create_or_update_secret "MCP_API_KEY_L" "$MCP_API_KEY_L"
create_or_update_secret "L9_EXECUTOR_API_KEY" "$L9_EXECUTOR_API_KEY"
create_or_update_secret "JWT_SECRET" "$JWT_SECRET"

# =============================================================================
# INTEGRATION SECRETS - Slack
# =============================================================================
echo ""
log_info "Creating/updating INTEGRATION secrets (Slack)..."
echo "----------------------------------------"

create_or_update_secret "SLACK_BOT_TOKEN" "$SLACK_BOT_TOKEN"
create_or_update_secret "SLACK_SIGNING_SECRET" "$SLACK_SIGNING_SECRET"
create_or_update_secret "SLACK_CLIENT_SECRET" "$SLACK_CLIENT_SECRET"
create_or_update_secret "SLACK_VERIFICATION_TOKEN" "$SLACK_VERIFICATION_TOKEN"

# =============================================================================
# INTEGRATION SECRETS - Communication
# =============================================================================
echo ""
log_info "Creating/updating INTEGRATION secrets (Communication)..."
echo "----------------------------------------"

create_or_update_secret "TWILIO_AUTH_TOKEN" "$TWILIO_AUTH_TOKEN"
create_or_update_secret "TWILIO_ACCOUNT_SID" "$TWILIO_ACCOUNT_SID"
create_or_update_secret "WABA_ACCESS_TOKEN" "$WABA_ACCESS_TOKEN"

# =============================================================================
# INTEGRATION SECRETS - Third-Party APIs
# =============================================================================
echo ""
log_info "Creating/updating INTEGRATION secrets (Third-Party APIs)..."
echo "----------------------------------------"

create_or_update_secret "GITHUB_TOKEN" "$GITHUB_TOKEN"
create_or_update_secret "MCP_GITHUB_TOKEN" "$MCP_GITHUB_TOKEN"
create_or_update_secret "NOTION_API_KEY" "$NOTION_API_KEY"
create_or_update_secret "MCP_NOTION_TOKEN" "$MCP_NOTION_TOKEN"
create_or_update_secret "GOOGLE_CALENDAR_API_KEY" "$GOOGLE_CALENDAR_API_KEY"
create_or_update_secret "GMAIL_API_KEY" "$GMAIL_API_KEY"

# =============================================================================
# OBSERVABILITY SECRETS
# =============================================================================
echo ""
log_info "Creating/updating OBSERVABILITY secrets..."
echo "----------------------------------------"

create_or_update_secret "GRAFANA_PASSWORD" "$GRAFANA_PASSWORD"
create_or_update_secret "L9_SLACK_WEBHOOK_URL" "$L9_SLACK_WEBHOOK_URL"
create_or_update_secret "L9_PAGERDUTY_INTEGRATION_KEY" "$L9_PAGERDUTY_INTEGRATION_KEY"
create_or_update_secret "L9_SECURITY_WEBHOOK_URL" "$L9_SECURITY_WEBHOOK_URL"

# =============================================================================
# SIGNING/ENCRYPTION SECRETS
# =============================================================================
echo ""
log_info "Creating/updating SIGNING secrets..."
echo "----------------------------------------"

create_or_update_secret "GPG_KEY" "$GPG_KEY"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "========================================"
echo "  Setup Complete"
echo "========================================"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN - No changes were made"
else
    log_info "Secrets have been populated in AWS Secrets Manager"
fi

echo ""
log_info "Next steps:"
echo "  1. Set L9_SECRETS_PROVIDER=aws in production environment"
echo "  2. Verify IAM role has secretsmanager:GetSecretValue permissions"
echo "  3. Optionally, set AWS_SECRETS_FALLBACK_TO_ENV=false in production"
echo ""

# =============================================================================
# List Created Secrets (optional)
# =============================================================================
if [ "$DRY_RUN" = false ]; then
    echo ""
    log_info "Secrets in AWS Secrets Manager (prefix: $SECRET_PREFIX):"
    SECRET_COUNT=0
    aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --filters Key=name,Values="$SECRET_PREFIX/" \
        --query "SecretList[].Name" \
        --output text \
        --no-cli-pager 2>/dev/null | tr '\t' '\n' | sort | while read -r secret; do
            echo "  - $secret"
            ((SECRET_COUNT++)) || true
        done

    TOTAL=$(aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --filters Key=name,Values="$SECRET_PREFIX/" \
        --query "length(SecretList)" \
        --output text \
        --no-cli-pager 2>/dev/null)
    echo ""
    log_info "Total secrets: $TOTAL"
fi

echo ""
log_info "Done!"
