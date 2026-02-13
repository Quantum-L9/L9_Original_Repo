"""
Deploy Node — Copy extracted files to their destinations.

Uses cp for file operations (no manual writing).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path

import structlog

from core.decorators import must_stay_async
from workflows.state import StepResult, WorkflowState

logger = structlog.get_logger(__name__)


async def _run_shell(cmd: str, cwd: str) -> tuple[int, str, str]:
    """Run shell command asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@must_stay_async("callers use await")
async def deploy_files_node(state: WorkflowState) -> dict:
    """
    Copy extracted files to their target locations.

    Only handles "copy" operations. Inject/replace handled separately.

    Args:
        state: Current workflow state with file_mappings

    Returns:
        State update with files_copied, results
    """
    start_time = time.time()
    step_id = "deploy_files"

    mappings = state.get("file_mappings", [])
    working_dir = state.get("working_directory", str(Path.cwd()))

    # Filter to copy operations only
    copy_mappings = [m for m in mappings if m.get("operation") == "copy"]

    logger.info(
        "deploy.start",
        total_mappings=len(mappings),
        copy_mappings=len(copy_mappings),
    )

    copied_files: list[str] = []
    outputs: list[str] = []
    errors: list[str] = []

    for mapping in copy_mappings:
        source = mapping["source"]
        destination = mapping["destination"]

        # Ensure destination directory exists
        dest_path = Path(working_dir) / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        cmd = f'cp "{source}" "{destination}"'
        code, _stdout, stderr = await _run_shell(cmd, working_dir)

        if code != 0:
            errors.append(f"Copy failed: {source} → {destination}: {stderr}")
            logger.error(
                "deploy.copy_failed", source=source, dest=destination, error=stderr
            )
            continue

        copied_files.append(destination)
        outputs.append(f"✓ {source} → {destination}")
        logger.info("deploy.file_copied", source=source, dest=destination)

    duration_ms = (time.time() - start_time) * 1000
    success = len(errors) == 0

    result = StepResult(
        step_id=step_id,
        success=success,
        output="\n".join(outputs),
        error="; ".join(errors) if errors else None,
        duration_ms=duration_ms,
        artifacts={"copied_count": len(copied_files)},
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "deploy.complete",
        success=success,
        copied_count=len(copied_files),
        duration_ms=duration_ms,
    )

    # Check if there are inject/replace operations
    has_inject = any(m.get("operation") in ("inject", "replace") for m in mappings)
    next_phase = (
        "inject" if has_inject and success else ("validate" if success else "done")
    )

    return {
        "files_copied": copied_files,
        "results": [result],
        "current_phase": next_phase,
        "should_continue": success,
        "error": result["error"],
        "messages": [
            {"role": "assistant", "content": f"Deployed {len(copied_files)} files"}
        ],
    }
