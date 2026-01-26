"""
Test: TensorGlobe adapter EOS gating
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapters.tensorglobe_bridge.adapter import TensorGlobeBridgeAdapter
from adapters.tensorglobe_bridge.schemas import (
    TensorOperation,
    TensorRequest,
)
from core.eos.schemas import Verdict, VerdictDecision


@pytest.fixture
def mock_accountability():
    return AsyncMock()


@pytest.fixture
def mock_substrate():
    return AsyncMock()


@pytest.fixture
def mock_boundary():
    return MagicMock()


@pytest.fixture
def adapter(mock_accountability, mock_substrate, mock_boundary):
    return TensorGlobeBridgeAdapter(
        accountability_engine=mock_accountability,
        substrate_service=mock_substrate,
        boundary_enforcer=mock_boundary,
        tensorglobe_endpoint="https://api.tensorglobe.io",
        tensorglobe_auth_key="test-key",
    )


@pytest.fixture
def sample_request():
    return TensorRequest(
        domain_id="domain-001",
        entities=["entity-a", "entity-b"],
        operation=TensorOperation.SIMILARITY_SEARCH,
        requester_agent_id="agent-001",
        signature="test_sig",
        signing_key_id="key-001",
    )


@pytest.mark.asyncio
async def test_eos_gate_allow(adapter, sample_request, mock_accountability):
    """Test that EOS ALLOW permits tensor call"""

    # Mock EOS verdict: ALLOW
    allowed_verdict = Verdict(
        action_id="action-123",
        decision=VerdictDecision.ALLOW,
        issuing_authority="L=CTO",
    )
    mock_accountability.evaluate_action.return_value = (allowed_verdict, [])

    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(adapter, "_validate_request_schema", return_value=True):
            with patch.object(adapter, "_validate_response_schema", return_value=True):
                with patch.object(
                    adapter, "_verify_response_signature", return_value=True
                ):
                    with patch.object(
                        adapter, "_call_tensorglobe", return_value=MagicMock()
                    ):
                        success, _response, error = await adapter.handle_tensor_request(
                            sample_request,
                            "agent-001",
                        )

    assert success is True
    assert error is None
    mock_accountability.evaluate_action.assert_called_once()


@pytest.mark.asyncio
async def test_eos_gate_deny(adapter, sample_request, mock_accountability):
    """Test that EOS DENY blocks tensor call"""

    # Mock EOS verdict: DENY
    denied_verdict = Verdict(
        action_id="action-123",
        decision=VerdictDecision.DENY,
        issuing_authority="L=CTO",
        justification_refs=["Missing capability"],
    )
    mock_accountability.evaluate_action.return_value = (
        denied_verdict,
        ["missing_capability"],
    )

    with patch.object(adapter, "_verify_request_signature", return_value=True):
        with patch.object(adapter, "_validate_request_schema", return_value=True):
            success, _response, error = await adapter.handle_tensor_request(
                sample_request,
                "agent-001",
            )

    assert success is False
    assert error is not None
    assert "missing_capability" in error
