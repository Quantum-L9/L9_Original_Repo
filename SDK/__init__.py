"""
L9 SDK - Canonical Entry Point for L9 AIOS
==========================================

The official SDK for interacting with L9 Secure AI OS.
Provides a simplified, unified API for all L9 operations.

Usage:
    from SDK import L9, get_l9

    # Get singleton instance
    l9 = await get_l9()
    await l9.initialize()

    # Run tasks, query memory, execute tools
    result = await l9.run_task("Research async patterns")
    memories = await l9.query_memory("async")
    await l9.execute_tool("slack_send", channel="#general", message="Done!")

Quick functions:
    from SDK import run_task, query_memory, execute_tool

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
    "source": "Relocated from core/sdk/ for cleaner SDK access",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["memory_substrate"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api", "agents", "services"],
    },
}
# ============================================================================

from SDK.SDK import (
    # Main SDK class (preferred)
    L9SDK,
    CheckpointsInterface,
    ComplianceInterface,
    GovernanceInterface,
    # Legacy alias
    L9Facade,
    # P2: Advanced interfaces (Nice to Have)
    LearningInterface,
    MCPInterface,
    ObservabilityInterface,
    ReasoningInterface,
    # P1: Operational interfaces (Should Have)
    TaskQueueInterface,
    # P0: Core interfaces (Must Have)
    WorldModelInterface,
    close_l9_facade,
    close_l9_sdk,
    execute_tool,
    # SDK accessors
    get_l9_facade,
    get_l9_sdk,
    query_memory,
    # Convenience functions
    run_task,
)

# =============================================================================
# Public Aliases (Clean SDK Names)
# =============================================================================

# Primary alias - cleaner name for the main class
L9 = L9SDK

# Primary accessor alias
get_l9 = get_l9_sdk
close_l9 = close_l9_sdk

# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main SDK (preferred names)
    "L9",
    "L9SDK",
    "get_l9",
    "get_l9_sdk",
    "close_l9",
    "close_l9_sdk",
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
