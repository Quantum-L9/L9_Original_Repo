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

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from api.routes.registry import router_registry
from core.decorators import must_stay_async

# Input segmenter for multi-part directive support (harvested from tokenizer)
from orchestration.input_segmenter import get_segmenter

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["agent"])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="/agent",
    tags=["agent"],
    module_id="agent_routes",
    display_name="Agent Task Management",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ExecuteTaskRequest(BaseModel):
    """Request model for /execute endpoint."""

    agent_id: str | None = Field(
        None, description="Target agent ID (uses default if not specified)"
    )
    kind: str = Field(
        default="query", description="Task kind: query, command, research, execution"
    )
    message: str = Field(..., description="User message or query")
    source_id: str = Field(default="api", description="Source identifier")
    thread_id: str | None = Field(
        None, description="Thread identifier for conversation continuity"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    max_iterations: int = Field(
        default=10, ge=1, le=50, description="Max reasoning iterations"
    )
    # Multi-part directive support (harvested from tokenizer)
    segment_multi_part: bool = Field(
        default=True,
        description="Auto-segment multi-part directives (e.g., 'Deploy RIL, test ToT')",
    )

    model_config = {"extra": "forbid"}


class SegmentResult(BaseModel):
    """Result for a single segment in multi-part execution."""

    segment: str = Field(..., description="The segmented directive")
    task_id: str = Field(..., description="Task ID for this segment")
    status: str = Field(..., description="Execution status")
    result: str | None = Field(None, description="Agent response")
    error: str | None = Field(None, description="Error if failed")


class ExecuteTaskResponse(BaseModel):
    """Response model for /execute endpoint."""

    ok: bool = Field(..., description="Whether execution succeeded")
    task_id: str = Field(..., description="Task identifier (first task if multi-part)")
    status: str = Field(
        ..., description="Execution status: completed, failed, terminated, duplicate"
    )
    result: str | None = Field(None, description="Agent response if completed")
    iterations: int = Field(default=0, description="Number of reasoning iterations")
    duration_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )
    error: str | None = Field(None, description="Error message if failed")
    # Multi-part fields
    was_multi_part: bool = Field(
        default=False, description="Whether input was segmented"
    )
    segments_processed: int = Field(
        default=1, description="Number of segments processed"
    )
    segment_results: list[SegmentResult] | None = Field(
        None, description="Individual results if multi-part"
    )

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

    from core.schemas import PacketEnvelopeIn
    from memory.ingestion import ingest_packet

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

    Multi-part directive support (harvested from tokenizer):
    - If segment_multi_part=True (default), compound directives like
      "Deploy RIL, test ToT, sync Supabase" are automatically segmented
      and processed as separate tasks.

    For long-running tasks, consider using /task for async submission.

    Requires authentication via L9_EXECUTOR_API_KEY.

    Example:
        POST /agent/execute
        Authorization: Bearer {L9_EXECUTOR_API_KEY}
        {
            "message": "Deploy RIL, test ToT, sync Supabase",
            "agent_id": "l9-standard-v1",
            "segment_multi_part": true
        }

    Returns:
        ExecuteTaskResponse with result or error (includes segment_results if multi-part)
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
        from core.agents.schemas import AgentTask, AgentType

        # Map string kind to AgentType
        type_map = {
            "query": AgentType.ANALYST,
            "command": AgentType.OPERATOR,
            "research": AgentType.RESEARCHER,
            "execution": AgentType.EXECUTOR,
            "conversation": AgentType.ASSISTANT,
        }
        agent_type = type_map.get(body.kind.lower(), AgentType.ASSISTANT)

        # === Multi-Part Directive Support (harvested from tokenizer) ===
        segmenter = get_segmenter()
        segment_result = segmenter.segment(body.message)

        # Process as multi-part if enabled and multiple segments detected
        if body.segment_multi_part and segment_result.segment_count > 1:
            logger.info(
                "Multi-part directive detected: %d segments",
                segment_result.segment_count,
                segments=segment_result.segments,
            )

            segment_results: list[SegmentResult] = []
            total_iterations = 0
            total_duration_ms = 0
            first_task_id = None
            all_successful = True
            combined_results: list[str] = []

            for i, segment in enumerate(segment_result.segments):
                # Create AgentTask for this segment
                task = AgentTask(
                    agent_type=agent_type,
                    agent_id=body.agent_id or "l9-standard-v1",
                    source_id=body.source_id,
                    thread_identifier=body.thread_id,
                    payload={
                        "message": segment,
                        "segment_index": i,
                        "total_segments": segment_result.segment_count,
                        "from_multi_part": True,
                        "original_message": body.message,
                        **body.context,
                    },
                    max_iterations=body.max_iterations,
                )

                if i == 0:
                    first_task_id = str(task.id)

                logger.info(
                    "Executing segment %d/%d: %s",
                    i + 1,
                    segment_result.segment_count,
                    segment,
                )

                # Execute segment
                result = await executor.start_agent_task(task)

                # Handle duplicate
                if hasattr(result, "ok") and result.status == "duplicate":
                    segment_results.append(
                        SegmentResult(
                            segment=segment,
                            task_id=str(result.task_id),
                            status="duplicate",
                            result=None,
                            error=None,
                        )
                    )
                    continue

                # Record result
                segment_results.append(
                    SegmentResult(
                        segment=segment,
                        task_id=str(result.task_id),
                        status=result.status,
                        result=result.result,
                        error=result.error,
                    )
                )

                total_iterations += result.iterations
                total_duration_ms += result.duration_ms

                if result.status != "completed":
                    all_successful = False
                else:
                    combined_results.append(result.result or "")

            # Combine results
            combined_result = (
                "\n\n---\n\n".join(combined_results) if combined_results else None
            )

            return ExecuteTaskResponse(
                ok=all_successful,
                task_id=first_task_id or "",
                status="completed" if all_successful else "partial",
                result=combined_result,
                iterations=total_iterations,
                duration_ms=total_duration_ms,
                error=None if all_successful else "Some segments failed",
                was_multi_part=True,
                segments_processed=segment_result.segment_count,
                segment_results=segment_results,
            )

        # === Single task execution (original behavior) ===
        task = AgentTask(
            agent_type=agent_type,
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
            detail=f"Task execution failed: {e!s}",
        ) from e


# =============================================================================
# Segmentation Endpoint (for preview/debugging)
# =============================================================================


class SegmentPreviewRequest(BaseModel):
    """Request model for segment preview."""

    message: str = Field(..., description="Message to segment")


class SegmentPreviewResponse(BaseModel):
    """Response model for segment preview."""

    segments: list[str] = Field(..., description="Segmented directives")
    segment_count: int = Field(..., description="Number of segments")
    was_multi_part: bool = Field(..., description="Whether multiple segments detected")
    original_input: str = Field(..., description="Original input")


@router.post("/segment", response_model=SegmentPreviewResponse)
async def segment_preview(
    body: SegmentPreviewRequest,
) -> SegmentPreviewResponse:
    """
    Preview how a message would be segmented (no execution).

    Useful for debugging multi-part directive parsing.

    Example:
        POST /agent/segment
        {"message": "Deploy RIL, test ToT, sync Supabase"}

    Returns:
        {"segments": ["deploy ril", "test tot", "sync supabase"], "segment_count": 3, ...}
    """
    segmenter = get_segmenter()
    result = segmenter.segment(body.message)

    return SegmentPreviewResponse(
        segments=result.segments,
        segment_count=result.segment_count,
        was_multi_part=result.was_multi_part,
        original_input=result.raw_input,
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
    "dependencies": [
        "api.auth",
        "core.agents.schemas",
        "core.decorators",
        "core.schemas",
        "memory.ingestion",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
        "queue",
    ],
    "keywords": [
        "agent",
        "execute",
        "health",
        "memory",
        "queue",
        "routes",
        "shutdown",
        "startup",
    ],
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
