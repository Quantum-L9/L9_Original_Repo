"""
L9 API Router Auto-Registry
===========================

Auto-discovery and registration for FastAPI routers.

Version: 1.0.0
Created: 2026-01-18
Author: L9 Auto-Wiring System
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Router Registry",
    "module_version": "1.0.0",
    "created_by": "L9_Auto_Wiring_System",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "registry",
    "type": "registry",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server", "api.routes.*"],
    },
}
# ============================================================================

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI

logger = structlog.get_logger(__name__)


@dataclass
class RouterDefinition:
    """Definition for an auto-registered router."""

    router: APIRouter
    prefix: str
    tags: list[str]
    module_id: str
    display_name: str
    dependencies: list[str] = None

    def __post_init__(self) -> None:
        """
        Initializes the RouterDefinition by ensuring dependencies list is set.
        Args:
            self: Instance of RouterDefinition being initialized.
        Returns:
            None.
        Raises:
            None.
        """
        if self.dependencies is None:
            self.dependencies = []


class RouterRegistry:
    """
    Auto-registry for FastAPI routers.

    Eliminates manual router registration in api/server.py.
    Routers self-register at import time using this registry.

    Usage in router file (e.g., api/routes/reasoning.py):

        from api.routes.registry import router_registry

        router = APIRouter()

        # Auto-register at module import
        router_registry.register(
            router=router,
            prefix="/reasoning",
            tags=["reasoning"],
            display_name="Reasoning Orchestrator"
        )

        # ... define routes ...

    Then in api/server.py:

        from api.routes.registry import router_registry, discover_routers

        # Discover all routers
        discover_routers()

        # Wire all routers to app
        router_count = router_registry.wire_all(app)

    Benefits:
        - Zero boilerplate in server.py
        - Routers self-describe their configuration
        - Automatic module registry integration
        - Fail-safe error handling
        - Observability via snapshot()
    """

    def __init__(self) -> None:
        """Initializes the RouterRegistry for auto-discovering and managing FastAPI routers within the L9 API system."""
        self._routers: dict[str, RouterDefinition] = {}
        self._wired: dict[str, bool] = {}
        logger.info("RouterRegistry initialized")

    def register(
        self,
        router: APIRouter,
        prefix: str,
        tags: list[str] | None = None,
        module_id: str | None = None,
        display_name: str | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """
        Register a router for auto-wiring.

        Args:
            router: FastAPI router instance
            prefix: URL prefix (e.g., "/reasoning")
            tags: OpenAPI tags
            module_id: Unique module identifier (auto-generated if None)
            display_name: Human-readable name (auto-generated if None)
            dependencies: List of required app.state attributes

        Example:
            router_registry.register(
                router=router,
                prefix="/reasoning",
                tags=["reasoning"],
                display_name="Reasoning Orchestrator",
                dependencies=["reasoning_orchestrator"]
            )
        """
        # Auto-generate module_id from prefix
        if module_id is None:
            module_id = prefix.strip("/").replace("/", "_")

        # Auto-generate display_name from module_id
        if display_name is None:
            display_name = module_id.replace("_", " ").title()

        # Default tags
        if tags is None:
            tags = [module_id]

        definition = RouterDefinition(
            router=router,
            prefix=prefix,
            tags=tags,
            module_id=module_id,
            display_name=display_name,
            dependencies=dependencies or [],
        )

        self._routers[module_id] = definition
        self._wired[module_id] = False

        logger.info(
            f"Router registered: {display_name}",
            module_id=module_id,
            prefix=prefix,
            tags=tags,
        )

    def wire_all(self, app: FastAPI) -> int:
        """
        Wire all registered routers to the FastAPI app.

        Args:
            app: FastAPI application instance

        Returns:
            Count of successfully wired routers

        Features:
            - Dependency validation (checks app.state)
            - Module registry integration
            - Graceful error handling
            - Idempotent (safe to call multiple times)
        """
        count = 0
        errors = []

        for module_id, definition in sorted(self._routers.items()):
            # Skip if already wired
            if self._wired.get(module_id, False):
                logger.debug(f"Router already wired: {module_id}")
                continue

            try:
                # Validate dependencies
                missing_deps = []
                for dep in definition.dependencies:
                    if not hasattr(app.state, dep):
                        missing_deps.append(dep)

                if missing_deps:
                    logger.warning(
                        f"Router {module_id} has missing dependencies: {missing_deps}",
                        module_id=module_id,
                        missing=missing_deps,
                    )
                    errors.append(f"{module_id}: missing {missing_deps}")
                    continue

                # Wire router to app
                app.include_router(
                    definition.router, prefix=definition.prefix, tags=definition.tags
                )

                self._wired[module_id] = True
                count += 1

                logger.info(
                    f"Router wired: {definition.display_name}",
                    module_id=module_id,
                    prefix=definition.prefix,
                )

                # Also register in module_registry if available
                if hasattr(app.state, "module_registry"):
                    try:
                        from core.moduleregistry import ModuleDefinition

                        app.state.module_registry.register(
                            ModuleDefinition(
                                module_id=definition.module_id,
                                display_name=definition.display_name,
                                route_prefix=definition.prefix,
                            )
                        )
                        logger.debug(
                            f"Router registered in module_registry: {module_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to register router in module_registry: {module_id}",
                            error=str(e),
                        )

            except Exception as e:
                logger.error(
                    f"Failed to wire router: {module_id}", error=str(e), exc_info=True
                )
                errors.append(f"{module_id}: {e!s}")

        if errors:
            logger.warning(
                "Router wiring completed with errors",
                success_count=count,
                error_count=len(errors),
                errors=errors,
            )
        else:
            logger.info(f"✅ All routers wired successfully: {count} routers")

        return count

    def get_definition(self, module_id: str) -> RouterDefinition | None:
        """Get router definition by module ID."""
        return self._routers.get(module_id)

    def is_wired(self, module_id: str) -> bool:
        """Check if router has been wired."""
        return self._wired.get(module_id, False)

    def snapshot(self) -> dict:
        """
        Get JSON-serializable snapshot of registered routers.

        Returns:
            Dictionary with registry state
        """
        return {
            "count": len(self._routers),
            "wired_count": sum(self._wired.values()),
            "routers": [
                {
                    "module_id": defn.module_id,
                    "display_name": defn.display_name,
                    "prefix": defn.prefix,
                    "tags": defn.tags,
                    "dependencies": defn.dependencies,
                    "wired": self._wired.get(defn.module_id, False),
                }
                for defn in sorted(self._routers.values(), key=lambda d: d.module_id)
            ],
        }

    def __len__(self) -> int:
        """Get count of registered routers."""
        return len(self._routers)

    def __repr__(self) -> str:
        """String representation."""
        wired_count = sum(self._wired.values())
        return f"RouterRegistry(total={len(self)}, wired={wired_count})"


# Global router registry (singleton)
router_registry = RouterRegistry()


def discover_routers() -> int:
    """
    Auto-discover all routers in api/ subdirectories.

    Scans: api/routes/, api/memory/, api/tools/, api/adapters/, api/middleware/

    Convention: Each router file should call router_registry.register()
    at module level (outside any function).

    Returns:
        Count of discovered router modules

    Example:
        from api.routes.registry import discover_routers

        # This imports all router modules, triggering registration
        count = discover_routers()
        logger.info(f"Discovered {count} router modules")
    """
    import importlib
    import pkgutil

    # All api subdirectories to scan for routers
    api_packages = [
        "api.routes",
        "api.memory",
        "api.tools",
        "api.adapters",
        "api.middleware",
    ]

    # Modules to skip (not routers)
    skip_modules = {"registry", "__init__", "conftest"}

    count = 0
    for package_name in api_packages:
        try:
            package = importlib.import_module(package_name)
            if not hasattr(package, "__path__"):
                continue

            for _importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                # Skip non-router modules
                if ispkg or modname in skip_modules:
                    continue
                try:
                    # Import router module (triggers registration)
                    importlib.import_module(f"{package_name}.{modname}")
                    count += 1
                    logger.debug(f"Discovered router module: {package_name}.{modname}")
                except Exception as e:
                    logger.warning(
                        f"Failed to import router module: {package_name}.{modname}",
                        error=str(e),
                    )
        except ImportError:
            # Package doesn't exist, skip
            logger.debug(f"Package not found (skipping): {package_name}")
        except Exception as e:
            logger.error(f"Failed to scan package: {package_name}", error=str(e))

    logger.info(f"Router discovery complete: {count} modules imported")
    return count


def get_router_registry() -> RouterRegistry:
    """Get the global router registry."""
    return router_registry


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPS-ROUTER-REG-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["fastapi", "core.moduleregistry"],
    "tags": ["api", "registry", "auto-wiring", "routers"],
    "keywords": ["router", "fastapi", "auto-registration", "wiring", "discovery"],
    "business_value": "Eliminates 150+ lines of manual router registration boilerplate",
    "last_modified": "2026-01-18T00:00:00Z",
    "modified_by": "L9_Auto_Wiring_System",
    "change_summary": "Initial router auto-registry implementation",
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
