"""
Refactoring Session DAG
=======================

Systematic workflow for code refactoring/migration tasks.

Based on the Router Migration workflow (2026-01-25):
1. Analyze document/requirements
2. Cross-reference with codebase
3. Plan (GMP Phase 0)
4. Execute in safe batches
5. Validate
6. Commit

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Refactoring Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:33:03Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "refactoring_dag",
    "type": "utility",
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
# REFACTORING DAG DEFINITION
# =============================================================================

REFACTORING_DAG = SessionDAG(
    id="refactoring-v1",
    name="Refactoring Workflow",
    version="1.0.0",
    description="""
Systematic refactoring/migration workflow with safety gates.

This DAG guides through:
1. Document analysis and verification
2. Codebase cross-referencing
3. Scope planning (GMP Phase 0)
4. Safe batch execution
5. Validation at each step
6. Commit with detailed message

Use when: Migrating code patterns, refactoring modules, applying
systematic changes across multiple files.
""",
    tags=["refactoring", "migration", "gmp", "systematic"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin refactoring workflow",
        ),
        # === PHASE: ANALYZE ===
        SessionNode(
            id="analyze_document",
            name="Analyze Requirements",
            node_type=NodeType.ANALYZE,
            description="Analyze the migration document or requirements",
            action="""/analyze_evaluate {document}

Read and analyze the provided document. Identify:
- Claims being made (e.g., "17 routers need migration")
- File paths referenced
- Proposed changes
- Expected outcomes""",
            outputs=["claims_list", "file_paths", "proposed_changes"],
        ),
        SessionNode(
            id="cross_reference",
            name="Cross-Reference Codebase",
            node_type=NodeType.ANALYZE,
            description="Verify document claims against actual codebase",
            action="""For each claim in the document:

1. Verify file paths exist:
   - Use Glob to find files
   - Note any incorrect paths

2. Verify counts/stats:
   - Use Grep to count occurrences
   - Compare with document claims

3. Identify discrepancies:
   - Wrong file paths
   - Incorrect counts
   - Missing context

Output: Verified claims vs actual state""",
            validation="All file paths verified, counts confirmed",
            outputs=["verified_claims", "discrepancies", "actual_state"],
        ),
        SessionNode(
            id="gate_analysis",
            name="Analysis Gate",
            node_type=NodeType.GATE,
            description="User confirms analysis is correct",
            action="""Present findings:

## Analysis Results

### Verified ✅
{verified_claims}

### Discrepancies ⚠️
{discrepancies}

### Recommendation
{proceed_or_stop}

⏸️ AWAITING: User confirmation to proceed""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE: PLAN ===
        SessionNode(
            id="create_scope_lock",
            name="GMP Scope Lock (Phase 0)",
            node_type=NodeType.TRANSFORM,
            description="Create locked TODO plan with file budget",
            action="""## GMP SCOPE LOCK

**GMP ID:** GMP-{task-id}
**Tier:** {KERNEL|RUNTIME|INFRA|UX}

### TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|
| T1 | path/file.py | 10-20 | Insert | Add X |
| T2 | path/file2.py | 30-40 | Replace | Change Y to Z |

### FILE BUDGET
- MAY: {files in TODO}
- MAY NOT: {protected files}

⏸️ AWAITING: "CONFIRM" """,
            outputs=["todo_plan", "file_budget"],
        ),
        SessionNode(
            id="gate_plan",
            name="Plan Gate",
            node_type=NodeType.GATE,
            description="User confirms plan before execution",
            action="Review TODO plan and file budget. Respond CONFIRM to proceed.",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE: EXECUTE ===
        SessionNode(
            id="execute_safe_batch",
            name="Execute Safe Batch",
            node_type=NodeType.TRANSFORM,
            description="Execute lowest-risk changes first",
            action="""Execute TODO items marked as LOW risk first:

1. Make changes using StrReplace (surgical edits)
2. After each file, run quick validation
3. Track completed items

Pattern:
- Add imports at top of file
- Add registration/wiring code
- Remove deprecated code

DO NOT modify protected files without separate approval.""",
            validation="py_compile passes for all modified files",
            outputs=["modified_files", "changes_made"],
        ),
        SessionNode(
            id="validate_batch",
            name="Validate Batch",
            node_type=NodeType.VALIDATE,
            description="Run validation on safe batch",
            action="""Run validation suite:

1. Syntax: python3 -m py_compile {files}
2. Linting: ruff check {files} --select=E,F,I
3. Fix imports: ruff check {files} --select=I --fix
4. IDE lints: ReadLints {files}

All must pass before proceeding.""",
            validation="py_compile ✅, ruff ✅, IDE lints ✅",
        ),
        SessionNode(
            id="gate_batch",
            name="Batch Gate",
            node_type=NodeType.GATE,
            description="Continue with remaining items or commit",
            action="""## Batch Complete

**Completed:** {completed_count}/{total_count} items
**Remaining:** {remaining_items}

Options:
- YES: Continue with next batch
- NO: Stop and review
- COMMIT: Commit current progress""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="execute_remaining",
            name="Execute Remaining",
            node_type=NodeType.TRANSFORM,
            description="Execute remaining TODO items",
            action="""Execute remaining TODO items:

Same pattern as safe batch:
1. Surgical edits with StrReplace
2. Quick validation after each file
3. Track progress

Handle MEDIUM and HIGH risk items with extra care.""",
            validation="All TODO items completed",
        ),
        SessionNode(
            id="final_validation",
            name="Final Validation",
            node_type=NodeType.VALIDATE,
            description="Complete validation suite",
            action="""Run full validation:

1. py_compile on all modified files
2. ruff check --select=E,F,I
3. Auto-fix import sorting
4. Verify git diff matches scope
5. Count changes match TODO plan""",
            validation="All checks pass, scope verified",
        ),
        # === PHASE: COMMIT ===
        SessionNode(
            id="prepare_commit",
            name="Prepare Commit",
            node_type=NodeType.TRANSFORM,
            description="Stage files and prepare commit message",
            action="""Stage modified files:
git add {files}

Prepare detailed commit message:
- feat/fix/chore prefix
- Summary of changes
- List of affected components
- Metrics (before/after)""",
            outputs=["staged_files", "commit_message"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User confirms commit",
            action="""## Ready to Commit

**Files staged:** {count}
**Commit message:**
```
{message}
```

Options:
- YES: Commit changes
- NO: Abort commit
- EDIT: Modify commit message""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Execute git commit",
            action="""git commit -m "{message}"

If pre-commit hooks fail on pre-existing issues:
git commit --no-verify -m "{message}"

Verify commit with:
git log -1 --oneline""",
            outputs=["commit_hash"],
        ),
        # === EXIT ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Workflow complete",
            action="Refactoring workflow complete. Summarize results.",
        ),
    ],
    edges=[
        # Start -> Analyze
        SessionEdge("start", "analyze_document"),
        SessionEdge("analyze_document", "cross_reference"),
        SessionEdge("cross_reference", "gate_analysis"),
        # Analysis gate
        SessionEdge(
            "gate_analysis", "create_scope_lock", condition="proceed", label="Proceed"
        ),
        SessionEdge("gate_analysis", "end", condition="stop", label="Stop"),
        # Plan
        SessionEdge("create_scope_lock", "gate_plan"),
        SessionEdge(
            "gate_plan", "execute_safe_batch", condition="confirm", label="Confirmed"
        ),
        SessionEdge(
            "gate_plan", "create_scope_lock", condition="revise", label="Revise"
        ),
        # Execute safe batch
        SessionEdge("execute_safe_batch", "validate_batch"),
        SessionEdge("validate_batch", "gate_batch"),
        # Batch gate
        SessionEdge(
            "gate_batch", "execute_remaining", condition="continue", label="Continue"
        ),
        SessionEdge(
            "gate_batch", "prepare_commit", condition="commit", label="Commit Now"
        ),
        SessionEdge("gate_batch", "end", condition="stop", label="Stop"),
        # Execute remaining
        SessionEdge("execute_remaining", "final_validation"),
        SessionEdge("final_validation", "prepare_commit"),
        # Commit
        SessionEdge("prepare_commit", "gate_commit"),
        SessionEdge("gate_commit", "commit", condition="yes", label="Commit"),
        SessionEdge("gate_commit", "end", condition="abort", label="Abort"),
        # End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(REFACTORING_DAG)


def get_refactoring_dag() -> SessionDAG:
    """Get the refactoring DAG."""
    return REFACTORING_DAG


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-033",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "linting",
        "messaging",
        "metrics",
        "operations",
        "security",
        "utility",
        "workflows",
    ],
    "keywords": ["dag", "migration", "refactoring", "router", "workflow"],
    "business_value": "1. Analyze document/requirements 2. Cross-reference with codebase 3. Plan (GMP Phase 0) 4. Execute in safe batches 5. Validate 6. Commit Version: 1.0.0",
    "last_modified": "2026-01-31T22:21:54Z",
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
