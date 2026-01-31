"""
Report Node — Generate final workflow report.

Summarizes all steps, artifacts, and results.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog

from workflows.state import StepResult, WorkflowState

logger = structlog.get_logger(__name__)


async def report_node(state: WorkflowState) -> dict:
    """
    Generate final workflow report.

    Summarizes:
        - All step results
        - Files created/modified
        - Validation status
        - Total duration
        - Artifacts collected

    Args:
        state: Current workflow state

    Returns:
        State update with final report
    """
    start_time = time.time()
    step_id = "report"

    workflow_id = state.get("workflow_id", "unknown")
    workflow_name = state.get("workflow_name", "Workflow")
    started_at = state.get("started_at", "")

    results = state.get("results", [])
    files_extracted = state.get("files_extracted", [])
    files_copied = state.get("files_copied", [])
    files_modified = state.get("files_modified", [])
    validation_passed = state.get("validation_passed", False)
    error = state.get("error")

    # Build report
    lines = [
        "",
        "=" * 60,
        f"WORKFLOW REPORT: {workflow_name}",
        "=" * 60,
        "",
        f"ID:        {workflow_id}",
        f"Started:   {started_at}",
        f"Completed: {datetime.now().isoformat()}",
        f"Status:    {'✅ SUCCESS' if validation_passed and not error else '❌ FAILED'}",
        "",
    ]

    # Step results
    lines.append("STEPS:")
    lines.append("-" * 40)

    total_duration = 0.0
    for result in results:
        status = "✅" if result["success"] else "❌"
        duration = result.get("duration_ms", 0)
        total_duration += duration
        lines.append(f"  {status} {result['step_id']} ({duration:.0f}ms)")
        if result.get("error"):
            lines.append(f"     └─ Error: {result['error'][:60]}...")

    lines.append(f"\nTotal duration: {total_duration:.0f}ms")
    lines.append("")

    # Files
    lines.append("FILES:")
    lines.append("-" * 40)

    if files_extracted:
        lines.append(f"  Extracted: {len(files_extracted)}")
        for f in files_extracted[:5]:
            lines.append(f"    - {f}")
        if len(files_extracted) > 5:
            lines.append(f"    ... and {len(files_extracted) - 5} more")

    if files_copied:
        lines.append(f"  Deployed: {len(files_copied)}")
        for f in files_copied[:5]:
            lines.append(f"    - {f}")
        if len(files_copied) > 5:
            lines.append(f"    ... and {len(files_copied) - 5} more")

    if files_modified:
        lines.append(f"  Modified: {len(files_modified)}")
        for f in files_modified[:5]:
            lines.append(f"    - {f}")
        if len(files_modified) > 5:
            lines.append(f"    ... and {len(files_modified) - 5} more")

    lines.append("")

    # Validation
    lines.append("VALIDATION:")
    lines.append("-" * 40)
    lines.append(f"  Status: {'PASSED ✅' if validation_passed else 'FAILED ❌'}")

    if error:
        lines.append(f"  Error: {error}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    report_text = "\n".join(lines)

    # Print report
    print(report_text)

    duration_ms = (time.time() - start_time) * 1000

    result = StepResult(
        step_id=step_id,
        success=True,
        output=report_text,
        error=None,
        duration_ms=duration_ms,
        artifacts={
            "total_files": len(files_extracted)
            + len(files_copied)
            + len(files_modified),
            "total_duration_ms": total_duration,
            "validation_passed": validation_passed,
        },
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "report.generated",
        workflow_id=workflow_id,
        success=validation_passed and not error,
        total_files=len(files_extracted) + len(files_copied) + len(files_modified),
        total_duration_ms=total_duration,
    )

    return {
        "current_phase": "done",
        "should_continue": False,
        "results": [result],
        "artifacts": {"report": report_text},
        "messages": [{"role": "assistant", "content": "Workflow report generated"}],
    }
