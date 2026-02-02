"""
Wire DAG — Component Wiring Workflow (Enforced)
================================================

This DAG enforces the /wire workflow for structural wiring repair.

IMPORTANT: /wire is a STRUCTURAL REPAIR command.
It fixes references and exports.
It does NOT prove runtime correctness.
Runtime proof REQUIRES /verify-component.

Phases:
1. DISCOVERY — Find ALL references (exhaustive)
2. ANALYSIS — Classify component type (structural + context)
3. PLAN — Create surgical plan (minimal + explicit)
4. EXECUTE — Apply changes (surgical only)
5. VALIDATE — py_compile, imports, tests
6. RE-DISCOVERY — Confirm all refs resolved
7. CONFIRM-WIRING — Integration audit
8. REPORT — Generate GMP report

Version: 1.0.0
Based on: .cursor-commands/commands/wire.md v10.2.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Wire Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "wire_dag",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
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
# PROTECTED FILES — Require /gmp escalation
# =============================================================================
PROTECTED_FILES = [
    "core/agents/executor.py",
    "runtime/websocket_orchestrator.py",
    "memory/substrate_service.py",
    "Dockerfile",
    "Dockerfile.*",
    "docker-compose.yml",
    "docker-compose.*.yml",
]

# =============================================================================
# SEMANTIC REFUSALS — Hard stops
# =============================================================================
SEMANTIC_REFUSALS = [
    "introduce import-time side effects",
    "cause DB / network access at import time",
    "wire sync code into async-only paths",
    "violate bootstrap vs runtime boundaries",
    "mutate global state at import",
    "rely on implicit side effects",
]

# =============================================================================
# WIRE DAG DEFINITION
# =============================================================================

WIRE_DAG = SessionDAG(
    id="wire-v1",
    name="Component Wiring Workflow (Enforced)",
    version="1.0.0",
    description="""
Structural wiring repair with semantic guards. Fix refs, exports, and registrations.

IMPORTANT:
- /wire is a STRUCTURAL REPAIR command
- It fixes references and exports
- It does NOT prove runtime correctness
- Runtime proof REQUIRES /verify-component

PHASES:
1. DISCOVERY — Find ALL references (exhaustive, no sampling)
2. ANALYSIS — Classify component type and required structure
3. PLAN — Create numbered surgical plan (one action = one edit)
4. EXECUTE — Apply changes (StrReplace/Insert only)
5. VALIDATE — py_compile, import tests, pytest
6. RE-DISCOVERY — Confirm all refs resolved
7. CONFIRM-WIRING — Integration audit
8. REPORT — Auto-generate GMP report

HARD STOPS:
- Protected files require /gmp escalation
- Semantic refusals trigger immediate STOP
- Any behavior change requires /gmp escalation

SUCCESS CRITERIA:
- All references resolve
- No broken imports remain
- No protected files touched
- No semantic refusals triggered
""",
    tags=["wire", "structural", "refs", "exports", "surgical", "no-behavior-change"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start Wire",
            node_type=NodeType.START,
            description="Entry point for /wire workflow",
            action="Begin /wire workflow. Extract component path or name from user input.",
        ),
        # === PHASE 1: DISCOVERY (EXHAUSTIVE) ===
        SessionNode(
            id="discovery",
            name="Discovery (Exhaustive)",
            node_type=NodeType.ANALYZE,
            description="Find ALL references to the target component — no sampling",
            action="""Find ALL references to the target component.

Commands:
```bash
# Find all occurrences of the component name
rg "{component}" --type py -n

# Find all imports
rg "from .*{component}|import .*{component}" --type py -n
```

Collect EVERY occurrence. No sampling. No assumptions.

Output table:
| File | Line | Ref Type | Status |
|------|------|----------|--------|
| service.py | 12 | import | ❌ |
| loader.py | 41 | usage | ❌ |
| __init__.py | 5 | export | ❌ |

⚠️ If no references found → STOP → report "unused component"
⚠️ Must find ALL references before proceeding""",
            validation="All references collected (exhaustive search completed)",
            outputs=["references_table", "reference_count", "broken_count"],
        ),
        SessionNode(
            id="gate_discovery",
            name="Discovery Gate",
            node_type=NodeType.GATE,
            description="User confirms reference discovery before analysis",
            action="""## DISCOVERY COMPLETE

### References Found
| File | Line | Ref Type | Status |
|------|------|----------|--------|
{references_table}

**Total references:** {reference_count}
**Broken references:** {broken_count}

If no references found:
→ STOP → Component is unused

⏸️ **AWAITING:** "CONTINUE" to analyze component type""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 2: ANALYSIS (STRUCTURAL + CONTEXT) ===
        SessionNode(
            id="analysis",
            name="Analysis (Structural + Context)",
            node_type=NodeType.ANALYZE,
            description="Classify component type and determine required structure",
            action="""Classify the component:

| Type | Required Structure |
|------|--------------------|
| Module | file exists, __init__.py exports |
| Class | imported, instantiated, reachable |
| Function | imported, callable, no side effects |
| Service | registered, lifecycle-safe |
| Route | exported, mounted |
| Tool | registered, discoverable |
| Config | loader exists, path valid |

Check for SEMANTIC REFUSALS (hard stops):
- Would introduce import-time side effects?
- Would cause DB/network access at import time?
- Would wire sync code into async-only paths?
- Would violate bootstrap vs runtime boundaries?
- Would mutate global state at import?
- Would rely on implicit side effects?

Check for PROTECTED FILES:
- core/agents/executor.py
- runtime/websocket_orchestrator.py
- memory/substrate_service.py
- Any Dockerfile
- docker-compose.yml

⚠️ If classification ambiguous → STOP → request clarification
⚠️ If semantic refusal triggered → STOP → escalate to /gmp
⚠️ If protected file touched → STOP → escalate to /gmp""",
            validation="Component classified, no semantic refusals, no protected files",
            outputs=[
                "component_type",
                "required_structure",
                "semantic_check",
                "protected_check",
            ],
        ),
        SessionNode(
            id="gate_analysis",
            name="Analysis Gate",
            node_type=NodeType.GATE,
            description="User confirms analysis before planning",
            action="""## ANALYSIS COMPLETE

**Component:** {component}
**Type:** {component_type}
**Required Structure:** {required_structure}

### Semantic Checks
| Check | Status |
|-------|--------|
| No import-time side effects | {status} |
| No DB/network at import | {status} |
| No sync→async violation | {status} |
| Bootstrap/runtime boundaries | {status} |
| No global state mutation | {status} |
| No implicit side effects | {status} |

### Protected File Check
| File | Touched? |
|------|----------|
{protected_check}

If ANY semantic refusal triggered:
→ STOP → Escalate to /gmp with evidence

If ANY protected file touched:
→ STOP → Escalate to /gmp

⏸️ **AWAITING:** "CONTINUE" to create surgical plan
Options: CONTINUE, ESCALATE (to /gmp), ABORT""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 3: PLAN (MINIMAL + EXPLICIT) ===
        SessionNode(
            id="plan",
            name="Plan (Minimal + Explicit)",
            node_type=NodeType.ANALYZE,
            description="Create numbered surgical plan — one action = one edit",
            action="""Create a numbered, surgical plan.

Rules:
- One action = one edit
- No speculative changes
- No batching

Plan table:
| # | Action | File | Change |
|---|--------|------|--------|
| W1 | Fix import path | service.py:12 | `from old import X` → `from new import X` |
| W2 | Add export | module/__init__.py | `from .x import Y` |
| W3 | Register component | registry.py | add Y to registry |

ALLOWED ACTIONS:
- Fix import path
- Add export to __init__.py
- Register component
- Fix reference

FORBIDDEN ACTIONS:
- Change behavior
- Add side effects
- Restructure logic
- Refactor code
- "While I'm here" cleanup

⚠️ If plan requires refactor → STOP → escalate to /gmp""",
            outputs=["plan_table", "action_count", "files_affected"],
        ),
        SessionNode(
            id="gate_plan",
            name="Plan Gate",
            node_type=NodeType.GATE,
            description="User confirms surgical plan before execution",
            action="""## SURGICAL PLAN READY

### Actions
| # | Action | File | Change |
|---|--------|------|--------|
{plan_table}

**Total actions:** {action_count}
**Files affected:** {files_affected}

### Constraints
- StrReplace / Insert only
- Preserve formatting
- Preserve logic
- No rewrites

If execution would:
- Change behavior → STOP → /gmp
- Add side effects → STOP → /gmp
- Restructure logic → STOP → /gmp

⏸️ **AWAITING:** "EXECUTE" to apply changes
Options: EXECUTE, MODIFY, ESCALATE (to /gmp), ABORT""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 4: EXECUTE (SURGICAL ONLY) ===
        SessionNode(
            id="execute",
            name="Execute (Surgical Only)",
            node_type=NodeType.TRANSFORM,
            description="Apply surgical changes — StrReplace/Insert only",
            action="""Execute each action in plan order:

For each W# in plan:
1. Read the target file
2. Apply the change (StrReplace or Insert)
3. Verify the change was applied

Constraints:
- StrReplace / Insert ONLY
- Preserve formatting
- Preserve logic
- No rewrites

For each action, log:
| W# | File | Before | After | Status |
|----|------|--------|-------|--------|
| W1 | service.py | old import | new import | ✅ |

⚠️ If any action would change behavior → STOP
⚠️ If any action fails → STOP → report failure""",
            validation="All actions applied successfully",
            outputs=["changes_made", "files_modified"],
        ),
        # === PHASE 5: VALIDATE (LOCAL STRUCTURE) ===
        SessionNode(
            id="validate",
            name="Validate (Local Structure)",
            node_type=NodeType.VALIDATE,
            description="Verify syntax safety, imports, and tests",
            action="""Run validation suite:

1. **Syntax check:**
```bash
python3 -m py_compile {all_modified_files}
```

2. **Import check:**
```bash
python3 -c "from {package} import {component}"
```

3. **Test run:**
```bash
pytest tests/{package}/ -v
```

Purpose:
- Syntax safety
- Obvious import correctness
- Wiring-level test coverage

⚠️ This does NOT prove runtime safety
⚠️ Any failure → STOP → do not proceed to re-discovery""",
            validation="py_compile ✅, imports ✅, tests ✅",
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Gate",
            node_type=NodeType.GATE,
            description="Validation must pass before re-discovery",
            action="""## VALIDATION RESULTS

### Syntax Check (py_compile)
{syntax_results}

### Import Check
{import_results}

### Test Results
{test_results}

**Overall Status:** {PASS/FAIL}

If FAIL:
- Do NOT proceed to re-discovery
- Fix issues and re-execute

If PASS:
- ⏸️ **AWAITING:** "CONTINUE" to verify all refs resolved""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 6: RE-DISCOVERY (STRUCTURAL CONFIRMATION) ===
        SessionNode(
            id="rediscovery",
            name="Re-Discovery (Structural Confirmation)",
            node_type=NodeType.VALIDATE,
            description="Repeat discovery to confirm all refs resolved",
            action="""Repeat Phase 1 discovery:

```bash
rg "{component}" --type py -n
rg "from .*{component}|import .*{component}" --type py -n
```

Compare with original table:

| File | Line | Ref Type | Before | After |
|------|------|----------|--------|-------|
| service.py | 12 | import | ❌ | ✅ |
| loader.py | 41 | usage | ❌ | ✅ |

Confirm:
- All previous ❌ refs are now ✅
- No new broken refs introduced
- No duplicate or shadowed imports

⚠️ If ANY unresolved reference remains → FAIL""",
            validation="All references resolved, no new broken refs",
            outputs=["final_references_table", "resolved_count", "remaining_broken"],
        ),
        # === PHASE 7: CONFIRM-WIRING (INTEGRATION AUDIT) ===
        SessionNode(
            id="confirm_wiring",
            name="Confirm Wiring (Integration Audit)",
            node_type=NodeType.VALIDATE,
            description="Run /confirm-wiring integration audit",
            action="""Run integration audit (/confirm-wiring):

### 1. VERIFY IMPORTS
```bash
python3 -c "from {package} import {component}"
```

### 2. VERIFY EXPORTS
Check `__init__.py` exports match usage.

### 3. VERIFY CONSUMERS
```bash
rg "from.*{component}|import.*{component}" --type py -l
```

### 4. VERIFY TESTS
```bash
ls tests/{package}/test_{component}.py
pytest tests/{package}/test_{component}.py -v
```

Output:
## ✅ WIRING CONFIRMED: {component}

| Check | Status |
|-------|--------|
| Imports resolve | ✅ |
| Exports consumed | ✅ |
| Tests exist | ✅ |
| Tests pass | ✅ |

**Consumers:** {list}
**Orphans:** None

⚠️ If wiring incomplete → FAIL → /wire is INCOMPLETE""",
            validation="Imports ✅, Exports ✅, Tests ✅, No orphans",
        ),
        SessionNode(
            id="gate_confirm",
            name="Confirm Wiring Gate",
            node_type=NodeType.GATE,
            description="User confirms wiring is complete before report",
            action="""## WIRING CONFIRMATION RESULTS

### Wiring Checks
| Check | Status |
|-------|--------|
| Imports resolve | {status} |
| Exports consumed | {status} |
| Tests exist | {status} |
| Tests pass | {status} |

### Consumers
{consumers_list}

### Orphans
{orphans_list}

**Overall Status:** {CONFIRMED/INCOMPLETE}

If INCOMPLETE:
- Do NOT proceed
- Review failures and fix

If CONFIRMED:
- ⏸️ **AWAITING:** "REPORT" to generate GMP report""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 8: REPORT ===
        SessionNode(
            id="generate_report",
            name="Generate Report",
            node_type=NodeType.TRANSFORM,
            description="Auto-generate GMP report using the report generator script",
            action="""Generate the GMP report using the CANONICAL REPORT GENERATOR:

```bash
python3 scripts/generate_gmp_report.py \\
  --task "Wire component: {component}" \\
  --tier RUNTIME_TIER \\
  --todo "W1|{file}|{lines}|{action}|{description}" \\
  --validation "py_compile|✅" \\
  --validation "imports|✅" \\
  --validation "tests|✅" \\
  --validation "confirm-wiring|✅" \\
  --summary "Structural wiring repair for {component}" \\
  --update-workflow
```

The script will:
1. Auto-detect the next GMP ID (e.g., GMP-130)
2. Generate canonical report: `reports/GMP-Report-{ID}-Wire-{Component}.md`
3. Update `workflow_state.md` if --update-workflow passed

Output:

## 🔌 WIRE: {component}

| Metric | Value |
|--------|-------|
| References found | N |
| References fixed | N |
| Exports added | N |
| Files modified | N |

### Actions
| # | Action | File | Status |
|---|--------|------|--------|
| W1 | Fix import | service.py | ✅ |

### Validation
| Check | Status |
|-------|--------|
| py_compile | ✅ |
| import test | ✅ |
| tests | ✅ |
| confirm-wiring | ✅ |

📄 Report: `reports/GMP-Report-{ID}-Wire-{Component}.md`""",
            outputs=["report", "report_path"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User decides whether to commit (DO NOT PUSH)",
            action="""## Ready to Commit?

**Changes staged:** {count} files
**GMP Report:** {report_path}

### /ynp

**Y**es: Commit with generated message (DO NOT PUSH)
**N**o: Exit without committing
**P**roceed: Different action (specify)

⚠️ REMINDER: Commit only — DO NOT PUSH""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves (DO NOT PUSH)",
            action="""git add {files}

git commit -m "$(cat <<'EOF'
fix(wire): structural wiring repair for {component}

## Wire Summary
- References found: {reference_count}
- References fixed: {fixed_count}
- Exports added: {export_count}
- Files modified: {file_count}

## Validation
- py_compile: ✅
- imports: ✅
- tests: ✅
- confirm-wiring: ✅

GMP Report: {report_path}
EOF
)"

git log -1 --oneline

⚠️ DO NOT PUSH — Commit only""",
            outputs=["commit_hash"],
        ),
        # === EXIT ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Wire workflow complete",
            action="""/wire workflow complete.

STRUCTURAL SUCCESS declared only if:
- All references resolve
- No broken imports remain
- No protected files touched
- No semantic refusals triggered

Runtime correctness is explicitly OUT OF SCOPE.
To verify runtime correctness → /verify-component {component}""",
        ),
    ],
    edges=[
        # Start -> Discovery
        SessionEdge("start", "discovery"),
        # Discovery -> Gate
        SessionEdge("discovery", "gate_discovery"),
        # Discovery gate decisions
        SessionEdge(
            "gate_discovery", "analysis", condition="continue", label="Continue"
        ),
        SessionEdge(
            "gate_discovery", "end", condition="abort", label="Unused component"
        ),
        # Analysis -> Gate
        SessionEdge("analysis", "gate_analysis"),
        # Analysis gate decisions
        SessionEdge("gate_analysis", "plan", condition="continue", label="Continue"),
        SessionEdge(
            "gate_analysis", "end", condition="escalate", label="Escalate to /gmp"
        ),
        SessionEdge("gate_analysis", "end", condition="abort", label="Abort"),
        # Plan -> Gate
        SessionEdge("plan", "gate_plan"),
        # Plan gate decisions
        SessionEdge("gate_plan", "execute", condition="execute", label="Execute"),
        SessionEdge("gate_plan", "plan", condition="modify", label="Modify plan"),
        SessionEdge("gate_plan", "end", condition="escalate", label="Escalate to /gmp"),
        SessionEdge("gate_plan", "end", condition="abort", label="Abort"),
        # Execute -> Validate
        SessionEdge("execute", "validate"),
        # Validate -> Gate
        SessionEdge("validate", "gate_validation"),
        # Validation gate decisions
        SessionEdge(
            "gate_validation", "rediscovery", condition="continue", label="Validated"
        ),
        SessionEdge("gate_validation", "execute", condition="fix", label="Fix issues"),
        SessionEdge("gate_validation", "end", condition="abort", label="Abort"),
        # Re-discovery -> Confirm Wiring
        SessionEdge("rediscovery", "confirm_wiring"),
        # Confirm Wiring -> Gate
        SessionEdge("confirm_wiring", "gate_confirm"),
        # Confirm gate decisions
        SessionEdge(
            "gate_confirm",
            "generate_report",
            condition="report",
            label="Generate Report",
        ),
        SessionEdge("gate_confirm", "execute", condition="fix", label="Fix issues"),
        SessionEdge("gate_confirm", "end", condition="abort", label="Abort"),
        # Report -> Commit Gate
        SessionEdge("generate_report", "gate_commit"),
        # Commit gate decisions
        SessionEdge("gate_commit", "commit", condition="yes", label="Commit"),
        SessionEdge("gate_commit", "end", condition="no", label="Skip Commit"),
        # Commit -> End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(WIRE_DAG)


def get_wire_dag() -> SessionDAG:
    """Get the wire DAG."""
    return WIRE_DAG


# Generate Mermaid diagram for documentation
if __name__ == "__main__":
    print(WIRE_DAG.to_markdown())  # noqa: ADR-0019
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-032",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "audit-tool",
        "batch-processing",
        "cli",
        "messaging",
        "metrics",
        "operations",
        "realtime",
        "rest-api",
        "security",
        "testing",
    ],
    "keywords": [
        "analysis",
        "audit",
        "commands",
        "component",
        "confirm",
        "dag",
        "discovery",
        "plan",
    ],
    "business_value": "This DAG enforces the /wire workflow for structural wiring repair. IMPORTANT: /wire is a STRUCTURAL REPAIR command. It fixes references and exports. It does NOT prove runtime correctness. Runtime proo",
    "last_modified": "2026-01-31T22:27:11Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
