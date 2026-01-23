"""
L9 Dependency Injection Package
===============================

Lightweight DI framework following Dependency Inversion Principle.

Exports:
- DIContainer: Main container for dependency registration and resolution
- get_di_container: Get global container instance
- reset_di_container: Reset global container (testing)
- Error classes for handling resolution failures

Usage:
    from core.di import DIContainer, get_di_container
    from core.protocols import CacheClient

    container = get_di_container()
    container.bind_singleton(CacheClient, lambda: RedisClient())
    cache = container.resolve(CacheClient)

Version: 1.0.0
"""

from core.di.container import (
    DIContainer,
    DIContainerError,
    CircularDependencyError,
    BindingNotFoundError,
    ResolutionError,
    get_di_container,
    reset_di_container,
)

__all__ = [
    "DIContainer",
    "DIContainerError",
    "CircularDependencyError",
    "BindingNotFoundError",
    "ResolutionError",
    "get_di_container",
    "reset_di_container",
]
