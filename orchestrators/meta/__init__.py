"""
L9 Meta Orchestrator
====================

Selects best blueprint/design from multiple candidates.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:55Z",
    "layer": "intelligence",
    "domain": "orchestration",
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

from .adapter import BlueprintAdapter
from .interface import (
    Blueprint,
    BlueprintEvaluation,
    BlueprintScore,
    BlueprintType,
    EvaluationCriteria,
    IMetaOrchestrator,
    MetaOrchestratorRequest,
    MetaOrchestratorResponse,
)
from .orchestrator import MetaOrchestrator

__all__ = [
    "Blueprint",
    "BlueprintAdapter",
    "BlueprintEvaluation",
    "BlueprintScore",
    "BlueprintType",
    "EvaluationCriteria",
    "IMetaOrchestrator",
    "MetaOrchestrator",
    "MetaOrchestratorRequest",
    "MetaOrchestratorResponse",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-026",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["intelligence", "orchestration", "utility"],
    "keywords": ["orchestrator"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:55Z",
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
