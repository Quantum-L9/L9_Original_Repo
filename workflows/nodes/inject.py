"""
Inject Node — Inject/replace code in existing files.

Uses sed for surgical modifications (no manual rewriting).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path

import structlog

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


async def inject_files_node(state: WorkflowState) -> dict:
    """
    Inject or replace content in existing files.

    Operations:
        - inject: Insert content after specified line/pattern
        - replace: Delete line range, then insert content

    Uses sed -i for in-place modification (macOS compatible).

    Args:
        state: Current workflow state with file_mappings

    Returns:
        State update with files_modified, results
    """
    start_time = time.time()
    step_id = "inject_files"

    mappings = state.get("file_mappings", [])
    working_dir = state.get("working_directory", str(Path.cwd()))

    # Filter to inject/replace operations
    modify_mappings = [
        m for m in mappings if m.get("operation") in ("inject", "replace")
    ]

    logger.info(
        "inject.start",
        total_mappings=len(mappings),
        modify_mappings=len(modify_mappings),
    )

    modified_files: list[str] = []
    outputs: list[str] = []
    errors: list[str] = []

    for mapping in modify_mappings:
        source = mapping["source"]
        destination = mapping["destination"]
        operation = mapping["operation"]

        if operation == "inject":
            # Inject after line or pattern
            after_line = mapping.get("after_line")
            after_pattern = mapping.get("after_pattern")

            if after_line:
                # sed -i '' 'Nr source_file' destination
                # macOS sed uses -i '' for in-place edit
                cmd = f"sed -i '' '{after_line}r {source}' \"{destination}\""
                location = f"line {after_line}"
            elif after_pattern:
                cmd = f"sed -i '' '/{after_pattern}/r {source}' \"{destination}\""
                location = f"pattern '{after_pattern}'"
            else:
                errors.append(
                    f"Inject requires after_line or after_pattern: {destination}"
                )
                continue

            code, _stdout, stderr = await _run_shell(cmd, working_dir)

            if code != 0:
                errors.append(f"Inject failed: {source} → {destination}: {stderr}")
                logger.error(
                    "inject.failed", source=source, dest=destination, error=stderr
                )
                continue

            modified_files.append(destination)
            outputs.append(f"✓ Injected {source} → {destination} after {location}")
            logger.info(
                "inject.file_modified",
                source=source,
                dest=destination,
                location=location,
            )

        elif operation == "replace":
            # Replace line range: delete lines, then insert
            start_line = mapping.get("start_line")
            end_line = mapping.get("end_line")

            if not start_line or not end_line:
                errors.append(
                    f"Replace requires start_line and end_line: {destination}"
                )
                continue

            # Step 1: Delete the line range
            delete_cmd = f"sed -i '' '{start_line},{end_line}d' \"{destination}\""
            code, _, stderr = await _run_shell(delete_cmd, working_dir)

            if code != 0:
                errors.append(f"Delete failed in {destination}: {stderr}")
                logger.error("inject.delete_failed", dest=destination, error=stderr)
                continue

            # Step 2: Insert source content at (start_line - 1)
            insert_line = start_line - 1
            insert_cmd = f"sed -i '' '{insert_line}r {source}' \"{destination}\""
            code, _, stderr = await _run_shell(insert_cmd, working_dir)

            if code != 0:
                errors.append(f"Insert failed in {destination}: {stderr}")
                logger.error("inject.insert_failed", dest=destination, error=stderr)
                continue

            modified_files.append(destination)
            outputs.append(
                f"✓ Replaced {destination}:{start_line}-{end_line} with {source}"
            )
            logger.info(
                "inject.file_replaced",
                source=source,
                dest=destination,
                start=start_line,
                end=end_line,
            )

    duration_ms = (time.time() - start_time) * 1000
    success = len(errors) == 0

    result = StepResult(
        step_id=step_id,
        success=success,
        output="\n".join(outputs),
        error="; ".join(errors) if errors else None,
        duration_ms=duration_ms,
        artifacts={"modified_count": len(modified_files)},
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "inject.complete",
        success=success,
        modified_count=len(modified_files),
        duration_ms=duration_ms,
    )

    return {
        "files_modified": modified_files,
        "results": [result],
        "current_phase": "validate" if success else "done",
        "should_continue": success,
        "error": result["error"],
        "messages": [
            {"role": "assistant", "content": f"Modified {len(modified_files)} files"}
        ],
    }
