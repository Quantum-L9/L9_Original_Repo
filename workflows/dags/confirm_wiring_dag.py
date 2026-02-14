"""
Confirm-Wiring DAG — Integration Audit Workflow (Enforced)
==========================================================

Verifies a component is fully wired into L9 — no orphan refs, no broken imports,
no runtime failures.

Phases:
1. RESOLVE — Verify all imports resolve
2. TRY-RUN — Actually run/import the file (syntax + import + execution)
3. EXPORTS — Verify __init__.py exports match usage
4. CONSUMERS — Find all consumers via rg
5. TESTS — Verify tests exist and pass
6. REPORT — Present wiring status table

Version: 1.0.0
Based on: .cursor-commands/commands/confirm-wiring.md v2.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Confirm Wiring Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-14T00:00:00Z",
    "updated_at": "2026-02-14T00:00:00Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "confirm_wiring_dag",
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
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)

# =============================================================================
# CONFIRM-WIRING DAG DEFINITION
# =============================================================================

CONFIRM_WIRING_DAG = SessionDAG(
    id="confirm-wiring-v1",
    name="Integration Audit (Enforced)",
    version="1.0.0",
    description="""
Verify a component is fully wired into L9 — no orphan refs, no broken imports,
no runtime failures.

PHASES:
1. RESOLVE — python3 -c "from {package} import {component}"
2. TRY-RUN — make try-run FILE={file} (syntax + import + execution)
3. EXPORTS — Check __init__.py exports match usage
4. CONSUMERS — rg for all consumers
5. TESTS — Verify tests exist and pass
6. REPORT — Present wiring status table

SUCCESS CRITERIA:
- All imports resolve
- File runs without errors (try-run PASS)
- Exports consumed by at least one file
- Tests exist and pass
- No orphan references

FAILURE ROUTING:
- Import fails → /wire
- Try-run fails → fix file, re-run
- No consumers → flag as potentially dead code
- Tests fail → fix tests
""",
    tags=["wiring", "integration", "audit", "verify", "try-run"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start Confirm-Wiring",
            node_type=NodeType.START,
            description="Entry point for /confirm-wiring workflow",
            action="""Begin /confirm-wiring workflow.

Extract the target from user input:
- File path: `core/tools/registry_adapter.py`
- Module path: `core.tools.registry_adapter`
- Component name: `RegistryAdapter` (search for file)

Determine:
- {file} = full file path (e.g., core/tools/registry_adapter.py)
- {package} = Python package path (e.g., core.tools.registry_adapter)
- {component} = class/function name if specified""",
        ),
        # === PHASE 1: RESOLVE IMPORTS ===
        SessionNode(
            id="resolve_imports",
            name="Phase 1: Resolve Imports",
            node_type=NodeType.VALIDATE,
            description="Verify the file's imports all resolve",
            action="""Verify the target file can be imported:

```bash
python3 -c "from {package} import *"
```

If a specific component was named:
```bash
python3 -c "from {package} import {component}"
```

Record result: PASS or FAIL with error message.

If FAIL:
- Capture the ImportError / ModuleNotFoundError
- Note which import is broken
- This will route to /wire at the end""",
            validation="Import statement executes without error",
            outputs=["import_status", "import_error"],
        ),
        # === PHASE 2: TRY-RUN ===
        SessionNode(
            id="try_run",
            name="Phase 2: Try-Run",
            node_type=NodeType.VALIDATE,
            description="Actually run the file to catch runtime errors beyond imports",
            action="""Run the file through try-run validator:

```bash
make try-run FILE={file}
```

This runs THREE levels:
1. Syntax check (ast.parse)
2. Import check (python3 -c "import {module}")
3. Full execution (python3 {file})

Record result: PASS, FAIL (with traceback), or TIMEOUT.

If the file has no __main__ block, use import-only mode:
```bash
make try-run FILE={file} MODE=--import-only
```

Key: This catches what static analysis misses:
- Missing f-prefixes on format strings
- Broken structlog kwargs
- NameError from undefined variables
- Runtime TypeError from wrong signatures""",
            validation="try-run exits with code 0",
            outputs=["try_run_status", "try_run_output", "try_run_level"],
        ),
        # === PHASE 3: VERIFY EXPORTS ===
        SessionNode(
            id="verify_exports",
            name="Phase 3: Verify Exports",
            node_type=NodeType.ANALYZE,
            description="Check __init__.py exports match what the file provides",
            action="""Check if the component is exported from its package __init__.py:

```bash
# Find the package __init__.py
cat {package_dir}/__init__.py
```

Check:
1. Is the component in __all__?
2. Is there an import statement for it?
3. If no __init__.py exists, is the file imported directly?

Record:
- exported: True/False
- export_location: path to __init__.py or "direct import"
- in_all: True/False (if __all__ exists)""",
            validation="Component is exported or directly importable",
            outputs=["export_status", "export_location", "in_all"],
        ),
        # === PHASE 4: FIND CONSUMERS ===
        SessionNode(
            id="find_consumers",
            name="Phase 4: Find Consumers",
            node_type=NodeType.ANALYZE,
            description="Find all files that import/use this component",
            action="""Find all consumers of the component:

```bash
rg "from.*{component}|import.*{component}" --type py -l
```

Also check for string references (e.g., in configs, registries):
```bash
rg "{component}" --type yaml --type toml -l
```

Record:
- consumer_count: number of files that import it
- consumers: list of file paths
- orphan: True if consumer_count == 0 (excluding tests and __init__.py)

⚠️ If orphan AND not a CLI script/entrypoint → flag as potentially dead code""",
            validation="At least one consumer found (or file is a CLI entrypoint)",
            outputs=["consumer_count", "consumers", "is_orphan"],
        ),
        # === PHASE 5: VERIFY TESTS ===
        SessionNode(
            id="verify_tests",
            name="Phase 5: Verify Tests",
            node_type=NodeType.VALIDATE,
            description="Check that tests exist and pass for this component",
            action="""Find and run tests for the component:

```bash
# Find test files
ls tests/{package_path}/test_{component_file}.py 2>/dev/null
rg "test.*{component}" tests/ --type py -l
```

If test file found:
```bash
python3 -m pytest {test_file} -v --tb=short
```

Record:
- test_exists: True/False
- test_file: path (or "not found")
- test_result: PASS/FAIL/SKIP
- test_count: number of test functions""",
            validation="Tests exist and pass",
            outputs=["test_exists", "test_file", "test_result", "test_count"],
        ),
        # === PHASE 6: REPORT ===
        SessionNode(
            id="report",
            name="Phase 6: Wiring Report",
            node_type=NodeType.END,
            description="Present final wiring status",
            action="""Generate the wiring report.

If ALL checks pass:

```markdown
## ✅ WIRING CONFIRMED: {component}

| Check | Status | Detail |
|-------|--------|--------|
| Imports resolve | ✅ | {import_status} |
| Try-run | ✅ | {try_run_level}: {try_run_status} |
| Exports | ✅ | {export_location} |
| Consumers | ✅ | {consumer_count} files |
| Tests | ✅ | {test_count} tests in {test_file} |

**Consumers:** {consumers}
**Orphans:** None
```

If ANY check fails:

```markdown
## ❌ WIRING INCOMPLETE: {component}

| Check | Status | Detail |
|-------|--------|--------|
| Imports resolve | {status} | {detail} |
| Try-run | {status} | {detail} |
| Exports | {status} | {detail} |
| Consumers | {status} | {detail} |
| Tests | {status} | {detail} |

### Recommended Actions

| Issue | Fix |
|-------|-----|
| Import fails | → Run `/wire {component}` |
| Try-run fails | → Fix errors shown in traceback, re-run |
| Not exported | → Add to `__init__.py` |
| No consumers | → Flag as dead code or add usage |
| No tests | → Create `tests/{path}/test_{name}.py` |
```

### /ynp routing:
- All pass → **YES**: Component fully wired
- Import/try-run fail → **PROCEED**: `/wire {component}`
- Tests missing → **PROCEED**: Create tests
- Dead code → **NO**: Consider removal""",
        ),
    ],
    edges=[
        SessionEdge(from_node="start", to_node="resolve_imports"),
        SessionEdge(from_node="resolve_imports", to_node="try_run"),
        SessionEdge(from_node="try_run", to_node="verify_exports"),
        SessionEdge(from_node="verify_exports", to_node="find_consumers"),
        SessionEdge(from_node="find_consumers", to_node="verify_tests"),
        SessionEdge(from_node="verify_tests", to_node="report"),
    ],
)

# ============================================================================
__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
# ============================================================================
