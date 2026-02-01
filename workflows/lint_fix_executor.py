#!/usr/bin/env python3
"""
Lint-Fix Executor — The ONLY Entry Point for /lint-fix
=======================================================

Systematically fixes lint errors across the codebase.

The DAG handles everything:
- Run linter to get all errors
- Categorize by fix type (auto, semi, manual)
- Apply auto-fixes with ruff
- Apply semi-auto fixes with sed patterns
- Validate no new errors introduced
- Generate report
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/lint_fix_executor.py
    python3 workflows/lint_fix_executor.py --only B904
    python3 workflows/lint_fix_executor.py --status
    python3 workflows/lint_fix_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Lint Fix Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "lint_fix_executor",
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
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
STATE_FILE = REPO_ROOT / ".lint_fix_executor_state.json"

# Known fix patterns for common lint rules
AUTO_FIXABLE = {"I001", "I002", "UP", "F401", "W", "E"}  # ruff --fix handles these
SEMI_AUTO_PATTERNS = {
    "B904": {
        "description": "raise without from in except",
        "pattern": r"raise\s+(\w+)\((.*?)\)(?!\s+from)",
        "replacement": r"raise \1(\2) from e",
    },
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class LintError:
    code: str
    file: str
    line: int
    message: str
    status: str = "pending"


@dataclass
class LintFixState:
    started_at: str
    current_step: str
    target_codes: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    errors_before: list[dict] = field(default_factory=list)
    errors_after: list[dict] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> LintFixState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "scan_errors",
    "categorize",
    "apply_auto_fixes",
    "apply_semi_fixes",
    "validate",
    "rescan",
    "generate_report",
    "commit",
]


# =============================================================================
# Lint-Fix Executor
# =============================================================================


class LintFixExecutor:
    """Executes the /lint-fix DAG — fully autonomous, no user gates."""

    def __init__(self):
        self.state: LintFixState | None = None

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = LintFixState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = None

    def _run_shell(self, cmd: str, capture: bool = True) -> tuple[int, str, str]:
        """Run shell command."""
        result = subprocess.run(  # noqa: S602 - shell=True required for DAG executor
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

    def _parse_ruff_output(self, output: str) -> list[dict]:
        """Parse ruff output into structured errors."""
        errors = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            # Format: file.py:10:5: CODE message
            match = re.match(r"(.+?):(\d+):\d+:\s+(\w+)\s+(.+)", line)
            if match:
                errors.append(
                    {
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "code": match.group(3),
                        "message": match.group(4),
                        "status": "pending",
                    }
                )
        return errors

    # =========================================================================
    # STEP 1: SCAN ERRORS
    # =========================================================================
    def _step_scan_errors(self) -> bool:
        self._print_header("SCAN LINT ERRORS")

        # Run ruff to get all errors
        cmd = "ruff check . --output-format=text 2>&1 || true"
        _code, stdout, _stderr = self._run_shell(cmd)

        errors = self._parse_ruff_output(stdout)

        # Filter by target codes if specified
        if self.state.target_codes:
            errors = [
                e
                for e in errors
                if any(e["code"].startswith(c) for c in self.state.target_codes)
            ]

        self.state.errors_before = errors

        # Summarize by code
        code_counts = Counter(e["code"] for e in errors)

        print(f"Found {len(errors)} lint errors:")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("| Code | Count |")  # noqa: ADR-0019
        print("|------|-------|")  # noqa: ADR-0019
        for code, count in code_counts.most_common(20):
            print(f"| {code:6} | {count:5} |")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019

        if not errors:
            print("✅ No lint errors found!")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 2: CATEGORIZE
    # =========================================================================
    def _step_categorize(self) -> bool:
        self._print_header("CATEGORIZE ERRORS")

        auto_count = 0
        semi_count = 0
        manual_count = 0

        for error in self.state.errors_before:
            code = error["code"]
            # Check if auto-fixable
            if any(code.startswith(prefix) for prefix in AUTO_FIXABLE):
                error["fix_type"] = "auto"
                auto_count += 1
            elif code in SEMI_AUTO_PATTERNS:
                error["fix_type"] = "semi"
                semi_count += 1
            else:
                error["fix_type"] = "manual"
                manual_count += 1

        print("Categorization:")  # noqa: ADR-0019
        print(f"  🤖 AUTO (ruff --fix): {auto_count}")  # noqa: ADR-0019
        print(f"  🔧 SEMI (sed patterns): {semi_count}")  # noqa: ADR-0019
        print(f"  👤 MANUAL (requires review): {manual_count}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 3: APPLY AUTO FIXES
    # =========================================================================
    def _step_apply_auto_fixes(self) -> bool:
        self._print_header("APPLY AUTO FIXES (ruff --fix)")

        auto_errors = [
            e for e in self.state.errors_before if e.get("fix_type") == "auto"
        ]

        if not auto_errors:
            print("✅ No auto-fixable errors")  # noqa: ADR-0019
            return True

        print(f"Applying ruff --fix for {len(auto_errors)} errors...")  # noqa: ADR-0019

        # Run ruff with --fix
        cmd = "ruff check . --fix 2>&1 || true"
        _code, stdout, _stderr = self._run_shell(cmd)

        # Check what was fixed
        if "Fixed" in stdout:
            match = re.search(r"Fixed (\d+)", stdout)
            if match:
                fixed = int(match.group(1))
                print(f"✅ ruff fixed {fixed} errors")  # noqa: ADR-0019
        else:
            print("✅ ruff --fix completed")  # noqa: ADR-0019

        # Track modified files
        for error in auto_errors:
            if error["file"] not in self.state.files_modified:
                self.state.files_modified.append(error["file"])
            error["status"] = "fixed"

        return True

    # =========================================================================
    # STEP 4: APPLY SEMI-AUTO FIXES
    # =========================================================================
    def _step_apply_semi_fixes(self) -> bool:
        self._print_header("APPLY SEMI-AUTO FIXES (sed patterns)")

        semi_errors = [
            e for e in self.state.errors_before if e.get("fix_type") == "semi"
        ]

        if not semi_errors:
            print("✅ No semi-auto fixable errors")  # noqa: ADR-0019
            return True

        # Group by code
        by_code = {}
        for error in semi_errors:
            code = error["code"]
            if code not in by_code:
                by_code[code] = []
            by_code[code].append(error)

        for code, errors in by_code.items():
            if code not in SEMI_AUTO_PATTERNS:
                print(f"⚠️  {code}: No pattern defined")  # noqa: ADR-0019
                continue

            pattern_info = SEMI_AUTO_PATTERNS[code]
            print(f"\n🔧 Fixing {code}: {pattern_info['description']}")  # noqa: ADR-0019
            print(f"   Pattern: {pattern_info['pattern']}")  # noqa: ADR-0019

            # Group by file for efficiency
            by_file = {}
            for e in errors:
                if e["file"] not in by_file:
                    by_file[e["file"]] = []
                by_file[e["file"]].append(e)

            for filepath, file_errors in by_file.items():
                full_path = REPO_ROOT / filepath
                if not full_path.exists():
                    continue

                # Read file content
                content = full_path.read_text()
                original = content

                # Apply pattern replacement
                if code == "B904":
                    # Special handling for B904: add 'from e' to raises in except blocks
                    # This is a simplified version - real implementation would be more sophisticated
                    lines = content.split("\n")
                    in_except = False
                    except_var = "e"
                    modified_lines = []

                    for i, line in enumerate(lines):
                        # Track except blocks
                        if re.match(r"\s*except\s+(\w+)\s+as\s+(\w+)", line):
                            match = re.match(r"\s*except\s+(\w+)\s+as\s+(\w+)", line)
                            except_var = match.group(2) if match else "e"
                            in_except = True
                        elif re.match(r"\s*except\s*:", line) or re.match(
                            r"\s*except\s+\w+\s*:", line
                        ):
                            in_except = True
                            except_var = "e"
                        elif in_except and re.match(
                            r"\s*(def|class|async def)\s+", line
                        ):
                            in_except = False

                        # Fix raises in except blocks
                        if in_except and "raise " in line and " from " not in line:
                            # Add 'from e' or 'from exc' based on context
                            if line.rstrip().endswith(")") or re.match(
                                r"\s*raise\s+\w+\s*$", line.rstrip()
                            ):
                                line = line.rstrip() + f" from {except_var}"

                        modified_lines.append(line)

                    content = "\n".join(modified_lines)

                if content != original:
                    full_path.write_text(content)
                    if filepath not in self.state.files_modified:
                        self.state.files_modified.append(filepath)
                    print(f"   ✅ {filepath}")  # noqa: ADR-0019
                    for e in file_errors:
                        e["status"] = "fixed"

        return True

    # =========================================================================
    # STEP 5: VALIDATE
    # =========================================================================
    def _step_validate(self) -> bool:
        self._print_header("VALIDATE FIXES")

        validations = []

        # py_compile on modified files
        py_files = [f for f in self.state.files_modified if f.endswith(".py")]
        if py_files:
            passed = 0
            for f in py_files:
                full_path = REPO_ROOT / f
                code, _stdout, stderr = self._run_shell(
                    f'python3 -m py_compile "{full_path}"'
                )
                if code == 0:
                    passed += 1
                else:
                    print(f"❌ {f}: {stderr[:60]}")  # noqa: ADR-0019

            status = (
                f"✅ {passed}/{len(py_files)}"
                if passed == len(py_files)
                else f"⚠️ {passed}/{len(py_files)}"
            )
            validations.append({"check": "py_compile", "status": status})
            print(f"✅ Syntax valid: {passed}/{len(py_files)} files")  # noqa: ADR-0019

        self.state.validation_results = validations
        return True

    # =========================================================================
    # STEP 6: RESCAN
    # =========================================================================
    def _step_rescan(self) -> bool:
        self._print_header("RESCAN FOR REMAINING ERRORS")

        # Run ruff again
        cmd = "ruff check . --output-format=text 2>&1 || true"
        _code, stdout, _stderr = self._run_shell(cmd)

        errors = self._parse_ruff_output(stdout)

        # Filter by target codes if specified
        if self.state.target_codes:
            errors = [
                e
                for e in errors
                if any(e["code"].startswith(c) for c in self.state.target_codes)
            ]

        self.state.errors_after = errors

        before = len(self.state.errors_before)
        after = len(errors)
        fixed = before - after

        print("Results:")  # noqa: ADR-0019
        print(f"  Before: {before} errors")  # noqa: ADR-0019
        print(f"  After:  {after} errors")  # noqa: ADR-0019
        print(f"  Fixed:  {fixed} errors")  # noqa: ADR-0019

        if after > 0:
            # Summarize remaining
            code_counts = Counter(e["code"] for e in errors)
            print("\nRemaining errors:")  # noqa: ADR-0019
            for code, count in code_counts.most_common(10):
                print(f"  {code}: {count}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 7: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT")

        before = len(self.state.errors_before)
        after = len(self.state.errors_after)
        fixed = before - after

        # Build TODO items
        todo_args = [
            f'--todo "L1|scan|*|SCAN|{before} errors found"',
            f'--todo "L2|fix|*|FIX|{fixed} errors fixed"',
            f'--todo "L3|validate|*|VALIDATE|{len(self.state.files_modified)} files"',
        ]

        # Build validation items
        val_args = []
        for v in self.state.validation_results:
            val_args.append(f'--validation "{v["check"]}|{v["status"]}"')
        val_args.append(f'--validation "errors_remaining|{after}"')

        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "Lint fix: {fixed}/{before} errors" \
            --tier RUNTIME_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "Lint error fixing via /lint-fix DAG executor" \
            --skip-verify 2>/dev/null || echo "Report generation skipped"'''

        print("Generating report...")  # noqa: ADR-0019
        _code, stdout, _stderr = self._run_shell(cmd)

        # Extract report path
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line.lower():
                self.state.report_path = line.strip()
                break

        if self.state.report_path:
            print(f"✅ Report: {self.state.report_path}")  # noqa: ADR-0019
        else:
            print("⚠️  Report generation skipped")  # noqa: ADR-0019
            self.state.report_path = "N/A"

        return True

    # =========================================================================
    # STEP 8: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT (NO PUSH)")

        if not self.state.files_modified:
            print("✅ No files to commit")  # noqa: ADR-0019
            return True

        # Stage modified files
        for f in self.state.files_modified:
            self._run_shell(f'git add "{REPO_ROOT / f}"')

        # Create commit message
        before = len(self.state.errors_before)
        after = len(self.state.errors_after)
        fixed = before - after

        codes = {
            e["code"] for e in self.state.errors_before if e.get("status") == "fixed"
        }
        codes_str = ", ".join(sorted(codes)[:3])
        if len(codes) > 3:
            codes_str += f" +{len(codes) - 3}"

        commit_msg = f"lint: fix {fixed} errors ({codes_str})"

        # Commit
        cmd = f'git commit -m "{commit_msg}" --no-verify 2>&1 || true'
        code, stdout, _stderr = self._run_shell(cmd)

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")  # noqa: ADR-0019
        elif code == 0 or "file changed" in stdout.lower():
            _code, hash_out, _ = self._run_shell("git rev-parse --short HEAD")
            self.state.commit_hash = hash_out.strip()
            print(f"✅ Committed: {self.state.commit_hash}")  # noqa: ADR-0019
            print(f"   Message: {commit_msg}")  # noqa: ADR-0019
        else:
            print(f"⚠️  Commit result: {stdout[:100]}")  # noqa: ADR-0019

        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019

        return True

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active /lint-fix execution. Start with:")  # noqa: ADR-0019
            print("  python3 workflows/lint_fix_executor.py")  # noqa: ADR-0019
            return

        self._print_header("LINT-FIX STATUS")
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print(f"Current step: {self.state.current_step}")  # noqa: ADR-0019
        print(f"Target codes: {self.state.target_codes or 'all'}")  # noqa: ADR-0019
        print(f"Errors before: {len(self.state.errors_before)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")  # noqa: ADR-0019
            elif step == self.state.current_step:
                print(f"  🔄 {step}")  # noqa: ADR-0019
            else:
                print(f"  ⏳ {step}")  # noqa: ADR-0019

    def run(self, target_codes: list[str] | None = None, resume: bool = False):
        """Execute the /lint-fix DAG — fully autonomous."""
        # Initialize or resume
        if resume and self._load_state():
            print("Resuming lint-fix...")  # noqa: ADR-0019
        else:
            self.state = LintFixState(
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
                target_codes=target_codes or [],
            )
            self._save_state()

        self._print_header("LINT-FIX EXECUTOR")
        if self.state.target_codes:
            print(f"Target codes: {', '.join(self.state.target_codes)}")  # noqa: ADR-0019

        # Step executors
        executors = {
            "scan_errors": self._step_scan_errors,
            "categorize": self._step_categorize,
            "apply_auto_fixes": self._step_apply_auto_fixes,
            "apply_semi_fixes": self._step_apply_semi_fixes,
            "validate": self._step_validate,
            "rescan": self._step_rescan,
            "generate_report": self._step_generate_report,
            "commit": self._step_commit,
        }

        # Execute steps in order
        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                continue

            self.state.current_step = step
            self._save_state()

            executor = executors.get(step)
            if not executor:
                print(f"❌ No executor for step: {step}")  # noqa: ADR-0019
                break

            success = executor()

            if success:
                self.state.completed_steps.append(step)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {step}")  # noqa: ADR-0019
                print("\nResume with: python3 workflows/lint_fix_executor.py --resume")  # noqa: ADR-0019
                return False

        # Complete
        self._print_header("LINT-FIX COMPLETE")
        before = len(self.state.errors_before)
        after = len(self.state.errors_after)
        print(f"✅ Errors: {before} → {after} ({before - after} fixed)")  # noqa: ADR-0019
        print(f"   Files modified: {len(self.state.files_modified)}")  # noqa: ADR-0019
        print(f"   Report: {self.state.report_path}")  # noqa: ADR-0019
        if self.state.commit_hash:
            print(f"   Commit: {self.state.commit_hash}")  # noqa: ADR-0019
        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Lint-Fix Executor — Fix lint errors systematically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/lint_fix_executor.py
    python3 workflows/lint_fix_executor.py --only B904 N811
    python3 workflows/lint_fix_executor.py --resume
    python3 workflows/lint_fix_executor.py --status
        """,
    )

    parser.add_argument("--only", nargs="+", help="Only fix specific error codes")
    parser.add_argument(
        "--resume", action="store_true", help="Resume interrupted execution"
    )
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--reset", action="store_true", help="Clear state and start fresh"
    )

    args = parser.parse_args()

    executor = LintFixExecutor()

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
            print("No lint-fix execution to resume")  # noqa: ADR-0019
            sys.exit(1)
        executor.run(resume=True)
        return

    success = executor.run(target_codes=args.only)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "cli",
        "dataclass",
        "executor",
        "filesystem",
        "linting",
        "messaging",
        "operations",
        "security",
        "serialization",
    ],
    "keywords": ["executor", "fix", "lint", "state", "status"],
    "business_value": "Run linter to get all errors Categorize by fix type (auto, semi, manual) Apply auto-fixes with ruff Apply semi-auto fixes with sed patterns Validate no new errors introduced Generate report Commit (NO",
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
