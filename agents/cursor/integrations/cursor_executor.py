"""
L9 Cursor Executor
Version: 2.0.0

High-level executor that Cursor IDE can call to run/resume tasks through
LangGraph with full memory + governance integration.

Updated to use MemorySubstrateService directly (removed SubstrateDagOrchestrator).
"""

from __future__ import annotations

import structlog
from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from agents.cursor.integrations.cursor_langgraph import (
    CursorAgentState,
)
from agents.cursor.integrations.cursor_gateway import CursorMemoryGateway
from memory.substrate_service import MemorySubstrateService
from memory.checkpoint.cursor_checkpoint_manager import CursorCheckpointManager
from core.governance.approval_manager import ApprovalManager

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class CursorTaskSpec(BaseModel):
    """Task specification for Cursor executor."""

    task: str = Field(..., description="Task description")
    project_id: str = Field(..., description="Project identifier")
    initial_state: Optional[CursorAgentState] = Field(
        None, description="Initial state (optional)"
    )
    entry_file: Optional[str] = Field(None, description="Entry file path")
    selection: Optional[str] = Field(None, description="Selected code snippet")


class CursorResult(BaseModel):
    """Result of Cursor task execution."""

    thread_id: str = Field(..., description="Thread identifier")
    final_state: CursorAgentState = Field(..., description="Final agent state")
    decisions: list[dict[str, Any]] = Field(
        default_factory=list, description="Decisions made"
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Errors encountered"
    )
    reasoning_trace: list[dict[str, Any]] = Field(
        default_factory=list, description="Reasoning trace"
    )


# =============================================================================
# Executor Class
# =============================================================================


class CursorExecutor:
    """
    High-level executor for Cursor tasks.

    Orchestrates LangGraph execution with memory, governance, and checkpointing.
    """

    def __init__(
        self,
        langgraph_app: Any,  # Compiled LangGraph app
        memory_gateway: CursorMemoryGateway,
        substrate_service: MemorySubstrateService,
        checkpoint_manager: CursorCheckpointManager,
        approval_manager: ApprovalManager,
    ):
        """
        Initialize Cursor executor.

        Args:
            langgraph_app: Compiled LangGraph application
            memory_gateway: CursorMemoryGateway instance
            substrate_service: MemorySubstrateService instance
            checkpoint_manager: CursorCheckpointManager instance
            approval_manager: ApprovalManager instance
        """
        self._app = langgraph_app
        self._gateway = memory_gateway
        self._substrate_service = substrate_service
        self._checkpoint_manager = checkpoint_manager
        self._approval_manager = approval_manager
        logger.info("CursorExecutor initialized")

    async def run_task(self, task: CursorTaskSpec) -> CursorResult:
        """
        Run a Cursor task through LangGraph.

        Args:
            task: Task specification

        Returns:
            CursorResult with execution results
        """
        logger.info(
            "Running Cursor task", task=task.task[:50], project_id=task.project_id
        )

        # Generate thread ID
        thread_id = str(uuid4())

        # Build initial state
        initial_state = task.initial_state or CursorAgentState(
            thread_id=thread_id,
            task=task.task,
            current_file=task.entry_file,
            selected_code=task.selection,
            project_id=task.project_id,
            task_status="pending",
        )

        try:
            # Execute LangGraph
            config = {"configurable": {"thread_id": thread_id}}
            final_state_dict = await self._app.invoke(
                initial_state.model_dump(), config=config
            )

            # Convert back to CursorAgentState
            final_state = CursorAgentState(**final_state_dict)

            # Save checkpoint
            await self._checkpoint_manager.checkpoint(thread_id, final_state)

            logger.info(
                "Task completed", thread_id=thread_id, status=final_state.task_status
            )

            return CursorResult(
                thread_id=thread_id,
                final_state=final_state,
                decisions=final_state.decisions,
                errors=final_state.errors,
                reasoning_trace=[
                    block.model_dump() if hasattr(block, "model_dump") else block
                    for block in final_state.reasoning_trace
                ],
            )
        except Exception as e:
            logger.error("Task execution failed", error=str(e), thread_id=thread_id)

            # Save error state
            error_state = initial_state.model_copy(
                update={
                    "task_status": "failed",
                    "errors": initial_state.errors
                    + [{"type": "execution_error", "error": str(e)}],
                }
            )

            # Write error to memory
            try:
                await self._gateway.write_error(error_state)
            except Exception as write_error:
                logger.error("Failed to write error", error=str(write_error))

            # Return error result
            return CursorResult(
                thread_id=thread_id,
                final_state=error_state,
                decisions=[],
                errors=error_state.errors,
                reasoning_trace=[],
            )

    async def resume_thread(self, thread_id: str) -> CursorResult:
        """
        Resume a thread from last checkpoint.

        Args:
            thread_id: Thread identifier

        Returns:
            CursorResult with execution results
        """
        logger.info("Resuming thread", thread_id=thread_id)

        # Restore checkpoint
        restored_state = await self._checkpoint_manager.restore(thread_id)

        if not restored_state:
            raise ValueError(f"No checkpoint found for thread {thread_id}")

        try:
            # Resume LangGraph execution
            config = {"configurable": {"thread_id": thread_id}}
            final_state_dict = await self._app.invoke(
                restored_state.model_dump(), config=config
            )

            # Convert back to CursorAgentState
            final_state = CursorAgentState(**final_state_dict)

            # Save checkpoint
            await self._checkpoint_manager.checkpoint(thread_id, final_state)

            logger.info("Thread resumed and completed", thread_id=thread_id)

            return CursorResult(
                thread_id=thread_id,
                final_state=final_state,
                decisions=final_state.decisions,
                errors=final_state.errors,
                reasoning_trace=[
                    block.model_dump() if hasattr(block, "model_dump") else block
                    for block in final_state.reasoning_trace
                ],
            )
        except Exception as e:
            logger.error("Thread resume failed", error=str(e), thread_id=thread_id)
            raise
