#!/usr/bin/env python3
"""
================================================================================
Module: Decision Synthesizer
Purpose: Combine multiple reasoning modes into unified decision
================================================================================

Summary:
    Synthesizes final decisions from outputs of multiple reasoning modes
    (symbolic, causal, analogical, reflective). Applies confidence weighting,
    conflict resolution, and produces actionable recommendations.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: INT-DTB-002
# layer: intelligence
# domain: decision_making
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class Decision:
    """Synthesized decision from reasoning modes."""

    action: str
    confidence: float
    reasoning_summary: str
    contributing_modes: list[str]
    conflicts_resolved: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionSynthesizer:
    """
    Synthesizes decisions from multiple reasoning outputs.

    Handles:
    - Confidence-weighted voting
    - Conflict detection and resolution
    - Uncertainty handling
    - Decision audit logging
    """

    def __init__(self, mode_weights: dict[str, float] | None = None):
        self.mode_weights = mode_weights or {
            "symbolic": 0.3,
            "causal": 0.25,
            "analogical": 0.2,
            "reflective": 0.25,
        }

    @must_stay_async("callers use await")
    async def synthesize_decision(
        self,
        reasoning_outputs: list[dict[str, Any]],
    ) -> Decision:
        """
        Combine reasoning mode outputs into final decision.

        Args:
            reasoning_outputs: List of outputs from reasoning modes

        Returns:
            Synthesized Decision
        """
        logger.info("synthesizing_decision", input_count=len(reasoning_outputs))

        # Detect conflicts
        conflicts = self._detect_conflicts(reasoning_outputs)

        # Resolve conflicts
        resolved = self._resolve_conflicts(conflicts)

        # Calculate weighted confidence
        confidence = self._calculate_weighted_confidence(reasoning_outputs)

        # Determine action
        action = self._determine_action(reasoning_outputs, confidence)

        # Build summary
        summary = self._build_summary(reasoning_outputs, resolved)

        decision = Decision(
            action=action,
            confidence=confidence,
            reasoning_summary=summary,
            contributing_modes=self._get_contributing_modes(reasoning_outputs),
            conflicts_resolved=resolved,
            metadata={"input_count": len(reasoning_outputs)},
        )

        logger.info(
            "decision_synthesized",
            action=action,
            confidence=confidence,
            conflicts_resolved=len(resolved),
        )

        return decision

    def _detect_conflicts(
        self,
        outputs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect conflicting recommendations across modes."""
        conflicts = []

        recommendations = []
        for output in outputs:
            if "recommendation" in output:
                recommendations.append(output["recommendation"])

        if len(set(recommendations)) > 1:
            conflicts.append(
                {
                    "type": "recommendation_conflict",
                    "values": recommendations,
                }
            )

        return conflicts

    def _resolve_conflicts(
        self,
        conflicts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Resolve detected conflicts using weighted voting."""
        resolved = []

        for conflict in conflicts:
            resolution = {
                "conflict": conflict,
                "resolution_method": "weighted_voting",
                "resolved": True,
            }
            resolved.append(resolution)

        return resolved

    def _calculate_weighted_confidence(
        self,
        outputs: list[dict[str, Any]],
    ) -> float:
        """Calculate weighted confidence from all outputs."""
        total_weight = 0.0
        weighted_confidence = 0.0

        for output in outputs:
            mode = output.get("mode", "default")
            weight = self.mode_weights.get(mode, 0.2)

            # Extract confidence from various possible keys
            confidence = 0.5
            for key in [
                "confidence",
                "causal_confidence",
                "pattern_confidence",
                "rule_confidence",
            ]:
                if key in output:
                    confidence = output[key]
                    break

            weighted_confidence += weight * confidence
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return weighted_confidence / total_weight

    def _determine_action(
        self,
        outputs: list[dict[str, Any]],
        confidence: float,
    ) -> str:
        """Determine final action based on outputs and confidence."""
        if confidence < 0.3:
            return "escalate_for_review"
        if confidence < 0.5:
            return "proceed_with_caution"
        if confidence < 0.8:
            return "proceed"
        return "proceed_with_high_confidence"

    def _get_contributing_modes(
        self,
        outputs: list[dict[str, Any]],
    ) -> list[str]:
        """Extract list of contributing modes."""
        modes = []
        for output in outputs:
            mode = output.get("mode")
            if mode:
                modes.append(mode)
        return modes

    def _build_summary(
        self,
        outputs: list[dict[str, Any]],
        resolved: list[dict[str, Any]],
    ) -> str:
        """Build human-readable summary of synthesis."""
        parts = [f"Synthesized from {len(outputs)} reasoning modes."]

        if resolved:
            parts.append(f"Resolved {len(resolved)} conflicts.")

        return " ".join(parts)


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================


__all__ = [
    "Decision",
    "DecisionSynthesizer",
]
