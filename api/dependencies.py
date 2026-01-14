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

from typing import Any, Optional

from fastapi import Request, HTTPException

import structlog

# Re-export verify_api_key for convenience
from api.auth import verify_api_key

logger = structlog.get_logger(__name__)

__all__ = [
    "verify_api_key",
    "get_substrate_service",
    "get_agent_executor",
    "get_governance_engine",
    "get_tool_registry",
    "get_neo4j_client",
    "get_redis_client",
    "get_observability_service",
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
            status_code=503,
            detail="Memory substrate service not available"
        )
    return service


def get_agent_executor(request: Request) -> Any:  # LEGITIMATE: Scaffolding for agent routes
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
            status_code=503,
            detail="Agent executor service not available"
        )
    return executor


def get_governance_engine(request: Request) -> Any:  # SCAFFOLDING: Awaiting governance route integration
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
        raise HTTPException(
            status_code=503,
            detail="Governance engine not available"
        )
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
        raise HTTPException(
            status_code=503,
            detail="Tool registry not available"
        )
    return registry


# =============================================================================
# Infrastructure Dependencies
# =============================================================================


def get_neo4j_client(request: Request) -> Any:  # SCAFFOLDING: Routes use own lazy import
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
        raise HTTPException(
            status_code=503,
            detail="Neo4j client not available"
        )
    return client


def get_redis_client(request: Request) -> Any:  # SCAFFOLDING: Routes use own lazy import
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
        raise HTTPException(
            status_code=503,
            detail="Redis client not available"
        )
    return client


# =============================================================================
# Optional Service Dependencies (return None if not available)
# =============================================================================


def get_observability_service(request: Request) -> Optional[Any]:  # SCAFFOLDING: Awaiting observability routes
    """
    Get ObservabilityService from app.state.
    
    Returns the observability service for tracing/metrics, or None if not enabled.
    
    SCAFFOLDING: This dependency is prepared for future observability routes.
    Currently, observability is accessed directly via app.state in lifespan.
    
    Note: Does not raise - observability is optional.
    """
    return getattr(request.app.state, "observability_service", None)


def get_memory_orchestrator(request: Request) -> Optional[Any]:
    """
    Get MemoryOrchestrator from app.state.
    
    Returns the memory orchestrator for batch operations, or None if not available.
    
    Note: Does not raise - orchestrator is optional.
    """
    return getattr(request.app.state, "memory_orchestrator", None)


def get_world_model_service(request: Request) -> Optional[Any]:  # SCAFFOLDING: Awaiting world model routes
    """
    Get WorldModelService from app.state.
    
    Returns the world model service, or None if not available.
    
    SCAFFOLDING: This dependency is prepared for future world model routes.
    Currently, world model service is accessed directly via app.state.
    
    Note: Does not raise - world model is optional.
    """
    return getattr(request.app.state, "world_model_service", None)





