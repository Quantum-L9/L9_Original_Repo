"""
L9 Core - Auto Registry Framework
==================================

Generic, type-safe auto-discovery and registration system for L9 components.

This module provides the foundational `AutoRegistry` class that enables
automatic discovery and registration of components (routers, tools, agents,
orchestrators, etc.) without manual wiring.

Key Features:
- Type-safe generic registry with full type hints
- Decorator-based registration for clean, declarative code
- Auto-discovery via filesystem scanning
- Validation and health checks
- Observability with snapshots and metrics

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Auto Registry Framework",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-19T00:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "auto_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
__l9_trace__ = {
    "gmp_id": "GMP-95",
    "pr_id": "PR-17",
    "last_modified_by": "cursor",
}
# ============================================================================

import importlib
import inspect
import pkgutil
import structlog
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Exceptions
# =============================================================================


class RegistryError(Exception):
    """Base exception for registry errors."""

    pass


class DuplicateRegistrationError(RegistryError):
    """Raised when attempting to register a component with a duplicate ID."""

    pass


class ComponentNotFoundError(RegistryError):
    """Raised when a requested component is not found in the registry."""

    pass


class ValidationError(RegistryError):
    """Raised when a component fails validation."""

    pass


# =============================================================================
# Core AutoRegistry
# =============================================================================


class AutoRegistry(Generic[T]):
    """
    Generic auto-discovery and registration system for L9 components.

    This class provides a type-safe, decorator-based registration system
    that eliminates manual wiring and enables automatic component discovery.

    Type Parameters:
        T: The type of component being registered (e.g., APIRouter, BaseAgent)

    Attributes:
        name: Human-readable name of the registry
        _components: Internal storage for registered components
        _metadata: Additional metadata for each component

    Example:
        # Create a registry for API routers
        router_registry = AutoRegistry[APIRouter]("api_routers")

        # Register a component
        @router_registry.register(name="users", priority=10)
        def create_users_router():
            router = APIRouter()
            # ... router setup ...
            return router

        # Discover all routers in a package
        router_registry.discover("api.routes")

        # Get all registered routers
        routers = router_registry.get_all()
    """

    def __init__(
        self,
        name: str,
        validator: Optional[Callable[[T], bool]] = None,
        allow_duplicates: bool = False,
    ) -> None:
        """
        Initialize the registry.

        Args:
            name: Human-readable name for this registry
            validator: Optional validation function for components
            allow_duplicates: Whether to allow duplicate registrations
        """
        self.name = name
        self._validator = validator
        self._allow_duplicates = allow_duplicates
        self._components: Dict[str, T] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._factories: Dict[str, Callable[[], T]] = {}

    def clear(self) -> None:
        """Clear all registered components, factories, and metadata."""
        self._components.clear()
        self._metadata.clear()
        self._factories.clear()
        logger.info("registry.cleared", registry_name=self.name)

    def register(
        self,
        name: Optional[str] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        **metadata: Any,
    ) -> Callable[[Union[T, Callable[[], T]]], Union[T, Callable[[], T]]]:
        """
        Decorator to register a component or factory function.

        Args:
            name: Component identifier (defaults to function/class name)
            priority: Registration priority (higher = loaded first)
            tags: Optional tags for categorization
            **metadata: Additional metadata to store

        Returns:
            Decorator function

        Raises:
            DuplicateRegistrationError: If component already registered
            ValidationError: If component fails validation

        Example:
            @router_registry.register(name="users", priority=10)
            def create_users_router():
                return APIRouter()
        """

        def decorator(
            component: Union[T, Callable[[], T]],
        ) -> Union[T, Callable[[], T]]:
            # Determine component name
            component_name = name
            if component_name is None:
                if callable(component):
                    component_name = component.__name__
                else:
                    component_name = component.__class__.__name__

            # Check for duplicates
            if not self._allow_duplicates and component_name in self._components:
                raise DuplicateRegistrationError(
                    f"Component '{component_name}' already registered in {self.name}"
                )

            # Determine if this is a factory or instance
            if callable(component) and not inspect.isclass(component):
                # It's a factory function
                self._factories[component_name] = component
                logger.debug(
                    "registry.factory_registered",
                    registry=self.name,
                    component=component_name,
                    priority=priority,
                )
            else:
                # It's an instance or class
                if self._validator and not self._validator(component):
                    raise ValidationError(
                        f"Component '{component_name}' failed validation"
                    )

                self._components[component_name] = component
                logger.debug(
                    "registry.component_registered",
                    registry=self.name,
                    component=component_name,
                    priority=priority,
                )

            # Store metadata
            self._metadata[component_name] = {
                "name": component_name,
                "priority": priority,
                "tags": tags or [],
                **metadata,
            }

            return component

        return decorator

    def register_instance(
        self,
        component_id: str,
        component: T,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        **metadata: Any,
    ) -> None:
        """
        Programmatically register a component instance.

        Args:
            component_id: Unique identifier for the component
            component: The component instance to register
            priority: Registration priority
            tags: Optional tags for categorization
            **metadata: Additional metadata

        Raises:
            DuplicateRegistrationError: If component already registered
            ValidationError: If component fails validation
        """
        if not self._allow_duplicates and component_id in self._components:
            raise DuplicateRegistrationError(
                f"Component '{component_id}' already registered in {self.name}"
            )

        if self._validator and not self._validator(component):
            raise ValidationError(f"Component '{component_id}' failed validation")

        self._components[component_id] = component
        self._metadata[component_id] = {
            "name": component_id,
            "priority": priority,
            "tags": tags or [],
            **metadata,
        }

        logger.info(
            "registry.instance_registered",
            registry=self.name,
            component=component_id,
            priority=priority,
        )

    def discover(
        self,
        package_name: str,
        pattern: Optional[str] = None,
        recursive: bool = True,
    ) -> int:
        """
        Automatically discover and import modules in a package.

        This method scans a package for modules matching a pattern and
        imports them, triggering any decorator-based registrations.

        Args:
            package_name: Python package to scan (e.g., "api.routes")
            pattern: Optional filename pattern (e.g., "*_router.py")
            recursive: Whether to scan subdirectories

        Returns:
            Number of modules discovered and imported

        Example:
            # Discover all routers in api.routes
            count = router_registry.discover("api.routes")
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            logger.warning(
                "registry.discover_failed",
                registry=self.name,
                package=package_name,
                error=str(e),
            )
            return 0

        discovered_count = 0

        if hasattr(package, "__path__"):
            # It's a package, scan for modules
            for _, module_name, is_pkg in pkgutil.walk_packages(
                package.__path__, prefix=f"{package_name}."
            ):
                # Skip __pycache__ and private modules
                if "__pycache__" in module_name or module_name.split(".")[
                    -1
                ].startswith("_"):
                    continue

                # Apply pattern filter if provided
                if pattern and not self._matches_pattern(module_name, pattern):
                    continue

                # Skip subpackages if not recursive
                if not recursive and is_pkg:
                    continue

                try:
                    importlib.import_module(module_name)
                    discovered_count += 1
                    logger.debug(
                        "registry.module_discovered",
                        registry=self.name,
                        module=module_name,
                    )
                except Exception as e:
                    logger.warning(
                        "registry.module_import_failed",
                        registry=self.name,
                        module=module_name,
                        error=str(e),
                    )

        logger.info(
            "registry.discovery_complete",
            registry=self.name,
            package=package_name,
            discovered=discovered_count,
            registered=len(self._components),
        )

        return discovered_count

    def initialize_factories(self) -> int:
        """
        Initialize all registered factory functions.

        This method calls all factory functions and registers their
        returned components.

        Returns:
            Number of components initialized from factories

        Example:
            # After discovery, initialize all factories
            router_registry.initialize_factories()
        """
        initialized_count = 0

        for factory_name, factory_func in list(self._factories.items()):
            try:
                component = factory_func()

                if self._validator and not self._validator(component):
                    raise ValidationError(
                        f"Factory '{factory_name}' produced invalid component"
                    )

                self._components[factory_name] = component
                initialized_count += 1

                logger.debug(
                    "registry.factory_initialized",
                    registry=self.name,
                    factory=factory_name,
                )
            except Exception as e:
                logger.error(
                    "registry.factory_failed",
                    registry=self.name,
                    factory=factory_name,
                    error=str(e),
                )

        logger.info(
            "registry.factories_initialized",
            registry=self.name,
            count=initialized_count,
        )

        return initialized_count

    def get(self, component_id: str) -> Optional[T]:
        """
        Get a registered component by ID.

        Args:
            component_id: Component identifier

        Returns:
            The component, or None if not found
        """
        return self._components.get(component_id)

    def get_all(self, tags: Optional[List[str]] = None) -> List[T]:
        """
        Get all registered components, optionally filtered by tags.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of components sorted by priority (highest first)
        """
        components = []

        for component_id, component in self._components.items():
            metadata = self._metadata.get(component_id, {})

            # Filter by tags if provided
            if tags:
                component_tags = set(metadata.get("tags", []))
                if not component_tags.intersection(tags):
                    continue

            components.append((metadata.get("priority", 0), component))

        # Sort by priority (highest first)
        components.sort(key=lambda x: x[0], reverse=True)

        return [comp for _, comp in components]

    def get_metadata(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a registered component."""
        return self._metadata.get(component_id)

    def list_ids(self) -> List[str]:
        """Get list of all registered component IDs."""
        return list(self._components.keys())

    def count(self) -> int:
        """Get the number of registered components."""
        return len(self._components)

    def snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of the registry state for observability.

        Returns:
            Dictionary containing registry statistics and component list
        """
        return {
            "registry_name": self.name,
            "component_count": len(self._components),
            "factory_count": len(self._factories),
            "components": [
                {
                    "id": comp_id,
                    **self._metadata.get(comp_id, {}),
                }
                for comp_id in self._components.keys()
            ],
        }

    def _matches_pattern(self, module_name: str, pattern: str) -> bool:
        """Check if a module name matches a pattern."""
        # Simple pattern matching (can be enhanced with fnmatch if needed)
        return pattern in module_name


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
