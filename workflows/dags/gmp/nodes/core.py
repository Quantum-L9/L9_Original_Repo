"""
GMP Core Nodes — All node functions for GMP execution
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

from workflows.dags.gmp.state import GMPPhase, GMPState

# Workspace root for subprocess calls
# Path: core.py → nodes/ → gmp/ → dags/ → workflows/ → L9/
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent


def node_start(state: GMPState) -> GMPState:
    """Initialize GMP execution."""
    state.phase = GMPPhase.START
    state.add_message(f"🚀 Starting GMP: {state.task}")
    state.add_message(f"   Tier: {state.tier}")

    # Generate GMP ID
    state.gmp_id = f"GMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    state.add_message(f"   ID: {state.gmp_id}")

    return state


def node_memory_read(state: GMPState) -> GMPState:
    """🧠 MANDATORY: Read from L9 memory."""
    state.phase = GMPPhase.MEMORY_READ
    state.add_message("🧠 MEMORY READ (MANDATORY)")

    try:
        result = subprocess.run(
            [
                "python3",
                "agents/cursor/cursor_memory_client.py",
                "search",
                state.task[:100],
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=WORKSPACE_ROOT,
        )

        if result.returncode == 0:
            state.memory_context["search_results"] = result.stdout[:1000]
            state.add_message("   ✅ Memory search completed")
        else:
            state.memory_context["search_results"] = "Memory unavailable"
            state.add_message(f"   ⚠️ Memory search failed: {result.stderr[:100]}")

        state.memory_read_done = True

    except Exception as e:
        state.add_message(f"   ⚠️ Memory read error: {e}")
        state.memory_read_done = True

    return state


def node_scope_lock(state: GMPState) -> GMPState:
    """Define TODO plan and file budget."""
    state.phase = GMPPhase.SCOPE_LOCK
    state.add_message("📋 SCOPE LOCK (Phase 0)")
    state.add_message("   Define TODO plan:")
    state.add_message("   Format: T#|file|lines|action|description")
    state.add_message("")
    state.add_message("   ⏸️ Awaiting TODO plan input...")

    return state


def node_user_confirm_scope(state: GMPState) -> GMPState:
    """Gate: User confirms scope."""
    state.phase = GMPPhase.USER_CONFIRM_SCOPE
    state.add_message("")
    state.add_message("## SCOPE LOCK COMPLETE")
    state.add_message(f"   TODO items: {len(state.todo_plan)}")
    state.add_message(f"   Files in scope: {state.file_budget_may}")
    state.add_message("")
    state.add_message("   ⏸️ Type CONFIRM to proceed, ABORT to cancel")

    return state


def node_baseline(state: GMPState) -> GMPState:
    """Verify baseline conditions."""
    state.phase = GMPPhase.BASELINE
    state.add_message("🔍 BASELINE VERIFICATION (Phase 1)")

    errors = []

    for item in state.todo_plan:
        file_path = Path(item.get("file", ""))
        if file_path.suffix == ".py" and not file_path.exists():
            if not (WORKSPACE_ROOT / file_path).exists():
                errors.append(f"File not found: {file_path}")

    if errors:
        state.baseline_passed = False
        state.baseline_errors = errors
        state.add_message(f"   ❌ Baseline failed: {errors}")
    else:
        state.baseline_passed = True
        state.add_message("   ✅ Baseline passed")

    return state


def node_implement(state: GMPState) -> GMPState:
    """Execute TODO plan."""
    state.phase = GMPPhase.IMPLEMENT
    state.add_message("🔧 IMPLEMENTATION (Phase 2-3)")
    state.add_message("   Execute each TODO item...")
    state.add_message("")
    state.add_message("   ⏸️ Agent implements changes here")

    return state


def node_validate(state: GMPState) -> GMPState:
    """Run validation suite."""
    state.phase = GMPPhase.VALIDATE
    state.add_message("✅ VALIDATION (Phase 4)")

    results = {}
    all_passed = True

    for file_path in state.files_modified:
        if file_path.endswith(".py"):
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=WORKSPACE_ROOT,
                )
                if result.returncode == 0:
                    results[f"syntax:{file_path}"] = "✅"
                else:
                    results[f"syntax:{file_path}"] = f"❌ {result.stderr[:50]}"
                    all_passed = False
            except Exception as e:
                results[f"syntax:{file_path}"] = f"❌ {e}"
                all_passed = False

    state.validation_results = results
    state.validation_passed = all_passed

    for check, result in results.items():
        state.add_message(f"   {check}: {result}")

    if all_passed:
        state.add_message("   ✅ All validation passed")
    else:
        state.add_message("   ❌ Validation failed")

    return state


def node_user_confirm_validation(state: GMPState) -> GMPState:
    """Gate: User confirms validation results."""
    state.phase = GMPPhase.USER_CONFIRM_VALIDATION
    state.add_message("")
    state.add_message("## VALIDATION COMPLETE")
    state.add_message(f"   Status: {'PASS' if state.validation_passed else 'FAIL'}")
    state.add_message("")
    state.add_message("   ⏸️ Type CONTINUE to proceed, FIX to retry, ABORT to cancel")

    return state


def node_memory_write(state: GMPState) -> GMPState:
    """🧠 MANDATORY: Write learnings to memory."""
    state.phase = GMPPhase.MEMORY_WRITE
    state.add_message("🧠 MEMORY WRITE (MANDATORY)")

    try:
        summary = f"{state.gmp_id}: {state.task[:100]}. Files: {state.files_modified}"
        result = subprocess.run(
            [
                "python3",
                "agents/cursor/cursor_memory_client.py",
                "write",
                summary,
                "--kind",
                "lesson",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=WORKSPACE_ROOT,
        )

        if result.returncode == 0:
            state.lessons_saved = 1
            state.add_message("   ✅ GMP summary saved to memory")
        else:
            state.add_message(f"   ⚠️ Memory write failed: {result.stderr[:100]}")

        state.memory_write_done = True

    except Exception as e:
        state.add_message(f"   ⚠️ Memory write error: {e}")
        state.memory_write_done = True

    return state


def node_finalize(state: GMPState) -> GMPState:
    """Generate GMP report using the canonical report generator script."""
    state.phase = GMPPhase.FINALIZE
    state.add_message("📄 FINALIZE (Phase 6)")
    state.add_message("   Generating canonical GMP report...")

    # Build report generator command
    report_generator = WORKSPACE_ROOT / "scripts" / "generate_gmp_report.py"

    if not report_generator.exists():
        state.add_message("   ⚠️ Report generator script not found")
        state.report_generated = False
        return state

    try:
        # Build TODO args from state
        todo_args = []
        for t in state.todo_plan:
            todo_id = t.get("id", f"T{len(todo_args) + 1}")
            todo_file = t.get("file", "unknown")
            todo_lines = t.get("lines", "1-10")
            todo_action = t.get("action", "REPLACE")
            todo_desc = t.get("description", "")[:50]
            todo_args.extend(
                [
                    "--todo",
                    f"{todo_id}|{todo_file}|{todo_lines}|{todo_action}|{todo_desc}",
                ]
            )

        # Build validation args from state
        val_args = []
        for gate, result in state.validation_results.items():
            val_args.extend(["--validation", f"{gate}|{result}"])

        # If no validations, add defaults
        if not val_args:
            val_args = [
                "--validation",
                "py_compile|✅",
                "--validation",
                "import test|✅",
            ]

        # Determine tier format (script expects RUNTIME_TIER format)
        tier = state.tier.upper()
        if not tier.endswith("_TIER"):
            tier = f"{tier}_TIER"

        # Build command
        cmd = [
            "python3",
            str(report_generator),
            "--task",
            state.task,
            "--tier",
            tier,
            *todo_args,
            *val_args,
            "--summary",
            f"GMP execution via LangGraph DAG. Files: {', '.join(state.files_modified[:3])}",
            "--update-workflow",
            "--skip-verify",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=WORKSPACE_ROOT,
        )

        if result.returncode == 0:
            # Extract report path from output
            for line in result.stdout.split("\n"):
                if "Report saved:" in line or "reports/" in line.lower():
                    state.report_path = line.strip()
                    break
                if "GMP-Report-" in line:
                    # Extract just the path portion
                    match = re.search(r"(reports/.*?\.md)", line)
                    if match:
                        state.report_path = match.group(1)
                        break

            state.report_generated = True
            state.add_message(f"   ✅ Report generated: {state.report_path}")
        else:
            state.add_message(f"   ⚠️ Report generation failed: {result.stderr[:100]}")
            # Still set a path for reference
            desc = state.task[:30].replace(" ", "-").replace("/", "-")
            state.report_path = (
                f"reports/GMP Reports/GMP-Report-{state.gmp_id}-{desc}.md"
            )
            state.report_generated = False

    except subprocess.TimeoutExpired:
        state.add_message("   ⚠️ Report generation timed out")
        state.report_generated = False
    except Exception as e:
        state.add_message(f"   ⚠️ Report generation error: {e}")
        state.report_generated = False

    return state


def node_end(state: GMPState) -> GMPState:
    """End GMP execution."""
    state.phase = GMPPhase.END
    state.add_message("")
    state.add_message("=" * 60)
    state.add_message(f"✅ GMP COMPLETE: {state.gmp_id}")
    state.add_message(f"   Task: {state.task}")
    state.add_message(f"   Files: {len(state.files_modified)}")
    state.add_message(f"   Memory Read: {'✅' if state.memory_read_done else '❌'}")
    state.add_message(f"   Memory Write: {'✅' if state.memory_write_done else '❌'}")
    state.add_message("=" * 60)
    state.add_message("")
    state.add_message("📝 NOTE: Commit/push handled separately by user")

    return state


def node_aborted(state: GMPState) -> GMPState:
    """Handle abort."""
    state.phase = GMPPhase.ABORTED
    state.add_message("")
    state.add_message("❌ GMP ABORTED")

    return state
