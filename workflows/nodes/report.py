"""
Report Node — Generate final workflow report.

Summarizes all steps, artifacts, and results.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "report",
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

import time
from datetime import datetime

import structlog

from workflows.state import StepResult, WorkflowState

logger = structlog.get_logger(__name__)


@must_stay_async("callers use await")
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
    print(report_text)  # noqa: ADR-0019

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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-022",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "logging", "messaging", "operations", "service", "workflows"],
    "keywords": ["report"],
    "business_value": "Utility module for report",
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
