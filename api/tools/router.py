"""
L9 Tools API Router
Version: 2.0.0

Tool execution endpoints using ExecutorToolRegistry.
All tool calls are validated, safety-checked, and logged.

DEPRECATED: ActionToolOrchestrator (v1.x) removed in v2.0.
Using ExecutorToolRegistry for governance-aware dispatch.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Router",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-26T17:26:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "router",
    "type": "router",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": ["POST /test", "POST /execute", "GET /health"],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": ["api.server", "api.tools.__init__"],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from api.routes.registry import router_registry
from core.decorators import must_stay_async
from core.tools.registry_adapter import ExecutorToolRegistry

logger = structlog.get_logger(__name__)

router = APIRouter()

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="/tools",
    tags=["tools"],
    module_id="tools_api",
    display_name="Tools API",
    dependencies=["tool_registry"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ToolExecuteRequest(BaseModel):
    """Request model for tool execution."""

    tool_id: str = Field(..., description="Canonical tool identity")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    max_retries: int = Field(default=3, description="Max retry attempts")
    require_approval: bool = Field(default=False, description="Require human approval")


class ToolExecuteResponse(BaseModel):
    """Response model for tool execution."""

    success: bool = Field(..., description="Whether operation succeeded")
    result: dict[str, Any] | None = Field(
        default=None, description="Tool execution result"
    )
    safety_level: str = Field(default="safe", description="Safety assessment")
    retries_used: int = Field(default=0, description="Number of retries used")
    message: str = Field(default="", description="Result message")


# ============================================================================
# Dependency: Get ExecutorToolRegistry from app.state
# ============================================================================


def get_tool_registry(request: Request) -> ExecutorToolRegistry:
    """
    Get ExecutorToolRegistry from app.state.

    DEPRECATED: ActionToolOrchestrator (v1.x) removed in v2.0.
    Using ExecutorToolRegistry for governance-aware dispatch.
    """
    registry = getattr(request.app.state, "tool_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="Tool registry not initialized. Check server logs.",
        )
    return registry


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/test")
@must_stay_async("FastAPI/ASGI route handler")
async def tools_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify tools router is reachable."""
    return {"ok": True, "msg": "tools endpoint reachable"}


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    http_request: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    registry: ExecutorToolRegistry = Depends(get_tool_registry),
):
    """
    Execute a tool via ExecutorToolRegistry.

    DEPRECATED: ActionToolOrchestrator (v1.x) removed in v2.0.
    Using ExecutorToolRegistry for governance-aware dispatch.

    The registry handles:
    - Tool validation via Pydantic schemas
    - Governance policy checks
    - Execution with timeout
    - Packet logging to memory substrate
    """
    try:
        logger.info(
            "Tool execution request",
            tool_id=request.tool_id,
            require_approval=request.require_approval,
        )

        # Build execution context
        context = {
            "principal_id": "api",
            "agent_id": "api-tools-router",
            "require_approval": request.require_approval,
        }

        # Execute via registry dispatch
        result = await registry.dispatch_tool_call(
            tool_id=request.tool_id,
            arguments=request.arguments,
            context=context,
        )

        logger.info(
            "Tool execution complete",
            tool_id=request.tool_id,
            success=result.success,
            duration_ms=result.duration_ms,
        )

        return ToolExecuteResponse(
            success=result.success,
            result=result.result if result.success else None,
            safety_level="safe",  # Registry handles governance checks
            retries_used=0,  # Registry doesn't track retries
            message=result.error if not result.success else "OK",
        )
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Tool execution failed: {e!s}"
        ) from e


@router.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def tool_graph_health(request: Request) -> dict:
    """
    Check tool graph health status.

    Returns:
        {
            "status": "healthy" | "degraded",
            "neo4j_available": true | false,
            "impact": null | "No blast radius/dependency queries",
            "tools_executable": true,
            "timestamp": "2026-01-04T..."
        }
    """
    is_healthy = getattr(request.app.state, "tool_graph_healthy", False)
    return {
        "status": "healthy" if is_healthy else "degraded",
        "neo4j_available": is_healthy,
        "impact": None if is_healthy else "No blast radius/dependency queries",
        "tools_executable": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-010",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.decorators", "core.tools.registry_adapter"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
        "router",
    ],
    "keywords": [
        "execute",
        "executortoolregistry",
        "governance",
        "graph",
        "health",
        "registry",
        "router",
        "test",
    ],
    "business_value": "Provides router components including ToolExecuteRequest, ToolExecuteResponse",
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
