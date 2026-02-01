"""
L9 Startup Guard
Ensures bootstrap has completed before API startup.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Startup Guard",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T12:26:24Z",
    "updated_at": "2026-01-31T22:21:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "startup_guard",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": [
            "api.os_routes",
            "api.server",
            "tests.api.test_bootstrap_fail_fast",
        ],
    },
}
# ============================================================================

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BOOTSTRAP_KEY = "l9.bootstrap"


def _ensure_asyncpg_url(url: str) -> str:
    """
    Ensure DATABASE_URL uses asyncpg driver for SQLAlchemy.
    Converts postgresql:// to postgresql+asyncpg://
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def ensure_bootstrap() -> None:
    """
    Check that bootstrap has been completed.
    Raises RuntimeError if bootstrap artifact is missing.
    """
    db_url = _ensure_asyncpg_url(os.environ["DATABASE_URL"])
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM system_state WHERE key = :key"),
                {"key": BOOTSTRAP_KEY},
            )
            if not result.first():
                raise RuntimeError("Bootstrap not completed")
    finally:
        await engine.dispose()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-019",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "api-gateway", "async", "operations", "orm", "service"],
    "keywords": ["bootstrap", "ensure", "guard", "startup"],
    "business_value": "Utility module for startup guard",
    "last_modified": "2026-01-31T22:21:57Z",
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
