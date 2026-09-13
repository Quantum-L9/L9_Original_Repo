"""
L9 OS Routes
Basic health and system status endpoints.
"""


from fastapi import APIRouter

from api.routes.registry import router_registry
from core.decorators import must_stay_async

router = APIRouter(tags=["os"])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="/os",
    tags=["os"],
    module_id="os_routes",
    display_name="OS Health & Status",
)


@router.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def os_health():
    """Health check for OS layer."""
    return {"status": "ok", "service": "os"}


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def os_status():
    """System status endpoint."""
    return {
        "status": "operational",
        "version": "1.1.0",
        "components": {
            "memory_substrate": "active",
            "orchestrators": "ready",
        },
    }


@router.get("/readiness")
@must_stay_async("FastAPI/ASGI route handler")
async def os_readiness():
    """
    Readiness probe endpoint.
    Returns 200 if bootstrap completed, 503 otherwise.
    Used by K8s readinessProbe.
    """
    from fastapi import HTTPException

    try:
        from api.startup_guard import ensure_bootstrap

        await ensure_bootstrap()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# Runtime execution trace - updated automatically on every execution
