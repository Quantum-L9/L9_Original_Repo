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

# ============================================================================
__dora_meta__ = {
    "component_name": "Scheduler Registration",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "services",
    "module_name": "tool_learning_scheduler",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "logging",
        "operations",
        "scheduling",
        "service",
        "services",
    ],
    "keywords": [
        "analysis",
        "feedback",
        "jobs",
        "learning",
        "module",
        "register",
        "registration",
        "scheduler",
    ],
    "business_value": "This module provides a function to register the ToolLearningEngine's daily_analysis() method as a scheduled job. Call register_tool_learning_jobs() from your application's startup (e.g., in api/server",
    "last_modified": "2026-01-31T22:22:00Z",
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
