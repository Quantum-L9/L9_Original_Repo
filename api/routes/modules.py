"""
L9 Modules API Router
====================

Runtime visibility into which modules are wired and their status, backed by core.moduleregistry.ModuleRegistry.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Modules",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T01:42:58Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "modules",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /status"],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

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
        pass
    return registry.snapshot()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.decorators", "core.moduleregistry"],
    "tags": ["api", "api-gateway", "async", "auth", "endpoint", "operations", "router"],
    "keywords": ["moduleregistry", "modules", "router", "status"],
    "business_value": "Utility module for modules",
    "last_modified": "2026-01-17T23:47:56Z",
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
