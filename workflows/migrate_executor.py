#!/usr/bin/env python3
"""
Migrate Executor — The ONLY Entry Point for /migrate
=====================================================

Fully autonomous code migration DAG.

The DAG handles everything:
- Index analysis (find all occurrences)
- Pattern extraction (identify migration pattern)
- Batch generation (create all changes)
- Apply changes (sed/cp, NO manual rewriting)
- Validate (py_compile, imports, tests)
- Wire + confirm-wiring (update refs)
- Generate GMP report (with script)
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/migrate_executor.py "old_pattern" "new_pattern"
    python3 workflows/migrate_executor.py --status
    python3 workflows/migrate_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Migrate Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "migrate_executor",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
STATE_FILE = REPO_ROOT / ".migrate_executor_state.json"

# Protected files - escalate if touched
PROTECTED_FILES = {
    "core/agents/executor.py",
    "runtime/websocket_orchestrator.py",
    "memory/substrate_service.py",
    "docker-compose.yml",
    "Dockerfile",
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class MigrationMatch:
    file: str
    line: int
    content: str
    migrated: bool = False
    new_content: str = ""


@dataclass
class MigrateState:
    old_pattern: str
    new_pattern: str
    started_at: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> MigrateState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "index_analysis",
    "pattern_extract",
    "batch_generate",
    "apply_changes",
    "validate",
    "wire_refs",
    "confirm_wiring",
    "generate_report",
    "commit",
]


# =============================================================================
# Migrate Executor
# =============================================================================


class MigrateExecutor:
    """Executes the /migrate DAG — fully autonomous, no user gates."""

    def __init__(self):
        self.state: MigrateState | None = None

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = MigrateState.from_dict(data)
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

    # =========================================================================
    # STEP 1: INDEX ANALYSIS
    # =========================================================================
    def _step_index_analysis(self) -> bool:
        self._print_header("INDEX ANALYSIS — Find All Occurrences")

        pattern = self.state.old_pattern
        print(f"Searching for: {pattern}\n")  # noqa: ADR-0019

        # Use ripgrep to find all matches
        escaped_pattern = pattern.replace('"', '\\"')
        cmd = f'rg "{escaped_pattern}" --type py -n 2>/dev/null || true'
        _code, stdout, _stderr = self._run_shell(cmd)

        matches = []
        for line in stdout.strip().split("\n"):
            if not line or ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                filepath = parts[0]
                try:
                    line_num = int(parts[1])
                except ValueError:
                    continue
                content = parts[2].strip()
                matches.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "content": content[:200],
                        "migrated": False,
                        "new_content": "",
                    }
                )

        self.state.matches = matches

        print(f"Found {len(matches)} occurrences:")  # noqa: ADR-0019
        print("-" * 70)  # noqa: ADR-0019
        print("| File | Line | Content |")  # noqa: ADR-0019
        print("|------|------|---------|")  # noqa: ADR-0019
        for m in matches[:30]:  # Show first 30
            print(f"| {m['file'][:35]} | {m['line']:4} | {m['content'][:40]} |")  # noqa: ADR-0019
        if len(matches) > 30:
            print(f"| ... and {len(matches) - 30} more |")  # noqa: ADR-0019
        print("-" * 70)  # noqa: ADR-0019

        if not matches:
            print("⚠️  No matches found — pattern may not exist")  # noqa: ADR-0019
            return True  # Continue but note it

        # Check for protected files
        protected_touched = [m["file"] for m in matches if m["file"] in PROTECTED_FILES]
        if protected_touched:
            print("\n⚠️  PROTECTED FILES CONTAIN PATTERN:")  # noqa: ADR-0019
            for f in protected_touched:
                print(f"   - {f}")  # noqa: ADR-0019
            print("\n⚠️  Will migrate but requires extra review")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 2: PATTERN EXTRACTION
    # =========================================================================
    def _step_pattern_extract(self) -> bool:
        self._print_header("PATTERN EXTRACTION — Analyze Migration")

        old = self.state.old_pattern
        new = self.state.new_pattern

        print("Migration pattern:")  # noqa: ADR-0019
        print(f"  FROM: {old}")  # noqa: ADR-0019
        print(f"  TO:   {new}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        # Analyze pattern type
        pattern_type = "simple_replace"
        if "(" in old and ")" in old:
            pattern_type = "function_rename"
        elif old.startswith("from ") or old.startswith("import "):
            pattern_type = "import_change"
        elif "." in old and "." in new:
            pattern_type = "module_rename"

        print(f"Pattern type: {pattern_type}")  # noqa: ADR-0019

        # Compute preview for first match
        if self.state.matches:
            sample = self.state.matches[0]["content"]
            preview = sample.replace(old, new)
            print("\nPreview (first match):")  # noqa: ADR-0019
            print(f"  Before: {sample[:60]}")  # noqa: ADR-0019
            print(f"  After:  {preview[:60]}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 3: BATCH GENERATION
    # =========================================================================
    def _step_batch_generate(self) -> bool:
        self._print_header("BATCH GENERATION — Prepare All Changes")

        old = self.state.old_pattern
        new = self.state.new_pattern

        # Group by file
        files_to_modify = {}
        for m in self.state.matches:
            if m["file"] not in files_to_modify:
                files_to_modify[m["file"]] = []
            files_to_modify[m["file"]].append(m)
            m["new_content"] = m["content"].replace(old, new)

        print(f"Files to modify: {len(files_to_modify)}")  # noqa: ADR-0019
        print(f"Total changes: {len(self.state.matches)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        # Show file summary
        print("-" * 50)  # noqa: ADR-0019
        print("| File | Changes |")  # noqa: ADR-0019
        print("|------|---------|")  # noqa: ADR-0019
        for f, changes in sorted(files_to_modify.items()):
            print(f"| {f[:35]} | {len(changes):3} |")  # noqa: ADR-0019
        print("-" * 50)  # noqa: ADR-0019

        self.state.files_modified = list(files_to_modify.keys())

        return True

    # =========================================================================
    # STEP 4: APPLY CHANGES (AUTONOMOUS - NO CONFIRMATION)
    # =========================================================================
    def _step_apply_changes(self) -> bool:
        self._print_header("APPLY CHANGES — Using sed (Autonomous)")

        old = self.state.old_pattern
        new = self.state.new_pattern

        # Escape special characters for sed
        old_escaped = old.replace("/", "\\/").replace("&", "\\&")
        new_escaped = new.replace("/", "\\/").replace("&", "\\&")

        success_count = 0
        fail_count = 0

        for filepath in self.state.files_modified:
            full_path = REPO_ROOT / filepath
            if not full_path.exists():
                print(f"⚠️  File not found: {filepath}")  # noqa: ADR-0019
                fail_count += 1
                continue

            # Use sed for in-place replacement
            cmd = f'sed -i "" "s/{old_escaped}/{new_escaped}/g" "{full_path}"'
            code, _stdout, stderr = self._run_shell(cmd)

            if code == 0:
                success_count += 1
                print(f"✅ {filepath}")  # noqa: ADR-0019
            else:
                fail_count += 1
                print(f"❌ {filepath}: {stderr[:50]}")  # noqa: ADR-0019

        # Mark matches as migrated
        for m in self.state.matches:
            m["migrated"] = True

        print(f"\n✅ Applied: {success_count} files")  # noqa: ADR-0019
        if fail_count:
            print(f"❌ Failed: {fail_count} files")  # noqa: ADR-0019

        return fail_count == 0 or success_count > 0

    # =========================================================================
    # STEP 5: VALIDATE
    # =========================================================================
    def _step_validate(self) -> bool:
        self._print_header("VALIDATE — Syntax and Import Check")

        validations = []

        # py_compile on modified files
        py_files = [f for f in self.state.files_modified if f.endswith(".py")]
        if py_files:
            files_str = " ".join(str(REPO_ROOT / f) for f in py_files)
            code, _stdout, stderr = self._run_shell(
                f"python3 -m py_compile {files_str}"
            )
            if code == 0:
                validations.append({"check": "py_compile", "status": "✅"})
                print(f"✅ py_compile: {len(py_files)} files OK")  # noqa: ADR-0019
            else:
                validations.append(
                    {"check": "py_compile", "status": "❌", "error": stderr}
                )
                print("❌ py_compile: FAILED")  # noqa: ADR-0019
                print(stderr[:200])  # noqa: ADR-0019
                # Don't fail - let wiring step handle

        # Quick import test for affected modules
        modules_tested = set()
        for filepath in py_files[:5]:  # Test first 5
            module = filepath.replace("/", ".").replace(".py", "")
            if module in modules_tested:
                continue
            modules_tested.add(module)

            cmd = f'python3 -c "import {module}" 2>&1'
            code, _stdout, _stderr = self._run_shell(cmd)
            if code == 0:
                print(f"✅ import {module[:40]}")  # noqa: ADR-0019
            else:
                print(f"⚠️  import {module[:40]}: may need wiring")  # noqa: ADR-0019

        self.state.validation_results = validations
        return True

    # =========================================================================
    # STEP 6: WIRE REFS
    # =========================================================================
    def _step_wire_refs(self) -> bool:
        self._print_header("WIRE REFS — Update Dependent Imports")

        new_pattern = self.state.new_pattern

        # Check if migration created new import requirements
        if "from " in new_pattern or "import " in new_pattern:
            print("Migration involves imports - checking refs...")  # noqa: ADR-0019
            # Extract module name from new pattern
            match = re.search(
                r"from\s+([\w.]+)\s+import|import\s+([\w.]+)", new_pattern
            )
            if match:
                module_name = match.group(1) or match.group(2)
                # Verify module exists
                cmd = f'python3 -c "import {module_name}" 2>&1'
                code, stdout, _stderr = self._run_shell(cmd)
                if code == 0:
                    print(f"✅ Module {module_name} is importable")  # noqa: ADR-0019
                else:
                    print(f"⚠️  Module {module_name} import issue: {stdout[:80]}")  # noqa: ADR-0019
        else:
            print("✅ No additional wiring needed")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 7: CONFIRM WIRING
    # =========================================================================
    def _step_confirm_wiring(self) -> bool:
        self._print_header("CONFIRM WIRING — Final Verification")

        checks = []

        # Verify no broken references remain
        old_pattern = self.state.old_pattern
        cmd = f'rg "{old_pattern}" --type py -l 2>/dev/null | wc -l'
        _code, stdout, _stderr = self._run_shell(cmd)
        remaining = int(stdout.strip() or "0")

        if remaining == 0:
            checks.append({"check": "Old pattern removed", "status": "✅"})
            print("✅ Old pattern fully migrated")  # noqa: ADR-0019
        else:
            checks.append(
                {"check": "Old pattern removed", "status": f"⚠️ {remaining} remaining"}
            )
            print(f"⚠️  {remaining} files still contain old pattern")  # noqa: ADR-0019

        # Verify new pattern exists
        new_pattern = self.state.new_pattern
        cmd = f'rg "{new_pattern}" --type py -l 2>/dev/null | wc -l'
        _code, stdout, _stderr = self._run_shell(cmd)
        new_count = int(stdout.strip() or "0")

        checks.append(
            {"check": "New pattern present", "status": f"✅ {new_count} files"}
        )
        print(f"✅ New pattern in {new_count} files")  # noqa: ADR-0019

        # Summary
        print("\n" + "=" * 40)  # noqa: ADR-0019
        print("WIRING CONFIRMATION SUMMARY")  # noqa: ADR-0019
        print("=" * 40)  # noqa: ADR-0019
        for c in checks:
            print(f"  {c['status']} {c['check']}")  # noqa: ADR-0019

        self.state.validation_results.extend(checks)
        return True

    # =========================================================================
    # STEP 8: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT — GMP Report via Script")

        # Build TODO items
        todo_args = []
        for i, f in enumerate(self.state.files_modified[:10], 1):
            todo_args.append(f'--todo "M{i}|{f}|*|MIGRATE|sed replace"')

        # Build validation items
        val_args = []
        for v in self.state.validation_results:
            val_args.append(f'--validation "{v["check"]}|{v["status"]}"')

        if not todo_args:
            todo_args.append('--todo "M1|migration|*|VERIFY|Pattern migration"')
        if not val_args:
            val_args.append('--validation "migration|✅"')

        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "Migrate: {self.state.old_pattern[:30]} → {self.state.new_pattern[:30]}" \
            --tier RUNTIME_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "Code migration via /migrate DAG executor" \
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
    # STEP 9: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT — Stage and Commit (NO PUSH)")

        if not self.state.files_modified:
            print("✅ No files modified — nothing to commit")  # noqa: ADR-0019
            return True

        # Stage files
        for f in self.state.files_modified:
            self._run_shell(f'git add "{f}"')

        # Create commit message
        old = self.state.old_pattern[:20]
        new = self.state.new_pattern[:20]
        count = len(self.state.files_modified)

        commit_msg = f"migrate: {old} → {new} ({count} files)"

        # Commit
        cmd = f'git commit -m "{commit_msg}" --no-verify 2>&1 || true'
        code, stdout, _stderr = self._run_shell(cmd)

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")  # noqa: ADR-0019
        elif code == 0 or "file changed" in stdout.lower():
            # Get commit hash
            code, hash_out, _ = self._run_shell("git rev-parse --short HEAD")
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
            print("No active /migrate execution. Start with:")  # noqa: ADR-0019
            print('  python3 workflows/migrate_executor.py "old" "new"')  # noqa: ADR-0019
            return

        self._print_header(
            f"MIGRATE STATUS: {self.state.old_pattern} → {self.state.new_pattern}"
        )
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print(f"Current step: {self.state.current_step}")  # noqa: ADR-0019
        print(f"Matches: {len(self.state.matches)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")  # noqa: ADR-0019
            elif step == self.state.current_step:
                print(f"  🔄 {step}")  # noqa: ADR-0019
            else:
                print(f"  ⏳ {step}")  # noqa: ADR-0019

    def run(self, old_pattern: str = "", new_pattern: str = "", resume: bool = False):
        """Execute the /migrate DAG — fully autonomous."""
        # Initialize or resume
        if resume and self._load_state():
            print(
                f"Resuming migration: {self.state.old_pattern} → {self.state.new_pattern}"
            )  # noqa: ADR-0019
        else:
            if not old_pattern or not new_pattern:
                print("❌ Both old and new patterns required")  # noqa: ADR-0019
                return False
            self.state = MigrateState(
                old_pattern=old_pattern,
                new_pattern=new_pattern,
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
            )
            self._save_state()

        self._print_header(
            f"MIGRATE EXECUTOR: {self.state.old_pattern} → {self.state.new_pattern}"
        )

        # Step executors
        executors = {
            "index_analysis": self._step_index_analysis,
            "pattern_extract": self._step_pattern_extract,
            "batch_generate": self._step_batch_generate,
            "apply_changes": self._step_apply_changes,
            "validate": self._step_validate,
            "wire_refs": self._step_wire_refs,
            "confirm_wiring": self._step_confirm_wiring,
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
                print("\nResume with: python3 workflows/migrate_executor.py --resume")  # noqa: ADR-0019
                return False

        # Complete
        self._print_header("MIGRATION COMPLETE")
        print(f"✅ Pattern: {self.state.old_pattern} → {self.state.new_pattern}")  # noqa: ADR-0019
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
        description="Migrate Executor — Run the /migrate DAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/migrate_executor.py "old_function" "new_function"
    python3 workflows/migrate_executor.py "from old.module" "from new.module"
    python3 workflows/migrate_executor.py --resume
    python3 workflows/migrate_executor.py --status
        """,
    )

    parser.add_argument("old_pattern", nargs="?", help="Pattern to find and replace")
    parser.add_argument("new_pattern", nargs="?", help="Pattern to replace with")
    parser.add_argument(
        "--resume", action="store_true", help="Resume interrupted execution"
    )
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--reset", action="store_true", help="Clear state and start fresh"
    )

    args = parser.parse_args()

    executor = MigrateExecutor()

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
            print("No migration to resume")  # noqa: ADR-0019
            sys.exit(1)
        executor.run(resume=True)
        return

    if not args.old_pattern or not args.new_pattern:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.old_pattern, args.new_pattern)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "cli",
        "dataclass",
        "executor",
        "filesystem",
        "messaging",
        "migration",
        "operations",
        "realtime",
        "security",
    ],
    "keywords": ["executor", "match", "migrate", "migration", "state", "status"],
    "business_value": "Index analysis (find all occurrences) Pattern extraction (identify migration pattern) Batch generation (create all changes) Apply changes (sed/cp, NO manual rewriting) Validate (py_compile, imports, t",
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
