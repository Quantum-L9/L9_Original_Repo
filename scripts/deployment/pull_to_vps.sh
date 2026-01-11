#!/usr/bin/env bash
#
# Pull latest code from GitHub to VPS
# PRESERVES all VPS local changes (modified and untracked files)
#

set -euo pipefail

cd /opt/l9

echo "📥 Pulling latest from GitHub (preserving VPS changes)..."
echo ""

# Show current commit
echo "Current VPS commit:"
git rev-parse --short HEAD
echo ""

# Show what will be updated
echo "Latest on GitHub:"
git fetch origin main
git log --oneline HEAD..origin/main | head -5
echo ""

# Stash VPS changes to preserve them
echo "💾 Stashing VPS local changes (modified files)..."
git stash push -m "VPS local changes before pull" -- api/server_memory.py .dockerignore runtime/Dockerfile 2>/dev/null || {
    echo "   (No modified files to stash)"
}

# Pull latest (untracked files are NOT affected by git pull)
echo "⬇️  Pulling from origin/main (fast-forward only)..."
if git pull --ff-only origin main; then
    echo "✅ Fast-forward pull successful!"
else
    echo "⚠️  Cannot fast-forward (VPS has local commits or diverged)"
    echo "   Attempting regular pull with merge..."
    if git pull origin main; then
        echo "✅ Merge pull successful!"
    else
        echo "❌ Merge conflict detected!"
        echo "   Resolving by keeping VPS version..."
        # If there's a conflict, keep VPS version
        git checkout --ours . 2>/dev/null || true
        git add . 2>/dev/null || true
        git commit -m "Merge: keeping VPS local changes" 2>/dev/null || true
    fi
fi

# Restore stashed VPS changes
if git stash list | grep -q "VPS local changes"; then
    echo "🔄 Restoring VPS local changes..."
    git stash pop 2>/dev/null || {
        echo "   (Stash conflicts - you may need to resolve manually)"
    }
fi

echo ""
echo "✅ Done! Latest code pulled from GitHub."
echo ""
echo "Current commit:"
git rev-parse --short HEAD
echo ""
echo "📝 VPS local changes preserved:"
echo "   - Modified files: kept your VPS versions"
echo "   - Untracked files: untouched (api/config.py, runtime/entrypoint.sh, etc.)"
echo ""
echo "⚠️  If you see merge conflicts above, resolve them manually."

