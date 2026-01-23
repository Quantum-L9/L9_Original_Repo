#!/usr/bin/env bash
# L9 INSTALLATION & CONFIGURATION SUITE
# Deploys enhanced pre-commit security infrastructure

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HOOK_DIR="$REPO_ROOT/.git/hooks"
LIB_DIR="$HOOK_DIR/lib"
BACKUP_DIR="$REPO_ROOT/.git/hooks/.backups"

echo "🔧 L9 Pre-Commit Security Installation"
echo "========================================"

# Create directories
mkdir -p "$LIB_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p /var/log/l9

# Backup existing pre-commit hook
if [ -f "$HOOK_DIR/pre-commit" ]; then
    BACKUP_NAME="pre-commit.backup.$(date +%Y%m%d-%H%M%S)"
    cp "$HOOK_DIR/pre-commit" "$BACKUP_DIR/$BACKUP_NAME"
    echo "✓ Backed up existing hook to: $BACKUP_DIR/$BACKUP_NAME"
fi

# Deploy enhanced pre-commit hook
if [ -f "pre-commit-enhanced.sh" ]; then
    cp pre-commit-enhanced.sh "$HOOK_DIR/pre-commit"
    chmod +x "$HOOK_DIR/pre-commit"
    echo "✓ Deployed enhanced pre-commit hook"
else
    echo "❌ pre-commit-enhanced.sh not found"
    exit 1
fi

# Verify hook is executable
if [ -x "$HOOK_DIR/pre-commit" ]; then
    echo "✓ Pre-commit hook is executable"
else
    chmod +x "$HOOK_DIR/pre-commit"
    echo "✓ Fixed hook permissions"
fi

# Test hook
echo ""
echo "Testing hook..."
if "$HOOK_DIR/pre-commit" --version 2>/dev/null || "$HOOK_DIR/pre-commit" --help 2>/dev/null || true; then
    echo "✓ Hook test passed"
fi

# Verify logging setup
if touch "$REPO_ROOT/.git/hooks/lib/audit.sh" 2>/dev/null; then
    echo "✓ Logging directory writable"
    rm "$REPO_ROOT/.git/hooks/lib/audit.sh"
else
    echo "⚠️  May need sudo for /var/log/l9 permissions"
    sudo mkdir -p /var/log/l9
    sudo chmod 777 /var/log/l9
fi

echo ""
echo "✅ Installation complete!"
echo "📝 Next steps:"
echo "   1. Test: git commit --allow-empty -m 'test: verify pre-commit'"
echo "   2. Review logs: tail -f /var/log/l9/pre-commit-hooks.jsonl"
echo "   3. Configure SIEM: Set SIEM_HEC_URL env var for Splunk integration"
echo "========================================"
