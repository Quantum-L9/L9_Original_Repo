#!/bin/bash
# ============================================================================
# L9 Docker Validator
# ============================================================================
# Validates Dockerfile and docker-compose.yml for common issues.
#
# Usage:
#   ./scripts/docker-validator.sh [check-only]
#
# Options:
#   check-only   Run validation without attempting builds
#
# Exit codes:
#   0 = All validations passed
#   1 = Validation failed
# ============================================================================

set -e

MODE="${1:-full}"
ERRORS=0

echo "🐳 L9 Docker Validator"
echo "======================"

# Check Dockerfiles exist (ADR-0089: canonical at repo root only)
DOCKERFILES=("Dockerfile" "Dockerfile.mcp-memory")
FOUND_ANY=0

for df in "${DOCKERFILES[@]}"; do
    if [ -f "$df" ]; then
        echo "✅ $df found"
        FOUND_ANY=1

        # Check for Python version
        if grep -q "FROM python:3.12" "$df"; then
            echo "   ✅ Uses Python 3.12"
        elif grep -q "FROM python:3" "$df"; then
            PY_VERSION=$(grep "FROM python:" "$df" | head -1 | sed 's/.*python:\([0-9.]*\).*/\1/')
            echo "   ⚠️  Uses Python $PY_VERSION (L9 requires 3.12+)"
        fi
    fi
done

if [ $FOUND_ANY -eq 0 ]; then
    echo "❌ No Dockerfiles found (expected root Dockerfile and Dockerfile.mcp-memory)"
    ERRORS=$((ERRORS + 1))
fi

# Check docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in root directory"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ docker-compose.yml found"

    # Check for required services
    for svc in "l9-api" "postgres" "neo4j" "redis"; do
        if grep -q "$svc:" docker-compose.yml; then
            echo "✅ Service '$svc' defined"
        else
            echo "⚠️  Service '$svc' not found (may be optional)"
        fi
    done

    # Check for hardcoded secrets
    if grep -E "(password|secret|key):\s*['\"]?[^$\{]" docker-compose.yml | grep -v "NEO4J_AUTH=none" > /dev/null 2>&1; then
        echo "⚠️  Potential hardcoded secrets in docker-compose.yml"
    else
        echo "✅ No hardcoded secrets detected"
    fi
fi

# Check .dockerignore
if [ ! -f ".dockerignore" ]; then
    echo "⚠️  .dockerignore not found (recommended)"
else
    echo "✅ .dockerignore found"
fi

# Summary
echo ""
echo "======================"
if [ $ERRORS -gt 0 ]; then
    echo "❌ Docker validation FAILED ($ERRORS error(s))"
    exit 1
else
    echo "✅ Docker validation PASSED"
    exit 0
fi
