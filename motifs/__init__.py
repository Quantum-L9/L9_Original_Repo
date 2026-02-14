"""
L9 Motifs Layer

Reusable reasoning patterns, cross-domain compression, failure fingerprints,
and plan rerouting primitives. Motifs are epistemic accelerators that let
EOS recognize patterns: "I've seen this shape of reasoning before."

Components:
- MotifFeedbackGraph: Track motif activations and outcomes
- MultimodalPlanRanker: Rank plans using tensor + symbolic + motif signals
- TensorMotifLinker: Bind motif metadata to tensor packets
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-26T11:14:45Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "motifs",
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

from .motif_feedback_graph import MotifEvent, MotifFeedbackGraph, MotifTrace
from .multimodal_plan_ranker import MultimodalPlanRanker, PlanCandidate, RankedPlan
from .tensor_motif_linker import MotifMetadata, TensorMotifLinker

__version__ = "1.0.0"

__all__ = [
    # Data classes
    "MotifEvent",
    "MotifMetadata",
    "MotifTrace",
    "PlanCandidate",
    "RankedPlan",
    # Core classes
    "MultimodalPlanRanker",
    "TensorMotifLinker",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MOT-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["event-driven", "motifs", "operations", "tracing", "utility"],
    "keywords": ["motif", "motifs", "patterns", "reasoning", "tensor"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:54Z",
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
