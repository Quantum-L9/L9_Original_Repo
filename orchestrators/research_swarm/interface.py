"""
L9 ResearchSwarm Orchestrator - Interface
Version: 1.0.0

Runs concurrent research agents, analyst pass, dreamers, convergence.
"""

from typing import Protocol, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.decorators import must_stay_async


class ResearchSwarmRequest(BaseModel):
    """Request to research_swarm orchestrator."""

    query: str = Field(default="", description="Research query")
    agent_count: int = Field(default=3, description="Number of parallel agents")
    convergence_threshold: float = Field(default=0.8, description="Agreement threshold")


class ResearchSwarmResponse(BaseModel):
    """Response from research_swarm orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Agent results"
    )
    consensus: Optional[str] = Field(default=None, description="Converged consensus")


class IResearchSwarmOrchestrator(Protocol):
    """Interface for ResearchSwarm Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: ResearchSwarmRequest) -> ResearchSwarmResponse:
        """Execute research_swarm orchestration."""
        ...
