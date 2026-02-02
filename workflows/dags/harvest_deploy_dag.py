"""
Harvest-Deploy Session DAG
==========================

Systematic workflow for harvesting code from documents and deploying.

Based on the 2026-01-25 session workflow:
1. Parse plan document
2. Extract code blocks
3. Deploy full files
4. Inject diffs
5. Validate
6. Report/Commit

Version: 1.0.0
"""

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# HARVEST-DEPLOY DAG DEFINITION
# =============================================================================

HARVEST_DEPLOY_DAG = SessionDAG(
    id="harvest-deploy-v1",
    name="Harvest-Deploy Workflow",
    version="1.0.0",
    description="""
Systematic workflow for harvesting code from markdown documents
and deploying to the L9 codebase.

This DAG guides through:
1. Parse plan/source documents
2. Extract code blocks (using sed, not manual copy)
3. Deploy full files (copy)
4. Inject diffs into existing files (sed)
5. Validate all changes
6. Generate report and optionally commit

Use when: Deploying code from research documents, chat transcripts,
or planning documents that contain code blocks to harvest.

CRITICAL RULES:
- NO manual code writing - use sed/cp only
- Extract EXACTLY what's in the document
- Validate syntax before proceeding
""",
    tags=["harvest", "deploy", "sed", "systematic", "no-manual-write"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin harvest-deploy workflow",
        ),
        # === PHASE: PARSE ===
        SessionNode(
            id="parse_plan",
            name="Parse Plan Document",
            node_type=NodeType.ANALYZE,
            description="Analyze the plan document for extraction instructions",
            action="""Read and analyze the plan document:

1. Identify CREATES (new files):
   - Source line ranges in markdown
   - Target file paths

2. Identify INJECTS (diffs):
   - Source line ranges in markdown
   - Target files and injection points
   - after_line or after_pattern

3. Identify REPLACES (replacements):
   - Source line ranges
   - Target file ranges to replace

Output: Extraction plan with line numbers""",
            outputs=["creates", "injects", "replaces", "source_document"],
        ),
        SessionNode(
            id="verify_sources",
            name="Verify Source Document",
            node_type=NodeType.VALIDATE,
            description="Verify source document exists and has expected line counts",
            action="""Verify source document:

wc -l {source_document}

Check that referenced line ranges exist:
sed -n '{start},{end}p' {source_document} | wc -l

Flag any discrepancies.""",
            validation="Source document exists, line counts verified",
        ),
        SessionNode(
            id="gate_plan",
            name="Plan Gate",
            node_type=NodeType.GATE,
            description="User confirms extraction plan",
            action="""## Extraction Plan

### CREATES (New Files)
| # | Lines | Output File | Target |
|---|-------|-------------|--------|
{creates_table}

### INJECTS (Diffs)
| # | Lines | Target | After |
|---|-------|--------|-------|
{injects_table}

### REPLACES
| # | Lines | Target | Replace |
|---|-------|--------|---------|
{replaces_table}

⏸️ AWAITING: "CONFIRM" to proceed""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE: EXTRACT ===
        SessionNode(
            id="extract_files",
            name="Extract Code Blocks",
            node_type=NodeType.TRANSFORM,
            description="Extract code blocks using sed",
            action="""For each extraction pattern:

# Strip backticks (remove first and last line of code block)
sed -n '{start},{end}p' "{source}" | sed '1d' | sed '$d' > "{output}"

# Verify extraction
wc -l "{output}"

CRITICAL:
- Use sed ONLY
- Do NOT manually write or copy content
- Extract EXACTLY what's in the source""",
            validation="wc -l confirms expected line counts",
            outputs=["extracted_files"],
        ),
        SessionNode(
            id="validate_extraction",
            name="Validate Extraction",
            node_type=NodeType.VALIDATE,
            description="Validate extracted files",
            action="""For each extracted file:

1. Check it exists and has content:
   ls -la {extracted_files}

2. For Python files, validate syntax:
   python3 -m py_compile {file.py}

3. For SQL files, basic structure check:
   head -5 {file.sql}

Report any issues.""",
            validation="All extracted files valid",
        ),
        SessionNode(
            id="gate_extraction",
            name="Extraction Gate",
            node_type=NodeType.GATE,
            description="User confirms extraction before deployment",
            action="""## Extraction Complete

**Files extracted:** {count}

### Validation Results
{validation_results}

⏸️ AWAITING: "CONTINUE" to deploy""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE: DEPLOY ===
        SessionNode(
            id="deploy_creates",
            name="Deploy Full Files",
            node_type=NodeType.TRANSFORM,
            description="Copy extracted files to target locations",
            action="""For each CREATE mapping:

# Ensure target directory exists
mkdir -p $(dirname "{target}")

# Copy file
cp "{source}" "{target}"

# Verify
ls -la "{target}"

CRITICAL:
- Use cp ONLY
- Create directories as needed
- Do NOT modify file contents during copy""",
            validation="All files copied to correct locations",
            outputs=["deployed_files"],
        ),
        SessionNode(
            id="deploy_injects",
            name="Inject Diffs",
            node_type=NodeType.TRANSFORM,
            description="Inject diff content into existing files",
            action="""For each INJECT mapping:

# Inject after specific line
sed -i '' '{line}r {source}' "{target}"

# Or inject after pattern
sed -i '' '/{pattern}/r {source}' "{target}"

CRITICAL:
- Use sed -i '' for macOS in-place edit
- Verify injection point exists before injecting
- Check line numbers haven't shifted from prior injections""",
            validation="Injections verified with grep",
            outputs=["modified_files"],
        ),
        SessionNode(
            id="deploy_replaces",
            name="Replace Sections",
            node_type=NodeType.TRANSFORM,
            description="Replace line ranges in existing files",
            action="""For each REPLACE mapping:

# Step 1: Delete the line range
sed -i '' '{start},{end}d' "{target}"

# Step 2: Insert new content at (start - 1)
sed -i '' '{start-1}r {source}' "{target}"

CRITICAL:
- Delete THEN insert (two-step process)
- Verify line numbers before each operation
- Check replacement was successful""",
            validation="Replacements verified",
        ),
        # === PHASE: VALIDATE ===
        SessionNode(
            id="validate_all",
            name="Full Validation",
            node_type=NodeType.VALIDATE,
            description="Validate all deployed and modified files",
            action="""Run full validation suite:

1. Python syntax:
   python3 -m py_compile {all_py_files}

2. Import check:
   python3 -c "from {module} import *"

3. Linting:
   ruff check {files} --select=E,F

4. Check for expected patterns:
   grep -l "{expected_pattern}" {target_files}

All must pass.""",
            validation="py_compile ✅, imports ✅, lint ✅",
        ),
        SessionNode(
            id="gate_validation",
            name="Validation Gate",
            node_type=NodeType.GATE,
            description="User confirms validation before report",
            action="""## Validation Results

### Syntax Check
{syntax_results}

### Import Check
{import_results}

### Lint Check
{lint_results}

**Status:** {PASS/FAIL}

⏸️ AWAITING: "REPORT" to generate final report""",
            gate_type=GateType.USER_CONFIRM,
        ),
        # === PHASE: REPORT ===
        SessionNode(
            id="generate_report",
            name="Generate Report",
            node_type=NodeType.TRANSFORM,
            description="Generate final deployment report",
            action="""Generate deployment report:

## HARVEST-DEPLOY REPORT

**Workflow ID:** {workflow_id}
**Started:** {started_at}
**Completed:** {completed_at}

### Files Created
| File | Lines |
|------|-------|
{created_files_table}

### Files Modified
| File | Change |
|------|--------|
{modified_files_table}

### Validation
- Syntax: ✅ PASSED
- Imports: ✅ PASSED
- Lint: ✅ PASSED

### Next Steps
- Review changes: git diff
- Commit if satisfied
- Run tests: pytest tests/""",
            outputs=["report"],
        ),
        SessionNode(
            id="gate_commit",
            name="Commit Gate",
            node_type=NodeType.GATE,
            description="User decides whether to commit",
            action="""## Ready to Commit?

**Changes staged:** {count} files

Options:
- YES: Commit with generated message
- NO: Exit without committing
- DIFF: Show git diff first""",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves",
            action="""git add {files}

git commit -m "$(cat <<'EOF'
feat(harvest): deploy {module_name}

## Files Created
{created_list}

## Files Modified
{modified_list}

Deployed via harvest-deploy workflow.
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
            description="Workflow complete",
            action="Harvest-deploy workflow complete.",
        ),
    ],
    edges=[
        # Start -> Parse
        SessionEdge("start", "parse_plan"),
        SessionEdge("parse_plan", "verify_sources"),
        SessionEdge("verify_sources", "gate_plan"),
        # Plan gate
        SessionEdge(
            "gate_plan", "extract_files", condition="confirm", label="Confirmed"
        ),
        SessionEdge("gate_plan", "end", condition="abort", label="Abort"),
        # Extract
        SessionEdge("extract_files", "validate_extraction"),
        SessionEdge("validate_extraction", "gate_extraction"),
        # Extraction gate
        SessionEdge(
            "gate_extraction", "deploy_creates", condition="continue", label="Deploy"
        ),
        SessionEdge("gate_extraction", "end", condition="abort", label="Abort"),
        # Deploy
        SessionEdge("deploy_creates", "deploy_injects"),
        SessionEdge("deploy_injects", "deploy_replaces"),
        SessionEdge("deploy_replaces", "validate_all"),
        # Validation
        SessionEdge("validate_all", "gate_validation"),
        SessionEdge(
            "gate_validation", "generate_report", condition="proceed", label="Report"
        ),
        SessionEdge("gate_validation", "end", condition="abort", label="Abort"),
        # Report
        SessionEdge("generate_report", "gate_commit"),
        SessionEdge("gate_commit", "commit", condition="yes", label="Commit"),
        SessionEdge("gate_commit", "end", condition="no", label="Skip Commit"),
        # End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(HARVEST_DEPLOY_DAG)


def get_harvest_deploy_dag() -> SessionDAG:
    """Get the harvest-deploy DAG."""
    return HARVEST_DEPLOY_DAG


# Generate Mermaid diagram for documentation
if __name__ == "__main__":
    print(HARVEST_DEPLOY_DAG.to_markdown())  # noqa: ADR-0019
