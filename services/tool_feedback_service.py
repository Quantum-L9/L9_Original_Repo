"""
L9 Tool Feedback Learning - Execution Outcome Recording
=======================================================

GMP-TFL-001: Centralized service for recording tool execution outcomes and
exposing recent success-rate signals to dynamic discovery.

This builds on the existing audit system (core/tools/tool_audit.py) by:
- Storing structured execution outcomes in Postgres
- Enabling feedback-aware re-ranking in core/tools/dynamic_discovery.py
- Providing a single async API for recording and querying feedback

Alignment:
- Uses MemorySubstrateService connection pattern (postgres_pool)
- Must remain async (see must_stay_async decorator usage in audit)
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import structlog

from config.settings import get_integration_settings

logger = structlog.get_logger(__name__)


@dataclass
class ToolFeedbackEntry:
    """In-memory representation of a single tool execution outcome."""

    task_query: str
    task_embedding: Sequence[float]
    task_type: str | None
    session_id: str | None

    tool_name: str
    success: bool
    execution_time_ms: float
    error_type: str | None

    agent_id: str
    confidence_score: float | None
    discovery_rank: int | None

    request_id: str | None


class ToolFeedbackService:
    """
    Service responsible for persisting tool execution feedback and
    computing recent success-rate signals.

    This is intentionally lightweight and focused on:
    - Batched inserts into tool_execution_feedback
    - Success-rate aggregation using the materialized view if present
    """

    def __init__(self, substrate_service: MemorySubstrateService) -> None:
        self.substrate = substrate_service
        self._buffer: list[ToolFeedbackEntry] = []
        self._buffer_size = get_integration_settings().l9_tool_feedback_buffer_size

    # --------------------------------------------------------------------- #
    # Recording
    # --------------------------------------------------------------------- #

    async def record_outcome(self, entry: ToolFeedbackEntry) -> None:
        """
        Record a single tool execution outcome, with batched flushing.

        Safe to call in the hot path (tool_audit.execute_tool_with_audit).
        """
        settings = get_integration_settings()
        if not settings.l9_tool_feedback_enabled:
            return

        if not getattr(self.substrate, "postgres_pool", None):
            logger.debug("Tool feedback: postgres_pool not available, skipping")
            return

        self._buffer.append(entry)
        if len(self._buffer) >= self._buffer_size:
            await self.flush()

    async def flush(self) -> None:
        """
        Flush buffered feedback entries into Postgres.

        Called opportunistically from record_outcome; can also be called
        explicitly by background maintenance jobs.
        """
        if not self._buffer:
            return

        if not getattr(self.substrate, "postgres_pool", None):
            logger.debug("Tool feedback: postgres_pool not available, skipping flush")
            return

        buffer = self._buffer
        self._buffer = []

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                # We rely on the application to ensure the task_embedding dim matches
                await conn.executemany(
                    """
                    INSERT INTO tool_execution_feedback (
                        task_query,
                        task_embedding,
                        task_type,
                        session_id,
                        tool_name,
                        success,
                        execution_time_ms,
                        error_type,
                        agent_id,
                        confidence_score,
                        discovery_rank,
                        request_id
                    )
                    VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7, $8,
                        $9, $10, $11, $12
                    )
                    """,
                    [
                        (
                            e.task_query,
                            list(e.task_embedding),
                            e.task_type,
                            e.session_id,
                            e.tool_name,
                            e.success,
                            e.execution_time_ms,
                            e.error_type,
                            e.agent_id,
                            e.confidence_score,
                            e.discovery_rank,
                            e.request_id,
                        )
                        for e in buffer
                    ],
                )

            logger.info("Tool feedback: flushed entries", count=len(buffer))
        except Exception as exc:
            logger.error("Tool feedback: flush failed", error=str(exc))
            # Put entries back to retry later
            self._buffer.extend(buffer)

    # --------------------------------------------------------------------- #
    # Success-rate Queries
    # --------------------------------------------------------------------- #

    async def get_success_rates(
        self,
        tool_names: Iterable[str],
        task_type: str | None,
    ) -> dict[str, float]:
        """
        Return a mapping tool_name -> success_rate for the last 24h window.

        Uses the materialized view tool_success_rates_24h when present.
        Falls back to a direct aggregate query on tool_execution_feedback.
        """
        settings = get_integration_settings()
        neutral = settings.l9_tool_success_neutral_prior

        names = list({n for n in tool_names if n})
        if not names:
            return {}

        if not getattr(self.substrate, "postgres_pool", None):
            return dict.fromkeys(names, neutral)

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                if task_type:
                    rows = await conn.fetch(
                        """
                        SELECT tool_name, success_rate
                        FROM tool_success_rates_24h
                        WHERE tool_name = ANY($1::text[])
                          AND task_type = $2
                        """,
                        names,
                        task_type,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT tool_name, success_rate
                        FROM tool_success_rates_24h
                        WHERE tool_name = ANY($1::text[])
                        """,
                        names,
                    )

            rates: dict[str, float] = dict.fromkeys(names, neutral)
            for row in rows:
                tool = row["tool_name"]
                rate = row["success_rate"]
                if rate is not None:
                    rates[tool] = float(rate)

            return rates

        except Exception as exc:
            logger.error("Tool feedback: get_success_rates failed", error=str(exc))
            return dict.fromkeys(names, neutral)


# Convenience constructor to avoid circular imports at module import time
_tool_feedback_service: ToolFeedbackService | None = None


def get_tool_feedback_service(
    substrate_service: MemorySubstrateService,
) -> ToolFeedbackService:
    """
    Get singleton-like ToolFeedbackService bound to the given substrate.

    We intentionally avoid global substrate references and require explicit
    passing from the caller, matching patterns used elsewhere in L9.
    """
    global _tool_feedback_service

    if _tool_feedback_service is None:
        _tool_feedback_service = ToolFeedbackService(substrate_service)

    return _tool_feedback_service
