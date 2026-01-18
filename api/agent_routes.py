"""
L9 Agent Routes
Background agent tasking and management endpoints.

Includes:
- /health - Agent system health check
- /status - Agent system status
- /task - Submit task to memory queue
- /execute - Execute task via AgentExecutorService (v2.2+)

Version: 1.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Routes",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "agent_routes",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /health", "GET /status", "POST /task", "POST /execute"],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "tests.smoke_test", "tests.smoke_test_root"],
    },
}
# ============================================================================

import structlog
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["agent"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ExecuteTaskRequest(BaseModel):
    """Request model for /execute endpoint."""

    agent_id: Optional[str] = Field(
        None, description="Target agent ID (uses default if not specified)"
    )
    kind: str = Field(
        default="query", description="Task kind: query, command, research, execution"
    )
    message: str = Field(..., description="User message or query")
    source_id: str = Field(default="api", description="Source identifier")
    thread_id: Optional[str] = Field(
        None, description="Thread identifier for conversation continuity"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    max_iterations: int = Field(
        default=10, ge=1, le=50, description="Max reasoning iterations"
    )

    model_config = {"extra": "forbid"}


class ExecuteTaskResponse(BaseModel):
    """Response model for /execute endpoint."""

    ok: bool = Field(..., description="Whether execution succeeded")
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(
        ..., description="Execution status: completed, failed, terminated, duplicate"
    )
    result: Optional[str] = Field(None, description="Agent response if completed")
    iterations: int = Field(default=0, description="Number of reasoning iterations")
    duration_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )
    error: Optional[str] = Field(None, description="Error message if failed")

    model_config = {"extra": "forbid"}


@router.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def agent_health():
    """Health check for agent layer."""
    return {"status": "ok", "service": "agent"}


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def agent_status():
    """Agent system status."""
    return {
        "status": "ready",
        "active_tasks": 0,
        "orchestrators": ["memory", "reasoning", "world_model"],
    }


@router.post("/task")
async def submit_task(
    payload: dict,
    _: bool = Depends(verify_api_key),
):
    """
    Submit a task to the agent system.

    Ingests task to memory and routes to orchestrator.

    Requires authentication via L9_EXECUTOR_API_KEY.
    """
    from uuid import uuid4
    from memory.ingestion import ingest_packet
    from core.schemas import PacketEnvelopeIn

    task_id = str(uuid4())
    logger.info("Task submitted: %s (id=%s)", payload.get("type", "unknown"), task_id)

    # Ingest task to memory (canonical ingestion point)
    try:
        packet_in = PacketEnvelopeIn(
            packet_type="agent_task_submitted",
            payload={
                "task_id": task_id,
                "task_type": payload.get("type", "unknown"),
                "task_payload": payload,
            },
            metadata={"agent": "api", "source": "agent_routes"},
        )
        await ingest_packet(packet_in)
    except Exception as e:
        logger.warning(f"Failed to ingest task to memory: {e}")
        # Don't fail the request if memory ingestion fails

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Task queued for processing and ingested to memory",
    }


@router.post("/execute", response_model=ExecuteTaskResponse)
async def execute_task(
    request: Request,
    body: ExecuteTaskRequest,
    _: bool = Depends(verify_api_key),
) -> ExecuteTaskResponse:
    """
    Execute a task via the AgentExecutorService.

    This endpoint provides synchronous agent execution:
    1. Creates an AgentTask from the request
    2. Submits to AgentExecutorService
    3. Waits for completion
    4. Returns the result

    For long-running tasks, consider using /task for async submission.

    Requires authentication via L9_EXECUTOR_API_KEY.

    Example:
        POST /agent/execute
        Authorization: Bearer {L9_EXECUTOR_API_KEY}
        {
            "message": "What is the capital of France?",
            "agent_id": "l9-standard-v1",
            "max_iterations": 5
        }

    Returns:
        ExecuteTaskResponse with result or error
    """
    # Check if executor is available
    executor = getattr(request.app.state, "agent_executor", None)
    if executor is None:
        raise HTTPException(
            status_code=503,
            detail="Agent executor not initialized. Check server startup logs.",
        )

    try:
        # Import here to avoid circular imports
        from core.agents.schemas import AgentTask, TaskKind

        # Map string kind to enum
        kind_map = {
            "query": TaskKind.QUERY,
            "command": TaskKind.COMMAND,
            "research": TaskKind.RESEARCH,
            "execution": TaskKind.EXECUTION,
            "conversation": TaskKind.CONVERSATION,
        }
        task_kind = kind_map.get(body.kind.lower(), TaskKind.QUERY)

        # Create AgentTask
        task = AgentTask(
            kind=task_kind,
            agent_id=body.agent_id or "l9-standard-v1",
            source_id=body.source_id,
            thread_identifier=body.thread_id,
            payload={
                "message": body.message,
                **body.context,
            },
            max_iterations=body.max_iterations,
        )

        logger.info(
            "Executing task via executor: task_id=%s, agent_id=%s",
            str(task.id),
            task.agent_id,
        )

        # Execute task
        result = await executor.start_agent_task(task)

        # Check if duplicate response
        if hasattr(result, "ok") and result.status == "duplicate":
            return ExecuteTaskResponse(
                ok=True,
                task_id=str(result.task_id),
                status="duplicate",
                result=None,
                iterations=0,
                duration_ms=0,
                error=None,
            )

        # Normal execution result
        return ExecuteTaskResponse(
            ok=result.status == "completed",
            task_id=str(result.task_id),
            status=result.status,
            result=result.result,
            iterations=result.iterations,
            duration_ms=result.duration_ms,
            error=result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing task: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Task execution failed: {str(e)}",
        )


@must_stay_async("health endpoint")
async def startup():
    """Called on app startup if exists."""
    logger.info("Agent routes initialized")


@must_stay_async("health endpoint")
async def shutdown():
    """Called on app shutdown if exists."""
    logger.info("Agent routes shutting down")

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.agents.schemas", "core.decorators", "core.schemas", "memory.ingestion"],
    "tags": ["api", "api-gateway", "async", "auth", "endpoint", "logging", "messaging", "operations", "pydantic", "queue"],
    "keywords": ["agent", "execute", "health", "memory", "queue", "routes", "shutdown", "startup"],
    "business_value": "Provides agent routes components including ExecuteTaskRequest, ExecuteTaskResponse",
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
