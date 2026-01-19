"""
L9 API - Router Auto-Registration System
=========================================

Automatic discovery and registration of FastAPI routers.

This module eliminates manual router imports and `app.include_router()` calls
by providing a decorator-based registration system that automatically discovers
and wires all API routers.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Router Auto-Registration",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "api",
    "domain": "routing",
    "module_name": "router_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import structlog
from fastapi import APIRouter, FastAPI
from typing import Optional

from core.auto_registry import AutoRegistry
from core.moduleregistry import ModuleDefinition, ModuleRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Router Registry
# =============================================================================


def _validate_router(router: APIRouter) -> bool:
    """Validate that an object is a FastAPI router."""
    return isinstance(router, APIRouter)


# Global router registry
router_registry = AutoRegistry[APIRouter](
    name="api_routers", validator=_validate_router, allow_duplicates=False
)


def register_router(
    prefix: str,
    name: Optional[str] = None,
    tags: Optional[list[str]] = None,
    priority: int = 0,
    module_display_name: Optional[str] = None,
):
    """
    Decorator to register a FastAPI router for auto-wiring.

    This decorator marks a router or router factory function for automatic
    discovery and registration with the FastAPI application.

    Args:
        prefix: URL prefix for the router (e.g., "/api/v1/users")
        name: Router identifier (defaults to function/variable name)
        tags: OpenAPI tags for the router
        priority: Loading priority (higher = loaded first)
        module_display_name: Human-readable module name for ModuleRegistry

    Example:
        @register_router(prefix="/api/v1/users", tags=["users"])
        def create_users_router():
            router = APIRouter()
            # ... define routes ...
            return router

        # Or with an existing router
        router = APIRouter()
        # ... define routes ...
        register_router(prefix="/api/v1/users")(router)
    """
    return router_registry.register(
        name=name,
        priority=priority,
        tags=tags or [],
        prefix=prefix,
        module_display_name=module_display_name,
    )


def discover_routers(package: str = "api.routes") -> int:
    """
    Automatically discover all routers in the specified package.

    Args:
        package: Python package to scan for routers

    Returns:
        Number of modules discovered
    """
    logger.info("router_registry.discovering", package=package)
    count = router_registry.discover(package, recursive=True)
    logger.info("router_registry.discovered", package=package, count=count)
    return count


def wire_routers(app: FastAPI, module_registry: Optional[ModuleRegistry] = None) -> int:
    """
    Wire all registered routers to the FastAPI application.

    This function takes all discovered routers and includes them in the
    FastAPI app, optionally registering them with the ModuleRegistry.

    Args:
        app: FastAPI application instance
        module_registry: Optional ModuleRegistry for tracking modules

    Returns:
        Number of routers wired

    Example:
        app = FastAPI()
        discover_routers()
        wire_routers(app, module_registry)
    """
    # Initialize any factory functions
    router_registry.initialize_factories()

    # Get all routers sorted by priority
    routers = router_registry.get_all()

    wired_count = 0
    for router in routers:
        # Get router metadata
        router_id = None
        for rid in router_registry.list_ids():
            if router_registry.get(rid) == router:
                router_id = rid
                break

        if router_id is None:
            logger.warning("router_registry.no_id", router=router)
            continue

        metadata = router_registry.get_metadata(router_id)
        if metadata is None:
            logger.warning("router_registry.no_metadata", router_id=router_id)
            continue

        prefix = metadata.get("prefix", "")
        tags = metadata.get("tags", [])
        module_display_name = metadata.get("module_display_name")

        # Include router in app
        try:
            app.include_router(router, prefix=prefix, tags=tags)
            wired_count += 1

            logger.info(
                "router_registry.wired",
                router_id=router_id,
                prefix=prefix,
                tags=tags,
            )

            # Register with ModuleRegistry if provided
            if module_registry and module_display_name:
                module_registry.register(
                    ModuleDefinition(
                        module_id=router_id,
                        display_name=module_display_name,
                        route_prefix=prefix,
                    )
                )

        except Exception as e:
            logger.error(
                "router_registry.wire_failed",
                router_id=router_id,
                prefix=prefix,
                error=str(e),
            )

    logger.info("router_registry.wiring_complete", count=wired_count)
    return wired_count


def get_router_snapshot() -> dict:
    """Get a snapshot of all registered routers for observability."""
    return router_registry.snapshot()


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-ROUT-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
