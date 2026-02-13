"""
L9 Core - Singleton Service Auto-Registration System
=====================================================

Automatic discovery and registration of singleton services.

This module eliminates manual singleton registration by providing
a decorator-based system that allows services to self-register with
the singleton registry.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Singleton Auto-Registration",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "core",
    "domain": "infrastructure",
    "module_name": "singleton_auto_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.singleton_registry"],
    },
}
# ============================================================================

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar

import structlog

from core.auto_registry import AutoRegistry
from core.singleton_registry import SingletonLifecycle

logger = structlog.get_logger(__name__)

# Type variables for decorator type preservation
P = ParamSpec("P")
R = TypeVar("R")


# =============================================================================
# Singleton Service Configuration
# =============================================================================


@dataclass
class SingletonServiceConfig:
    """Configuration for a singleton service."""

    name: str
    module_path: str
    getter: Callable
    closer: Callable | None = None
    lifecycle: SingletonLifecycle = SingletonLifecycle.LAZY
    dependencies: list[str] = None
    description: str = ""
    category: str = "general"

    def __post_init__(self):
        """
        Performs post-initialization setup for SingletonServiceConfig, ensuring dependencies list is initialized.

        Args:
            self: Instance of SingletonServiceConfig to set up dependencies.
        """
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for registration."""
        return {
            "name": self.name,
            "module_path": self.module_path,
            "getter": self.getter,
            "closer": self.closer,
            "lifecycle": self.lifecycle,
            "dependencies": self.dependencies,
            "description": self.description,
        }


# =============================================================================
# Singleton Service Registry
# =============================================================================


def _validate_singleton_config(config: SingletonServiceConfig) -> bool:
    """Validate that an object is a valid singleton service config."""
    return (
        isinstance(config, SingletonServiceConfig)
        and bool(config.name)
        and bool(config.getter)
    )


# Global singleton service registry
singleton_service_registry = AutoRegistry[SingletonServiceConfig](
    name="singleton_services",
    validator=_validate_singleton_config,
    allow_duplicates=False,
)


def register_singleton_service(
    name: str,
    module_path: str,
    getter: Callable,
    closer: Callable | None = None,
    lifecycle: str | SingletonLifecycle = SingletonLifecycle.LAZY,
    dependencies: list[str] | None = None,
    description: str = "",
    category: str = "general",
    priority: int = 0,
) -> SingletonServiceConfig:
    """
    Register a singleton service programmatically.

    Args:
        name: Unique singleton name (e.g., "redis_client")
        module_path: Module path (e.g., "runtime.redis_client")
        getter: Function to get/create instance
        closer: Function to close/cleanup instance
        lifecycle: When singleton is initialized
        dependencies: List of singleton names this depends on
        description: Human-readable description
        category: Service category (e.g., "core", "memory", "clients")
        priority: Registration priority (higher = loaded first)

    Returns:
        SingletonServiceConfig instance

    Example:
        register_singleton_service(
            name="redis_client",
            module_path="runtime.redis_client",
            getter=get_redis_client,
            closer=close_redis_client,
            lifecycle=SingletonLifecycle.STARTUP,
            dependencies=[],
            description="Redis cache/queue client",
            category="core"
        )
    """
    # Convert string lifecycle to enum if needed
    if isinstance(lifecycle, str):
        lifecycle_enum = SingletonLifecycle(lifecycle)
    else:
        lifecycle_enum = lifecycle

    config = SingletonServiceConfig(
        name=name,
        module_path=module_path,
        getter=getter,
        closer=closer,
        lifecycle=lifecycle_enum,
        dependencies=dependencies or [],
        description=description,
        category=category,
    )

    singleton_service_registry.register_instance(
        component_id=name,
        component=config,
        priority=priority,
        tags=[category, lifecycle_enum.value],
    )

    logger.info("singleton_service_registry.registered", name=name, category=category)
    return config


def register_singleton(
    name: str | None = None,
    lifecycle: str | SingletonLifecycle = SingletonLifecycle.LAZY,
    dependencies: list[str] | None = None,
    description: str = "",
    category: str = "general",
    priority: int = 0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to register a singleton service getter function.

    This decorator marks a getter function for automatic singleton registration.
    The function name (or explicit name) becomes the singleton name.

    Args:
        name: Singleton name (defaults to function name without 'get_' prefix)
        lifecycle: When singleton is initialized
        dependencies: List of singleton names this depends on
        description: Human-readable description
        category: Service category
        priority: Registration priority

    Example:
        @register_singleton(
            lifecycle=SingletonLifecycle.STARTUP,
            dependencies=["redis_client"],
            description="Memory substrate repository",
            category="memory"
        )
        @must_stay_async("callers use await")
        async def get_memory_substrate_repository():
            # ... implementation ...
            return repository

        # Optionally pair with a closer
        @register_singleton_closer("memory_substrate_repository")
        @must_stay_async("callers use await")
        async def close_memory_substrate_repository():
            # ... cleanup ...
            pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """
        Performs automatic registration of singleton services by decorating functions within the singleton auto-registration system.

        Args:
            func: The service provider function to be registered as a singleton.

        Returns:
            A wrapped function that registers the service as a singleton upon invocation.
        """
        # Determine singleton name
        singleton_name = name
        if not singleton_name:
            # Strip 'get_' prefix if present
            func_name = func.__name__
            if func_name.startswith("get_"):
                singleton_name = func_name[4:]
            else:
                singleton_name = func_name

        # Determine module path
        module_path = func.__module__

        # Register the singleton
        register_singleton_service(
            name=singleton_name,
            module_path=module_path,
            getter=func,
            closer=None,  # Will be set via @register_singleton_closer
            lifecycle=lifecycle,
            dependencies=dependencies,
            description=description,
            category=category,
            priority=priority,
        )

        return func

    return decorator


def register_singleton_closer(
    singleton_name: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to register a closer function for a singleton.

    This decorator associates a closer function with an already-registered
    singleton service.

    Args:
        singleton_name: Name of the singleton to attach closer to

    Example:
        @register_singleton_closer("redis_client")
        @must_stay_async("callers use await")
        async def close_redis_client():
            # ... cleanup ...
            pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """
        Registers a singleton service cleanup function in the auto-registration system.
        Args:
            func: Callable cleanup function to be registered as the singleton's closer.
        Returns:
            Callable: The same function, registered for automatic cleanup.
        """
        # Find the singleton config
        config = singleton_service_registry.get(singleton_name)
        if config:
            config.closer = func
            logger.debug(
                "singleton_service_registry.closer_registered",
                singleton=singleton_name,
            )
        else:
            logger.warning(
                "singleton_service_registry.closer_orphaned",
                singleton=singleton_name,
                closer=func.__name__,
            )

        return func

    return decorator


def discover_singleton_services(package: str = "runtime") -> int:
    """
    Automatically discover all singleton services in the specified package.

    Args:
        package: Python package to scan for singleton services

    Returns:
        Number of modules discovered
    """
    logger.info("singleton_service_registry.discovering", package=package)
    count = singleton_service_registry.discover(package, recursive=True)
    logger.info("singleton_service_registry.discovered", package=package, count=count)
    return count


def get_all_singleton_services() -> dict[str, SingletonServiceConfig]:
    """
    Get all registered singleton service configurations.

    Returns:
        Dictionary mapping singleton names to configurations

    Example:
        services = get_all_singleton_services()
        for name, config in services.items():
            print(f"Singleton: {name}, Module: {config.module_path}")  # noqa: ADR-0019
    """
    singleton_service_registry.initialize_factories()

    services: dict[str, SingletonServiceConfig] = {}

    for service_id in singleton_service_registry.list_ids():
        config = singleton_service_registry.get(service_id)
        if config:
            services[service_id] = config

    logger.info("singleton_service_registry.services_retrieved", count=len(services))
    return services


def get_singleton_services_by_category(
    category: str,
) -> dict[str, SingletonServiceConfig]:
    """
    Get all singleton services in a specific category.

    Args:
        category: Category to filter by (e.g., "core", "memory", "clients")

    Returns:
        Dictionary mapping singleton names to configurations
    """
    singleton_service_registry.initialize_factories()

    configs = singleton_service_registry.get_all(tags=[category])
    services: dict[str, SingletonServiceConfig] = {}

    for config in configs:
        services[config.name] = config

    return services


def get_singleton_services_by_lifecycle(
    lifecycle: SingletonLifecycle,
) -> dict[str, SingletonServiceConfig]:
    """
    Get all singleton services with a specific lifecycle.

    Args:
        lifecycle: Lifecycle to filter by

    Returns:
        Dictionary mapping singleton names to configurations
    """
    singleton_service_registry.initialize_factories()

    configs = singleton_service_registry.get_all(tags=[lifecycle.value])
    services: dict[str, SingletonServiceConfig] = {}

    for config in configs:
        services[config.name] = config

    return services


def wire_singletons_to_registry(registry) -> int:
    """
    Wire all auto-registered singleton services to the main singleton registry.

    This function takes all singleton services registered via decorators
    and registers them with the main SingletonRegistry.

    Args:
        registry: The main SingletonRegistry instance

    Returns:
        Number of singletons wired

    Example:
        from core.singleton_registry import get_singleton_registry
        from core.singleton_auto_registry import wire_singletons_to_registry

        # Discover all singleton services
        discover_singleton_services("runtime")
        discover_singleton_services("memory")

        # Wire them to the main registry
        registry = get_singleton_registry()
        count = wire_singletons_to_registry(registry)
        print(f"Wired {count} singletons")  # noqa: ADR-0019
    """
    services = get_all_singleton_services()
    wired_count = 0

    for name, config in services.items():
        try:
            registry.register(
                name=config.name,
                module_path=config.module_path,
                getter=config.getter,
                closer=config.closer,
                lifecycle=config.lifecycle,
                dependencies=config.dependencies,
                description=config.description,
            )
            wired_count += 1
            logger.debug("singleton_service_registry.wired", name=name)
        except Exception as e:
            logger.error(
                "singleton_service_registry.wire_failed", name=name, error=str(e)
            )

    logger.info("singleton_service_registry.wiring_complete", count=wired_count)
    return wired_count


def get_singleton_service_snapshot() -> dict:
    """Get a snapshot of all registered singleton services for observability."""
    return singleton_service_registry.snapshot()


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-SING-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
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
