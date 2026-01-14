"""
L9 Cursor API Router
Version: 1.0.0

API endpoints for Cursor IDE integration with LangGraph executor.
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["cursor"])


# =============================================================================
# Dependency: Get CursorExecutor from app.state
# =============================================================================


def get_cursor_executor(request: Request):
    """Get CursorExecutor from app.state."""
    executor = getattr(request.app.state, "cursor_executor", None)
    if executor is None:
        raise HTTPException(
            status_code=503,
            detail="CursorExecutor not initialized. Check server logs.",
        )
    return executor


# =============================================================================
# Request/Response Models
# =============================================================================


class CursorTaskRequest(BaseModel):
    """Request model for Cursor task execution."""

    task: str = Field(..., description="Task description")
    project_id: str = Field(..., description="Project identifier")
    entry_file: Optional[str] = Field(None, description="Entry file path")
    selection: Optional[str] = Field(None, description="Selected code snippet")
    thread_id: Optional[str] = Field(None, description="Thread ID for continuation")


class CursorTaskResponse(BaseModel):
    """Response model for Cursor task execution."""

    success: bool = Field(..., description="Whether operation succeeded")
    thread_id: str = Field(..., description="Thread identifier")
    task_status: str = Field(..., description="Task status")
    decisions: list[Dict[str, Any]] = Field(
        default_factory=list, description="Decisions made"
    )
    errors: list[Dict[str, Any]] = Field(
        default_factory=list, description="Errors encountered"
    )
    reasoning_trace: list[Dict[str, Any]] = Field(
        default_factory=list, description="Reasoning trace"
    )
    message: Optional[str] = Field(None, description="Result message")


class CursorResumeRequest(BaseModel):
    """Request model for resuming a thread."""

    thread_id: str = Field(..., description="Thread identifier to resume")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/test")
async def cursor_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify cursor router is reachable."""
    return {"ok": True, "msg": "cursor endpoint reachable"}


@router.post("/task", response_model=CursorTaskResponse)
async def cursor_task(
    request: CursorTaskRequest,
    http_request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute a Cursor task via LangGraph executor.
    
    Creates a new task or continues an existing thread.
    """
    logger.info("Cursor task request", task=request.task[:50], project_id=request.project_id)
    
    executor = get_cursor_executor(http_request)
    
    try:
        from agents.cursor.integrations.cursor_executor import CursorTaskSpec
        
        # Build task spec
        task_spec = CursorTaskSpec(
            task=request.task,
            project_id=request.project_id,
            entry_file=request.entry_file,
            selection=request.selection,
            initial_state=None,  # Will be created by executor
        )
        
        # Execute task
        result = await executor.run_task(task_spec)
        
        logger.info(
            "Cursor task completed",
            thread_id=result.thread_id,
            status=result.final_state.task_status,
        )
        
        return CursorTaskResponse(
            success=result.final_state.task_status == "completed",
            thread_id=result.thread_id,
            task_status=result.final_state.task_status,
            decisions=result.decisions,
            errors=result.errors,
            reasoning_trace=result.reasoning_trace,
            message="Task executed successfully" if result.final_state.task_status == "completed" else "Task failed",
        )
    except Exception as e:
        logger.exception("Cursor task execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Task execution error: {e}")


@router.post("/resume", response_model=CursorTaskResponse)
async def cursor_resume(
    request: CursorResumeRequest,
    http_request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Resume a Cursor thread from last checkpoint.
    
    Restores state from checkpoint and continues execution.
    """
    logger.info("Cursor resume request", thread_id=request.thread_id)
    
    executor = get_cursor_executor(http_request)
    
    try:
        
        # Resume thread
        result = await executor.resume_thread(request.thread_id)
        
        logger.info(
            "Cursor thread resumed",
            thread_id=result.thread_id,
            status=result.final_state.task_status,
        )
        
        return CursorTaskResponse(
            success=result.final_state.task_status == "completed",
            thread_id=result.thread_id,
            task_status=result.final_state.task_status,
            decisions=result.decisions,
            errors=result.errors,
            reasoning_trace=result.reasoning_trace,
            message="Thread resumed successfully" if result.final_state.task_status == "completed" else "Thread resume failed",
        )
    except ValueError as e:
        logger.warning("Cursor resume failed: thread not found", thread_id=request.thread_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Thread not found: {e}")
    except Exception as e:
        logger.exception("Cursor resume execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Resume execution error: {e}")

