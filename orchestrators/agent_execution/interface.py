"""
L9 Agent Execution Orchestrator - Interface
Version: 1.0.0

Orchestrates Mac Agent task execution from file-based queue.
"""


from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from core.decorators import must_stay_async


class TaskExecutionStatus(str, Enum):
    """Task execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentExecutionRequest(BaseModel):
    """Request to agent_execution orchestrator."""

    task_id: str = Field(..., description="Task identifier")
    task_type: str = Field(default="mac_task", description="Task type (mac_task only)")
    steps: list[dict[str, Any]] = Field(
        default_factory=list, description="Automation steps"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Task metadata")
    artifacts: list[dict[str, Any]] | None = Field(
        default=None, description="File artifacts"
    )


class AgentExecutionResponse(BaseModel):
    """Response from agent_execution orchestrator."""

    success: bool = Field(..., description="Whether execution succeeded")
    status: TaskExecutionStatus = Field(..., description="Final execution status")
    result: dict[str, Any] | None = Field(
        default=None, description="Execution result with logs, screenshots, data"
    )
    error: str | None = Field(None, description="Error message if failed")
    task_id: str = Field(..., description="Task identifier")


class IAgentExecutionOrchestrator(Protocol):
    """Interface for Agent Execution Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: AgentExecutionRequest) -> AgentExecutionResponse:
        """Execute Mac Agent task orchestration."""
        ...

    @must_stay_async("callers use await")
    async def poll_and_execute(self) -> None:
        """Poll queue and execute tasks (main loop)."""
        ...


# Runtime execution trace - updated automatically on every execution
