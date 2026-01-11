#!/usr/bin/env bash
# =============================================================================
# L9 Environment Variable Checker
# Version: 1.0.0
#
# Validates that all required environment variables are set.
# Run before deployment to catch missing config early.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Required variables (deployment will fail without these)
REQUIRED_VARS=(
    "OPENAI_API_KEY"
    "L9_API_KEY"
    "POSTGRES_PASSWORD"
)

# Optional but recommended
RECOMMENDED_VARS=(
    "DATABASE_URL"
    "MEMORY_DSN"
    "POSTGRES_USER"
    "POSTGRES_DB"
)

ERRORS=0
WARNINGS=0

echo -e "${GREEN}Checking L9 environment variables...${NC}"
echo ""

# Check required variables
echo -e "${YELLOW}Required Variables:${NC}"
for var in "${REQUIRED_VARS[@]}"; do
    value="${!var:-}"
    if [[ -z "$value" ]]; then
        echo -e "  ${RED}✗${NC} $var - MISSING"
        ((ERRORS++))
    elif [[ "$value" == *"YOUR_"* ]] || [[ "$value" == *"_HERE"* ]]; then
        echo -e "  ${RED}✗${NC} $var - PLACEHOLDER (needs real value)"
        ((ERRORS++))
    else
        # Mask the value for security
        masked="${value:0:4}****${value: -4}"
        echo -e "  ${GREEN}✓${NC} $var = $masked"
    fi
done

echo ""

# Check recommended variables
echo -e "${YELLOW}Recommended Variables:${NC}"
for var in "${RECOMMENDED_VARS[@]}"; do
    value="${!var:-}"
    if [[ -z "$value" ]]; then
        echo -e "  ${YELLOW}○${NC} $var - not set (using default)"
        ((WARNINGS++))
    else
        echo -e "  ${GREEN}✓${NC} $var = (set)"
    fi
done

echo ""

# Check for localhost in DATABASE_URL (the bug we fixed)
if [[ -n "${DATABASE_URL:-}" ]]; then
    if [[ "$DATABASE_URL" == *"127.0.0.1"* ]] || [[ "$DATABASE_URL" == *"localhost"* ]]; then
        echo -e "${RED}⚠ WARNING: DATABASE_URL contains localhost!${NC}"
        echo -e "  This will fail inside Docker containers."
        echo -e "  Use service name 'postgres' instead of localhost."
        ((WARNINGS++))
    fi
fi

echo ""

# Summary
if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}✗ $ERRORS required variable(s) missing or invalid${NC}"
    echo -e "  Fix these before deploying!"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}○ $WARNINGS warning(s) - check recommended variables${NC}"
    exit 0
else
    echo -e "${GREEN}✓ All environment variables OK${NC}"
    exit 0
fi

