# memory/consolidation/__init__.py
"""
Memory Consolidation Module - Cache to memory promotion rules.

Provides deterministic rules for when ephemeral cache data
earns promotion to long-term memory.
"""

from memory.consolidation.promotion_rules import (
    PromotionSignal,
    get_promotion_reason,
    promotion_confidence_score,
    should_promote,
)

__all__ = [
    "PromotionSignal",
    "get_promotion_reason",
    "promotion_confidence_score",
    "should_promote",
]
