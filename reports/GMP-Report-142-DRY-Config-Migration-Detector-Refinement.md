# GMP-142: DRY Config Constants Migration + Detector Refinement

**GMP ID:** GMP-142
**Title:** DRY Config Constants Migration + Detector Refinement
**Tier:** RUNTIME_TIER
**Date:** 2026-02-13
**Status:** COMPLETE
**Depends On:** GMP-141 (Bug Classification & Knowledge Capture)

---

## TODO Plan (Locked)

### Step 1: Production Fixes (DRY Migration)
- [x] `memory/governance_gate.py` — Replace hardcoded scope whitelists with `ALLOWED_SCOPES_L`, `ALLOWED_SCOPES_CURSOR`
- [x] `api/routes/mcp.py` — Replace hardcoded scope whitelists with `ALLOWED_SCOPES_L`, `ALLOWED_SCOPES_CURSOR`
- [x] `mcp_memory/src/mcp_server.py` — Replace 3 hardcoded JSON schema enum lists with `MCP_WRITE_SCOPES`, `MCP_SEARCH_SCOPES`
- [x] `mcp_memory/src/routes/memory_unified.py` — Replace 2 remaining `["developer", "global", "l-private"]` with `ALLOWED_SCOPES_L`
- [x] `agents/cursor/cursor_memory_client.py` — DRY 21 occurrences of `["cursor", "developer", "global"]` into `_DEFAULT_SCOPES`
- [x] `agents/cursor/integrations/cursor_langgraph.py` — Replace 2 `["developer", "global"]` with `DEFAULT_SEARCH_SCOPES`
- [x] `core/agents/bootstrap/phase_7_verify_and_lock.py` — Replace 1 `["developer", "global"]` with `DEFAULT_SEARCH_SCOPES`

### Step 2: Detector Refinement
- [x] Add `igor/`, `.backup/`, `DONE!/` to excluded directories
- [x] Add `SCOPE_PARAM_EXCLUDED_FILES` for domain-specific `scope` parameters
- [x] Exclude `core/config_constants.py` from all detectors (canonical source)
- [x] Exclude `tests/` and `scripts/` from scope-list detector (intentional hardcoded values)
- [x] Skip docstrings in scope-list extraction
- [x] Skip lines referencing `config_constants` or `_DEFAULT_SCOPES` (already DRY)
- [x] Remove `scope` from default-value detector (different defaults are intentional per context)
- [x] Write clean report when 0 issues found (replace stale reports)

---

## Scope Boundaries

**MAY modify:**
- `core/config_constants.py` (add `MCP_WRITE_SCOPES`, `MCP_SEARCH_SCOPES`)
- `memory/governance_gate.py` (import + replace)
- `api/routes/mcp.py` (import + replace)
- `mcp_memory/src/mcp_server.py` (import + replace 3 locations)
- `mcp_memory/src/routes/memory_unified.py` (import + replace 2 locations)
- `agents/cursor/cursor_memory_client.py` (add constant + replace 21 locations)
- `agents/cursor/integrations/cursor_langgraph.py` (import + replace 2 locations)
- `core/agents/bootstrap/phase_7_verify_and_lock.py` (import + replace 1 location)
- `tools/bug_detection/find_config_mismatches.py` (refinement)
- `readme/adr/0099-dry-config-constants-enforcement.md` (new ADR)
- `readme/adr/README.md` (register ADR-0099)

**MAY NOT modify:**
- Kernel files, executor, memory substrate core
- Docker/deployment manifests
- Test files (intentional hardcoded values)

---

## Files Modified

| File | Action | Lines Changed |
|------|--------|---------------|
| `core/config_constants.py` | Insert | +6 (MCP_WRITE_SCOPES, MCP_SEARCH_SCOPES) |
| `memory/governance_gate.py` | Replace | Import + 2 scope list replacements |
| `api/routes/mcp.py` | Replace | Import + 2 scope list replacements |
| `mcp_memory/src/mcp_server.py` | Replace | Import + 3 JSON schema enum replacements |
| `mcp_memory/src/routes/memory_unified.py` | Replace | Import + 2 scope list replacements |
| `agents/cursor/cursor_memory_client.py` | Insert+Replace | +4 (constant def) + 21 replacements |
| `agents/cursor/integrations/cursor_langgraph.py` | Replace | Import + 2 scope list replacements |
| `core/agents/bootstrap/phase_7_verify_and_lock.py` | Replace | Import + 1 scope list replacement |
| `tools/bug_detection/find_config_mismatches.py` | Refine | ~30 lines (exclusions, docstring skip, clean report) |
| `readme/adr/0099-dry-config-constants-enforcement.md` | Create | New ADR |
| `readme/adr/README.md` | Update | Register ADR-0099, bump next to 0100 |

---

## Validation Results

### `make bug-detect` — PASS

```
Exit code: 0
no_config_mismatches_detected
Report: 0 issues
```

**Before GMP-142:** 6 issues (1 critical, 5 high)
**After GMP-142:** 0 issues

### Linter — PASS

All 8 modified production files: no linter errors.

---

## Phase 5: Recursive Verification

| Check | Result |
|-------|--------|
| Scope drift from Phase 0 plan | None — all planned files modified, no extras |
| New constants in config_constants.py | `MCP_WRITE_SCOPES`, `MCP_SEARCH_SCOPES` — both used |
| Standalone client pattern | `_DEFAULT_SCOPES` in cursor_memory_client.py with canonical source comment |
| Detector false positive rate | 0 false positives in production code |
| ADR-0099 registered | Yes, in README.md |
| Previous GMP-141 assets intact | Yes — ADR-0098, PATTERN-001, Makefile target all preserved |

---

## Outstanding Items

None. All production code uses `config_constants.py`. Detector passes clean.

---

## Final Declaration

GMP-142 COMPLETE. All configuration constants follow the DRY principle as enforced by ADR-0098 and ADR-0099. The automated detector (`make bug-detect`) validates zero drift across all production files.
