"""
L9 Research Swarm Orchestrator
==============================

Runs concurrent research agents, analyst pass, dreamers, convergence.
"""

from .convergence import Convergence
from .interface import (IResearchSwarmOrchestrator, ResearchSwarmRequest,
                        ResearchSwarmResponse)
from .orchestrator import ResearchSwarmOrchestrator

__all__ = [
    "IResearchSwarmOrchestrator",
    "ResearchSwarmRequest",
    "ResearchSwarmResponse",
    "ResearchSwarmOrchestrator",
    "Convergence",
]
