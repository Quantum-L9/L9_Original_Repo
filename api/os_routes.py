"""
L9 OS Routes
Basic health and system status endpoints.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Os Routes",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "os_routes",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /health", "GET /status"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server", "tests.smoke_test", "tests.smoke_test_root"],
    },
}
# ============================================================================

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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["api", "api-gateway", "async", "endpoint", "operations", "router"],
    "keywords": ["health", "routes", "status"],
    "business_value": "Utility module for os routes",
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
