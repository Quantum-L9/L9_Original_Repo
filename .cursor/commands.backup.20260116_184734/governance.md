---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-GOVERNANCE-001"
component_name: "Governance - Compliance Validation"
layer: "commands"
domain: "compliance"
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
name: governance
description: "L9-native compliance check — headers, versions, tags, domains, policy validation"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 GOVERNANCE: Strict Compliance Validation ===
# Cursor Slash Command: /governance
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After validation, **automatically runs /ynp** to recommend fixes, commit readiness, or next check.

---

## WHAT IT DOES

**Strict governance validation across 6 dimensions:**

1. **Headers** — Required metadata present and valid
2. **Versions** — Consistent, semantic versioning
3. **Tags/Domain** — Correct classification
4. **L9 Patterns** — Code follows L9 conventions
5. **Policy Compliance** — No contradictions with governance
6. **Protected Files** — KERNEL_TIER changes via GMP only

**Output:** Validation report + Fix Pack for any issues.

**Key principle:** Nothing merges without governance pass.

---

## WHEN TO USE

| Scenario | Why /governance |
|----------|-----------------|
| Before commit | Catch issues before they enter repo |
| Before PR | Ensure review-ready state |
| Before canonical promotion | Final gate for production |
| CI pipeline | Automated compliance check |
| After bulk changes | Verify consistency across files |

---

## EXECUTION PROTOCOL

### Step 1: HEADER VALIDATION

Check all modified files for required headers:

```yaml
# Python files require:
"""
Module description.

Created: YYYY-MM-DD
Modified: YYYY-MM-DD
Author: [name]
"""

# YAML files require:
# META:
#   path: /path/to/file.yaml
#   filename: file.yaml
#   version: X.Y.Z
#   created: YYYY-MM-DD
#   modified: YYYY-MM-DD
```

**Header Checks:**
| Check | Required | Blocking |
|-------|----------|----------|
| Docstring present | ✅ Yes | 🟡 Warn |
| Created date | ✅ Yes | 🟡 Warn |
| Modified date current | ✅ Yes | 🟡 Warn |
| Version field | For YAML | 🟡 Warn |

### Step 2: VERSION VALIDATION

```
VERSION CHECKS:
├── Semantic format (X.Y.Z)
├── Increment logic correct
│   ├── MAJOR: Breaking changes
│   ├── MINOR: New features
│   └── PATCH: Bug fixes
├── Version consistency across related files
└── No version downgrades
```

### Step 3: DOMAIN/TAG VALIDATION

```
DOMAIN CHECKS:
├── Domain field matches file location
│   ├── core/ → domain: core
│   ├── api/ → domain: api
│   ├── memory/ → domain: memory
│   └── orchestration/ → domain: orchestration
├── Tags are valid L9 tags
│   ├── agent, kernel, tool, memory, governance
│   ├── api, router, service, model
│   └── test, util, config
└── No deprecated tags
```

### Step 4: L9 PATTERN VALIDATION

```python
L9_PATTERN_CHECKS = {
    # Required patterns
    "structlog": "Uses structlog, not logging module",
    "httpx": "Uses httpx, not requests",
    "async_io": "Async functions for I/O",
    "pydantic_v2": "Pydantic v2 patterns (model_config)",
    "type_hints": "Public functions have type hints",
    
    # Forbidden patterns
    "no_print": "No print() statements",
    "no_bare_except": "No bare except clauses",
    "no_sync_in_async": "No time.sleep in async",
    "no_hardcoded_secrets": "No credentials in code",
}
```

### Step 5: POLICY COMPLIANCE

```
POLICY CHECKS:
├── No contradictions with existing kernels
├── Safety constraints respected
├── Authority hierarchy intact
├── Approval gates present where required
└── Memory substrate patterns followed
```

### Step 6: PROTECTED FILE CHECK

```
PROTECTED FILES (require /gmp, not /forge):
├── core/kernels/kernel_loader.py
├── core/agents/executor.py
├── memory/substrate_service.py
├── runtime/websocket_orchestrator.py
├── docker-compose.yml
└── Any file in kernels/ directory
```

---

## OUTPUT FORMAT

```markdown
## 🔒 GOVERNANCE VALIDATION REPORT

### 📊 Summary
- **Files Checked:** [count]
- **Issues Found:** [count]
- **Blocking Issues:** [count]
- **Status:** [PASS | PASS WITH WARNINGS | FAIL]

---

### ✅ Passed Checks

| Check | Files | Status |
|-------|-------|--------|
| Headers | 12/12 | ✅ |
| Versions | 12/12 | ✅ |
| L9 Patterns | 10/12 | ⚠️ |
| Policy | 12/12 | ✅ |

---

### ⚠️ Warnings (Non-Blocking)

| File | Issue | Fix |
|------|-------|-----|
| api/utils.py | Uses `logging` | Change to `structlog` |
| core/tools/new.py | Missing docstring | Add module docstring |

---

### 🔴 Errors (Blocking)

| File | Issue | Severity |
|------|-------|----------|
| config/secrets.py | Hardcoded API key L:45 | 🔴 CRITICAL |
| core/executor.py | Modified without GMP | 🔴 PROTECTED |

---

### 🔧 FIX PACK

Apply these fixes to resolve all issues:

#### Fix 1: api/utils.py (logging → structlog)
```python
# Replace:
import logging
logger = logging.getLogger(__name__)

# With:
import structlog
logger = structlog.get_logger(__name__)
```

#### Fix 2: core/tools/new.py (add docstring)
```python
# Add at top of file:
"""
New tool implementation.

Created: 2026-01-01
Modified: 2026-01-01
"""
```

#### Fix 3: config/secrets.py (remove hardcoded key)
```python
# Replace L:45:
API_KEY = "sk-12345"

# With:
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")
```

---

### 🎯 YNP (Your Next Play)
**Primary:** [Action based on validation result]
```

---

## USAGE

### Full Governance Check
```
/governance

Checks all staged files.
```

### Target Specific Files
```
/governance @api/routes/commands.py
/governance @core/

Checks only specified files/directory.
```

### With Auto-Fix
```
/governance --fix

Automatically applies non-breaking fixes.
```

### CI Mode
```
/governance --ci

Outputs in CI-friendly format, exit code 1 on failure.
```

### Strict Mode
```
/governance --strict

Treat all warnings as errors.
```

---

## GOVERNANCE TIERS

| Tier | Files | Check Level |
|------|-------|-------------|
| **KERNEL** | kernels/, executor.py, substrate | MAXIMUM — all checks mandatory |
| **RUNTIME** | agents/, tools/, orchestration/ | HIGH — patterns + policies |
| **INFRA** | docker-compose, deploy/, scripts/ | MEDIUM — env + secrets |
| **UX** | docs/, tests/, client/ | STANDARD — headers only |

---

## INTEGRATION

- **Part of:** `/pipeline-precommit` (Stage 4)
- **Chains to:** `/ynp` (always)
- **Blocks:** Commit if FAIL status
- **Auto-fixes:** Non-breaking issues

---

## CI INTEGRATION

```yaml
# .github/workflows/governance.yml
governance-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run Governance Check
      run: |
        # Simulated by running checks
        python -m ruff check .
        python -m mypy . --ignore-missing-imports
        # Check for forbidden patterns
        ! grep -r "import logging" --include="*.py" core/ api/
        ! grep -r "import requests" --include="*.py" core/ api/
```

---

## EXAMPLES

### Example 1: Clean Pass
```
/governance @api/routes/

🔒 GOVERNANCE VALIDATION REPORT

📊 Summary
- Files Checked: 5
- Issues Found: 0
- Status: ✅ PASS

🎯 YNP: Ready to commit
```

### Example 2: Warnings
```
/governance @core/tools/

🔒 GOVERNANCE VALIDATION REPORT

📊 Summary
- Files Checked: 8
- Issues Found: 2
- Blocking: 0
- Status: ⚠️ PASS WITH WARNINGS

⚠️ Warnings:
1. new_tool.py: Missing type hints on 2 functions
2. registry.py: Modified date not updated

🔧 FIX PACK provided

🎯 YNP: Fix warnings (optional) or commit with notes
```

### Example 3: Blocking Failure
```
/governance @config/

🔒 GOVERNANCE VALIDATION REPORT

📊 Summary
- Files Checked: 3
- Issues Found: 1
- Blocking: 1
- Status: 🔴 FAIL

🔴 Blocking Error:
- secrets.py L:23: Hardcoded AWS credentials

🎯 YNP: MUST fix secrets.py before commit
```

---

## ANTI-PATTERNS

❌ **DON'T:** Skip governance for "quick fixes"
❌ **DON'T:** Ignore warnings repeatedly
❌ **DON'T:** Bypass protected file checks
❌ **DON'T:** Commit with FAIL status

✅ **DO:** Run governance before every commit
✅ **DO:** Fix warnings proactively
✅ **DO:** Use /gmp for protected files
✅ **DO:** Apply Fix Pack suggestions

