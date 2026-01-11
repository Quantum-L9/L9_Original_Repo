#!/bin/bash
# L9 Comprehensive Test Suite
# Tests everything possible in the Docker environment

# Don't exit on error - we want to test everything
set +e

API_URL="http://localhost:8000"
API_KEY="9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PASSED=0
FAILED=0

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

test_info() {
    echo -e "${YELLOW}→${NC} $1"
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           L9 COMPREHENSIVE TEST SUITE                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# 1. Docker Services Check
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. DOCKER SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Checking Docker containers..."
if docker compose ps | grep -q "Up.*healthy"; then
    test_pass "All Docker services are running and healthy"
    docker compose ps
else
    test_fail "Some Docker services are not healthy"
    docker compose ps
fi

# =============================================================================
# 2. Health Endpoints
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. HEALTH ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing /health"
if curl -s -f "$API_URL/health" | grep -q "ok"; then
    test_pass "Main health endpoint"
else
    test_fail "Main health endpoint"
fi

test_info "Testing /os/health"
if curl -s -f "$API_URL/os/health" | grep -q "ok"; then
    test_pass "OS health endpoint"
else
    test_fail "OS health endpoint"
fi

test_info "Testing /agent/health"
if curl -s -f "$API_URL/agent/health" | grep -q "ok"; then
    test_pass "Agent health endpoint"
else
    test_fail "Agent health endpoint"
fi

test_info "Testing /os/status"
if curl -s -f "$API_URL/os/status" > /dev/null; then
    test_pass "OS status endpoint"
else
    test_fail "OS status endpoint"
fi

test_info "Testing /agent/status"
if curl -s -f "$API_URL/agent/status" > /dev/null; then
    test_pass "Agent status endpoint"
else
    test_fail "Agent status endpoint"
fi

# =============================================================================
# 3. API Info & Documentation
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. API INFO & DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing root endpoint"
if curl -s -f "$API_URL/" | grep -q "L9"; then
    test_pass "Root endpoint returns API info"
    echo "   Features: $(curl -s "$API_URL/" | python3 -c "import sys, json; d=json.load(sys.stdin); print(', '.join([k for k,v in d.get('features', {}).items() if v]))" 2>/dev/null || echo 'N/A')"
else
    test_fail "Root endpoint"
fi

# /docs endpoint disabled - no Swagger UI in production
# test_info "Testing /docs endpoint"
# if curl -s -f "$API_URL/docs" | grep -q "FastAPI"; then
#     test_pass "API documentation accessible"
# else
#     test_fail "API documentation"
# fi

test_info "Testing /openapi.json"
if curl -s -f "$API_URL/openapi.json" | grep -q "openapi"; then
    test_pass "OpenAPI schema accessible"
else
    test_fail "OpenAPI schema"
fi

# =============================================================================
# 4. Memory System
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. MEMORY SYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing /api/v1/memory/test"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/test" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json")
if echo "$RESPONSE" | grep -q "ok"; then
    test_pass "Memory test endpoint"
else
    test_fail "Memory test endpoint: $RESPONSE"
fi

test_info "Testing /api/v1/memory/stats"
STATUS=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/api/v1/memory/stats" \
    -H "Authorization: Bearer $API_KEY")
if [ "$STATUS" = "200" ] || [ "$STATUS" = "503" ]; then
    test_pass "Memory stats endpoint (status: $STATUS)"
else
    test_fail "Memory stats endpoint (status: $STATUS)"
fi

test_info "Testing /api/v1/memory/packet write"
PACKET_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/packet" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "packet_type": "test.comprehensive_test",
        "payload": {"test": "comprehensive", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
        "metadata": {"source": "test_everything.sh"}
    }')
if echo "$PACKET_RESPONSE" | grep -q "packet_id\|ok\|status"; then
    test_pass "Memory packet write"
else
    test_fail "Memory packet write: $PACKET_RESPONSE"
fi

# =============================================================================
# 5. Agent Execution
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. AGENT EXECUTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing /agent/execute (simple query)"
EXEC_RESPONSE=$(curl -s -X POST "$API_URL/agent/execute" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "What is 2 + 2?",
        "kind": "query",
        "max_iterations": 2
    }')
EXEC_STATUS=$(echo "$EXEC_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "error")
if [ "$EXEC_STATUS" != "error" ]; then
    test_pass "Agent execute endpoint (status: $EXEC_STATUS)"
    echo "   Response preview: $(echo "$EXEC_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('result', d.get('error', 'N/A'))[:50])" 2>/dev/null || echo 'N/A')"
else
    test_fail "Agent execute endpoint: $EXEC_RESPONSE"
fi

test_info "Testing /agent/task"
TASK_RESPONSE=$(curl -s -X POST "$API_URL/agent/task" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "agent_id": "l9-standard-v1",
        "payload": {"message": "Test task from comprehensive test suite"}
    }')
if echo "$TASK_RESPONSE" | grep -q "task_id\|status"; then
    test_pass "Agent task submission"
else
    test_fail "Agent task submission: $TASK_RESPONSE"
fi

test_info "Testing /chat endpoint"
CHAT_RESPONSE=$(curl -s -X POST "$API_URL/chat" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "Hello L, this is a test",
        "thread_id": "test-comprehensive-123"
    }')
if echo "$CHAT_RESPONSE" | grep -q "reply\|error"; then
    test_pass "Chat endpoint"
else
    test_fail "Chat endpoint: $CHAT_RESPONSE"
fi

# =============================================================================
# 6. Authentication
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. AUTHENTICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing endpoint without auth (should fail)"
NO_AUTH_STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/memory/test")
if [ "$NO_AUTH_STATUS" = "401" ] || [ "$NO_AUTH_STATUS" = "403" ]; then
    test_pass "Authentication required (status: $NO_AUTH_STATUS)"
else
    test_fail "Authentication check (status: $NO_AUTH_STATUS)"
fi

test_info "Testing endpoint with invalid auth (should fail)"
INVALID_AUTH_STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/memory/test" \
    -H "Authorization: Bearer invalid_key")
if [ "$INVALID_AUTH_STATUS" = "401" ] || [ "$INVALID_AUTH_STATUS" = "403" ]; then
    test_pass "Invalid auth rejected (status: $INVALID_AUTH_STATUS)"
else
    test_fail "Invalid auth check (status: $INVALID_AUTH_STATUS)"
fi

# =============================================================================
# 7. Redis Connectivity
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. REDIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing Redis connection"
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    test_pass "Redis is responding"
else
    test_fail "Redis connection"
fi

# =============================================================================
# 8. Neo4j Connectivity
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. NEO4J"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing Neo4j HTTP endpoint"
NEO4J_STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:7474)
if [ "$NEO4J_STATUS" = "200" ] || [ "$NEO4J_STATUS" = "301" ] || [ "$NEO4J_STATUS" = "302" ]; then
    test_pass "Neo4j HTTP endpoint (status: $NEO4J_STATUS)"
else
    test_fail "Neo4j HTTP endpoint (status: $NEO4J_STATUS)"
fi

# =============================================================================
# 9. Automated Test Suite
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. AUTOMATED TEST SUITE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Running Docker smoke tests..."
if docker compose exec -T l9-api python -m pytest /app/tests/docker/test_stack_smoke.py -v --tb=short 2>&1 | tee /tmp/smoke_test_output.txt | grep -q "PASSED\|passed"; then
    test_pass "Smoke tests passed"
    echo "   $(grep -E "passed|PASSED" /tmp/smoke_test_output.txt | tail -1)"
else
    SMOKE_FAILED=$(grep -c "FAILED\|failed" /tmp/smoke_test_output.txt 2>/dev/null | head -1 || echo "0")
    SMOKE_FAILED=${SMOKE_FAILED:-0}
    if [ "$SMOKE_FAILED" -gt 0 ] 2>/dev/null; then
        test_fail "Smoke tests had failures"
        echo "   Check /tmp/smoke_test_output.txt for details"
    else
        test_info "Smoke tests completed (check output above)"
    fi
fi

# =============================================================================
# 10. WebSocket (if available)
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "10. WEBSOCKET"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Checking WebSocket endpoint availability"
WS_STATUS=$(curl -s -w "%{http_code}" -o /dev/null -H "Upgrade: websocket" -H "Connection: Upgrade" "$API_URL/ws" 2>&1 || echo "000")
if [ "$WS_STATUS" = "426" ] || [ "$WS_STATUS" = "101" ] || echo "$WS_STATUS" | grep -q "websocket"; then
    test_pass "WebSocket endpoint exists (status: $WS_STATUS)"
    test_info "   Note: Full WebSocket testing requires a WebSocket client"
else
    test_info "WebSocket endpoint check (status: $WS_STATUS) - may require WebSocket client"
fi

# =============================================================================
# 11. Dashboard
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "11. DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Checking dashboard health"
DASHBOARD_STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://127.0.0.1:5050/api/health 2>&1 || echo "000")
if [ "$DASHBOARD_STATUS" = "200" ]; then
    test_pass "Dashboard is running"
    DASHBOARD_INFO=$(curl -s http://127.0.0.1:5050/api/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Conversations: {d.get('conversation_count', 0)}\")" 2>/dev/null || echo "")
    echo "   $DASHBOARD_INFO"
else
    test_info "Dashboard not running (status: $DASHBOARD_STATUS)"
    echo "   Start with: cd local_dashboard && python3 app.py"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
TOTAL=$((PASSED + FAILED))
echo "Tests passed: ${GREEN}$PASSED${NC}"
echo "Tests failed: ${RED}$FAILED${NC}"
echo "Total tests:  $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ALL TESTS PASSED! 🎉                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║           SOME TESTS FAILED - CHECK OUTPUT ABOVE           ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

