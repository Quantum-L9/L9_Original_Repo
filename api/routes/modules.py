"""
L9 Modules API Router
====================

Runtime visibility into which modules are wired and their status, backed by core.moduleregistry.ModuleRegistry.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verify_api_key
from core.decorators import must_stay_async

router = APIRouter(prefix="/modules", tags=["modules"])


def _get_module_registry(request: Request):
    registry = getattr(request.app.state, "module_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="ModuleRegistry not initialized. Check server logs.",
        )
    return registry


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def get_modules_status(
    request: Request,
    _: bool = Depends(verify_api_key),
):
    registry = _get_module_registry(request)
    try:
        from core.moduleregistry import ModuleStatus

        # Runtime-derived statuses (best-effort; never raises)
        substrate_service = getattr(request.app.state, "substrate_service", None)
        memory_ready = substrate_service is not None
        registry.set_status(
            ModuleStatus(
                module_id="memory",
                enabled=memory_ready,
                available=memory_ready,
                initialized=memory_ready,
                notes=None if memory_ready else "Memory service not initialized",
            )
        )

        tool_registry = getattr(request.app.state, "tool_registry", None)
        registry.set_status(
            ModuleStatus(
                module_id="tools",
                enabled=bool(tool_registry),
                available=bool(tool_registry),
                initialized=bool(tool_registry),
                notes=None if tool_registry else "Tool registry not initialized",
            )
        )

        slack_validator = getattr(request.app.state, "slack_validator", None)
        registry.set_status(
            ModuleStatus(
                module_id="slack",
                enabled=slack_validator is not None,
                available=slack_validator is not None,
                initialized=slack_validator is not None,
                notes=None
                if slack_validator is not None
                else "Slack adapter not initialized",
            )
        )

        research_swarm_orchestrator = getattr(
            request.app.state, "research_swarm_orchestrator", None
        )
        registry.set_status(
            ModuleStatus(
                module_id="research_swarm",
                enabled=research_swarm_orchestrator is not None,
                available=research_swarm_orchestrator is not None,
                initialized=research_swarm_orchestrator is not None,
                notes=None
                if research_swarm_orchestrator is not None
                else "ResearchSwarm orchestrator not initialized",
            )
        )

        world_model_runtime = getattr(request.app.state, "world_model_runtime", None)
        registry.set_status(
            ModuleStatus(
                module_id="world_model",
                enabled=world_model_runtime is not None,
                available=world_model_runtime is not None,
                initialized=world_model_runtime is not None,
                notes=None
                if world_model_runtime is not None
                else "World model runtime not initialized",
            )
        )
    except Exception:
        pass
    return registry.snapshot()
