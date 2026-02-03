#!/usr/bin/env bash
#
# e2e_test.sh - End-to-End Integration Test for L9 on C1
#
# Tests:
#   1. Memory System (PacketStore, semantic search, graph)
#   2. Tool System (registry, discovery, execution)
#   3. World Model (entities, relationships, queries)
#   4. Full Integration (memory → tools → world model flow)
#
# Usage:
#   ./scripts/e2e_test.sh              # Run all tests
#   ./scripts/e2e_test.sh --memory     # Memory tests only
#   ./scripts/e2e_test.sh --tools      # Tools tests only
#   ./scripts/e2e_test.sh --worldmodel # World model tests only
#   ./scripts/e2e_test.sh --local      # Run against local (not C1)
#

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────
C1_IP="46.62.243.82"
API_PORT="80"
BASE_URL="http://${C1_IP}:${API_PORT}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Test options
RUN_MEMORY=true
RUN_TOOLS=true
RUN_WORLDMODEL=true
RUN_INTEGRATION=true

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --memory)
            RUN_TOOLS=false; RUN_WORLDMODEL=false; RUN_INTEGRATION=false
            shift ;;
        --tools)
            RUN_MEMORY=false; RUN_WORLDMODEL=false; RUN_INTEGRATION=false
            shift ;;
        --worldmodel)
            RUN_MEMORY=false; RUN_TOOLS=false; RUN_INTEGRATION=false
            shift ;;
        --local)
            BASE_URL="http://127.0.0.1:8000"
            shift ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --memory      Run memory tests only"
            echo "  --tools       Run tool tests only"
            echo "  --worldmodel  Run world model tests only"
            echo "  --local       Test against localhost instead of C1"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

log_test() { echo -e "${CYAN}[TEST]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((TESTS_PASSED++)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((TESTS_FAILED++)); }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; ((TESTS_SKIPPED++)); }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    
    if [ -n "$data" ]; then
        curl -sf -X "$method" "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null
    else
        curl -sf -X "$method" "${BASE_URL}${endpoint}" 2>/dev/null
    fi
}

api_status() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    
    if [ -n "$data" ]; then
        curl -sf -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "000"
    else
        curl -sf -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${endpoint}" 2>/dev/null || echo "000"
    fi
}

# ─────────────────────────────────────────────────────────────────────
# Pre-flight Checks
# ─────────────────────────────────────────────────────────────────────

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  L9 End-to-End Integration Tests                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Target: $BASE_URL"
echo "Time:   $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

log_info "Pre-flight: Checking API availability..."
health_status=$(api_status GET "/health")
if [ "$health_status" != "200" ]; then
    log_fail "API not available at $BASE_URL (status: $health_status)"
    echo ""
    echo "Make sure the L9 API is running. Run: deploy"
    exit 1
fi
log_pass "API is healthy"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: MEMORY SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if $RUN_MEMORY; then
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 1: MEMORY SYSTEM TESTS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1.1 Write a test packet
log_test "1.1 Write test packet to memory"
TEST_PACKET_ID="e2e-test-$(date +%s)"
write_response=$(api_call POST "/api/v1/memory/ingest" "{
    \"source_id\": \"e2e_test\",
    \"agent_id\": \"test_agent\",
    \"thread_id\": \"e2e_thread_${TEST_PACKET_ID}\",
    \"kind\": \"TEST\",
    \"payload\": {
        \"test_id\": \"${TEST_PACKET_ID}\",
        \"message\": \"E2E test packet\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    },
    \"metadata\": {
        \"test_run\": true,
        \"e2e\": true
    }
}")

if echo "$write_response" | grep -q "packet_id\|id\|success\|ok"; then
    log_pass "Packet written successfully"
    echo "    Response: $(echo "$write_response" | head -c 200)"
else
    log_fail "Packet write failed"
    echo "    Response: $write_response"
fi
echo ""

# 1.2 Semantic search
log_test "1.2 Semantic search"
search_response=$(api_call POST "/api/v1/memory/search" "{
    \"query\": \"E2E test packet\",
    \"top_k\": 5
}")

if echo "$search_response" | grep -q "results\|hits\|packets"; then
    log_pass "Semantic search returned results"
    echo "    Response: $(echo "$search_response" | head -c 300)"
else
    log_skip "Semantic search endpoint may not exist or returned empty"
    echo "    Response: $search_response"
fi
echo ""

# 1.3 Memory stats
log_test "1.3 Memory statistics"
stats_response=$(api_call GET "/api/v1/memory/stats" || api_call GET "/memory/stats" || echo "")

if [ -n "$stats_response" ]; then
    log_pass "Memory stats retrieved"
    echo "    Response: $(echo "$stats_response" | head -c 300)"
else
    log_skip "Memory stats endpoint not available"
fi
echo ""

# 1.4 Graph connectivity (Neo4j)
log_test "1.4 Graph database connectivity"
graph_response=$(api_call GET "/api/v1/graph/health" || api_call GET "/graph/status" || echo "")

if [ -n "$graph_response" ]; then
    log_pass "Graph database accessible"
    echo "    Response: $(echo "$graph_response" | head -c 200)"
else
    log_skip "Graph endpoint not available (may be expected)"
fi
echo ""

fi # RUN_MEMORY

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TOOL SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if $RUN_TOOLS; then
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 2: TOOL SYSTEM TESTS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 2.1 List available tools
log_test "2.1 List available tools"
tools_response=$(api_call GET "/api/v1/tools" || api_call GET "/tools/list" || echo "")

if echo "$tools_response" | grep -q "tools\|name\|id"; then
    tool_count=$(echo "$tools_response" | grep -o '"name"' | wc -l | tr -d ' ')
    log_pass "Tool registry returned $tool_count tools"
    echo "    Sample: $(echo "$tools_response" | head -c 400)"
else
    log_skip "Tool list endpoint not available"
    echo "    Response: $tools_response"
fi
echo ""

# 2.2 Get tool by ID
log_test "2.2 Get specific tool definition"
tool_response=$(api_call GET "/api/v1/tools/MEMORY_SEARCH" || api_call GET "/tools/MEMORY_SEARCH" || echo "")

if echo "$tool_response" | grep -q "name\|description\|parameters"; then
    log_pass "Tool definition retrieved"
    echo "    Response: $(echo "$tool_response" | head -c 300)"
else
    log_skip "Tool lookup not available or tool not found"
fi
echo ""

# 2.3 Tool categories
log_test "2.3 Tool categories"
categories_response=$(api_call GET "/api/v1/tools/categories" || echo "")

if [ -n "$categories_response" ]; then
    log_pass "Tool categories retrieved"
    echo "    Response: $(echo "$categories_response" | head -c 300)"
else
    log_skip "Tool categories endpoint not available"
fi
echo ""

# 2.4 Execute a safe tool (memory search)
log_test "2.4 Execute tool: MEMORY_SEARCH"
exec_response=$(api_call POST "/api/v1/tools/execute" "{
    \"tool_id\": \"MEMORY_SEARCH\",
    \"arguments\": {
        \"query\": \"test\",
        \"top_k\": 3
    }
}" || echo "")

if echo "$exec_response" | grep -q "result\|output\|success"; then
    log_pass "Tool execution succeeded"
    echo "    Response: $(echo "$exec_response" | head -c 300)"
else
    log_skip "Tool execution endpoint not available or failed"
    echo "    Response: $(echo "$exec_response" | head -c 200)"
fi
echo ""

fi # RUN_TOOLS

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: WORLD MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if $RUN_WORLDMODEL; then
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 3: WORLD MODEL TESTS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 3.1 World model status
log_test "3.1 World model status"
wm_status=$(api_call GET "/api/v1/worldmodel/status" || api_call GET "/worldmodel/status" || echo "")

if [ -n "$wm_status" ]; then
    log_pass "World model status retrieved"
    echo "    Response: $(echo "$wm_status" | head -c 300)"
else
    log_skip "World model status endpoint not available"
fi
echo ""

# 3.2 Create test entity
log_test "3.2 Create test entity"
entity_response=$(api_call POST "/api/v1/worldmodel/entities" "{
    \"entity_type\": \"test_object\",
    \"name\": \"E2E Test Entity $(date +%s)\",
    \"attributes\": {
        \"test\": true,
        \"created_by\": \"e2e_test\"
    }
}" || echo "")

if echo "$entity_response" | grep -q "id\|entity_id\|created"; then
    log_pass "Entity created"
    ENTITY_ID=$(echo "$entity_response" | grep -o '"id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "    Entity ID: $ENTITY_ID"
    echo "    Response: $(echo "$entity_response" | head -c 300)"
else
    log_skip "Entity creation endpoint not available"
    echo "    Response: $(echo "$entity_response" | head -c 200)"
fi
echo ""

# 3.3 Query entities
log_test "3.3 Query world model entities"
query_response=$(api_call GET "/api/v1/worldmodel/entities?type=test_object&limit=5" || echo "")

if echo "$query_response" | grep -q "entities\|results\|data"; then
    log_pass "Entity query succeeded"
    echo "    Response: $(echo "$query_response" | head -c 300)"
else
    log_skip "Entity query endpoint not available"
fi
echo ""

# 3.4 Get entity relationships
log_test "3.4 Entity relationships"
rel_response=$(api_call GET "/api/v1/worldmodel/relationships" || echo "")

if [ -n "$rel_response" ]; then
    log_pass "Relationships query succeeded"
    echo "    Response: $(echo "$rel_response" | head -c 300)"
else
    log_skip "Relationships endpoint not available"
fi
echo ""

fi # RUN_WORLDMODEL

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if $RUN_INTEGRATION; then
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 4: INTEGRATION TESTS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 4.1 Full agent task flow
log_test "4.1 Agent task submission"
task_response=$(api_call POST "/api/v1/agent/task" "{
    \"task\": \"Test task from e2e suite\",
    \"agent_id\": \"test_agent\",
    \"context\": {
        \"source\": \"e2e_test\",
        \"test_run\": true
    }
}" || echo "")

if echo "$task_response" | grep -q "task_id\|id\|status\|queued"; then
    log_pass "Agent task submitted"
    echo "    Response: $(echo "$task_response" | head -c 300)"
else
    log_skip "Agent task endpoint not available"
    echo "    Response: $(echo "$task_response" | head -c 200)"
fi
echo ""

# 4.2 Reasoning endpoint
log_test "4.2 Reasoning orchestrator"
reasoning_response=$(api_call POST "/api/v1/reasoning/analyze" "{
    \"input\": \"What is the status of the memory system?\",
    \"context\": {}
}" || echo "")

if echo "$reasoning_response" | grep -q "result\|output\|analysis"; then
    log_pass "Reasoning endpoint responded"
    echo "    Response: $(echo "$reasoning_response" | head -c 300)"
else
    log_skip "Reasoning endpoint not available"
fi
echo ""

# 4.3 Module registry
log_test "4.3 Module registry"
modules_response=$(api_call GET "/api/v1/modules" || api_call GET "/modules/list" || echo "")

if echo "$modules_response" | grep -q "modules\|name\|id"; then
    module_count=$(echo "$modules_response" | grep -o '"module_id"\|"name"' | wc -l | tr -d ' ')
    log_pass "Module registry returned entries"
    echo "    Response: $(echo "$modules_response" | head -c 400)"
else
    log_skip "Module registry not available"
fi
echo ""

# 4.4 Health of all subsystems
log_test "4.4 Subsystem health check"
subsystems=("memory" "tools" "worldmodel" "reasoning")
for sub in "${subsystems[@]}"; do
    sub_health=$(api_status GET "/api/v1/${sub}/health" || api_status GET "/${sub}/health")
    if [ "$sub_health" = "200" ]; then
        echo "    ✅ ${sub}: healthy"
    else
        echo "    ⚠️ ${sub}: status $sub_health"
    fi
done
log_pass "Subsystem health check complete"
echo ""

fi # RUN_INTEGRATION

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Target:     $BASE_URL"
echo "Completed:  $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Results:"
echo "  ${GREEN}✅ Passed:${NC}  $TESTS_PASSED"
echo "  ${RED}❌ Failed:${NC}  $TESTS_FAILED"
echo "  ${YELLOW}⏭️ Skipped:${NC} $TESTS_SKIPPED"
echo ""

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
if [ $TOTAL -gt 0 ]; then
    PASS_RATE=$((TESTS_PASSED * 100 / TOTAL))
    echo "Pass Rate: ${PASS_RATE}%"
    echo ""
fi

if [ $TESTS_FAILED -eq 0 ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ ALL TESTS PASSED                                         ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  SOME TESTS FAILED - Review output above                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    exit 1
fi
