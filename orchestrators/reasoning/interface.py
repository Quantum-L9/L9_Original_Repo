"""
L9 Reasoning Orchestrator - Interface
Version: 1.0.0

Controls reasoning engine modes, depth, tree/forest strategy.
"""

from typing import Protocol, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from core.decorators import must_stay_async


class ReasoningMode(str, Enum):
    """Reasoning engine modes."""

    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    FOREST_OF_THOUGHT = "forest_of_thought"
    BEAM_SEARCH = "beam_search"


class ReasoningRequest(BaseModel):
    """Request to reasoning orchestrator."""

    context: str = Field(default="", description="Input context")
    mode: ReasoningMode = Field(
        default=ReasoningMode.CHAIN_OF_THOUGHT, description="Reasoning mode"
    )
    depth: int = Field(default=3, description="Reasoning depth")
    branch_factor: int = Field(default=3, description="Branch factor for tree modes")


class ReasoningResponse(BaseModel):
    """Response from reasoning orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    reasoning_trace: List[str] = Field(
        default_factory=list, description="Reasoning steps"
    )
    conclusion: Optional[str] = Field(default=None, description="Final conclusion")


class IReasoningOrchestrator(Protocol):
    """Interface for Reasoning Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: ReasoningRequest) -> ReasoningResponse:
        """Execute reasoning orchestration."""
        ...
