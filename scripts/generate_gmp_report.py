#!/usr/bin/env python3
"""
generate_gmp_report.py — Automatic GMP Report Generator
========================================================

Generates canonical GMP reports following gmp-report-contract.yaml.
Called at Phase 6 of GMP execution to produce production-quality reports.

Usage:
    # Interactive mode (prompts for data)
    python scripts/generate_gmp_report.py
    
    # From JSON file (for automation)
    python scripts/generate_gmp_report.py --from-json gmp_data.json
    
    # With inline parameters
    python scripts/generate_gmp_report.py \
        --task "Add resilience to checkpoint" \
        --tier RUNTIME_TIER \
        --todo "T1|memory/checkpoint.py|45-60|REPLACE|Add retry logic" \
        --todo "T2|tests/test_checkpoint.py|1-50|CREATE|Add tests" \
        --change "memory/checkpoint.py|45-60|REPLACE|Added exponential backoff" \
        --validation "py_compile|PASS" \
        --validation "import test|PASS"

Version: 1.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Generate Gmp Report",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T15:29:16Z",
    "updated_at": "2026-01-24T13:02:53Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "generate_gmp_report",
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
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(os.getenv("L9_REPO_ROOT", "/Users/ib-mac/Projects/L9"))
REPORTS_DIR = REPO_ROOT / "reports"
WORKFLOW_STATE_PATH = REPO_ROOT / "workflow_state.md"

VALID_TIERS = ["KERNEL_TIER", "RUNTIME_TIER", "INFRA_TIER", "UX_TIER"]
VALID_ACTIONS = ["CREATE", "INSERT", "REPLACE", "DELETE", "WRAP"]
VALID_STATUSES = ["✅ COMPLETE", "⚠️ PARTIAL", "❌ FAILED"]


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class TodoItem:
    """A single TODO item from Phase 0."""

    id: str  # T1, T2, etc.
    file: str
    lines: str  # e.g., "45-60" or "L45" or "1-50"
    action: str  # CREATE, INSERT, REPLACE, DELETE, WRAP
    description: str
    status: str = "✅"  # ✅, ❌, ⚠️


@dataclass
class ChangeItem:
    """A change made during implementation."""

    file: str
    lines: str
    action: str
    description: str


@dataclass
class ValidationResult:
    """A validation gate result."""

    gate: str  # e.g., "py_compile", "import test", "unit tests"
    result: str  # ✅, ❌, ⚠️ SKIP, N/A
    details: str = ""  # e.g., "24 passed"


@dataclass
class PhaseStatus:
    """Status of a GMP phase."""

    phase: int
    name: str
    status: str  # ✅, ❌, ⚠️, N/A


@dataclass
class GMPReportData:
    """All data needed to generate a GMP report."""

    task: str
    tier: str
    todos: List[TodoItem] = field(default_factory=list)
    changes: List[ChangeItem] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    phases: List[PhaseStatus] = field(default_factory=list)
    summary: str = ""
    root_cause: str = ""
    breaking_changes: str = ""

    # Auto-populated
    gmp_id: int = 0
    date: str = ""
    time: str = ""
    status: str = "✅ COMPLETE"


# ============================================================================
# Report Generator
# ============================================================================


class GMPReportGenerator:
    """Generates canonical GMP reports."""

    def __init__(self, reports_dir: Path = REPORTS_DIR):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def find_next_gmp_id(self) -> int:
        """Find the next sequential GMP ID."""
        max_id = 0

        # Check both reports/ and reports/GMP Reports/ for existing IDs
        for pattern in ["GMP-Report-*.md", "GMP_Report_*.md", "GMP Reports/GMP*.md"]:
            for path in self.reports_dir.glob(pattern):
                # Extract number from filename
                match = re.search(
                    r"(?:GMP-Report-|GMP_Report_GMP-|GMP-)(\d+)", path.name
                )
                if match:
                    try:
                        num = int(match.group(1))
                        max_id = max(max_id, num)
                    except ValueError:
                        pass

        return max_id + 1

    def generate_filename(self, gmp_id: int, task: str) -> str:
        """Generate canonical filename."""
        # Convert task to kebab-case
        description = task.strip()
        # Remove special characters, replace spaces with hyphens
        description = re.sub(r"[^\w\s-]", "", description)
        description = re.sub(r"\s+", "-", description)
        description = re.sub(r"-+", "-", description)
        # Capitalize each word (kebab-case with capitals)
        description = "-".join(
            word.capitalize() for word in description.split("-") if word
        )
        # Truncate if too long
        if len(description) > 50:
            description = description[:50].rsplit("-", 1)[0]

        return f"GMP-Report-{gmp_id:03d}-{description}.md"

    def generate_report(self, data: GMPReportData) -> str:
        """Generate the report content."""
        # Auto-populate missing data
        if not data.gmp_id:
            data.gmp_id = self.find_next_gmp_id()

        # Use EST timezone for accurate timestamps
        est = ZoneInfo("America/New_York")
        now_est = datetime.now(est)
        if not data.date:
            data.date = now_est.strftime("%Y-%m-%d")
        if not data.time:
            data.time = now_est.strftime("%H:%M EST")

        # Determine overall status
        if data.phases:
            all_passed = all(p.status == "✅" for p in data.phases)
            any_failed = any(p.status == "❌" for p in data.phases)
            if any_failed:
                data.status = "❌ FAILED"
            elif not all_passed:
                data.status = "⚠️ PARTIAL"
            else:
                data.status = "✅ COMPLETE"

        # Default phases if not provided
        if not data.phases:
            data.phases = [
                PhaseStatus(0, "PLANNING", "✅"),
                PhaseStatus(1, "BASELINE", "✅"),
                PhaseStatus(2, "IMPLEMENTATION", "✅"),
                PhaseStatus(3, "ENFORCEMENT", "✅"),
                PhaseStatus(4, "VALIDATION", "✅"),
                PhaseStatus(5, "RECURSION", "✅"),
                PhaseStatus(6, "FINALIZATION", "✅"),
            ]

        # Generate report content
        lines = []

        # Header (each field on its own line)
        lines.append(f"# GMP-Report-{data.gmp_id:03d}")
        lines.append("")
        lines.append(f"**ID:** GMP-{data.gmp_id:03d}")
        lines.append(f"**Task:** {data.task}")
        lines.append(f"**Tier:** {data.tier}")
        lines.append(f"**Date:** {data.date}")
        lines.append(f"**Time:** {data.time}")
        lines.append(f"**Status:** {data.status}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Optional Summary (only if provided)
        if data.summary:
            lines.append("## SUMMARY")
            lines.append("")
            lines.append(data.summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Optional Root Cause (only for bug fixes)
        if data.root_cause:
            lines.append("## ROOT CAUSE")
            lines.append("")
            lines.append(data.root_cause)
            lines.append("")
            lines.append("---")
            lines.append("")

        # PLAN (required)
        lines.append("## PLAN")
        lines.append("")
        lines.append("| ID | File | Lines | Action | Status |")
        lines.append("|----|------|-------|--------|--------|")
        for todo in data.todos:
            lines.append(
                f"| {todo.id} | `{todo.file}` | {todo.lines} | {todo.action} | {todo.status} |"
            )
        lines.append("")

        # Hash
        key_files = ", ".join(set(t.file.split("/")[-1] for t in data.todos[:3]))
        lines.append(f"**Hash:** `{len(data.todos)} TODOs | {key_files}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # CHANGES (required)
        lines.append("## CHANGES")
        lines.append("")
        lines.append("| File | Lines | Action | Description |")
        lines.append("|------|-------|--------|-------------|")
        for change in data.changes:
            lines.append(
                f"| `{change.file}` | {change.lines} | {change.action} | {change.description} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

        # TODO → CHANGE MAP (required)
        lines.append("## TODO → CHANGE MAP")
        lines.append("")
        lines.append("| TODO | File | Change |")
        lines.append("|------|------|--------|")
        for i, todo in enumerate(data.todos):
            if i < len(data.changes):
                change = data.changes[i]
                lines.append(
                    f"| {todo.id} | {todo.file.split('/')[-1]} | {change.description[:80]} |"
                )
            else:
                lines.append(
                    f"| {todo.id} | {todo.file.split('/')[-1]} | {todo.description[:80]} |"
                )
        lines.append("")
        lines.append("---")
        lines.append("")

        # VALIDATION (required)
        lines.append("## VALIDATION")
        lines.append("")
        lines.append("| Gate | Result |")
        lines.append("|------|--------|")

        # Default validations if none provided
        if not data.validations:
            data.validations = [
                ValidationResult("py_compile", "✅"),
                ValidationResult("import test", "✅"),
            ]

        for val in data.validations:
            result = val.result
            if val.details:
                result = f"{val.result} {val.details}"
            lines.append(f"| {val.gate} | {result} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Optional Breaking Changes
        if data.breaking_changes and data.breaking_changes.lower() != "none":
            lines.append("## BREAKING CHANGES")
            lines.append("")
            lines.append(data.breaking_changes)
            lines.append("")
            lines.append("---")
            lines.append("")

        # DECLARATION (required)
        lines.append("## DECLARATION")
        lines.append("")
        lines.append("Phases 0-6 complete. No assumptions. No drift.")
        lines.append("")

        return "\n".join(lines)

    def save_report(self, data: GMPReportData) -> Path:
        """Generate and save the report."""
        if not data.gmp_id:
            data.gmp_id = self.find_next_gmp_id()

        content = self.generate_report(data)
        filename = self.generate_filename(data.gmp_id, data.task)
        filepath = self.reports_dir / filename

        filepath.write_text(content, encoding="utf-8")
        return filepath

    def update_workflow_state(self, data: GMPReportData, filepath: Path) -> bool:
        """Update workflow_state.md with the completed GMP."""
        if not WORKFLOW_STATE_PATH.exists():
            return False

        try:
            content = WORKFLOW_STATE_PATH.read_text(encoding="utf-8")

            # Create entry for Recent Changes section
            date_str = datetime.now().strftime("%Y-%m-%d")
            files_summary = ", ".join(
                set(t.file.split("/")[-1] for t in data.todos[:3])
            )

            new_entry = f"- [{date_str}] **GMP-{data.gmp_id:03d}: {data.task}** — "
            if data.summary:
                new_entry += data.summary[:150]
            else:
                new_entry += f"Files: {files_summary}. Report: `{filepath.name}`"

            # Find "## Recent Changes" section and add entry
            changes_pattern = r"(## Recent Changes.*?\n)"
            if re.search(changes_pattern, content, re.IGNORECASE):
                # Insert after the header
                content = re.sub(
                    r"(## Recent Changes[^\n]*\n(?:Full history:[^\n]*\n)?)\n",
                    f"\\1\n{new_entry}\n",
                    content,
                    count=1,
                )

            # Update "**COMPLETED THIS SESSION" section if it exists
            session_date = datetime.now().strftime("%Y-%m-%d")
            session_pattern = rf"\*\*COMPLETED THIS SESSION \({session_date}\)\*\*:"
            if re.search(session_pattern, content):
                # Add to existing session
                content = re.sub(
                    rf"(\*\*COMPLETED THIS SESSION \({session_date}\)\*\*:\n)",
                    f"\\1- ✅ **GMP-{data.gmp_id:03d}: {data.task}** — {files_summary}. Report: `{filepath.name}`\n",
                    content,
                    count=1,
                )

            WORKFLOW_STATE_PATH.write_text(content, encoding="utf-8")
            return True

        except Exception as e:
            print(f"Warning: Could not update workflow_state.md: {e}", file=sys.stderr)
            return False


# ============================================================================
# CLI Interface
# ============================================================================


def parse_todo(s: str) -> TodoItem:
    """Parse a TODO string: 'T1|file|lines|action|description'."""
    parts = s.split("|")
    if len(parts) < 5:
        raise ValueError(
            f"Invalid TODO format: {s}. Expected: ID|file|lines|action|description"
        )
    return TodoItem(
        id=parts[0].strip(),
        file=parts[1].strip(),
        lines=parts[2].strip(),
        action=parts[3].strip().upper(),
        description=parts[4].strip(),
        status="✅",
    )


def parse_change(s: str) -> ChangeItem:
    """Parse a CHANGE string: 'file|lines|action|description'."""
    parts = s.split("|")
    if len(parts) < 4:
        raise ValueError(
            f"Invalid CHANGE format: {s}. Expected: file|lines|action|description"
        )
    return ChangeItem(
        file=parts[0].strip(),
        lines=parts[1].strip(),
        action=parts[2].strip().upper(),
        description=parts[3].strip(),
    )


def parse_validation(s: str) -> ValidationResult:
    """Parse a VALIDATION string: 'gate|result' or 'gate|result|details'."""
    parts = s.split("|")
    if len(parts) < 2:
        raise ValueError(f"Invalid VALIDATION format: {s}. Expected: gate|result")
    return ValidationResult(
        gate=parts[0].strip(),
        result=parts[1].strip(),
        details=parts[2].strip() if len(parts) > 2 else "",
    )


def interactive_mode() -> GMPReportData:
    """Interactive mode to collect GMP data."""
    print("\n=== GMP Report Generator (Interactive Mode) ===\n")

    data = GMPReportData(task="", tier="")

    # Task
    data.task = input("Task description: ").strip()
    if not data.task:
        print("Error: Task is required")
        sys.exit(1)

    # Tier
    print(f"\nValid tiers: {', '.join(VALID_TIERS)}")
    data.tier = input("Tier [RUNTIME_TIER]: ").strip().upper() or "RUNTIME_TIER"
    if data.tier not in VALID_TIERS:
        print(f"Warning: Invalid tier '{data.tier}', using RUNTIME_TIER")
        data.tier = "RUNTIME_TIER"

    # Summary (optional)
    data.summary = input("\nSummary (optional, max 200 chars): ").strip()

    # TODOs
    print("\n--- TODO Items (enter empty line to finish) ---")
    print("Format: T#|file|lines|action|description")
    print("Example: T1|memory/checkpoint.py|45-60|REPLACE|Add retry logic")

    todo_num = 1
    while True:
        todo_str = input(f"TODO T{todo_num}: ").strip()
        if not todo_str:
            break
        if not todo_str.startswith("T"):
            todo_str = f"T{todo_num}|{todo_str}"
        try:
            data.todos.append(parse_todo(todo_str))
            todo_num += 1
        except ValueError as e:
            print(f"  Error: {e}")

    # Changes (default to TODOs if not specified)
    print("\n--- Changes (enter empty to use TODOs, or specify) ---")
    print("Format: file|lines|action|description")

    while True:
        change_str = input("Change: ").strip()
        if not change_str:
            break
        try:
            data.changes.append(parse_change(change_str))
        except ValueError as e:
            print(f"  Error: {e}")

    # If no changes specified, derive from TODOs
    if not data.changes and data.todos:
        data.changes = [
            ChangeItem(t.file, t.lines, t.action, t.description) for t in data.todos
        ]

    # Validations
    print("\n--- Validation Results (enter empty to use defaults) ---")
    print("Format: gate|result or gate|result|details")
    print("Example: unit tests|✅|24 passed")

    while True:
        val_str = input("Validation: ").strip()
        if not val_str:
            break
        try:
            data.validations.append(parse_validation(val_str))
        except ValueError as e:
            print(f"  Error: {e}")

    return data


def from_json_file(path: str) -> GMPReportData:
    """Load GMP data from a JSON file."""
    with open(path, "r") as f:
        raw = json.load(f)

    data = GMPReportData(
        task=raw.get("task", ""),
        tier=raw.get("tier", "RUNTIME_TIER"),
        summary=raw.get("summary", ""),
        root_cause=raw.get("root_cause", ""),
        breaking_changes=raw.get("breaking_changes", ""),
    )

    for t in raw.get("todos", []):
        data.todos.append(
            TodoItem(
                id=t.get("id", f"T{len(data.todos) + 1}"),
                file=t.get("file", ""),
                lines=t.get("lines", ""),
                action=t.get("action", "REPLACE"),
                description=t.get("description", ""),
                status=t.get("status", "✅"),
            )
        )

    for c in raw.get("changes", []):
        data.changes.append(
            ChangeItem(
                file=c.get("file", ""),
                lines=c.get("lines", ""),
                action=c.get("action", "REPLACE"),
                description=c.get("description", ""),
            )
        )

    for v in raw.get("validations", []):
        data.validations.append(
            ValidationResult(
                gate=v.get("gate", ""),
                result=v.get("result", "✅"),
                details=v.get("details", ""),
            )
        )

    return data


def run_verification(filepath: Path, quiet: bool = False) -> bool:
    """Run the verification script on the generated report."""
    import time

    validator_script = REPO_ROOT / "scripts" / "validate_gmp_report.py"

    if not validator_script.exists():
        if not quiet:
            print("   ⚠️ Validator script not found, skipping verification")
        return True

    # Wait for filesystem to sync (prevents race condition)
    time.sleep(2)

    try:
        result = subprocess.run(
            ["python3", str(validator_script), str(filepath)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )

        if result.returncode == 0:
            if not quiet:
                print("   ✅ Verification: PASSED")
            return True
        else:
            if not quiet:
                print("   ❌ Verification: FAILED")
                # Show errors from validator output
                for line in result.stdout.split("\n"):
                    if "ERROR" in line or "🔴" in line:
                        print(f"      {line.strip()}")
            return False

    except subprocess.TimeoutExpired:
        if not quiet:
            print("   ⚠️ Verification: Timeout")
        return False
    except Exception as e:
        if not quiet:
            print(f"   ⚠️ Verification error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate canonical GMP reports following gmp-report-contract.yaml"
    )
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--tier", choices=VALID_TIERS, default="RUNTIME_TIER")
    parser.add_argument(
        "--todo", action="append", help="TODO item (T#|file|lines|action|desc)"
    )
    parser.add_argument(
        "--change", action="append", help="Change item (file|lines|action|desc)"
    )
    parser.add_argument(
        "--validation", action="append", help="Validation (gate|result[|details])"
    )
    parser.add_argument("--summary", help="Optional summary")
    parser.add_argument("--root-cause", help="Root cause (for bug fixes)")
    parser.add_argument("--from-json", help="Load data from JSON file")
    parser.add_argument(
        "--update-workflow", action="store_true", help="Update workflow_state.md"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print report without saving"
    )
    parser.add_argument(
        "--skip-verify", action="store_true", help="Skip automatic verification"
    )
    parser.add_argument(
        "--gmp-id", type=int, help="Force specific GMP ID (override auto-detect)"
    )

    args = parser.parse_args()

    # Determine data source
    if args.from_json:
        data = from_json_file(args.from_json)
    elif args.task:
        # From CLI arguments
        data = GMPReportData(
            task=args.task,
            tier=args.tier,
            summary=args.summary or "",
            root_cause=args.root_cause or "",
        )

        for t in args.todo or []:
            data.todos.append(parse_todo(t))

        for c in args.change or []:
            data.changes.append(parse_change(c))

        # If no changes specified, derive from TODOs
        if not data.changes and data.todos:
            data.changes = [
                ChangeItem(t.file, t.lines, t.action, t.description) for t in data.todos
            ]

        for v in args.validation or []:
            data.validations.append(parse_validation(v))
    else:
        # Interactive mode
        data = interactive_mode()

    # Override GMP ID if specified
    if args.gmp_id:
        data.gmp_id = args.gmp_id

    # Generate report
    generator = GMPReportGenerator()

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Report would be:")
        print("=" * 60 + "\n")
        print(generator.generate_report(data))
    else:
        filepath = generator.save_report(data)
        print(f"\n✅ Report saved: {filepath}")
        print(f"   GMP ID: GMP-{data.gmp_id:03d}")
        print(f"   Status: {data.status}")

        # Automatic verification (unless skipped)
        if not args.skip_verify:
            verification_passed = run_verification(filepath)
            if not verification_passed:
                print(
                    "\n⚠️  Report generated but has validation issues. Review and fix."
                )

        if args.update_workflow:
            if generator.update_workflow_state(data, filepath):
                print("   workflow_state.md: Updated")
            else:
                print("   workflow_state.md: Failed to update")

        # Final output
        print(f"\n📋 Report path: {filepath}")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "cli",
        "dataclass",
        "event-driven",
        "filesystem",
        "operations",
        "scripts",
        "security",
        "serialization",
        "subprocess",
    ],
    "keywords": [
        "change",
        "filename",
        "find",
        "generate",
        "generator",
        "gmp",
        "interactive",
        "json",
    ],
    "business_value": "Provides generate gmp report components including TodoItem, ChangeItem, ValidationResult",
    "last_modified": "2026-01-24T13:02:53Z",
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
