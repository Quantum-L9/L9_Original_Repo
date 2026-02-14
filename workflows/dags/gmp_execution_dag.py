"""
GMP Execution DAG — Enforced Step Ordering
==========================================

This DAG enforces the /gmp workflow with MANDATORY steps that cannot be skipped.

The core problem this solves:
- Text-based rules (.mdc) are SUGGESTIONS — agent can skip steps
- This DAG is ENFORCED — steps have dependencies, agent cannot proceed without completing them

Key enforcement points:
1. 🧠 MEMORY READ is a REQUIRED node before any implementation
2. 🧠 MEMORY WRITE is a REQUIRED node before finalization
3. User confirmation gates at Phase 0 and Phase 6
4. Validation must pass before proceeding

Version: 1.0.0
Based on: DAG-Harvest-1.md transcript analysis
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Gmp Execution Dag",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-02-14T12:00:00Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "gmp_execution_dag",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
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
# GMP EXECUTION DAG DEFINITION
# =============================================================================

GMP_EXECUTION_DAG = SessionDAG(
    id="gmp-execution-v1",
    name="GMP Execution Workflow (Enforced)",
    version="2.0.0",
    description="""
Governance Managed Process execution with ENFORCED step ordering.

MANDATORY STEPS (cannot be skipped):
1. Memory Read — Search for context, preferences, lessons BEFORE implementation
2. Scope Lock — Define TODO plan with explicit file budget
3. User Confirm — Wait for explicit CONFIRM before executing
4. Baseline — Verify files exist and assumptions hold
5. Implement — Execute TODO plan (surgical edits only)
6. Validate — py_compile, imports, lint, tests must pass
7. Memory Write — Save learnings BEFORE finalize
8. Finalize — Generate report via script, validate, update workflow_state

CRITICAL RULES:
- Memory operations are NOT OPTIONAL
- Validation failures STOP execution
- Scope drift is NOT ALLOWED
- All changes must map 1:1 to TODO plan
- Use StrReplace for edits, not sed/awk
- Use Read tool for file inspection, not cat/head/tail
""",
    tags=["gmp", "enforced", "memory", "governance", "no-skip"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start GMP",
            node_type=NodeType.START,
            description="Entry point for GMP execution",
            action="""Begin GMP workflow.

1. Extract task description from user input
2. Classify tier: KERNEL | RUNTIME | INFRA | UX
3. Read governance reference: agents/cursor/governance-reference.md
4. Read workflow_state.md for current phase and context

Tier classification:
- KERNEL_TIER: kernels, executor, websocket orchestrator, memory substrate core
- RUNTIME_TIER: task queue, Redis client, tool registry, agents
- INFRA_TIER: docker-compose, deploy scripts, k8s, helm
- UX_TIER: frontend, docs, glue scripts""",
        ),
        # === PHASE 0: MEMORY READ (MANDATORY) ===
        SessionNode(
            id="memory_read",
            name="Memory Read (MANDATORY)",
            node_type=NodeType.TRANSFORM,
            description="Search L9 memory for context BEFORE any implementation",
            action="""MANDATORY: Search memory for relevant context.

Extract 2-3 keyword phrases from the task, then run:

```bash
# 1. Search for related work (use actual task keywords)
python3 agents/cursor/cursor_memory_client.py search "keyword phrase from task"

# 2. Search for lessons and errors in the target area
python3 agents/cursor/cursor_memory_client.py search "lessons errors <component name>"

# 3. Search for preferences relevant to this domain
python3 agents/cursor/cursor_memory_client.py search "preferences <domain>"
```

Present results as:

## MEMORY CONTEXT INJECTED

### Related Work Found
- [list prior GMPs or related tasks from search results]

### Lessons to Apply
- [lessons/errors to avoid from search results]

### Preferences
- [any user preferences found]

If memory server is unavailable, log the failure explicitly:
"Memory unavailable — proceeding without context injection."

THIS STEP CANNOT BE SKIPPED.""",
            validation="Memory search executed (results or explicit failure logged)",
            outputs=["memory_context", "related_work", "lessons"],
        ),
        # === PHASE 0: SCOPE LOCK ===
        SessionNode(
            id="scope_lock",
            name="Scope Lock (Phase 0)",
            node_type=NodeType.ANALYZE,
            description="Define TODO plan with explicit file budget",
            action="""Create locked scope definition.

Read each file in scope BEFORE defining line ranges.

## GMP SCOPE LOCK

Tier: KERNEL | RUNTIME | INFRA | UX

### TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|
| T1 | path/to/file.py | 10-50 | Insert/Replace/Delete | What changes |
| T2 | path/to/other.py | 1-5 | Insert | Add import |

### FILE BUDGET
- MAY modify: [only files listed in TODO]
- MAY NOT modify: [everything else — explicit list of nearby files NOT to touch]

### MEMORY CONTEXT APPLIED
- Applied lessons: [from memory_read step]
- Applied patterns: [from memory_read step]
- Related prior work: [from memory_read step]

### PROTECTED FILE CHECK
If any TODO file is protected, note approval requirement:
- core/agents/executor.py → KERNEL approval required
- runtime/websocket_orchestrator.py → KERNEL approval required
- memory/substrate_service.py → KERNEL approval required
- docker-compose.yml → INFRA approval required
- runtime/kernel_loader.py → KERNEL approval required

Present scope and WAIT for user confirmation.""",
            outputs=["todo_plan", "file_budget", "tier"],
        ),
        SessionNode(
            id="gate_scope",
            name="Scope Confirmation Gate",
            node_type=NodeType.GATE,
            description="User must explicitly confirm scope before execution",
            action="""Present scope summary and wait for user decision.

## SCOPE LOCK COMPLETE

### TODO Plan: {count} items across {count} files
[summary table]

### File Budget
- MAY modify: [list]
- MAY NOT modify: [list]

### Memory Context: Applied

AWAITING user response:
- **CONFIRM** — Proceed with implementation
- **MODIFY** — Request scope changes (return to scope_lock)
- **ABORT** — Cancel GMP""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 1: BASELINE ===
        SessionNode(
            id="baseline",
            name="Baseline Verification (Phase 1)",
            node_type=NodeType.VALIDATE,
            description="Verify files exist and assumptions hold",
            action="""Verify baseline conditions for every file in TODO plan.

For each file in TODO:

1. **File exists:** Use Read tool to open the file
2. **Line ranges valid:** Verify the lines referenced in TODO actually contain
   the code you expect to modify (read the specific line range)
3. **Content matches:** Confirm the code at those lines is what you plan to change

For Python files, also verify:
```bash
python3 -m py_compile path/to/file.py
```

If ANY baseline check fails:
- STOP immediately
- Report which file/lines failed and why
- Return to scope_lock to revise the TODO plan

Do NOT proceed to implementation with invalid baselines.""",
            validation="All files exist, line ranges valid, content matches expectations",
        ),
        # === PHASE 2-3: IMPLEMENT ===
        SessionNode(
            id="implement",
            name="Implementation (Phase 2-3)",
            node_type=NodeType.TRANSFORM,
            description="Execute TODO plan — no scope drift allowed",
            action="""Execute each TODO item in order using SURGICAL EDITS.

For each T# in TODO plan:
1. Read the target file (Read tool)
2. Apply the change using StrReplace tool (search_replace)
3. Verify the edit was applied correctly (Read tool again)

### TOOL USAGE
- StrReplace: For modifying existing code (Insert/Replace/Delete)
- Write: ONLY for creating new files that don't exist yet
- Read: To verify changes after each edit

### FORBIDDEN
- Reformatting code not in TODO
- Renaming variables not in TODO
- "While I'm here" cleanup of adjacent code
- ANY change not explicitly in TODO plan
- Using sed/awk for edits (use StrReplace)
- Rewriting entire files (use surgical StrReplace)

### SCOPE DRIFT CHECK
After all TODO items are complete, verify:
- Every change maps 1:1 to a TODO item
- No extra files were modified
- No extra lines were changed

If additional changes are needed beyond TODO:
- STOP
- Propose scope expansion to user
- Wait for approval before proceeding""",
            outputs=["changes_made", "files_modified"],
        ),
        # === PHASE 4: VALIDATE ===
        SessionNode(
            id="validate",
            name="Validation (Phase 4)",
            node_type=NodeType.VALIDATE,
            description="All validation must pass before proceeding",
            action="""Run validation suite on ALL modified files.

### Step 1: Syntax check
```bash
python3 -m py_compile path/to/each/modified/file.py
```

### Step 2: Import check
```bash
python3 -c "from module.path import *"
```
(for each modified module)

### Step 3: Lint check
```bash
ruff check path/to/modified/files --select=E,F
```

### Step 4: Run validation script (if files_modified > 0)
```bash
python3 scripts/gmp-validate-stage.py --files path/to/file1.py path/to/file2.py --json
```

### Step 5: Run relevant tests (if they exist)
```bash
python3 -m pytest tests/path/to/relevant_tests.py -v
```

### FAILURE HANDLING
- ANY validation failure → STOP
- Do NOT patch forward or add # noqa
- Fix the actual issue, then re-run validation
- Do NOT proceed to memory write if validation fails

Present results as a clear pass/fail table.""",
            validation="py_compile pass, imports pass, lint pass, tests pass",
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Gate",
            node_type=NodeType.GATE,
            description="Validation must pass before memory write",
            action="""Present validation results and wait for user decision.

## VALIDATION RESULTS

| Check | Status | Detail |
|-------|--------|--------|
| py_compile | pass/FAIL | ... |
| imports | pass/FAIL | ... |
| lint | pass/FAIL | ... |
| gmp-validate-stage | pass/FAIL | ... |
| tests | pass/FAIL/skipped | ... |

**Overall:** PASS or FAIL

If FAIL → Do NOT proceed. Fix issues and re-validate.

AWAITING user response:
- **CONTINUE** — Proceed to memory write and finalize
- **FIX** — Return to implement to fix issues
- **ABORT** — Cancel GMP""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 5: MEMORY WRITE (MANDATORY) ===
        SessionNode(
            id="memory_write",
            name="Memory Write (MANDATORY)",
            node_type=NodeType.TRANSFORM,
            description="Save learnings to memory BEFORE finalization",
            action="""MANDATORY: Write learnings to L9 memory.

### Step 1: Write GMP summary (ALWAYS)
```bash
python3 agents/cursor/cursor_memory_client.py write \
  "GMP: <brief summary of what was done>. Files: <list>. Tier: <tier>" \
  --kind lesson
```

### Step 2: Write insights discovered (if any new patterns found)
```bash
python3 agents/cursor/cursor_memory_client.py write \
  "INSIGHT: <what was learned>. Context: <domain>" \
  --kind insight
```

### Step 3: Write error fixes (if errors were encountered and fixed)
```bash
python3 agents/cursor/cursor_memory_client.py write \
  "ERROR FIX: <error description> -> <fix applied>. Component: <name>" \
  --kind error
```

Valid --kind values: note, preference, lesson, insight, error

Present results:

## MEMORY WRITTEN
- GMP summary: saved / failed
- Insights: {count} saved (if any)
- Error fixes: {count} saved (if any)

If memory write fails, log the failure explicitly but continue.
THIS STEP CANNOT BE SKIPPED.""",
            validation="Memory write executed (success or explicit failure logged)",
            outputs=["memory_written", "lessons_saved"],
        ),
        # === PHASE 6: FINALIZE ===
        SessionNode(
            id="finalize",
            name="Finalize (Phase 6)",
            node_type=NodeType.TRANSFORM,
            description="Generate report, validate it, update workflow_state",
            action="""Three-step finalization using canonical scripts.

### Step 1: Generate GMP report
```bash
python3 scripts/generate_gmp_report.py \
  --task "<task description>" \
  --tier <TIER>_TIER \
  --todo "T1|path/file.py|10-50|Replace|Description" \
  --todo "T2|path/other.py|1-5|Insert|Description" \
  --validation "py_compile|pass" \
  --validation "imports|pass" \
  --validation "lint|pass" \
  --summary "<one-line summary of changes>" \
  --update-workflow
```

The script auto-detects the next GMP ID and writes to:
`reports/GMP Reports/GMP-Report-{ID}-{Description}.md`

### Step 2: Validate the generated report
```bash
python3 scripts/validate_gmp_report.py "reports/GMP Reports/GMP-Report-{ID}-{Description}.md"
```

### Step 3: Confirm workflow_state.md was updated
Read workflow_state.md and verify the new GMP appears in Recent Changes.

DO NOT create reports manually — ALWAYS use the script.

Present results:
- Report: `reports/GMP Reports/GMP-Report-{ID}-{Description}.md`
- Validation: PASSED / FAILED
- workflow_state.md: Updated / Failed""",
            outputs=["report_path", "report_generated"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User decides whether to commit",
            action="""Present commit summary and wait for user decision.

## Ready to Commit?

**Files changed:** {list of modified files}
**Report:** {report path}

AWAITING user response (/ynp):
- **YES** — Commit all changes with GMP message
- **NO** — Exit without committing (changes remain unstaged)
- **PROCEED** — Different action (user specifies)""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves",
            action="""Stage and commit changes.

```bash
git add <all modified files> <report file>
```

Commit message format (use HEREDOC):
```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <summary>

GMP-{ID}: <task description>

Files modified:
- path/to/file1.py
- path/to/file2.py

Report: reports/GMP Reports/GMP-Report-{ID}-{Description}.md
EOF
)"
```

Then verify:
```bash
git log -1 --oneline
git status
```

Do NOT push unless user explicitly asks.""",
            outputs=["commit_hash"],
        ),
        # === EXIT ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="GMP workflow complete",
            action="GMP execution complete. Report generated, memory updated.",
        ),
    ],
    edges=[
        # Start -> Memory Read (MANDATORY FIRST)
        SessionEdge("start", "memory_read"),
        # Memory Read -> Scope Lock
        SessionEdge("memory_read", "scope_lock"),
        # Scope Lock -> Gate
        SessionEdge("scope_lock", "gate_scope"),
        # Gate decisions
        SessionEdge("gate_scope", "baseline", condition="confirm", label="Confirmed"),
        SessionEdge(
            "gate_scope", "scope_lock", condition="modify", label="Modify Scope"
        ),
        SessionEdge("gate_scope", "end", condition="abort", label="Abort"),
        # Baseline -> Implement
        SessionEdge("baseline", "implement"),
        # Implement -> Validate
        SessionEdge("implement", "validate"),
        # Validate -> Gate
        SessionEdge("validate", "gate_validation"),
        # Validation gate decisions
        SessionEdge(
            "gate_validation", "memory_write", condition="continue", label="Validated"
        ),
        SessionEdge(
            "gate_validation", "implement", condition="fix", label="Fix Issues"
        ),
        SessionEdge("gate_validation", "end", condition="abort", label="Abort"),
        # Memory Write (MANDATORY) -> Finalize
        SessionEdge("memory_write", "finalize"),
        # Finalize -> Commit Gate
        SessionEdge("finalize", "gate_commit"),
        # Commit gate decisions
        SessionEdge("gate_commit", "commit", condition="yes", label="Commit"),
        SessionEdge("gate_commit", "end", condition="no", label="Skip Commit"),
        # Commit -> End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(GMP_EXECUTION_DAG)


def get_gmp_execution_dag() -> SessionDAG:
    """Get the GMP execution DAG."""
    return GMP_EXECUTION_DAG


# Generate Mermaid diagram for documentation
if __name__ == "__main__":
    print(GMP_EXECUTION_DAG.to_markdown())  # noqa: ADR-0019
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-027",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cli",
        "linting",
        "messaging",
        "operations",
        "realtime",
        "security",
        "testing",
        "workflows",
    ],
    "keywords": [
        "agent",
        "analysis",
        "based",
        "before",
        "cannot",
        "dag",
        "enforced",
        "execution",
    ],
    "business_value": "This DAG enforces the /gmp workflow with MANDATORY steps that cannot be skipped.",
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
