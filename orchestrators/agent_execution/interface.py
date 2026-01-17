"""
L9 Agent Execution Orchestrator - Interface
Version: 1.0.0

Orchestrates Mac Agent task execution from file-based queue.
"""

from typing import Protocol, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
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
    steps: list[Dict[str, Any]] = Field(
        default_factory=list, description="Automation steps"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")
    artifacts: Optional[list[Dict[str, Any]]] = Field(
        default=None, description="File artifacts"
    )


class AgentExecutionResponse(BaseModel):
    """Response from agent_execution orchestrator."""

    success: bool = Field(..., description="Whether execution succeeded")
    status: TaskExecutionStatus = Field(..., description="Final execution status")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Execution result with logs, screenshots, data"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
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
