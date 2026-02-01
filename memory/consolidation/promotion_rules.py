# ============================================================================
__dora_meta__ = {
    "component_name": "Promotion Rules",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "promotion_rules",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "memory.consolidation.__init__",
            "tests.memory.consolidation.test_promotion_rules",
        ],
    },
}
# ============================================================================

# memory/consolidation/promotion_rules.py
"""
Deterministic rules for cache → memory escalation.
Nothing ambiguous. No "vibes-based" memory.
"""

from enum import Enum
from typing import Any, Dict


class PromotionSignal(str, Enum):
    """What makes something worthy of permanent memory."""

    USER_CONFIRMED = "user_confirmed"
    TEST_PASSED = "test_passed"
    REPEATED_SUCCESS = "repeated_success"  # reused 2+ times
    GOVERNANCE_APPROVED = "governance_approved"
    CRITICAL_ERROR = "critical_error"  # negative memory


def should_promote(event: dict[str, Any]) -> bool:
    """
    Deterministic. No fuzzy logic. No ML hand-waving.

    Args:
        event: action record from working memory

    Returns:
        True if this should be promoted to long-term memory

    Principle: STRICT > LOOSE
    Better to forget something and re-learn than canonize a mistake.
    """

    # Rule 1: Explicit user confirmation always promotes
    if event.get("user_confirmed"):
        return True

    # Rule 2: Test-passed + reused 2+ times → solid pattern
    if event.get("tests_passed") and event.get("reuse_count", 0) >= 2:
        return True

    # Rule 3: Governance explicitly approved
    if event.get("governance_approved"):
        return True

    # Rule 4: Critical error (always remember what broke)
    if event.get("is_critical_error"):
        return True

    # Default: do not promote
    # Cache expires; only high-confidence facts become memory
    return False


def promotion_confidence_score(event: dict[str, Any]) -> float:
    """
    Optional: rank promotion confidence (0.0 → 1.0).
    For sorting multiple candidates.
    """
    score = 0.0

    if event.get("user_confirmed"):
        score += 0.9

    if event.get("governance_approved"):
        score += 0.7

    if event.get("tests_passed"):
        score += 0.3

    if event.get("reuse_count", 0) >= 2:
        score += 0.2

    return min(score, 1.0)


def get_promotion_reason(event: dict[str, Any]) -> str:
    """Human-readable reason why this will be promoted."""
    reasons = []

    if event.get("user_confirmed"):
        reasons.append("user confirmed")
    if event.get("governance_approved"):
        reasons.append("governance approved")
    if event.get("tests_passed"):
        reasons.append("tests passed")
    if event.get("reuse_count", 0) >= 2:
        reasons.append(f"reused {event.get('reuse_count')} times")
    if event.get("is_critical_error"):
        reasons.append("critical error (negative memory)")

    return " + ".join(reasons) if reasons else "no promotion signal"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-080",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "data-models", "enum", "event-driven", "learning", "testing"],
    "keywords": [
        "confidence",
        "promote",
        "promotion",
        "reason",
        "rules",
        "score",
        "should",
        "signal",
    ],
    "business_value": "Implements PromotionSignal for promotion rules functionality",
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
