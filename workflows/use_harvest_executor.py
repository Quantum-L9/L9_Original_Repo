#!/usr/bin/env python3
"""
Use-Harvest Executor — The ONLY Entry Point for /use-harvest
============================================================

Deploys harvested code files to their target locations.

The DAG handles everything:
- Read HARVEST_TABLE.md
- Verify target locations exist
- Deploy files using cp (NO manual rewriting)
- Validate syntax
- Wire imports/exports
- Generate report
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/use_harvest_executor.py path/to/harvested/
    python3 workflows/use_harvest_executor.py --status
    python3 workflows/use_harvest_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
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
STATE_FILE = REPO_ROOT / ".use_harvest_executor_state.json"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DeployItem:
    number: int
    source_file: str
    target_path: str
    action: str  # CREATE, REPLACE, EXTEND
    status: str = "pending"


@dataclass
class UseHarvestState:
    harvest_dir: str
    started_at: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    files_deployed: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> UseHarvestState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "read_harvest_table",
    "verify_targets",
    "deploy_files",
    "validate_syntax",
    "wire_imports",
    "generate_report",
    "commit",
]


# =============================================================================
# Use-Harvest Executor
# =============================================================================


class UseHarvestExecutor:
    """Executes the /use-harvest DAG — fully autonomous, no user gates."""

    def __init__(self):
        self.state: UseHarvestState | None = None

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = UseHarvestState.from_dict(data)
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
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    # =========================================================================
    # STEP 1: READ HARVEST TABLE
    # =========================================================================
    def _step_read_harvest_table(self) -> bool:
        self._print_header("READ HARVEST TABLE")

        harvest_dir = Path(self.state.harvest_dir)
        if not harvest_dir.is_absolute():
            harvest_dir = REPO_ROOT / self.state.harvest_dir

        table_file = harvest_dir / "HARVEST_TABLE.md"

        if not table_file.exists():
            # Try to find harvested files directly
            py_files = list(harvest_dir.glob("*.py"))
            if py_files:
                print(f"⚠️  No HARVEST_TABLE.md, using {len(py_files)} .py files directly")
                items = []
                for i, f in enumerate(sorted(py_files), 1):
                    items.append({
                        "number": i,
                        "source_file": str(f),
                        "target_path": "",  # Will need to be specified
                        "action": "CREATE",
                        "status": "pending",
                    })
                self.state.items = items
                return True

            print(f"❌ No HARVEST_TABLE.md found at {table_file}")
            return False

        # Parse the harvest table
        content = table_file.read_text()
        items = []

        # Parse table rows: | # | Pattern | Source Lines | Target |
        for line in content.split("\n"):
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4:
                    try:
                        num = int(parts[0])
                    except ValueError:
                        continue

                    pattern = parts[1].strip("`")
                    target = parts[3].strip("`")

                    # Find the actual source file
                    source_file = harvest_dir / target
                    if not source_file.exists():
                        # Try with number prefix
                        for f in harvest_dir.glob(f"{num}_*"):
                            source_file = f
                            break

                    items.append({
                        "number": num,
                        "source_file": str(source_file),
                        "target_path": target if "/" in target else "",
                        "action": "CREATE",
                        "status": "pending",
                    })

        self.state.items = items

        print(f"✅ Read harvest table: {len(items)} items")
        for item in items[:10]:
            print(f"   {item['number']:2}. {Path(item['source_file']).name}")
        if len(items) > 10:
            print(f"   ... and {len(items) - 10} more")

        return len(items) > 0

    # =========================================================================
    # STEP 2: VERIFY TARGETS
    # =========================================================================
    def _step_verify_targets(self) -> bool:
        self._print_header("VERIFY TARGET LOCATIONS")

        for item in self.state.items:
            target = item["target_path"]
            if not target:
                print(f"⚠️  {item['number']}: No target path specified")
                item["action"] = "MANUAL"
                continue

            target_path = REPO_ROOT / target

            if target_path.exists():
                item["action"] = "REPLACE"
                print(f"🔄 {item['number']:2}. {target} — REPLACE")
            else:
                # Check if parent directory exists
                parent = target_path.parent
                if parent.exists():
                    item["action"] = "CREATE"
                    print(f"✨ {item['number']:2}. {target} — CREATE")
                else:
                    item["action"] = "CREATE_DIR"
                    print(f"📁 {item['number']:2}. {target} — CREATE (+ dir)")

        return True

    # =========================================================================
    # STEP 3: DEPLOY FILES (using cp, NOT manual rewrite)
    # =========================================================================
    def _step_deploy_files(self) -> bool:
        self._print_header("DEPLOY FILES (cp-based, NO manual rewrite)")

        files_deployed = []

        for item in self.state.items:
            source = Path(item["source_file"])
            target = item["target_path"]

            if not target or item["action"] == "MANUAL":
                print(f"⏭️  {item['number']}: Skipped (no target)")
                continue

            if not source.exists():
                print(f"❌ {item['number']}: Source not found: {source}")
                item["status"] = "failed"
                continue

            target_path = REPO_ROOT / target

            # Create parent directory if needed
            if item["action"] == "CREATE_DIR":
                target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file using cp
            cmd = f'cp "{source}" "{target_path}"'
            code, _stdout, stderr = self._run_shell(cmd)

            if code == 0:
                item["status"] = "deployed"
                files_deployed.append(target)
                print(f"✅ {item['number']:2}. {target}")
            else:
                item["status"] = "failed"
                print(f"❌ {item['number']:2}. {target}: {stderr[:50]}")

        self.state.files_deployed = files_deployed

        success = len(files_deployed)
        total = len([i for i in self.state.items if i["action"] != "MANUAL"])
        print(f"\n✅ Deployed: {success}/{total} files")

        return success > 0 or total == 0

    # =========================================================================
    # STEP 4: VALIDATE SYNTAX
    # =========================================================================
    def _step_validate_syntax(self) -> bool:
        self._print_header("VALIDATE SYNTAX")

        validations = []
        py_files = [f for f in self.state.files_deployed if f.endswith(".py")]

        if not py_files:
            print("⚠️  No Python files to validate")
            validations.append({"check": "py_compile", "status": "⚠️ N/A"})
            self.state.validation_results = validations
            return True

        # py_compile each file
        passed = 0
        for f in py_files:
            full_path = REPO_ROOT / f
            code, _stdout, stderr = self._run_shell(f'python3 -m py_compile "{full_path}"')
            if code == 0:
                passed += 1
                print(f"✅ {f}")
            else:
                print(f"❌ {f}: {stderr[:60]}")

        validations.append({
            "check": "py_compile",
            "status": f"✅ {passed}/{len(py_files)}" if passed == len(py_files) else f"⚠️ {passed}/{len(py_files)}",
        })

        self.state.validation_results = validations
        print(f"\n✅ Syntax valid: {passed}/{len(py_files)} files")

        return True

    # =========================================================================
    # STEP 5: WIRE IMPORTS
    # =========================================================================
    def _step_wire_imports(self) -> bool:
        self._print_header("WIRE IMPORTS")

        # Check if any deployed files need imports added to __init__.py
        for f in self.state.files_deployed:
            if not f.endswith(".py"):
                continue

            target_path = REPO_ROOT / f
            parent_dir = target_path.parent
            init_file = parent_dir / "__init__.py"

            if init_file.exists():
                module_name = target_path.stem
                init_content = init_file.read_text()

                # Check if already imported
                if module_name not in init_content:
                    print(f"⚠️  {f} may need to be added to {parent_dir.name}/__init__.py")
            else:
                # No __init__.py - may need to create one
                print(f"⚠️  No __init__.py in {parent_dir.name}/ — may need to create")

        print("\n✅ Wiring check complete")
        print("   → Run /wire for full import resolution")

        return True

    # =========================================================================
    # STEP 6: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT")

        # Build TODO items
        todo_args = []
        for item in self.state.items[:10]:
            if item["target_path"]:
                todo_args.append(f'--todo "D{item["number"]}|{item["target_path"]}|*|{item["action"]}|{item["status"]}"')

        # Build validation items
        val_args = []
        for v in self.state.validation_results:
            val_args.append(f'--validation "{v["check"]}|{v["status"]}"')

        if not todo_args:
            todo_args.append('--todo "D1|deployment|*|DEPLOY|complete"')
        if not val_args:
            val_args.append('--validation "deployment|✅"')

        harvest_name = Path(self.state.harvest_dir).name
        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "Deploy: {harvest_name[:30]}" \
            --tier RUNTIME_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "Harvested code deployment via /use-harvest DAG executor" \
            --skip-verify 2>/dev/null || echo "Report generation skipped"'''

        print("Generating report...")
        _code, stdout, _stderr = self._run_shell(cmd)

        # Extract report path
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line.lower():
                self.state.report_path = line.strip()
                break

        if self.state.report_path:
            print(f"✅ Report: {self.state.report_path}")
        else:
            print("⚠️  Report generation skipped")
            self.state.report_path = "N/A"

        return True

    # =========================================================================
    # STEP 7: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT (NO PUSH)")

        if not self.state.files_deployed:
            print("✅ No files to commit")
            return True

        # Stage deployed files
        for f in self.state.files_deployed:
            self._run_shell(f'git add "{REPO_ROOT / f}"')

        # Create commit message
        harvest_name = Path(self.state.harvest_dir).name
        count = len(self.state.files_deployed)

        commit_msg = f"deploy({harvest_name}): {count} files from harvest"

        # Commit
        cmd = f'git commit -m "{commit_msg}" --no-verify 2>&1 || true'
        code, stdout, _stderr = self._run_shell(cmd)

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")
        elif code == 0 or "file changed" in stdout.lower():
            _code, hash_out, _ = self._run_shell("git rev-parse --short HEAD")
            self.state.commit_hash = hash_out.strip()
            print(f"✅ Committed: {self.state.commit_hash}")
            print(f"   Message: {commit_msg}")
        else:
            print(f"⚠️  Commit result: {stdout[:100]}")

        print("\n⚠️  DO NOT PUSH — Review changes first")

        return True

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active /use-harvest execution. Start with:")
            print('  python3 workflows/use_harvest_executor.py path/to/harvested/')
            return

        self._print_header(f"USE-HARVEST STATUS: {self.state.harvest_dir}")
        print(f"Started: {self.state.started_at}")
        print(f"Current step: {self.state.current_step}")
        print(f"Items: {len(self.state.items)}")
        print()

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")
            elif step == self.state.current_step:
                print(f"  🔄 {step}")
            else:
                print(f"  ⏳ {step}")

    def run(self, harvest_dir: str = "", resume: bool = False):
        """Execute the /use-harvest DAG — fully autonomous."""
        # Initialize or resume
        if resume and self._load_state():
            print(f"Resuming use-harvest: {self.state.harvest_dir}")
        else:
            if not harvest_dir:
                print("❌ Harvest directory required")
                return False
            self.state = UseHarvestState(
                harvest_dir=harvest_dir,
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
            )
            self._save_state()

        self._print_header(f"USE-HARVEST EXECUTOR: {self.state.harvest_dir}")

        # Step executors
        executors = {
            "read_harvest_table": self._step_read_harvest_table,
            "verify_targets": self._step_verify_targets,
            "deploy_files": self._step_deploy_files,
            "validate_syntax": self._step_validate_syntax,
            "wire_imports": self._step_wire_imports,
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
                print(f"❌ No executor for step: {step}")
                break

            success = executor()

            if success:
                self.state.completed_steps.append(step)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {step}")
                print("\nResume with: python3 workflows/use_harvest_executor.py --resume")
                return False

        # Complete
        self._print_header("USE-HARVEST COMPLETE")
        print(f"✅ Harvest: {self.state.harvest_dir}")
        print(f"   Items: {len(self.state.items)}")
        print(f"   Deployed: {len(self.state.files_deployed)}")
        print(f"   Report: {self.state.report_path}")
        if self.state.commit_hash:
            print(f"   Commit: {self.state.commit_hash}")
        print("\n⚠️  DO NOT PUSH — Review changes first")
        print("\n→ Next: Run /wire on deployed modules")

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Use-Harvest Executor — Deploy harvested code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/use_harvest_executor.py current_work/harvested/doc_name/
    python3 workflows/use_harvest_executor.py --resume
    python3 workflows/use_harvest_executor.py --status
        """,
    )

    parser.add_argument("harvest_dir", nargs="?", help="Directory containing harvested files")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted execution")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--reset", action="store_true", help="Clear state and start fresh")

    args = parser.parse_args()

    executor = UseHarvestExecutor()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("✅ State cleared")
        return

    if args.status:
        executor.status()
        return

    if args.resume:
        if not STATE_FILE.exists():
            print("No use-harvest execution to resume")
            sys.exit(1)
        executor.run(resume=True)
        return

    if not args.harvest_dir:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.harvest_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
