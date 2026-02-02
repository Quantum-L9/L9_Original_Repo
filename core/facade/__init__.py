"""
L9 Facade Module (DEPRECATED - use `l9` package instead)
========================================================

This module is maintained for backwards compatibility only.
All exports are re-exported from the canonical `l9/` package.

MIGRATION:
    # Old (deprecated)
    from core.facade import L9Facade, get_l9_facade

    # New (preferred)
    from l9 import L9, get_l9
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Facade (Backwards Compat)",
    "module_version": "2.0.0",
    "created_by": "GMP-134",
    "created_at": "2026-01-24T13:25:14Z",
    "updated_at": "2026-02-02T18:50:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "deprecated",
    "deprecation_notice": "Use 'from l9 import L9, get_l9' instead",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# Re-export everything from the canonical l9 package location
from l9 import (
    # P1: Operational interfaces (Should Have)
    CheckpointsInterface,
    # P2: Advanced interfaces (Nice to Have)
    ComplianceInterface,
    # P0: Core interfaces (Must Have)
    GovernanceInterface,
    # Main facade
    L9Facade,
    LearningInterface,
    MCPInterface,
    ObservabilityInterface,
    ReasoningInterface,
    TaskQueueInterface,
    WorldModelInterface,
    close_l9_facade,
    # Convenience functions
    execute_tool,
    get_l9_facade,
    query_memory,
    run_task,
)

__all__ = [
    # Main facade
    "L9Facade",
    "get_l9_facade",
    "close_l9_facade",
    # Convenience functions
    "execute_tool",
    "query_memory",
    "run_task",
    # P0: Core interfaces
    "WorldModelInterface",
    "GovernanceInterface",
    "ObservabilityInterface",
    # P1: Operational interfaces
    "TaskQueueInterface",
    "CheckpointsInterface",
    "MCPInterface",
    # P2: Advanced interfaces
    "LearningInterface",
    "ComplianceInterface",
    "ReasoningInterface",
]
