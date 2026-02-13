#!/bin/bash
# =============================================================================
# PUSH Local .env → AWS Secrets Manager
# =============================================================================
# Reads your local .env files and uploads secrets to AWS.
# Direction: LOCAL → AWS (one-way push)
#
# Usage:
#   ./push_env_to_aws.sh              # Dry-run: show what would be pushed
#   ./push_env_to_aws.sh --push       # Actually push to AWS
#   ./push_env_to_aws.sh --list-aws   # Show what's already in AWS
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PREFIX="${AWS_SECRETS_PREFIX:-l9}"

# Parse args
PUSH_MODE=false
LIST_MODE=false
for arg in "$@"; do
    case $arg in
        --push) PUSH_MODE=true ;;
        --list-aws) LIST_MODE=true ;;
        --help)
            echo "Usage: $0 [--push] [--list-aws]"
            echo "  --push      Push missing secrets from .env to AWS"
            echo "  --list-aws  List secrets already in AWS"
            exit 0 ;;
    esac
done

# Non-secret config vars (skip these)
NON_SECRETS="L9_SECRETS_PROVIDER AWS_REGION AWS_SECRETS_PREFIX AWS_SECRETS_CACHE_TTL AWS_SECRETS_FALLBACK_TO_ENV LOG_LEVEL DEBUG ENVIRONMENT MCPMEMORYENABLED C1_HOST VPS_HOST POSTGRES_USER POSTGRES_DB POSTGRES_HOST POSTGRES_PORT NEO4J_USER NEO4J_HOST NEO4J_PORT REDIS_HOST REDIS_PORT API_HOST API_PORT MCP_MEMORY_PORT EMBEDDING_PROVIDER EMBEDDING_MODEL LLM_MODEL LLM_PROVIDER HOST PORT WORKERS"

is_non_secret() {
    echo "$NON_SECRETS" | grep -qw "$1"
}

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  LOCAL .env → AWS Secrets Manager"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "AWS Region: $AWS_REGION"
echo "AWS Prefix: $AWS_PREFIX"
echo ""

# List mode
if $LIST_MODE; then
    echo "Secrets currently in AWS:"
    echo ""
    aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --query 'SecretList[].Name' \
        --output text | tr '\t' '\n' | grep "^${AWS_PREFIX}/" | sed "s|${AWS_PREFIX}/||" | sort | while read -r s; do
        echo "  ✅ $s"
    done
    echo ""
    exit 0
fi

# Get AWS secrets into a temp file for fast lookup
AWS_SECRETS_FILE=$(mktemp)
aws secretsmanager list-secrets \
    --region "$AWS_REGION" \
    --query 'SecretList[].Name' \
    --output text | tr '\t' '\n' | grep "^${AWS_PREFIX}/" | sed "s|${AWS_PREFIX}/||" > "$AWS_SECRETS_FILE" 2>/dev/null || true

AWS_COUNT=$(wc -l < "$AWS_SECRETS_FILE" | tr -d ' ')
echo "Found $AWS_COUNT secrets already in AWS"
echo ""

# Scan .env files
echo "Scanning local .env files..."
echo ""

ENV_FILES="$REPO_ROOT/.env $REPO_ROOT/.env.vps $REPO_ROOT/.env.docker $REPO_ROOT/mcp_memory/.env"

MISSING_FILE=$(mktemp)
EXISTING_FILE=$(mktemp)
SKIPPED_FILE=$(mktemp)
VALUES_FILE=$(mktemp)

for env_file in $ENV_FILES; do
    if [[ -f "$env_file" ]]; then
        rel="${env_file#$REPO_ROOT/}"
        echo "  Reading: $rel"

        grep -v '^#' "$env_file" 2>/dev/null | grep '=' | while IFS='=' read -r key value; do
            # Clean key
            key=$(echo "$key" | sed 's/^export //' | tr -d ' ')
            [[ -z "$key" ]] && continue

            # Skip non-secrets
            if is_non_secret "$key"; then
                echo "$key" >> "$SKIPPED_FILE"
                continue
            fi

            # Check if in AWS
            if grep -qx "$key" "$AWS_SECRETS_FILE" 2>/dev/null; then
                echo "$key" >> "$EXISTING_FILE"
            else
                echo "$key" >> "$MISSING_FILE"
                echo "${key}=${value}" >> "$VALUES_FILE"
            fi
        done
    else
        rel="${env_file#$REPO_ROOT/}"
        echo "  Not found: $rel"
    fi
done

echo ""

# Deduplicate
sort -u "$EXISTING_FILE" -o "$EXISTING_FILE" 2>/dev/null || true
sort -u "$MISSING_FILE" -o "$MISSING_FILE" 2>/dev/null || true
sort -u "$SKIPPED_FILE" -o "$SKIPPED_FILE" 2>/dev/null || true

EXISTING_COUNT=$(wc -l < "$EXISTING_FILE" 2>/dev/null | tr -d ' ' || echo 0)
MISSING_COUNT=$(wc -l < "$MISSING_FILE" 2>/dev/null | tr -d ' ' || echo 0)
SKIPPED_COUNT=$(wc -l < "$SKIPPED_FILE" 2>/dev/null | tr -d ' ' || echo 0)

echo "═══════════════════════════════════════════════════════════"
echo "  Results"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "✅ Already in AWS ($EXISTING_COUNT):"
cat "$EXISTING_FILE" 2>/dev/null | while read -r v; do echo "   $v"; done || true
echo ""

echo "⚠️  MISSING from AWS - need to push ($MISSING_COUNT):"
cat "$MISSING_FILE" 2>/dev/null | while read -r v; do echo "   $v"; done || true
echo ""

echo "ℹ️  Skipped non-secrets ($SKIPPED_COUNT):"
cat "$SKIPPED_FILE" 2>/dev/null | while read -r v; do echo "   $v"; done || true
echo ""

# Push mode
if $PUSH_MODE && [[ $MISSING_COUNT -gt 0 ]]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "  Pushing to AWS..."
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    cat "$VALUES_FILE" 2>/dev/null | while IFS='=' read -r key value; do
        [[ -z "$key" ]] && continue
        [[ -z "$value" ]] && continue
        [[ "$value" == "your-"* ]] && echo "  ⏭️  Skipping $key (placeholder)" && continue
        [[ "$value" == "changeme"* ]] && echo "  ⏭️  Skipping $key (placeholder)" && continue

        echo "  Pushing: $key"

        # Check if exists (update) or create new
        if aws secretsmanager describe-secret --region "$AWS_REGION" --secret-id "${AWS_PREFIX}/${key}" &>/dev/null; then
            aws secretsmanager put-secret-value \
                --region "$AWS_REGION" \
                --secret-id "${AWS_PREFIX}/${key}" \
                --secret-string "$value" &>/dev/null
            echo "  ✅ Updated: $key"
        else
            aws secretsmanager create-secret \
                --region "$AWS_REGION" \
                --name "${AWS_PREFIX}/${key}" \
                --secret-string "$value" \
                --tags "Key=Application,Value=L9" &>/dev/null
            echo "  ✅ Created: $key"
        fi
    done
    echo ""
fi

# Cleanup
rm -f "$AWS_SECRETS_FILE" "$MISSING_FILE" "$EXISTING_FILE" "$SKIPPED_FILE" "$VALUES_FILE"

# Summary
echo "═══════════════════════════════════════════════════════════"
echo "  Summary"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Already in AWS:  $EXISTING_COUNT"
echo "  Missing:         $MISSING_COUNT"
echo "  Non-secrets:     $SKIPPED_COUNT"
echo ""

if [[ $MISSING_COUNT -gt 0 ]] && ! $PUSH_MODE; then
    echo "👉 To push missing secrets to AWS, run:"
    echo ""
    echo "   $0 --push"
    echo ""
fi
