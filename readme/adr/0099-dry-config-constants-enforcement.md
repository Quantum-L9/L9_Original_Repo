# ADR-0099: DRY Enforcement for Configuration Constants

## Status

**Accepted** — 2026-02-13

## Context

ADR-0098 established `core/config_constants.py` as the single source of truth for configuration defaults (scope whitelists, project IDs, caller-specific settings). However, ADR-0098 only documented the *decision* to centralize. This ADR documents the **enforcement mechanism** — how we ensure the DRY principle is maintained as the codebase evolves.

### Problem

After GMP-141 created `config_constants.py`, a follow-up scan (GMP-142) found **6 remaining issues** across production files where hardcoded scope lists and defaults had not yet been migrated. Additionally, the automated detector (`tools/bug_detection/find_config_mismatches.py`) produced false positives from:

- Test files (intentionally hardcoded values for assertions)
- Docstrings containing scope examples
- Domain-specific `scope` parameters unrelated to memory governance (e.g., tool graph visibility, approval scope)
- The canonical `config_constants.py` file itself

### Decision

**The DRY principle for configuration constants is enforced through three layers:**

1. **Canonical Source**: All configuration values are defined exactly once in `core/config_constants.py`. No other file may define these values independently.

2. **Automated Detection**: `make bug-detect` runs `tools/bug_detection/find_config_mismatches.py` which scans all production Python files for:
   - Inconsistent parameter defaults (`project_id`, `caller_scope`, `memory_scope`)
   - Hardcoded multi-element scope lists that should reference constants
   - Divergent `os.getenv('L9_PROJECT_ID', ...)` fallback values

3. **Intelligent Exclusions**: The detector excludes:
   - `core/config_constants.py` itself (canonical source)
   - `tests/` and `scripts/` directories (intentional hardcoded values for assertions/diagnostics)
   - Lines already referencing `config_constants` or `_DEFAULT_SCOPES` (already DRY)
   - Docstrings and comments (documentation, not code)
   - Domain-specific `scope` parameters in files where `scope` means something other than memory governance scope

### Constants Defined in `config_constants.py`

| Constant | Type | Purpose |
|----------|------|---------|
| `DEFAULT_PROJECT_ID_FALLBACK` | `str` | Default project ID when env var missing |
| `get_default_project_id()` | `function` | Reads `L9_PROJECT_ID` env with fallback |
| `CallerScope` | `Literal` | Valid caller scope values |
| `DEFAULT_CALLER_SCOPE` | `str` | Default scope for new callers |
| `DEFAULT_MEMORY_SCOPE` | `str` | Default memory scope |
| `DEFAULT_SEARCH_SCOPES` | `list[str]` | Default scopes for search operations |
| `ALLOWED_SCOPES_L` | `list[str]` | Scopes L (CTO agent) can access |
| `ALLOWED_SCOPES_CURSOR` | `list[str]` | Scopes Cursor agent can access |
| `MCP_WRITE_SCOPES` | `list[str]` | Valid scopes for MCP save_memory schema |
| `MCP_SEARCH_SCOPES` | `list[str]` | Valid scopes for MCP search_memory schema |
| `MemoryScope` | `Literal` | All valid memory scope values |
| `RLS_VISIBLE_SCOPES` | `frozenset[str]` | Scopes visible through RLS policies |
| `get_allowed_scopes_for_caller()` | `function` | Returns scope whitelist by caller ID |
| `get_default_scope_for_caller()` | `function` | Returns default scope by caller ID |

### Standalone Client Pattern

For files that run outside the L9 Python path (e.g., `agents/cursor/cursor_memory_client.py`), the DRY pattern is:

```python
# ADR-0099: DRY — defined once, used everywhere.
# Canonical source: core.config_constants.ALLOWED_SCOPES_CURSOR
# Duplicated here because this client runs standalone (outside L9 sys.path).
_DEFAULT_SCOPES: list[str] = ["cursor", "developer", "global"]
```

The value is defined once at module level with a comment citing the canonical source. All usages within the file reference `_DEFAULT_SCOPES`.

## Consequences

### Positive

- **Zero configuration drift**: `make bug-detect` exits 0 — no mismatches in production code
- **DRY enforcement is automated**: New drift is caught by CI before merge
- **False positive rate near zero**: Intelligent exclusions prevent noise from tests, docs, and unrelated parameters
- **Self-documenting**: Each constant has a docstring explaining its purpose and usage context
- **Standalone clients supported**: Pattern for files outside sys.path preserves DRY within the file

### Negative

- Standalone clients (cursor_memory_client.py) must manually sync if the canonical value changes — mitigated by the detector catching the drift
- Adding new scope values requires updating `config_constants.py` and potentially MCP schema constants
- Detector parse warnings for malformed scripts (cosmetic, not functional)

## Compliance

- **ADR-0098**: This ADR extends 0098 with enforcement specifics
- **ADR-0087**: SQL parameterization — config constants prevent SQL injection via scope values
- **ADR-0006**: PacketEnvelope audit — scope values in packets come from validated constants

## References

- `core/config_constants.py` — Canonical source of truth
- `tools/bug_detection/find_config_mismatches.py` — Automated detector
- `readme/bug_patterns/PATTERN_001_config_drift.md` — Bug pattern documentation
- GMP-141: Initial centralization
- GMP-142: DRY migration + detector refinement
