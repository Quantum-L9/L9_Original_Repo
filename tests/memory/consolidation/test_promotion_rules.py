"""
L9 Memory Consolidation - Promotion Rules Tests
================================================

Contract-grade tests for promotion_rules.py deterministic escalation logic.

Acceptance criteria:
- Rule 1: user_confirmed always promotes
- Rule 2: tests_passed + reuse_count >= 2 promotes
- Rule 3: governance_approved always promotes
- Rule 4: critical_error always promotes
- Default: no promotion (strict over loose)
- Confidence scoring works correctly
- Promotion reasons are human-readable

Version: 1.0.0
ADR: 0014 (DORA metadata), 0019 (structlog)
"""

from __future__ import annotations

import pytest

from memory.consolidation.promotion_rules import (
    PromotionSignal,
    get_promotion_reason,
    promotion_confidence_score,
    should_promote,
)

# =============================================================================
# Test: Rule 1 - user_confirmed always promotes
# =============================================================================


def test_user_confirmed_always_promotes() -> None:
    """
    Contract: Rule 1 - Explicit user confirmation always promotes.

    Verifies:
    - user_confirmed=True returns True
    - Works regardless of other signals
    """
    event = {"user_confirmed": True}
    assert should_promote(event) is True


def test_user_confirmed_overrides_missing_signals() -> None:
    """
    Contract: user_confirmed promotes even without tests or governance.

    Verifies:
    - user_confirmed alone is sufficient
    """
    event = {
        "user_confirmed": True,
        "tests_passed": False,
        "governance_approved": False,
        "reuse_count": 0,
    }
    assert should_promote(event) is True


# =============================================================================
# Test: Rule 2 - tests_passed + reuse_count >= 2
# =============================================================================


def test_tests_passed_with_sufficient_reuse_promotes() -> None:
    """
    Contract: Rule 2 - tests_passed + reuse_count >= 2 promotes.

    Verifies:
    - tests_passed=True AND reuse_count=2 returns True
    - Solid pattern validation
    """
    event = {
        "tests_passed": True,
        "reuse_count": 2,
    }
    assert should_promote(event) is True


def test_tests_passed_with_high_reuse_promotes() -> None:
    """
    Contract: Higher reuse counts satisfy Rule 2.

    Verifies:
    - reuse_count > 2 still promotes
    """
    event = {
        "tests_passed": True,
        "reuse_count": 5,
    }
    assert should_promote(event) is True


def test_tests_passed_with_insufficient_reuse_does_not_promote() -> None:
    """
    Contract: Rule 2 requires BOTH tests_passed AND reuse_count >= 2.

    Verifies:
    - tests_passed=True but reuse_count=1 does NOT promote
    - Strict over loose principle
    """
    event = {
        "tests_passed": True,
        "reuse_count": 1,
    }
    assert should_promote(event) is False


def test_tests_passed_with_zero_reuse_does_not_promote() -> None:
    """
    Contract: Single use without reuse does not promote.

    Verifies:
    - Even with tests, no reuse = no promotion
    """
    event = {
        "tests_passed": True,
        "reuse_count": 0,
    }
    assert should_promote(event) is False


def test_no_tests_with_high_reuse_does_not_promote() -> None:
    """
    Contract: Reuse without test validation does not promote.

    Verifies:
    - tests_passed=False blocks promotion even with high reuse
    """
    event = {
        "tests_passed": False,
        "reuse_count": 10,
    }
    assert should_promote(event) is False


# =============================================================================
# Test: Rule 3 - governance_approved always promotes
# =============================================================================


def test_governance_approved_always_promotes() -> None:
    """
    Contract: Rule 3 - Governance approval always promotes.

    Verifies:
    - governance_approved=True returns True
    """
    event = {"governance_approved": True}
    assert should_promote(event) is True


def test_governance_approved_overrides_missing_signals() -> None:
    """
    Contract: governance_approved promotes even without tests or reuse.

    Verifies:
    - governance_approved alone is sufficient
    """
    event = {
        "governance_approved": True,
        "tests_passed": False,
        "reuse_count": 0,
    }
    assert should_promote(event) is True


# =============================================================================
# Test: Rule 4 - critical_error always promotes (negative memory)
# =============================================================================


def test_critical_error_always_promotes() -> None:
    """
    Contract: Rule 4 - Critical errors always promote (negative memory).

    Verifies:
    - is_critical_error=True returns True
    - Errors must be remembered
    """
    event = {"is_critical_error": True}
    assert should_promote(event) is True


def test_critical_error_overrides_missing_signals() -> None:
    """
    Contract: critical_error promotes even without positive signals.

    Verifies:
    - Errors are remembered regardless of success metrics
    """
    event = {
        "is_critical_error": True,
        "tests_passed": False,
        "reuse_count": 0,
    }
    assert should_promote(event) is True


# =============================================================================
# Test: Default behavior - do not promote
# =============================================================================


def test_empty_event_does_not_promote() -> None:
    """
    Contract: Default - no signals means no promotion.

    Verifies:
    - Empty event returns False
    - Strict over loose principle
    """
    event = {}
    assert should_promote(event) is False


def test_insufficient_signals_do_not_promote() -> None:
    """
    Contract: Partial signals without meeting any rule do not promote.

    Verifies:
    - tests_passed alone is insufficient
    - reuse_count alone is insufficient
    """
    event = {
        "tests_passed": True,
        "reuse_count": 1,
    }
    assert should_promote(event) is False


def test_unknown_signals_do_not_promote() -> None:
    """
    Contract: Unknown signals are ignored.

    Verifies:
    - Random keys don't cause promotion
    """
    event = {
        "random_signal": True,
        "unknown_field": 999,
    }
    assert should_promote(event) is False


# =============================================================================
# Test: Confidence scoring
# =============================================================================


def test_user_confirmed_has_highest_confidence() -> None:
    """
    Contract: user_confirmed gives highest confidence score.

    Verifies:
    - user_confirmed contributes 0.9
    """
    event = {"user_confirmed": True}
    score = promotion_confidence_score(event)
    assert score == 0.9


def test_governance_approved_confidence() -> None:
    """
    Contract: governance_approved contributes 0.7.

    Verifies:
    - governance_approved score
    """
    event = {"governance_approved": True}
    score = promotion_confidence_score(event)
    assert score == 0.7


def test_tests_passed_confidence() -> None:
    """
    Contract: tests_passed contributes 0.3.

    Verifies:
    - tests_passed score
    """
    event = {"tests_passed": True}
    score = promotion_confidence_score(event)
    assert score == 0.3


def test_reuse_confidence() -> None:
    """
    Contract: reuse_count >= 2 contributes 0.2.

    Verifies:
    - reuse score
    """
    event = {"reuse_count": 2}
    score = promotion_confidence_score(event)
    assert score == 0.2


def test_combined_signals_confidence_capped_at_one() -> None:
    """
    Contract: Combined confidence score capped at 1.0.

    Verifies:
    - user_confirmed + governance_approved + tests_passed + reuse = 1.0 (not > 1.0)
    """
    event = {
        "user_confirmed": True,  # 0.9
        "governance_approved": True,  # 0.7
        "tests_passed": True,  # 0.3
        "reuse_count": 2,  # 0.2
    }
    score = promotion_confidence_score(event)
    assert score == 1.0  # Capped


def test_partial_signals_confidence() -> None:
    """
    Contract: Partial signals combine correctly.

    Verifies:
    - tests_passed + reuse = 0.5
    """
    event = {
        "tests_passed": True,  # 0.3
        "reuse_count": 2,  # 0.2
    }
    score = promotion_confidence_score(event)
    assert score == 0.5


def test_empty_event_has_zero_confidence() -> None:
    """
    Contract: No signals means zero confidence.

    Verifies:
    - Empty event returns 0.0
    """
    event = {}
    score = promotion_confidence_score(event)
    assert score == 0.0


# =============================================================================
# Test: Human-readable promotion reasons
# =============================================================================


def test_user_confirmed_reason() -> None:
    """
    Contract: get_promotion_reason returns human-readable explanation.

    Verifies:
    - user_confirmed reason
    """
    event = {"user_confirmed": True}
    reason = get_promotion_reason(event)
    assert "user confirmed" in reason


def test_governance_approved_reason() -> None:
    """
    Contract: governance_approved reason.

    Verifies:
    - governance reason
    """
    event = {"governance_approved": True}
    reason = get_promotion_reason(event)
    assert "governance approved" in reason


def test_tests_passed_reason() -> None:
    """
    Contract: tests_passed reason.

    Verifies:
    - tests reason
    """
    event = {"tests_passed": True, "reuse_count": 2}
    reason = get_promotion_reason(event)
    assert "tests passed" in reason


def test_reuse_count_reason() -> None:
    """
    Contract: reuse_count reason includes count.

    Verifies:
    - reuse reason with count
    """
    event = {"tests_passed": True, "reuse_count": 3}
    reason = get_promotion_reason(event)
    assert "reused 3 times" in reason


def test_critical_error_reason() -> None:
    """
    Contract: critical_error reason.

    Verifies:
    - error reason (negative memory)
    """
    event = {"is_critical_error": True}
    reason = get_promotion_reason(event)
    assert "critical error" in reason


def test_combined_reasons() -> None:
    """
    Contract: Multiple signals combine with ' + ' separator.

    Verifies:
    - Multiple reasons joined correctly
    """
    event = {
        "user_confirmed": True,
        "governance_approved": True,
    }
    reason = get_promotion_reason(event)
    assert "user confirmed" in reason
    assert "governance approved" in reason
    assert " + " in reason


def test_no_promotion_signal_reason() -> None:
    """
    Contract: No signals returns 'no promotion signal'.

    Verifies:
    - Empty event reason
    """
    event = {}
    reason = get_promotion_reason(event)
    assert reason == "no promotion signal"


# =============================================================================
# Test: PromotionSignal enum
# =============================================================================


def test_promotion_signal_enum_values() -> None:
    """
    Contract: PromotionSignal enum has expected values.

    Verifies:
    - All signal types exist
    """
    assert PromotionSignal.USER_CONFIRMED == "user_confirmed"
    assert PromotionSignal.TEST_PASSED == "test_passed"
    assert PromotionSignal.REPEATED_SUCCESS == "repeated_success"
    assert PromotionSignal.GOVERNANCE_APPROVED == "governance_approved"
    assert PromotionSignal.CRITICAL_ERROR == "critical_error"


# =============================================================================
# Public API
# =============================================================================

__all__ = []
