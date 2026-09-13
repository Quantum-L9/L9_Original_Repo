"""
Health check module for symbolic computation.

Provides HTTP endpoint for health monitoring in production.
"""


import asyncio
from typing import Any

import structlog
from symbolic_computation import SymbolicComputation

logger = structlog.get_logger(__name__)


async def perform_health_check() -> dict[str, Any]:
    """
    Perform comprehensive health check.

    Returns:
        Health status dictionary
    """
    engine = SymbolicComputation()

    try:
        # Test basic computation
        result = await engine.compute("x + 1", {"x": 1.0}, backend="numpy")

        # Get metrics
        health = await engine.health_check()

        return {
            "status": "healthy" if result.success else "degraded",
            "details": health,
            "timestamp": str(asyncio.get_event_loop().time()),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(asyncio.get_event_loop().time()),
        }


if __name__ == "__main__":
    result = asyncio.run(perform_health_check())
    logger.info(result)

    # Exit with appropriate code
    exit(0 if result["status"] == "healthy" else 1)

# Runtime execution trace - updated automatically on every execution
