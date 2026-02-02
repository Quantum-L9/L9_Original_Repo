"""
Slash Command Update DAG — Update Commands as Minimal Triggers
==============================================================

This DAG enforces the proper pattern for updating slash commands
that trigger DAGs.

CRITICAL INSIGHT (from DAG-Harvest-6):
- Slash commands that trigger DAGs should be ~30 lines
- All detailed instructions live in the DAG's node action fields
- NEVER duplicate instructions between command file and DAG
- A 300-line command file that just triggers a DAG is WASTEFUL

Phases:
1. ANALYZE — Check current command file size and structure
2. IDENTIFY — Find the DAG it triggers (or should trigger)
3. REDUCE — Strip command file to minimal trigger
4. VALIDATE — Verify command still works
5. VERIFY — Confirm no instructions lost (all in DAG)

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slash Command Update Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "slash_command_update_dag",
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
# SIZE THRESHOLDS
# =============================================================================
MAX_TRIGGER_LINES = 40  # Command files triggering DAGs should be ~30-40 lines
VERBOSE_THRESHOLD = 100  # Anything over this is definitely too verbose

# =============================================================================
# SLASH COMMAND UPDATE DAG DEFINITION
# =============================================================================

SLASH_COMMAND_UPDATE_DAG = SessionDAG(
    id="slash-command-update-v1",
    name="Slash Command Update Workflow",
    version="1.0.0",
    description="""
Update slash commands to be MINIMAL TRIGGERS (~30 lines).

PROBLEM PATTERN:
- Command file is 300+ lines
- DAG already contains all the instructions
- Command file duplicates everything → WASTEFUL

SOLUTION PATTERN:
- Command file = ~30 lines (trigger only)
- DAG = all detailed instructions in node actions
- No duplication

MINIMAL COMMAND TEMPLATE:
```markdown
name: command
version: "1.0.0"
description: "Brief description"
auto_chain: ynp
dag: dag-id
dag_file: workflows/dags/dag_file.py

# /command — Title

**DAG-ENFORCED.** Execute the `dag-id` DAG.

## Usage
/{command} [options]

## Execution
The DAG contains all instructions. Follow each node's action field exactly.

## Key Files
- **DAG**: path/to/dag.py
```

KEY FILES:
- Commands: .cursor-commands/commands/*.md
- DAGs: workflows/dags/*.py
- Registry: .cursor/rules/02-slash-commands.mdc
""",
    tags=["meta", "command", "update", "minimal", "trigger", "efficiency"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin slash command update workflow. Identify command to update.",
        ),
        # === PHASE 1: ANALYZE ===
        SessionNode(
            id="analyze_command",
            name="Analyze Command",
            node_type=NodeType.ANALYZE,
            description="Check current command file size and structure",
            action="""Analyze the current command file.

1. **Get file path:**
   ```bash
   ls .cursor-commands/commands/{command}.md
   ```

2. **Count lines:**
   ```bash
   wc -l .cursor-commands/commands/{command}.md
   ```

3. **Check for DAG reference:**
   ```bash
   grep -E "^dag:|^dag_file:" .cursor-commands/commands/{command}.md
   ```

4. **Assess verbosity:**
   - < 40 lines → Already minimal ✅
   - 40-100 lines → Could be reduced
   - > 100 lines → Definitely needs reduction ⚠️

5. **Document in state:**
   ```python
   state["command_path"] = ".cursor-commands/commands/example.md"
   state["line_count"] = 312
   state["has_dag_ref"] = True
   state["dag_id"] = "example-dag-v1"
   ```

Pre-reading: .cursor-commands/commands/{command}.md""",
            outputs=["command_path", "line_count", "has_dag_ref", "dag_id"],
        ),
        # === GATE: NEEDS REDUCTION? ===
        SessionNode(
            id="gate_needs_reduction",
            name="Needs Reduction?",
            node_type=NodeType.GATE,
            description="Check if command file is too verbose",
            action="""Determine if command needs reduction.

REDUCE if ANY of:
- line_count > 40 AND has DAG reference
- line_count > 100 (always too verbose for DAG trigger)
- Contains duplicate instructions from DAG

SKIP if:
- line_count <= 40 (already minimal)
- No DAG reference (not a DAG-trigger command)""",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('line_count', 0) > 40 and state.get('has_dag_ref', False)",
        ),
        # === PHASE 2: IDENTIFY DAG ===
        SessionNode(
            id="identify_dag",
            name="Identify DAG",
            node_type=NodeType.ANALYZE,
            description="Find and verify the DAG this command triggers",
            action="""Identify the DAG that this command triggers.

1. **Extract DAG reference from command:**
   ```bash
   grep -E "^dag:|^dag_file:" .cursor-commands/commands/{command}.md
   ```

2. **Read DAG file:**
   ```bash
   cat workflows/dags/{dag_file}.py | head -100
   ```

3. **Verify DAG contains instructions:**
   Check that DAG nodes have detailed `action` fields.

4. **List node actions:**
   ```python
   from workflows.dags.{dag} import DAG_CONSTANT
   for node in DAG_CONSTANT.nodes:
       print(f"{node.id}: {len(node.action)} chars")  # noqa: ADR-0019
   ```

5. **Document:**
   ```python
   state["dag_path"] = "workflows/dags/example_dag.py"
   state["dag_has_instructions"] = True  # node actions are detailed
   ```

⚠️ If DAG nodes have empty/minimal actions:
   - DON'T reduce command file
   - Instead, MOVE instructions from command to DAG first

Pre-reading: workflows/dags/{dag_file}.py""",
            outputs=["dag_path", "dag_has_instructions"],
        ),
        # === GATE: DAG HAS INSTRUCTIONS? ===
        SessionNode(
            id="gate_dag_ready",
            name="DAG Has Instructions?",
            node_type=NodeType.GATE,
            description="Check if DAG already has detailed instructions",
            action="""Verify DAG nodes have detailed action fields.

PROCEED if:
- Most DAG nodes have >100 chars in action field
- Instructions are executable (commands, steps, etc.)

STOP if:
- DAG nodes have minimal/empty actions
- Need to move instructions TO DAG first

If STOP:
- Use /dag-authoring to flesh out DAG first
- Then return to reduce command file""",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('dag_has_instructions', False)",
        ),
        # === PHASE 3: REDUCE ===
        SessionNode(
            id="reduce_command",
            name="Reduce to Minimal",
            node_type=NodeType.TRANSFORM,
            description="Strip command file to minimal trigger",
            action="""Reduce command file to minimal trigger (~30 lines).

KEEP:
- YAML frontmatter (name, version, description, auto_chain, dag, dag_file)
- Title heading
- Brief "DAG-ENFORCED" statement
- Usage section (2-3 examples)
- "The DAG contains all instructions" statement
- Key Files section

REMOVE:
- Detailed phase-by-phase instructions
- Multi-line code blocks with implementation
- Duplicate content from DAG nodes
- Verbose explanations

TEMPLATE:
```markdown
name: {command}
version: "1.0.0"
description: "Brief description"
auto_chain: ynp
dag: {dag-id}
dag_file: workflows/dags/{dag_file}.py

# /{command} — {Title}

**DAG-ENFORCED.** Execute the `{dag-id}` DAG.

## Usage

```
/{command}                    # Default
/{command} --option value     # With options
```

## Execution

Load and execute the DAG:

```python
from workflows.dags import {DAG_CONSTANT}
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `{dag_path}`
- **Other key files**
```

Write reduced version to command file.

Pre-reading: .cursor-commands/commands/{command}.md (current)
Output: .cursor-commands/commands/{command}.md (reduced)""",
            outputs=["reduced_line_count"],
        ),
        # === PHASE 4: VALIDATE ===
        SessionNode(
            id="validate_command",
            name="Validate Command",
            node_type=NodeType.VALIDATE,
            description="Verify command still works after reduction",
            action="""Validate the reduced command file.

1. **Check line count:**
   ```bash
   wc -l .cursor-commands/commands/{command}.md
   ```
   Should be 30-40 lines.

2. **Verify YAML frontmatter:**
   ```bash
   head -10 .cursor-commands/commands/{command}.md
   ```
   Must have: name, version, description, dag, dag_file

3. **Verify DAG reference valid:**
   ```python
   python -c "from workflows.dags.{dag} import DAG_CONSTANT; print(DAG_CONSTANT.id)"
   ```

4. **Check key sections present:**
   - Title heading
   - Usage section
   - Execution section
   - Key Files section

5. **Verify NO lost instructions:**
   Compare removed content against DAG nodes.
   Every removed instruction should exist in a DAG node action.

SUCCESS CRITERIA:
- Line count: 30-40 ✓
- YAML frontmatter complete ✓
- DAG import works ✓
- All instructions preserved in DAG ✓""",
            outputs=["validation_passed", "final_line_count"],
        ),
        # === GATE: VALIDATION PASSED? ===
        SessionNode(
            id="gate_validation",
            name="Validation Passed?",
            node_type=NodeType.GATE,
            description="Check if reduction validated successfully",
            action="If validation passed, proceed to verify. Otherwise fix issues.",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('validation_passed', False)",
        ),
        # === PHASE 5: VERIFY ===
        SessionNode(
            id="verify_completeness",
            name="Verify Completeness",
            node_type=NodeType.VALIDATE,
            description="Confirm no instructions were lost",
            action="""Final verification that no instructions were lost.

1. **List what was in old command:**
   Original had N lines of instructions.

2. **List what's in DAG:**
   ```python
   from workflows.dags.{dag} import DAG_CONSTANT
   for node in DAG_CONSTANT.nodes:
       if node.action and len(node.action) > 50:
           print(f"- {node.name}: {len(node.action)} chars")  # noqa: ADR-0019
   ```

3. **Verify coverage:**
   Every major instruction from old command should map to a DAG node.

4. **Report:**
   | Old Command Section | DAG Node | Status |
   |----|-----|-----|
   | Phase 1 instructions | node_phase1 | ✅ Covered |
   | Phase 2 instructions | node_phase2 | ✅ Covered |

COMPLETENESS CHECK:
- [ ] All phases covered in DAG nodes
- [ ] All commands preserved
- [ ] All file references preserved
- [ ] No orphaned instructions""",
            outputs=["completeness_verified"],
        ),
        # === REPORT ===
        SessionNode(
            id="report",
            name="Generate Report",
            node_type=NodeType.ANALYZE,
            description="Summarize the reduction",
            action="""Generate summary report.

## Slash Command Reduction Report

| Metric | Before | After |
|--------|--------|-------|
| Line count | {old_count} | {new_count} |
| Reduction | - | {percentage}% |

### What Changed
- Removed verbose instructions (now in DAG)
- Kept minimal trigger structure
- Preserved all functionality

### Files Modified
- `.cursor-commands/commands/{command}.md` — reduced

### Verification
- [x] DAG import works
- [x] All instructions preserved in DAG
- [x] Command triggers correctly

### Token Savings
Before: ~{old_tokens} tokens to process
After: ~{new_tokens} tokens to process
Savings: ~{savings}% per invocation""",
            outputs=["report"],
        ),
        # === SKIP PATH ===
        SessionNode(
            id="skip_already_minimal",
            name="Already Minimal",
            node_type=NodeType.ANALYZE,
            description="Command is already minimal, nothing to do",
            action="""Command is already minimal (~30-40 lines).

No reduction needed. Current structure is correct.

If you want to:
- Update instructions → Edit the DAG file, not the command file
- Add new features → Add nodes to DAG
- Change flow → Modify DAG edges""",
            outputs=["skipped"],
        ),
        # === END ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Workflow complete",
            action="Slash command update workflow complete.",
        ),
    ],
    edges=[
        # Main flow
        SessionEdge(from_node="start", to_node="analyze_command"),
        SessionEdge(from_node="analyze_command", to_node="gate_needs_reduction"),
        # Gate: needs reduction?
        SessionEdge(
            from_node="gate_needs_reduction",
            to_node="identify_dag",
            condition="needs_reduction",
            label="Too verbose",
        ),
        SessionEdge(
            from_node="gate_needs_reduction",
            to_node="skip_already_minimal",
            condition="already_minimal",
            label="Already minimal",
        ),
        # Identify DAG flow
        SessionEdge(from_node="identify_dag", to_node="gate_dag_ready"),
        # Gate: DAG ready?
        SessionEdge(
            from_node="gate_dag_ready",
            to_node="reduce_command",
            condition="dag_ready",
            label="DAG has instructions",
        ),
        SessionEdge(
            from_node="gate_dag_ready",
            to_node="end",
            condition="dag_not_ready",
            label="Need to update DAG first",
        ),
        # Reduce and validate
        SessionEdge(from_node="reduce_command", to_node="validate_command"),
        SessionEdge(from_node="validate_command", to_node="gate_validation"),
        # Validation gate
        SessionEdge(
            from_node="gate_validation",
            to_node="verify_completeness",
            condition="passed",
            label="Validation passed",
        ),
        SessionEdge(
            from_node="gate_validation",
            to_node="reduce_command",
            condition="failed",
            label="Fix issues",
        ),
        # Complete flow
        SessionEdge(from_node="verify_completeness", to_node="report"),
        SessionEdge(from_node="report", to_node="end"),
        SessionEdge(from_node="skip_already_minimal", to_node="end"),
    ],
)


# =============================================================================
# REGISTRATION
# =============================================================================


def register():
    """Register the slash command update DAG."""
    register_session_dag(SLASH_COMMAND_UPDATE_DAG)


# Auto-register on import
register()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-029",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "metrics", "operations", "utility", "workflows"],
    "keywords": [
        "command",
        "commands",
        "dag",
        "dags",
        "instructions",
        "minimal",
        "pattern",
        "register",
    ],
    "business_value": "This DAG enforces the proper pattern for updating slash commands that trigger DAGs. Slash commands that trigger DAGs should be ~30 lines All detailed instructions live in the DAG's node action fields ",
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
