# GMP-Report-141: Bug Classification & Knowledge Capture

**GMP ID:** GMP-141
**Title:** Bug Classification & Knowledge Capture — Implement Reusable Assets
**Tier:** RUNTIME_TIER
**Date:** 2026-02-13
**Status:** PASS

---

## TODO Plan (Locked)

| # | File | Action | Status |
|---|------|--------|--------|
| 1 | `core/config_constants.py` | CREATE | ✅ |
| 2 | `readme/adr/0098-single-source-of-truth-for-config-defaults.md` | CREATE | ✅ |
| 3 | `tools/bug_detection/find_config_mismatches.py` | CREATE | ✅ |
| 4 | `tools/bug_detection/__init__.py` | CREATE | ✅ |
| 5 | `readme/bug_patterns/PATTERN_001_config_drift.md` | CREATE | ✅ |
| 6 | `Makefile` | INSERT (bug-detect target) | ✅ |
| 7 | `mcp_memory/src/main.py` | REPLACE (import from config_constants) | ✅ |
| 8 | `mcp_memory/src/mcp_server.py` | REPLACE (import from config_constants) | ✅ |
| 9 | `mcp_memory/src/routes/memory_unified.py` | REPLACE (import from config_constants) | ✅ |
| 10 | `readme/adr/README.md` | INSERT (ADR-0098 entry + bump next number) | ✅ |

---

## Scope Boundaries

- **In scope:** Centralize config defaults, create detection tooling, create ADR + bug pattern docs, wire mcp_memory imports
- **Out of scope:** Fixing ALL hardcoded scope lists across entire codebase (incremental), CI pipeline integration, migration 0033 for RLS policies
- **Behavioral changes:** NONE — all values remain identical, only source location changed

---

## Files Modified

| File | Lines Changed | Action |
|------|--------------|--------|
| `core/config_constants.py` | +133 (new) | Created centralized config constants |
| `readme/adr/0098-single-source-of-truth-for-config-defaults.md` | +57 (new) | ADR documenting the decision |
| `tools/bug_detection/find_config_mismatches.py` | +319 (new) | Automated detector with 3 scan modes |
| `tools/bug_detection/__init__.py` | +5 (new) | Package init |
| `readme/bug_patterns/PATTERN_001_config_drift.md` | +119 (new) | Bug pattern documentation |
| `Makefile` | +7 | Added `bug-detect` target |
| `readme/adr/README.md` | +4 | Added ADR-0098 to inventory, bumped next number to 0099 |
| `mcp_memory/src/main.py` | ~15 | Replaced hardcoded project_id/scopes with config_constants imports |
| `mcp_memory/src/mcp_server.py` | ~12 | Replaced hardcoded project_id/scopes with config_constants imports |
| `mcp_memory/src/routes/memory_unified.py` | ~25 | Replaced hardcoded project_id/scopes with config_constants imports |

---

## Validation Results

### Compilation
- `core/config_constants.py` — ✅ py_compile pass
- `mcp_memory/src/main.py` — ✅ py_compile pass
- `mcp_memory/src/mcp_server.py` — ✅ py_compile pass
- `mcp_memory/src/routes/memory_unified.py` — ✅ py_compile pass
- `tools/bug_detection/find_config_mismatches.py` — ✅ py_compile pass

### Behavioral Verification
- `get_default_project_id()` → `"l9-default"` ✅ (matches original)
- `get_allowed_scopes_for_caller("L")` → `["developer", "global", "l-private", "cursor"]` ✅
- `get_allowed_scopes_for_caller("C")` → `["cursor", "developer", "global"]` ✅
- `get_default_scope_for_caller("L")` → `"developer"` ✅
- `get_default_scope_for_caller("C")` → `"cursor"` ✅

### Detector Run
- **6 issues detected** (1 critical, 5 high) — these are pre-existing hardcoded scope lists in files outside the 3 mcp_memory files we fixed
- Report: `reports/bug_detection/config_mismatches.md`
- Runtime: 11s

### Linter
- All 5 edited files: ✅ 0 linter errors

---

## Phase 5: Recursive Verification

| Check | Result |
|-------|--------|
| All planned files touched? | ✅ 10/10 |
| No unplanned files modified? | ✅ (README.md update is standard ADR procedure) |
| No behavioral changes? | ✅ All values identical to originals |
| No scope drift from Phase 0? | ✅ |
| No hardcoded project_id in mcp_memory? | ✅ 0 occurrences |
| No hardcoded scope lists in mcp_memory? | ✅ 0 occurrences (except docstring comments) |

---

## Outstanding Items

1. **Incremental migration**: ~49 remaining hardcoded scope lists across the broader codebase (outside mcp_memory)
2. **Migration 0033**: `migrations/0033_add_cursor_scope.sql` exists but needs RLS policy update verification
3. **CI integration**: Add `make bug-detect` to CI pipeline
4. **Remaining `os.getenv("L9_PROJECT_ID", ...)` calls**: Check `api/routes/mcp.py`, `memory/governance_gate.py`

---

## Final Declaration

GMP-141 is **PASS**. All 4 deliverables from the Bug Knowledge Package have been created:
1. ✅ `core/config_constants.py` — Centralized config (ADR-0098)
2. ✅ `tools/bug_detection/find_config_mismatches.py` — Automated detector
3. ✅ `readme/bug_patterns/PATTERN_001_config_drift.md` — Bug pattern doc
4. ✅ `readme/adr/0098-single-source-of-truth-for-config-defaults.md` — ADR

Plus: Makefile target, mcp_memory wiring (3 files), ADR README update.

**Templates used:** GMP-Action, GMP-Audit Canonical
**Phases completed:** 0, 1, 2, 3, 4, 5, 6
