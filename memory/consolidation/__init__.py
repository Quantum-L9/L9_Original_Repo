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
from memory.consolidation.promotion_rules import (
    PromotionSignal,
    get_promotion_reason,
    promotion_confidence_score,
    should_promote,
)

__all__ = [
    "ConsolidationPipeline",
    "ConsolidationReport",
    "PromotionSignal",
    "get_promotion_reason",
    "promotion_confidence_score",
    "should_promote",
]
