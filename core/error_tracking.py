"""
L9 Core - Error Causality Tracking
===================================

Tracks errors in Neo4j with causality chains.
Enables root cause analysis and error pattern detection.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Error Causality Tracking",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "error_tracking",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "memory.slack_ingest",
            "memory.substrate_service",
        ],
    },
}
# ============================================================================

import traceback
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


async def log_error_to_graph(
    error: Exception,
    context: dict[str, Any] | None = None,
    parent_error_id: str | None = None,
    source: str | None = None,
) -> str:
    """
    Log an error to Neo4j with causality chain.

    Creates an Error event node linked to its cause (if parent_error_id provided).
    This enables queries like "show all errors caused by X".

    Args:
        error: The exception that occurred
        context: Additional context (endpoint, agent_id, etc.)
        parent_error_id: ID of the error that caused this one (for chaining)
        source: Source of the error (e.g., "api.chat", "tool.web_search")

    Returns:
        Error ID for use as parent_error_id in downstream errors

    Example:
        try:
            result = await call_openai()
        except TimeoutError as e:
            err_id = await log_error_to_graph(e, {"service": "openai"})
            raise ToolError("OpenAI timeout", cause_id=err_id)
    """
    try:
        from memory.graph_client import get_neo4j_client
    except ImportError:
        logger.debug("Neo4j client not available - skipping error logging")
        return ""

    neo4j = await get_neo4j_client()
    if not neo4j:
        return ""  # Neo4j not available, skip silently

    error_id = f"error:{uuid4()}"
    ctx = context or {}

    try:
        await neo4j.create_event(
            event_id=error_id,
            event_type="error",
            timestamp=datetime.utcnow().isoformat(),
            properties={
                "error_type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
                "source": source or ctx.get("source", "unknown"),
                **ctx,
            },
            parent_event_id=parent_error_id,  # Creates TRIGGERED relationship
        )

        # Create Error type entity for aggregation
        error_type = type(error).__name__
        await neo4j.create_entity(
            entity_type="ErrorType",
            entity_id=error_type,
            properties={"name": error_type},
        )
        await neo4j.create_relationship(
            from_type="Event",
            from_id=error_id,
            to_type="ErrorType",
            to_id=error_type,
            rel_type="IS_TYPE",
        )

        logger.debug(f"Logged error to graph: {error_id} ({error_type})")
        return error_id

    except Exception as e:
        logger.warning(f"Failed to log error to Neo4j: {e}")
        return ""


async def get_error_chain(error_id: str) -> list[dict[str, Any]]:
    """
    Get the causality chain for an error (all errors that led to this one).

    Args:
        error_id: The error ID to trace back from

    Returns:
        List of error events in causality order (root cause first)
    """
    try:
        from memory.graph_client import get_neo4j_client
    except ImportError:
        return []

    neo4j = await get_neo4j_client()
    if not neo4j:
        return []

    try:
        # Traverse backwards through TRIGGERED relationships
        return await neo4j.run_query(
            """
            MATCH path = (root:Event)-[:TRIGGERED*0..10]->(target:Event {id: $error_id})
            WHERE root.event_type = 'error'
            UNWIND nodes(path) as node
            RETURN DISTINCT node
            ORDER BY node.timestamp
        """,
            {"error_id": error_id},
        )

    except Exception as e:
        logger.warning(f"Failed to get error chain: {e}")
        return []


async def get_errors_by_type(
    error_type: str,
    limit: int = 50,
    since: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get all errors of a specific type.

    Args:
        error_type: Error class name (e.g., "TimeoutError", "ValueError")
        limit: Maximum errors to return
        since: ISO timestamp to filter from (optional)

    Returns:
        List of error events
    """
    try:
        from memory.graph_client import get_neo4j_client
    except ImportError:
        return []

    neo4j = await get_neo4j_client()
    if not neo4j:
        return []

    try:
        params: dict[str, Any] = {"error_type": error_type, "limit": limit}

        if since:
            query = """
                MATCH (e:Event)-[:IS_TYPE]->(:ErrorType {id: $error_type})
                WHERE e.timestamp >= $since
                RETURN e
                ORDER BY e.timestamp DESC
                LIMIT $limit
            """
            params["since"] = since
        else:
            query = """
                MATCH (e:Event)-[:IS_TYPE]->(:ErrorType {id: $error_type})
                RETURN e
                ORDER BY e.timestamp DESC
                LIMIT $limit
            """

        result = await neo4j.run_query(query, params)
        return [dict(r["e"]) for r in result] if result else []

    except Exception as e:
        logger.warning(f"Failed to get errors by type: {e}")
        return []


async def get_error_stats(hours: int = 24) -> dict[str, int]:
    """
    Get error counts by type for the last N hours.

    Args:
        hours: Number of hours to look back

    Returns:
        Dict mapping error type to count
    """
    try:
        from memory.graph_client import get_neo4j_client
    except ImportError:
        return {}

    neo4j = await get_neo4j_client()
    if not neo4j:
        return {}

    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        result = await neo4j.run_query(
            """
            MATCH (e:Event {event_type: 'error'})
            WHERE e.timestamp >= $cutoff
            RETURN e.error_type as error_type, count(*) as count
            ORDER BY count DESC
        """,
            {"cutoff": cutoff},
        )

        return {r["error_type"]: r["count"] for r in result} if result else {}

    except Exception as e:
        logger.warning(f"Failed to get error stats: {e}")
        return {}


__all__ = [
    "get_error_chain",
    "get_error_stats",
    "get_errors_by_type",
    "log_error_to_graph",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_client"],
    "tags": [
        "api",
        "async",
        "core",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "service",
        "streaming",
    ],
    "keywords": [
        "analysis",
        "causality",
        "chain",
        "detection",
        "errors",
        "graph",
        "log",
        "pattern",
    ],
    "business_value": "Utility module for error tracking",
    "last_modified": "2026-01-07T13:35:57Z",
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
