"""
L9 WorldModel Orchestrator - Scheduler
Version: 1.1.0

Specialized component for world_model orchestration.
Handles scheduling of propagation and update cycles.
"""

import structlog
from datetime import datetime, timedelta
from typing import Any, Optional
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class WorldModelScheduler:
    """
    Scheduler for WorldModel Orchestrator.

    Manages timing and scheduling of world model updates.
    Implements batching and throttling for efficient updates.
    """

    def __init__(
        self,
        min_interval_seconds: int = 5,
        batch_size: int = 10,
        max_pending: int = 100,
    ):
        """
        Initialize scheduler.

        Args:
            min_interval_seconds: Minimum time between updates
            batch_size: Minimum insights to trigger immediate update
            max_pending: Maximum pending updates before forced flush
        """
        self._min_interval = timedelta(seconds=min_interval_seconds)
        self._batch_size = batch_size
        self._max_pending = max_pending
        self._last_update: Optional[datetime] = None
        self._pending_count = 0
        logger.info(
            f"WorldModelScheduler initialized (interval={min_interval_seconds}s)"
        )

    def schedule_update(self, insights: list[dict[str, Any]]) -> bool:
        """
        Determine if world model update should proceed now.

        Returns True if update should happen immediately,
        False if it should be queued for later.

        Args:
            insights: List of insights to evaluate

        Returns:
            True to proceed with update, False to queue
        """
        now = datetime.utcnow()

        # Count high-confidence insights
        high_confidence = sum(
            1
            for i in insights
            if i.get("confidence", 0) >= 0.8 and i.get("trigger_world_model", False)
        )

        # Update pending count
        self._pending_count += len(insights)

        # Force update if max pending exceeded
        if self._pending_count >= self._max_pending:
            logger.info(f"Scheduler: force update (pending={self._pending_count})")
            self._last_update = now
            self._pending_count = 0
            return True

        # Check batch size threshold
        if high_confidence >= self._batch_size:
            logger.info(
                f"Scheduler: batch threshold reached ({high_confidence} high-confidence)"
            )
            self._last_update = now
            self._pending_count = 0
            return True

        # Check time interval
        if self._last_update is None or (now - self._last_update) >= self._min_interval:
            logger.debug("Scheduler: interval elapsed, allowing update")
            self._last_update = now
            self._pending_count = 0
            return True

        # Queue for later
        logger.debug(f"Scheduler: queuing update (pending={self._pending_count})")
        return False

    @must_stay_async("callers use await")
    async def process(self, data: dict) -> dict:
        """
        Process scheduling request.

        Args:
            data: Dict with 'insights' key

        Returns:
            Dict with scheduling decision
        """
        insights = data.get("insights", [])
        should_update = self.schedule_update(insights)

        return {
            "success": True,
            "should_update": should_update,
            "pending_count": self._pending_count,
        }

    def reset(self) -> None:
        """Reset scheduler state."""
        self._last_update = None
        self._pending_count = 0
        logger.info("Scheduler reset")


# Backwards compatibility alias
Scheduler = WorldModelScheduler
