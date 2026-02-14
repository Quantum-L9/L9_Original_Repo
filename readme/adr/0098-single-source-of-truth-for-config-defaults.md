## ADR-0098: Single Source of Truth for Configuration Defaults (2026-02-13)

**Status:** Accepted

**Tier:** CRITICAL

**Decision:** All configuration defaults, whitelists, and scope enums MUST be defined in a single canonical location: `core/config_constants.py`. No module may hardcode these values inline.

**Context:**

Multiple bugs (BUG-001 through BUG-004) traced to configuration values scattered across files:
- `project_id` default: "l9" in some files, "l9-default" in others → 403 errors on every search
- `caller_scope` whitelist: outdated after adding "cursor" scope → valid Cursor callers rejected
- RLS policies: stuck on migration 0008 defaults after scope expansion → data access failures

Root cause: **Distributed Configuration Anti-Pattern** — no centralized configuration constants.

**Canonical File:** `core/config_constants.py`

**What it contains:**
- `get_default_project_id()` — runtime project ID from env with consistent fallback
- `DEFAULT_SEARCH_SCOPES` — default scopes for search operations
- `ALLOWED_SCOPES_L` / `ALLOWED_SCOPES_CURSOR` — per-caller scope whitelists
- `CallerScope` / `MemoryScope` — Literal type aliases for type safety
- `get_allowed_scopes_for_caller()` — helper to get scopes by caller ID
- `get_default_scope_for_caller()` — helper to get default scope by caller ID

**Usage in code:**

```python
from core.config_constants import (
    get_default_project_id,
    DEFAULT_SEARCH_SCOPES,
    get_allowed_scopes_for_caller,
    get_default_scope_for_caller,
)

project_id = get_default_project_id()
scopes = requested_scopes or DEFAULT_SEARCH_SCOPES
allowed = get_allowed_scopes_for_caller(caller_id)
```

**Consequences:**

Positive:
- Single source of truth prevents drift across files
- Type safety via `Literal` types catches invalid values at type-check time
- Easy updates: change once in `config_constants.py`, applies everywhere
- Grep-friendly: `from core.config_constants import` shows all consumers

Negative:
- Extra import required in each consuming module (minor boilerplate)

**Enforcement:**
- `tools/bug_detection/find_config_mismatches.py` scans for hardcoded defaults
- `make bug-detect` runs the scanner
- CI integration: add `make bug-detect` to pipeline

**Related Bugs:** BUG-001, BUG-002, BUG-003, BUG-004 (2026-02-13)

**See Also:**
- ADR-0014 (DORA metadata blocks)
- ADR-0019 (structlog logging standard)
- Bug Pattern: `readme/bug_patterns/PATTERN_001_config_drift.md`
