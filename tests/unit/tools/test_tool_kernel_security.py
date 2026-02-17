# SPDX-License-Identifier: PROPRIETARY
# Copyright (c) 2024-2026 L9 Technologies
"""
Tool Kernel Security Invariant Tests.

Validates fail-closed security model:
- No implicit privilege escalation
- principal_id MANDATORY for all tool calls
- Kernel ALWAYS routes through guarded_execute
- No bypass paths exist

DORA Meta
  - Status: implemented
  - Phase: security-hardening
  - Component: tool-execution-kernel-tests
  - Coverage: security-invariants
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.schemas.tool_schemas import ToolInvocationRequest, ToolInvocationResult
from core.tools.tool_kernel import SYSTEM_PRINCIPAL_ID, execute_via_kernel

if TYPE_CHECKING:
    pass

__all__ = []


@pytest.mark.asyncio
async def test_kernel_fails_closed_without_principal():
    """
    SECURITY INVARIANT: Kernel MUST raise RuntimeError if principal_id is missing.
    No implicit escalation allowed.
    """
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test", "segment": "working"},
        context={"source": "test"},
        principal_id=None,  # MISSING
    )

    with pytest.raises(RuntimeError, match="principal_id is required"):
        await execute_via_kernel(request)


@pytest.mark.asyncio
async def test_kernel_fails_closed_with_empty_principal():
    """
    SECURITY INVARIANT: Kernel MUST raise RuntimeError if principal_id is empty string.
    """
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id="",  # EMPTY
    )

    with pytest.raises(RuntimeError, match="principal_id is required"):
        await execute_via_kernel(request)


@pytest.mark.asyncio
async def test_kernel_fails_closed_with_whitespace_principal():
    """
    SECURITY INVARIANT: Kernel MUST raise RuntimeError if principal_id is whitespace only.
    """
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id="   ",  # WHITESPACE ONLY
    )

    with pytest.raises(RuntimeError, match="principal_id is required"):
        await execute_via_kernel(request)


@pytest.mark.asyncio
async def test_no_implicit_privilege_escalation():
    """
    SECURITY INVARIANT: Kernel MUST NOT inject SYSTEM_PRINCIPAL_ID when principal missing.
    """
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id=None,  # MISSING
    )

    try:
        await execute_via_kernel(request)
        pytest.fail("Should have raised RuntimeError, not executed with system principal")
    except RuntimeError as e:
        # Verify error message indicates principal is required
        assert "principal_id is required" in str(e)
        assert "memory_write" in str(e)


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_kernel_routes_to_guarded_execute(mock_get_registry):
    """
    INVARIANT: Kernel ALWAYS routes through ExecutorToolRegistry.guarded_execute().
    No bypass paths allowed.
    """
    # Mock registry
    mock_registry = MagicMock()
    mock_registry.guarded_execute = AsyncMock(
        return_value=ToolCallResult(
            call_id=MagicMock(),
            tool_id="memory_write",
            success=True,
            result={"result": "test"},
        )
    )
    mock_get_registry.return_value = mock_registry

    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id="user:alice",
    )

    await execute_via_kernel(request)

    # Verify guarded_execute was called with correct args
    mock_registry.guarded_execute.assert_called_once()
    call_kwargs = mock_registry.guarded_execute.call_args.kwargs
    assert call_kwargs["tool_id"] == "memory_write"
    assert call_kwargs["arguments"] == {"content": "test"}
    assert call_kwargs["principal_id"] == "user:alice"


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_explicit_system_principal_allowed(mock_get_registry):
    """
    INVARIANT: Bootstrap flows CAN explicitly pass SYSTEM_PRINCIPAL_ID.
    But kernel must NOT inject it implicitly.
    """
    # Mock registry
    mock_registry = MagicMock()
    mock_registry.guarded_execute = AsyncMock(
        return_value=ToolCallResult(
            call_id=MagicMock(),
            tool_id="health_check",
            success=True,
            result={"status": "healthy"},
        )
    )
    mock_get_registry.return_value = mock_registry

    # Bootstrap flow explicitly passes system principal
    request = ToolInvocationRequest(
        tool_id="health_check",
        arguments={},
        context={"bootstrap": True},
        principal_id=SYSTEM_PRINCIPAL_ID,  # EXPLICIT
    )

    await execute_via_kernel(request)

    # Verify system principal was passed through correctly
    call_kwargs = mock_registry.guarded_execute.call_args.kwargs
    assert call_kwargs["principal_id"] == SYSTEM_PRINCIPAL_ID


def test_no_fallback_in_kernel_code():
    """
    CODE AUDIT: Verify kernel source contains NO implicit escalation patterns.
    """
    from pathlib import Path

    kernel_path = Path("core/tools/tool_kernel.py")
    assert kernel_path.exists(), "Kernel file must exist"

    content = kernel_path.read_text()

    # MUST NOT contain implicit fallback patterns
    assert "or SYSTEM_PRINCIPAL_ID" not in content, (
        "Kernel contains implicit privilege escalation: 'or SYSTEM_PRINCIPAL_ID'"
    )
    assert "request.principal_id or " not in content, (
        "Kernel contains implicit fallback on principal_id"
    )

    # MUST contain explicit fail-closed check
    assert "request.principal_id is None" in content, (
        "Kernel missing fail-closed principal check"
    )
    assert "raise RuntimeError" in content, (
        "Kernel missing RuntimeError for missing principal"
    )


@pytest.mark.asyncio
@patch("core.tools.tool_kernel.get_tool_registry_adapter")
async def test_kernel_preserves_error_context(mock_get_registry):
    """
    INVARIANT: Kernel must preserve error context when guarded_execute fails.
    """
    # Mock registry to raise PermissionError
    mock_registry = MagicMock()
    mock_registry.guarded_execute = AsyncMock(
        side_effect=PermissionError("Governance denied: insufficient privileges")
    )
    mock_get_registry.return_value = mock_registry

    request = ToolInvocationRequest(
        tool_id="sensitive_operation",
        arguments={"action": "delete"},
        context={"source": "test"},
        principal_id="user:alice",
    )

    with pytest.raises(PermissionError, match="Governance denied"):
        await execute_via_kernel(request)


# Import ToolCallResult for mock return values
from core.agents.schemas import ToolCallResult


# =========================================================================
# SUPERSEDING PATCH 5: Regression tests to catch future escalation
# =========================================================================


def test_no_executor_escalation():
    """
    REGRESSION GUARD: Executor MUST NOT contain bootstrap escalation to SYSTEM.
    If both SYSTEM_PRINCIPAL_ID and bootstrap appear together, escalation has crept back.
    """
    from pathlib import Path

    executor_path = Path("core/agents/executor.py")
    content = executor_path.read_text()

    assert "SYSTEM_PRINCIPAL_ID" not in content or "bootstrap" not in content, (
        "Executor contains bootstrap escalation pattern. "
        "Bootstrap flows must construct principal_id at callsite."
    )


def test_no_mcp_default_internal_true():
    """
    REGRESSION GUARD: MCP server MUST NOT use get("internal", True).
    Default True = silent escalation.
    """
    from pathlib import Path

    mcp_path = Path("mcp_memory/src/mcp_server.py")
    content = mcp_path.read_text()

    assert 'get("internal", True)' not in content, (
        "MCP server contains implicit internal escalation: "
        'get("internal", True) defaults to system principal.'
    )


@pytest.mark.asyncio
async def test_kernel_rejects_non_namespaced_principal():
    """
    SECURITY INVARIANT: Kernel MUST reject principal_id without namespace prefix.
    Valid: user:alice, agent:l-cto, system:l9-memory
    Invalid: alice, admin, root
    """
    request = ToolInvocationRequest(
        tool_id="memory_write",
        arguments={"content": "test"},
        context={"source": "test"},
        principal_id="alice",  # NO NAMESPACE
    )

    with pytest.raises(RuntimeError, match="Invalid principal_id format"):
        await execute_via_kernel(request)
