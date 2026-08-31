# SPDX-License-Identifier: PROPRIETARY
# Copyright (c) 2024-2026 L9 Technologies
"""
Tool Invocation Schemas for the Tool Execution Kernel.

These schemas define the canonical request/result types for execute_via_kernel().
They complement (but do not replace) ToolCallRequest/ToolCallResult in core.agents.schemas,
which are OpenAI-format types used by the executor loop.

DORA Meta
  - Status: implemented
  - Phase: security-hardening
  - Component: tool-invocation-schemas
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "ToolInvocationRequest",
    "ToolInvocationResult",
]


class ToolInvocationRequest(BaseModel):
    """
    Canonical request for execute_via_kernel().

    This is the kernel-level request type. All callers (MCP, Executor, Bootstrap)
    construct this before calling execute_via_kernel().

    Attributes:
        tool_id: Canonical tool identifier (must be registered).
        arguments: Tool-specific arguments (will be sanitized by registry).
        context: Execution context (agent_id, thread_id, source, etc.).
        principal_id: MANDATORY - who authorized this execution.
        agent: Optional kernel-aware agent instance (for governance checks).
    """

    tool_id: str = Field(..., description="Canonical tool identifier")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific arguments"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Execution context"
    )
    principal_id: str | None = Field(
        None,
        description="Principal authorizing execution (MANDATORY at runtime)",
    )
    agent: Any = Field(
        None,
        description="Optional kernel-aware agent instance",
        exclude=True,
    )

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class ToolInvocationResult(BaseModel):
    """
    Canonical result from execute_via_kernel().

    Wraps the outcome of a tool execution with normalized fields.

    Attributes:
        success: Whether the tool executed successfully.
        output: Tool output (JSON-serializable).
        error: Error message if success is False.
        metadata: Execution metadata (duration, audit trail, etc.).
    """

    success: bool = Field(..., description="Whether execution succeeded")
    output: Any = Field(None, description="Tool output")
    error: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )

    model_config = {"extra": "forbid"}
