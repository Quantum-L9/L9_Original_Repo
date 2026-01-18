# ============================================================================
__dora_meta__ = {
    "component_name": "Auth",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "auth",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.agent_routes",
            "api.dependencies",
            "api.memory.cache",
            "api.memory.graph",
            "api.memory.router",
            "api.routes.commands",
            "api.routes.cursor",
            "api.routes.modules",
            "api.routes.pattern",
            "api.routes.reasoning",
        ],
    },
}
# ============================================================================

import os
from fastapi import Header, HTTPException

EXECUTOR_API_KEY = os.environ.get("L9_EXECUTOR_API_KEY")


def verify_api_key(authorization: str = Header(None)):
    if not EXECUTOR_API_KEY:
        raise HTTPException(status_code=500, detail="Executor key not configured")
    expected = f"Bearer {EXECUTOR_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "api-gateway", "auth", "operations", "utility"],
    "keywords": ["api", "auth", "verify"],
    "business_value": "Utility module for auth",
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
