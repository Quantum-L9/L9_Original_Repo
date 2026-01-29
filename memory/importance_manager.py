"""
L9 Memory Substrate - Importance Manager
Version: 3.1.0

Implements dynamic importance management for memory facts:
- Access tracking (increment access_count, update last_accessed)
- Importance elevation (boost importance when facts are useful)
- Importance decay (reduce importance for unused facts)
- Importance-based pruning (remove low-importance facts)

Based on frontier AI lab patterns for adaptive memory management.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Importance Manager",
    "module_version": "3.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "importance_manager",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.__init__",
            "tests.memory.test_frontier_memory_pipeline",
        ],
    },
}
# ============================================================================

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class ImportanceConfig:
    """
    Configuration for importance management.
    """

    # Elevation settings
    elevation_increment: float = 0.1  # How much to boost on access
    elevation_cap: float = 0.95  # Maximum importance

    # Decay settings
    decay_half_life_days: float = 30.0  # Days until importance halves
    decay_floor: float = 0.1  # Minimum importance after decay
    decay_exempt_tiers: tuple[str, ...] = ("identity",)  # Tiers exempt from decay

    # Pruning settings
    prune_threshold: float = 0.15  # Below this = candidate for pruning
    prune_min_age_days: int = 90  # Only prune facts older than this
    prune_exempt_tiers: tuple[str, ...] = (
        "identity",
        "project",
    )  # Tiers exempt from pruning

    # Access tracking
    access_recency_window_days: int = 7  # Window for "recent" access


# Default configuration
DEFAULT_CONFIG = ImportanceConfig()


# =============================================================================
# Access Record
# =============================================================================


@dataclass
class AccessRecord:
    """
    Record of a fact access event.
    """

    fact_id: UUID
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_type: str = "retrieval"  # retrieval, elevation, reference
    context: str = ""  # What triggered the access

    # Optional: who accessed
    agent_id: str | None = None
    session_id: UUID | None = None


@dataclass
class ImportanceUpdate:
    """
    Result of an importance update operation.
    """

    fact_id: UUID
    old_importance: float
    new_importance: float
    reason: str
    updated_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Importance Manager
# =============================================================================


class ImportanceManager:
    """
    Manages dynamic importance scores for memory facts.

    Importance determines:
    - Retrieval priority (higher importance = more likely to surface)
    - Consolidation survival (low importance = candidate for pruning)
    - Context injection precedence (high importance = always included)

    Operations:
    - track_access: Record fact access, increment counter
    - elevate_importance: Boost importance when fact is useful
    - decay_importance: Reduce importance based on time since access
    - prune_low_importance: Remove facts below threshold
    """

    def __init__(
        self,
        repository: SubstrateRepository | None = None,
        config: ImportanceConfig | None = None,
    ):
        """
        Initialize ImportanceManager.

        Args:
            repository: SubstrateRepository instance
            config: Optional ImportanceConfig
        """
        self._repository = repository
        self._config = config or DEFAULT_CONFIG
        logger.info("ImportanceManager initialized", config=str(self._config))

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    # =========================================================================
    # Access Tracking
    # =========================================================================

    async def track_access(
        self,
        fact_id: UUID,
        access_type: str = "retrieval",
        context: str = "",
        auto_elevate: bool = True,
    ) -> ImportanceUpdate | None:
        """
        Track access to a fact and optionally elevate importance.

        Args:
            fact_id: UUID of the accessed fact
            access_type: Type of access (retrieval, reference, etc.)
            context: Context string for logging
            auto_elevate: Whether to automatically elevate importance

        Returns:
            ImportanceUpdate if importance changed, None otherwise
        """
        if not self._repository:
            return None

        try:
            # Update access_count and last_accessed
            async with self._repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    UPDATE semantic_facts
                    SET access_count = access_count + 1,
                        last_accessed = NOW(),
                        updated_at = NOW()
                    WHERE fact_id = $1
                    RETURNING fact_id, importance, access_count
                    """,
                    fact_id,
                )

                if not row:
                    logger.warning(f"Fact not found for access tracking: {fact_id}")
                    return None

                logger.debug(
                    "Tracked access",
                    fact_id=str(fact_id),
                    access_count=row["access_count"],
                    access_type=access_type,
                )

            # Auto-elevate if configured
            if auto_elevate:
                return await self.elevate_importance(
                    fact_id=fact_id,
                    reason=f"access:{access_type}",
                )

        except Exception as e:
            logger.error(f"Error tracking access: {e}", fact_id=str(fact_id))

        return None

    # =========================================================================
    # Importance Elevation
    # =========================================================================

    async def elevate_importance(
        self,
        fact_id: UUID,
        increment: float | None = None,
        reason: str = "manual",
    ) -> ImportanceUpdate | None:
        """
        Elevate importance of a fact.

        Args:
            fact_id: UUID of the fact
            increment: How much to increase (uses config default if None)
            reason: Reason for elevation

        Returns:
            ImportanceUpdate with old and new values
        """
        if not self._repository:
            return None

        increment = increment or self._config.elevation_increment
        cap = self._config.elevation_cap

        try:
            async with self._repository.acquire() as conn:
                # Get current importance
                row = await conn.fetchrow(
                    "SELECT importance FROM semantic_facts WHERE fact_id = $1",
                    fact_id,
                )

                if not row:
                    return None

                old_importance = row["importance"]
                new_importance = min(cap, old_importance + increment)

                # Skip if no change
                if abs(new_importance - old_importance) < 0.001:
                    return None

                # Update importance
                await conn.execute(
                    """
                    UPDATE semantic_facts
                    SET importance = $1, updated_at = NOW()
                    WHERE fact_id = $2
                    """,
                    new_importance,
                    fact_id,
                )

                logger.debug(
                    "Elevated importance",
                    fact_id=str(fact_id),
                    old=old_importance,
                    new=new_importance,
                    reason=reason,
                )

                return ImportanceUpdate(
                    fact_id=fact_id,
                    old_importance=old_importance,
                    new_importance=new_importance,
                    reason=reason,
                )

        except Exception as e:
            logger.error(f"Error elevating importance: {e}", fact_id=str(fact_id))

        return None

    # =========================================================================
    # Importance Decay
    # =========================================================================

    async def decay_importance(
        self,
        batch_size: int = 1000,
    ) -> list[ImportanceUpdate]:
        """
        Apply importance decay to facts that haven't been accessed recently.

        Uses exponential decay based on time since last access.
        Identity tier facts are exempt from decay.

        Args:
            batch_size: Maximum facts to process

        Returns:
            List of ImportanceUpdate for affected facts
        """
        if not self._repository:
            return []

        updates = []
        now = datetime.now(timezone.utc)

        try:
            async with self._repository.acquire() as conn:
                # Find facts eligible for decay
                exempt_tiers = list(self._config.decay_exempt_tiers)

                rows = await conn.fetch(
                    """
                    SELECT fact_id, importance, last_accessed, tier
                    FROM semantic_facts
                    WHERE tier != ALL($1::text[])
                    AND importance > $2
                    AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
                    LIMIT $3
                    """,
                    exempt_tiers,
                    self._config.decay_floor,
                    batch_size,
                )

                for row in rows:
                    fact_id = row["fact_id"]
                    old_importance = row["importance"]
                    last_accessed = row["last_accessed"]

                    # Calculate decay
                    new_importance = self._calculate_decay(
                        old_importance,
                        last_accessed,
                        now,
                    )

                    # Skip if no significant change
                    if abs(new_importance - old_importance) < 0.01:
                        continue

                    # Update
                    await conn.execute(
                        """
                        UPDATE semantic_facts
                        SET importance = $1, updated_at = NOW()
                        WHERE fact_id = $2
                        """,
                        new_importance,
                        fact_id,
                    )

                    updates.append(
                        ImportanceUpdate(
                            fact_id=fact_id,
                            old_importance=old_importance,
                            new_importance=new_importance,
                            reason="time_decay",
                        )
                    )

            if updates:
                logger.info(f"Applied decay to {len(updates)} facts")

        except Exception as e:
            logger.error(f"Error applying decay: {e}")

        return updates

    def _calculate_decay(
        self,
        importance: float,
        last_accessed: datetime | None,
        now: datetime,
    ) -> float:
        """Calculate decayed importance using exponential decay."""
        if last_accessed is None:
            # Never accessed - decay from creation (assume 30 days old)
            days_since_access = 30.0
        else:
            days_since_access = (now - last_accessed).total_seconds() / 86400.0

        # Exponential decay: I(t) = I_0 * 2^(-t/half_life)
        half_life = self._config.decay_half_life_days
        decay_factor = math.pow(2, -days_since_access / half_life)

        decayed = importance * decay_factor

        # Apply floor
        return max(self._config.decay_floor, decayed)

    # =========================================================================
    # Pruning
    # =========================================================================

    async def prune_low_importance(
        self,
        batch_size: int = 100,
        dry_run: bool = False,
    ) -> int:
        """
        Remove facts with importance below threshold.

        Identity and project tiers are exempt from pruning.
        Facts must be older than min_age_days.

        Args:
            batch_size: Maximum facts to prune
            dry_run: If True, only count candidates without deleting

        Returns:
            Number of facts pruned (or would be pruned if dry_run)
        """
        if not self._repository:
            return 0

        threshold = self._config.prune_threshold
        min_age_days = self._config.prune_min_age_days
        exempt_tiers = list(self._config.prune_exempt_tiers)

        try:
            async with self._repository.acquire() as conn:
                if dry_run:
                    # Just count candidates
                    row = await conn.fetchrow(
                        f"""
                        SELECT COUNT(*) as count
                        FROM semantic_facts
                        WHERE tier != ALL($1::text[])
                        AND importance < $2
                        AND created_at < NOW() - INTERVAL '{min_age_days} days'
                        """,
                        exempt_tiers,
                        threshold,
                    )
                    count = row["count"] if row else 0
                    logger.info(f"DRY RUN: Would prune {count} facts")
                    return count

                # Actually prune
                result = await conn.execute(
                    f"""
                    DELETE FROM semantic_facts
                    WHERE fact_id IN (
                        SELECT fact_id
                        FROM semantic_facts
                        WHERE tier != ALL($1::text[])
                        AND importance < $2
                        AND created_at < NOW() - INTERVAL '{min_age_days} days'
                        LIMIT $3
                    )
                    """,
                    exempt_tiers,
                    threshold,
                    batch_size,
                )

                # Parse DELETE count from result
                count = int(result.split()[-1]) if result else 0
                logger.info(f"Pruned {count} low-importance facts")
                return count

        except Exception as e:
            logger.error(f"Error pruning facts: {e}")

        return 0

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_importance_stats(self) -> dict[str, Any]:
        """
        Get statistics about importance distribution.

        Returns:
            Dict with importance statistics per tier
        """
        if not self._repository:
            return {}

        try:
            async with self._repository.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        tier,
                        COUNT(*) as count,
                        AVG(importance) as avg_importance,
                        MIN(importance) as min_importance,
                        MAX(importance) as max_importance,
                        AVG(access_count) as avg_access_count
                    FROM semantic_facts
                    GROUP BY tier
                    ORDER BY tier
                    """)

                stats = {}
                for row in rows:
                    stats[row["tier"]] = {
                        "count": row["count"],
                        "avg_importance": (
                            round(row["avg_importance"], 3)
                            if row["avg_importance"]
                            else 0
                        ),
                        "min_importance": (
                            round(row["min_importance"], 3)
                            if row["min_importance"]
                            else 0
                        ),
                        "max_importance": (
                            round(row["max_importance"], 3)
                            if row["max_importance"]
                            else 0
                        ),
                        "avg_access_count": (
                            round(row["avg_access_count"], 1)
                            if row["avg_access_count"]
                            else 0
                        ),
                    }

                return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return {}


# =============================================================================
# Singleton / Factory
# =============================================================================


_manager: ImportanceManager | None = None


def get_importance_manager() -> ImportanceManager:
    """Get or create the ImportanceManager singleton."""
    global _manager
    if _manager is None:
        _manager = ImportanceManager()
    return _manager


def init_importance_manager(
    repository,
    config: ImportanceConfig | None = None,
) -> ImportanceManager:
    """Initialize the ImportanceManager with dependencies."""
    manager = get_importance_manager()
    manager.set_repository(repository)
    if config:
        manager._config = config
    return manager


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-047",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "batch-processing",
        "dataclass",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
    ],
    "keywords": [
        "access",
        "based",
        "decay",
        "elevate",
        "facts",
        "importance",
        "low",
        "management",
    ],
    "business_value": "Access tracking (increment access_count, update last_accessed) Importance elevation (boost importance when facts are useful) Importance decay (reduce importance for unused facts) Importance-based prun",
    "last_modified": "2026-01-17T23:47:56Z",
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
