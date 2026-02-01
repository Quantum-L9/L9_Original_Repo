"""
L9 Reasoning Module
Theorem-of-Thought (ToTh) reasoning integration for L9 agents
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:56:34Z",
    "updated_at": "2026-01-31T22:21:47Z",
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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-123",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.reasoning.l9_toth_adapter", "core.reasoning.toth_engine"],
    "tags": ["core", "foundation", "utility"],
    "keywords": ["module", "reasoning"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:47Z",
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
