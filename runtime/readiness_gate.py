"""P0 readiness helper used by api.server lifespan."""

from __future__ import annotations

from typing import Any


def assert_runtime_ready(app: Any) -> None:
    """Fail-closed if required app.state handles were never attached."""
    required = (
        "substrate_service",
        "neo4j_client",
        "governance",
        "agent_executor",
    )
    missing = [name for name in required if not getattr(app.state, name, None)]
    if missing:
        raise RuntimeError(
            "P0 Readiness Gate FAILED: missing app.state handles: "
            + ", ".join(missing)
        )
