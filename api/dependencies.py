"""
L9 API Dependencies
====================

FastAPI dependency injection functions for accessing services from app.state.

This module provides standard Depends() wrappers for:
- SubstrateService (memory substrate)
- AgentExecutorService (agent execution)
- GovernanceEngineService (governance policies)
- ExecutorToolRegistry (tool dispatch)
- Neo4j/Redis clients (infrastructure)

Version: 1.0.0
Created: 2026-01-06
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Dependencies",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-18T02:40:23Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "dependencies",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.routes.compliance", "ci.check_dependency_patterns"],
    },
}
# ============================================================================

from typing import Any

import structlog
from fastapi import HTTPException, Request

# Re-export verify_api_key for convenience
from api.auth import verify_api_key

logger = structlog.get_logger(__name__)

__all__ = [
    "get_agent_executor",
    "get_aios_runtime",
    "get_consolidation_service",
    "get_evaluator",
    "get_governance_engine",
    "get_memory_state_manager",
    "get_neo4j_client",
    "get_observability_service",
    "get_redis_client",
    "get_substrate_service",
    "get_timeline_service",
    "get_tool_registry",
    "verify_api_key",
]

# =============================================================================
# Core Service Dependencies
# =============================================================================


def get_substrate_service(request: Request) -> Any:
    """
    Get SubstrateService from app.state.

    Returns the memory substrate service for packet storage and retrieval.

    Raises:
        HTTPException: If substrate service is not initialized.
    """
    service = getattr(request.app.state, "substrate_service", None)
    if service is None:
        logger.warning("substrate_service not available in app.state")
        raise HTTPException(
            status_code=503, detail="Memory substrate service not available"
        )
    return service


def get_agent_executor(
    request: Request,
) -> Any:  # LEGITIMATE: Scaffolding for agent routes
    """
    Get AgentExecutorService from app.state.

    Returns the agent executor for task execution.

    Raises:
        HTTPException: If agent executor is not initialized.
    """
    executor = getattr(request.app.state, "agent_executor", None)
    if executor is None:
        logger.warning("agent_executor not available in app.state")
        raise HTTPException(
            status_code=503, detail="Agent executor service not available"
        )
    return executor


def get_governance_engine(
    request: Request,
) -> Any:  # SCAFFOLDING: Awaiting governance route integration
    """
    Get GovernanceEngineService from app.state.

    Returns the governance engine for policy evaluation.

    SCAFFOLDING: This dependency is prepared for future governance routes.
    Currently, governance engine is accessed directly via app.state in lifespan.

    Raises:
        HTTPException: If governance engine is not initialized.
    """
    engine = getattr(request.app.state, "governance_engine", None)
    if engine is None:
        logger.warning("governance_engine not available in app.state")
        raise HTTPException(status_code=503, detail="Governance engine not available")
    return engine


def get_tool_registry(request: Request) -> Any:
    """
    Get ExecutorToolRegistry from app.state.

    Returns the tool registry for governance-aware tool dispatch.

    Raises:
        HTTPException: If tool registry is not initialized.
    """
    registry = getattr(request.app.state, "tool_registry", None)
    if registry is None:
        logger.warning("tool_registry not available in app.state")
        raise HTTPException(status_code=503, detail="Tool registry not available")
    return registry


# =============================================================================
# Infrastructure Dependencies
# =============================================================================


def get_neo4j_client(
    request: Request,
) -> Any:  # SCAFFOLDING: Routes use own lazy import
    """
    Get Neo4j client from app.state.

    Returns the Neo4j async client for graph operations.

    SCAFFOLDING: This dependency is prepared for future routes.
    Currently, api/memory/graph.py uses its own get_neo4j() lazy import.

    Raises:
        HTTPException: If Neo4j client is not initialized.
    """
    client = getattr(request.app.state, "neo4j_client", None)
    if client is None:
        logger.warning("neo4j_client not available in app.state")
        raise HTTPException(status_code=503, detail="Neo4j client not available")
    return client


def get_redis_client(
    request: Request,
) -> Any:  # SCAFFOLDING: Routes use own lazy import
    """
    Get Redis client from app.state.

    Returns the Redis client for caching and state management.

    SCAFFOLDING: This dependency is prepared for future routes.
    Currently, api/memory/cache.py uses its own get_redis() lazy import.

    Raises:
        HTTPException: If Redis client is not initialized.
    """
    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        logger.warning("redis_client not available in app.state")
        raise HTTPException(status_code=503, detail="Redis client not available")
    return client


# =============================================================================
# Optional Service Dependencies (return None if not available)
# =============================================================================


def get_observability_service(
    request: Request,
) -> Any | None:  # SCAFFOLDING: Awaiting observability routes
    """
    Get ObservabilityService from app.state.

    Returns the observability service for tracing/metrics, or None if not enabled.

    SCAFFOLDING: This dependency is prepared for future observability routes.
    Currently, observability is accessed directly via app.state in lifespan.

    Note: Does not raise - observability is optional.
    """
    return getattr(request.app.state, "observability_service", None)


def get_memory_orchestrator(request: Request) -> Any | None:
    """
    Get MemoryOrchestrator from app.state.

    Returns the memory orchestrator for batch operations, or None if not available.

    Note: Does not raise - orchestrator is optional.
    """
    return getattr(request.app.state, "memory_orchestrator", None)


def get_world_model_service(
    request: Request,
) -> Any | None:  # SCAFFOLDING: Awaiting world model routes
    """
    Get WorldModelService from app.state.

    Returns the world model service, or None if not available.

    SCAFFOLDING: This dependency is prepared for future world model routes.
    Currently, world model service is accessed directly via app.state.

    Note: Does not raise - world model is optional.
    """
    return getattr(request.app.state, "world_model_service", None)


# =============================================================================
# Memory & Timeline Dependencies
# =============================================================================


def get_timeline_service(request: Request) -> Any | None:
    """
    Get TimelineService from app.state.

    Returns the timeline service for reconstructing agent memory timelines,
    or None if not available.

    Note: Does not raise - timeline service is optional.
    """
    return getattr(request.app.state, "timeline_service", None)


def get_memory_state_manager(request: Request) -> Any | None:
    """
    Get MemoryStateManager from app.state.

    Returns the memory state manager for agent state management,
    or None if not available.

    Note: Does not raise - state manager is optional.
    """
    return getattr(request.app.state, "memory_state_manager", None)


def get_consolidation_service(request: Request) -> Any | None:
    """
    Get ConsolidationService from app.state.

    Returns the memory consolidation service for summarization and rollups,
    or None if not available.

    Note: Does not raise - consolidation is optional.
    """
    return getattr(request.app.state, "consolidation_service", None)


# =============================================================================
# Runtime Dependencies
# =============================================================================


def get_aios_runtime(request: Request) -> Any | None:
    """
    Get AIOSRuntime from app.state.

    Returns the AIOS runtime for agent execution orchestration,
    or None if not available.

    Note: Does not raise - runtime is optional.
    """
    return getattr(request.app.state, "aios_runtime", None)


def get_evaluator(request: Request) -> Any | None:
    """
    Get Evaluator from app.state.

    Returns the evaluator service for response evaluation,
    or None if not available.

    Note: Does not raise - evaluator is optional.
    """
    return getattr(request.app.state, "evaluator", None)


def get_virtual_context_manager(request: Request) -> Any | None:
    """
    Get VirtualContextManager from app.state.

    Returns the virtual context manager for memory windowing,
    or None if not available.

    Note: Does not raise - virtual context is optional.
    """
    return getattr(request.app.state, "virtual_context_manager", None)


def get_housekeeping_engine(request: Request) -> Any | None:
    """
    Get HousekeepingEngine from app.state.

    Returns the memory housekeeping engine for scheduled cleanup,
    or None if not available.

    Note: Does not raise - housekeeping is optional.
    """
    return getattr(request.app.state, "housekeeping_engine", None)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth"],
    "tags": [
        "adapter",
        "api",
        "api-gateway",
        "auth",
        "batch-processing",
        "caching",
        "logging",
        "metrics",
        "operations",
        "scheduling",
    ],
    "keywords": [
        "agent",
        "aios",
        "client",
        "consolidation",
        "dependencies",
        "engine",
        "evaluator",
        "executor",
    ],
    "business_value": "SubstrateService (memory substrate) AgentExecutorService (agent execution) GovernanceEngineService (governance policies) ExecutorToolRegistry (tool dispatch) Neo4j/Redis clients (infrastructure) Versi",
    "last_modified": "2026-01-18T02:40:23Z",
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
