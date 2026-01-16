#!/usr/bin/env bash
# Dev Layer Artifact Compilation Wrapper
# Usage: ./scripts/dev_layer_compile.sh [--log-level DEBUG]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default log level
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔨 Dev Layer Artifact Compilation"
echo "   Input:  l9/dev_layer/artifacts/raw/"
echo "   Output: l9/dev_layer/artifacts/compiled/"
echo "   Log Level: $LOG_LEVEL"
echo ""

python -m dev_layer.am_engine.compile \
    --input l9/dev_layer/artifacts/raw \
    --output l9/dev_layer/artifacts/compiled \
    --log-level "$LOG_LEVEL"

echo ""
echo "✅ Compilation complete"
echo "   Run: pytest l9/dev_layer/tests/ -v"
