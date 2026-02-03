"""
L9 SDK - Canonical Entry Point for L9 AIOS
==========================================

The official SDK for interacting with L9 Secure AI OS.
Provides a simplified, unified API for all L9 operations.

Usage:
    from l9 import L9, get_l9

    # Get singleton instance
    l9 = await get_l9()
    await l9.initialize()

    # Run tasks, query memory, execute tools
    result = await l9.run_task("Research async patterns")
    memories = await l9.query_memory("async")
    await l9.execute_tool("slack_send", channel="#general", message="Done!")

Quick functions:
    from l9 import run_task, query_memory, execute_tool

    result = await run_task("Analyze code")
    memories = await query_memory("patterns")
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 SDK",
    "module_version": "2.0.0",
    "created_by": "GMP-134",
    "created_at": "2026-02-02T18:50:00Z",
    "updated_at": "2026-02-02T18:50:00Z",
    "layer": "sdk",
    "domain": "public_api",
    "module_name": "__init__",
    "type": "package",
    "status": "active",
    "source": "Relocated from core/facade/ for cleaner SDK access",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["memory_substrate"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api", "agents", "services"],
    },
}
# ============================================================================

from l9.facade import (
    # P1: Operational interfaces (Should Have)
    CheckpointsInterface,
    # P2: Advanced interfaces (Nice to Have)
    ComplianceInterface,
    # P0: Core interfaces (Must Have)
    GovernanceInterface,
    # Main SDK class
    L9Facade,
    LearningInterface,
    MCPInterface,
    ObservabilityInterface,
    ReasoningInterface,
    TaskQueueInterface,
    WorldModelInterface,
    # Singleton accessors
    close_l9_facade,
    # Convenience functions
    execute_tool,
    get_l9_facade,
    query_memory,
    run_task,
)

# =============================================================================
# Public Aliases (Clean SDK Names)
# =============================================================================

# Primary alias - cleaner name for the main class
L9 = L9Facade

# Primary accessor alias
get_l9 = get_l9_facade
close_l9 = close_l9_facade

# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main SDK (preferred names)
    "L9",
    "get_l9",
    "close_l9",
    # Legacy names (backwards compat)
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
