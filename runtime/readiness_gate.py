from __future__ import annotations

"""
L9 Runtime Readiness Gate
=========================
Deterministic assertion that all mandatory subsystems are initialized.

Called before yield in api/server.py lifespan to prevent degraded startup.

Usage:
    from runtime.readiness_gate import assert_runtime_ready
    assert_runtime_ready(app)  # raises RuntimeError if any subsystem is None

ADR: No noqa suppressions.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "ReadinessGate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T18:00:00Z",
    "updated_at": "2026-02-16T18:00:00Z",
    "layer": "runtime",
    "domain": "observability",
    "module_name": "readiness_gate",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any

# Mandatory subsystems that MUST be non-None at startup.
# Each key is the app.state attribute name.
MANDATORY_SUBSYSTEMS = [
    "substrate_service",     # Postgres memory substrate
    "neo4j_client",          # Neo4j graph database
    "governance",            # GovernanceIntegration
    "governance_engine",     # GovernanceEngineService
    "agent_executor",        # AgentExecutorService
    "redis_client",          # Redis cache/session store
]


def assert_runtime_ready(app: Any) -> None:
    """
    Assert that all mandatory subsystems are initialized and non-None.

    Checks:
    1. All MANDATORY_SUBSYSTEMS are present and non-None in app.state.
    2. Tool registry has >0 registered executors.

    Args:
        app: The FastAPI application instance.

    Raises:
        RuntimeError: With a precise list of missing subsystems if any are None.
    """
    missing = []
    for name in MANDATORY_SUBSYSTEMS:
        value = getattr(app.state, name, None)
        if value is None:
            missing.append(name)

    if missing:
        raise RuntimeError(
            f"P0 Readiness Gate FAILED: the following mandatory subsystems are None: "
            f"{', '.join(missing)}. L9 cannot start in degraded mode."
        )

    # Verify tool registry has >0 executors
    try:
        from runtime.tool_registry import get_tool_snapshot

        snap = get_tool_snapshot()
        if snap["component_count"] == 0:
            raise RuntimeError(
                "P0 Readiness Gate FAILED: tool registry has 0 executors. "
                "L9 cannot start without tools."
            )
    except ImportError as e:
        raise RuntimeError(
            f"P0 Readiness Gate FAILED: cannot import tool_registry: {e}"
        ) from e
