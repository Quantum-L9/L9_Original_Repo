"""
L9 Governance - Rejection Recorder Tests
=========================================

Contract-grade tests for rejection_recorder.py negative memory capture.

Acceptance criteria:
- record_rejection stores FAILURE with DO_NOT_REPEAT rule
- Write failures are logged but don't crash
- record_governance_violation wraps correctly
- record_test_failure wraps correctly
- All timestamps are ISO 8601 UTC
- repo_id scoping works

Version: 1.0.0
ADR: 0013 (governance hierarchy), 0019 (structlog)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from governance.rejection_recorder import (
    record_governance_violation,
    record_rejection,
    record_test_failure,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_memory_service() -> Mock:
    """Mock memory service for write isolation."""
    service = Mock()
    service.write = Mock(return_value=None)
    return service


# =============================================================================
# Test: record_rejection basic behavior
# =============================================================================


def test_record_rejection_writes_failure_artifact(mock_memory_service: Mock) -> None:
    """
    Contract: record_rejection stores FAILURE with DO_NOT_REPEAT rule.
    
    Verifies:
    - memory_service.write called with kind='FAILURE'
    - content includes reason, context, rule
    - recorded_at is ISO 8601 timestamp
    """
    reason = "test_failure"
    context = {"code": "print('hello')", "test": "test_example"}
    
    record_rejection(
        memory_service=mock_memory_service,
        reason=reason,
        context=context,
    )
    
    # Verify write was called
    mock_memory_service.write.assert_called_once()
    
    # Extract call arguments
    call_args = mock_memory_service.write.call_args
    assert call_args.kwargs["kind"] == "FAILURE"
    
    content = call_args.kwargs["content"]
    assert content["type"] == "FAILURE"
    assert content["reason"] == reason
    assert content["context"] == context
    assert content["rule"] == "DO_NOT_REPEAT"
    assert "recorded_at" in content
    
    # Verify timestamp is ISO 8601
    timestamp = content["recorded_at"]
    datetime.fromisoformat(timestamp)  # Should not raise


def test_record_rejection_includes_repo_id_when_provided(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: repo_id is included when provided.
    
    Verifies:
    - repo_id scoping works
    """
    record_rejection(
        memory_service=mock_memory_service,
        reason="test",
        context={},
        repo_id="L9",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["repo_id"] == "L9"


def test_record_rejection_repo_id_none_by_default(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: repo_id defaults to None.
    
    Verifies:
    - repo_id is optional
    """
    record_rejection(
        memory_service=mock_memory_service,
        reason="test",
        context={},
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["repo_id"] is None


# =============================================================================
# Test: Error handling - write failures don't crash
# =============================================================================


def test_record_rejection_handles_write_failure_gracefully(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """
    Contract: Write failures are logged but don't crash.
    
    Verifies:
    - Exception from memory_service.write is caught
    - Error message printed
    - No exception raised to caller
    """
    mock_service = Mock()
    mock_service.write = Mock(side_effect=Exception("Redis connection failed"))
    
    # Should not raise
    record_rejection(
        memory_service=mock_service,
        reason="test",
        context={},
    )
    
    # Verify error was printed
    captured = capfd.readouterr()
    assert "[RejectionRecorder] failed to record" in captured.out
    assert "Redis connection failed" in captured.out


# =============================================================================
# Test: record_governance_violation wrapper
# =============================================================================


def test_record_governance_violation_calls_record_rejection(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: record_governance_violation wraps record_rejection correctly.
    
    Verifies:
    - Formats reason as 'governance_violation:{type}'
    - Includes code, violation, detail in context
    """
    record_governance_violation(
        memory_service=mock_memory_service,
        violation_type="protected_file_write",
        attempted_code="rm -rf /",
        reason="Attempted to modify protected file",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    
    assert content["reason"] == "governance_violation:protected_file_write"
    assert content["context"]["code"] == "rm -rf /"
    assert content["context"]["violation"] == "protected_file_write"
    assert content["context"]["detail"] == "Attempted to modify protected file"


def test_record_governance_violation_with_repo_id(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: record_governance_violation passes repo_id.
    
    Verifies:
    - repo_id scoping works
    """
    record_governance_violation(
        memory_service=mock_memory_service,
        violation_type="rate_limit",
        attempted_code=None,
        reason="Rate limit exceeded",
        repo_id="L9",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["repo_id"] == "L9"


def test_record_governance_violation_with_none_code(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: attempted_code can be None.
    
    Verifies:
    - None code is stored correctly
    """
    record_governance_violation(
        memory_service=mock_memory_service,
        violation_type="credential_leak",
        attempted_code=None,
        reason="Detected credentials in logs",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["context"]["code"] is None


# =============================================================================
# Test: record_test_failure wrapper
# =============================================================================


def test_record_test_failure_calls_record_rejection(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: record_test_failure wraps record_rejection correctly.
    
    Verifies:
    - Reason is 'test_failure'
    - Includes test_name, test_output, solution_attempted in context
    """
    record_test_failure(
        memory_service=mock_memory_service,
        test_name="test_promotion_rules",
        test_output="AssertionError: expected True, got False",
        attempted_solution="def should_promote(): return False",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    
    assert content["reason"] == "test_failure"
    assert content["context"]["test_name"] == "test_promotion_rules"
    assert "AssertionError" in content["context"]["test_output"]
    assert "def should_promote()" in content["context"]["solution_attempted"]


def test_record_test_failure_with_repo_id(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: record_test_failure passes repo_id.
    
    Verifies:
    - repo_id scoping works
    """
    record_test_failure(
        memory_service=mock_memory_service,
        test_name="test_example",
        test_output="FAILED",
        attempted_solution=None,
        repo_id="L9",
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["repo_id"] == "L9"


def test_record_test_failure_with_none_solution(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: attempted_solution can be None.
    
    Verifies:
    - None solution is stored correctly
    """
    record_test_failure(
        memory_service=mock_memory_service,
        test_name="test_example",
        test_output="FAILED",
        attempted_solution=None,
    )
    
    call_args = mock_memory_service.write.call_args
    content = call_args.kwargs["content"]
    assert content["context"]["solution_attempted"] is None


# =============================================================================
# Test: Integration - multiple rejection types
# =============================================================================


def test_multiple_rejections_are_independent(
    mock_memory_service: Mock,
) -> None:
    """
    Contract: Multiple rejections can be recorded independently.
    
    Verifies:
    - Each call is independent
    - No state pollution
    """
    record_rejection(
        memory_service=mock_memory_service,
        reason="first",
        context={"id": 1},
    )
    
    record_rejection(
        memory_service=mock_memory_service,
        reason="second",
        context={"id": 2},
    )
    
    assert mock_memory_service.write.call_count == 2
    
    # Verify each call had different content
    calls = mock_memory_service.write.call_args_list
    assert calls[0].kwargs["content"]["reason"] == "first"
    assert calls[1].kwargs["content"]["reason"] == "second"


# =============================================================================
# Public API
# =============================================================================

__all__ = []
