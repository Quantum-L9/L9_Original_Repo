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

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .action_registry import ActionRegistry, ActionResult, registry
from .agent_state import AgentState, AgentStateManager, ProactivityLevel
from .foresight_engine import (
    FORESIGHT_OK,
    HIGHEST_LEVERAGE_QUESTION,
    CandidateAction,
    DecisionMode,
    ForesightCycleResult,
    ForesightDecision,
    ForesightEngine,
)
from .memory_adapter import MemoryAdapter
from .reflection_engine import ReflectionEngine, ReflectionResult

__all__ = [
    # Action registry
    "ActionRegistry",
    "ActionResult",
    # State management
    "AgentState",
    "AgentStateManager",
    "CandidateAction",
    "DecisionMode",
    "ForesightDecision",
    "FORESIGHT_OK",
    "ForesightCycleResult",
    "HIGHEST_LEVERAGE_QUESTION",
    # Foresight engine
    "ForesightEngine",
    # Memory
    "MemoryAdapter",
    "ProactivityLevel",
    # Reflection engine
    "ReflectionEngine",
    "ReflectionResult",
    "registry",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-222",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "auth", "core", "foundation"],
    "keywords": [
        "agent",
        "engine",
        "foresight",
        "memory",
        "module",
        "reflection",
        "runtime",
        "state",
    ],
    "business_value": "Action registry for executable actions Foresight engine for anticipatory behavior Reflection engine for continuous learning Agent state management Memory adapter for integration Version: 1.0.0 Author:",
    "last_modified": "2026-01-31T22:21:48Z",
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
