# L9 Memory + Cursor Wiring Audit: Phase 0 TODO PLAN
**Date:** January 13, 2026  
**Status:** LOCKED FOR EXECUTION  
**Scope:** Repair stale paths in docs, audit cache, and scripts; verify no L9 invariants broken.

---

## EXECUTIVE SUMMARY

The "Wiring Mis-Alignment Audit Plan" (original) is **too local and reactive**. This Phase 0 reframes it as a **repo-wide, invariant-backed wiring audit** for the Memory + Cursor integration boundary.

**3 Core Problems Identified:**
1. `gap-analysis-memory.md` has 7+ stale refs to non-existent `api/routes/memory.py`
2. `.audit_cache/manifest.json` lists 5 files moved from `tools/`, `memory/extractor/`, `core/governance/` to `agents/cursor/`
3. Audit scripts (`scriptsmemory*.py`, `scriptsaudittier1*.py`) may emit stale paths into cache

**Outcome:** Synchronized doc→code→audit mapping with live path verification.

---

## PART I: WIRING INVARIANT DECLARATION

**Core Invariant:**
> Every referenced path to memory APIs and Cursor integration must:
> - Point to a real file in the current codebase
> - Match the canonical router layout from `file_metrics.txt`:
>   - `apimemoryrouter.py` (689 LOC, 9 classes, 1 method, 17 async; unified memory router)
>   - `mcpmemorysrcroutesmemory.py` (913 LOC, 14 async; memory ingestion)
>   - `mcpmemorysrcroutesmemoryunified.py` (1409 LOC, 3 classes, 16 async; unified MCP server)
>   - `apiroutescursor.py` (189 LOC, 3 classes, 1 method, 3 async; cursor task execution)
>   - `agentscursorextractorscursoractionextractor.py` (661 LOC, real)
>   - `agentscursorintegrationscursorgateway.py` (282 LOC, real)
>   - Related substrate: `memorysubstrateservice.py` (908 LOC, 19 async), `memorysubstraterepository.py` (976 LOC, 25 async)

**Protected L9 Invariants (DO NOT TOUCH):**
- ✓ `coreschemaseventstream.py`, `coreschemaswseventstream.py` (packet protocol)
- ✓ `coregovernanceapprovalmanager.py`, `coregovernanceengine.py`, `memorygovernancepatterns.py`
- ✓ Memory substrate models: `memorysubstratemodels.py`
- ✓ Kernel infrastructure: `corekernelsschemas.py`, `runtimekernelloader.py`

---

## PART II: STRUCTURED DOC–CODE ALIGNMENT TABLE

**This table is the ground truth for all path references:**

| Logical Component | Old Path (Stale) | New Canonical Path | Router/Module | File Metrics Anchor | Notes |
|---|---|---|---|---|---|
| **Memory Batch Operations** | `api/routes/memory.py` (WRONG) | `api/memory/router.py` *or* see below | `apimemoryrouter.py` | 689 LOC, async: `batchwriterequest`, `batchwriterequest`, `compactstorage` | Unified batch write/search/health. Handles PacketEnvelope mutations. |
| **Memory Ingestion (MCP)** | N/A | `mcp/memory/src/routes/memory.py` (conceptual) | `mcpmemorysrcroutesmemory.py` | 913 LOC, 14 async fns: `saveMemory`, `searchMemory`, `queryTemporal`, `getContextInjection`, `getMemoryStats`, `getProactiveSuggestions`, `getGcStats`, `getStats`, `healthcheck`, others | MCP server's memory save/search surface. |
| **Unified MCP Routes** | N/A | `mcp/memory/src/routes/memory_unified.py` (conceptual) | `mcpmemorysrcroutesmemoryunified.py` | 1409 LOC, 16 async: `saveMemoryRoute`, `searchMemoryRoute`, `others` | Newer unified unified routing; may supersede older mcp routes. Check phase 0 validation. |
| **Cursor Task Execution** | N/A | `api/routes/cursor.py` *or* `api/cursor/routes.py` | `apiroutescursor.py` | 189 LOC, 3 async: `cursorTask`, `cursorResume`, `cursorTest` | Direct Cursor agent task dispatch. Thin wrapper. |
| **Cursor Extractor** | `memory/extractor/cursor_action_extractor.py` (MOVED) | `agents/cursor/extractors/cursor_action_extractor.py` | `agentscursorextractorscursoractionextractor.py` | 661 LOC, 11 async fns (e.g., extract Cursor actions from memory) | Dual-mirrored in `igoraudit-memorymemoryextractorcursoractionextractor.py` (661 LOC). |
| **Cursor Gateway** | `core/governance/cursor_memory_kernel.py` (MOVED) | `agents/cursor/cursor_gateway.py` | `agentscursorintegrationscursorgateway.py` | 282 LOC, 2 classes, 5 async | Scope enforcement, memory access boundary for Cursor agent. |
| **Cursor Integration Base** | `tools/cursor_client.py` (MOVED) | `agents/cursor/cursor_client.py` | (none found in metrics; assume `agentscursorintegrationscursor*.py`) | Search `agentscursor*` | Primary Cursor agent integration surface. |
| **Cursor Check Script** | `scripts/cursor_check_mistakes.py` (MOVED) | `agents/cursor/scripts/cursor_check_mistakes.py` | (script, not a module) | N/A | Utility for Cursor self-audits. |
| **Memory Substrate Service** | N/A | `memory/substrate/service.py` (or class in) | `memorysubstrateservice.py` | 908 LOC, 19 async: full ingestion/retrieval/storage pipeline | Central memory substrate orchestrator. Do NOT break. |
| **Memory Substrate Repository** | N/A | `memory/substrate/repository.py` (or class in) | `memorysubstraterepository.py` | 976 LOC, 25 async: checkpoints, facts, events, housekeeping | DB access layer. Do NOT break. |
| **Memory Governance Patterns** | N/A | `memory/governance_patterns.py` | `memorygovernancepatterns.py` | 152 LOC, 3 classes; `igoraudit-memorymemorygovernancepatterns.py` mirror | Decision type, governance pattern recall. Protected. |

---

## PART III: PHASE 0 TODO LIST

### TODO-1: Scan All Docs for Stale Refs (Immediate)

**File:** `gap-analysis-memory.md`  
**Operation:** REPLACE (7 occurrences)  
**Match Pattern:**  
```
api/routes/memory.py
```

**Replacement:** Depends on actual file layout:
- **If** `api/memory/router.py` exists → replace with `api/memory/router.py`
- **Else if** module is truly `apimemoryrouter.py` → replace with `apimemoryrouter.py` (import path context)
- **Validate:** Check `file_metrics.txt` under "apimemoryrouter.py"; confirm it's 689 LOC with async functions matching those in the doc.

**Expected Behavior:**  
Lines 482, 705, 806, 990, 1083, 1216, 1363, 1375, 1386, 1403 (from original plan) all now point to canonical router.

**Owner:** Human (Cursor will execute)

---

### TODO-2: Scan Docs, Scripts, ADRs for Cursor Path Stales

**Files:**  
- `docs/*.md`
- `scripts/audit/*.py`, `scriptsmemory*.py`
- `architecture_decisions.md` (for context, do NOT modify)
- `docs/*/` any subdirs with .md, .txt

**Search Patterns (case-insensitive):**
```
tools/cursor_client
memory/extractor/cursor_action_extractor
core/governance/cursor_memory_kernel
scripts/cursor_check_mistakes
```

**Operation:** REPLACE each with canonical modern path from Table (above).

**Example Match & Fix:**
```
Old: "The Cursor client is in tools/cursor_client.py"
New: "The Cursor client integration is in agents/cursor/ (agentscursorintegrationscursorlanggraph.py and related)"
```

**Verify:** Cross-check against `file_metrics.txt` for real file existence.

---

### TODO-3: Audit Cache Regeneration (With Guardrails)

**File:** `.audit_cache/manifest.json`  
**Operation:** REGENERATE (controlled)

**Pre-Gen Checklist:**
1. [ ] Confirm `scripts/audit/run_all.py` exists and is runnable
2. [ ] List all sub-scripts it calls:
   - `scriptsaudittier1auditcodeintegrity.py` (918 LOC)
   - `scriptsaudittier1auditinfrastructurehealth.py` (617 LOC)
   - `scriptsaudittier1auditcapabilityinventory.py` (531 LOC)
   - `scriptsmemoryauditgraphs.py` (533 LOC)
   - `scriptsmemoryauditgraphsvps.py` (395 LOC)
3. [ ] For each, verify it does NOT hardcode old Cursor paths or `api/routes/memory.py`

**Gen Command:**
```bash
cd /path/to/l9
rm -rf .audit_cache
python3 scripts/audit/run_all.py
```

**Post-Gen Validation (NEW):**
```bash
# Check that regenerated manifest contains NO stale paths
grep -E "tools/cursor|memory/extractor/cursor|core/governance/cursor|api/routes/memory" .audit_cache/manifest.json && echo "FAIL: Found stale paths" || echo "PASS: No stale paths"

# Confirm all paths in manifest exist as real files (sample check)
python3 scripts/audit/validate_manifest_paths.py  # (You'll need to create this tiny script)
```

---

### TODO-4: Async Function Map Cross-Check

**File:** (N/A; reference only)  
**Purpose:** Validate that routers emit expected endpoints

**Check Commands:**
```bash
# Extract all async functions from apimemoryrouter.py
grep "^async " file_metrics.txt | grep "apimemoryrouter" || echo "No async functions found; check file_metrics update"

# Confirm at least 17 async functions exist (from file_metrics: 689 LOC, 17 async)
grep "apimemoryrouter.py" async_function_map.txt | wc -l  # should be ~17+
```

**Expected Output:** Lines like:
```
async batchwriterequest, authorization, , orchestrator apimemoryrouter.py
async compactstorage, authorization, , orchestrator apimemoryrouter.py
async searchmemoryroutereq mcpmemorysrcroutesmemoryunified.py
async savememoryroutereq mcpmemorysrcroutesmemoryunified.py
```

**If FAIL:** Indicates async_function_map.txt is stale; run `python3 scripts/audit/extract_async_functions.py` (if it exists) or regenerate manually.

---

### TODO-5: Create Wiring Validator Script (Optional but Recommended)

**File to Create:** `scripts/audit/validate_wiring_alignment.py`

**Purpose:** Automated cross-check of docs, audit cache, and code.

**Pseudo-Code:**
```python
#!/usr/bin/env python3
"""
Validate that all memory/cursor paths in docs, audit cache, and scripts are real.
"""
import json, os, re
from pathlib import Path

CANONICAL_ROUTERS = {
    "apimemoryrouter.py",
    "mcpmemorysrcroutesmemory.py",
    "mcpmemorysrcroutesmemoryunified.py",
    "apiroutescursor.py",
    "agentscursorextractorscursoractionextractor.py",
    "agentscursorintegrationscursorgateway.py",
    # ... add others
}

STALE_PATTERNS = [
    r"api/routes/memory\.py",
    r"tools/cursor_client",
    r"memory/extractor/cursor_action_extractor",
    r"core/governance/cursor_memory_kernel",
    r"scripts/cursor_check_mistakes",
]

def validate_docs():
    """Scan docs for stale refs."""
    broken = []
    for md_file in Path("docs").rglob("*.md"):
        content = md_file.read_text()
        for pattern in STALE_PATTERNS:
            if re.search(pattern, content):
                broken.append(str(md_file))
    return broken

def validate_cache():
    """Check audit cache for stale paths."""
    if not Path(".audit_cache/manifest.json").exists():
        return ["WARN: .audit_cache/manifest.json missing"]
    with open(".audit_cache/manifest.json") as f:
        manifest = json.load(f)
    broken = []
    for entry in manifest.get("files", []):
        for pattern in STALE_PATTERNS:
            if re.search(pattern, entry):
                broken.append(entry)
    return broken

def main():
    print("=== Wiring Alignment Validator ===")
    doc_issues = validate_docs()
    cache_issues = validate_cache()
    
    print(f"\nDocs with stale refs: {len(doc_issues)}")
    for issue in doc_issues:
        print(f"  - {issue}")
    
    print(f"\nCache entries with stale refs: {len(cache_issues)}")
    for issue in cache_issues:
        print(f"  - {issue}")
    
    if doc_issues or cache_issues:
        print("\nSTATUS: FAIL")
        exit(1)
    else:
        print("\nSTATUS: PASS - All paths aligned")
        exit(0)

if __name__ == "__main__":
    main()
```

**Execute After Fixes:**
```bash
python3 scripts/audit/validate_wiring_alignment.py
```

---

## PART IV: TELEMETRY & OBSERVABILITY SANITY CHECK

**Post-Fix Health Check (Run After Execution):**

1. **Memory Substrate Metrics Still Wire:**
   ```bash
   # Confirm that prometheus/observability still scrapes memory metrics from substrate
   grep -r "l9memorywritestotal\|l9memorysearchestotal\|l9memorysubstratehealth" coreobservability*.py
   # Should see references to memorysubstrateservice or memorysubstraterepository
   ```

2. **Tool Audit Log Still Maps:**
   ```bash
   # Confirm that tool invocation logs still reference memorysubstrateservice
   grep -r "toolinvocation" coreobservability*.py | grep -i memory
   # Should confirm no "zombie" stats.
   ```

3. **Async Function Map Includes All Routers:**
   ```bash
   # Spot-check 3 key routers appear in async_function_map.txt with correct counts
   for router in apimemoryrouter mcpmemorysrcroutesmemory apiroutescursor; do
     count=$(grep "^async.*$router\.py" async_function_map.txt | wc -l)
     echo "$router: $count async functions"
   done
   # apimemoryrouter: ~17+
   # mcpmemorysrcroutesmemory: ~14+
   # apiroutescursor: ~3+
   ```

---

## PART V: FINAL VALIDATION CHECKLIST

**Before Marking "Complete":**

- [ ] `gap-analysis-memory.md` has zero refs to `api/routes/memory.py`
- [ ] All docs/scripts reference new Cursor paths (`agents/cursor/`, NOT `tools/`, `memory/extractor/`, `core/governance/`)
- [ ] `.audit_cache/manifest.json` regenerated and contains NO stale paths
- [ ] `scripts/audit/validate_wiring_alignment.py` passes (exit code 0)
- [ ] Memory metrics/observability still wires cleanly (spot-check 3 metrics)
- [ ] No L9 invariants broken:
  - [ ] `coregov*.py` untouched
  - [ ] Packet protocol unchanged
  - [ ] Memory substrate models unchanged
  - [ ] Kernel infrastructure unchanged
- [ ] `architecture_decisions.md` **NOT modified** (it documents *why* moves happened; leave it as-is)

---

## SCOPE & BOUNDARIES

### DO:
✅ Fix stale path references in docs, audit cache, scripts  
✅ Validate async function map matches real routers  
✅ Create lightweight wiring validator  
✅ Spot-check observability/metrics still integrate  

### DO NOT:
❌ Modify `coregovernance*.py`, packet protocol, or memory substrate models  
❌ Touch `architecture_decisions.md` (it's the *why*; leave it)  
❌ Change import paths or module structure (only reference fixes)  
❌ Alter `.audit_cache` generation logic (just regenerate, don't hack manually)  

---

## ESTIMATED EFFORT

| Step | Time | Owner |
|---|---|---|
| TODO-1: Replace refs in gap-analysis-memory.md | 5 min | Cursor (guided search/replace) |
| TODO-2: Scan & replace Cursor path refs | 10 min | Cursor (batch grep/replace) |
| TODO-3: Audit cache regeneration | 5 min | Manual: `rm -rf && python3` |
| TODO-4: Async function map spot-check | 5 min | Manual: grep verification |
| TODO-5: Create validator script (optional) | 15 min | Cursor (template provided) |
| **Total** | ~40 min | Mixed |

---

## SIGN-OFF

**Phase 0 Plan Status:** ✅ **LOCKED FOR EXECUTION**

This plan:
- ✅ Reframes the audit as a repo-wide wiring invariant, not just doc cleanup
- ✅ Provides a structured doc–code alignment table as ground truth
- ✅ Protects all L9 invariants (governance, protocol, substrate)
- ✅ Includes automated validation (manifest check, validator script)
- ✅ Binds observability/metrics sanity checks
- ✅ Is small, reviewable, and executable step-by-step

**Next:** Present this to C for review and final approval, then execute Phases 1–6 (actual code edits).
