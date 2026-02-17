# SPDX-License-Identifier: PROPRIETARY
# Copyright (c) 2024-2026 L9 Technologies
"""
Tool Kernel Integration Tests.

End-to-end validation of convergence funnel:
- MCP -> kernel -> registry -> tool execution
- Executor -> kernel -> registry -> tool execution
- Bootstrap flows with explicit system principal

DORA Meta
  - Status: implemented
  - Phase: security-hardening
  - Component: tool-kernel-integration-tests
  - Coverage: end-to-end-flows
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.schemas.tool_schemas import ToolInvocationRequest, ToolInvocationResult
from core.tools.tool_kernel import SYSTEM_PRINCIPAL_ID

if TYPE_CHECKING:
    pass

__all__ = []


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_bootstrap_explicit_system_principal(mock_get_registry):
    """
    E2E: Bootstrap flow with explicit SYSTEM_PRINCIPAL_ID
    """
    from core.agents.schemas import ToolCallResult
    from core.tools.tool_kernel import execute_via_kernel

    # Mock registry
    mock_registry = MagicMock()
    mock_registry.guarded_execute = AsyncMock(
        return_value=ToolCallResult(
            call_id=MagicMock(),
            tool_id="infrastructure_health_check",
            success=True,
            result={"status": "healthy", "checks": ["postgres", "redis", "neo4j"]},
        )
    )
    mock_get_registry.return_value = mock_registry

    # Bootstrap flow explicitly passes system principal
    request = ToolInvocationRequest(
        tool_id="infrastructure_health_check",
        arguments={},
        context={"bootstrap": True, "phase": "init"},
        principal_id=SYSTEM_PRINCIPAL_ID,  # EXPLICIT
    )

    result = await execute_via_kernel(request)

    # Verify system principal was used
    call_kwargs = mock_registry.guarded_execute.call_args.kwargs
    assert call_kwargs["principal_id"] == SYSTEM_PRINCIPAL_ID

    # Verify health check executed
    assert result.success is True


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_kernel_rejects_non_string_principal(mock_get_registry):
    """
    E2E: Kernel rejects non-string principal_id types.
    """
    from core.tools.tool_kernel import execute_via_kernel

    # Test with integer
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id=12345,  # type: ignore  # Non-string
    )

    with pytest.raises(RuntimeError, match="principal_id is required"):
        await execute_via_kernel(request)


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_kernel_propagates_context(mock_get_registry):
    """
    E2E: Kernel propagates context to guarded_execute.
    """
    from core.agents.schemas import ToolCallResult
    from core.tools.tool_kernel import execute_via_kernel

    # Mock registry
    mock_registry = MagicMock()
    mock_registry.guarded_execute = AsyncMock(
        return_value=ToolCallResult(
            call_id=MagicMock(),
            tool_id="memory_write",
            success=True,
            result={"written": True},
        )
    )
    mock_get_registry.return_value = mock_registry

    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test", "segment": "working"},
        context={"agent_id": "agent_test", "thread_id": "thread_123", "source": "test"},
        principal_id="user:alice",
    )

    await execute_via_kernel(request)

    # Verify context was passed through
    call_kwargs = mock_registry.guarded_execute.call_args.kwargs
    assert call_kwargs["context"]["agent_id"] == "agent_test"
    assert call_kwargs["context"]["source"] == "test"
    assert call_kwargs["principal_id"] == "user:alice"
