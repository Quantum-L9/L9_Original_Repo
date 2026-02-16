"""Intake leverage scoring and observe-cycle prioritization.

Computes an initial importance/leverage score at task intake based on:
- Access patterns (memory_access_log / AccessRecord from ImportanceManager)
- Role (MessageRole weight: system=0.9, assistant=0.7, user=0.5, tool=0.3)
- Tier (episodic events vs semantic facts — tier-specific modifiers)

The importance score set here feeds into:
1. ImportanceManager.elevate_importance() — boosts importance_score on packet_store
2. NeuralDecayScheduler.calculate_salience() — S(m,t) = I(m)*exp(-λt)*R(m)
   where I(m) is seeded from importance_score at intake

Migration: 0034_intake_leverage_rating.sql
ADR: 0006 (PacketEnvelope), 0012 (DAG pipeline), 0014 (DORA metadata)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

__all__ = [
    "IntakeLeverageQuery",
    "IntakeLeverageScorer",
    "IntakeTier",
    "LeverageCandidate",
    "RoleWeight",
    "fetch_highest_leverage_tasks",
    "score_intake_leverage",
]


# =============================================================================
# Role Weights (MessageRole → initial importance contribution)
# =============================================================================


class RoleWeight(float, Enum):
    """Weight contribution of message role to intake leverage score.

    Higher roles (system, governance) produce higher initial importance,
    matching ImportanceManager's elevation_cap=0.95 ceiling.
    """

    SYSTEM = 0.90
    GOVERNANCE = 0.85
    ASSISTANT = 0.70
    USER = 0.50
    TOOL = 0.30
    UNKNOWN = 0.40


# =============================================================================
# Memory Tier Modifiers (aligned with NeuralDecayScheduler tier logic)
# =============================================================================


class IntakeTier(str, Enum):
    """Memory tier for intake scoring.

    Modifiers align with NeuralDecayScheduler._process_facts() tier logic:
    - identity: exempt from decay (modifier 0.0 in decay, boost 1.0 in intake)
    - project: decays at 0.5× rate → high retention → boost intake importance
    - session: decays at 2.0× rate → low retention → reduce intake importance
    - general: standard decay rate → neutral modifier
    - episodic: event-based memory → moderate boost (impact_score/severity)
    """

    IDENTITY = "identity"
    PROJECT = "project"
    SESSION = "session"
    GENERAL = "general"
    EPISODIC = "episodic"


_TIER_INTAKE_MODIFIER: dict[IntakeTier, float] = {
    IntakeTier.IDENTITY: 1.00,
    IntakeTier.PROJECT: 0.85,
    IntakeTier.GENERAL: 0.60,
    IntakeTier.EPISODIC: 0.70,
    IntakeTier.SESSION: 0.40,
}


# =============================================================================
# Intake Leverage Scorer
# =============================================================================


@dataclass(frozen=True, slots=True)
class IntakeLeverageScorer:
    """Computes importance_score at task intake.

    Combines three signals:
    1. Role weight (MessageRole → RoleWeight enum)
    2. Tier modifier (IntakeTier → _TIER_INTAKE_MODIFIER)
    3. Access pattern bonus (recent_access_count from memory_access_log)

    The resulting score is clamped to [0.0, 1.0] and stored as
    importance_score on packet_store via metadata.
    """

    role_weight_factor: float = 0.40
    tier_modifier_factor: float = 0.35
    access_pattern_factor: float = 0.25
    access_count_cap: int = 50


def score_intake_leverage(
    scorer: IntakeLeverageScorer | None = None,
    role: str = "user",
    tier: str = "general",
    recent_access_count: int = 0,
    roi_estimate: float | None = None,
    estimated_time_saved_minutes: float | None = None,
) -> dict[str, float | None]:
    """Compute intake leverage fields for PacketEnvelope metadata.

    This is the primary entry point called at task-intake time. The returned
    dict is merged into PacketEnvelopeIn.metadata before ingest_packet().

    Args:
        scorer: Scoring config (uses defaults if None).
        role: Message role string (system/assistant/user/tool).
        tier: Memory tier string (identity/project/session/general/episodic).
        recent_access_count: Number of accesses in ImportanceConfig.access_recency_window_days.
        roi_estimate: Optional estimated ROI multiplier.
        estimated_time_saved_minutes: Optional time savings estimate.

    Returns:
        Dict with importance, roi_estimate, estimated_time_saved_minutes
        ready to merge into metadata.
    """
    if scorer is None:
        scorer = IntakeLeverageScorer()

    # 1. Role weight
    try:
        role_w = RoleWeight[role.upper()].value
    except KeyError:
        role_w = RoleWeight.UNKNOWN.value

    # 2. Tier modifier
    try:
        tier_mod = _TIER_INTAKE_MODIFIER[IntakeTier(tier)]
    except (ValueError, KeyError):
        tier_mod = _TIER_INTAKE_MODIFIER[IntakeTier.GENERAL]

    # 3. Access pattern bonus (normalized 0.0–1.0)
    capped_access = min(recent_access_count, scorer.access_count_cap)
    access_bonus = (
        capped_access / scorer.access_count_cap if scorer.access_count_cap > 0 else 0.0
    )

    # Weighted combination
    raw_score = (
        scorer.role_weight_factor * role_w
        + scorer.tier_modifier_factor * tier_mod
        + scorer.access_pattern_factor * access_bonus
    )

    # Clamp to [0.0, 1.0]
    importance_score = max(0.0, min(1.0, raw_score))

    logger.info(
        "intake_leverage_scored",
        role=role,
        tier=tier,
        recent_access_count=recent_access_count,
        role_weight=role_w,
        tier_modifier=tier_mod,
        access_bonus=round(access_bonus, 3),
        importance_score=round(importance_score, 4),
    )

    return {
        "importance": round(importance_score, 4),
        "roi_estimate": roi_estimate,
        "estimated_time_saved_minutes": estimated_time_saved_minutes,
    }


# =============================================================================
# Observe-Cycle Query Helpers
# =============================================================================


@dataclass(frozen=True, slots=True)
class LeverageCandidate:
    """A candidate task surfaced by importance score for the observe cycle.

    Uses importance_score (ImportanceManager-managed, decayed by
    NeuralDecayScheduler) for prioritization.
    """

    packet_id: str
    packet_type: str
    importance_score: float = 0.5
    roi_estimate: float | None = None
    estimated_time_saved_minutes: float | None = None
    access_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    summary: str = ""


@dataclass(frozen=True, slots=True)
class IntakeLeverageQuery:
    """Parameters for querying highest-leverage tasks.

    Filters by importance_score (ImportanceManager-managed signal) so the
    observe cycle can surface the most important candidate tasks.
    """

    packet_types: tuple[str, ...] = ("agent_task_submitted",)
    min_importance_score: float = 0.0
    limit: int = 20


_LEVERAGE_QUERY = """\
SELECT
    packet_id,
    packet_type,
    importance_score,
    access_count,
    created_at,
    envelope
FROM packet_store
WHERE importance_score IS NOT NULL
  AND importance_score >= $1
  AND packet_type = ANY($2)
ORDER BY importance_score DESC NULLS LAST
LIMIT $3
"""


async def fetch_highest_leverage_tasks(
    pool: Any,
    query: IntakeLeverageQuery | None = None,
) -> list[LeverageCandidate]:
    """Fetch highest-leverage candidate tasks from packet_store.

    Uses importance_score (managed by ImportanceManager, decayed by
    NeuralDecayScheduler) for prioritization. ROI and time-saved
    estimates are extracted from the envelope metadata JSON.

    Args:
        pool: asyncpg connection pool.
        query: Query parameters. Defaults to IntakeLeverageQuery().

    Returns:
        List of LeverageCandidate ordered by importance_score DESC.
    """
    if query is None:
        query = IntakeLeverageQuery()

    logger.info(
        "fetching_highest_leverage_tasks",
        min_importance=query.min_importance_score,
        packet_types=query.packet_types,
        limit=query.limit,
    )

    rows = await pool.fetch(
        _LEVERAGE_QUERY,
        query.min_importance_score,
        list(query.packet_types),
        query.limit,
    )

    candidates = [
        LeverageCandidate(
            packet_id=str(row["packet_id"]),
            packet_type=row["packet_type"],
            importance_score=float(row["importance_score"] or 0.5),
            roi_estimate=_extract_metadata_float(row, "roi_estimate"),
            estimated_time_saved_minutes=_extract_metadata_float(
                row,
                "estimated_time_saved_minutes",
            ),
            access_count=int(row["access_count"] or 0),
            created_at=row["created_at"],
        )
        for row in rows
    ]

    logger.info(
        "highest_leverage_tasks_fetched",
        count=len(candidates),
        top_importance=candidates[0].importance_score if candidates else None,
    )

    return candidates


def _extract_metadata_float(row: Any, key: str) -> float | None:
    """Extract a float value from envelope.metadata JSON."""
    try:
        envelope = row.get("envelope") or {}
        metadata = envelope.get("metadata") or {}
        val = metadata.get(key)
        return float(val) if val is not None else None
    except (TypeError, ValueError, AttributeError):
        return None
