"""
L9 SDK - Internal Facade for L9 AIOS Subsystems
=================================================

An **internal convenience layer** that wraps L9's core subsystems behind a
simplified, unified API.  It is designed as a "pull when needed" package:
external integrators, new agents, or scripts that want one-stop access to
tasks, memory, tools, governance, and observability can import from here
instead of reaching into individual subsystem packages.

The 16 public symbols exposed below are the facade surface.  They may show
as "zero-reference" in triage reports because consumers adopt them on demand
rather than being wired at startup.  This is intentional — do NOT remove
them from ``__all__`` based on triage alone.

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
    # P1: Commands (ADR-0102)
    CommandsInterface,
    ComplianceInterface,
    # P1: Email (ADR-0102)
    EmailInterface,
    # P2: Evaluation (ADR-0102)
    EvaluationInterface,
    # P2: Factory (ADR-0102)
    FactoryInterface,
    GovernanceInterface,
    # Legacy alias
    L9Facade,
    # P2: Advanced interfaces (ADR-0102)
    LearningInterface,
    MCPInterface,
    # P0: Memory stack (ADR-0102)
    MemoryCacheInterface,
    MemoryGraphInterface,
    MemoryInterface,
    ObservabilityInterface,
    ReasoningInterface,
    # P1: Research (ADR-0102)
    ResearchInterface,
    # P2: Simulation (ADR-0102)
    SimulationInterface,
    # P1: Operational interfaces
    TaskQueueInterface,
    # P1: Workflow executors (ADR-0101)
    WorkflowsInterface,
    # P0: Core interfaces
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
    "L9",
    "L9SDK",
    "CheckpointsInterface",
    "CommandsInterface",
    "ComplianceInterface",
    "EmailInterface",
    "EvaluationInterface",
    "FactoryInterface",
    "GovernanceInterface",
    "L9Facade",
    "LearningInterface",
    "MCPInterface",
    "MemoryCacheInterface",
    "MemoryGraphInterface",
    "MemoryInterface",
    "ObservabilityInterface",
    "ReasoningInterface",
    "ResearchInterface",
    "SimulationInterface",
    "TaskQueueInterface",
    "WorkflowsInterface",
    "WorldModelInterface",
    "close_l9",
    "close_l9_facade",
    "close_l9_sdk",
    "execute_tool",
    "get_l9",
    "get_l9_facade",
    "get_l9_sdk",
    "query_memory",
    "run_task",
]
