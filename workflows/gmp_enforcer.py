#!/usr/bin/env python3
"""
GMP Enforcer — Bridge Between Slash Commands and DAG Execution
===============================================================

This script enforces GMP step ordering by:
1. Tracking which steps have been executed
2. Refusing to proceed without required dependencies
3. Generating prompts for the next required step

Usage:
    # Check current state and get next required step
    python3 workflows/gmp_enforcer.py status

    # Mark a step as complete
    python3 workflows/gmp_enforcer.py complete memory_read

    # Get the prompt for the next required step
    python3 workflows/gmp_enforcer.py next

    # Reset workflow state
    python3 workflows/gmp_enforcer.py reset

The enforcer maintains state in .gmp_state.json and REFUSES to let
the agent skip steps or proceed out of order.

Author: L9 Team
Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Gmp Enforcer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:34:22Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "gmp_enforcer",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# =============================================================================
# Data Models
# =============================================================================


class StepStatus(str, Enum):
    """Status of a GMP step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class GMPStep:
    """A single step in the GMP workflow."""

    id: str
    name: str
    description: str
    prompt: str
    depends_on: list[str] = field(default_factory=list)
    required: bool = True
    status: StepStatus = StepStatus.PENDING
    completed_at: str | None = None
    output: str | None = None


@dataclass
class GMPState:
    """Persistent state of GMP execution."""

    gmp_id: str
    tier: str
    task_description: str
    started_at: str
    steps: dict[str, GMPStep] = field(default_factory=dict)
    current_step: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        result = asdict(self)
        # Convert StepStatus enum to string
        for step_id, step_data in result["steps"].items():
            if isinstance(step_data["status"], StepStatus):
                step_data["status"] = step_data["status"].value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GMPState:
        """Create from dict."""
        steps = {}
        for step_id, step_data in data.get("steps", {}).items():
            step_data["status"] = StepStatus(step_data["status"])
            steps[step_id] = GMPStep(**step_data)
        data["steps"] = steps
        return cls(**data)


# =============================================================================
# GMP Workflow Definition
# =============================================================================

GMP_WORKFLOW = [
    GMPStep(
        id="memory_read",
        name="🧠 Memory Read (MANDATORY)",
        description="Search L9 memory for context BEFORE implementation",
        prompt="""## 🧠 MEMORY READ — REQUIRED STEP

Execute these commands NOW:

```bash
python3 agents/cursor/cursor_memory_client.py search "{task_keywords}"
python3 agents/cursor/cursor_memory_client.py search "lessons errors {component}"
python3 agents/cursor/cursor_memory_client.py search "{domain} patterns"
```

Then output:

## 🧠 MEMORY CONTEXT INJECTED

### Related Work Found
- [list findings]

### Relevant Patterns
- [list patterns]

### Lessons to Apply
- [list lessons]

⚠️ THIS STEP CANNOT BE SKIPPED. Mark complete with:
`python3 workflows/gmp_enforcer.py complete memory_read`
""",
        depends_on=[],
        required=True,
    ),
    GMPStep(
        id="scope_lock",
        name="Scope Lock (Phase 0)",
        description="Define TODO plan with explicit file budget",
        prompt="""## SCOPE LOCK — REQUIRED STEP

Create the TODO plan:

## GMP SCOPE LOCK

GMP ID: GMP-XXX
Tier: KERNEL | RUNTIME | INFRA | UX

### TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|

### FILE BUDGET
- MAY: [files in TODO only]
- MAY NOT: [everything else]

### MEMORY CONTEXT APPLIED
- Patterns: [from memory_read]
- Lessons: [from memory_read]

⏸️ Awaiting "CONFIRM" from user

Mark complete with: `python3 workflows/gmp_enforcer.py complete scope_lock`
""",
        depends_on=["memory_read"],
        required=True,
    ),
    GMPStep(
        id="user_confirm",
        name="User Confirmation Gate",
        description="Wait for explicit CONFIRM from user",
        prompt="""## AWAITING USER CONFIRMATION

The scope is locked. Wait for user to type "CONFIRM" before proceeding.

Do NOT proceed without explicit confirmation.

Mark complete with: `python3 workflows/gmp_enforcer.py complete user_confirm`
""",
        depends_on=["scope_lock"],
        required=True,
    ),
    GMPStep(
        id="baseline",
        name="Baseline Verification (Phase 1)",
        description="Verify files exist and assumptions hold",
        prompt="""## BASELINE VERIFICATION — REQUIRED STEP

Verify:
1. All files in TODO exist
2. Line ranges are correct
3. Imports resolve
4. No protected files without approval

```bash
ls -la {files_in_todo}
wc -l {files_in_todo}
python3 -c "from {module} import *"
```

Any failure → STOP → Return to Phase 0

Mark complete with: `python3 workflows/gmp_enforcer.py complete baseline`
""",
        depends_on=["user_confirm"],
        required=True,
    ),
    GMPStep(
        id="implement",
        name="Implementation (Phase 2-3)",
        description="Execute TODO plan — no scope drift",
        prompt="""## IMPLEMENTATION — REQUIRED STEP

Execute each TODO item:

### RULES
- For /use-harvest: Use sed/cp ONLY — NO manual rewriting
- For semantic changes: Apply targeted edits
- ALL changes must map 1:1 to TODO items
- NO scope drift

### FORBIDDEN
- Reformatting not in TODO
- "While I'm here" cleanup
- ANY change not in TODO

Mark complete with: `python3 workflows/gmp_enforcer.py complete implement`
""",
        depends_on=["baseline"],
        required=True,
    ),
    GMPStep(
        id="validate",
        name="Validation (Phase 4)",
        description="All validation must pass",
        prompt="""## VALIDATION — REQUIRED STEP

Run validation:

```bash
python3 -m py_compile {modified_files}
python3 -c "from {module} import *"
ruff check {modified_files} --select=E,F
pytest tests/{relevant} -v
```

### FAILURE HANDLING
- ANY failure → STOP
- Do NOT patch forward
- Return failure with evidence

Mark complete with: `python3 workflows/gmp_enforcer.py complete validate`
""",
        depends_on=["implement"],
        required=True,
    ),
    GMPStep(
        id="memory_write",
        name="🧠 Memory Write (MANDATORY)",
        description="Save learnings BEFORE finalization",
        prompt="""## 🧠 MEMORY WRITE — REQUIRED STEP

Execute these commands NOW:

```bash
python3 agents/cursor/cursor_memory_client.py write \\
  "GMP-XXX: {summary}. Tags: gmp, {component}" --kind lesson

python3 agents/cursor/cursor_memory_client.py write \\
  "{pattern}. Tags: {domain}, pattern" --kind pattern

python3 agents/cursor/cursor_memory_client.py write \\
  "{error_fix}. Tags: error, {component}" --kind lesson
```

Output:

## 🧠 MEMORY WRITTEN

- ✅ GMP summary saved
- ✅ Patterns saved (if any)
- ✅ Lessons saved (if any)

⚠️ THIS STEP CANNOT BE SKIPPED. Mark complete with:
`python3 workflows/gmp_enforcer.py complete memory_write`
""",
        depends_on=["validate"],
        required=True,
    ),
    GMPStep(
        id="finalize",
        name="Finalize (Phase 6)",
        description="Generate GMP report using the report generator script",
        prompt="""## FINALIZE — REQUIRED STEP

Generate the GMP report using the canonical report generator:

```bash
# Generate report with the script (MANDATORY)
python3 scripts/generate_gmp_report.py \\
  --task "{task_description}" \\
  --tier {TIER}_TIER \\
  --todo "T1|{file}|{lines}|{action}|{description}" \\
  --validation "py_compile|✅" \\
  --validation "imports|✅" \\
  --summary "{brief_summary}" \\
  --update-workflow
```

OR use interactive mode:
```bash
python3 scripts/generate_gmp_report.py
```

The script will:
1. Auto-detect the next GMP ID (e.g., GMP-129)
2. Generate `reports/GMP Reports/GMP-Report-{ID}-{Description}.md`
3. Optionally update `workflow_state.md`
4. Run automatic verification

⚠️ DO NOT create inline reports — USE THE SCRIPT!

After running the script, output:

## GMP REPORT GENERATED

- 📄 Report: `reports/GMP Reports/GMP-Report-{ID}-{Description}.md`
- ✅ Verification: PASSED
- ✅ workflow_state.md: Updated

### /ynp
- YES: Commit all changes
- NO: Exit without commit
- PROCEED: Different action

Mark complete with: `python3 workflows/gmp_enforcer.py complete finalize`
""",
        depends_on=["memory_write"],
        required=True,
    ),
]


# =============================================================================
# GMP Enforcer
# =============================================================================


class GMPEnforcer:
    """Enforces GMP step ordering."""

    STATE_FILE = Path(".gmp_state.json")

    def __init__(self, working_dir: Path | None = None):
        """Initialize enforcer."""
        self.working_dir = working_dir or Path.cwd()
        self.state_file = self.working_dir / self.STATE_FILE
        self.state: GMPState | None = None
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                data = json.load(f)
            self.state = GMPState.from_dict(data)

    def _save_state(self) -> None:
        """Save state to file."""
        if self.state:
            with open(self.state_file, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2)

    def initialize(self, gmp_id: str, tier: str, task_description: str) -> None:
        """Initialize a new GMP execution."""
        steps = {step.id: step for step in GMP_WORKFLOW}
        self.state = GMPState(
            gmp_id=gmp_id,
            tier=tier,
            task_description=task_description,
            started_at=datetime.now().isoformat(),
            steps=steps,
            current_step="memory_read",
        )
        self._save_state()
        print(f"✅ GMP initialized: {gmp_id}")  # noqa: ADR-0019
        print(f"   Tier: {tier}")  # noqa: ADR-0019
        print(f"   Task: {task_description}")  # noqa: ADR-0019
        print("\n📍 First step: memory_read")  # noqa: ADR-0019

    def status(self) -> None:
        """Print current status."""
        if not self.state:
            print("❌ No active GMP. Initialize with:")  # noqa: ADR-0019
            print(  # noqa: ADR-0019
                "   python3 workflows/gmp_enforcer.py init GMP-XXX RUNTIME 'task description'"
            )
            return

        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"GMP: {self.state.gmp_id} ({self.state.tier})")  # noqa: ADR-0019
        print(f"Task: {self.state.task_description}")  # noqa: ADR-0019
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print(f"{'=' * 60}")  # noqa: ADR-0019

        for step in GMP_WORKFLOW:
            state_step = self.state.steps.get(step.id)
            if state_step:
                status_icon = {
                    StepStatus.PENDING: "⏳",
                    StepStatus.IN_PROGRESS: "🔄",
                    StepStatus.COMPLETED: "✅",
                    StepStatus.SKIPPED: "⏭️",
                    StepStatus.FAILED: "❌",
                }.get(state_step.status, "❓")

                current = " ← CURRENT" if step.id == self.state.current_step else ""
                print(f"  {status_icon} {step.name}{current}")  # noqa: ADR-0019

        print(f"{'=' * 60}\n")  # noqa: ADR-0019

    def next_step(self) -> None:
        """Get prompt for next required step."""
        if not self.state:
            print("❌ No active GMP")  # noqa: ADR-0019
            return

        current = self.state.current_step
        if not current:
            print("✅ All steps complete!")  # noqa: ADR-0019
            return

        step = self.state.steps.get(current)
        if not step:
            print(f"❌ Unknown step: {current}")  # noqa: ADR-0019
            return

        # Check dependencies
        for dep in step.depends_on:
            dep_step = self.state.steps.get(dep)
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                print(  # noqa: ADR-0019
                    f"❌ BLOCKED: Step '{current}' requires '{dep}' to be completed first!"
                )
                print(f"\nComplete '{dep}' first with:")  # noqa: ADR-0019
                print(f"   python3 workflows/gmp_enforcer.py complete {dep}")  # noqa: ADR-0019
                return

        # Show prompt
        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"NEXT REQUIRED STEP: {step.name}")  # noqa: ADR-0019
        print(f"{'=' * 60}")  # noqa: ADR-0019
        print(step.prompt)  # noqa: ADR-0019

    def complete_step(self, step_id: str, output: str = "") -> None:
        """Mark a step as complete."""
        if not self.state:
            print("❌ No active GMP")  # noqa: ADR-0019
            return

        step = self.state.steps.get(step_id)
        if not step:
            print(f"❌ Unknown step: {step_id}")  # noqa: ADR-0019
            return

        # Check dependencies
        for dep in step.depends_on:
            dep_step = self.state.steps.get(dep)
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                print(  # noqa: ADR-0019
                    f"❌ BLOCKED: Cannot complete '{step_id}' — requires '{dep}' first!"
                )
                return

        # Mark complete
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.now().isoformat()
        step.output = output

        # Find next step
        for workflow_step in GMP_WORKFLOW:
            state_step = self.state.steps.get(workflow_step.id)
            if state_step and state_step.status == StepStatus.PENDING:
                self.state.current_step = workflow_step.id
                break
        else:
            self.state.current_step = None

        self._save_state()
        print(f"✅ Step '{step_id}' completed!")  # noqa: ADR-0019

        if self.state.current_step:
            print(f"📍 Next step: {self.state.current_step}")  # noqa: ADR-0019
        else:
            print("🎉 All steps complete!")  # noqa: ADR-0019

    def reset(self) -> None:
        """Reset workflow state."""
        if self.state_file.exists():
            self.state_file.unlink()
        self.state = None
        print("✅ GMP state reset")  # noqa: ADR-0019


# =============================================================================
# CLI
# =============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GMP Enforcer — Enforce step ordering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/gmp_enforcer.py init GMP-123 RUNTIME "add tool discovery"
    python3 workflows/gmp_enforcer.py status
    python3 workflows/gmp_enforcer.py next
    python3 workflows/gmp_enforcer.py complete memory_read
    python3 workflows/gmp_enforcer.py reset
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Init
    init_parser = subparsers.add_parser("init", help="Initialize GMP")
    init_parser.add_argument("gmp_id", help="GMP ID (e.g., GMP-123)")
    init_parser.add_argument("tier", choices=["KERNEL", "RUNTIME", "INFRA", "UX"])
    init_parser.add_argument("task", help="Task description")

    # Status
    subparsers.add_parser("status", help="Show current status")

    # Next
    subparsers.add_parser("next", help="Get next required step")

    # Complete
    complete_parser = subparsers.add_parser("complete", help="Mark step complete")
    complete_parser.add_argument("step_id", help="Step ID to mark complete")
    complete_parser.add_argument("--output", "-o", default="", help="Step output")

    # Reset
    subparsers.add_parser("reset", help="Reset workflow state")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    enforcer = GMPEnforcer()

    if args.command == "init":
        enforcer.initialize(args.gmp_id, args.tier, args.task)
    elif args.command == "status":
        enforcer.status()
    elif args.command == "next":
        enforcer.next_step()
    elif args.command == "complete":
        enforcer.complete_step(args.step_id, args.output)
    elif args.command == "reset":
        enforcer.reset()


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-009",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "cli",
        "data-models",
        "dataclass",
        "filesystem",
        "operations",
        "serialization",
        "testing",
    ],
    "keywords": [
        "complete",
        "enforcer",
        "gmp",
        "initialize",
        "reset",
        "state",
        "status",
        "step",
    ],
    "business_value": "1. Tracking which steps have been executed 2. Refusing to proceed without required dependencies 3. Generating prompts for the next required step # Check current state and get next required step python",
    "last_modified": "2026-01-31T22:34:22Z",
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
