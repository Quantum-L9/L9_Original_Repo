"""
FastAPI application lifespan management with async DI container.

Implements the async context manager pattern for app startup/shutdown
coordination with the async DI container.

Supports both modern FastAPI (0.93+) lifespan and legacy on_event decorators.

References:
    - ADR-0033: Async Context Manager Pattern
    - ADR-0052: DI/DIP Foundation
    - FastAPI docs: https://fastapi.tiangolo.com/advanced/events/

Usage (Modern FastAPI 0.93+):
    from fastapi import FastAPI
    from core.fastapi_lifespan import lifespan

    app = FastAPI(lifespan=lifespan)

Usage (Legacy FastAPI < 0.93):
    from fastapi import FastAPI
    from core.fastapi_lifespan import startup_lifespan, shutdown_lifespan

    app = FastAPI()

    @app.on_event("startup")
    async def startup():
        await startup_lifespan()

    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_lifespan()
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Fastapi Lifespan",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:23:17Z",
    "updated_at": "2026-01-31T23:16:17Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "fastapi_lifespan",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.fastapi_lifespan"],
    },
}
# ============================================================================

# Re-export from di_async_config for cleaner imports
from config.di_async_config import (
    lifespan,
    shutdown_lifespan,
    startup_lifespan,
)

__all__ = [
    "lifespan",
    "shutdown_lifespan",
    "startup_lifespan",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-006",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "core",
        "endpoint",
        "event-driven",
        "foundation",
        "service",
    ],
    "keywords": [
        "async",
        "await",
        "container",
        "core",
        "fastapi",
        "legacy",
        "lifespan",
        "manager",
    ],
    "business_value": "Implements the async context manager pattern for app startup/shutdown coordination with the async DI container. Supports both modern FastAPI (0.93+) lifespan and legacy on_event decorators. ADR-0033: ",
    "last_modified": "2026-01-31T23:16:17Z",
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
