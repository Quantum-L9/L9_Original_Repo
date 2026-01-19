---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-PIPELINEPRE-001"
component_name: "Pipeline-Precommit - Commit Gate"
layer: "commands"
domain: "pipeline"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: pipeline-precommit
description: "L9 commit gate — full audit before any code commit with analysis, governance, and next action"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 PIPELINE-PRECOMMIT: Full Commit Gate Audit ===
# Cursor Slash Command: /pipeline-precommit
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After audit, **automatically runs /ynp** to recommend: commit, fix issues, or run additional validation.

---

## WHAT IT DOES

**Five-stage commit gate pipeline:**

1. **Stage 1: `/analyze+evaluate`** — Structure analysis + code health scoring
2. **Stage 2: Run All Tests** — Unit, integration, type check, lint
3. **Stage 3: Run CI Scripts** — Full CI validation suite
4. **Stage 4: `/governance`** — Header validation, version checks, compliance
5. **Stage 5: `/ynp`** — Single highest-leverage next action

**Key principle:** No broken or non-compliant code enters canonical state. Gate everything.

---

## WHEN TO USE

- ✅ Before committing any change
- ✅ Before merging to main branch
- ✅ Before promoting to canonical status
- ✅ Before deploying to VPS
- ✅ Before creating PR

---

## EXECUTION PROTOCOL

### Stage 1: ANALYZE + EVALUATE

```
1. Run /analyze+evaluate on staged changes
2. Generate structure map + compliance report
3. Identify issues and tech debt
4. Calculate overall health score
```

**Output:**
- Structure health: [score]%
- Code quality: [score]%
- GMP compliance: [score]%
- Test coverage: [score]%

### Stage 2: RUN ALL TESTS

```bash
# Unit Tests
pytest tests/ -v --tb=short

# Integration Tests  
pytest tests/integration/ -v --tb=short

# Type Check
python -m mypy core/ api/ --ignore-missing-imports

# Lint Check
ruff check core/ api/ memory/ orchestration/

# Syntax Validation
python -m py_compile $(git diff --cached --name-only -- '*.py')
```

**Test Thresholds:**
| Test Type | Required | Blocking |
|-----------|----------|----------|
| Unit Tests | 100% pass | 🔴 Yes |
| Integration Tests | 100% pass | 🔴 Yes |
| Type Check | 0 errors | 🟡 Warn |
| Lint | 0 errors | 🟡 Warn |
| Syntax | 100% valid | 🔴 Yes |

### Stage 3: RUN CI SCRIPTS

```bash
# Run the full CI validation script
./scripts/ci_validate.sh

# Or individual checks:
./scripts/lint.sh
./scripts/type_check.sh
./scripts/test_unit.sh
./scripts/test_integration.sh
./scripts/security_scan.sh
```

**CI Script Checks:**
- [ ] `lint.sh` — No linting errors
- [ ] `type_check.sh` — No type errors
- [ ] `test_unit.sh` — All unit tests pass
- [ ] `test_integration.sh` — All integration tests pass
- [ ] `security_scan.sh` — No secrets in code

### Stage 4: GOVERNANCE CHECK

```
1. Validate file headers (version, date, author)
2. Check naming conventions (kebab-case)
3. Verify import patterns (structlog, httpx)
4. Check for L9 anti-patterns
5. Validate env var usage (no hardcoded secrets)
```

**Checks:**
- [ ] Headers present and valid
- [ ] Version numbers consistent
- [ ] No hardcoded secrets
- [ ] L9 patterns followed
- [ ] Protected files unchanged (or via GMP)

### Stage 5: YNP (Your Next Play)

```
Based on findings:
1. If all checks pass → Recommend: "Commit ready"
2. If minor issues → Recommend: "Fix X then commit"
3. If major issues → Recommend: "/gmp to fix Y"
4. If critical issues → Recommend: "Block: Z must be resolved"
```

---

## OUTPUT FORMAT

```markdown
## 🚦 PRECOMMIT GATE AUDIT

### 📊 Stage 1: Analysis + Evaluation

| Metric | Score | Status |
|--------|-------|--------|
| Structure Health | 85% | 🟢 |
| Code Quality | 92% | 🟢 |
| GMP Compliance | 78% | 🟡 |
| Test Coverage | 65% | 🟡 |
| **Overall** | **80%** | 🟢 |

**Issues Found:**
- 🟡 2 functions missing type hints
- 🟡 1 file missing docstring header
- 🟢 No critical issues

---

### 🔒 Stage 2: Governance Check

| Check | Status | Details |
|-------|--------|---------|
| Headers | ✅ | All files have valid headers |
| Versions | ✅ | Version numbers consistent |
| Secrets | ✅ | No hardcoded credentials |
| Patterns | ⚠️ | 1 file uses logging instead of structlog |
| Protected | ✅ | No protected files modified |

**Governance Score:** 95%

---

### ✅ Stage 3: Gate Decision

**GATE STATUS: 🟢 PASS WITH NOTES**

The commit can proceed, but consider these improvements:
1. Add type hints to 2 functions (optional)
2. Replace logging with structlog in api/utils.py (recommended)

---

### 🎯 YNP (Your Next Play)

**Primary:** Commit changes — gate passed
```bash
git add -A
git commit -m "feat: [description]"
```

**Before next commit:** Fix structlog usage in api/utils.py

**Alternates:**
1. `/forge fix structlog` to auto-fix pattern issue
2. `/gmp` if you want formal tracking of the fix
```

---

## GATE DECISIONS

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 **PASS** | All checks pass, no issues | Commit immediately |
| 🟢 **PASS WITH NOTES** | Minor issues, non-blocking | Commit, fix later |
| 🟡 **CONDITIONAL** | Issues need attention | Fix or acknowledge |
| 🔴 **BLOCK** | Critical issues found | Must fix before commit |

### Blocking Issues (Always Block)

- Hardcoded secrets detected
- Protected files modified without GMP
- Syntax errors in staged files
- Broken imports
- KERNEL_TIER changes without GMP

### Non-Blocking Issues (Notes)

- Missing docstrings
- Type hints incomplete
- Minor pattern deviations
- Test coverage below target

---

## USAGE

### Standard Precommit
```
/pipeline-precommit

Runs full 3-stage pipeline on all staged changes.
```

### Target Specific Files
```
/pipeline-precommit @api/routes/commands.py

Focuses audit on specific files.
```

### With Auto-Fix
```
/pipeline-precommit --fix

Automatically fixes minor issues (formatting, imports).
```

### Quick Mode
```
/pipeline-precommit --quick

Skip deep analysis, just governance + critical checks.
```

### Strict Mode
```
/pipeline-precommit --strict

Treat all issues as blocking (no PASS WITH NOTES).
```

---

## INTEGRATION WITH GIT WORKFLOW

### Pre-Commit Hook Setup

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running L9 precommit gate..."
# Trigger /pipeline-precommit via Cursor
# Block commit if BLOCK status returned
```

### Typical Workflow

```
1. Make changes
2. git add -A
3. /pipeline-precommit
4. If PASS: git commit
5. If BLOCK: Fix issues, repeat from step 3
```

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--fix` | Auto-fix minor issues | false |
| `--quick` | Skip deep analysis | false |
| `--strict` | All issues block | false |
| `--staged-only` | Only check staged files | true |
| `--json` | Output as JSON | false |

---

## ANTI-PATTERNS

❌ **DON'T:** Commit without running precommit
❌ **DON'T:** Ignore BLOCK status
❌ **DON'T:** Skip precommit for "small changes"
❌ **DON'T:** Override strict mode without reason

✅ **DO:** Run before every commit
✅ **DO:** Fix blocking issues immediately
✅ **DO:** Track non-blocking issues for later
✅ **DO:** Use --strict for main branch merges

---

## EXAMPLES

### Example 1: Clean Commit
```
/pipeline-precommit

🚦 PRECOMMIT GATE AUDIT

Stage 1: Overall 92% 🟢
Stage 2: Governance 100% 🟢

GATE STATUS: 🟢 PASS

🎯 YNP: Commit changes
git add -A && git commit -m "feat: add rate limiting"
```

### Example 2: Issues Found
```
/pipeline-precommit

🚦 PRECOMMIT GATE AUDIT

Stage 1: Overall 75% 🟡
Stage 2: Governance 85% 🟡

Issues:
- 🔴 Hardcoded API key in config.py:45
- 🟡 Missing type hints in 3 functions

GATE STATUS: 🔴 BLOCK

🎯 YNP: Remove hardcoded API key from config.py
Use: os.getenv("API_KEY") instead
```

### Example 3: Auto-Fix
```
/pipeline-precommit --fix

🚦 PRECOMMIT GATE AUDIT

Auto-fixes applied:
- ✅ Added missing imports
- ✅ Fixed formatting
- ✅ Updated headers

GATE STATUS: 🟢 PASS

🎯 YNP: Review auto-fixes, then commit
```
