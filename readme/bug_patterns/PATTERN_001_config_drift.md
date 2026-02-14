# Bug Pattern 001: Configuration Drift

## Pattern Name
**Distributed Configuration Anti-Pattern**

## Classification
- **Category:** Configuration Management
- **Severity:** 🔴 CRITICAL
- **Frequency:** Common (4 instances in one session)
- **Detection Difficulty:** Hard (requires cross-file analysis)

## Symptoms
- 403 errors despite valid auth
- Feature works in some contexts but not others
- "It worked yesterday" reports after unrelated changes
- Inconsistent behavior across API endpoints

## Root Cause
Configuration values (defaults, enums, whitelists) defined in multiple locations without synchronization.

## Real-World Examples (L9 Codebase)

### Example 1: project_id Default Mismatch
```python
# mcp_memory/src/mcp_server.py (BEFORE fix)
def search_memory(project_id: str = "l9"):  # ❌ WRONG default

# mcp_memory/src/main.py (BEFORE fix)
governance_context = build_context(
    project_id="l9-default"  # ❌ MISMATCH — different default
)
```

**Impact:** Every search returned 403 because governance context project_id didn't match.

### Example 2: Scope Whitelist Staleness
```python
# mcp_memory/src/main.py (BEFORE fix)
allowed_scopes = ["developer", "global"]  # ❌ Missing "cursor"
if caller_scope not in allowed_scopes:
    raise ValueError  # Rejected valid Cursor callers
```

### Example 3: Schema-Code Drift
```sql
-- migrations/0008_rls_policies.sql (BEFORE fix)
CREATE POLICY memory_read_policy
  USING (scope IN ('shared') OR scope IS NULL);  -- ❌ Outdated

-- Later: Added "cursor", "agent" scopes but forgot to update policy
```

## Detection Strategy

### Automated (Recommended)
```bash
# Run the configuration mismatch detector
python tools/bug_detection/find_config_mismatches.py

# Or via Makefile
make bug-detect
```

### Manual Search (Quick)
```bash
# Find parameter default inconsistencies
git grep -n "project_id.*=" | grep "default"

# Find scope-related hardcoded lists
git grep -n "developer.*global" | grep -E "(list|frozenset|\[)"

# Find SQL policies with scope checks
git grep -n "scope IN" migrations/
```

## Prevention

### Solution 1: Single Source of Truth (ADR-0098)

All configuration defaults centralized in `core/config_constants.py`:

```python
from core.config_constants import (
    get_default_project_id,
    DEFAULT_SEARCH_SCOPES,
    ALLOWED_SCOPES_L,
    ALLOWED_SCOPES_CURSOR,
    get_allowed_scopes_for_caller,
)
```

### Solution 2: CI Enforcement

```bash
# In CI pipeline
make bug-detect  # Fails if mismatches detected
```

### Solution 3: Migration Validation

When creating new migrations that affect scope or project_id:
```sql
-- VALIDATION: Check if this affects existing policies
-- RUN: SELECT * FROM pg_policies WHERE policyname LIKE '%scope%';
```

## AI Agent Search Prompts

### Find Similar Default Value Bugs
```
Search L9 repo for "distributed configuration anti-pattern" instances:
1. Find parameters named project_id, scope, or caller_scope with default values
2. Group by parameter name and list all unique default values
3. Flag any parameter appearing with 2+ different defaults
4. Check migrations/ for RLS policies using scope IN (...) and compare against current allowed scopes
```

### Proactive Detection
```
Audit the L9 codebase for configuration values that should be centralized:
1. Scan for string literals appearing in 3+ files (likely config)
2. Find enums/unions defined multiple times
3. Check SQL migrations for hardcoded lists that match Python enums
4. Identify parameters with "default" in name but no import from config module
```

## Related Patterns
- **Pattern 002:** Schema Migration Incomplete (migrations don't update dependent objects)
- **Pattern 003:** Enum Expansion Incompleteness (adding enum value but missing usages)

## Fix Checklist
- [x] Create centralized config file (`core/config_constants.py`)
- [x] Document in ADR (ADR-0098)
- [x] Create automated detector (`tools/bug_detection/find_config_mismatches.py`)
- [x] Add Makefile target (`make bug-detect`)
- [ ] Replace all hardcoded values with imports (Phase 3 — incremental)
- [ ] Update SQL migrations/policies (migration 0033)
- [ ] Add to CI pipeline

## Historical Context
**Discovered:** 2026-02-13
**Bugs Fixed:** BUG-001, BUG-002, BUG-003, BUG-004
**Files Changed:** 4 (initial fixes), 3+ (config_constants integration)
**Time to Root Cause:** ~20 minutes (due to distributed nature)
**Prevention Assets Created:** ADR-0098, config_constants.py, find_config_mismatches.py
