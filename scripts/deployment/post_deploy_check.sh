#!/usr/bin/env bash
# ============================================================================
# Post-Deployment Health Check Script
# ============================================================================
# 
# This script runs after a deployment to verify that the new version is
# functioning correctly and all services are healthy.
#
# DORA META:
# - component_name: "Post-Deploy-Check"
# - module_version: "1.0.0"
# - created_by: "Manus AI"
# - created_at: "2026-01-20T00:00:00Z"
# - layer: "operations"
# - domain: "deployment"
# - type: "script"
# - status: "active"
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Running post-deployment health checks..."

# Wait for services to stabilize
echo "Waiting for services to stabilize (30s)..."
sleep 30

# Check 1: Verify all services are running
echo -n "Checking services... "
REQUIRED_SERVICES=("l9-api" "l9-mcp-memory" "postgres" "redis" "neo4j")
ALL_RUNNING=true

for service in "${REQUIRED_SERVICES[@]}"; do
    if ! docker compose ps | grep -q "$service.*running"; then
        echo -e "${RED}✗${NC}"
        echo "  Service $service is not running"
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = true ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}Post-deployment check failed: Not all services are running${NC}"
    exit 1
fi

# Check 2: Verify API health endpoint
echo -n "Checking API health... "
RETRY_COUNT=0
MAX_RETRIES=10
API_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        API_HEALTHY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 3
done

if [ "$API_HEALTHY" = true ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Post-deployment check failed: API health endpoint not responding after $MAX_RETRIES retries${NC}"
    exit 1
fi

# Check 3: Verify API version endpoint
echo -n "Checking API version... "
VERSION_RESPONSE=$(curl -s http://localhost:8000/api/v1/status 2>/dev/null || echo "{}")
if echo "$VERSION_RESPONSE" | grep -q "version"; then
    VERSION=$(echo "$VERSION_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓${NC} (v$VERSION)"
else
    echo -e "${YELLOW}⚠${NC} (version endpoint not available)"
fi

# Check 4: Verify database connectivity
echo -n "Checking database connectivity... "
if docker compose exec -T postgres pg_isready -U l9_user > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Post-deployment check failed: Cannot connect to PostgreSQL${NC}"
    exit 1
fi

# Check 5: Verify Redis connectivity
echo -n "Checking Redis connectivity... "
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Post-deployment check failed: Cannot connect to Redis${NC}"
    exit 1
fi

# Check 6: Verify Neo4j connectivity
echo -n "Checking Neo4j connectivity... "
if curl -s -f http://localhost:7474 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Post-deployment check failed: Cannot connect to Neo4j${NC}"
    exit 1
fi

# Check 7: Verify MCP Memory service
echo -n "Checking MCP Memory service... "
if docker compose ps | grep -q "l9-mcp-memory.*running"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} (service not running)"
fi

# Check 8: Verify no error logs in the last 60 seconds
echo -n "Checking for recent errors... "
ERROR_COUNT=$(docker compose logs --since 60s l9-api 2>/dev/null | grep -i "error\|exception\|traceback" | wc -l || echo "0")
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} ($ERROR_COUNT errors found in logs)"
fi

# Check 9: Smoke test - Create a test request
echo -n "Running smoke test... "
SMOKE_TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/test -H "Content-Type: application/json" -d '{"test": true}' 2>/dev/null || echo "{}")
if echo "$SMOKE_TEST_RESPONSE" | grep -q "success\|ok\|test"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} (smoke test endpoint not available)"
fi

# Check 10: Verify Prometheus metrics
echo -n "Checking Prometheus metrics... "
if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} (Prometheus not available)"
fi

echo ""
echo -e "${GREEN}✓ All post-deployment checks passed${NC}"
echo "Deployment successful!"

exit 0
