"""
L9 ActionTool Orchestrator - Interface
Version: 1.0.0

Validates and executes tools, retries, safety, logs tool packets.
"""

from typing import Protocol, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from core.decorators import must_stay_async


class ToolSafetyLevel(str, Enum):
    """Tool safety levels."""

    SAFE = "safe"
    REQUIRES_APPROVAL = "requires_approval"
    DANGEROUS = "dangerous"


class ActionToolRequest(BaseModel):
    """Request to action_tool orchestrator."""

    tool_id: str = Field(default="", description="Canonical tool identity")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    max_retries: int = Field(default=3, description="Max retry attempts")
    require_approval: bool = Field(default=False, description="Require human approval")


class ActionToolResponse(BaseModel):
    """Response from action_tool orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool execution result"
    )
    retries_used: int = Field(default=0, description="Number of retries used")
    safety_level: ToolSafetyLevel = Field(
        default=ToolSafetyLevel.SAFE, description="Safety assessment"
    )


class IActionToolOrchestrator(Protocol):
    """Interface for ActionTool Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: ActionToolRequest) -> ActionToolResponse:
        """Execute action_tool orchestration."""
        ...
