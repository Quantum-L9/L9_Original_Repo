"""
L9 Facade Module
================

Provides a simplified, unified API for L9 AIOS operations.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T13:25:14Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.facade.l9_facade import (
    CheckpointsInterface,
    ComplianceInterface,
    GovernanceInterface,
    # Main facade
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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-086",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.facade.l9_facade"],
    "tags": ["api", "core", "foundation", "utility"],
    "keywords": ["module"],
    "business_value": "Provides a simplified, unified API for L9 AIOS operations.",
    "last_modified": "2026-01-31T22:21:46Z",
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
