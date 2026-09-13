"""
L9 Modules API Router
====================

Runtime visibility into which modules are wired and their status, backed by core.moduleregistry.ModuleRegistry.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verify_api_key
from core.decorators import must_stay_async

router = APIRouter(prefix="/modules", tags=["modules"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/modules"
    tags=["modules"],
    module_id="modules",
    display_name="Module Registry",
    dependencies=["module_registry"],
)


def _get_module_registry(request: Request):
    """
    Gets the module registry from the request context, providing runtime visibility into wired modules and their status.

    Args:
        request: The incoming HTTP request containing application state.

    Returns:
        The module registry object used for module management.

    Raises:
        HTTPException: If the module registry is not initialized in the application state.
    """
    registry = getattr(request.app.state, "module_registry", None)
    if registry is None:
        """
        Performs asynchronous retrieval of module statuses from the core registry, providing runtime visibility into module wiring and health.

        Args:
            request: FastAPI request object for context and dependency injection.
            _: bool: Dependency-injected API key verification result.

        Returns:
            Module status information indicating current wiring and operational state.

        Raises:
            ImportError: If core.moduleregistry or ModuleStatus cannot be imported.
        """
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
    """
    Gets the current status of all modules in the ModuleRegistry for runtime visibility.

    Args:
        request: FastAPI Request object for context and dependency injection.
        _: bool: Dependency-injected flag for API key verification.

    Returns:
        A list or dict representing the status of each module, suitable for monitoring or debugging.
    """
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
                notes=(
                    None
                    if slack_validator is not None
                    else "Slack adapter not initialized"
                ),
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
                notes=(
                    None
                    if research_swarm_orchestrator is not None
                    else "ResearchSwarm orchestrator not initialized"
                ),
            )
        )

        world_model_runtime = getattr(request.app.state, "world_model_runtime", None)
        registry.set_status(
            ModuleStatus(
                module_id="world_model",
                enabled=world_model_runtime is not None,
                available=world_model_runtime is not None,
                initialized=world_model_runtime is not None,
                notes=(
                    None
                    if world_model_runtime is not None
                    else "World model runtime not initialized"
                ),
            )
        )
    except Exception:
        logger.debug("modules.world_model_status_failed")
    return registry.snapshot()


# Runtime execution trace - updated automatically on every execution
