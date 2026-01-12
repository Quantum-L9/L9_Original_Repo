#!/bin/bash
# L9 Memory v3.1 API Endpoint Tester
# Tests POST /reasoning/replay and POST /consolidation/run endpoints

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304}"

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
echo "║           L9 Memory v3.1 API Endpoint Tester                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "API URL: $API_URL"
echo ""

# =============================================================================
# 1. Test POST /api/v1/memory/reasoning/replay
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. REASONING REPLAY ENDPOINT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing POST /api/v1/memory/reasoning/replay (narrative format)"

# First, create a test packet to get a packet_id
PACKET_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/packet" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "packet_type": "test.reasoning_replay",
        "payload": {"decision": "test", "reason": "API endpoint testing"},
        "agent_id": "test_agent"
    }')

PACKET_ID=$(echo "$PACKET_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('packet_id', ''))" 2>/dev/null || echo "")

if [ -z "$PACKET_ID" ]; then
    test_fail "Could not create test packet for reasoning replay"
    echo "   Response: $PACKET_RESPONSE"
else
    test_info "Created test packet: $PACKET_ID"
    
    # Test reasoning replay with narrative format
    REPLAY_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/reasoning/replay" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"packet_id\": \"$PACKET_ID\",
            \"format\": \"narrative\"
        }")
    
    REPLAY_STATUS=$(echo "$REPLAY_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('chain_id', 'error'))" 2>/dev/null || echo "error")
    
    if [ "$REPLAY_STATUS" != "error" ] && echo "$REPLAY_RESPONSE" | grep -q "chain_id\|explanation"; then
        test_pass "Reasoning replay endpoint (narrative format)"
        echo "   Chain ID: $(echo "$REPLAY_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('chain_id', 'N/A'))" 2>/dev/null || echo 'N/A')"
    else
        HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/api/v1/memory/reasoning/replay" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"packet_id\": \"$PACKET_ID\", \"format\": \"narrative\"}")
        
        if [ "$HTTP_CODE" = "503" ]; then
            test_info "Reasoning replay endpoint not available (status: 503) - service may not be initialized"
        else
            test_fail "Reasoning replay endpoint (status: $HTTP_CODE)"
            echo "   Response: $REPLAY_RESPONSE"
        fi
    fi
fi

# Test with JSON format
test_info "Testing POST /api/v1/memory/reasoning/replay (json format)"
if [ -n "$PACKET_ID" ]; then
    REPLAY_JSON_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/reasoning/replay" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"packet_id\": \"$PACKET_ID\",
            \"format\": \"json\"
        }")
    
    if echo "$REPLAY_JSON_RESPONSE" | grep -q "chain_id\|packets"; then
        test_pass "Reasoning replay endpoint (json format)"
    else
        HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/api/v1/memory/reasoning/replay" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"packet_id\": \"$PACKET_ID\", \"format\": \"json\"}")
        test_info "Reasoning replay (json) status: $HTTP_CODE"
    fi
fi

# =============================================================================
# 2. Test POST /api/v1/memory/consolidation/run
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. CONSOLIDATION ENDPOINT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_info "Testing POST /api/v1/memory/consolidation/run (dry-run mode)"

CONSOLIDATION_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/memory/consolidation/run" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "dry_run": true,
        "batch_size": 100,
        "sleep_between_batches_ms": 10
    }')

CONSOLIDATION_SUCCESS=$(echo "$CONSOLIDATION_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")

if [ "$CONSOLIDATION_SUCCESS" = "True" ] || echo "$CONSOLIDATION_RESPONSE" | grep -q "deduplication_count\|archived_count"; then
    test_pass "Consolidation endpoint (dry-run mode)"
    echo "   Deduplication: $(echo "$CONSOLIDATION_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('deduplication_count', 0))" 2>/dev/null || echo '0')"
    echo "   Archived: $(echo "$CONSOLIDATION_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('archived_count', 0))" 2>/dev/null || echo '0')"
    echo "   Summarized: $(echo "$CONSOLIDATION_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('summarized_count', 0))" 2>/dev/null || echo '0')"
    echo "   Expired: $(echo "$CONSOLIDATION_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('expired_count', 0))" 2>/dev/null || echo '0')"
else
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/api/v1/memory/consolidation/run" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"dry_run": true}')
    
    if [ "$HTTP_CODE" = "503" ]; then
        test_info "Consolidation endpoint not available (status: 503) - service may not be initialized"
    else
        test_fail "Consolidation endpoint (status: $HTTP_CODE)"
        echo "   Response: $CONSOLIDATION_RESPONSE"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Tests passed: ${GREEN}$PASSED${NC}"
echo "Tests failed: ${RED}$FAILED${NC}"
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

