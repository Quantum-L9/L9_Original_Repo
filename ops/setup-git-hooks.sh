#!/bin/bash
# =============================================================================
# L9 Git Hooks Setup v3.0
# Run once on VPS or local: ./ops/setup-git-hooks.sh
#
# This script installs the production-ready hooks from scripts/hooks/
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up L9 git hooks v3.0..."
echo ""

# =============================================================================
# Install hooks from scripts/hooks/
# =============================================================================
if [ -f "$REPO_ROOT/scripts/install_git_hooks.sh" ]; then
    cd "$REPO_ROOT"
    bash scripts/install_git_hooks.sh
else
    echo "❌ scripts/install_git_hooks.sh not found!"
    echo "   Expected at: $REPO_ROOT/scripts/install_git_hooks.sh"
    exit 1
fi

# =============================================================================
# Make VPS scripts executable
# =============================================================================
if [ -d "$REPO_ROOT/scripts/vps" ]; then
    chmod +x "$REPO_ROOT/scripts/vps/"*.sh 2>/dev/null || true
    echo ""
    echo "VPS Scripts (scripts/vps/):"
    echo "  ./scripts/vps/sync_env_vars.sh     - Add missing env vars"
    echo "  ./scripts/vps/verify_vps_env.sh    - Full env verification"
    echo "  ./scripts/vps/run_migrations.sh    - Run pending migrations"
    echo "  ./scripts/vps/backup_database.sh   - Database backup (cron)"
    echo "  ./scripts/vps/vps-mri.sh           - Full system diagnostic"
fi

echo ""
echo "✅ Setup complete!"
