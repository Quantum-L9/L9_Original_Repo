"""
L9 TensorGlobe Bridge Adapter Tests
====================================

Contract-grade tests for TensorGlobeBridgeAdapter.

Acceptance criteria:
- Happy path: EOS approves, TensorGlobe returns valid response → success
- EOS deny: request denied → returns error tuple
- Invalid request: schema/signature fails → raises error
- Anomaly detected: critical anomaly → suspends provider
- Ledger events: all actions emit accountability events

Version: 1.0.0
ADR: 0013 (governance hierarchy), 0019 (structlog)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapters.tensorglobe_bridge.adapter import TensorGlobeBridgeAdapter
from adapters.tensorglobe_bridge.schemas import (
    AnomalySignal,
    TensorOperation,
    TensorRequest,
    TensorResponse,
    TensorResult,
)
from core.eos.schemas import Verdict, VerdictDecision

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_accountability():
    """Mock AccountabilityEngine."""
    mock = AsyncMock()
    # Default: approve requests
    mock.evaluate_action.return_value = (
        MagicMock(decision=MagicMock(value="approve")),
        [],
    )
    return mock


@pytest.fixture
def mock_substrate():
    """Mock MemorySubstrateService."""
    mock = AsyncMock()
    mock.write_evidence.return_value = "evidence_123"
    mock.write_audit_log.return_value = None
    return mock


@pytest.fixture
def mock_boundary():
    """Mock BoundaryEnforcer."""
    return MagicMock()


@pytest.fixture
def adapter(mock_accountability, mock_substrate, mock_boundary):
    """Create adapter with mocked dependencies."""
    return TensorGlobeBridgeAdapter(
        accountability_engine=mock_accountability,
        substrate_service=mock_substrate,
        boundary_enforcer=mock_boundary,
        tensorglobe_endpoint="https://tensorglobe.example.com/api",
        tensorglobe_auth_key="test_auth_key_123",
    )


@pytest.fixture
def valid_tensor_request():
    """Create a valid TensorRequest for testing."""
    return TensorRequest(
        request_id="req_001",
        domain_id="test_domain",
        entities=["entity_a", "entity_b"],
        operation=TensorOperation.SIMILARITY_SEARCH,
        requester_agent_id="agent_001",
        signature="valid_signature",
        signing_key_id="key_001",
    )


@pytest.fixture
def valid_tensor_response():
    """Create a valid TensorResponse for testing."""
    return TensorResponse(
        request_id="req_001",
        results=[
            TensorResult(
                entity_a="entity_a",
                entity_b="entity_b",
                score=0.85,
                confidence=0.9,
                uncertainty=0.1,
            )
        ],
        model_metadata={"model_id": "tensorglobe-v1", "version": "1.0"},
        latency_ms=100.0,
        batch_processing_time_ms=50.0,
        signature="response_signature",
        signing_key_id="tensorglobe_key_001",
    )


# =============================================================================
# Test: Happy Path - EOS Approves
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_happy_path(
    adapter,
    valid_tensor_request,
    valid_tensor_response,
    mock_accountability,
    mock_substrate,
):
    """
    Contract: Happy path - EOS approves, valid response returned.

    Verifies:
    - Request validated
    - EOS gate called
    - TensorGlobe called
    - Response validated
    - Evidence emitted to substrate
    - Ledger event emitted
    """
    # Patch signature verification (placeholder returns True) and TensorGlobe call
    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", return_value=valid_tensor_response
        ):
            success, response, error = await adapter.handle_tensor_request(
                valid_tensor_request, "agent_001"
            )

    assert success is True
    assert response is not None
    assert response.request_id == "req_001"
    assert error is None

    # Verify EOS was called
    mock_accountability.evaluate_action.assert_called_once()

    # Verify evidence was written
    mock_substrate.write_evidence.assert_called_once()

    # Verify audit log was written
    assert mock_substrate.write_audit_log.call_count >= 1


@pytest.mark.asyncio
async def test_handle_tensor_request_emits_success_ledger_event(
    adapter, valid_tensor_request, valid_tensor_response, mock_substrate
):
    """
    Contract: Successful request emits 'tensor_response_received' ledger event.
    """
    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", return_value=valid_tensor_response
        ):
            await adapter.handle_tensor_request(valid_tensor_request, "agent_001")

    # Check the last audit log call contains success event
    calls = mock_substrate.write_audit_log.call_args_list
    event_types = [call.args[0]["event_type"] for call in calls]
    assert "tensor_response_received" in event_types


# =============================================================================
# Test: EOS Denies Request
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_eos_denies(
    adapter, valid_tensor_request, mock_accountability
):
    """
    Contract: EOS deny → returns (False, None, error_message).

    Verifies:
    - EOS gate returns deny verdict
    - Adapter returns failure tuple
    - No TensorGlobe call is made
    """
    # Configure EOS to deny
    mock_accountability.evaluate_action.return_value = (
        MagicMock(decision=MagicMock(value="deny")),
        ["insufficient_capability"],
    )

    with patch.object(adapter, "_verify_request_signature", return_value=True):
        success, response, error = await adapter.handle_tensor_request(
            valid_tensor_request, "agent_001"
        )

    assert success is False
    assert response is None
    assert "EOS gate denied" in error
    assert "insufficient_capability" in error


@pytest.mark.asyncio
async def test_eos_deny_does_not_call_tensorglobe(
    adapter, valid_tensor_request, mock_accountability
):
    """
    Contract: When EOS denies, TensorGlobe is never called.
    """
    mock_accountability.evaluate_action.return_value = (
        MagicMock(decision=MagicMock(value="deny")),
        ["policy_violation"],
    )

    with patch.object(adapter, "_call_tensorglobe") as mock_call:
        await adapter.handle_tensor_request(valid_tensor_request, "agent_001")
        mock_call.assert_not_called()


# =============================================================================
# Test: Invalid Request (Schema/Signature)
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_invalid_signature(adapter, valid_tensor_request):
    """
    Contract: Invalid signature → returns failure.
    """
    with patch.object(adapter, "_verify_request_signature", return_value=False):
        success, response, error = await adapter.handle_tensor_request(
            valid_tensor_request, "agent_001"
        )

    assert success is False
    assert response is None
    assert "signature" in error.lower()


@pytest.mark.asyncio
async def test_handle_tensor_request_invalid_schema(adapter, valid_tensor_request):
    """
    Contract: Invalid schema → returns failure.
    """
    with patch.object(adapter, "_validate_request_schema", return_value=False):
        success, response, error = await adapter.handle_tensor_request(
            valid_tensor_request, "agent_001"
        )

    assert success is False
    assert response is None
    assert "schema" in error.lower()


# =============================================================================
# Test: Anomaly Detection
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_critical_anomaly_suspends_provider(
    adapter, valid_tensor_request, valid_tensor_response, mock_accountability
):
    """
    Contract: Critical anomaly detected → suspends provider, returns failure.
    """
    critical_anomaly = AnomalySignal(
        request_id="req_001",
        anomaly_type="confidence_collapse",
        anomaly_score=0.95,
        severity="critical",
        action_taken="suspend",
    )

    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", return_value=valid_tensor_response
        ):
            with patch.object(
                adapter.anomaly_detector, "detect", return_value=[critical_anomaly]
            ):
                with patch.object(adapter, "_suspend_provider") as mock_suspend:
                    success, response, error = await adapter.handle_tensor_request(
                        valid_tensor_request, "agent_001"
                    )

                    mock_suspend.assert_called_once()

    assert success is False
    assert response is None
    assert "suspended" in error.lower()


@pytest.mark.asyncio
async def test_handle_tensor_request_non_critical_anomaly_continues(
    adapter, valid_tensor_request, valid_tensor_response
):
    """
    Contract: Non-critical anomaly → logs warning but continues.
    """
    warning_anomaly = AnomalySignal(
        request_id="req_001",
        anomaly_type="latency_warning",
        anomaly_score=0.6,
        severity="medium",
        action_taken="downgrade",
    )

    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", return_value=valid_tensor_response
        ):
            with patch.object(
                adapter.anomaly_detector, "detect", return_value=[warning_anomaly]
            ):
                success, response, error = await adapter.handle_tensor_request(
                    valid_tensor_request, "agent_001"
                )

    # Non-critical should still succeed
    assert success is True
    assert response is not None


# =============================================================================
# Test: Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_exception_emits_failure_event(
    adapter, valid_tensor_request, mock_substrate
):
    """
    Contract: Exception during processing → emits 'tensor_request_failed' event.
    """
    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", side_effect=Exception("Network error")
        ):
            success, response, error = await adapter.handle_tensor_request(
                valid_tensor_request, "agent_001"
            )

    assert success is False
    assert "Network error" in error

    # Check failure event was logged
    calls = mock_substrate.write_audit_log.call_args_list
    event_types = [call.args[0]["event_type"] for call in calls]
    assert "tensor_request_failed" in event_types


@pytest.mark.asyncio
async def test_handle_tensor_request_timeout_handled(adapter, valid_tensor_request):
    """
    Contract: TensorGlobe timeout → returns failure with timeout message.
    """
    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter,
            "_call_tensorglobe",
            side_effect=ValueError("TensorGlobe timeout (5s exceeded)"),
        ):
            success, response, error = await adapter.handle_tensor_request(
                valid_tensor_request, "agent_001"
            )

    assert success is False
    assert "timeout" in error.lower()


# =============================================================================
# Test: Response Validation
# =============================================================================


@pytest.mark.asyncio
async def test_handle_tensor_request_invalid_response_signature(
    adapter, valid_tensor_request, valid_tensor_response
):
    """
    Contract: Invalid response signature → returns failure.
    """
    with patch.object(adapter, "_call_tensorglobe", return_value=valid_tensor_response):
        with patch.object(adapter, "_verify_response_signature", return_value=False):
            success, response, error = await adapter.handle_tensor_request(
                valid_tensor_request, "agent_001"
            )

    assert success is False
    assert "signature" in error.lower()


@pytest.mark.asyncio
async def test_handle_tensor_request_invalid_response_schema(
    adapter, valid_tensor_request, valid_tensor_response
):
    """
    Contract: Invalid response schema → returns failure.
    """
    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(
            adapter, "_call_tensorglobe", return_value=valid_tensor_response
        ):
            with patch.object(adapter, "_validate_response_schema", return_value=False):
                success, response, error = await adapter.handle_tensor_request(
                    valid_tensor_request, "agent_001"
                )

    assert success is False
    assert "schema" in error.lower()


# =============================================================================
# Public API
# =============================================================================

__all__ = []
