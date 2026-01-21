"""
L9 Agents - L-CTO Memory Emission Tests
=======================================

Tests for L-CTO agent direct memory emission:
- Agent emits PacketEnvelope with agent_id="l-cto"
- Memory emission is best-effort, non-blocking
- Packets use PacketEnvelope.yaml spec

Version: 1.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path (required for test imports)
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from unittest.mock import AsyncMock, patch

# Lazy imports - will be imported inside test functions


class TestLCTOMemoryEmission:
    """Test L-CTO agent memory emission."""

    @pytest.mark.asyncio
    async def test_emits_reasoning_packet_on_success(self):
        """Agent should emit reasoning packet after successful execution."""
        from agents.l_cto import LCTOAgent
        from agents.base_agent import AgentResponse

        agent = LCTOAgent(agent_id="test-l-cto")
        agent.kernel_state = "ACTIVE"  # Simulate activated agent

        task = {"message": "Test message"}
        response = AgentResponse(
            agent_id="test-l-cto",
            content="Test response",
            success=True,
            tokens_used=100,
            duration_ms=500,
        )

        # Mock substrate service
        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock()

        with patch("agents.l_cto.init_service", return_value=mock_substrate):
            await agent._emit_reasoning_packet(task, response, None)

        # Verify packet was emitted
        assert mock_substrate.write_packet.called
        call_args = mock_substrate.write_packet.call_args[0][0]

        assert call_args.packet_type == "agent.l_cto.reasoning"
        assert call_args.metadata.agent == "test-l-cto"
        assert call_args.metadata.schema_version == "1.0.0"
        assert call_args.payload["response"]["success"] is True

    @pytest.mark.asyncio
    async def test_emission_gracefully_handles_missing_service(self):
        """Emission should not fail if substrate service unavailable."""
        from agents.l_cto import LCTOAgent
        from agents.base_agent import AgentResponse

        agent = LCTOAgent(agent_id="test-l-cto")
        agent.kernel_state = "ACTIVE"

        task = {"message": "Test"}
        response = AgentResponse(agent_id="test-l-cto", content="Test", success=True)

        # Mock service unavailable
        with patch("agents.l_cto.init_service", side_effect=Exception("Service unavailable")):
            # Should not raise
            await agent._emit_reasoning_packet(task, response, None)

    @pytest.mark.asyncio
    async def test_emission_includes_task_and_response(self):
        """Packet payload should include task and response data."""
        from agents.l_cto import LCTOAgent
        from agents.base_agent import AgentResponse

        agent = LCTOAgent(agent_id="test-l-cto")
        agent.kernel_state = "ACTIVE"

        task = {"message": "Analyze code", "context": {"file": "test.py"}}
        response = AgentResponse(
            agent_id="test-l-cto",
            content="Analysis complete",
            success=True,
            tokens_used=200,
        )

        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock()

        with patch("agents.l_cto.init_service", return_value=mock_substrate):
            await agent._emit_reasoning_packet(task, response, {"extra": "context"})

        call_args = mock_substrate.write_packet.call_args[0][0]
        payload = call_args.payload

        assert "task" in payload
        assert payload["task"]["message"] == "Analyze code"
        assert "response" in payload
        assert payload["response"]["content"] == "Analysis complete"
        assert payload["agent_id"] == "test-l-cto"

    @pytest.mark.asyncio
    async def test_run_calls_emission(self):
        """LCTOAgent.run() should call _emit_reasoning_packet."""
        from agents.l_cto import LCTOAgent
        from agents.base_agent import AgentResponse

        agent = LCTOAgent(agent_id="test-l-cto")
        agent.kernel_state = "ACTIVE"

        # Mock LLM call
        mock_response = AgentResponse(
            agent_id="test-l-cto",
            content="Response",
            success=True,
        )

        with patch.object(agent, "call_llm", return_value=mock_response):
            with patch.object(agent, "_emit_reasoning_packet", new_callable=AsyncMock) as mock_emit:
                task = {"message": "Test"}
                await agent.run(task)

                # Verify emission was called
                assert mock_emit.called
                call_args = mock_emit.call_args
                assert call_args[0][0] == task  # task passed
                assert call_args[0][1] == mock_response  # response passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
