# memory/consolidation/__init__.py
"""
Memory Consolidation Module - Cache to memory promotion rules.

Provides deterministic rules for when ephemeral cache data
earns promotion to long-term memory.

Also re-exports ConsolidationPipeline and ConsolidationReport from
memory/consolidation.py to resolve the module/package naming conflict.
"""

from memory.consolidation.promotion_rules import (
    PromotionSignal,
    get_promotion_reason,
    promotion_confidence_score,
    should_promote,
)

# Re-export from the consolidation.py module (parent directory)
# This resolves the module/package naming conflict where:
# - memory/consolidation.py contains ConsolidationPipeline
# - memory/consolidation/ is a package that shadows it
try:
    import importlib.util
    from pathlib import Path
    
    # Load memory/consolidation.py directly to avoid circular import
    _consolidation_file = Path(__file__).parent.parent / "consolidation.py"
    if _consolidation_file.exists():
        _spec = importlib.util.spec_from_file_location(
            "memory._consolidation_module", 
            _consolidation_file
        )
        if _spec and _spec.loader:
            _consolidation_module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_consolidation_module)
            ConsolidationPipeline = _consolidation_module.ConsolidationPipeline
            ConsolidationReport = _consolidation_module.ConsolidationReport
except Exception as _e:
    # Fallback: define stubs if import fails
    import warnings
    warnings.warn(f"Could not import ConsolidationPipeline: {_e}")
    ConsolidationPipeline = None  # type: ignore
    ConsolidationReport = None  # type: ignore

__all__ = [
    "PromotionSignal",
    "get_promotion_reason",
    "promotion_confidence_score",
    "should_promote",
    "ConsolidationPipeline",
    "ConsolidationReport",
]
