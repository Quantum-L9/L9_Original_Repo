"""
Component Audit DAG — Systematic Package Wiring Verification
=============================================================

Audits a component (Python package) for export consistency, file wiring,
and API instantiation. Identifies components with missing public APIs.

Phases:
1. DISCOVER — List components to audit
2. SELECT — Pick target component
3. LEVEL_A — Package export audit (__all__ vs imports)
4. FIX — Resolve export gaps
5. LEVEL_B — File-level wiring (confirm-wiring per file)
6. LEVEL_C — API instantiation check (if API exists or should exist)
7. RECORD — Save audit report

Key insight: Level C runs when a component has (or should have) a public API.
This surfaces components with MISSING APIs — not just broken ones.

Version: 1.0.0
Based on: reports/COMPONENT_WIRING_AUDIT_GUIDE.md
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Component Audit Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-14T00:00:00Z",
    "updated_at": "2026-02-14T00:00:00Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "component_audit_dag",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# COMPONENT AUDIT DAG DEFINITION
# =============================================================================

COMPONENT_AUDIT_DAG = SessionDAG(
    id="component-audit-v1",
    name="Component Wiring Audit",
    version="1.0.0",
    description="""
Systematic audit of a Python package for export consistency, file wiring,
and API instantiation.

THREE LEVELS:
- Level A: Package export consistency (__all__ vs imports in __init__.py)
- Level B: File-level wiring (imports resolve, consumers exist, tests exist)
- Level C: API instantiation (public symbols are used; missing APIs flagged)

KEY INSIGHT:
Level C is NOT optional — it runs whenever a component HAS or SHOULD HAVE
a public API. This catches:
- Components with __all__ but unused symbols (dead API)
- Components WITHOUT __all__ that SHOULD have one (missing API)
- Components that intentionally skip __all__ (documented, no action needed)

TOOLS:
- Level A: tools/validation/audit_package_exports.py
- Level B: /confirm-wiring (workflows/dags/confirm_wiring_dag.py)
- Level C: rg for public symbol consumers

REFERENCE: reports/COMPONENT_WIRING_AUDIT_GUIDE.md
""",
    tags=["audit", "wiring", "exports", "api", "component", "verify"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start Component Audit",
            node_type=NodeType.START,
            description="Entry point for /audit-component workflow",
            action="""Begin component audit workflow.

If user specified a package name, use it. Otherwise proceed to discovery.

Extract from user input:
- {package} = top-level package name (e.g. memory, core, runtime, api)
- If not specified, proceed to discover_components.""",
        ),
        # === PHASE 1: DISCOVER ===
        SessionNode(
            id="discover_components",
            name="Phase 1: Discover Components",
            node_type=NodeType.ANALYZE,
            description="List all top-level packages that could be audited",
            action="""List all top-level Python packages in the repo.

```bash
find . -maxdepth 1 -name __init__.py -exec dirname {} \\; | sort
```

For each, classify:

| Package | Has __init__.py? | Has __all__? | Tier | Priority |
|---------|-----------------|-------------|------|----------|

Tier classification (from 86-module-tier-mapping.mdc):
- KERNEL_TIER: core (kernels, executor, memory substrate core)
- RUNTIME_TIER: runtime, memory, agents
- INFRA_TIER: config, scripts
- UX_TIER: docs, tools

Priority order for audit:
1. KERNEL_TIER + RUNTIME_TIER first (highest impact)
2. Packages with __all__ (have a declared API surface)
3. Packages WITHOUT __all__ that have >5 submodules (likely SHOULD have one)

Record:
- component_list: all packages found
- priority_order: ordered list for audit
- packages_with_all: those that define __all__
- packages_should_have_all: those with >5 submodules but no __all__""",
            outputs=[
                "component_list",
                "priority_order",
                "packages_with_all",
                "packages_should_have_all",
            ],
        ),
        # === PHASE 2: SELECT ===
        SessionNode(
            id="select_component",
            name="Phase 2: Select Component",
            node_type=NodeType.ANALYZE,
            description="Select which component to audit",
            action="""Select the target component for this audit run.

If user specified a package → use it.
If not → pick the highest-priority unaudited package from Phase 1.

Check if a previous audit report exists:
```bash
ls reports/{package}_export_audit.md 2>/dev/null
```

Record:
- target_package: the package to audit
- has_prior_audit: True/False
- package_path: full path to package directory""",
            outputs=["target_package", "has_prior_audit", "package_path"],
        ),
        # === PHASE 3: LEVEL A — EXPORT AUDIT ===
        SessionNode(
            id="level_a_export_audit",
            name="Phase 3: Level A — Export Audit",
            node_type=NodeType.VALIDATE,
            description="Check __all__ vs imports in __init__.py",
            action="""Run the package export audit script.

```bash
python tools/validation/audit_package_exports.py {package}
```

Or with report output:
```bash
python tools/validation/audit_package_exports.py {package} --report reports/{package}_export_audit.md
```

Or via Makefile:
```bash
make audit-exports PACKAGE={package}
```

The script checks:
1. Every name in __all__ is bound by an import in __init__.py (no broken re-exports)
2. Every name imported from {package}.* submodules is in __all__ (no missing re-exports)

Record:
- level_a_status: OK or FAIL
- in_all_not_imported: list of broken re-exports
- imported_not_in_all: list of missing re-exports
- all_count: number of names in __all__
- has_all: whether __all__ exists at all""",
            validation="level_a_status == 'OK'",
            outputs=[
                "level_a_status",
                "in_all_not_imported",
                "imported_not_in_all",
                "all_count",
                "has_all",
            ],
        ),
        # === GATE: LEVEL A CLEAN? ===
        SessionNode(
            id="gate_level_a",
            name="Level A Clean?",
            node_type=NodeType.GATE,
            description="Check if Level A passed with no gaps",
            action="""If level_a_status is OK → proceed to Level B.
If level_a_status is FAIL → route to fix_exports.""",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('level_a_status') == 'OK'",
        ),
        # === FIX EXPORTS ===
        SessionNode(
            id="fix_exports",
            name="Fix Export Gaps",
            node_type=NodeType.TRANSFORM,
            description="Add missing names to __all__ or fix broken re-exports",
            action="""Fix the gaps found in Level A.

For each name in `in_all_not_imported` (broken re-export):
- Check if the name is actually imported (regex bug?) by grepping __init__.py
- If truly not imported: either add the import or remove from __all__

For each name in `imported_not_in_all` (missing re-export):
- Add the name to __all__ in alphabetical position
- Classes go in the uppercase section; functions/get_*/init_* go in the lowercase section

Pattern for adding to __all__:
```python
# Find the right alphabetical spot and insert
# e.g. "DeduplicationEngine" goes between "DecayResult" and "EncodingResult"
```

After fixing, re-run Level A to confirm:
```bash
python tools/validation/audit_package_exports.py {package} --quiet
```

Record:
- fixes_applied: list of changes made
- level_a_recheck: OK or FAIL""",
            outputs=["fixes_applied", "level_a_recheck"],
        ),
        # === PHASE 4: LEVEL B — FILE WIRING ===
        SessionNode(
            id="level_b_file_wiring",
            name="Phase 4: Level B — File Wiring",
            node_type=NodeType.VALIDATE,
            description="Check each file in the component is properly wired",
            action="""For each .py file in the component (excluding __init__.py, __pycache__):

```bash
find {package}/ -maxdepth 1 -name "*.py" -not -name "__init__.py" | sort
```

For each file, run a lightweight wiring check:

1. **Has consumers?**
```bash
rg "from {package}.{module}|import {package}.{module}" --type py -l | grep -v __init__ | wc -l
```

2. **Has tests?**
```bash
ls tests/{package}/test_{module}.py 2>/dev/null
rg "test.*{module}" tests/ --type py -l 2>/dev/null
```

3. **Is it re-exported from __init__.py?**
   Check if any of its public names appear in __all__.

For CRITICAL files (KERNEL_TIER, RUNTIME_TIER), also run:
```bash
make try-run FILE={package}/{module}.py MODE=--import-only
```

Classify each file:
- ✅ WIRED: has consumers + re-exported (or intentionally direct-import)
- ⚠️ PARTIAL: has consumers but not re-exported, or re-exported but no consumers
- ❌ ORPHAN: no consumers, not an entrypoint, not re-exported
- 📋 ENTRYPOINT: CLI script or __main__ (no consumers expected)

Record:
- files_checked: total count
- wired_files: list of ✅
- partial_files: list of ⚠️
- orphan_files: list of ❌
- entrypoint_files: list of 📋""",
            outputs=[
                "files_checked",
                "wired_files",
                "partial_files",
                "orphan_files",
                "entrypoint_files",
            ],
        ),
        # === GATE: HAS/SHOULD-HAVE API? ===
        SessionNode(
            id="gate_has_api",
            name="Has or Should Have Public API?",
            node_type=NodeType.GATE,
            description="Determine if this component has or should have a public API",
            action="""Classify the component's API status:

**HAS_API** — Component defines __all__ with >0 entries.
  → Proceed to Level C (check instantiation).

**SHOULD_HAVE_API** — Component has NO __all__ but:
  - Has >5 .py submodules, OR
  - Has classes/functions imported by >3 external consumers, OR
  - Is KERNEL_TIER or RUNTIME_TIER
  → Flag as MISSING API, then proceed to Level C anyway (check what WOULD be the API).

**NO_API_NEEDED** — Component intentionally has no public API:
  - Is a scripts/ or tools/ package (CLI entrypoints only)
  - Has <3 submodules and is UX_TIER or INFRA_TIER
  - Has explicit "import on-demand" documentation in __init__.py
  → Skip Level C, proceed to record.

Record:
- api_status: HAS_API | SHOULD_HAVE_API | NO_API_NEEDED
- api_reason: why this classification""",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('api_status') in ('HAS_API', 'SHOULD_HAVE_API')",
            outputs=["api_status", "api_reason"],
        ),
        # === PHASE 5: LEVEL C — API INSTANTIATION ===
        SessionNode(
            id="level_c_api_instantiation",
            name="Phase 5: Level C — API Instantiation Check",
            node_type=NodeType.VALIDATE,
            description="Verify public API symbols are used; flag unused or missing API",
            action="""Check that public API symbols are actually used (instantiated).

**If HAS_API:**

For each name in __all__ (or top ~30 most important):
```bash
rg "{name}" --type py -l | grep -v "{package}/" | grep -v "tests/" | wc -l
```

Classify each symbol:
- ✅ USED: >=1 consumer outside the package (excluding tests)
- 🧪 TEST_ONLY: consumers only in tests/ (may be fine for internal utilities)
- ❌ UNUSED: zero consumers anywhere (dead API — candidate for removal)

**If SHOULD_HAVE_API:**

Scan the package for its most-imported symbols:
```bash
rg "from {package}\\." --type py | grep -v "{package}/" | sort | uniq -c | sort -rn | head -20
```

These are the symbols that SHOULD be in __all__ — they're the de-facto public API.
List them as "recommended __all__ entries".

**For BOTH:**

Check for common API patterns that are missing:
- get_* / create_* factory functions (should be in __all__ if they exist)
- Main service classes (e.g. FooService, FooEngine — should be in __all__)
- Configuration classes (e.g. FooConfig — should be in __all__)

Record:
- used_symbols: list of ✅
- test_only_symbols: list of 🧪
- unused_symbols: list of ❌
- recommended_all_entries: list (only if SHOULD_HAVE_API)
- missing_api_patterns: list of get_*/create_*/Service/Config not in __all__""",
            outputs=[
                "used_symbols",
                "test_only_symbols",
                "unused_symbols",
                "recommended_all_entries",
                "missing_api_patterns",
            ],
        ),
        # === PHASE 6: RECORD RESULTS ===
        SessionNode(
            id="record_results",
            name="Phase 6: Record Results",
            node_type=NodeType.TRANSFORM,
            description="Save audit report and update index",
            action="""Generate and save the audit report.

**Report path:** `reports/{package}_export_audit.md`

**Report structure:**

```markdown
# Package Export Audit: {package}

**Date:** YYYY-MM-DD
**API Status:** HAS_API | SHOULD_HAVE_API | NO_API_NEEDED

## Level A: Export Consistency
- __all__ count: {all_count}
- Gaps found: {gap_count}
- Status: ✅ PASS / ❌ FAIL (fixed)

## Level B: File Wiring
- Files checked: {files_checked}
- ✅ Wired: {wired_count}
- ⚠️ Partial: {partial_count}
- ❌ Orphan: {orphan_count}

| File | Status | Consumers | Tests | Re-exported |
|------|--------|-----------|-------|-------------|
| ... | ✅/⚠️/❌ | N | Y/N | Y/N |

## Level C: API Instantiation
- ✅ Used: {used_count}
- 🧪 Test-only: {test_only_count}
- ❌ Unused: {unused_count}

### Missing API Patterns
- {list of get_*/Service/Config not in __all__}

### Recommended Actions
- {specific fixes}
```

**Update index (if exists):**
```bash
# Append to reports/COMPONENT_AUDIT_INDEX.md
echo "| {package} | {date} | {status} | reports/{package}_export_audit.md |" >> reports/COMPONENT_AUDIT_INDEX.md
```

Record:
- report_path: path to saved report
- overall_status: CLEAN / NEEDS_WORK / MISSING_API""",
            outputs=["report_path", "overall_status"],
        ),
        # === END ===
        SessionNode(
            id="end",
            name="Audit Complete",
            node_type=NodeType.END,
            description="Component audit complete",
            action="""Component audit complete.

Summary:
- Package: {target_package}
- Level A: {level_a_status}
- Level B: {files_checked} files, {orphan_count} orphans
- Level C: {api_status} — {used_count} used, {unused_count} unused
- Report: {report_path}

### /ynp routing:
- All clean → **YES**: Component fully wired
- Export gaps fixed → **YES**: Fixed during audit
- Orphan files found → **PROCEED**: Review orphans for removal
- Missing API → **PROCEED**: Create __all__ with recommended entries
- Unused API symbols → **PROCEED**: Remove or document dead API""",
        ),
    ],
    edges=[
        # Linear: start → discover → select → level_a
        SessionEdge(from_node="start", to_node="discover_components"),
        SessionEdge(from_node="discover_components", to_node="select_component"),
        SessionEdge(from_node="select_component", to_node="level_a_export_audit"),
        SessionEdge(from_node="level_a_export_audit", to_node="gate_level_a"),
        # Gate: Level A clean?
        SessionEdge(
            from_node="gate_level_a",
            to_node="level_b_file_wiring",
            condition="passed",
            label="Level A clean",
        ),
        SessionEdge(
            from_node="gate_level_a",
            to_node="fix_exports",
            condition="failed",
            label="Gaps found",
        ),
        # Fix loop back to Level A
        SessionEdge(from_node="fix_exports", to_node="level_a_export_audit"),
        # Level B → API gate
        SessionEdge(from_node="level_b_file_wiring", to_node="gate_has_api"),
        # Gate: Has/should-have API?
        SessionEdge(
            from_node="gate_has_api",
            to_node="level_c_api_instantiation",
            condition="has_or_should",
            label="Has or should have API",
        ),
        SessionEdge(
            from_node="gate_has_api",
            to_node="record_results",
            condition="no_api_needed",
            label="No API needed",
        ),
        # Level C → record
        SessionEdge(from_node="level_c_api_instantiation", to_node="record_results"),
        # Record → end
        SessionEdge(from_node="record_results", to_node="end"),
    ],
)


# =============================================================================
# REGISTRATION
# =============================================================================


def register():
    """Register the component audit DAG."""
    register_session_dag(COMPONENT_AUDIT_DAG)


# Auto-register on import
register()
# ============================================================================
__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
# ============================================================================
