"""
L9 API Routes - Example Auto-Wired Router
==========================================

This is a demonstration router using the new auto-registration system.
It shows how routers can be automatically discovered and wired without
manual imports or app.include_router() calls.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Example Auto-Wired Router",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "api",
    "domain": "routes",
    "module_name": "example_autowired",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["/api/v1/autowired/health"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from api.router_registry import register_router

logger = structlog.get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str
    autowired: bool


class EchoRequest(BaseModel):
    """Echo request."""

    message: str


class EchoResponse(BaseModel):
    """Echo response."""

    echo: str
    autowired: bool


# =============================================================================
# Router Factory
# =============================================================================


@register_router(
    prefix="/api/v1/autowired",
    name="example_autowired",
    tags=["example", "autowired"],
    priority=10,
    module_display_name="Example Auto-Wired Module",
)
def create_example_router() -> APIRouter:
    """
    Create and configure the example auto-wired router.

    This router is automatically discovered and registered by the
    auto-wiring system. No manual import or app.include_router() needed!

    Returns:
        Configured APIRouter instance
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """
        Health check endpoint for the auto-wired module.

        Returns:
            Health status
        """
        logger.info("example_autowired.health_check")
        return HealthResponse(
            status="healthy",
            message="Auto-wired router is working!",
            autowired=True,
        )

    @router.post("/echo", response_model=EchoResponse)
    async def echo(request: EchoRequest) -> EchoResponse:
        """
        Echo endpoint that returns the input message.

        Args:
            request: Echo request with message

        Returns:
            Echo response
        """
        logger.info("example_autowired.echo", message=request.message)
        return EchoResponse(echo=request.message, autowired=True)

    @router.get("/info")
    async def info() -> dict:
        """
        Information about this auto-wired router.

        Returns:
            Router metadata
        """
        return {
            "name": "Example Auto-Wired Router",
            "version": "1.0.0",
            "autowired": True,
            "description": "Demonstrates the L9 auto-registration system",
            "endpoints": ["/health", "/echo", "/info"],
        }

    return router


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-ROUT-EXAMPLE",
    "governance_level": "standard",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
