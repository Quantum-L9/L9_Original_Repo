"""
L9 API - World Model Routes
============================

API endpoints for querying the L9 world model.

Version: 1.0.0 (GMP-18)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "World Model Routes",
    "module_version": "1.0.0 (GMP-18)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "worldmodel",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /agent/{agent_id}/capabilities",
            "GET /infrastructure/status",
            "GET /approvals/summary",
            "GET /integrations",
            "GET /context/{agent_id}",
        ],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verify_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/worldmodel", tags=["worldmodel"])


def get_world_model_service(request: Request) -> Any:
    """Get WorldModelService from app.state."""
    service = getattr(request.app.state, "world_model_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="WorldModelService not initialized. Check server logs.",
        )
    return service


@router.get("/agent/{agent_id}/capabilities")
async def get_agent_capabilities(
    agent_id: str,
    request: Request,
    _: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get capabilities for an agent.

    Returns list of tools, segments readable/writable, and capabilities.
    """
    service = get_world_model_service(request)
    await service.initialize()

    result = await service.get_agent_capabilities(agent_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/infrastructure/status")
async def get_infrastructure_status(
    request: Request,
    _: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get status of all infrastructure components.

    Returns health status of Postgres, Redis, Neo4j, Caddy, etc.
    """
    service = get_world_model_service(request)
    await service.initialize()

    return await service.get_infrastructure_status()


@router.get("/approvals/summary")
async def get_approvals_summary(
    request: Request,
    _: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get summary of approval requirements.

    Returns tools that require Igor approval and their risk levels.
    """
    service = get_world_model_service(request)
    await service.initialize()

    return await service.get_approvals_summary()


@router.get("/integrations")
async def get_integrations(
    request: Request,
    _: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get list of external system integrations.

    Returns connection status of GitHub, Slack, Perplexity, etc.
    """
    service = get_world_model_service(request)
    await service.initialize()

    return await service.get_integrations()


@router.get("/context/{agent_id}")
async def get_world_model_context(
    agent_id: str,
    request: Request,
    _: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """
    Get world model context for agent prompts.

    Returns natural language context suitable for prepending to agent system prompts.
    """
    service = get_world_model_service(request)

    context = await service.get_world_model_context(agent_id)
    return {"context": context}


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
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "logging",
        "operations",
        "router",
    ],
    "keywords": [
        "agent",
        "approvals",
        "capabilities",
        "infrastructure",
        "integrations",
        "model",
        "routes",
        "service",
    ],
    "business_value": "Utility module for worldmodel",
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
