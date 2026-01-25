#!/usr/bin/env python3
"""
L9 DAG Workflow Runner
======================

A flexible DAG-based workflow runner for orchestrating multi-step sessions.

Key Features:
- Define workflows as Python DAGs (nodes + edges)
- Checkpoint support (pause for confirmation)
- State persistence (resume interrupted workflows)
- Shell execution via subprocess (sed, cp, etc.)
- Progress reporting and validation

Usage:
    # Run a workflow
    python3 scripts/workflows/dag_runner.py run harvest-deploy.yaml

    # Resume interrupted workflow
    python3 scripts/workflows/dag_runner.py resume harvest-deploy.yaml

    # Validate workflow definition
    python3 scripts/workflows/dag_runner.py validate harvest-deploy.yaml

Example Workflow YAML:
    See scripts/workflows/examples/harvest-deploy.yaml

Author: L9 Team
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Data Models
# =============================================================================


class StepStatus(Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"


class StepType(Enum):
    """Type of workflow step."""

    SHELL = "shell"  # Run shell command
    EXTRACT = "extract"  # Extract code from document (sed)
    COPY = "copy"  # Copy files (cp)
    INJECT = "inject"  # Inject into existing file (sed)
    REPLACE = "replace"  # Replace lines in file (sed)
    VALIDATE = "validate"  # Run validation checks
    CHECKPOINT = "checkpoint"  # Pause for user confirmation
    PYTHON = "python"  # Run Python function


@dataclass
class StepResult:
    """Result of executing a step."""

    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """A single step in the workflow DAG."""

    id: str
    name: str
    type: StepType
    config: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    checkpoint: bool = False
    continue_on_fail: bool = False
    status: StepStatus = StepStatus.PENDING
    result: StepResult | None = None


@dataclass
class WorkflowState:
    """Persistent state of a workflow execution."""

    workflow_id: str
    started_at: str
    updated_at: str
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Step Executors
# =============================================================================


class StepExecutor:
    """Execute different types of workflow steps."""

    def __init__(self, working_dir: Path, variables: dict[str, Any]):
        self.working_dir = working_dir
        self.variables = variables

    def execute(self, step: Step) -> StepResult:
        """Execute a step based on its type."""
        start_time = time.time()

        try:
            executor_map = {
                StepType.SHELL: self._execute_shell,
                StepType.EXTRACT: self._execute_extract,
                StepType.COPY: self._execute_copy,
                StepType.INJECT: self._execute_inject,
                StepType.REPLACE: self._execute_replace,
                StepType.VALIDATE: self._execute_validate,
                StepType.CHECKPOINT: self._execute_checkpoint,
                StepType.PYTHON: self._execute_python,
            }

            executor = executor_map.get(step.type)
            if not executor:
                return StepResult(
                    success=False,
                    error=f"Unknown step type: {step.type}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            result = executor(step.config)
            result.duration_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            return StepResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _resolve_vars(self, text: str) -> str:
        """Resolve ${var} placeholders in text."""

        def replacer(match):
            var_name = match.group(1)
            return str(self.variables.get(var_name, match.group(0)))

        return re.sub(r"\$\{(\w+)\}", replacer, text)

    def _run_shell(self, cmd: str, capture: bool = True) -> tuple[int, str, str]:
        """Run a shell command."""
        cmd = self._resolve_vars(cmd)
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=self.working_dir,
            capture_output=capture,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def _execute_shell(self, config: dict) -> StepResult:
        """Execute shell command(s)."""
        commands = config.get("commands", [])
        if isinstance(commands, str):
            commands = [commands]

        outputs = []
        for cmd in commands:
            code, stdout, stderr = self._run_shell(cmd)
            outputs.append(f"$ {cmd}\n{stdout}")
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Command failed (exit {code}): {stderr}",
                )

        return StepResult(success=True, output="\n".join(outputs))

    def _execute_extract(self, config: dict) -> StepResult:
        """Extract code blocks from document using sed."""
        source = self._resolve_vars(config["source"])
        target_dir = self._resolve_vars(config["target_dir"])
        patterns = config.get("patterns", [])

        # Ensure target directory exists
        os.makedirs(Path(self.working_dir) / target_dir, exist_ok=True)

        outputs = []
        for pattern in patterns:
            start_line = pattern["start_line"]
            end_line = pattern["end_line"]
            output_file = pattern["output"]
            strip_backticks = pattern.get("strip_backticks", True)

            target_path = f"{target_dir}/{output_file}"

            # Build sed command
            if strip_backticks:
                cmd = f"sed -n '{start_line},{end_line}p' \"{source}\" | sed '1d' | sed '$d' > \"{target_path}\""
            else:
                cmd = (
                    f'sed -n \'{start_line},{end_line}p\' "{source}" > "{target_path}"'
                )

            code, stdout, stderr = self._run_shell(cmd)
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Extract failed for {output_file}: {stderr}",
                )

            # Verify file created
            verify_cmd = f'wc -l "{target_path}"'
            code, stdout, _ = self._run_shell(verify_cmd)
            outputs.append(f"✓ Extracted {output_file} ({stdout.strip()})")

        return StepResult(
            success=True,
            output="\n".join(outputs),
            artifacts={"extracted_files": [p["output"] for p in patterns]},
        )

    def _execute_copy(self, config: dict) -> StepResult:
        """Copy files from source to target."""
        mappings = config.get("mappings", [])

        outputs = []
        for mapping in mappings:
            src = self._resolve_vars(mapping["from"])
            dst = self._resolve_vars(mapping["to"])

            # Ensure target directory exists
            dst_path = Path(self.working_dir) / dst
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = f'cp "{src}" "{dst}"'
            code, stdout, stderr = self._run_shell(cmd)
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Copy failed: {src} -> {dst}: {stderr}",
                )

            outputs.append(f"✓ Copied {src} -> {dst}")

        return StepResult(
            success=True,
            output="\n".join(outputs),
            artifacts={"copied_files": [m["to"] for m in mappings]},
        )

    def _execute_inject(self, config: dict) -> StepResult:
        """Inject content into existing file after specified line."""
        mappings = config.get("mappings", [])

        outputs = []
        for mapping in mappings:
            src = self._resolve_vars(mapping["from"])
            dst = self._resolve_vars(mapping["to"])
            after_line = mapping.get("after_line")
            after_pattern = mapping.get("after_pattern")

            if after_line:
                cmd = f"sed -i '' '{after_line}r '{src}' \"{dst}\""
            elif after_pattern:
                cmd = f"sed -i '' '/{after_pattern}/r '{src}' \"{dst}\""
            else:
                return StepResult(
                    success=False,
                    error=f"Inject requires 'after_line' or 'after_pattern': {dst}",
                )

            code, stdout, stderr = self._run_shell(cmd)
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Inject failed: {src} -> {dst}: {stderr}",
                )

            outputs.append(f"✓ Injected {src} -> {dst}:{after_line or after_pattern}")

        return StepResult(
            success=True,
            output="\n".join(outputs),
            artifacts={"modified_files": [m["to"] for m in mappings]},
        )

    def _execute_replace(self, config: dict) -> StepResult:
        """Replace lines in file with content from source."""
        mappings = config.get("mappings", [])

        outputs = []
        for mapping in mappings:
            src = self._resolve_vars(mapping["from"])
            dst = self._resolve_vars(mapping["to"])
            start_line = mapping["start_line"]
            end_line = mapping["end_line"]

            # Delete lines, then insert
            delete_cmd = f"sed -i '' '{start_line},{end_line}d' \"{dst}\""
            insert_cmd = f"sed -i '' '{start_line - 1}r '{src}' \"{dst}\""

            code, _, stderr = self._run_shell(delete_cmd)
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Delete failed in {dst}: {stderr}",
                )

            code, _, stderr = self._run_shell(insert_cmd)
            if code != 0:
                return StepResult(
                    success=False,
                    output="\n".join(outputs),
                    error=f"Insert failed in {dst}: {stderr}",
                )

            outputs.append(f"✓ Replaced {dst}:{start_line}-{end_line} with {src}")

        return StepResult(
            success=True,
            output="\n".join(outputs),
            artifacts={"modified_files": [m["to"] for m in mappings]},
        )

    def _execute_validate(self, config: dict) -> StepResult:
        """Run validation checks."""
        checks = config.get("checks", [])

        outputs = []
        for check in checks:
            check_type = check.get("type", "py_compile")
            files = check.get("files", [])
            files = [self._resolve_vars(f) for f in files]

            if check_type == "py_compile":
                cmd = f"python3 -m py_compile {' '.join(files)}"
                code, stdout, stderr = self._run_shell(cmd)
                if code != 0:
                    return StepResult(
                        success=False,
                        output="\n".join(outputs),
                        error=f"py_compile failed: {stderr}",
                    )
                outputs.append(f"✓ py_compile passed for {len(files)} files")

            elif check_type == "exists":
                for f in files:
                    path = Path(self.working_dir) / f
                    if not path.exists():
                        return StepResult(
                            success=False,
                            output="\n".join(outputs),
                            error=f"File does not exist: {f}",
                        )
                outputs.append(f"✓ All {len(files)} files exist")

            elif check_type == "grep":
                pattern = check.get("pattern", "")
                for f in files:
                    cmd = f'grep -q "{pattern}" "{f}"'
                    code, _, _ = self._run_shell(cmd)
                    if code != 0:
                        return StepResult(
                            success=False,
                            output="\n".join(outputs),
                            error=f"Pattern '{pattern}' not found in {f}",
                        )
                outputs.append(f"✓ Pattern '{pattern}' found in all files")

            elif check_type == "shell":
                cmd = check.get("command", "")
                code, stdout, stderr = self._run_shell(cmd)
                if code != 0:
                    return StepResult(
                        success=False,
                        output="\n".join(outputs),
                        error=f"Shell check failed: {stderr}",
                    )
                outputs.append(f"✓ Shell check passed: {cmd[:50]}...")

        return StepResult(success=True, output="\n".join(outputs))

    def _execute_checkpoint(self, config: dict) -> StepResult:
        """Pause for user confirmation."""
        message = config.get("message", "Continue?")

        print(f"\n⏸️  CHECKPOINT: {message}")
        response = input("   Continue? [Y/n]: ").strip().lower()

        if response in ("", "y", "yes"):
            return StepResult(success=True, output="User confirmed: continue")
        return StepResult(
            success=False,
            output="User paused workflow",
            error="Paused by user",
        )

    def _execute_python(self, config: dict) -> StepResult:
        """Execute Python code or function."""
        code_str = config.get("code", "")

        # Create execution context with variables
        context = {"variables": self.variables, "working_dir": self.working_dir}

        try:
            exec(code_str, context)
            return StepResult(
                success=True,
                output=context.get("output", "Python executed successfully"),
                artifacts=context.get("artifacts", {}),
            )
        except Exception as e:
            return StepResult(success=False, error=f"Python error: {e}")


# =============================================================================
# DAG Runner
# =============================================================================


class DAGRunner:
    """Execute a workflow DAG."""

    def __init__(self, workflow_path: Path, working_dir: Path | None = None):
        self.workflow_path = workflow_path
        self.working_dir = working_dir or Path.cwd()
        self.workflow: dict = {}
        self.steps: dict[str, Step] = {}
        self.state: WorkflowState | None = None
        self.state_file: Path | None = None

    def load(self) -> None:
        """Load workflow definition from YAML."""
        with open(self.workflow_path) as f:
            self.workflow = yaml.safe_load(f)

        # Parse steps
        for step_def in self.workflow.get("steps", []):
            step = Step(
                id=step_def["id"],
                name=step_def.get("name", step_def["id"]),
                type=StepType(step_def["type"]),
                config=step_def.get("config", {}),
                depends_on=step_def.get("depends_on", []),
                checkpoint=step_def.get("checkpoint", False),
                continue_on_fail=step_def.get("continue_on_fail", False),
            )
            self.steps[step.id] = step

        # Initialize state
        workflow_id = self.workflow.get("id", self.workflow_path.stem)
        self.state_file = self.working_dir / f".workflow_state_{workflow_id}.json"

        if self.state_file.exists():
            self._load_state()
        else:
            self.state = WorkflowState(
                workflow_id=workflow_id,
                started_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                variables=self.workflow.get("variables", {}),
            )

    def _load_state(self) -> None:
        """Load persisted state."""
        with open(self.state_file) as f:
            data = json.load(f)
        self.state = WorkflowState(**data)

    def _save_state(self) -> None:
        """Persist current state."""
        if self.state and self.state_file:
            self.state.updated_at = datetime.now().isoformat()
            with open(self.state_file, "w") as f:
                json.dump(self.state.__dict__, f, indent=2)

    def _get_ready_steps(self) -> list[Step]:
        """Get steps that are ready to execute (all dependencies met)."""
        ready = []
        for step in self.steps.values():
            if step.status != StepStatus.PENDING:
                continue

            # Check all dependencies are completed
            deps_met = all(
                self.steps[dep].status == StepStatus.COMPLETED
                for dep in step.depends_on
                if dep in self.steps
            )

            if deps_met:
                ready.append(step)

        return ready

    def _topological_order(self) -> list[str]:
        """Get steps in topological order."""
        visited = set()
        order = []

        def visit(step_id: str):
            if step_id in visited:
                return
            visited.add(step_id)
            step = self.steps.get(step_id)
            if step:
                for dep in step.depends_on:
                    visit(dep)
                order.append(step_id)

        for step_id in self.steps:
            visit(step_id)

        return order

    def run(self, resume: bool = False) -> bool:
        """Execute the workflow DAG."""
        self.load()

        print(f"\n{'=' * 60}")
        print(f"WORKFLOW: {self.workflow.get('name', self.workflow_path.name)}")
        print(f"{'=' * 60}")

        # Mark completed steps if resuming
        if resume and self.state:
            for step_id in self.state.completed_steps:
                if step_id in self.steps:
                    self.steps[step_id].status = StepStatus.COMPLETED
                    print(f"  ↩️  Skipping (already done): {step_id}")

        # Get execution order
        execution_order = self._topological_order()

        # Create executor
        variables = {
            **self.workflow.get("variables", {}),
            **(self.state.variables if self.state else {}),
        }
        executor = StepExecutor(self.working_dir, variables)

        # Execute steps in order
        for step_id in execution_order:
            step = self.steps[step_id]

            if step.status == StepStatus.COMPLETED:
                continue

            # Check dependencies
            for dep in step.depends_on:
                if dep in self.steps and self.steps[dep].status != StepStatus.COMPLETED:
                    print(f"  ⏭️  Skipping {step_id}: dependency {dep} not completed")
                    step.status = StepStatus.SKIPPED
                    continue

            # Execute step
            print(f"\n{'─' * 40}")
            print(f"STEP: {step.name} [{step.type.value}]")
            print(f"{'─' * 40}")

            step.status = StepStatus.RUNNING
            if self.state:
                self.state.current_step = step_id
            self._save_state()

            result = executor.execute(step)
            step.result = result

            if result.output:
                print(result.output)

            if result.success:
                step.status = StepStatus.COMPLETED
                if self.state:
                    self.state.completed_steps.append(step_id)
                    self.state.artifacts.update(result.artifacts)
                print(f"\n✅ {step.name} completed ({result.duration_ms:.0f}ms)")
            else:
                step.status = StepStatus.FAILED
                if self.state:
                    self.state.failed_steps.append(step_id)
                print(f"\n❌ {step.name} failed: {result.error}")

                if not step.continue_on_fail:
                    self._save_state()
                    return False

            self._save_state()

            # Checkpoint pause
            if step.checkpoint and step.status == StepStatus.COMPLETED:
                checkpoint_result = executor._execute_checkpoint(
                    {"message": f"After {step.name}"}
                )
                if not checkpoint_result.success:
                    print("\n⏸️ Workflow paused by user")
                    return False

        # Final report
        self._print_summary()

        # Clean up state file on success
        if self.state_file and self.state_file.exists():
            all_completed = all(
                s.status == StepStatus.COMPLETED for s in self.steps.values()
            )
            if all_completed:
                self.state_file.unlink()

        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in self.steps.values()
        )

    def _print_summary(self) -> None:
        """Print workflow execution summary."""
        print(f"\n{'=' * 60}")
        print("WORKFLOW SUMMARY")
        print(f"{'=' * 60}")

        for step in self.steps.values():
            status_icon = {
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.PAUSED: "⏸️",
            }.get(step.status, "❓")

            duration = f"({step.result.duration_ms:.0f}ms)" if step.result else ""
            print(f"  {status_icon} {step.name} {duration}")

        print(f"{'=' * 60}\n")

    def validate(self) -> bool:
        """Validate workflow definition."""
        self.load()

        errors = []

        # Check for missing dependencies
        for step in self.steps.values():
            for dep in step.depends_on:
                if dep not in self.steps:
                    errors.append(f"Step '{step.id}' depends on unknown step '{dep}'")

        # Check for cycles (simple check)
        try:
            self._topological_order()
        except RecursionError:
            errors.append("Workflow contains a cycle")

        if errors:
            print("❌ Workflow validation failed:")
            for err in errors:
                print(f"   - {err}")
            return False

        print("✅ Workflow validation passed")
        print(f"   Steps: {len(self.steps)}")
        print(f"   Order: {' → '.join(self._topological_order())}")
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="L9 DAG Workflow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 dag_runner.py run workflow.yaml
    python3 dag_runner.py run workflow.yaml --working-dir /path/to/project
    python3 dag_runner.py resume workflow.yaml
    python3 dag_runner.py validate workflow.yaml
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute workflow")
    run_parser.add_argument("workflow", type=Path, help="Path to workflow YAML")
    run_parser.add_argument("--working-dir", "-w", type=Path, help="Working directory")

    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume interrupted workflow")
    resume_parser.add_argument("workflow", type=Path, help="Path to workflow YAML")
    resume_parser.add_argument(
        "--working-dir", "-w", type=Path, help="Working directory"
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate workflow definition"
    )
    validate_parser.add_argument("workflow", type=Path, help="Path to workflow YAML")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    working_dir = getattr(args, "working_dir", None) or Path.cwd()
    runner = DAGRunner(args.workflow, working_dir)

    if args.command == "validate":
        success = runner.validate()
    elif args.command == "run":
        success = runner.run(resume=False)
    elif args.command == "resume":
        success = runner.run(resume=True)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
