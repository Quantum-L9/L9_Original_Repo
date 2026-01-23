"""
L9 Reasoning Module
Theorem-of-Thought (ToTh) reasoning integration for L9 agents
"""

from core.reasoning.toth_engine import (
    ProductionToThEngine,
    ToThConfig,
    ReasoningMode,
    ModelProvider,
    ReasoningResult,
    ReasoningStep,
    FormalReasoningGraph,
    CloudModelClient
)

from core.reasoning.l9_toth_adapter import (
    L9ToThAdapter,
    L9ReasoningContext
)

__all__ = [
    # Core ToTh Engine
    'ProductionToThEngine',
    'ToThConfig',
    'ReasoningMode',
    'ModelProvider',
    'ReasoningResult',
    'ReasoningStep',
    'FormalReasoningGraph',
    'CloudModelClient',
    
    # L9 Integration
    'L9ToThAdapter',
    'L9ReasoningContext',
]

__version__ = '1.0.0'
