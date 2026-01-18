"""Health check endpoint."""

# ============================================================================
__dora_meta__ = {
    "component_name": "Health",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T13:38:48Z",
    "layer": "integration",
    "domain": "api_gateway",
    "module_name": "health",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /health"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from fastapi import APIRouter
from src import db  # Import module to access pool after init_db() updates it
from src.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    db_ok = db.pool is not None
    db_connected = False
    db_error = None
    if db_ok:
        try:
            async with db.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                db_connected = True
        except Exception as e:
            db_connected = False
            db_error = str(e)
    else:
        db_error = "Database pool not initialized"

    return {
        "status": "healthy" if db_connected else "unhealthy",
        "database": "connected" if db_connected else "disconnected",
        "database_error": db_error if db_error else None,
        "mcp_version": "2025-03-26",
        "index_type": settings.VECTOR_INDEX_TYPE,
        "compounding_enabled": settings.COMPOUNDING_ENABLED,
        "decay_enabled": settings.DECAY_ENABLED,
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "api-gateway", "async", "endpoint", "integration", "router"],
    "keywords": ["check", "health"],
    "business_value": "Utility module for health",
    "last_modified": "2026-01-14T13:38:48Z",
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
