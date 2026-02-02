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
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
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
    version="1.0.0",
    description="""
Governance Managed Process execution with ENFORCED step ordering.

MANDATORY STEPS (cannot be skipped):
1. 🧠 Memory Read — Search for context, preferences, lessons BEFORE implementation
2. Scope Lock — Define TODO plan with explicit file budget
3. User Confirm — Wait for explicit CONFIRM before executing
4. Baseline — Verify files exist and assumptions hold
5. Implement — Execute TODO plan (harvest or semantic change)
6. Validate — py_compile, tests, lint must pass
7. 🧠 Memory Write — Save learnings, patterns, errors BEFORE finalize
8. Finalize — Generate report, optionally commit

CRITICAL RULES:
- Memory operations are NOT OPTIONAL
- Validation failures STOP execution
- Scope drift is NOT ALLOWED
- All changes must map 1:1 to TODO plan
""",
    tags=["gmp", "enforced", "memory", "governance", "no-skip"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start GMP",
            node_type=NodeType.START,
            description="Entry point for GMP execution",
            action="Begin GMP workflow. Extract task description and tier from user input.",
        ),
        # === PHASE 0: MEMORY READ (MANDATORY) ===
        SessionNode(
            id="memory_read",
            name="🧠 Memory Read (MANDATORY)",
            node_type=NodeType.TRANSFORM,
            description="Search L9 memory for context BEFORE any implementation",
            action="""MANDATORY: Search memory for relevant context.

Execute these commands:

```bash
# 1. Search for related work and patterns
python3 agents/cursor/cursor_memory_client.py search "{task_keywords}"

# 2. Search for lessons and errors to avoid
python3 agents/cursor/cursor_memory_client.py search "lessons errors {component}"

# 3. Search for domain patterns
python3 agents/cursor/cursor_memory_client.py search "{domain} patterns"
```

Output format:

## 🧠 MEMORY CONTEXT INJECTED

### Related Work Found
- [list prior GMPs or related tasks]

### Relevant Patterns
- [patterns from memory that apply]

### Lessons to Apply
- [lessons/errors to avoid]

📍 Proceeding with scope lock...

⚠️ THIS STEP CANNOT BE SKIPPED
If memory is unavailable, note the failure but continue with explicit acknowledgment.""",
            validation="Memory search executed (results or explicit failure logged)",
            outputs=["memory_context", "related_work", "lessons", "patterns"],
        ),
        # === PHASE 0: SCOPE LOCK ===
        SessionNode(
            id="scope_lock",
            name="Scope Lock (Phase 0)",
            node_type=NodeType.ANALYZE,
            description="Define TODO plan with explicit file budget",
            action="""Create locked scope definition:

## GMP SCOPE LOCK

GMP ID: GMP-XXX
Tier: KERNEL | RUNTIME | INFRA | UX

### TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|
| T1 | path/file.py | 10-50 | Insert/Replace/Delete | What changes |

### FILE BUDGET
- MAY: [files in TODO only]
- MAY NOT: [everything else]

### MEMORY CONTEXT APPLIED
- Patterns: {from memory_read}
- Lessons: {from memory_read}
- Related work: {from memory_read}

⏸️ Awaiting explicit CONFIRM""",
            outputs=["todo_plan", "file_budget", "gmp_id", "tier"],
        ),
        SessionNode(
            id="gate_scope",
            name="Scope Confirmation Gate",
            node_type=NodeType.GATE,
            description="User must explicitly confirm scope before execution",
            action="""## SCOPE LOCK COMPLETE

### TODO Plan Summary
{todo_plan_summary}

### File Budget
- MAY modify: {may_files}
- MAY NOT modify: {may_not_files}

### Memory Context Applied
- ✅ Related work checked
- ✅ Patterns applied
- ✅ Lessons incorporated

⏸️ **AWAITING:** Type "CONFIRM" to proceed with implementation

Options:
- CONFIRM: Proceed with implementation
- ABORT: Cancel GMP
- MODIFY: Request scope changes""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 1: BASELINE ===
        SessionNode(
            id="baseline",
            name="Baseline Verification (Phase 1)",
            node_type=NodeType.VALIDATE,
            description="Verify files exist and assumptions hold",
            action="""Verify baseline conditions:

1. Check all files in TODO exist:
   ```bash
   ls -la {files_in_todo}
   ```

2. Verify line ranges are correct:
   ```bash
   wc -l {files_in_todo}
   sed -n '{start},{end}p' {file}
   ```

3. Verify imports resolve:
   ```bash
   python3 -c "from {module} import *"
   ```

4. Check for protected files:
   - runtime/websocket_orchestrator.py → KERNEL approval required
   - core/agents/executor.py → KERNEL approval required
   - memory/substrate_service.py → KERNEL approval required
   - docker-compose.yml → INFRA approval required

Any failure → STOP → Return to Phase 0""",
            validation="All files exist, line ranges valid, imports resolve",
        ),
        # === PHASE 2-3: IMPLEMENT ===
        SessionNode(
            id="implement",
            name="Implementation (Phase 2-3)",
            node_type=NodeType.TRANSFORM,
            description="Execute TODO plan — no scope drift allowed",
            action="""Execute each TODO item in order:

For each T# in TODO plan:
1. Read the target file
2. Apply the change (Insert/Replace/Delete)
3. Verify the change was applied correctly

### ALLOWED ACTIONS
- Insert: Add new code at specified location
- Replace: Change existing code at specified lines
- Delete: Remove code at specified lines
- Copy: Copy harvested file to target (for /use-harvest)

### FORBIDDEN ACTIONS
- Reformatting code not in TODO
- Renaming variables not in TODO
- "While I'm here" cleanup
- ANY change not explicitly in TODO plan

### CRITICAL RULES
- Use sed/cp for harvested code — NO manual rewriting
- All edits must map 1:1 to TODO items
- If additional changes needed → STOP → request scope expansion""",
            outputs=["changes_made", "files_modified"],
        ),
        # === PHASE 4: VALIDATE ===
        SessionNode(
            id="validate",
            name="Validation (Phase 4)",
            node_type=NodeType.VALIDATE,
            description="All validation must pass before proceeding",
            action="""Run validation suite:

1. **Syntax check:**
   ```bash
   python3 -m py_compile {all_modified_files}
   ```

2. **Import check:**
   ```bash
   python3 -c "from {module} import *"
   ```

3. **Lint check (if applicable):**
   ```bash
   ruff check {modified_files} --select=E,F
   ```

4. **Test run (if tests exist):**
   ```bash
   pytest tests/{relevant_tests} -v
   ```

### FAILURE HANDLING
- ANY validation failure → STOP
- Do NOT patch forward
- Return failure with evidence
- Do NOT proceed to memory write if validation fails""",
            validation="py_compile ✅, imports ✅, lint ✅, tests ✅",
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Gate",
            node_type=NodeType.GATE,
            description="Validation must pass before memory write",
            action="""## VALIDATION RESULTS

### Syntax Check
{syntax_results}

### Import Check
{import_results}

### Lint Check
{lint_results}

### Test Results
{test_results}

**Overall Status:** {PASS/FAIL}

If FAIL:
- Do NOT proceed to memory write
- Fix issues and re-validate

If PASS:
- ⏸️ **AWAITING:** "CONTINUE" to write to memory and finalize""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE 5.5: MEMORY WRITE (MANDATORY) ===
        SessionNode(
            id="memory_write",
            name="🧠 Memory Write (MANDATORY)",
            node_type=NodeType.TRANSFORM,
            description="Save learnings to memory BEFORE finalization",
            action="""MANDATORY: Write learnings to L9 memory.

Execute these commands:

```bash
# 1. Write GMP summary
python3 agents/cursor/cursor_memory_client.py write \\
  "GMP-XXX: {summary_of_changes}. Tags: gmp, {component}" --kind lesson

# 2. Write patterns discovered (if any)
python3 agents/cursor/cursor_memory_client.py write \\
  "{pattern_description}. Tags: {domain}, pattern" --kind pattern

# 3. Write errors/fixes encountered (if any)
python3 agents/cursor/cursor_memory_client.py write \\
  "{error_and_fix}. Tags: error, {component}" --kind lesson
```

Output format:

## 🧠 MEMORY WRITTEN

- ✅ GMP summary saved: "{summary}"
- ✅ Patterns saved: {count} (if any)
- ✅ Lessons saved: {count} (if any)

📍 Proceeding to finalize...

⚠️ THIS STEP CANNOT BE SKIPPED
If memory write fails, log the failure but continue with explicit acknowledgment.""",
            validation="Memory write executed (success or explicit failure logged)",
            outputs=["memory_written", "lessons_saved", "patterns_saved"],
        ),
        # === PHASE 6: FINALIZE ===
        SessionNode(
            id="finalize",
            name="Finalize (Phase 6)",
            node_type=NodeType.TRANSFORM,
            description="Generate GMP report using the report generator script",
            action="""Generate the GMP report using the CANONICAL REPORT GENERATOR:

```bash
# MANDATORY: Use the report generator script
python3 scripts/generate_gmp_report.py \\
  --task "{task_description}" \\
  --tier {TIER}_TIER \\
  --todo "T1|{file}|{lines}|{action}|{description}" \\
  --validation "py_compile|✅" \\
  --validation "imports|✅" \\
  --summary "{brief_summary}" \\
  --update-workflow
```

The script will:
1. Auto-detect the next GMP ID (e.g., GMP-129)
2. Generate canonical report: `reports/GMP Reports/GMP-Report-{ID}-{Description}.md`
3. Follow `gmp-report-contract.yaml` format
4. Update `workflow_state.md` if --update-workflow passed
5. Run automatic verification

⚠️ DO NOT create inline reports — USE THE SCRIPT!

After running, output:

## GMP REPORT GENERATED

- 📄 Report: `reports/GMP Reports/GMP-Report-{ID}-{Description}.md`
- ✅ Verification: PASSED
- ✅ workflow_state.md: Updated

### /ynp
- YES: Commit all changes
- NO: Exit without commit
- PROCEED: Different action""",
            outputs=["report", "report_path"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User decides whether to commit",
            action="""## Ready to Commit?

**Changes staged:** {count} files

### /ynp

**Y**es: Commit with generated message
**N**o: Exit without committing
**P**roceed: Different action (specify)""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves",
            action="""git add {files}

git commit -m "$(cat <<'EOF'
{commit_message}

GMP-XXX: {summary}

Files modified:
{files_list}

Memory operations:
- Read: ✅ Context injected
- Write: ✅ Lessons saved
EOF
)"

git log -1 --oneline""",
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
