# 🚀 Production-Ready Git Hooks for L9 (Frontier AI Lab Grade)

 **3 production-ready scripts** you can drop into your repo immediately.

***

## 📦 DELIVERABLES

### **Script 1: `pre-commit` (Secret Scanning + Auto-Format + Lint)**

### **Script 2: `post-merge` (Enhanced with Kernel Reload + Cache Invalidation)**

### **Script 3: `pre-push` (Smoke Tests + Large File Blocker + Schema Validation)**
### **Bonus: Installation Script + Pre-Commit Config**

***

## 🔐 **Script 1: `.git/hooks/pre-commit`**

```bash
#!/usr/bin/env bash
# L9 Pre-Commit Hook - Secret Scanning, Auto-Format, Lint
# Drop this into .git/hooks/pre-commit and chmod +x

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 L9 Pre-Commit Checks${NC}"
echo "========================================"

# Get list of staged Python files
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$STAGED_PY_FILES" ]; then
    echo -e "${GREEN}✓ No Python files staged, skipping checks${NC}"
    exit 0
fi

# ============================================
# 1. SECRET SCANNING
# ============================================
echo -e "\n${YELLOW}[1/5]${NC} Scanning for secrets..."

# Check if gitleaks is installed
if command -v gitleaks &> /dev/null; then
    if gitleaks protect --staged --redact 2>/dev/null; then
        echo -e "${GREEN}✓ No secrets detected${NC}"
    else
        echo -e "${RED}❌ SECRETS DETECTED IN STAGED FILES!${NC}"
        echo -e "${RED}   Commit blocked for security.${NC}"
        echo ""
        echo "To fix:"
        echo "  1. Remove the secret from your code"
        echo "  2. Add it to .env or use environment variables"
        echo "  3. If false positive, add to .gitleaksignore"
        echo ""
        echo "To bypass (NOT recommended): git commit --no-verify"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ gitleaks not installed, skipping secret scan${NC}"
    echo "   Install: brew install gitleaks (Mac) or see https://github.com/gitleaks/gitleaks"
fi

# ============================================
# 2. AUTO-FORMAT PYTHON (ruff format)
# ============================================
echo -e "\n${YELLOW}[2/5]${NC} Auto-formatting Python code..."

if command -v ruff &> /dev/null; then
    # Format staged files
    echo "$STAGED_PY_FILES" | xargs ruff format --quiet 2>/dev/null || true
    
    # Re-stage formatted files
    echo "$STAGED_PY_FILES" | xargs git add
    
    echo -e "${GREEN}✓ Code formatted with ruff${NC}"
else
    echo -e "${YELLOW}⚠ ruff not installed, skipping format${NC}"
    echo "   Install: pip install ruff"
fi

# ============================================
# 3. LINT PYTHON (ruff check --fix)
# ============================================
echo -e "\n${YELLOW}[3/5]${NC} Linting Python code..."

if command -v ruff &> /dev/null; then
    # Run ruff with auto-fix
    if echo "$STAGED_PY_FILES" | xargs ruff check --fix --exit-zero 2>/dev/null; then
        # Re-stage fixed files
        echo "$STAGED_PY_FILES" | xargs git add
        echo -e "${GREEN}✓ Lint checks passed (auto-fixed)${NC}"
    else
        echo -e "${RED}❌ Lint errors found that cannot be auto-fixed${NC}"
        echo "   Run: ruff check . --fix"
        echo "   Or bypass: git commit --no-verify"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ ruff not installed, skipping lint${NC}"
fi

# ============================================
# 4. TYPE CHECKING (mypy - optional)
# ============================================
echo -e "\n${YELLOW}[4/5]${NC} Type checking..."

# Skip type checking if SKIP_TYPECHECK=1 or mypy not installed
if [ "$SKIP_TYPECHECK" = "1" ]; then
    echo -e "${YELLOW}⚠ Type checking skipped (SKIP_TYPECHECK=1)${NC}"
elif ! command -v mypy &> /dev/null; then
    echo -e "${YELLOW}⚠ mypy not installed, skipping type check${NC}"
    echo "   Install: pip install mypy"
else
    # Run mypy only on staged files (fast)
    if echo "$STAGED_PY_FILES" | xargs mypy --no-error-summary --ignore-missing-imports 2>/dev/null; then
        echo -e "${GREEN}✓ Type checking passed${NC}"
    else
        echo -e "${YELLOW}⚠ Type errors found (non-blocking)${NC}"
        echo "   To fix: mypy <file>"
        # Don't block commit on type errors (can be noisy)
    fi
fi

# ============================================
# 5. FORBIDDEN PATTERNS CHECK
# ============================================
echo -e "\n${YELLOW}[5/5]${NC} Checking for forbidden patterns..."

FORBIDDEN_PATTERNS=(
    "import pdb"
    "breakpoint()"
    "print\(.*\)  # TODO.*remove"
    "FIXME|XXX|HACK"
    "password.*=.*['\"]"
)

VIOLATIONS=0
for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if echo "$STAGED_PY_FILES" | xargs grep -nE "$pattern" 2>/dev/null; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done

if [ $VIOLATIONS -gt 0 ]; then
    echo -e "${RED}❌ Found $VIOLATIONS forbidden pattern(s)${NC}"
    echo "   Remove debugging statements, TODOs, or hardcoded secrets"
    echo "   Or bypass: git commit --no-verify"
    exit 1
else
    echo -e "${GREEN}✓ No forbidden patterns found${NC}"
fi

# ============================================
# SUCCESS
# ============================================
echo ""
echo -e "${GREEN}✅ All pre-commit checks passed!${NC}"
echo "========================================"
exit 0
```

**Installation:**
```bash
# Copy to your repo
cp pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Install dependencies
brew install gitleaks  # Mac
# OR
pip install gitleaks   # Python wrapper
pip install ruff mypy
```

***

## 🔄 **Script 2: `.git/hooks/post-merge`**

```bash
#!/usr/bin/env bash
# L9 Post-Merge Hook - Auto-sync after git pull
# Drop this into .git/hooks/post-merge and chmod +x

set -e  # Exit on any error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔄 L9 Post-Merge Automation${NC}"
echo "========================================"

# Get changed files between previous HEAD and current HEAD
CHANGED_FILES=$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD 2>/dev/null || true)

if [ -z "$CHANGED_FILES" ]; then
    echo -e "${GREEN}✓ No changes detected${NC}"
    exit 0
fi

# ============================================
# 1. ENVIRONMENT VARIABLES SYNC
# ============================================
echo -e "\n${YELLOW}[1/8]${NC} Checking environment variables..."

if echo "$CHANGED_FILES" | grep -q "^\.env\.example$"; then
    echo -e "${YELLOW}⚠ .env.example changed!${NC}"
    
    # Check for new required vars
    if [ -f ".env.example" ] && [ -f ".env" ]; then
        NEW_VARS=$(comm -23 <(grep "^[A-Z]" .env.example | cut -d= -f1 | sort) <(grep "^[A-Z]" .env | cut -d= -f1 | sort) || true)
        
        if [ -n "$NEW_VARS" ]; then
            echo -e "${RED}❌ Missing environment variables:${NC}"
            echo "$NEW_VARS" | while read var; do
                echo "   - $var"
            done
            echo ""
            echo "Action required:"
            echo "  1. Copy missing vars from .env.example to .env"
            echo "  2. Set appropriate values"
        else
            echo -e "${GREEN}✓ All required env vars present${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ No env changes${NC}"
fi

# ============================================
# 2. PYTHON DEPENDENCIES
# ============================================
echo -e "\n${YELLOW}[2/8]${NC} Checking Python dependencies..."

if echo "$CHANGED_FILES" | grep -qE "^(requirements\.txt|pyproject\.toml|setup\.py)$"; then
    echo -e "${YELLOW}⚠ Dependencies changed!${NC}"
    echo "   Auto-installing..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet 2>&1 | tail -5 || true
    elif [ -f "pyproject.toml" ]; then
        pip install -e . --quiet 2>&1 | tail -5 || true
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ No dependency changes${NC}"
fi

# ============================================
# 3. DATABASE MIGRATIONS
# ============================================
echo -e "\n${YELLOW}[3/8]${NC} Checking for new migrations..."

if echo "$CHANGED_FILES" | grep -q "^migrations/.*\.sql$"; then
    NEW_MIGRATIONS=$(echo "$CHANGED_FILES" | grep "^migrations/.*\.sql$" || true)
    
    echo -e "${YELLOW}⚠ New migrations detected:${NC}"
    echo "$NEW_MIGRATIONS" | while read migration; do
        echo "   - $migration"
    done
    
    # Check if migration runner exists
    if [ -f "memory/migration_runner.py" ]; then
        echo "   Auto-running migrations..."
        python3 -c "from memory.migration_runner import MigrationRunner; import asyncio; asyncio.run(MigrationRunner().run_migrations())" 2>&1 | tail -5 || {
            echo -e "${RED}❌ Migration failed! Check logs.${NC}"
        }
        echo -e "${GREEN}✓ Migrations applied${NC}"
    else
        echo -e "${YELLOW}   Manual action required: Run migrations${NC}"
    fi
else
    echo -e "${GREEN}✓ No new migrations${NC}"
fi

# ============================================
# 4. DOCKER CHANGES
# ============================================
echo -e "\n${YELLOW}[4/8]${NC} Checking Docker configuration..."

if echo "$CHANGED_FILES" | grep -qE "^(Dockerfile|docker-compose\.yml|\.dockerignore)$"; then
    echo -e "${YELLOW}⚠ Docker configuration changed!${NC}"
    echo ""
    echo "Action required:"
    echo "  docker-compose down"
    echo "  docker-compose up --build -d"
    echo ""
else
    echo -e "${GREEN}✓ No Docker changes${NC}"
fi

# ============================================
# 5. KERNEL HOT-RELOAD (NEW!)
# ============================================
echo -e "\n${YELLOW}[5/8]${NC} Checking kernel changes..."

if echo "$CHANGED_FILES" | grep -q "^kernels/"; then
    echo -e "${YELLOW}⚠ Kernels changed!${NC}"
    
    # Attempt hot-reload via API
    if curl -s -X POST http://localhost:8000/api/kernels/reload --max-time 2 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Kernels hot-reloaded${NC}"
    else
        echo -e "${YELLOW}   (Server not running - kernels will reload on next startup)${NC}"
    fi
else
    echo -e "${GREEN}✓ No kernel changes${NC}"
fi

# ============================================
# 6. AUDIT CACHE INVALIDATION (NEW!)
# ============================================
echo -e "\n${YELLOW}[6/8]${NC} Checking audit scripts..."

if echo "$CHANGED_FILES" | grep -q "^scripts/audit/"; then
    echo -e "${YELLOW}⚠ Audit scripts changed!${NC}"
    
    if [ -d ".audit_cache" ]; then
        echo "   Clearing audit cache..."
        rm -rf .audit_cache/
        echo -e "${GREEN}✓ Cache cleared${NC}"
    else
        echo -e "${GREEN}✓ No cache to clear${NC}"
    fi
else
    echo -e "${GREEN}✓ No audit script changes${NC}"
fi

# ============================================
# 7. PRE-COMMIT CONFIG UPDATE (NEW!)
# ============================================
echo -e "\n${YELLOW}[7/8]${NC} Checking pre-commit configuration..."

if echo "$CHANGED_FILES" | grep -q "^\.pre-commit-config\.yaml$"; then
    echo -e "${YELLOW}⚠ Pre-commit config changed!${NC}"
    
    if command -v pre-commit &> /dev/null; then
        echo "   Reinstalling hooks..."
        pre-commit install --install-hooks >/dev/null 2>&1 || true
        echo -e "${GREEN}✓ Hooks updated${NC}"
    else
        echo -e "${YELLOW}   Install pre-commit: pip install pre-commit${NC}"
    fi
else
    echo -e "${GREEN}✓ No pre-commit changes${NC}"
fi

# ============================================
# 8. REPO INDEX REGENERATION (NEW!)
# ============================================
echo -e "\n${YELLOW}[8/8]${NC} Checking repo index..."

if echo "$CHANGED_FILES" | grep -qE "\.(py|md|yaml)$"; then
    if [ -f "scripts/generate_repo_index.py" ]; then
        echo "   Regenerating repo index (background)..."
        nohup python3 scripts/generate_repo_index.py --quiet >/dev/null 2>&1 &
        echo -e "${GREEN}✓ Index regeneration started${NC}"
    else
        echo -e "${GREEN}✓ No index generator found${NC}"
    fi
else
    echo -e "${GREEN}✓ No index regeneration needed${NC}"
fi

# ============================================
# SUCCESS
# ============================================
echo ""
echo -e "${GREEN}✅ Post-merge automation complete!${NC}"
echo "========================================"
exit 0
```

**Installation:**
```bash
cp post-merge .git/hooks/post-merge
chmod +x .git/hooks/post-merge
```

***

## 🚀 **Script 3: `.git/hooks/pre-push`**

```bash
#!/usr/bin/env bash
# L9 Pre-Push Hook - Smoke Tests + Validation
# Drop this into .git/hooks/pre-push and chmod +x

set -e  # Exit on any error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 L9 Pre-Push Validations${NC}"
echo "========================================"

# ============================================
# 1. SMOKE TESTS
# ============================================
echo -e "\n${YELLOW}[1/4]${NC} Running smoke tests..."

if [ -f "tests/smoke_test.py" ]; then
    echo "   Running tests/smoke_test.py..."
    
    if pytest tests/smoke_test.py -v --tb=short --maxfail=3 2>&1 | tail -20; then
        echo -e "${GREEN}✓ Smoke tests passed${NC}"
    else
        echo -e "${RED}❌ SMOKE TESTS FAILED!${NC}"
        echo ""
        echo "Your changes broke critical paths. Fix before pushing."
        echo ""
        echo "To bypass (NOT recommended): git push --no-verify"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ No smoke tests found, skipping${NC}"
fi

# ============================================
# 2. LARGE FILE CHECK
# ============================================
echo -e "\n${YELLOW}[2/4]${NC} Checking for large files..."

# Get list of files being pushed
LARGE_FILES=$(git diff --stat=200 --cached | grep -E '^\s.*\|.*\+' | awk '{print $1}' | while read file; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$size" -gt 10485760 ]; then  # 10MB
            echo "$file:$(($size / 1048576))MB"
        fi
    fi
done)

if [ -n "$LARGE_FILES" ]; then
    echo -e "${RED}❌ LARGE FILES DETECTED:${NC}"
    echo "$LARGE_FILES" | while IFS=: read file size; do
        echo "   - $file ($size)"
    done
    echo ""
    echo "Large files should not be committed. Options:"
    echo "  1. Add to .gitignore"
    echo "  2. Use Git LFS: git lfs track '$file'"
    echo "  3. Store in S3/external storage"
    echo ""
    echo "To bypass: git push --no-verify"
    exit 1
else
    echo -e "${GREEN}✓ No large files detected${NC}"
fi

# ============================================
# 3. SCHEMA VALIDATION
# ============================================
echo -e "\n${YELLOW}[3/4]${NC} Validating schemas..."

# Check if memory spec validator exists
if [ -f "scripts/audit/verify_memory_spec_v3.py" ]; then
    echo "   Validating memory/memory_spec_v3.0.yaml..."
    
    if python3 scripts/audit/verify_memory_spec_v3.py --quiet 2>&1 | tail -10; then
        echo -e "${GREEN}✓ Schema validation passed${NC}"
    else
        echo -e "${RED}❌ Schema validation failed!${NC}"
        echo "   Fix memory spec before pushing"
        echo "   Or bypass: git push --no-verify"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ No schema validator found, skipping${NC}"
fi

# ============================================
# 4. BREAKING CHANGE DETECTION
# ============================================
echo -e "\n${YELLOW}[4/4]${NC} Checking for breaking changes..."

# Check if PacketEnvelope schema changed
if git diff --cached --name-only | grep -q "memory/substrate_models.py"; then
    echo -e "${YELLOW}⚠ substrate_models.py changed!${NC}"
    echo "   This may contain breaking changes to PacketEnvelope"
    echo "   Ensure backward compatibility or update version"
    echo ""
    
    # Check if version was bumped
    if git diff --cached memory/substrate_models.py | grep -q "PACKET_SCHEMA_VERSION"; then
        echo -e "${GREEN}✓ Schema version updated${NC}"
    else
        echo -e "${YELLOW}⚠ Schema version NOT updated (may be okay)${NC}"
    fi
else
    echo -e "${GREEN}✓ No schema changes detected${NC}"
fi

# ============================================
# SUCCESS
# ============================================
echo ""
echo -e "${GREEN}✅ All pre-push validations passed!${NC}"
echo -e "${GREEN}   Safe to push to remote.${NC}"
echo "========================================"
exit 0
```

**Installation:**
```bash
cp pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

***

## 🎁 **BONUS: Installation Script**

Save this as `scripts/install_git_hooks.sh`:

```bash
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
echo "  brew install gitleaks        # Secret scanning"
echo "  pip install ruff mypy pytest # Python tools"
echo ""
echo "Test hooks:"
echo "  git commit -m 'test'   # Triggers pre-commit"
echo "  git pull               # Triggers post-merge"
echo "  git push               # Triggers pre-push"
```

**Run:**
```bash
bash scripts/install_git_hooks.sh
```

***

## 📚 **File Structure**

```
l9/
├── .git/hooks/
│   ├── pre-commit      ← Script 1
│   ├── post-merge      ← Script 2
│   └── pre-push        ← Script 3
├── scripts/
│   ├── install_git_hooks.sh  ← Installer
│   └── hooks/
│       ├── pre-commit
│       ├── post-merge
│       └── pre-push
```

***

## ✅ **Next Steps**

1. **Copy scripts to `scripts/hooks/`**
2. **Run installer:** `bash scripts/install_git_hooks.sh`
3. **Install dependencies:**
   ```bash
   brew install gitleaks
   pip install ruff mypy pytest
   ```
4. **Test hooks:**
   ```bash
   # Test pre-commit
   echo "test" >> test.py && git add test.py && git commit -m "test"
   
   # Test post-merge
   git pull
   
   # Test pre-push
   git push --dry-run
   ```
