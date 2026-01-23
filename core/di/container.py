"""
L9 Dependency Injection Container
==================================

Frontier-grade lightweight DI container for L9 following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready dependency injection framework.

Features:
- ✅ Constructor injection via type hints
- ✅ Singleton/transient lifecycle management
- ✅ Circular dependency detection
- ✅ Protocol-based resolution
- ✅ Thread-safe operations
- ✅ Comprehensive error reporting
- ✅ Zero external dependencies

Usage:
    from core.di.container import DIContainer
    from core.protocols import CacheClient

    container = DIContainer()
    container.bind_singleton(CacheClient, lambda: RedisClient())

    # Resolve with automatic dependency injection
    cache = container.resolve(CacheClient)

Version: 1.0.0
GMP: di-dip-phase2-container
Author: Top Frontier AI Lab
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "DI Container",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "di_container",
    "type": "infrastructure",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "runtime.kernel_loader_ultimate",
            "core.singleton_registry",
            "memory.substrate_service",
            "tests.unit.test_di_container",
        ],
    },
}
# ============================================================================

import inspect
import threading
from typing import Any, Callable, Dict, Optional, Set, Type, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class DIContainerError(Exception):
    """Base exception for DI container errors."""

    pass


class CircularDependencyError(DIContainerError):
    """Raised when circular dependency is detected."""

    pass


class BindingNotFoundError(DIContainerError):
    """Raised when no binding exists for requested type."""

    pass


class ResolutionError(DIContainerError):
    """Raised when dependency resolution fails."""

    pass


class DIContainer:
    """
    Lightweight dependency injection container for L9.

    Provides constructor injection, lifecycle management, and circular
    dependency detection with thread-safe operations.

    Example:
        container = DIContainer()

        # Bind singleton
        container.bind_singleton(CacheClient, lambda: RedisClient())

        # Bind transient
        container.bind_transient(Logger, lambda: StructlogLogger())

        # Resolve with auto-injection
        cache = container.resolve(CacheClient)
    """

    def __init__(self):
        """Initialize DI container."""
        self._bindings: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_bindings: Set[Type] = set()
        self._building: Set[Type] = set()
        self._lock = threading.RLock()

        logger.info("di_container.initialized")

    def bind_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Bind interface to singleton factory.

        The factory will be called once, and the same instance will be
        returned for all subsequent resolve() calls.

        Args:
            interface: Interface type (typically a Protocol)
            factory: Factory function that creates the instance

        Example:
            container.bind_singleton(CacheClient, lambda: RedisClient())
        """
        with self._lock:
            self._bindings[interface] = factory
            self._singleton_bindings.add(interface)

            logger.debug(
                "di_container.binding_registered",
                interface=interface.__name__,
                lifecycle="singleton",
            )

    def bind_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Bind interface to transient factory.

        The factory will be called each time resolve() is called,
        returning a new instance each time.

        Args:
            interface: Interface type (typically a Protocol)
            factory: Factory function that creates instances

        Example:
            container.bind_transient(Logger, lambda: StructlogLogger())
        """
        with self._lock:
            self._bindings[interface] = factory
            # Explicitly remove from singleton bindings if it was there
            self._singleton_bindings.discard(interface)

            logger.debug(
                "di_container.binding_registered",
                interface=interface.__name__,
                lifecycle="transient",
            )

    def bind_instance(self, interface: Type[T], instance: T) -> None:
        """
        Bind interface to existing instance.

        The provided instance will be returned for all resolve() calls.
        This is useful for pre-configured instances.

        Args:
            interface: Interface type
            instance: Pre-created instance

        Example:
            redis = RedisClient(host="localhost")
            container.bind_instance(CacheClient, redis)
        """
        with self._lock:
            self._singletons[interface] = instance
            self._singleton_bindings.add(interface)

            logger.debug(
                "di_container.instance_bound",
                interface=interface.__name__,
                instance_type=type(instance).__name__,
            )

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve dependency by interface type.

        Automatically injects constructor dependencies based on type hints.
        Detects circular dependencies and provides clear error messages.

        Args:
            interface: Interface type to resolve

        Returns:
            Instance implementing the interface

        Raises:
            BindingNotFoundError: If no binding exists for interface
            CircularDependencyError: If circular dependency detected
            ResolutionError: If resolution fails for any other reason

        Example:
            cache = container.resolve(CacheClient)
        """
        with self._lock:
            # Check if already instantiated as singleton
            if interface in self._singletons:
                logger.debug(
                    "di_container.resolved_from_cache",
                    interface=interface.__name__,
                )
                return self._singletons[interface]

            # Check for binding
            if interface not in self._bindings:
                logger.error(
                    "di_container.binding_not_found",
                    interface=interface.__name__,
                    available_bindings=list(self._bindings.keys()),
                )
                raise BindingNotFoundError(
                    f"No binding registered for {interface.__name__}. "
                    f"Available bindings: {[t.__name__ for t in self._bindings.keys()]}"
                )

            # Detect circular dependencies
            if interface in self._building:
                dependency_chain = " -> ".join(
                    [t.__name__ for t in self._building] + [interface.__name__]
                )
                logger.error(
                    "di_container.circular_dependency_detected",
                    interface=interface.__name__,
                    dependency_chain=dependency_chain,
                )
                raise CircularDependencyError(
                    f"Circular dependency detected: {dependency_chain}"
                )

            # Mark as building
            self._building.add(interface)

            try:
                factory = self._bindings[interface]

                # Auto-inject constructor dependencies
                instance = self._create_instance(factory, interface)

                # Cache singleton
                if interface in self._singleton_bindings:
                    self._singletons[interface] = instance
                    logger.debug(
                        "di_container.singleton_cached",
                        interface=interface.__name__,
                        instance_type=type(instance).__name__,
                    )

                logger.info(
                    "di_container.resolved",
                    interface=interface.__name__,
                    instance_type=type(instance).__name__,
                    lifecycle=(
                        "singleton"
                        if interface in self._singleton_bindings
                        else "transient"
                    ),
                )

                return instance

            except Exception as e:
                logger.error(
                    "di_container.resolution_failed",
                    interface=interface.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if isinstance(e, (CircularDependencyError, BindingNotFoundError)):
                    raise
                raise ResolutionError(
                    f"Failed to resolve {interface.__name__}: {str(e)}"
                ) from e
            finally:
                self._building.discard(interface)

    def _create_instance(self, factory: Callable, interface: Type) -> Any:
        """
        Create instance using factory with automatic dependency injection.

        Args:
            factory: Factory function or class
            interface: Interface type being resolved

        Returns:
            Created instance
        """
        try:
            # Check if factory is a class (type)
            if inspect.isclass(factory):
                # Get __init__ signature for classes
                sig = inspect.signature(factory.__init__)
                factory_name = factory.__name__
            else:
                # Get factory signature for functions
                sig = inspect.signature(factory)
                factory_name = getattr(factory, "__name__", "<lambda>")

            # If no parameters (or only 'self' for classes), call factory directly
            params = [p for p in sig.parameters.values() if p.name != "self"]
            if not params:
                return factory()

            # Auto-inject dependencies based on type hints
            deps = {}
            for param in params:
                if param.annotation != inspect.Parameter.empty:
                    annotation = param.annotation

                    # Handle string annotations (from __future__ import annotations)
                    if isinstance(annotation, str):
                        # Try to resolve string annotation using get_type_hints (safer than eval)
                        try:
                            from typing import get_type_hints
                            if inspect.isclass(factory):
                                hints = get_type_hints(factory.__init__, globalns=factory.__init__.__globals__, localns=None)
                                annotation = hints.get(param.name, annotation)
                            else:
                                hints = get_type_hints(factory, globalns=factory.__globals__, localns=None)
                                annotation = hints.get(param.name, annotation)
                        except Exception as e:
                            logger.debug(
                                "di_container.skipping_unresolvable_annotation",
                                parent=factory_name,
                                parameter=param.name,
                                annotation=param.annotation,
                                error=str(e),
                            )
                            continue

                    # Recursively resolve dependency
                    deps[param.name] = self.resolve(annotation)
                    logger.debug(
                        "di_container.dependency_injected",
                        parent=factory_name,
                        dependency=getattr(annotation, "__name__", str(annotation)),
                        parameter=param.name,
                    )

            # Call factory with injected dependencies
            return factory(**deps) if deps else factory()

        except Exception as e:
            logger.error(
                "di_container.instance_creation_failed",
                interface=interface.__name__,
                error=str(e),
            )
            raise

    def has_binding(self, interface: Type) -> bool:
        """
        Check if binding exists for interface.

        Args:
            interface: Interface type

        Returns:
            True if binding exists
        """
        with self._lock:
            return interface in self._bindings or interface in self._singletons

    def get_optional(self, interface: Type[T]) -> Optional[T]:
        """
        Resolve dependency optionally (returns None if not registered).

        Useful for optional dependencies that may not be available in all
        deployment configurations.

        Args:
            interface: Interface type to resolve

        Returns:
            Instance implementing the interface, or None if not registered

        Example:
            persistence = container.get_optional(AgentPersistenceService)
            if persistence:
                await persistence.save_state(agent)
        """
        try:
            return self.resolve(interface)
        except BindingNotFoundError:
            logger.debug(
                "di_container.optional_dependency_not_found",
                interface=interface.__name__,
            )
            return None
        except Exception as e:
            logger.warning(
                "di_container.optional_dependency_resolution_failed",
                interface=interface.__name__,
                error=str(e),
            )
            return None

    def list_registrations(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered services with metadata.

        Returns detailed information about all registered bindings including
        lifecycle type, instantiation status, and instance type.

        Returns:
            Dictionary mapping interface names to registration metadata

        Example:
            >>> registrations = container.list_registrations()
            >>> print(f"Registered: {len(registrations)} services")
            >>> for name, info in registrations.items():
            ...     print(f"{name}: {info['lifecycle']}")
        """
        with self._lock:
            registrations = {}

            for interface in self._bindings.keys():
                is_singleton = interface in self._singleton_bindings
                is_instantiated = interface in self._singletons

                metadata = {
                    "interface": interface.__name__,
                    "lifecycle": "singleton" if is_singleton else "transient",
                    "instantiated": is_instantiated,
                }

                # Add instance type if instantiated
                if is_instantiated:
                    instance = self._singletons[interface]
                    metadata["instance_type"] = type(instance).__name__

                registrations[interface.__name__] = metadata

            logger.debug(
                "di_container.registrations_listed",
                total_count=len(registrations),
                singleton_count=len(self._singleton_bindings),
                instantiated_count=len(self._singletons),
            )

            return registrations

    def clear_singletons(self) -> None:
        """
        Clear all singleton instances.

        Useful for testing or hot-reloading. Bindings are preserved.
        """
        with self._lock:
            count = len(self._singletons)
            self._singletons.clear()
            logger.info("di_container.singletons_cleared", count=count)

    def clear_all(self) -> None:
        """
        Clear all bindings and singletons.

        Resets container to initial state.
        """
        with self._lock:
            binding_count = len(self._bindings)
            singleton_count = len(self._singletons)

            self._bindings.clear()
            self._singletons.clear()
            self._singleton_bindings.clear()
            self._building.clear()

            logger.info(
                "di_container.cleared",
                bindings_cleared=binding_count,
                singletons_cleared=singleton_count,
            )

    def get_bindings(self) -> Dict[str, str]:
        """
        Get all registered bindings.

        Returns:
            Dictionary mapping interface names to lifecycle types
        """
        with self._lock:
            return {
                interface.__name__: (
                    "singleton"
                    if interface in self._singleton_bindings
                    else "transient"
                )
                for interface in self._bindings.keys()
            }

    def __repr__(self) -> str:
        """String representation of container."""
        with self._lock:
            return (
                f"DIContainer("
                f"bindings={len(self._bindings)}, "
                f"singletons={len(self._singletons)}, "
                f"building={len(self._building)})"
            )


# Global container instance
_global_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_di_container() -> DIContainer:
    """
    Get global DI container instance.

    Creates container on first call (singleton pattern).

    Returns:
        Global DIContainer instance
    """
    global _global_container

    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = DIContainer()
                logger.info("di_container.global_instance_created")

    return _global_container


def reset_di_container() -> None:
    """
    Reset global DI container.

    Useful for testing. Creates fresh container on next get_di_container() call.
    """
    global _global_container

    with _container_lock:
        if _global_container is not None:
            _global_container.clear_all()
        _global_container = None
        logger.info("di_container.global_instance_reset")


__all__ = [
    "DIContainer",
    "DIContainerError",
    "CircularDependencyError",
    "BindingNotFoundError",
    "ResolutionError",
    "get_di_container",
    "reset_di_container",
]
