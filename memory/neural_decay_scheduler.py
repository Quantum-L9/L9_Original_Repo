"""
L9 Memory - Neural Decay Scheduler
Version: 1.0.0

Implements neural decay for memory importance scoring.
Part of Stage 2: Hierarchical Memory Consolidation Engine (SUPER-PROMPT).

Decay Formula:
    S(m, t) = I(m) * exp(-λt) * R(m)

Where:
    S(m, t) = Current salience of memory m at time t
    I(m) = Initial importance score (0.0-1.0)
    λ = Decay constant (configurable, default 0.05)
    t = Time since last access (in days)
    R(m) = Reinforcement factor (1.0 + 0.1 * access_count)

Memories that are frequently accessed decay slower due to reinforcement.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Neural Decay Scheduler",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "neural_decay_scheduler",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.__init__",
            "tests.memory.test_hierarchical_consolidation",
        ],
    },
}
# ============================================================================

import asyncio
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from uuid import UUID

logger = structlog.get_logger(__name__)


@dataclass
class DecayConfig:
    """Configuration for neural decay calculation."""

    # Decay constant (λ) - higher = faster decay
    decay_constant: float = 0.05

    # Minimum importance threshold (below this, mark for archival)
    min_importance_threshold: float = 0.1

    # Maximum age in days before forced archival
    max_age_days: int = 365

    # Reinforcement boost per access
    reinforcement_per_access: float = 0.1

    # Maximum reinforcement factor
    max_reinforcement: float = 3.0

    # Batch size for processing
    batch_size: int = 500

    # Sleep between batches (ms)
    batch_sleep_ms: int = 100


@dataclass
class DecayResult:
    """Result of a decay calculation run."""

    packets_processed: int = 0
    packets_updated: int = 0
    packets_archived: int = 0
    facts_processed: int = 0
    facts_updated: int = 0
    facts_archived: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class NeuralDecayScheduler:
    """
    Neural decay scheduler for memory importance adjustment.

    Implements exponential decay with reinforcement to naturally
    deprecate unused memories while preserving frequently accessed ones.
    """

    def __init__(
        self,
        repository: Any | None = None,
        config: DecayConfig | None = None,
        dry_run: bool = False,
    ):
        """
        Initialize neural decay scheduler.

        Args:
            repository: SubstrateRepository for DB access
            config: Decay configuration (uses defaults if None)
            dry_run: If True, calculate but don't update
        """
        self._repository = repository
        self._config = config or DecayConfig()
        self._dry_run = dry_run

        logger.info(
            "NeuralDecayScheduler initialized",
            decay_constant=self._config.decay_constant,
            min_threshold=self._config.min_importance_threshold,
            dry_run=dry_run,
        )

    def calculate_salience(
        self,
        initial_importance: float,
        days_since_access: float,
        access_count: int = 0,
    ) -> float:
        """
        Calculate current salience using neural decay formula.

        S(m, t) = I(m) * exp(-λt) * R(m)

        Args:
            initial_importance: Original importance score (0.0-1.0)
            days_since_access: Days since last access
            access_count: Number of times accessed

        Returns:
            Current salience score (0.0-1.0)
        """
        # Clamp initial importance
        importance = max(0.0, min(1.0, initial_importance))

        # Calculate time decay: exp(-λt)
        decay_factor = math.exp(-self._config.decay_constant * days_since_access)

        # Calculate reinforcement: R(m) = 1.0 + 0.1 * access_count
        reinforcement = 1.0 + (self._config.reinforcement_per_access * access_count)
        reinforcement = min(reinforcement, self._config.max_reinforcement)

        # Calculate final salience
        salience = importance * decay_factor * reinforcement

        # Clamp to valid range
        return max(0.0, min(1.0, salience))

    @must_stay_async("callers use await")
    async def run_decay_pass(
        self,
        reference_time: datetime | None = None,
    ) -> DecayResult:
        """
        Run a full decay pass over all memories.

        Args:
            reference_time: Time to calculate decay from (default: now)

        Returns:
            DecayResult with statistics
        """
        reference_time = reference_time or datetime.now(UTC)
        start_time = datetime.now(UTC)
        result = DecayResult()

        logger.info(
            "Starting neural decay pass",
            reference_time=reference_time.isoformat(),
            dry_run=self._dry_run,
        )

        if self._repository is None:
            result.errors.append("No repository configured")
            return result

        # Process packet_store
        try:
            packet_result = await self._process_packets(reference_time)
            result.packets_processed = packet_result["processed"]
            result.packets_updated = packet_result["updated"]
            result.packets_archived = packet_result["archived"]
        except Exception as e:
            logger.error(f"Packet decay failed: {e}", exc_info=True)
            result.errors.append(f"Packet decay: {e!s}")

        # Process semantic_facts
        try:
            facts_result = await self._process_facts(reference_time)
            result.facts_processed = facts_result["processed"]
            result.facts_updated = facts_result["updated"]
            result.facts_archived = facts_result["archived"]
        except Exception as e:
            logger.error(f"Facts decay failed: {e}", exc_info=True)
            result.errors.append(f"Facts decay: {e!s}")

        result.duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        logger.info(
            "Neural decay pass complete",
            packets_updated=result.packets_updated,
            facts_updated=result.facts_updated,
            duration_ms=result.duration_ms,
        )

        return result

    async def _process_packets(
        self,
        reference_time: datetime,
    ) -> dict[str, int]:
        """Process decay for packet_store."""
        result = {"processed": 0, "updated": 0, "archived": 0}

        if self._repository is None:
            return result

        try:
            async with self._repository.acquire() as conn:
                offset = 0

                while True:
                    # Fetch batch
                    rows = await conn.fetch(
                        """
                        SELECT packet_id, importance_score, access_count,
                               last_accessed, created_at
                        FROM packet_store
                        WHERE importance_score > $1
                        ORDER BY packet_id
                        LIMIT $2 OFFSET $3
                        """,
                        self._config.min_importance_threshold,
                        self._config.batch_size,
                        offset,
                    )

                    if not rows:
                        break

                    result["processed"] += len(rows)

                    for row in rows:
                        packet_id = row["packet_id"]
                        initial_importance = row["importance_score"] or 0.5
                        access_count = row["access_count"] or 0

                        # Calculate days since last access
                        last_access = row["last_accessed"] or row["created_at"]
                        if last_access:
                            days_since = (
                                reference_time - last_access
                            ).total_seconds() / 86400
                        else:
                            days_since = 30  # Default to 30 days if unknown

                        # Calculate new salience
                        new_salience = self.calculate_salience(
                            initial_importance,
                            days_since,
                            access_count,
                        )

                        if self._dry_run:
                            if new_salience < self._config.min_importance_threshold:
                                result["archived"] += 1
                            elif abs(new_salience - initial_importance) > 0.01:
                                result["updated"] += 1
                            continue

                        # Update or archive
                        if new_salience < self._config.min_importance_threshold:
                            # Mark for archival
                            await conn.execute(
                                """
                                UPDATE packet_store
                                SET tags = array_append(
                                    COALESCE(tags, ARRAY[]::text[]),
                                    'decay_archived'
                                ),
                                importance_score = $1
                                WHERE packet_id = $2
                                AND NOT ('decay_archived' = ANY(COALESCE(tags, ARRAY[]::text[])))
                                """,
                                new_salience,
                                packet_id,
                            )
                            result["archived"] += 1
                        elif abs(new_salience - initial_importance) > 0.01:
                            # Update importance
                            await conn.execute(
                                """
                                UPDATE packet_store
                                SET importance_score = $1
                                WHERE packet_id = $2
                                """,
                                new_salience,
                                packet_id,
                            )
                            result["updated"] += 1

                    offset += len(rows)

                    if self._config.batch_sleep_ms > 0:
                        await asyncio.sleep(self._config.batch_sleep_ms / 1000.0)

        except Exception as e:
            logger.error(f"Packet processing failed: {e}", exc_info=True)
            raise

        return result

    async def _process_facts(
        self,
        reference_time: datetime,
    ) -> dict[str, int]:
        """Process decay for semantic_facts."""
        result = {"processed": 0, "updated": 0, "archived": 0}

        if self._repository is None:
            return result

        try:
            async with self._repository.acquire() as conn:
                offset = 0

                while True:
                    # Fetch batch (exclude identity tier - those don't decay)
                    rows = await conn.fetch(
                        """
                        SELECT fact_id, importance, access_count,
                               last_accessed, created_at, tier
                        FROM semantic_facts
                        WHERE importance > $1
                        AND tier != 'identity'
                        ORDER BY fact_id
                        LIMIT $2 OFFSET $3
                        """,
                        self._config.min_importance_threshold,
                        self._config.batch_size,
                        offset,
                    )

                    if not rows:
                        break

                    result["processed"] += len(rows)

                    for row in rows:
                        fact_id = row["fact_id"]
                        initial_importance = row["importance"] or 0.5
                        access_count = row["access_count"] or 0

                        # Calculate days since last access
                        last_access = row["last_accessed"] or row["created_at"]
                        if last_access:
                            days_since = (
                                reference_time - last_access
                            ).total_seconds() / 86400
                        else:
                            days_since = 30

                        # Apply tier-specific decay modifiers
                        tier = row["tier"]
                        tier_modifier = 1.0
                        if tier == "project":
                            tier_modifier = 0.5  # Project facts decay slower
                        elif tier == "session":
                            tier_modifier = 2.0  # Session facts decay faster

                        # Calculate new salience with tier modifier
                        adjusted_days = days_since * tier_modifier
                        new_salience = self.calculate_salience(
                            initial_importance,
                            adjusted_days,
                            access_count,
                        )

                        if self._dry_run:
                            if new_salience < self._config.min_importance_threshold:
                                result["archived"] += 1
                            elif abs(new_salience - initial_importance) > 0.01:
                                result["updated"] += 1
                            continue

                        # Update or archive
                        if new_salience < self._config.min_importance_threshold:
                            # Mark for archival
                            await conn.execute(
                                """
                                UPDATE semantic_facts
                                SET tags = array_append(
                                    COALESCE(tags, ARRAY[]::text[]),
                                    'decay_archived'
                                ),
                                importance = $1
                                WHERE fact_id = $2
                                AND NOT ('decay_archived' = ANY(COALESCE(tags, ARRAY[]::text[])))
                                """,
                                new_salience,
                                fact_id,
                            )
                            result["archived"] += 1
                        elif abs(new_salience - initial_importance) > 0.01:
                            # Update importance
                            await conn.execute(
                                """
                                UPDATE semantic_facts
                                SET importance = $1
                                WHERE fact_id = $2
                                """,
                                new_salience,
                                fact_id,
                            )
                            result["updated"] += 1

                    offset += len(rows)

                    if self._config.batch_sleep_ms > 0:
                        await asyncio.sleep(self._config.batch_sleep_ms / 1000.0)

        except Exception as e:
            logger.error(f"Facts processing failed: {e}", exc_info=True)
            raise

        return result

    @must_stay_async("callers use await")
    async def get_decay_preview(
        self,
        packet_id: UUID | None = None,
        fact_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Preview decay calculation for a specific memory.

        Args:
            packet_id: UUID of packet to preview
            fact_id: UUID of fact to preview

        Returns:
            Dict with current and projected values
        """
        if self._repository is None:
            return {"error": "No repository configured"}

        reference_time = datetime.now(UTC)

        try:
            async with self._repository.acquire() as conn:
                if packet_id:
                    row = await conn.fetchrow(
                        """
                        SELECT importance_score, access_count,
                               last_accessed, created_at
                        FROM packet_store
                        WHERE packet_id = $1
                        """,
                        packet_id,
                    )
                    if not row:
                        return {"error": "Packet not found"}

                    importance_key = "importance_score"
                elif fact_id:
                    row = await conn.fetchrow(
                        """
                        SELECT importance, access_count,
                               last_accessed, created_at, tier
                        FROM semantic_facts
                        WHERE fact_id = $1
                        """,
                        fact_id,
                    )
                    if not row:
                        return {"error": "Fact not found"}

                    importance_key = "importance"
                else:
                    return {"error": "No packet_id or fact_id provided"}

                initial = row[importance_key] or 0.5
                access_count = row["access_count"] or 0
                last_access = row["last_accessed"] or row["created_at"]

                if last_access:
                    days_since = (reference_time - last_access).total_seconds() / 86400
                else:
                    days_since = 30

                current_salience = self.calculate_salience(
                    initial, days_since, access_count
                )

                # Project 7, 30, 90 days
                return {
                    "current": {
                        "importance": initial,
                        "salience": current_salience,
                        "access_count": access_count,
                        "days_since_access": round(days_since, 1),
                    },
                    "projections": {
                        "7_days": round(
                            self.calculate_salience(
                                initial, days_since + 7, access_count
                            ),
                            3,
                        ),
                        "30_days": round(
                            self.calculate_salience(
                                initial, days_since + 30, access_count
                            ),
                            3,
                        ),
                        "90_days": round(
                            self.calculate_salience(
                                initial, days_since + 90, access_count
                            ),
                            3,
                        ),
                    },
                    "decay_constant": self._config.decay_constant,
                    "threshold": self._config.min_importance_threshold,
                }

        except Exception as e:
            logger.error(f"Decay preview failed: {e}", exc_info=True)
            return {"error": str(e)}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-036",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "batch-processing",
        "dataclass",
        "learning",
        "logging",
        "memory-substrate",
        "scheduling",
    ],
    "keywords": [
        "calculate",
        "decay",
        "importance",
        "memory",
        "neural",
        "pass",
        "preview",
        "reinforcement",
    ],
    "business_value": "Implements neural decay for memory importance scoring. Part of Stage 2: Hierarchical Memory Consolidation Engine (SUPER-PROMPT). S(m, t) = I(m) * exp(-λt) * R(m) S(m, t) = Current salience of memory m",
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
