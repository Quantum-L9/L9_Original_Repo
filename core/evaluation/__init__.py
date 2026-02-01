"""
L9 Evaluation Framework

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Provides: Continuous evaluation, LLM-as-judge scoring, CI/CD integration.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
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

from .eval_sets import (
    ALL_EVAL_SETS,
    CODE_ANALYSIS_EXAMPLES,
    EVAL_SET_DESCRIPTIONS,
    INFORMATION_RETRIEVAL_EXAMPLES,
    MEMORY_OPERATIONS_EXAMPLES,
    MULTI_TOOL_EXAMPLES,
    load_default_eval_sets,
)
from .evaluator import (
    EvaluationExample,
    EvaluationResult,
    EvaluationSet,
    Evaluator,
    RegressionError,
    ci_eval_gate,
)

__all__ = [
    "ALL_EVAL_SETS",
    "CODE_ANALYSIS_EXAMPLES",
    "EVAL_SET_DESCRIPTIONS",
    "INFORMATION_RETRIEVAL_EXAMPLES",
    "MEMORY_OPERATIONS_EXAMPLES",
    "MULTI_TOOL_EXAMPLES",
    "EvaluationExample",
    "EvaluationResult",
    "EvaluationSet",
    "Evaluator",
    "RegressionError",
    "ci_eval_gate",
    "load_default_eval_sets",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-188",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "foundation", "utility"],
    "keywords": ["evaluation"],
    "business_value": "Provides: Continuous evaluation, LLM-as-judge scoring, CI/CD integration.",
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
