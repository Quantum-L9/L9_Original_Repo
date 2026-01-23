#!/bin/bash
# ============================================================================
# L9 Mutation Testing Runner
# ============================================================================
# Version: 1.0.0
# Created: 2026-01-21
#
# Usage:
#   ./scripts/refactoring/run_mutation_tests.sh [--threshold 85] [--quick]
#
# Options:
#   --threshold N   Set minimum mutation score (default: 85)
#   --quick         Run on single file only (for fast feedback)
#   --help          Show this help
#
# ============================================================================

set -e

# Defaults
THRESHOLD=85
QUICK_MODE=false
PATHS="core/agents/executor.py,memory/substrate_service.py,core/governance/"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE=true
            PATHS="core/agents/executor.py"
            shift
            ;;
        --help)
            head -20 "$0" | tail -15
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              L9 MUTATION TESTING (mutmut)                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🧬 Configuration:"
echo "   Paths:     $PATHS"
echo "   Threshold: $THRESHOLD%"
echo "   Mode:      $([ "$QUICK_MODE" = true ] && echo 'Quick' || echo 'Full')"
echo ""

# Check if mutmut is installed
if ! command -v mutmut &> /dev/null; then
    echo "❌ mutmut not found. Installing..."
    pip install mutmut>=2.4.5
fi

# Check if jq is installed (for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "⚠️ jq not found - using fallback parsing"
    USE_JQ=false
else
    USE_JQ=true
fi

echo "🔄 Running mutation tests..."
echo ""

# Run mutmut
mutmut run \
    --paths-to-mutate "$PATHS" \
    --tests-dir tests/ \
    --timeout 30 \
    --no-progress \
    2>&1 || true

# Get results
echo ""
echo "📊 Calculating results..."

if [ "$USE_JQ" = true ]; then
    # Use jq for JSON parsing
    RESULTS=$(mutmut results --json 2>/dev/null || echo '{"killed":0,"total":1,"survived":0}')
    KILLED=$(echo "$RESULTS" | jq -r '.killed // 0')
    TOTAL=$(echo "$RESULTS" | jq -r '.total // 1')
    SURVIVED=$(echo "$RESULTS" | jq -r '.survived // 0')
else
    # Fallback: parse text output
    mutmut results > /tmp/mutmut_results.txt 2>&1 || true
    KILLED=$(grep -oP 'killed: \K\d+' /tmp/mutmut_results.txt 2>/dev/null || echo "0")
    TOTAL=$(grep -oP 'total: \K\d+' /tmp/mutmut_results.txt 2>/dev/null || echo "1")
    SURVIVED=$(grep -oP 'survived: \K\d+' /tmp/mutmut_results.txt 2>/dev/null || echo "0")
fi

# Calculate score (handle division by zero)
if [ "$TOTAL" -eq 0 ]; then
    SCORE="100.00"
else
    SCORE=$(echo "scale=2; $KILLED * 100 / $TOTAL" | bc)
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   MUTATION TEST RESULTS                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "   Total mutants:  $TOTAL"
echo "   Killed:         $KILLED"
echo "   Survived:       $SURVIVED"
echo "   Score:          $SCORE%"
echo "   Threshold:      $THRESHOLD%"
echo ""

# Check threshold
PASSED=$(echo "$SCORE >= $THRESHOLD" | bc -l)

if [ "$PASSED" -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ❌ FAILED: Mutation score below threshold                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "To see surviving mutants:"
    echo "  mutmut results"
    echo ""
    echo "To show a specific mutant:"
    echo "  mutmut show <id>"
    echo ""
    echo "To fix: Add test cases that kill surviving mutants"
    echo ""
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅ PASSED: Mutation score meets threshold                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
