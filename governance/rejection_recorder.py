# ============================================================================
__dora_meta__ = {
    "component_name": "Rejection Recorder",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "security",
    "domain": "governance",
    "module_name": "rejection_recorder",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "governance.__init__",
            "tests.governance.test_rejection_recorder",
        ],
    },
}
# ============================================================================

# governance/rejection_recorder.py
"""
Records "do not repeat" knowledge.
Every rejection is a lesson learned.
"""

from datetime import UTC, datetime
from typing import Any


def record_rejection(
    memory_service,
    reason: str,
    context: dict[str, Any],
    repo_id: str | None = None,
) -> None:
    """
    Record a rejected pattern or failed attempt.

    Args:
        memory_service: L9 memory substrate
        reason: why it was rejected ("governance_violation", "test_failure", etc)
        context: what was attempted (code, pattern, decision)
        repo_id: which repo (optional, for scoping)

    Effect: stores as FAILURE with DO_NOT_REPEAT rule
    """

    # Create memory artifact
    rejection_record = {
        "type": "FAILURE",
        "reason": reason,
        "context": context,
        "rule": "DO_NOT_REPEAT",
        "recorded_at": datetime.now(UTC).isoformat(),
        "repo_id": repo_id,
    }

    try:
        memory_service.write(
            kind="FAILURE",
            content=rejection_record,
        )
    except Exception as e:
        # If write fails, log but don't crash
        print(f"[RejectionRecorder] failed to record: {e}")  # noqa: ADR-0019


def record_governance_violation(
    memory_service,
    violation_type: str,
    attempted_code: str | None,
    reason: str,
    repo_id: str | None = None,
) -> None:
    """
    Special case: record governance rejections explicitly.
    """
    record_rejection(
        memory_service,
        reason=f"governance_violation:{violation_type}",
        context={
            "code": attempted_code,
            "violation": violation_type,
            "detail": reason,
        },
        repo_id=repo_id,
    )


def record_test_failure(
    memory_service,
    test_name: str,
    test_output: str,
    attempted_solution: str | None,
    repo_id: str | None = None,
) -> None:
    """
    Special case: record test-driven rejections.
    """
    record_rejection(
        memory_service,
        reason="test_failure",
        context={
            "test_name": test_name,
            "test_output": test_output,
            "solution_attempted": attempted_solution,
        },
        repo_id=repo_id,
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "GOV-SECU-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["governance", "security", "testing", "utility"],
    "keywords": [
        "failure",
        "governance",
        "record",
        "recorder",
        "rejection",
        "test",
        "violation",
    ],
    "business_value": "Utility module for rejection recorder",
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
