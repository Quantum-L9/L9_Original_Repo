# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "learning",
    "domain": "memory_substrate",
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

# memory/consolidation/__init__.py
"""
Memory Consolidation Module.

Combines:
- Cache to memory promotion rules (promotion_rules.py)
- Full consolidation pipeline (../consolidation.py re-exported)
"""

# Re-export from parent consolidation.py module
# Note: The directory shadows the .py file, so we import via direct path
import importlib.util
import os

# Load the consolidation.py module directly
_consolidation_py = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "consolidation.py"
)
if os.path.exists(_consolidation_py):
    _spec = importlib.util.spec_from_file_location(
        "_consolidation_module", _consolidation_py
    )
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

    # Re-export key classes
    ConsolidationPipeline = _module.ConsolidationPipeline
    ConsolidationReport = _module.ConsolidationReport
else:
    # Fallback: define stubs
    ConsolidationPipeline = None
    ConsolidationReport = None

# Export promotion rules
# Phase 0 Hardening: Parallel Pipeline + Adaptive Batching
from memory.consolidation.adaptive_batching import AdaptiveBatcher
from memory.consolidation.parallel_pipeline import (
    ParallelConsolidationPipeline,
    PhaseResult,
)
from memory.consolidation.promotion_rules import (
    PromotionSignal,
    get_promotion_reason,
    promotion_confidence_score,
    should_promote,
)

__all__ = [
    "AdaptiveBatcher",
    "ConsolidationPipeline",
    "ConsolidationReport",
    "ParallelConsolidationPipeline",
    "PhaseResult",
    "PromotionSignal",
    "get_promotion_reason",
    "promotion_confidence_score",
    "should_promote",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-081",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.consolidation.promotion_rules"],
    "tags": ["caching", "learning", "memory-substrate", "utility"],
    "keywords": [],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:50Z",
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
