"""
L9 Facade (DEPRECATED - use `l9.facade` instead)
================================================

This module is maintained for backwards compatibility only.
All exports are re-exported from the canonical `l9/facade.py`.

MIGRATION:
    # Old (deprecated)
    from core.facade.l9_facade import L9Facade

    # New (preferred)
    from l9 import L9
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Facade (Backwards Compat Shim)",
    "module_version": "2.0.0",
    "created_by": "GMP-134",
    "created_at": "2026-01-24T19:30:00Z",
    "updated_at": "2026-02-02T18:50:00Z",
    "layer": "core",
    "domain": "api_facade",
    "module_name": "l9_facade",
    "type": "shim",
    "status": "deprecated",
    "deprecation_notice": "Use 'from l9 import L9' instead",
}
# ============================================================================

# Re-export everything from the canonical location
from l9.facade import (
    # P1 Interfaces
    CheckpointsInterface,
    # P2 Interfaces
    ComplianceInterface,
    # P0 Interfaces
    GovernanceInterface,
    # Main facade class
    L9Facade,
    LearningInterface,
    MCPInterface,
    ObservabilityInterface,
    ReasoningInterface,
    TaskQueueInterface,
    WorldModelInterface,
    # Singleton functions
    close_l9_facade,
    execute_tool,
    get_l9_facade,
    # Convenience functions
    query_memory,
    run_task,
)

__all__ = [
    "CheckpointsInterface",
    "ComplianceInterface",
    "GovernanceInterface",
    "L9Facade",
    "LearningInterface",
    "MCPInterface",
    "ObservabilityInterface",
    "ReasoningInterface",
    "TaskQueueInterface",
    "WorldModelInterface",
    "close_l9_facade",
    "execute_tool",
    "get_l9_facade",
    "query_memory",
    "run_task",
]
