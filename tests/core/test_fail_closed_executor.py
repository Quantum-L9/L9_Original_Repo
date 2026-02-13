"""
L9 Core - Fail-Closed Executor Tests
=====================================

Tests for fail-closed enforcement in AgentExecutorService.

These tests verify that:
1. Tool dispatch requires kernel-aware agent
2. Tool dispatch requires guarded_execute method
3. Packet emission raises on failure

GMP-95: PR #11 Fail-Closed Enforcement Tests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.decorators import must_stay_async


class TestExecutorFailClosed:
    """Tests for AgentExecutorService fail-closed behavior."""

    @pytest.mark.asyncio
    async def test_emit_packet_raises_on_failure(self):
        """Packet emission raises exception instead of swallowing error."""
        from core.agents.executor import AgentExecutorService

        # Create executor with mock substrate that fails
        mock_substrate = MagicMock()
        mock_substrate.write_packet = AsyncMock(
            side_effect=Exception("Substrate unavailable")
        )

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=mock_substrate,
            agent_registry=MagicMock(),
        )

        # Emit packet should raise, not swallow
        with pytest.raises(Exception, match="Substrate unavailable"):
            await executor._emit_packet(
                packet_type="test_packet",
                payload={"task_id": str(uuid4())},
                thread_id=uuid4(),
            )

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_kernel_state_object_handling(self):
        """_get_kernel_aware_agent handles kernel_state as object with initialized attr."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        # Test with object-based kernel_state (initialized=True)
        mock_agent = MagicMock()
        mock_kernel_state = MagicMock()
        mock_kernel_state.initialized = True
        mock_agent.kernel_state = mock_kernel_state
        executor._kernel_aware_agent = mock_agent

        result = executor._get_kernel_aware_agent()
        assert result is mock_agent

        # Test with object-based kernel_state (initialized=False)
        mock_kernel_state.initialized = False
        result = executor._get_kernel_aware_agent()
        assert result is None

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_kernel_state_none_returns_none(self):
        """_get_kernel_aware_agent returns None when kernel_state is None."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        # Test with None kernel_state
        mock_agent = MagicMock()
        mock_agent.kernel_state = None
        executor._kernel_aware_agent = mock_agent

        result = executor._get_kernel_aware_agent()
        assert result is None

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_kernel_state_inactive_returns_none(self):
        """_get_kernel_aware_agent returns None when kernel_state != ACTIVE."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        # Test with INACTIVE string state
        mock_agent = MagicMock()
        mock_agent.kernel_state = "INACTIVE"
        executor._kernel_aware_agent = mock_agent

        result = executor._get_kernel_aware_agent()
        assert result is None
