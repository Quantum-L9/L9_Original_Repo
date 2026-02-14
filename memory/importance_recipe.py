"""ImportanceRecipe — shared deterministic importance scoring for L9 memory.

Used by both ActiveMemoryEncoder and PipelineRouter to ensure a single
canonical importance formula across the system.

Phase 1 formula (deterministic):
  base = tier_weight(segment)
  access_boost = f(access_count, last_access_age_hours)
  outcome_boost = g(success_signals, reflection_presence)
  raw_importance = clamp(base * access_boost * outcome_boost, 0.0, 1.0)

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "ImportanceRecipe",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Tier weights (procedural > semantic > episodic)
# ---------------------------------------------------------------------------

TIER_WEIGHTS: dict[str, float] = {
    "procedural": 0.85,
    "semantic": 0.65,
    "episodic": 0.45,
}

DEFAULT_TIER_WEIGHT = 0.50


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportanceInputs:
    """All inputs required to compute importance score."""

    segment: str = "episodic"
    access_count: int = 0
    last_access_age_hours: float = 0.0
    success_signal_count: int = 0
    has_reflection: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportanceUpdate:
    """Output compatible with ImportanceManager update API."""

    raw_importance: float
    tier_weight: float
    access_boost: float
    outcome_boost: float
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# Pure functions (stateless, testable)
# ---------------------------------------------------------------------------


def tier_weight(segment: str) -> float:
    """Get base weight for a memory segment/tier."""
    return TIER_WEIGHTS.get(segment.lower(), DEFAULT_TIER_WEIGHT)


def access_boost(access_count: int, last_access_age_hours: float) -> float:
    """Compute access-based boost.

    Frequency: monotonically increasing with diminishing returns (log).
    Recency: monotonically decreasing with age (exponential decay).
    """
    freq = 1.0 + 0.1 * math.log1p(access_count)
    recency = math.exp(-0.01 * max(last_access_age_hours, 0.0))
    return min(freq * recency, 2.0)


def outcome_boost(
    success_signal_count: int,
    has_reflection: bool,
) -> float:
    """Compute outcome-based boost with explicit caps."""
    base = 1.0 + 0.05 * min(success_signal_count, 20)
    if has_reflection:
        base += 0.1
    return min(base, 1.5)


def compute_importance(inputs: ImportanceInputs) -> ImportanceUpdate:
    """Compute deterministic importance score from inputs.

    This is the single canonical formula shared across:
    - ActiveMemoryEncoder (on task completion)
    - PipelineRouter (on ingest + access-tracked reads)
    """
    tw = tier_weight(inputs.segment)
    ab = access_boost(inputs.access_count, inputs.last_access_age_hours)
    ob = outcome_boost(inputs.success_signal_count, inputs.has_reflection)

    raw = max(0.0, min(tw * ab * ob, 1.0))

    logger.debug(
        "importance_computed",
        segment=inputs.segment,
        tier_weight=round(tw, 4),
        access_boost=round(ab, 4),
        outcome_boost=round(ob, 4),
        raw_importance=round(raw, 4),
    )

    return ImportanceUpdate(
        raw_importance=raw,
        tier_weight=tw,
        access_boost=ab,
        outcome_boost=ob,
    )


__all__ = [
    "ImportanceInputs",
    "ImportanceUpdate",
    "access_boost",
    "compute_importance",
    "outcome_boost",
    "tier_weight",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
