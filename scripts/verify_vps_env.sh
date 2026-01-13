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

# Prefer new naming convention
check_var "MCP_API_KEY_C" true
check_var "MCP_API_KEY_L" false

# Detect legacy names and warn (but don't require renaming)
if [ -n "$MCPAPIKEYC" ] && [ -z "$MCP_API_KEY_C" ]; then
    echo "  ⚠️  MCPAPIKEYC is set (legacy name). Consider: MCP_API_KEY_C=\$MCPAPIKEYC"
fi
if [ -n "$MCPAPIKEYL" ] && [ -z "$MCP_API_KEY_L" ]; then
    echo "  ⚠️  MCPAPIKEYL is set (legacy name). Consider: MCP_API_KEY_L=\$MCPAPIKEYL"
fi

# Check MCP enable flag
check_var "MCP_ENABLED" false
if [ -z "$MCP_ENABLED" ]; then
    echo "     → MCP_ENABLED not set (will default to 'true')"
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

# Verify MEMORY_DSN format and context
if [ -n "$MEMORY_DSN" ]; then
    if [[ "$MEMORY_DSN" == postgresql://* ]]; then
        echo "  ✅ MEMORY_DSN format: Valid PostgreSQL DSN"
        
        # Check if it's host mode or compose mode
        if [[ "$MEMORY_DSN" == *"127.0.0.1"* ]] || [[ "$MEMORY_DSN" == *"localhost"* ]]; then
            echo "     → Host mode (127.0.0.1 or localhost)"
        elif [[ "$MEMORY_DSN" == *"l9-postgres"* ]]; then
            echo "     → Compose mode (l9-postgres service)"
        fi
    else
        echo "  ❌ MEMORY_DSN format: Invalid (should start with postgresql://)"
        ALL_GOOD=false
    fi
fi

check_var "DATABASE_URL" false

echo ""

# ============================================================================
# OpenAI Configuration (CRITICAL for embeddings)
# ============================================================================
echo "🤖 OpenAI Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "OPENAI_API_KEY" true
check_var "OPENAI_MODEL" false
if [ -z "$OPENAI_MODEL" ]; then
    echo "     → OPENAI_MODEL not set (will use 'gpt-4o')"
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

echo ""

# ============================================================================
# Neo4j (Optional but part of full stack)
# ============================================================================
echo "🕸️  Neo4j Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "NEO4J_PASSWORD" false
if [ -n "$NEO4J_PASSWORD" ]; then
    check_var "NEO4J_USER" false
    check_var "NEO4J_URI" false
    echo "     → Neo4j graph enabled"
else
    echo "     → Neo4j not configured (Postgres-only mode OK)"
fi

echo ""

# ============================================================================
# Redis (Optional)
# ============================================================================
echo "📦 Redis Configuration:"
echo "─────────────────────────────────────────────────────────────────"

check_var "REDIS_HOST" false
check_var "REDIS_PORT" false
if [ -z "$REDIS_HOST" ]; then
    echo "     → REDIS_HOST not set (optional, rate limiting disabled)"
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
# Quick Test Commands (dynamic, context-aware)
# ============================================================================
echo "📋 Quick Verification Commands:"
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "# Test API health (after rebuild):"
echo "curl -s http://127.0.0.1:8000/health | jq ."
echo ""
echo "# Test MCP memory save (requires API key):"
echo "export MCP_KEY=\$(grep MCP_API_KEY_C /opt/l9/.env | cut -d= -f2)"
echo "curl -X POST http://127.0.0.1:8000/memory/packet \\"
echo "  -H \"Authorization: Bearer \$MCP_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  --data '{\"content\": \"test\", \"kind\": \"note\"}'"
echo ""
echo "# Check container logs for startup:"
echo "docker compose logs l9-api --tail=30"
echo ""
