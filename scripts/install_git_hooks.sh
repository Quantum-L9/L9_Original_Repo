#!/usr/bin/env bash
# L9 Git Hooks Installer
# Run: bash scripts/install_git_hooks.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 Installing L9 Git Hooks...${NC}"
echo ""

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy hooks
cp scripts/hooks/pre-commit .git/hooks/pre-commit
cp scripts/hooks/post-merge .git/hooks/post-merge
cp scripts/hooks/pre-push .git/hooks/pre-push

# Make executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-merge
chmod +x .git/hooks/pre-push

echo -e "${GREEN}✅ Hooks installed!${NC}"
echo ""
echo "Installed hooks:"
echo "  • pre-commit  → Secret scanning, linting, formatting"
echo "  • post-merge  → Deps, migrations, kernel reload"
echo "  • pre-push    → Smoke tests, large file check"
echo ""
echo "Dependencies (optional but recommended):"
echo ""
echo "  Python tools:"
echo "    pip install ruff mypy pytest"
echo ""
echo "  Secret scanning (gitleaks):"
echo "    macOS:  brew install gitleaks"
echo "    Linux:  wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.21.2_linux_x64.tar.gz"
echo "            tar -xzf gitleaks_*.tar.gz && sudo mv gitleaks /usr/local/bin/"
echo ""
echo "  Note: gitleaks only needed if committing from this machine."
echo "        VPS (pull-only) doesn't need it - hook skips gracefully."
echo ""
echo "Test hooks:"
echo "  git commit -m 'test'   # Triggers pre-commit"
echo "  git pull               # Triggers post-merge"
echo "  git push               # Triggers pre-push"
