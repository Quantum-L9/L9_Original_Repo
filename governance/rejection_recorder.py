# governance/rejection_recorder.py
"""
Records "do not repeat" knowledge.
Every rejection is a lesson learned.
"""

from datetime import datetime
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
        "recorded_at": datetime.utcnow().isoformat(),
        "repo_id": repo_id,
    }

    try:
        memory_service.write(
            kind="FAILURE",
            content=rejection_record,
        )
    except Exception as e:
        # If write fails, log but don't crash
        print(f"[RejectionRecorder] failed to record: {e}")


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
