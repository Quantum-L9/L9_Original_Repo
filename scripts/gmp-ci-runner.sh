#!/bin/bash
# GMP CI/CD Integration Runner
# Automates stage execution and validation in CI pipelines

set -euo pipefail

STAGE=${1:-}
REPORT_DIR="reports"
CONFIG_DIR="prompts/.stage-config"

usage() {
    echo "Usage: $0 <stage_number>"
    echo ""
    echo "Example: $0 2  # Execute Stage 2 (Consolidation)"
    echo ""
    echo "This script:"
    echo "  1. Validates prerequisites"
    echo "  2. Loads stage configuration"
    echo "  3. Runs GMP stage execution"
    echo "  4. Validates output report"
    echo "  5. Updates stage status"
    exit 1
}

[[ -z "$STAGE" ]] && usage

echo "🚀 GMP CI Runner - Stage $STAGE"
echo "================================"

# Step 1: Load stage config
CONFIG_FILE="$CONFIG_DIR/stage-$STAGE-*.yaml"
if ! ls $CONFIG_FILE 1> /dev/null 2>&1; then
    echo "❌ ERROR: Stage $STAGE config not found at $CONFIG_FILE"
    exit 1
fi

echo "✅ Loaded stage config: $CONFIG_FILE"

# Step 2: Validate prerequisites
echo ""
echo "🔍 Validating prerequisites..."

# Check PostgreSQL
if ! psql -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ ERROR: PostgreSQL not accessible"
    exit 1
fi
echo "✅ PostgreSQL: Connected"

# Check Redis
if ! redis-cli ping | grep -q PONG; then
    echo "❌ ERROR: Redis not accessible"
    exit 1
fi
echo "✅ Redis: Connected"

# Check Neo4j (if required)
if command -v cypher-shell &> /dev/null; then
    if cypher-shell "RETURN 1" > /dev/null 2>&1; then
        echo "✅ Neo4j: Connected"
    else
        echo "⚠️  WARNING: Neo4j not accessible (may not be required for Stage $STAGE)"
    fi
fi

# Step 3: Extract TODO plan
echo ""
echo "📋 Extracting TODO plan..."
TODO_TEMPLATE="prompts/.templates/stage-$STAGE-todo-template.md"

if [[ ! -f "$TODO_TEMPLATE" ]]; then
    echo "❌ ERROR: TODO template not found at $TODO_TEMPLATE"
    exit 1
fi

# Step 4: Run GMP execution (via Cursor or manual)
echo ""
echo "⚡ Ready to execute Stage $STAGE"
echo ""
echo "MANUAL EXECUTION:"
echo "  1. Open Cursor in L9 repo"
echo "  2. Load: prompts/GMP-Cursor-Stage-$STAGE-*.md"
echo "  3. Follow Phase 0-6 execution"
echo "  4. Report will be written to: $REPORT_DIR/GMP-Stage-$STAGE-Report-*.md"
echo ""
echo "Or press ENTER to continue with automated validation (assuming execution already done)..."
read -r

# Step 5: Find latest report
LATEST_REPORT=$(ls -t $REPORT_DIR/GMP-Stage-$STAGE-Report-*.md 2>/dev/null | head -1)

if [[ -z "$LATEST_REPORT" ]]; then
    echo "❌ ERROR: No report found for Stage $STAGE in $REPORT_DIR/"
    echo "   Expected: $REPORT_DIR/GMP-Stage-$STAGE-Report-*.md"
    exit 1
fi

echo "✅ Found report: $LATEST_REPORT"

# Step 6: Run validation
echo ""
echo "🔍 Validating report..."
python3 scripts/gmp-validate-stage.py \
    --stage "$STAGE" \
    --report "$LATEST_REPORT" \
    --config "$CONFIG_FILE"

VALIDATION_EXIT_CODE=$?

# Step 7: Update stage status
if [[ $VALIDATION_EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "✅ Stage $STAGE VALIDATION PASSED"
    echo ""
    echo "Next steps:"
    echo "  1. Review report: $LATEST_REPORT"
    echo "  2. Commit changes: git add . && git commit -m 'feat: Stage $STAGE complete'"
    echo "  3. Run next stage: $0 $((STAGE + 1))"
    exit 0
else
    echo ""
    echo "❌ Stage $STAGE VALIDATION FAILED"
    echo ""
    echo "Fix issues and re-run: $0 $STAGE"
    exit 1
fi
