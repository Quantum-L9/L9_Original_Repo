#!/bin/bash
# Verify VPS Environment Variables for MCP Memory
# Run this on VPS before rebuilding to ensure all required vars are set

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  VPS Environment Variable Verification                         ║"
echo "║  Run from: /opt/l9                                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

ENV_FILE="/opt/l9/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

echo "📄 Reading: $ENV_FILE"
echo ""

# Source the .env file
set -a
source "$ENV_FILE"
set +a

# Track status
ALL_GOOD=true

# ============================================================================
# MCP Memory Variables (CRITICAL)
# ============================================================================
echo "🔐 MCP Memory Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var() {
    local var_name=$1
    local required=${2:-true}
    local value="${!var_name}"
    
    if [ -z "$value" ]; then
        if [ "$required" = "true" ]; then
            echo "  ❌ $var_name: NOT SET (REQUIRED)"
            ALL_GOOD=false
        else
            echo "  ⚠️  $var_name: NOT SET (optional)"
        fi
    else
        # Mask sensitive values
        if [[ "$var_name" == *"KEY"* ]] || [[ "$var_name" == *"PASSWORD"* ]]; then
            masked="${value:0:8}...${value: -4}"
            echo "  ✅ $var_name: $masked"
        else
            echo "  ✅ $var_name: $value"
        fi
    fi
}

check_var "MCP_API_KEY_C" true
check_var "MCP_API_KEY_L" false

# Check for legacy variable names (for backward compatibility)
if [ -z "$MCP_API_KEY_C" ] && [ -n "$MCPAPIKEYC" ]; then
    echo "  ⚠️  MCP_API_KEY_C not set, but MCPAPIKEYC found (legacy)"
    echo "     → Consider renaming: MCPAPIKEYC → MCP_API_KEY_C"
fi
if [ -z "$MCP_API_KEY_L" ] && [ -n "$MCPAPIKEYL" ]; then
    echo "  ⚠️  MCP_API_KEY_L not set, but MCPAPIKEYL found (legacy)"
    echo "     → Consider renaming: MCPAPIKEYL → MCP_API_KEY_L"
fi

check_var "MCPMEMORYENABLED" false
if [ -z "$MCPMEMORYENABLED" ]; then
    echo "     → Setting MCPMEMORYENABLED=true (default)"
    echo "MCPMEMORYENABLED=true" >> "$ENV_FILE"
fi

echo ""

# ============================================================================
# Database Configuration (CRITICAL)
# ============================================================================
echo "🗄️  Database Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "POSTGRES_USER" true
check_var "POSTGRES_PASSWORD" true
check_var "POSTGRES_DB" true
check_var "MEMORY_DSN" true
check_var "DATABASE_URL" false

# Verify MEMORY_DSN format
if [ -n "$MEMORY_DSN" ]; then
    if [[ "$MEMORY_DSN" == postgresql://* ]]; then
        echo "  ✅ MEMORY_DSN format: Valid PostgreSQL connection string"
    else
        echo "  ❌ MEMORY_DSN format: Invalid (should start with postgresql://)"
        ALL_GOOD=false
    fi
fi

echo ""

# ============================================================================
# OpenAI Configuration (CRITICAL for embeddings)
# ============================================================================
echo "🤖 OpenAI Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "OPENAI_API_KEY" true
check_var "OPENAI_MODEL" false
if [ -z "$OPENAI_MODEL" ]; then
    echo "     → OPENAI_MODEL not set (will use default)"
fi

echo ""

# ============================================================================
# Embedding Provider (CRITICAL)
# ============================================================================
echo "🔍 Embedding Provider:"
echo "─────────────────────────────────────────────────────────────────"

check_var "EMBEDDING_PROVIDER" false
if [ -z "$EMBEDDING_PROVIDER" ]; then
    echo "     → EMBEDDING_PROVIDER not set (will default to 'openai')"
fi

check_var "EMBEDDING_MODEL" false
if [ -z "$EMBEDDING_MODEL" ]; then
    echo "     → EMBEDDING_MODEL not set (will default to 'text-embedding-3-large')"
fi

echo ""

# ============================================================================
# L9 API Keys (for authentication)
# ============================================================================
echo "🔑 L9 API Keys:"
echo "─────────────────────────────────────────────────────────────────"

check_var "L9_API_KEY" false
check_var "L9_EXECUTOR_API_KEY" false

# If L9_EXECUTOR_API_KEY not set, suggest using MCP_API_KEY_C
if [ -z "$L9_EXECUTOR_API_KEY" ] && [ -n "$MCP_API_KEY_C" ]; then
    echo "     → L9_EXECUTOR_API_KEY not set, but MCP_API_KEY_C is set"
    echo "     → Consider: L9_EXECUTOR_API_KEY=\$MCP_API_KEY_C"
fi

echo ""

# ============================================================================
# Neo4j (Optional)
# ============================================================================
echo "🕸️  Neo4j Configuration (Optional):"
echo "─────────────────────────────────────────────────────────────────"

check_var "NEO4J_PASSWORD" false
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "     → Neo4j not configured (Postgres-only mode)"
else
    check_var "NEO4J_USER" false
    check_var "NEO4J_URL" false
fi

echo ""

# ============================================================================
# Redis (Optional but recommended)
# ============================================================================
echo "📦 Redis Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "REDIS_HOST" false
check_var "REDIS_PORT" false
if [ -z "$REDIS_HOST" ]; then
    echo "     → REDIS_HOST not set (will default to 'redis')"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════╗"
if [ "$ALL_GOOD" = true ]; then
    echo "║  ✅ ALL REQUIRED VARIABLES ARE SET                            ║"
    echo "║  Ready to rebuild with: docker compose build --no-cache l9-api ║"
else
    echo "║  ❌ SOME REQUIRED VARIABLES ARE MISSING                       ║"
    echo "║  Fix missing variables in .env before rebuilding             ║"
fi
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$ALL_GOOD" = false ]; then
    exit 1
fi

# ============================================================================
# Quick Test Commands
# ============================================================================
echo "📋 Quick Verification Commands:"
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "# Test database connection:"
echo "docker exec -it l9-postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'SELECT 1;'"
echo ""
echo "# Test MCP endpoint (after rebuild):"
echo "curl -ks https://157.180.73.53:9001/mcp/tools \\"
echo "  -H \"Authorization: Bearer \$MCP_API_KEY_C\" | jq ."
echo ""
echo "# Check container logs for MCP router:"
echo "docker compose logs l9-api | grep -i 'mcp.*router'"
echo ""
