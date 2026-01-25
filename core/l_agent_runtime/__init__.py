"""
L9 L Agent Runtime Module
==========================
Runtime components for autonomous L agent with foresight and reflection.

This module provides:
- Action registry for executable actions
- Foresight engine for anticipatory behavior
- Reflection engine for continuous learning
- Agent state management
- Memory adapter for integration

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

from .action_registry import ActionRegistry, ActionResult, registry
from .agent_state import AgentState, AgentStateManager, ProactivityLevel
from .foresight_engine import (
    CandidateAction,
    DecisionMode,
    ForesightDecision,
    ForesightEngine,
)
from .memory_adapter import MemoryAdapter
from .reflection_engine import ReflectionEngine, ReflectionResult

__all__ = [
    # Action registry
    "ActionRegistry",
    "ActionResult",
    "registry",
    # Foresight engine
    "ForesightEngine",
    "CandidateAction",
    "ForesightDecision",
    "DecisionMode",
    # Reflection engine
    "ReflectionEngine",
    "ReflectionResult",
    # State management
    "AgentState",
    "AgentStateManager",
    "ProactivityLevel",
    # Memory
    "MemoryAdapter",
]
