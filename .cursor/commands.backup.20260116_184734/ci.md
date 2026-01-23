---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "CMD-CI-001"
component_name: "CI - Enforcement Generator"
layer: "commands"
domain: "ci_cd"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: ci
description: "Generate CI enforcement scripts from context or specification"
auto_chain: null
---

# === L9 CI: Generate Enforcement Scripts ===
# Cursor Slash Command: /ci
# Version: 1.0.0 (L9-native)
# Updated: 2026-01-01

---

## WHAT IT DOES

Generates CI enforcement scripts that:
1. **Catch violations** before they reach production
2. **Enforce rules** from recent refactors or explicit specifications
3. **Integrate** with existing `ci/run_ci_gates.sh` pipeline

**Two modes:**
- **Context mode** (default): Infer rule from recent work
- **Explicit mode**: User specifies the rule to enforce

---

## USAGE

```bash
# Context-aware (infers from recent work)
/ci

# Explicit rule specification
/ci no supabase imports
/ci all tools must have ToolName enum entries
/ci enforce structlog over logging module
/ci every api route must have auth decorator
```

---

## EXECUTION PROTOCOL

### Step 1: DETECT CONTEXT

If no explicit rule provided, infer from:

```
CONTEXT SOURCES (priority order):
1. Recent git diff (what files changed, what was removed/added)
2. Chat history (what did we just discuss/implement)
3. workflow_state.md recent changes
4. Open files in IDE
```

**Ask yourself:**
- What did we just remove? → Generate removal enforcement
- What did we just add? → Generate presence/consistency check
- What did we just fix? → Generate regression prevention

### Step 2: CLASSIFY RULE TYPE

| Rule Type | Trigger Keywords | Script Pattern |
|-----------|------------------|----------------|
| **REMOVAL** | "no", "remove", "eliminate", "ban", "forbid" | Grep for forbidden patterns |
| **CONSISTENCY** | "must match", "aligned", "consistent", "wired" | Compare two data sources |
| **PRESENCE** | "must have", "require", "every X needs Y" | Check file/pattern existence |
| **PATTERN** | "use X not Y", "replace", "prefer" | Detect wrong pattern, suggest right one |

### Step 3: GENERATE SCRIPT

Use this template structure:

```python
#!/usr/bin/env python3
"""
L9 CI Gate: [RULE_NAME]
========================

[One-line description of what this enforces]

Usage:
    python ci/[script_name].py

Exit codes:
    0 = All checks passed
    1 = Violations detected

Version: 1.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_[rule_name]() -> tuple[bool, list[str]]:
    """
    Check [what this validates].
    
    Returns:
        Tuple of (all_passed, list of error messages)
    """
    errors: list[str] = []
    
    # === DETECTION LOGIC HERE ===
    
    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("🔧 L9 CI GATE: [RULE_NAME]")
    print("=" * 60)
    
    passed, errors = check_[rule_name]()
    
    if passed:
        print("\n✅ CI GATE PASSED\n")
        return 0
    else:
        print(f"\n❌ CI GATE FAILED: {len(errors)} error(s)\n")
        for err in errors:
            print(f"   • {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Step 4: INTEGRATE (Optional)

Add to `ci/run_ci_gates.sh`:

```bash
# In run_ci_gates.sh, add a new gate function:

gate_N_[rule_name]() {
    log_header "GATE N: [RULE_NAME]"
    
    if [ ! -f "$SCRIPT_DIR/check_[rule_name].py" ]; then
        log_warn "[Rule] checker not found, skipping"
        return 0
    fi
    
    if ! python3 "$SCRIPT_DIR/check_[rule_name].py"; then
        log_error "[RULE] CHECK FAILED"
        return 1
    fi
    
    log_info "✅ [Rule] check passed"
    return 0
}

# Then add call in main():
gate_N_[rule_name] || exit 1
```

---

## SCRIPT PATTERNS BY TYPE

### Pattern 1: REMOVAL ENFORCEMENT

**Use when:** Something was eliminated (supabase, old library, deprecated pattern)

```python
def check_no_[thing]() -> tuple[bool, list[str]]:
    """Ensure [thing] is not used anywhere in codebase."""
    errors: list[str] = []
    
    FORBIDDEN_PATTERNS = [
        r"import supabase",
        r"from supabase",
        r"supabase\.",
        r"SUPABASE_",
    ]
    
    SCAN_DIRS = ["api", "core", "runtime", "services", "orchestration", "memory"]
    EXCLUDE_DIRS = {"__pycache__", ".git", "venv", "node_modules", "archive"}
    
    import re
    
    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob("*.py"):
            if any(excl in str(py_file) for excl in EXCLUDE_DIRS):
                continue
                
            content = py_file.read_text()
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, content):
                    rel_path = py_file.relative_to(PROJECT_ROOT)
                    errors.append(f"Forbidden pattern '{pattern}' in {rel_path}")
    
    return len(errors) == 0, errors
```

### Pattern 2: CONSISTENCY ENFORCEMENT

**Use when:** Two things must stay aligned (tools ↔ enums, routes ↔ schemas)

```python
def check_[x]_matches_[y]() -> tuple[bool, list[str]]:
    """Ensure [X] is consistent with [Y]."""
    errors: list[str] = []
    
    # Load source A
    from some_module import SOURCE_A
    items_a = set(SOURCE_A.keys())
    
    # Load source B
    from other_module import SOURCE_B
    items_b = set(SOURCE_B.values())
    
    # Check A ⊆ B
    missing_in_b = items_a - items_b
    for item in missing_in_b:
        errors.append(f"'{item}' in SOURCE_A but missing from SOURCE_B")
    
    # Check B ⊆ A (optional)
    missing_in_a = items_b - items_a
    for item in missing_in_a:
        errors.append(f"'{item}' in SOURCE_B but missing from SOURCE_A")
    
    return len(errors) == 0, errors
```

### Pattern 3: PRESENCE ENFORCEMENT

**Use when:** Every X must have a Y (every service needs tests, every route needs auth)

```python
def check_[x]_has_[y]() -> tuple[bool, list[str]]:
    """Ensure every [X] has a corresponding [Y]."""
    errors: list[str] = []
    
    # Find all X files
    x_files = list((PROJECT_ROOT / "api" / "routes").glob("*.py"))
    
    for x_file in x_files:
        if x_file.name.startswith("_"):
            continue
            
        # Check for corresponding Y
        expected_y = PROJECT_ROOT / "tests" / f"test_{x_file.stem}.py"
        if not expected_y.exists():
            errors.append(f"Route {x_file.name} has no test file: {expected_y.name}")
    
    return len(errors) == 0, errors
```

### Pattern 4: PATTERN REPLACEMENT ENFORCEMENT

**Use when:** Old pattern should be replaced with new (logging → structlog)

```python
def check_prefer_[new]_over_[old]() -> tuple[bool, list[str]]:
    """Ensure [new] is used instead of [old]."""
    errors: list[str] = []
    warnings: list[str] = []
    
    import re
    
    OLD_PATTERNS = [
        (r"^import logging$", "Use 'import structlog' instead"),
        (r"^from logging import", "Use 'from structlog import' instead"),
        (r"logging\.getLogger", "Use 'structlog.get_logger' instead"),
    ]
    
    ALLOWED_FILES = {"conftest.py", "test_*.py"}  # Exceptions
    
    for py_file in PROJECT_ROOT.rglob("*.py"):
        if any(py_file.match(allowed) for allowed in ALLOWED_FILES):
            continue
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue
            
        content = py_file.read_text()
        for pattern, suggestion in OLD_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(PROJECT_ROOT)
                errors.append(f"{rel_path}: {suggestion}")
    
    return len(errors) == 0, errors
```

---

## OUTPUT FORMAT

```markdown
## 🔧 CI SCRIPT: [Rule Name]

### 📍 Rule Type
[REMOVAL | CONSISTENCY | PRESENCE | PATTERN]

### 📝 Rule Description
[One sentence: what does this enforce?]

### 🎯 What It Catches
- [Specific violation 1]
- [Specific violation 2]

### 📁 Generated Script
`ci/check_[rule_name].py`

```python
[Full script content]
```

### 🔗 Integration (Optional)
Add to `ci/run_ci_gates.sh`:
```bash
[Gate function + call]
```

### ✅ Validation
```bash
python3 ci/check_[rule_name].py
# Expected: ✅ CI GATE PASSED
```
```

---

## EXAMPLES

### Example 1: Recent Removal (Supabase)
```
User: we just refactored eliminating supabase from repo
/ci

Output:
## 🔧 CI SCRIPT: No Supabase

### 📍 Rule Type
REMOVAL

### 📝 Rule Description
Ensures supabase is not imported or referenced anywhere in codebase.

### 🎯 What It Catches
- `import supabase`
- `from supabase import ...`
- `SUPABASE_URL` environment variables
- supabase client instantiation

[Generated script...]
```

### Example 2: Explicit Rule
```
/ci all api routes must have rate limiting decorator

Output:
## 🔧 CI SCRIPT: Rate Limiting Required

### 📍 Rule Type
PRESENCE

### 📝 Rule Description
Ensures every API route function has @rate_limit decorator.

[Generated script...]
```

### Example 3: Pattern Enforcement
```
/ci use httpx not requests library

Output:
## 🔧 CI SCRIPT: Prefer httpx Over requests

### 📍 Rule Type
PATTERN

### 📝 Rule Description
Ensures httpx is used for HTTP calls instead of requests library.

[Generated script...]
```

---

## CONTEXT INFERENCE EXAMPLES

| Recent Work | Inferred Rule |
|-------------|---------------|
| Removed supabase imports | No supabase anywhere |
| Added MEMORY_SEARCH to enum | All tools must have enum entries |
| Fixed mac_agent approval scope | High-risk tools must have approval scope |
| Migrated logging to structlog | No logging module, use structlog |
| Added auth to all routes | All routes must have auth decorator |

---

## ANTI-PATTERNS

❌ **DON'T:** Generate overly broad scripts that flag false positives
❌ **DON'T:** Forget to add exclusions for test files, archives, venv
❌ **DON'T:** Create scripts that require external services to run
❌ **DON'T:** Skip the validation step (always run the script)

✅ **DO:** Keep scripts focused on one rule
✅ **DO:** Provide clear error messages with file paths
✅ **DO:** Include common exclusions (venv, __pycache__, .git)
✅ **DO:** Test the script before considering it done
✅ **DO:** Integrate into CI pipeline for automation

---

## QUICK REFERENCE

```bash
# Context-aware (infers from recent work)
/ci

# Removal enforcement
/ci no [thing] imports/references

# Consistency enforcement  
/ci [X] must match [Y]

# Presence enforcement
/ci every [X] must have [Y]

# Pattern enforcement
/ci use [new] not [old]
```

---

**Remember:** A good CI script is worth 100 manual reviews. Catch once, enforce forever.

