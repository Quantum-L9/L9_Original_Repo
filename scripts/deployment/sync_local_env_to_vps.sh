#!/bin/bash
# =============================================================================
# Sync Local .env Values to VPS
# Safely copies env var VALUES from local .env to VPS .env
# Preserves VPS-specific values (like passwords) if they exist
#
# Usage:
#   ./sync_local_env_to_vps.sh                    # Sync all vars
#   ./sync_local_env_to_vps.sh L9_EXECUTOR_API_KEY  # Sync one var
# =============================================================================

set -euo pipefail

VPS_HOST="admin@157.180.73.53"
VPS_REPO="/opt/l9"
LOCAL_ENV="$HOME/Projects/L9/.env"

if [ ! -f "$LOCAL_ENV" ]; then
    echo "❌ Local .env not found: $LOCAL_ENV"
    exit 1
fi

# If specific var provided, sync just that one
if [ $# -gt 0 ]; then
    VAR_NAME="$1"
    echo "Syncing $VAR_NAME from local to VPS..."

    # Get value from local
    LOCAL_VALUE=$(grep "^${VAR_NAME}=" "$LOCAL_ENV" 2>/dev/null | cut -d= -f2- | sed 's/^"//;s/"$//' || echo "")

    if [ -z "$LOCAL_VALUE" ]; then
        echo "❌ $VAR_NAME not found in local .env"
        exit 1
    fi

    echo "  Local value: ${LOCAL_VALUE:0:20}..."

    # Update on VPS
    ssh "$VPS_HOST" "cd $VPS_REPO && \
        if grep -q '^${VAR_NAME}=' .env 2>/dev/null; then \
            sed -i.bak 's|^${VAR_NAME}=.*|${VAR_NAME}=${LOCAL_VALUE}|' .env && \
            echo '✅ Updated $VAR_NAME in VPS .env'; \
        else \
            echo '${VAR_NAME}=${LOCAL_VALUE}' >> .env && \
            echo '✅ Added $VAR_NAME to VPS .env'; \
        fi"

    echo "✅ $VAR_NAME synced"
    exit 0
fi

# Sync all vars
echo "Syncing all env vars from local to VPS..."
echo ""

# Read local .env and sync each var
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue

    # Remove quotes from value
    value=$(echo "$value" | sed 's/^"//;s/"$//')

    echo "Syncing $key..."

    # Update on VPS (preserve existing if it looks like a secret)
    ssh "$VPS_HOST" "cd $VPS_REPO && \
        if grep -q '^${key}=' .env 2>/dev/null; then \
            # Check if existing value looks like a real secret (not placeholder)
            EXISTING=\$(grep '^${key}=' .env | cut -d= -f2-); \
            if [[ \"\$EXISTING\" =~ ^(YOUR_|replace_me|YOUR_) ]]; then \
                sed -i.bak 's|^${key}=.*|${key}=${value}|' .env && \
                echo '  ✅ Updated (was placeholder)'; \
            else \
                echo '  ⚠️  Skipped (VPS has non-placeholder value)'; \
            fi; \
        else \
            echo '${key}=${value}' >> .env && \
            echo '  ✅ Added'; \
        fi" || echo "  ❌ Failed"

done < "$LOCAL_ENV"

echo ""
echo "✅ Sync complete"
echo ""
echo "Restarting containers to load new env vars..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose stop && docker compose up -d"
echo "✅ Containers restarted"
