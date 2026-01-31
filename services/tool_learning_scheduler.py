"""
L9 Tool Feedback Learning - Scheduler Registration
===================================================

GMP-TFL-001: Register daily analysis job for tool feedback learning.

This module provides a function to register the ToolLearningEngine's
daily_analysis() method as a scheduled job.

Call register_tool_learning_jobs() from your application's startup
(e.g., in api/server.py lifespan) to enable background learning.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

from config.settings import get_integration_settings
from memory.substrate_service import get_memory_substrate_service  # if available
from services.tool_learning_engine import ToolLearningEngine


async def register_tool_learning_jobs(scheduler):
    """
    Performs registration of daily tool feedback learning jobs in the scheduler based on integration settings.

    Args:
        scheduler: The scheduler instance to which jobs will be added.


    Raises:
        Exception: If job registration fails due to scheduler issues or missing settings.
    """
    settings = get_integration_settings()
    if not settings.l9_tool_feedback_enabled:
        return

    substrate_service = get_memory_substrate_service()
    engine = ToolLearningEngine(substrate_service)

    scheduler.add_job(
        engine.daily_analysis,
        trigger="cron",
        hour=settings.l9_tool_learning_daily_hour_utc,
        minute=settings.l9_tool_learning_daily_minute_utc,
        id="tool_learning_daily",
        replace_existing=True,
    )


__all__ = ["register_tool_learning_jobs"]
