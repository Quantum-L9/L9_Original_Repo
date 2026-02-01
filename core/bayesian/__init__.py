"""
L9 Bayesian Reasoning Module

Probabilistic reasoning, uncertainty quantification, and belief state management.

Components:
- bayesian_kernel: Core Bayesian reasoning kernel with belief state
- probabilistic_engine: Lightweight Bayesian inference for risk assessment
- hybrid_kernel: Combines deterministic FOL with probabilistic reasoning
- subjective_logic: Trust/Disbelief/Uncertainty representation
- uncertainty: Uncertainty decomposition (aleatoric vs epistemic)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T21:06:46Z",
    "updated_at": "2026-01-31T22:21:48Z",
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

from core.bayesian.bayesian_kernel import (
    BayesianKernel,
    BeliefState,
    EvidenceStrength,
    get_bayesian_kernel,
)

__all__ = [
    "BayesianKernel",
    "BeliefState",
    "EvidenceStrength",
    "get_bayesian_kernel",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-197",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.bayesian.bayesian_kernel"],
    "tags": ["core", "foundation", "utility"],
    "keywords": [
        "bayesian",
        "belief",
        "kernel",
        "module",
        "probabilistic",
        "reasoning",
        "state",
        "uncertainty",
    ],
    "business_value": "Utility module for   init  ",
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
