"""
Extract Node — Extract code blocks from source documents.

Uses sed for extraction (no manual code writing).
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Extract",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:21:53Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "extract",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.nodes.__init__"],
    },
}
# ============================================================================

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


@must_stay_async("callers use await")
async def extract_files_node(state: WorkflowState) -> dict:
    """
    Extract code blocks from source document to harvest directory.

    Uses sed to extract line ranges. Strips backticks if configured.

    Args:
        state: Current workflow state with extraction_patterns

    Returns:
        State update with files_extracted, results
    """
    start_time = time.time()
    step_id = "extract_files"

    source = state["source_document"]
    target_dir = state["harvest_directory"]
    patterns = state.get("extraction_patterns", [])
    working_dir = state.get("working_directory", str(Path.cwd()))

    logger.info(
        "extract.start",
        source=source,
        target_dir=target_dir,
        pattern_count=len(patterns),
    )

    # Ensure target directory exists
    target_path = Path(working_dir) / target_dir
    target_path.mkdir(parents=True, exist_ok=True)

    extracted_files: list[str] = []
    outputs: list[str] = []
    errors: list[str] = []

    for pattern in patterns:
        start_line = pattern["start_line"]
        end_line = pattern["end_line"]
        output_file = pattern["output_file"]
        strip_backticks = pattern.get("strip_backticks", True)

        output_path = f"{target_dir}/{output_file}"

        # Build sed command
        if strip_backticks:
            # Extract lines, remove first (```) and last (```) lines
            cmd = f"sed -n '{start_line},{end_line}p' \"{source}\" | sed '1d' | sed '$d' > \"{output_path}\""
        else:
            cmd = f'sed -n \'{start_line},{end_line}p\' "{source}" > "{output_path}"'

        code, _stdout, stderr = await _run_shell(cmd, working_dir)

        if code != 0:
            errors.append(f"Extract failed for {output_file}: {stderr}")
            logger.error("extract.failed", file=output_file, error=stderr)
            continue

        # Verify extraction
        verify_cmd = f'wc -l "{output_path}"'
        code, line_count, _ = await _run_shell(verify_cmd, working_dir)

        extracted_files.append(output_path)
        outputs.append(f"✓ {output_file} ({line_count.strip()})")
        logger.info("extract.file_done", file=output_file, lines=line_count.strip())

    duration_ms = (time.time() - start_time) * 1000
    success = len(errors) == 0

    result = StepResult(
        step_id=step_id,
        success=success,
        output="\n".join(outputs),
        error="; ".join(errors) if errors else None,
        duration_ms=duration_ms,
        artifacts={"extracted_count": len(extracted_files)},
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "extract.complete",
        success=success,
        extracted_count=len(extracted_files),
        duration_ms=duration_ms,
    )

    return {
        "files_extracted": extracted_files,
        "results": [result],
        "current_phase": "deploy" if success else "done",
        "should_continue": success,
        "error": result["error"],
        "messages": [
            {"role": "assistant", "content": f"Extracted {len(extracted_files)} files"}
        ],
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-021",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "filesystem",
        "logging",
        "messaging",
        "operations",
        "service",
        "workflows",
    ],
    "keywords": ["extract", "files"],
    "business_value": "Utility module for extract",
    "last_modified": "2026-01-31T22:21:53Z",
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
