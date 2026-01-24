#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

HOOK_FILE="$ROOT_DIR/.git/hooks/pre-commit"

mkdir -p "$(dirname "$HOOK_FILE")"

cat > "$HOOK_FILE" <<"EOF"
#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running L9 ADR enforcement (pre-commit)..."

# Only scan staged Python files for speed:
CHANGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)

if [ -z "$CHANGED_PY" ]; then
  echo "No Python changes staged. Skipping ADR enforcement."
  exit 0
fi

# Run full repo scan in strict mode (Option B: fail on any violation)
python tools/adr/adr_scanner.py --strict || {
  echo ""
  echo "❌ ADR enforcement failed. See details above."
  echo "   Fix violations before committing."
  exit 1
}

echo "✅ ADR enforcement passed."
EOF

chmod +x "$HOOK_FILE"

echo "✅ Installed ADR pre-commit hook at .git/hooks/pre-commit"
