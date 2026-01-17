"""
L9 Memory - Retention Engine
Version: 1.0.0

Automated checkpoint retention and cleanup service.
Implements memory_spec_v3.0.yaml retention policies.

Responsibilities:
- Define retention policies (keep_last_n, time-based)
- Schedule periodic cleanup jobs
- Execute deletion of old checkpoints
- Emit audit trail for retention operations
"""

from __future__ import annotations

import asyncio
import structlog
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from memory.agent_persistence import AgentPersistenceService
    from memory.substrate_repository import SubstrateRepository
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class RetentionPolicy:
    """
    Defines retention rules for checkpoints.

    Attributes:
        keep_last_n: Always keep the N most recent checkpoints
        keep_hourly_for_hours: Keep hourly checkpoints for this many hours
        keep_daily_for_days: Keep daily checkpoints for this many days
        keep_weekly_for_weeks: Keep weekly checkpoints for this many weeks
    """

    keep_last_n: int = 10
    keep_hourly_for_hours: int = 24
    keep_daily_for_days: int = 7
    keep_weekly_for_weeks: int = 4

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "keep_last_n": self.keep_last_n,
            "keep_hourly_for_hours": self.keep_hourly_for_hours,
            "keep_daily_for_days": self.keep_daily_for_days,
            "keep_weekly_for_weeks": self.keep_weekly_for_weeks,
        }


@dataclass
class RetentionResult:
    """Result of a retention cleanup operation."""

    agent_id: str
    checkpoints_before: int
    checkpoints_deleted: int
    checkpoints_after: int
    policy_applied: RetentionPolicy
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the retention operation succeeded."""
        return self.error is None


class RetentionEngine:
    """
    Checkpoint retention and cleanup engine.

    Manages automatic cleanup of old checkpoints based on configurable
    retention policies. Supports scheduled execution and manual triggers.
    """

    def __init__(
        self,
        persistence: Optional[AgentPersistenceService] = None,
        repository: Optional[SubstrateRepository] = None,
        policy: Optional[RetentionPolicy] = None,
    ):
        """
        Initialize retention engine.

        Args:
            persistence: AgentPersistenceService for checkpoint operations
            repository: SubstrateRepository for direct DB access
            policy: Retention policy (uses defaults if not provided)
        """
        self._persistence = persistence
        self._repository = repository
        self._policy = policy or RetentionPolicy()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            "RetentionEngine initialized",
            policy=self._policy.to_dict(),
        )

    def set_persistence(self, persistence: AgentPersistenceService) -> None:
        """Set or update persistence service reference."""
        self._persistence = persistence

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    def set_policy(self, policy: RetentionPolicy) -> None:
        """Update retention policy."""
        self._policy = policy
        logger.info("Retention policy updated", policy=policy.to_dict())

    async def run_cleanup(self, agent_id: str) -> RetentionResult:
        """
        Run retention cleanup for a specific agent.

        Deletes checkpoints that exceed the retention policy limits.

        Args:
            agent_id: Agent identifier to clean up

        Returns:
            RetentionResult with cleanup statistics
        """
        logger.debug("Starting retention cleanup", agent_id=agent_id)

        if self._persistence is None:
            return RetentionResult(
                agent_id=agent_id,
                checkpoints_before=0,
                checkpoints_deleted=0,
                checkpoints_after=0,
                policy_applied=self._policy,
                error="Persistence service not available",
            )

        try:
            # Get current checkpoint count
            checkpoints = await self._persistence.list_checkpoints(
                agent_id=agent_id,
                limit=1000,  # High limit to count all
            )
            checkpoints_before = len(checkpoints)

            # Apply retention policy
            deleted_count = await self._persistence.delete_old_checkpoints(
                agent_id=agent_id,
                keep_last=self._policy.keep_last_n,
            )

            checkpoints_after = checkpoints_before - deleted_count

            result = RetentionResult(
                agent_id=agent_id,
                checkpoints_before=checkpoints_before,
                checkpoints_deleted=deleted_count,
                checkpoints_after=checkpoints_after,
                policy_applied=self._policy,
            )

            logger.info(
                "Retention cleanup completed",
                agent_id=agent_id,
                before=checkpoints_before,
                deleted=deleted_count,
                after=checkpoints_after,
            )

            return result

        except Exception as e:
            logger.error(
                "Retention cleanup failed",
                agent_id=agent_id,
                error=str(e),
                exc_info=True,
            )
            return RetentionResult(
                agent_id=agent_id,
                checkpoints_before=0,
                checkpoints_deleted=0,
                checkpoints_after=0,
                policy_applied=self._policy,
                error=str(e),
            )

    async def run_cleanup_all(self, agent_ids: List[str]) -> List[RetentionResult]:
        """
        Run retention cleanup for multiple agents.

        Args:
            agent_ids: List of agent identifiers to clean up

        Returns:
            List of RetentionResult for each agent
        """
        results = []
        for agent_id in agent_ids:
            result = await self.run_cleanup(agent_id)
            results.append(result)
        return results

    @must_stay_async("callers use await")
    async def start_scheduler(self, interval_hours: int = 24) -> None:
        """
        Start the background retention scheduler.

        Args:
            interval_hours: Hours between cleanup runs (default: 24)
        """
        if self._running:
            logger.warning("Retention scheduler already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop(interval_hours))
        logger.info(
            "Retention scheduler started",
            interval_hours=interval_hours,
        )

    async def stop_scheduler(self) -> None:
        """Stop the background retention scheduler."""
        if not self._running:
            return

        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

        logger.info("Retention scheduler stopped")

    async def _scheduler_loop(self, interval_hours: int) -> None:
        """Internal scheduler loop."""
        while self._running:
            try:
                # Sleep first, then run (avoid immediate run on startup)
                await asyncio.sleep(interval_hours * 3600)

                if not self._running:
                    break

                # Get all unique agent IDs from repository
                # For now, use a default list - in production, query from DB
                # Canonical agent IDs: l-cto (L's primary), cursor-ide (Cursor's primary)
                default_agents = ["l-cto", "cursor-ide"]

                logger.info(
                    "Scheduled retention cleanup starting",
                    agent_count=len(default_agents),
                )

                results = await self.run_cleanup_all(default_agents)

                total_deleted = sum(r.checkpoints_deleted for r in results)
                logger.info(
                    "Scheduled retention cleanup completed",
                    agents_processed=len(results),
                    total_deleted=total_deleted,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Retention scheduler error",
                    error=str(e),
                    exc_info=True,
                )
                # Continue running despite errors
                await asyncio.sleep(60)  # Brief pause before retry


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "RetentionEngine",
    "RetentionPolicy",
    "RetentionResult",
]
