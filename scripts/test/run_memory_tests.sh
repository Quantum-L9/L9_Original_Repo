#!/bin/bash
# L9 Memory v3.1 Test Runner
# Runs tests for query_classifier, reasoning_replay, consolidation, agent_persistence

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           L9 Memory v3.1 Test Runner                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check for TEST_DATABASE_URL or DATABASE_URL
if [ -z "$TEST_DATABASE_URL" ] && [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗${NC} TEST_DATABASE_URL or DATABASE_URL not set"
    echo "   Set TEST_DATABASE_URL for test database or DATABASE_URL for shared database"
    echo "   Example: export TEST_DATABASE_URL='postgresql://user:pass@localhost:5432/l9_memory_test'"
    exit 1
fi

DB_URL="${TEST_DATABASE_URL:-$DATABASE_URL}"
echo -e "${YELLOW}→${NC} Using database: ${DB_URL%%@*}" # Show only user@host part
echo ""

# Test files to run
TEST_FILES=(
    "tests/memory/test_query_classifier.py"
    "tests/memory/test_reasoning_replay.py"
    "tests/memory/test_consolidation.py"
    "tests/memory/test_agent_persistence.py"
)

PASSED=0
FAILED=0
SKIPPED=0

# Run each test file
for test_file in "${TEST_FILES[@]}"; do
    if [ ! -f "$test_file" ]; then
        echo -e "${YELLOW}⚠${NC} Test file not found: $test_file"
        ((SKIPPED++))
        continue
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $test_file"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if python3 -m pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✓${NC} $test_file passed"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $test_file failed"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Tests passed: ${GREEN}$PASSED${NC}"
echo "Tests failed: ${RED}$FAILED${NC}"
echo "Tests skipped: ${YELLOW}$SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $SKIPPED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ALL TESTS PASSED! 🎉                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║           SOME TESTS SKIPPED - CHECK OUTPUT ABOVE          ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           SOME TESTS FAILED - CHECK OUTPUT ABOVE           ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
