"""
L9 Agent Execution Orchestrator - Interface
Version: 1.0.0

Orchestrates Mac Agent task execution from file-based queue.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Interface",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "interface",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-028",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "data-models", "enum", "intelligence", "messaging", "orchestration", "pydantic", "queue", "validation"],
    "keywords": ["agent", "execute", "execution", "interface", "orchestrator", "poll", "queue", "status"],
    "business_value": "Orchestrates Mac Agent task execution from file-based queue.",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
