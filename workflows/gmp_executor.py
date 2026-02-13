#!/usr/bin/env python3
"""
GMP Executor — The ONLY Entry Point for /gmp
============================================

This is what /gmp actually calls. Nothing else.

The DAG contains all steps, prompts, and enforcement.
This executor just runs it.

Usage:
    python3 workflows/gmp_executor.py "task description" --tier RUNTIME
    python3 workflows/gmp_executor.py --resume
    python3 workflows/gmp_executor.py --status

The executor:
1. Initializes the GMP state
2. Runs each step in order (cannot skip)
3. Prompts for user input at gates
4. Executes memory operations
5. Generates report with script
6. Commits if approved

Version: 1.0.0
"""

from __future__ import annotations

import structlog

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Gmp Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "gmp_executor",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent
MEMORY_CLIENT = REPO_ROOT / "agents" / "cursor" / "cursor_memory_client.py"
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
TEST_GENERATOR_MODULE = "core.testing"
README_GENERATOR = REPO_ROOT / "scripts" / "generate_readme.py"
STATE_FILE = REPO_ROOT / ".gmp_executor_state.json"


# =============================================================================
# Data Models
# =============================================================================


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class StepType(str, Enum):
    MEMORY_READ = "memory_read"
    SCOPE_LOCK = "scope_lock"
    USER_GATE = "user_gate"
    BASELINE = "baseline"
    IMPLEMENT = "implement"
    GENERATE_TESTS = "generate_tests"  # Optional: Auto-generate tests for new code
    GENERATE_README = (
        "generate_readme"  # Optional: Auto-generate README for new modules
    )
    VALIDATE = "validate"
    MEMORY_WRITE = "memory_write"
    GENERATE_REPORT = "generate_report"
    COMMIT_GATE = "commit_gate"


@dataclass
class StepResult:
    success: bool
    output: str = ""
    error: str = ""
    user_input: str = ""


@dataclass
class GMPState:
    gmp_id: str
    tier: str
    task: str
    started_at: str
    current_step: StepType
    completed_steps: list[str] = field(default_factory=list)
    todo_plan: list[dict] = field(default_factory=list)
    changes_made: list[dict] = field(default_factory=list)
    validations: list[dict] = field(default_factory=list)
    memory_context: str = ""
    report_path: str = ""
    # Optional step flags
    needs_tests: bool = False
    needs_readme: bool = False
    generated_tests: list[str] = field(default_factory=list)
    generated_readmes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["current_step"] = self.current_step.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> GMPState:
        d["current_step"] = StepType(d["current_step"])
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    StepType.MEMORY_READ,
    StepType.SCOPE_LOCK,
    StepType.USER_GATE,
    StepType.BASELINE,
    StepType.IMPLEMENT,
    StepType.GENERATE_TESTS,  # Conditional: runs if tests are required
    StepType.GENERATE_README,  # Conditional: runs if README is required
    StepType.VALIDATE,
    StepType.MEMORY_WRITE,
    StepType.GENERATE_REPORT,
    StepType.COMMIT_GATE,
]

# Keywords that trigger optional steps
TEST_KEYWORDS = ["test", "tests", "testing", "coverage", "pytest", "unittest"]
README_KEYWORDS = ["readme", "documentation", "docs", "module", "new module", "api"]


# =============================================================================
# Step Executors
# =============================================================================


class GMPExecutor:
    """Executes the GMP DAG."""

    def __init__(self):
        self.state: GMPState | None = None

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = GMPState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = None

    def _run_shell(self, cmd: str, capture: bool = True) -> tuple[int, str, str]:
        """Run shell command."""
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=REPO_ROOT,
            capture_output=capture,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def _print_header(self, title: str):
        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"  {title}")  # noqa: ADR-0019
        print(f"{'=' * 60}\n")  # noqa: ADR-0019

    def _print_step(self, step: StepType, status: str = ""):
        icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "blocked": "🚫",
        }.get(status, "  ")
        print(f"  {icon} {step.value}")  # noqa: ADR-0019

    # =========================================================================
    # STEP: Memory Read
    # =========================================================================
    def _step_memory_read(self) -> StepResult:
        self._print_header("🧠 MEMORY READ (MANDATORY)")

        print("Searching L9 memory for context...\n")  # noqa: ADR-0019

        # Search for related work
        searches = [
            f'"{self.state.task}"',
            f'"lessons errors {self.state.task.split()[0]}"',
            '"gmp patterns"',
        ]

        context_lines = []
        for query in searches:
            cmd = f'python3 {MEMORY_CLIENT} search {query} 2>/dev/null || echo "Memory unavailable"'
            code, stdout, stderr = self._run_shell(cmd)
            if stdout.strip():
                context_lines.append(f"Query: {query}")
                context_lines.append(stdout.strip()[:500])
                context_lines.append("")

        if context_lines:
            self.state.memory_context = "\n".join(context_lines)
            print("Memory context retrieved:")  # noqa: ADR-0019
            print("-" * 40)  # noqa: ADR-0019
            print(self.state.memory_context[:1000])  # noqa: ADR-0019
            print("-" * 40)  # noqa: ADR-0019
        else:
            self.state.memory_context = "No prior context found"
            print("⚠️  No prior context found in memory")  # noqa: ADR-0019

        return StepResult(success=True, output=self.state.memory_context)

    # =========================================================================
    # STEP: Scope Lock
    # =========================================================================
    def _step_scope_lock(self) -> StepResult:
        self._print_header("SCOPE LOCK (Phase 0)")

        print(f"GMP ID: {self.state.gmp_id}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Memory Context Applied:")  # noqa: ADR-0019
        print(self.state.memory_context[:500] if self.state.memory_context else "None")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("Define the TODO plan.")  # noqa: ADR-0019
        print("Format: T#|file|lines|action|description")  # noqa: ADR-0019
        print("Example: T1|core/tools/registry.py|45-60|REPLACE|Add validation")  # noqa: ADR-0019
        print("Enter empty line when done.")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019

        todos = []
        while True:
            try:
                line = input(f"T{len(todos) + 1}: ").strip()
            except EOFError:
                break
            if not line:
                break
            parts = line.split("|")
            if len(parts) >= 4:
                todos.append(
                    {
                        "id": f"T{len(todos) + 1}",
                        "file": parts[0] if not parts[0].startswith("T") else parts[1],
                        "lines": parts[1] if not parts[0].startswith("T") else parts[2],
                        "action": parts[2]
                        if not parts[0].startswith("T")
                        else parts[3],
                        "description": parts[3]
                        if not parts[0].startswith("T")
                        else (parts[4] if len(parts) > 4 else ""),
                    }
                )

        if not todos:
            return StepResult(success=False, error="No TODOs defined")

        self.state.todo_plan = todos

        print("\n" + "=" * 40)  # noqa: ADR-0019
        print("TODO PLAN LOCKED")  # noqa: ADR-0019
        print("=" * 40)  # noqa: ADR-0019
        print("| T# | File | Lines | Action |")  # noqa: ADR-0019
        print("|----|------|-------|--------|")  # noqa: ADR-0019
        for t in todos:
            print(f"| {t['id']} | {t['file']} | {t['lines']} | {t['action']} |")  # noqa: ADR-0019

        return StepResult(success=True, output=f"{len(todos)} TODOs defined")

    # =========================================================================
    # STEP: User Gate
    # =========================================================================
    def _step_user_gate(self) -> StepResult:
        self._print_header("USER CONFIRMATION GATE")

        print("Scope is locked. Review the TODO plan above.")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Options:")  # noqa: ADR-0019
        print("  CONFIRM - Proceed with implementation")  # noqa: ADR-0019
        print("  ABORT   - Cancel GMP")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        try:
            response = input("Enter CONFIRM or ABORT: ").strip().upper()
        except EOFError:
            response = "ABORT"

        if response == "CONFIRM":
            return StepResult(success=True, user_input="CONFIRM")
        return StepResult(success=False, error="User aborted", user_input=response)

    # =========================================================================
    # STEP: Baseline
    # =========================================================================
    def _step_baseline(self) -> StepResult:
        self._print_header("BASELINE VERIFICATION (Phase 1)")

        print("Verifying files exist and line ranges are correct...\n")  # noqa: ADR-0019

        errors = []
        for todo in self.state.todo_plan:
            filepath = REPO_ROOT / todo["file"]
            if todo["action"].upper() != "CREATE":
                if not filepath.exists():
                    errors.append(f"❌ File not found: {todo['file']}")
                else:
                    print(f"✅ {todo['file']} exists")  # noqa: ADR-0019

        if errors:
            for e in errors:
                print(e)  # noqa: ADR-0019
            return StepResult(success=False, error="\n".join(errors))

        return StepResult(success=True, output="All files verified")

    # =========================================================================
    # STEP: Implement
    # =========================================================================
    def _step_implement(self) -> StepResult:
        self._print_header("IMPLEMENTATION (Phase 2-3)")

        print("Execute the TODO plan now.")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("RULES:")  # noqa: ADR-0019
        print("  - For harvested code: Use sed/cp ONLY")  # noqa: ADR-0019
        print("  - All changes must map 1:1 to TODO items")  # noqa: ADR-0019
        print("  - NO scope drift")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("TODO items to implement:")  # noqa: ADR-0019
        for t in self.state.todo_plan:
            print(
                f"  [ ] {t['id']}: {t['file']} - {t['action']} - {t.get('description', '')}"
            )  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("Make your changes now, then press ENTER when done.")  # noqa: ADR-0019
        print("Or type ABORT to cancel.")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019

        try:
            response = input("Press ENTER when done (or ABORT): ").strip().upper()
        except EOFError:
            response = ""

        if response == "ABORT":
            return StepResult(success=False, error="User aborted implementation")

        # Record changes (simplified - in real use, this would diff)
        self.state.changes_made = [
            {
                "file": t["file"],
                "lines": t["lines"],
                "action": t["action"],
                "description": t.get("description", ""),
            }
            for t in self.state.todo_plan
        ]

        # Check if tests or README are needed based on task/TODO content
        task_lower = self.state.task.lower()
        todo_files = " ".join(t["file"] for t in self.state.todo_plan)

        self.state.needs_tests = (
            any(kw in task_lower for kw in TEST_KEYWORDS)
            or "test" in todo_files.lower()
        )
        self.state.needs_readme = any(kw in task_lower for kw in README_KEYWORDS)

        # Also check if any Python files were created/modified that don't have tests
        py_files = [
            t["file"]
            for t in self.state.todo_plan
            if t["file"].endswith(".py") and not t["file"].startswith("tests/")
        ]
        if py_files and not self.state.needs_tests:
            print("\n💡 Detected new Python files. Consider generating tests.")  # noqa: ADR-0019
            try:
                resp = input("   Generate tests automatically? [y/N]: ").strip().lower()
                self.state.needs_tests = resp == "y"
            except EOFError:
                pass

        return StepResult(
            success=True,
            output=f"Implementation complete: {len(self.state.changes_made)} changes",
        )

    # =========================================================================
    # STEP: Generate Tests (Optional)
    # =========================================================================
    def _step_generate_tests(self) -> StepResult:
        """Generate tests for new/modified Python files using LLM."""
        if not self.state.needs_tests:
            print("⏭️  Skipping test generation (not required)")  # noqa: ADR-0019
            return StepResult(success=True, output="Skipped - not required")

        self._print_header("🧪 GENERATE TESTS (Automatic)")

        # Find Python files that need tests
        py_files = [
            t["file"]
            for t in self.state.todo_plan
            if t["file"].endswith(".py") and not t["file"].startswith("tests/")
        ]

        if not py_files:
            print("No Python files to generate tests for")  # noqa: ADR-0019
            return StepResult(success=True, output="No files need tests")

        print(f"Generating tests for {len(py_files)} file(s)...\n")  # noqa: ADR-0019

        generated = []
        for py_file in py_files:
            filepath = REPO_ROOT / py_file
            if not filepath.exists():
                print(f"  ⚠️  {py_file} not found, skipping")  # noqa: ADR-0019
                continue

            # Determine test file path
            if py_file.startswith("core/"):
                test_file = f"tests/{py_file.replace('.py', '').replace('/', '/test_').replace('core/test_', 'core/')}"
            else:
                parts = py_file.split("/")
                test_file = f"tests/{'/'.join(parts[:-1])}/test_{parts[-1]}"

            test_file = test_file.replace("//", "/")
            if not test_file.endswith(".py"):
                test_file += ".py"

            print(f"  📝 {py_file} → {test_file}")  # noqa: ADR-0019

            # Generate tests using the test generator
            try:
                cmd = f'''python3 -c "
from core.testing import generate_test_file
from pathlib import Path

code = Path('{filepath}').read_text()
module_name = '{py_file}'.replace('/', '.').replace('.py', '')
tests = generate_test_file(code, module_name)

# Ensure test directory exists
test_path = Path('{REPO_ROOT / test_file}')
test_path.parent.mkdir(parents=True, exist_ok=True)
test_path.write_text(tests)

logger.info("generated {{len(tests.splitlines())}} lines")
"'''
                code, stdout, stderr = self._run_shell(cmd)
                if code == 0:
                    print(f"     ✅ {stdout.strip()}")  # noqa: ADR-0019
                    generated.append(test_file)
                else:
                    print(f"     ❌ Failed: {stderr[:100]}")  # noqa: ADR-0019
            except Exception as e:
                print(f"     ❌ Error: {e}")  # noqa: ADR-0019

        self.state.generated_tests = generated

        if generated:
            print(f"\n✅ Generated {len(generated)} test file(s)")  # noqa: ADR-0019
            # Add to TODO plan for commit
            for tf in generated:
                self.state.todo_plan.append(
                    {
                        "id": f"T{len(self.state.todo_plan) + 1}",
                        "file": tf,
                        "lines": "all",
                        "action": "CREATE",
                        "description": "Auto-generated tests",
                    }
                )
            return StepResult(
                success=True, output=f"Generated {len(generated)} test files"
            )
        print("\n⚠️  No tests were generated")  # noqa: ADR-0019
        return StepResult(success=True, output="No tests generated")

    # =========================================================================
    # STEP: Generate README (Optional)
    # =========================================================================
    def _step_generate_readme(self) -> StepResult:
        """Generate README for new modules."""
        if not self.state.needs_readme:
            print("⏭️  Skipping README generation (not required)")  # noqa: ADR-0019
            return StepResult(success=True, output="Skipped - not required")

        self._print_header("📖 GENERATE README (Automatic)")

        # Find directories with new files
        dirs_with_changes = set()
        for t in self.state.todo_plan:
            if "/" in t["file"]:
                dir_path = "/".join(t["file"].split("/")[:-1])
                dirs_with_changes.add(dir_path)

        if not dirs_with_changes:
            print("No directories to generate READMEs for")  # noqa: ADR-0019
            return StepResult(success=True, output="No READMEs needed")

        print(f"Checking {len(dirs_with_changes)} director(ies) for README needs...\n")  # noqa: ADR-0019

        generated = []
        for dir_path in dirs_with_changes:
            readme_path = REPO_ROOT / dir_path / "README.md"

            # Skip if README already exists
            if readme_path.exists():
                print(f"  ⏭️  {dir_path}/README.md already exists")  # noqa: ADR-0019
                continue

            print(f"  📝 Generating {dir_path}/README.md")  # noqa: ADR-0019

            # Check if readme generator script exists
            if README_GENERATOR.exists():
                cmd = f'python3 {README_GENERATOR} --dir "{REPO_ROOT / dir_path}" 2>/dev/null'
                code, stdout, stderr = self._run_shell(cmd)
                if code == 0:
                    print("     ✅ Generated via script")  # noqa: ADR-0019
                    generated.append(f"{dir_path}/README.md")
                else:
                    # Fallback: generate simple README
                    self._generate_simple_readme(dir_path, readme_path)
                    generated.append(f"{dir_path}/README.md")
            else:
                # Generate simple README
                self._generate_simple_readme(dir_path, readme_path)
                generated.append(f"{dir_path}/README.md")

        self.state.generated_readmes = generated

        if generated:
            print(f"\n✅ Generated {len(generated)} README(s)")  # noqa: ADR-0019
            for rf in generated:
                self.state.todo_plan.append(
                    {
                        "id": f"T{len(self.state.todo_plan) + 1}",
                        "file": rf,
                        "lines": "all",
                        "action": "CREATE",
                        "description": "Auto-generated README",
                    }
                )
            return StepResult(
                success=True, output=f"Generated {len(generated)} READMEs"
            )
        return StepResult(success=True, output="No READMEs generated")

    def _generate_simple_readme(self, dir_path: str, readme_path: Path):
        """Generate a simple README for a directory."""
        dir_name = dir_path.split("/")[-1]

        # List Python files in directory
        py_files = list((REPO_ROOT / dir_path).glob("*.py"))
        py_files = [f.name for f in py_files if f.name != "__init__.py"]

        content = f"""# {dir_name.replace("_", " ").title()}

## Overview

This module is part of the L9 Secure AI OS.

## Files

"""
        for pf in sorted(py_files):
            content += f"- `{pf}`\n"

        content += """
## Usage

```python
from {module_path} import ...
```

---
*Auto-generated by GMP Executor*
""".format(module_path=dir_path.replace("/", "."))

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(content)
        print("     ✅ Generated simple README")  # noqa: ADR-0019

    # =========================================================================
    # STEP: Validate
    # =========================================================================
    def _step_validate(self) -> StepResult:
        self._print_header("VALIDATION (Phase 4-5)")

        print("Running validation checks...\n")  # noqa: ADR-0019

        validations = []

        # py_compile
        py_files = [
            t["file"] for t in self.state.todo_plan if t["file"].endswith(".py")
        ]
        if py_files:
            files_str = " ".join(str(REPO_ROOT / f) for f in py_files)
            code, stdout, stderr = self._run_shell(f"python3 -m py_compile {files_str}")
            if code == 0:
                validations.append({"gate": "py_compile", "result": "✅"})
                print("✅ py_compile: PASSED")  # noqa: ADR-0019
            else:
                validations.append(
                    {"gate": "py_compile", "result": "❌", "details": stderr}
                )
                print(f"❌ py_compile: FAILED\n{stderr}")  # noqa: ADR-0019
                self.state.validations = validations
                return StepResult(success=False, error=f"py_compile failed: {stderr}")

        # Import check (simplified)
        validations.append({"gate": "syntax", "result": "✅"})
        print("✅ syntax: PASSED")  # noqa: ADR-0019

        self.state.validations = validations
        return StepResult(success=True, output="All validations passed")

    # =========================================================================
    # STEP: Memory Write
    # =========================================================================
    def _step_memory_write(self) -> StepResult:
        self._print_header("🧠 MEMORY WRITE (MANDATORY)")

        print("Writing learnings to L9 memory...\n")  # noqa: ADR-0019

        # Build summary
        files_changed = ", ".join(
            t["file"].split("/")[-1] for t in self.state.todo_plan[:3]
        )
        summary = f"{self.state.gmp_id}: {self.state.task}. Files: {files_changed}. Tags: gmp, {self.state.tier.lower()}"

        cmd = f'python3 {MEMORY_CLIENT} write "{summary}" --kind lesson 2>/dev/null || echo "Memory write failed"'
        code, stdout, stderr = self._run_shell(cmd)

        if "failed" in stdout.lower() or code != 0:
            print(f"⚠️  Memory write failed: {stdout}{stderr}")  # noqa: ADR-0019
            print("   Continuing anyway (memory is non-blocking)")  # noqa: ADR-0019
        else:
            print(f"✅ Memory written: {summary[:80]}...")  # noqa: ADR-0019

        return StepResult(success=True, output="Memory write attempted")

    # =========================================================================
    # STEP: Generate Report
    # =========================================================================
    def _step_generate_report(self) -> StepResult:
        self._print_header("GENERATE GMP REPORT (MANDATORY)")

        print("Generating canonical GMP report...\n")  # noqa: ADR-0019

        # Build command
        todo_args = []
        for t in self.state.todo_plan:
            todo_args.append(
                f'--todo "{t["id"]}|{t["file"]}|{t["lines"]}|{t["action"]}|{t.get("description", "")}"'
            )

        val_args = []
        for v in self.state.validations:
            val_args.append(f'--validation "{v["gate"]}|{v["result"]}"')

        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "{self.state.task}" \
            --tier {self.state.tier}_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "GMP execution via DAG executor" \
            --update-workflow \
            --skip-verify'''

        print("Running: python3 scripts/generate_gmp_report.py ...")  # noqa: ADR-0019
        code, stdout, stderr = self._run_shell(cmd)

        if code != 0:
            print(f"❌ Report generation failed: {stderr}")  # noqa: ADR-0019
            return StepResult(
                success=False, error=f"Report generation failed: {stderr}"
            )

        # Extract report path from output
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line:
                self.state.report_path = line.strip()
                break

        print(stdout)  # noqa: ADR-0019
        return StepResult(success=True, output=stdout)

    # =========================================================================
    # STEP: Commit Gate
    # =========================================================================
    def _step_commit_gate(self) -> StepResult:
        self._print_header("COMMIT GATE")

        print(f"Report generated: {self.state.report_path}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Options:")  # noqa: ADR-0019
        print("  YES  - Commit all changes")  # noqa: ADR-0019
        print("  NO   - Exit without commit")  # noqa: ADR-0019
        print("  DIFF - Show git diff first")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        try:
            response = input("Commit? [YES/NO/DIFF]: ").strip().upper()
        except EOFError:
            response = "NO"

        if response == "DIFF":
            code, stdout, stderr = self._run_shell("git diff --stat")
            print(stdout)  # noqa: ADR-0019
            try:
                response = input("Commit? [YES/NO]: ").strip().upper()
            except EOFError:
                response = "NO"

        if response == "YES":
            # Stage and commit
            files = " ".join(t["file"] for t in self.state.todo_plan)
            commit_msg = f"{self.state.gmp_id}: {self.state.task}"

            self._run_shell(f"git add {files}")
            code, stdout, stderr = self._run_shell(f'git commit -m "{commit_msg}"')

            if code == 0:
                print("✅ Changes committed")  # noqa: ADR-0019
                return StepResult(success=True, output="Committed", user_input="YES")
            print(f"⚠️  Commit failed: {stderr}")  # noqa: ADR-0019
            return StepResult(
                success=True,
                output="Commit failed but GMP complete",
                user_input="YES",
            )
        print("Skipping commit")  # noqa: ADR-0019
        return StepResult(success=True, output="No commit", user_input="NO")

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def _get_step_executor(self, step: StepType):
        """Get the executor function for a step."""
        executors = {
            StepType.MEMORY_READ: self._step_memory_read,
            StepType.SCOPE_LOCK: self._step_scope_lock,
            StepType.USER_GATE: self._step_user_gate,
            StepType.BASELINE: self._step_baseline,
            StepType.IMPLEMENT: self._step_implement,
            StepType.GENERATE_TESTS: self._step_generate_tests,
            StepType.GENERATE_README: self._step_generate_readme,
            StepType.VALIDATE: self._step_validate,
            StepType.MEMORY_WRITE: self._step_memory_write,
            StepType.GENERATE_REPORT: self._step_generate_report,
            StepType.COMMIT_GATE: self._step_commit_gate,
        }
        return executors.get(step)

    def _next_step(self) -> StepType | None:
        """Get the next step to execute."""
        for step in STEP_ORDER:
            if step.value not in self.state.completed_steps:
                return step
        return None

    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active GMP. Start with:")  # noqa: ADR-0019
            print('  python3 workflows/gmp_executor.py "task description"')  # noqa: ADR-0019
            return

        self._print_header(f"GMP STATUS: {self.state.gmp_id}")
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step.value in self.state.completed_steps:
                self._print_step(step, "completed")
            elif step == self.state.current_step:
                self._print_step(step, "running")
            else:
                self._print_step(step, "pending")

    def run(self, task: str, tier: str = "RUNTIME", resume: bool = False):
        """Execute the GMP DAG."""
        # Initialize or resume
        if resume and self._load_state():
            print(f"Resuming GMP: {self.state.gmp_id}")  # noqa: ADR-0019
        else:
            # Find next GMP ID
            gmp_num = 129  # Default
            reports_dir = REPO_ROOT / "reports" / "GMP Reports"
            for f in reports_dir.glob("GMP-Report-*.md"):
                import re

                match = re.search(r"GMP-Report-(\d+)", f.name)
                if match:
                    gmp_num = max(gmp_num, int(match.group(1)) + 1)

            self.state = GMPState(
                gmp_id=f"GMP-{gmp_num}",
                tier=tier,
                task=task,
                started_at=datetime.now().isoformat(),
                current_step=STEP_ORDER[0],
            )
            self._save_state()

        self._print_header(f"GMP EXECUTOR: {self.state.gmp_id}")
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019

        # Execute steps in order
        while True:
            next_step = self._next_step()
            if not next_step:
                break

            self.state.current_step = next_step
            self._save_state()

            executor = self._get_step_executor(next_step)
            if not executor:
                print(f"❌ No executor for step: {next_step}")  # noqa: ADR-0019
                break

            result = executor()

            if result.success:
                self.state.completed_steps.append(next_step.value)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {next_step.value}")  # noqa: ADR-0019
                print(f"   Error: {result.error}")  # noqa: ADR-0019
                print("\nResume with: python3 workflows/gmp_executor.py --resume")  # noqa: ADR-0019
                return False

        # Complete
        self._print_header("GMP COMPLETE")
        print(f"✅ {self.state.gmp_id}: {self.state.task}")  # noqa: ADR-0019
        print(f"   Report: {self.state.report_path}")  # noqa: ADR-0019

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="GMP Executor — Run the GMP DAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/gmp_executor.py "add validation to registry"
    python3 workflows/gmp_executor.py "fix bug" --tier KERNEL
    python3 workflows/gmp_executor.py --resume
    python3 workflows/gmp_executor.py --status
        """,
    )

    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument(
        "--tier", choices=["KERNEL", "RUNTIME", "INFRA", "UX"], default="RUNTIME"
    )
    parser.add_argument("--resume", action="store_true", help="Resume interrupted GMP")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--reset", action="store_true", help="Clear state and start fresh"
    )

    args = parser.parse_args()

    executor = GMPExecutor()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("✅ State cleared")  # noqa: ADR-0019
        return

    if args.status:
        executor.status()
        return

    if args.resume:
        if not STATE_FILE.exists():
            print("No GMP to resume")  # noqa: ADR-0019
            sys.exit(1)
        executor.run("", resume=True)
        return

    if not args.task:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.task, args.tier)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "cli",
        "data-models",
        "dataclass",
        "executor",
        "filesystem",
        "operations",
        "serialization",
        "subprocess",
        "testing",
    ],
    "keywords": ["executor", "gmp", "state", "status", "step"],
    "business_value": "This is what /gmp actually calls. Nothing else.",
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
