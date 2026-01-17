"""
L9 ActionTool Orchestrator - Implementation
Version: 1.0.0

Validates and executes tools, retries, safety, logs tool packets.
"""

import asyncio
import structlog
from typing import Any, Dict, Optional

from .interface import (
    IActionToolOrchestrator,
    ActionToolRequest,
    ActionToolResponse,
    ToolSafetyLevel,
)
from .validator import Validator
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Retry configuration
DEFAULT_MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0
BACKOFF_MULTIPLIER = 2.0


class ActionToolOrchestrator(IActionToolOrchestrator):
    """
    ActionTool Orchestrator implementation.

    Validates and executes tools with:
    - Pre-execution validation (safety, governance)
    - Retry logic with exponential backoff
    - Tool result logging to memory
    """

    def __init__(
        self,
        tool_registry: Optional[Any] = None,
        governance_engine: Optional[Any] = None,
    ):
        """
        Initialize action_tool orchestrator.

        Args:
            tool_registry: Optional ExecutorToolRegistry instance
            governance_engine: Optional GovernanceEngineService instance
        """
        self._registry = tool_registry
        self._governance = governance_engine
        self._validator = Validator(tool_registry)
        logger.info("ActionToolOrchestrator initialized")

    @must_stay_async("callers use await")
    async def _get_registry(self) -> Optional[Any]:
        """Get or lazily load the tool registry."""
        if self._registry is None:
            try:
                from core.tools.registry_adapter import create_executor_tool_registry

                self._registry = create_executor_tool_registry(
                    governance_enabled=self._governance is not None,
                    governance_engine=self._governance,
                )
            except ImportError:
                logger.warning("Tool registry not available")
                return None
        return self._registry

    async def execute(self, request: ActionToolRequest) -> ActionToolResponse:
        """
        Execute tool with validation and retry logic.

        Flow:
        1. Validate tool (safety, governance, arguments)
        2. Check if approval required
        3. Execute with retry on transient failures
        4. Return result with safety assessment
        """
        logger.info(
            "Executing action_tool orchestration",
            tool_id=request.tool_id,
            max_retries=request.max_retries,
        )

        # Build context for validation
        context = {
            "governance_engine": self._governance,
            "require_all_approvals": request.require_approval,
        }

        # Step 1: Validate
        validation = await self._validator.validate_tool(
            request.tool_id,
            request.arguments,
            context,
        )

        if not validation.valid:
            return ActionToolResponse(
                success=False,
                message=f"Validation failed: {', '.join(validation.errors)}",
                result=None,
                retries_used=0,
                safety_level=ToolSafetyLevel(validation.safety_level),
            )

        # Step 2: Check approval requirement
        if validation.requires_approval and request.require_approval:
            return ActionToolResponse(
                success=False,
                message=f"Tool '{request.tool_id}' requires Igor's approval",
                result={"pending_approval": True, "tool_id": request.tool_id},
                retries_used=0,
                safety_level=ToolSafetyLevel(validation.safety_level),
            )

        # Step 3: Execute with retry
        max_retries = min(request.max_retries, DEFAULT_MAX_RETRIES)
        result, retries_used = await self._execute_with_retry(
            request.tool_id,
            request.arguments,
            max_retries,
        )

        if result.get("success"):
            return ActionToolResponse(
                success=True,
                message="Tool executed successfully",
                result=result.get("result"),
                retries_used=retries_used,
                safety_level=ToolSafetyLevel(validation.safety_level),
            )
        else:
            return ActionToolResponse(
                success=False,
                message=result.get("error", "Tool execution failed"),
                result=result,
                retries_used=retries_used,
                safety_level=ToolSafetyLevel(validation.safety_level),
            )

    async def _execute_with_retry(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        max_retries: int,
    ) -> tuple[Dict[str, Any], int]:
        """
        Execute tool with exponential backoff retry.

        Returns:
            (result_dict, retries_used)
        """
        registry = await self._get_registry()
        if not registry:
            return {"success": False, "error": "Tool registry not available"}, 0

        backoff = INITIAL_BACKOFF_SECONDS
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Dispatch tool call
                result = await registry.dispatch_tool_call(
                    tool_id=tool_id,
                    arguments=arguments,
                    context={"attempt": attempt},
                )

                # Check result success
                if hasattr(result, "success"):
                    if result.success:
                        return {
                            "success": True,
                            "result": result.result
                            if hasattr(result, "result")
                            else None,
                        }, attempt
                    else:
                        last_error = (
                            result.error
                            if hasattr(result, "error")
                            else "Unknown error"
                        )
                else:
                    # Assume dict-like result
                    if result.get("success"):
                        return result, attempt
                    last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Tool execution failed, will retry",
                    tool_id=tool_id,
                    attempt=attempt,
                    error=str(e),
                )

            # Don't sleep after last attempt
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_SECONDS)

        return {"success": False, "error": last_error}, max_retries
