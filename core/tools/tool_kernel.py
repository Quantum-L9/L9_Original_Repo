# SPDX-License-Identifier: PROPRIETARY
# Copyright (c) 2024-2026 L9 Technologies
"""
Tool Execution Kernel - Canonical Entrypoint for ALL Tool Calls.

This module provides the ONLY authorized path for tool execution across L9.
All tool calls (MCP, AgentExecutor, Bootstrap) MUST route through execute_via_kernel().

Security Model (Fail-Closed):
- principal_id is MANDATORY (no implicit defaults)
- ALL calls route through ExecutorToolRegistry.guarded_execute()
- NO bypass paths, NO privilege escalation
- Audit trail for every tool invocation

ADR Compliance:
- ADR-0055: Fail-closed security model
- ADR-0013: Governance authority hierarchy
- ADR-0019: Structlog logging standard
- ADR-0083: UTC timezone standard

Architecture:
┌─────────────────────────────────────────┐
│   MCP │ Executor │ Bootstrap │ Others   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  execute_via_     │ ← CHOKE POINT
        │  kernel()         │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  guarded_execute │ ← ALWAYS ENFORCED
        │  • Sanitizer     │
        │  • Governance    │
        │  • Rate Limit    │
        │  • Timeout       │
        │  • Audit Trail   │
        └──────────────────┘

DORA Meta
  - Status: implemented
  - Phase: security-hardening
  - Component: tool-execution-kernel
  - Audit: mandatory-for-all-tool-calls
"""

from __future__ import annotations

import structlog

from core.schemas.tool_schemas import ToolInvocationRequest, ToolInvocationResult
from core.tools.registry_adapter import get_tool_registry_adapter

__all__ = [
    "SYSTEM_PRINCIPAL_ID",
    "execute_via_kernel",
]

logger = structlog.get_logger(__name__)

# System principal constant for EXPLICIT internal use only
# Bootstrap/health-check flows must EXPLICITLY pass this value
# Kernel NEVER injects this implicitly
SYSTEM_PRINCIPAL_ID = "system:l9-kernel"


async def execute_via_kernel(request: ToolInvocationRequest) -> ToolInvocationResult:
    """
    Canonical tool execution entrypoint. ALL tool calls route through here.

    This function enforces:
    - Kernel-aware governance (mandatory, no bypass)
    - Input sanitization via ExecutorToolRegistry
    - Rate limiting per tool/principal
    - Timeout enforcement
    - Tool audit trail in memory substrate
    - Normalized ToolInvocationResult

    Security Model (Fail-Closed):
    - principal_id is MANDATORY (must be present in request)
    - NO implicit fallback to SYSTEM_PRINCIPAL_ID
    - Raises RuntimeError if principal_id is missing/empty/whitespace
    - Internal flows MUST explicitly pass SYSTEM_PRINCIPAL_ID at callsite

    Args:
        request: ToolInvocationRequest containing:
            - tool_id: Tool identifier (must be registered)
            - arguments: Tool-specific arguments (sanitized by registry)
            - context: Execution context (agent_id, thread_id, etc.)
            - principal_id: MANDATORY - who authorized this execution
            - agent: Optional agent instance (for kernel-aware governance)

    Returns:
        ToolInvocationResult: Normalized result with:
            - success: True if tool executed successfully
            - output: Tool output (JSON-serializable)
            - error: Error message if success=False
            - metadata: Execution metadata (duration, audit trail, etc.)

    Raises:
        RuntimeError: If principal_id is missing, empty, or whitespace (fail-closed)
        ValueError: If tool_id is invalid or arguments fail sanitization
        TimeoutError: If tool execution exceeds configured timeout
        PermissionError: If governance denies execution

    Example (MCP):
        >>> request = ToolInvocationRequest(
        ...     tool_id="memory_write",
        ...     arguments={"content": "test", "segment": "working"},
        ...     context={"mcp_session": "abc123"},
        ...     principal_id="user:alice"  # EXPLICIT
        ... )
        >>> result = await execute_via_kernel(request)

    Example (Bootstrap - Explicit System Principal):
        >>> request = ToolInvocationRequest(
        ...     tool_id="health_check",
        ...     arguments={},
        ...     context={"bootstrap": True},
        ...     principal_id=SYSTEM_PRINCIPAL_ID  # EXPLICIT
        ... )
        >>> result = await execute_via_kernel(request)

    Example (WRONG - Implicit Escalation):
        >>> request = ToolInvocationRequest(
        ...     tool_id="memory_write",
        ...     arguments={"content": "test"},
        ...     principal_id=None  # MISSING
        ... )
        >>> result = await execute_via_kernel(request)
        RuntimeError: principal_id is required for tool execution...
    """
    # Fail-closed: principal_id is MANDATORY
    # Hardened: rejects None, non-string, empty, and whitespace-only
    if (
        request.principal_id is None
        or not isinstance(request.principal_id, str)
        or not request.principal_id.strip()
    ):
        logger.error(
            "tool_kernel_principal_missing",
            tool_id=request.tool_id,
            context=request.context,
        )
        raise RuntimeError(
            "principal_id is required for tool execution. "
            "Internal flows must explicitly pass SYSTEM_PRINCIPAL_ID. "
            f"Tool: {request.tool_id}"
        )

    # Enforce namespaced principal format: user:, agent:, system:
    cleaned_principal = request.principal_id.strip()
    if not cleaned_principal.startswith(("user:", "agent:", "system:")):
        raise RuntimeError(
            f"Invalid principal_id format: '{request.principal_id}'. "
            "Expected namespaced format (user:, agent:, system:)."
        )

    logger.info(
        "tool_kernel_execute_start",
        tool_id=request.tool_id,
        principal_id=request.principal_id,
        context=request.context,
    )

    # Get registry singleton
    registry = get_tool_registry_adapter()

    # ALWAYS route through guarded_execute (no bypass, no fallback)
    # This enforces:
    # - Governance policies (via kernel-aware agent if provided)
    # - Input sanitization
    # - Rate limiting
    # - Timeout
    # - Audit trail
    try:
        result = await registry.guarded_execute(
            agent=request.agent,  # May be None for non-agent flows
            tool_id=request.tool_id,
            arguments=request.arguments,
            context=request.context,
            principal_id=cleaned_principal,
        )

        logger.info(
            "tool_kernel_execute_success",
            tool_id=request.tool_id,
            principal_id=request.principal_id,
            success=result.success,
        )

        return ToolInvocationResult(
            success=result.success,
            output=result.result,
            error=result.error,
            metadata={
                "tool_id": result.tool_id,
                "call_id": str(result.call_id),
                "duration_ms": result.duration_ms,
            },
        )

    except Exception as e:
        logger.error(
            "tool_kernel_execute_failed",
            tool_id=request.tool_id,
            principal_id=request.principal_id,
            error=str(e),
            exc_info=True,
        )
        raise
