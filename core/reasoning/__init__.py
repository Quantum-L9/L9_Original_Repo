"""
L9 Reasoning Module
Theorem-of-Thought (ToTh) reasoning integration for L9 agents
"""

from core.reasoning.l9_toth_adapter import L9ReasoningContext, L9ToThAdapter
from core.reasoning.toth_engine import (
    CloudModelClient,
    FormalReasoningGraph,
    ModelProvider,
    ProductionToThEngine,
    ReasoningMode,
    ReasoningResult,
    ReasoningStep,
    ToThConfig,
)

__all__ = [
    "CloudModelClient",
    "FormalReasoningGraph",
    "L9ReasoningContext",
    # L9 Integration
    "L9ToThAdapter",
    "ModelProvider",
    # Core ToTh Engine
    "ProductionToThEngine",
    "ReasoningMode",
    "ReasoningResult",
    "ReasoningStep",
    "ToThConfig",
]

__version__ = "1.0.0"
