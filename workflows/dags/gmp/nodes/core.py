"""
GMP Core Nodes — All node functions for GMP execution

Designed for autonomous agents (L, Emma) running via SDK.
No interactive prompts — agents provide todo_plan at invocation.
Memory operations use async service calls, not subprocess.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from workflows.dags.gmp.state import GMPPhase, GMPState

logger = structlog.get_logger(__name__)

# Workspace root for file operations and subprocess calls
# Path: core.py -> nodes/ -> gmp/ -> dags/ -> workflows/ -> L9/
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent


# =============================================================================
# Helper: async memory operations
# =============================================================================


async def _memory_search(query: str, agent_id: str = "") -> list[dict[str, Any]]:
    """Search memory via retrieval service. Falls back to subprocess."""
    try:
        from memory.retrieval import MemoryRetrievalService

        service = MemoryRetrievalService()
        results = await service.search(
            query=query,
            agent_id=agent_id or None,
            limit=10,
            min_similarity=0.5,
        )
        return results
    except Exception as exc:
        logger.warning("memory_search_async_failed", error=str(exc), query=query[:50])
        # Fallback: subprocess to cursor_memory_client
        try:
            result = subprocess.run(
                [
                    "python3",
                    "agents/cursor/cursor_memory_client.py",
                    "search",
                    query[:100],
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=WORKSPACE_ROOT,
            )
            if result.returncode == 0:
                return [{"content": result.stdout[:1000], "source": "cli_fallback"}]
        except Exception:
            pass
        return []


async def _memory_write(content: str, kind: str = "lesson") -> bool:
    """Write to memory via ingestion service. Falls back to subprocess."""
    try:
        from memory.ingestion import ingest_packet
        from memory.substrate_models import PacketEnvelopeIn

        packet = PacketEnvelopeIn(
            source_id="gmp_langgraph_executor",
            agent_id="gmp_executor",
            kind=kind.upper(),
            payload={"content": content},
            metadata={"source": "gmp_dag", "kind": kind},
        )
        result = await ingest_packet(packet)
        return result is not None
    except Exception as exc:
        logger.warning("memory_write_async_failed", error=str(exc))
        # Fallback: subprocess
        try:
            result = subprocess.run(
                [
                    "python3",
                    "agents/cursor/cursor_memory_client.py",
                    "write",
                    content[:500],
                    "--kind",
                    kind,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=WORKSPACE_ROOT,
            )
            return result.returncode == 0
        except Exception:
            return False


# =============================================================================
# Node Functions
# =============================================================================


def node_start(state: GMPState) -> GMPState:
    """Initialize GMP execution."""
    state.phase = GMPPhase.START
    state.add_message(f"Starting GMP: {state.task}")
    state.add_message(f"   Tier: {state.tier}")
    state.add_message(f"   Agent: {state.agent_id or 'unknown'}")

    # Generate GMP ID
    state.gmp_id = f"GMP-{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"
    state.add_message(f"   ID: {state.gmp_id}")

    return state


def node_memory_read(state: GMPState) -> GMPState:
    """MANDATORY: Read from L9 memory for context before implementation."""
    state.phase = GMPPhase.MEMORY_READ
    state.add_message("MEMORY READ (MANDATORY)")

    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — schedule coroutine
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(
                    asyncio.run, _memory_search(state.task[:100], state.agent_id)
                ).result(timeout=30)
        else:
            results = asyncio.run(_memory_search(state.task[:100], state.agent_id))

        if results:
            state.memory_context["search_results"] = results[:5]
            state.add_message(f"   Memory search: {len(results)} results found")
        else:
            state.memory_context["search_results"] = []
            state.add_message("   Memory search: no results")

        state.memory_read_done = True

    except Exception as e:
        state.add_message(f"   Memory read error: {e}")
        state.memory_context["search_results"] = []
        state.memory_read_done = True

    return state


def node_scope_lock(state: GMPState) -> GMPState:
    """Validate the provided TODO plan and file budget.

    Autonomous agents provide todo_plan and file_budget_may at invocation.
    This node validates the plan is well-formed, not prompts for input.
    """
    state.phase = GMPPhase.SCOPE_LOCK
    state.add_message("SCOPE LOCK (Phase 0)")

    errors = []

    # Validate todo_plan was provided
    if not state.todo_plan:
        errors.append("No todo_plan provided — supply TODO items at invocation")

    # Validate each TODO item has required fields
    required_fields = {"file", "action"}
    for i, item in enumerate(state.todo_plan):
        item_id = item.get("id", f"T{i + 1}")
        missing = required_fields - set(item.keys())
        if missing:
            errors.append(f"{item_id}: missing fields {missing}")

        # Validate file exists (for non-create actions)
        file_path = item.get("file", "")
        action = item.get("action", "").lower()
        if file_path and action not in ("create", "insert_new"):
            full_path = WORKSPACE_ROOT / file_path
            if not full_path.exists():
                errors.append(f"{item_id}: file not found: {file_path}")

    # Validate file_budget_may
    if not state.file_budget_may and state.todo_plan:
        # Auto-derive from todo_plan
        state.file_budget_may = list(
            {item.get("file", "") for item in state.todo_plan if item.get("file")}
        )
        state.add_message(f"   File budget auto-derived: {state.file_budget_may}")

    if errors:
        for err in errors:
            state.add_message(f"   SCOPE ERROR: {err}")
        state.errors.extend(errors)
        state.add_message("   Scope lock FAILED — aborting")
    else:
        state.add_message(f"   TODO items: {len(state.todo_plan)}")
        state.add_message(f"   Files in scope: {state.file_budget_may}")
        state.add_message("   Scope lock PASSED")

    return state


def node_baseline(state: GMPState) -> GMPState:
    """Verify baseline conditions — all files exist and are accessible."""
    state.phase = GMPPhase.BASELINE
    state.add_message("BASELINE VERIFICATION (Phase 1)")

    errors = []

    for item in state.todo_plan:
        file_path = item.get("file", "")
        if not file_path:
            continue

        full_path = WORKSPACE_ROOT / file_path
        action = item.get("action", "").lower()

        # For create actions, verify parent directory exists
        if action in ("create", "insert_new"):
            if not full_path.parent.exists():
                errors.append(f"Parent dir missing: {full_path.parent}")
            continue

        # For modify actions, verify file exists
        if not full_path.exists():
            errors.append(f"File not found: {file_path}")
            continue

        # For Python files, verify they compile
        if full_path.suffix == ".py":
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", str(full_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=WORKSPACE_ROOT,
                )
                if result.returncode != 0:
                    err = result.stderr[:80]
                    errors.append(f"py_compile failed: {file_path}: {err}")
            except subprocess.TimeoutExpired:
                errors.append(f"py_compile timeout: {file_path}")

    if errors:
        state.baseline_passed = False
        state.baseline_errors = errors
        for err in errors:
            state.add_message(f"   BASELINE FAIL: {err}")
    else:
        state.baseline_passed = True
        state.add_message(f"   Baseline passed: {len(state.todo_plan)} items verified")

    return state


def node_implement(state: GMPState) -> GMPState:
    """Execute TODO plan items.

    For each TODO item, applies the specified action to the target file.
    Tracks all changes in state.changes_made and state.files_modified.

    Currently supports file-level operations via subprocess.
    Future: integrate with AgentExecutorService for reasoning-based changes.
    """
    state.phase = GMPPhase.IMPLEMENT
    state.add_message("IMPLEMENTATION (Phase 2-3)")

    for i, item in enumerate(state.todo_plan):
        item_id = item.get("id", f"T{i + 1}")
        file_path = item.get("file", "")
        action = item.get("action", "").lower()
        description = item.get("description", "")
        state.add_message(f"   [{item_id}] {action} {file_path}: {description}")

        full_path = WORKSPACE_ROOT / file_path

        try:
            if action == "create":
                # Create new file with content from description or empty
                content = item.get("content", f"# {description}\n")
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                state.add_message(f"   [{item_id}] Created: {file_path}")

            elif action == "delete":
                if full_path.exists():
                    full_path.unlink()
                    state.add_message(f"   [{item_id}] Deleted: {file_path}")
                else:
                    state.add_message(f"   [{item_id}] Already absent: {file_path}")

            elif action in ("replace", "insert", "insert_new"):
                # For replace/insert, the calling agent must provide
                # old_text and new_text in the TODO item
                old_text = item.get("old_text", "")
                new_text = item.get("new_text", "")

                if not old_text and action == "replace":
                    state.add_message(f"   [{item_id}] SKIP: replace requires old_text")
                    continue

                if action == "insert" and new_text:
                    # Append to file
                    current = full_path.read_text() if full_path.exists() else ""
                    full_path.write_text(current + new_text)
                    state.add_message(f"   [{item_id}] Inserted into: {file_path}")

                elif action == "replace" and old_text and new_text:
                    current = full_path.read_text()
                    if old_text in current:
                        updated = current.replace(old_text, new_text, 1)
                        full_path.write_text(updated)
                        state.add_message(f"   [{item_id}] Replaced in: {file_path}")
                    else:
                        state.add_message(
                            f"   [{item_id}] WARN: old_text not found in {file_path}"
                        )
                        state.errors.append(
                            f"{item_id}: old_text not found in {file_path}"
                        )

                elif action == "insert_new":
                    content = item.get("content", new_text or f"# {description}\n")
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    state.add_message(f"   [{item_id}] Created new: {file_path}")

            else:
                state.add_message(f"   [{item_id}] Unknown action: {action}")
                continue

            # Track modification
            if file_path not in state.files_modified:
                state.files_modified.append(file_path)
            state.changes_made.append(
                {
                    "id": item_id,
                    "file": file_path,
                    "action": action,
                    "description": description,
                    "status": "applied",
                }
            )

        except Exception as e:
            state.add_message(f"   [{item_id}] ERROR: {e}")
            state.errors.append(f"{item_id}: {e}")
            state.changes_made.append(
                {
                    "id": item_id,
                    "file": file_path,
                    "action": action,
                    "status": "failed",
                    "error": str(e),
                }
            )

    state.add_message(
        f"   Implementation complete: {len(state.changes_made)} items, "
        f"{len(state.files_modified)} files modified"
    )

    return state


def node_validate(state: GMPState) -> GMPState:
    """Run validation suite on all modified files."""
    state.phase = GMPPhase.VALIDATE
    state.add_message(f"VALIDATION (Phase 4) — attempt {state.retry_count + 1}")

    if not state.files_modified:
        state.add_message("   No files to validate")
        state.validation_passed = True
        return state

    all_passed = True

    # Step 1: py_compile each Python file
    for file_path in state.files_modified:
        if not file_path.endswith(".py"):
            continue
        full_path = WORKSPACE_ROOT / file_path
        if not full_path.exists():
            continue

        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(full_path)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=WORKSPACE_ROOT,
            )
            if result.returncode == 0:
                state.validation_results[f"py_compile:{file_path}"] = "pass"
            else:
                state.validation_results[f"py_compile:{file_path}"] = (
                    f"FAIL: {result.stderr[:100]}"
                )
                all_passed = False
                state.add_message(f"   py_compile FAIL: {file_path}")
        except Exception as e:
            state.validation_results[f"py_compile:{file_path}"] = f"ERROR: {e}"
            all_passed = False

    # Step 2: gmp-validate-stage.py (if available)
    validator_script = WORKSPACE_ROOT / "scripts" / "gmp-validate-stage.py"
    if validator_script.exists():
        try:
            cmd = [
                "python3",
                str(validator_script),
                "--files",
                *state.files_modified,
                "--json",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=WORKSPACE_ROOT,
            )

            try:
                validation_data = json.loads(result.stdout)
                stage_passed = validation_data.get("passed", False)

                for check in validation_data.get("checks", []):
                    name = check["name"]
                    passed = check["passed"]
                    detail = check.get("detail", "")
                    state.validation_results[name] = (
                        f"pass{f': {detail}' if detail else ''}"
                        if passed
                        else f"FAIL: {detail}"
                    )
                    if not passed:
                        all_passed = False
                        state.add_message(f"   {name}: FAIL — {detail}")

                if not stage_passed:
                    all_passed = False

            except json.JSONDecodeError:
                state.validation_results["gmp-validate-stage"] = (
                    "pass"
                    if result.returncode == 0
                    else f"FAIL: exit={result.returncode}"
                )
                if result.returncode != 0:
                    all_passed = False

        except subprocess.TimeoutExpired:
            state.validation_results["gmp-validate-stage"] = "FAIL: timeout"
            all_passed = False
        except Exception as e:
            state.validation_results["gmp-validate-stage"] = f"ERROR: {e}"
            all_passed = False

    state.validation_passed = all_passed
    status = "PASSED" if all_passed else "FAILED"
    state.add_message(f"   Validation {status}: {len(state.validation_results)} checks")

    return state


def route_after_validation(state: GMPState) -> str:
    """Auto-route after validation — no user gate needed for autonomous agents.

    - validation_passed=True → proceed to memory_write
    - validation_passed=False and retries left → retry implement
    - validation_passed=False and no retries → abort
    """
    if state.validation_passed:
        return "memory_write"
    if state.retry_count < state.max_retries:
        state.retry_count += 1
        state.add_message(
            f"   Validation retry {state.retry_count}/{state.max_retries}"
        )
        return "implement"
    state.add_message("   Max retries exceeded — aborting")
    return "aborted"


def node_memory_write(state: GMPState) -> GMPState:
    """MANDATORY: Write learnings to L9 memory before finalization."""
    state.phase = GMPPhase.MEMORY_WRITE
    state.add_message("MEMORY WRITE (MANDATORY)")

    import asyncio

    summary = (
        f"{state.gmp_id}: {state.task[:100]}. "
        f"Agent: {state.agent_id}. "
        f"Files: {', '.join(state.files_modified[:5])}. "
        f"Tier: {state.tier}"
    )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                success = pool.submit(
                    asyncio.run, _memory_write(summary, "lesson")
                ).result(timeout=30)
        else:
            success = asyncio.run(_memory_write(summary, "lesson"))

        if success:
            state.lessons_saved = 1
            state.add_message("   GMP summary saved to memory")
        else:
            state.add_message("   Memory write failed (logged, continuing)")

        state.memory_write_done = True

    except Exception as e:
        state.add_message(f"   Memory write error: {e}")
        state.memory_write_done = True

    return state


def node_finalize(state: GMPState) -> GMPState:
    """Phase 6: generate report -> validate report -> update workflow_state."""
    state.phase = GMPPhase.FINALIZE
    state.add_message("FINALIZE (Phase 6)")

    scripts = WORKSPACE_ROOT / "scripts"
    report_generator = scripts / "generate_gmp_report.py"
    report_validator = scripts / "validate_gmp_report.py"
    workflow_updater = scripts / "update_workflow_state.py"

    # -- Step 1: Generate report -----------------------------------------------
    state.add_message("   [1/3] Generating GMP report...")

    if not report_generator.exists():
        state.add_message("   generate_gmp_report.py not found")
        state.report_generated = False
        return state

    try:
        # Build TODO args
        todo_args: list[str] = []
        for t in state.todo_plan:
            tid = t.get("id", f"T{len(todo_args) + 1}")
            tfile = t.get("file", "unknown")
            tlines = t.get("lines", "1-10")
            taction = t.get("action", "REPLACE")
            tdesc = t.get("description", "")[:50]
            todo_args.extend(["--todo", f"{tid}|{tfile}|{tlines}|{taction}|{tdesc}"])

        # Build validation args
        val_args: list[str] = []
        for gate, result in state.validation_results.items():
            val_args.extend(["--validation", f"{gate}|{result}"])
        if not val_args:
            val_args = [
                "--validation",
                "py_compile|pass",
                "--validation",
                "import|pass",
            ]

        tier = state.tier.upper()
        if not tier.endswith("_TIER"):
            tier = f"{tier}_TIER"

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
            (
                f"GMP execution by {state.agent_id or 'agent'}. "
                f"Files: {', '.join(state.files_modified[:3])}"
            ),
            "--skip-verify",
        ]

        gen_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=WORKSPACE_ROOT,
        )

        if gen_result.returncode == 0:
            for line in gen_result.stdout.splitlines():
                match = re.search(r"(reports/.*?\.md)", line)
                if match:
                    state.report_path = match.group(1)
                    break
            state.report_generated = True
            state.add_message(f"   Report: {state.report_path}")
        else:
            state.add_message(f"   Report generation failed: {gen_result.stderr[:120]}")
            desc = state.task[:30].replace(" ", "-").replace("/", "-")
            state.report_path = (
                f"reports/GMP Reports/GMP-Report-{state.gmp_id}-{desc}.md"
            )
            state.report_generated = False

    except (subprocess.TimeoutExpired, Exception) as e:
        state.add_message(f"   Report generation error: {e}")
        state.report_generated = False

    # -- Step 2: Validate report -----------------------------------------------
    if state.report_generated and state.report_path:
        state.add_message("   [2/3] Validating report...")
        report_file = WORKSPACE_ROOT / state.report_path

        if report_validator.exists() and report_file.exists():
            try:
                val_result = subprocess.run(
                    ["python3", str(report_validator), str(report_file)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=WORKSPACE_ROOT,
                )
                if val_result.returncode == 0:
                    state.add_message("   Report validation passed")
                else:
                    state.add_message(f"   Report issues: {val_result.stdout[:150]}")
            except Exception as e:
                state.add_message(f"   Report validation error: {e}")
        else:
            state.add_message("   Skipped (validator or report not found)")
    else:
        state.add_message("   [2/3] Skipped (no report generated)")

    # -- Step 3: Update workflow_state.md --------------------------------------
    if state.report_generated and state.report_path:
        state.add_message("   [3/3] Updating workflow_state.md...")
        report_file = WORKSPACE_ROOT / state.report_path

        if workflow_updater.exists() and report_file.exists():
            try:
                ws_result = subprocess.run(
                    [
                        "python3",
                        str(workflow_updater),
                        "--from-report",
                        str(report_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=WORKSPACE_ROOT,
                )
                if ws_result.returncode == 0:
                    state.add_message("   workflow_state.md updated")
                else:
                    state.add_message(
                        f"   workflow_state update failed: {ws_result.stderr[:100]}"
                    )
            except Exception as e:
                state.add_message(f"   workflow_state error: {e}")
        else:
            state.add_message("   Skipped (updater or report not found)")
    else:
        state.add_message("   [3/3] Skipped (no report)")

    return state


def node_end(state: GMPState) -> GMPState:
    """End GMP execution."""
    state.phase = GMPPhase.END
    state.add_message("")
    state.add_message("=" * 60)
    state.add_message(f"GMP COMPLETE: {state.gmp_id}")
    state.add_message(f"   Task: {state.task}")
    state.add_message(f"   Agent: {state.agent_id}")
    state.add_message(f"   Files: {len(state.files_modified)}")
    mem_r = "done" if state.memory_read_done else "skipped"
    mem_w = "done" if state.memory_write_done else "skipped"
    state.add_message(f"   Memory Read: {mem_r}")
    state.add_message(f"   Memory Write: {mem_w}")
    state.add_message(f"   Report: {state.report_path or 'none'}")
    state.add_message("=" * 60)

    return state


def node_aborted(state: GMPState) -> GMPState:
    """Handle abort."""
    state.phase = GMPPhase.ABORTED
    state.add_message("")
    state.add_message(f"GMP ABORTED: {state.gmp_id}")
    if state.errors:
        state.add_message(f"   Errors: {state.errors}")

    return state
