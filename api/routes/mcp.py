"""
MCP (Model Context Protocol) Router for L9 API

Integrates MCP memory endpoints into unified l9-api.
Routes /mcp/* requests to MCP tool handlers.

GMP-68: Governance context is established from caller identity before tool calls.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Mcp",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T20:17:23Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "mcp",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /mcp/tools", "POST /mcp/call", "GET /mcp/health"],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

logger = structlog.get_logger(__name__)

router = APIRouter()

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/mcp",
    tags=["mcp"],
    display_name="MCP Memory",
)

# Try to import MCP components
_has_mcp = False
_verify_api_key_dep = None
_CallerIdentity = None

try:
    import sys
    from pathlib import Path

    # Add mcp_memory to path if needed
    mcp_path = Path(__file__).parent.parent.parent / "mcp_memory"
    if str(mcp_path) not in sys.path:
        sys.path.insert(0, str(mcp_path))

    from src.main import CallerIdentity, verify_api_key
    from src.mcp_server import MCPToolCall, get_mcp_tools, handle_tool_call
    from src.routes import health as mcp_health

    _has_mcp = True
    _verify_api_key_dep = verify_api_key
    _CallerIdentity = CallerIdentity
except ImportError as e:
    logger.warning(f"MCP memory components not available: {e}")

# Import governance context for memory operations
try:
    from config.rls_config import get_rls_config
    from memory.governance_gate import (build_governance_context,
                                        governance_context)

    _has_governance = True
except ImportError as e:
    logger.warning(f"Governance gate not available: {e}")
    _has_governance = False
    _has_mcp = False


def get_verify_api_key():
    """Get verify_api_key dependency or raise if not available."""
    if not _has_mcp or not _verify_api_key_dep:
        raise HTTPException(status_code=503, detail="MCP memory server not available")
    return _verify_api_key_dep


@router.get("/mcp/tools")
async def list_tools(request: Request, authorization: str = Header(None)):
    """List available MCP tools."""
    if not _has_mcp:
        raise HTTPException(status_code=503, detail="MCP memory server not available")

    # Verify API key
    caller = await _verify_api_key_dep(request, authorization)

    return {"tools": get_mcp_tools(), "caller": caller.caller_id}


@router.post("/mcp/call")
async def call_tool(request: Request, authorization: str = Header(None)):
    """Execute MCP tool with caller-enforced governance.

    Caller identity (L or C) determines:
    - user_id: Shared L_CTO_USER_ID (L and C collaborate in same space)
    - metadata.creator: "L-CTO" or "Cursor-IDE" (enforced server-side)
    - metadata.source: "l9-kernel" or "cursor-ide" (enforced server-side)
    - write/delete scope: C can only modify own memories (creator="Cursor-IDE")
    """
    if not _has_mcp:
        raise HTTPException(status_code=503, detail="MCP memory server not available")

    # Verify API key
    caller = await _verify_api_key_dep(request, authorization)

    try:
        payload = await request.json()
        tool_name = payload.get("tool_name")
        tool_args = payload.get("arguments", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")

        # Use shared user_id from caller identity (not payload)
        # This enforces L + C operate in same semantic space
        user_id = caller.user_id
        tool_call = MCPToolCall(name=tool_name, arguments=tool_args)

        # Get substrate service - prefer app.state (initialized in lifespan)
        # GMP-89/90: substrate_service is REQUIRED for MCP memory operations
        substrate_service = None

        # Primary: app.state (set during server startup)
        if hasattr(request.app.state, "substrate_service"):
            substrate_service = request.app.state.substrate_service
        elif hasattr(request.app.state, "memory_substrate_service"):
            substrate_service = request.app.state.memory_substrate_service

        # Fallback: singleton (if app.state not set)
        if substrate_service is None:
            try:
                from memory.substrate_service import get_service

                substrate_service = await get_service()
            except (ImportError, RuntimeError) as e:
                logger.warning(f"substrate_service singleton not available: {e}")

        # Log status for debugging
        if substrate_service is None:
            logger.error(
                "MCP call: substrate_service unavailable",
                tool_name=tool_name,
                app_state_keys=(
                    list(vars(request.app.state).keys())
                    if hasattr(request.app, "state")
                    else []
                ),
            )
        else:
            logger.debug(
                f"MCP call: using substrate_service={type(substrate_service).__name__}"
            )

        # GMP-68: Build governance context from caller identity
        # This MUST be set before any memory operations
        if _has_governance:
            # Determine allowed scopes based on caller
            # L can access all scopes, Cursor cannot access l-private
            if caller.caller_id == "L":
                allowed_scopes = ["developer", "global", "l-private"]
            else:
                allowed_scopes = ["developer", "global"]

            # Get scope from tool args or default to developer
            requested_scope = tool_args.get("scope", "developer")
            if requested_scope not in allowed_scopes:
                requested_scope = "developer"

            # Get RLS config for tenant/org/user UUIDs
            rls_config = get_rls_config()

            gov_ctx = build_governance_context(
                caller_id=caller.caller_id,
                role="admin" if caller.caller_id == "L" else "developer",
                scope=requested_scope,
                project_id="l9",
                allowed_scopes=allowed_scopes,
                tenant_id=rls_config.tenant_uuid,
                org_id=rls_config.org_uuid,
                user_id=rls_config.user_uuid,
                creator=caller.creator,
                source=caller.source,
            )

            async with governance_context(gov_ctx):
                result = await handle_tool_call(
                    tool_call, user_id, caller, substrate_service
                )
        else:
            # Governance not available - call without context (will fail on VPS)
            logger.warning("Governance gate not available - MCP call may fail")
            result = await handle_tool_call(
                tool_call, user_id, caller, substrate_service
            )

        return {"status": "success", "result": result, "caller": caller.caller_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        logger.exception("Tool call error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/health")
async def mcp_health_check():
    """MCP-specific health check."""
    if not _has_mcp:
        raise HTTPException(status_code=503, detail="MCP memory server not available")

    return await mcp_health.health_check()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.governance_gate", "memory.substrate_service"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "debugging",
        "endpoint",
        "filesystem",
        "logging",
        "operations",
        "router",
    ],
    "keywords": [
        "api",
        "check",
        "governance",
        "health",
        "mcp",
        "memory",
        "router",
        "tool",
    ],
    "business_value": "Utility module for mcp",
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
