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
