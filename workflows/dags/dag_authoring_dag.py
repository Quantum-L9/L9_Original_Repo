"""
DAG Authoring DAG — Create/Update DAGs the PROPER Way
======================================================

This DAG enforces the proper pattern for creating and updating DAGs.

CRITICAL INSIGHT:
- DAGs contain ALL detailed instructions in node `action` fields
- Slash commands are MINIMAL TRIGGERS (~30 lines)
- NEVER duplicate instructions between command file and DAG

Phases:
1. ANALYZE — Understand what workflow needs to be encoded
2. STRUCTURE — Design node graph (start → phases → gates → end)
3. WRITE_NODES — Write each node with detailed action instructions
4. WRITE_EDGES — Define flow between nodes
5. VALIDATE — Import test, registration check
6. CREATE_COMMAND — Create MINIMAL trigger command file

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Dag Authoring Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "dag_authoring_dag",
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
# DAG AUTHORING DAG DEFINITION
# =============================================================================

DAG_AUTHORING_DAG = SessionDAG(
    id="dag-authoring-v1",
    name="DAG Authoring Workflow",
    version="1.0.0",
    description="""
Create or update DAGs the PROPER way.

CRITICAL RULES:
1. DAG nodes contain ALL detailed instructions in `action` field
2. Slash command file is MINIMAL TRIGGER only (~30 lines)
3. NEVER duplicate instructions between command and DAG
4. Each node action should be copy-paste executable

NODE TYPES:
- START/END — Entry/exit points
- ANALYZE — Information gathering, no state change
- TRANSFORM — State-changing operations
- VALIDATE — Verification checks
- GATE — Conditional branching (CONDITIONAL or USER_CONFIRM)

PROPER PATTERN:
```python
SessionNode(
    id="unique_id",
    name="Human Name",
    node_type=NodeType.TRANSFORM,
    description="One-line summary",
    action='''Detailed multi-line instructions here.

Include:
- Exact commands to run
- Expected outputs
- Pre-reading files
- Success criteria
''',
    outputs=["state_key_1", "state_key_2"],
)
```

KEY FILES:
- DAGs: workflows/dags/*.py
- Interface: workflows/session/interface.py
- Registry: workflows/session/registry.py
- Commands: .cursor-commands/commands/*.md
""",
    tags=["meta", "dag", "authoring", "workflow", "creation"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin DAG authoring workflow. Identify what workflow to encode.",
        ),
        # === PHASE 1: ANALYZE ===
        SessionNode(
            id="analyze_workflow",
            name="Analyze Workflow",
            node_type=NodeType.ANALYZE,
            description="Understand the workflow to encode",
            action="""Analyze the workflow that needs to be encoded as a DAG.

1. **Identify the workflow source:**
   - Existing chat transcript with steps?
   - Manual process to automate?
   - New workflow design?

2. **Extract key elements:**
   - What are the PHASES? (numbered steps)
   - What are the GATES? (decision points, user confirms)
   - What are the OUTPUTS? (state values produced)
   - What files need to be read/modified?

3. **Document in state:**
   ```python
   state["workflow_name"] = "readme-pipeline"
   state["phases"] = ["gap_analysis", "enrich", "generate", "validate"]
   state["gates"] = ["gaps_found?", "template_update?", "validation_passed?"]
   state["key_files"] = ["config.yaml", "generator.py"]
   ```

4. **Check for existing DAGs:**
   ```bash
   ls workflows/dags/*.py
   ```
   Is there a similar DAG to use as template?

Pre-reading: workflows/dags/*.py (pick one as reference)""",
            outputs=["workflow_name", "phases", "gates", "key_files", "reference_dag"],
        ),
        # === PHASE 2: STRUCTURE ===
        SessionNode(
            id="design_structure",
            name="Design Node Structure",
            node_type=NodeType.ANALYZE,
            description="Design the node graph structure",
            action="""Design the DAG node graph.

1. **Create node list:**
   - start (START)
   - One node per phase (ANALYZE/TRANSFORM/VALIDATE)
   - One gate per decision point (GATE)
   - end (END)

2. **Map node types:**
   | Phase | Node ID | Node Type | Gate Type |
   |-------|---------|-----------|-----------|
   | Entry | start | START | - |
   | Analysis | analyze_X | ANALYZE | - |
   | Decision | gate_X | GATE | CONDITIONAL/USER_CONFIRM |
   | Transform | do_X | TRANSFORM | - |
   | Validate | validate_X | VALIDATE | - |
   | Exit | end | END | - |

3. **Design edge flow:**
   ```
   start → phase1 → gate1 → [branch_a, branch_b] → phase2 → validate → gate2 → [success, retry] → end
   ```

4. **Identify loop-backs:**
   - Validation failure → return to fix step
   - User rejection → return to earlier phase

5. **Document state flow:**
   What outputs from each node feed into later nodes?

Pre-reading: workflows/session/interface.py (for NodeType, GateType enums)""",
            outputs=["node_list", "edge_flow", "loop_backs"],
        ),
        # === PHASE 3: WRITE NODES ===
        SessionNode(
            id="write_nodes",
            name="Write Node Definitions",
            node_type=NodeType.TRANSFORM,
            description="Write each node with detailed action instructions",
            action="""Write each SessionNode with DETAILED action instructions.

⚠️ CRITICAL: Each node's `action` field contains ALL instructions.
   This is where the actual work is documented — NOT in the command file!

FOR EACH NODE:

```python
SessionNode(
    id="lowercase_snake_case",           # Unique identifier
    name="Human Readable Name",          # Display name
    node_type=NodeType.TRANSFORM,        # Type (see below)
    description="One-line what it does", # Brief summary
    action='''DETAILED instructions here.

## What to Do
1. Specific step one
2. Specific step two

## Commands to Run
```bash
actual_command --with-flags
```

## Expected Output
- Description of success state
- What files change

## Pre-reading
- path/to/file.py

## State Updates
```python
state["key"] = value
```
''',
    outputs=["state_keys_produced"],     # Optional: state keys this node sets
    gate_type=GateType.CONDITIONAL,      # Only for GATE nodes
    validation="state.get('x', False)",  # Only for GATE/VALIDATE nodes
)
```

NODE TYPE GUIDE:
- START/END — Entry/exit (minimal action)
- ANALYZE — Read, compare, discover (no mutations)
- TRANSFORM — Create, modify, delete (mutations)
- VALIDATE — Check, verify, test (assertions)
- GATE — Decision point (needs gate_type)

GATE TYPE GUIDE:
- CONDITIONAL — Auto-evaluated (validation expression)
- USER_CONFIRM — Requires user approval

✅ DO: Include exact commands, file paths, expected outputs
❌ DON'T: Leave vague instructions like "do the thing"

Pre-reading: workflows/dags/readme_pipeline_dag.py (good example)""",
            outputs=["nodes_written"],
        ),
        # === PHASE 4: WRITE EDGES ===
        SessionNode(
            id="write_edges",
            name="Write Edge Definitions",
            node_type=NodeType.TRANSFORM,
            description="Define flow between nodes",
            action="""Write SessionEdge definitions for all transitions.

EDGE STRUCTURE:
```python
SessionEdge(
    from_node="node_id",        # Source node
    to_node="target_id",        # Destination node
    condition="condition_key",  # Optional: for conditional branches
    label="Display Label",      # Optional: edge label for visualization
)
```

PATTERNS:

1. **Linear flow:**
```python
SessionEdge(from_node="start", to_node="phase1"),
SessionEdge(from_node="phase1", to_node="phase2"),
```

2. **Conditional branch (from gate):**
```python
SessionEdge(from_node="gate_x", to_node="path_a", condition="yes", label="Approved"),
SessionEdge(from_node="gate_x", to_node="path_b", condition="no", label="Rejected"),
```

3. **Loop-back (validation retry):**
```python
SessionEdge(from_node="gate_valid", to_node="fix_step", condition="failed", label="Fix issues"),
SessionEdge(from_node="gate_valid", to_node="next_step", condition="passed", label="Continue"),
```

4. **Merge (multiple paths join):**
```python
SessionEdge(from_node="path_a", to_node="merged_step"),
SessionEdge(from_node="path_b", to_node="merged_step"),
```

COMPLETENESS CHECK:
- Every node except END has at least one outgoing edge
- Every node except START has at least one incoming edge
- All gate nodes have edges for each possible outcome""",
            outputs=["edges_written"],
        ),
        # === PHASE 5: VALIDATE ===
        SessionNode(
            id="validate_dag",
            name="Validate DAG",
            node_type=NodeType.VALIDATE,
            description="Test DAG imports and registration",
            action="""Validate the DAG is syntactically correct and registerable.

1. **Syntax check:**
```bash
python -m py_compile workflows/dags/new_dag.py
```

2. **Import test:**
```python
python -c "from workflows.dags.new_dag import NEW_DAG; print(f'ID: {NEW_DAG.id}')"
```

3. **Registration test:**
```python
python -c "
from workflows.session.registry import get_dag
from workflows.dags import new_dag  # Triggers auto-register
dag = get_dag('new-dag-id')
print(f'Registered: {dag.name}')  # noqa: ADR-0019
print(f'Nodes: {len(dag.nodes)}')  # noqa: ADR-0019
print(f'Edges: {len(dag.edges)}')  # noqa: ADR-0019
"
```

4. **Completeness check:**
   - All nodes referenced in edges exist
   - All gate nodes have multiple outgoing edges
   - START has no incoming, END has no outgoing

5. **Update __init__.py:**
```python
# Add to workflows/dags/__init__.py
from workflows.dags.new_dag import NEW_DAG
```

SUCCESS CRITERIA:
- py_compile passes
- Import succeeds
- Registration succeeds
- Completeness verified""",
            outputs=["validation_passed"],
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Passed?",
            node_type=NodeType.GATE,
            description="Check if DAG validation succeeded",
            action="If validation passed, proceed to create command. Otherwise fix issues.",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('validation_passed', False)",
        ),
        # === PHASE 6: CREATE COMMAND ===
        SessionNode(
            id="create_command",
            name="Create Minimal Command",
            node_type=NodeType.TRANSFORM,
            description="Create MINIMAL trigger command file (~30 lines)",
            action="""Create the slash command file as a MINIMAL TRIGGER.

⚠️ CRITICAL: Command file is ~30 lines. NO detailed instructions!
   All instructions are in the DAG's node action fields.

TEMPLATE (.cursor-commands/commands/{command}.md):

```markdown
name: {command}
version: "1.0.0"
description: "One-line description"
auto_chain: ynp
dag: {dag-id}
dag_file: workflows/dags/{dag_file}.py

# /{command} — {Human Title}

**DAG-ENFORCED.** Execute the `{dag-id}` DAG.

## Usage

```
/{command}                    # Default usage
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

- **DAG**: `workflows/dags/{dag_file}.py`
- **Other relevant files**
```

CHECKLIST:
- [ ] YAML frontmatter with dag and dag_file
- [ ] Brief usage examples (3-5 lines)
- [ ] Reference to DAG file
- [ ] NO detailed instructions (those are in DAG)
- [ ] Total ~30-40 lines

❌ ANTI-PATTERN (verbose command file):
```markdown
# BAD: 300+ lines of instructions
## Phase 1: Do this...
## Phase 2: Do that...
```

✅ CORRECT PATTERN (minimal trigger):
```markdown
# GOOD: ~30 lines pointing to DAG
The DAG contains all instructions.
```""",
            outputs=["command_created"],
        ),
        # === PHASE 7: UPDATE REGISTRY ===
        SessionNode(
            id="update_registry",
            name="Update Command Registry",
            node_type=NodeType.TRANSFORM,
            description="Add command to slash command registry",
            action="""Update slash command registry to include new command.

1. **Add to 02-slash-commands.mdc:**
```markdown
| /{command} | `commands/{command}.md` | Brief description |
```

2. **Add to commands-index.md:**
   - Quick reference table
   - Auto-chaining table (if applicable)

3. **Verify command recognition:**
   Test that /{command} triggers the file read.

Pre-reading: .cursor/rules/02-slash-commands.mdc""",
            outputs=["registry_updated"],
        ),
        # === END ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="DAG authoring complete",
            action="DAG authoring workflow complete. New DAG ready for use.",
        ),
    ],
    edges=[
        # Linear flow
        SessionEdge(from_node="start", to_node="analyze_workflow"),
        SessionEdge(from_node="analyze_workflow", to_node="design_structure"),
        SessionEdge(from_node="design_structure", to_node="write_nodes"),
        SessionEdge(from_node="write_nodes", to_node="write_edges"),
        SessionEdge(from_node="write_edges", to_node="validate_dag"),
        SessionEdge(from_node="validate_dag", to_node="gate_validation"),
        # Validation gate
        SessionEdge(
            from_node="gate_validation",
            to_node="create_command",
            condition="passed",
            label="Validation passed",
        ),
        SessionEdge(
            from_node="gate_validation",
            to_node="write_nodes",
            condition="failed",
            label="Fix issues",
        ),
        # Complete flow
        SessionEdge(from_node="create_command", to_node="update_registry"),
        SessionEdge(from_node="update_registry", to_node="end"),
    ],
)


# =============================================================================
# REGISTRATION
# =============================================================================


def register():
    """Register the DAG authoring DAG."""
    register_session_dag(DAG_AUTHORING_DAG)


# Auto-register on import
register()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-026",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "testing", "utility", "workflows"],
    "keywords": [
        "action",
        "authoring",
        "between",
        "command",
        "create",
        "dag",
        "dags",
        "detailed",
    ],
    "business_value": "This DAG enforces the proper pattern for creating and updating DAGs. DAGs contain ALL detailed instructions in node `action` fields Slash commands are MINIMAL TRIGGERS (~30 lines) NEVER duplicate inst",
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
