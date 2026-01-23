"""
Core Patterns Module

Provides reusable design patterns for L9 architecture.
"""

from core.patterns.singleton import (
    SingletonMeta,
    clear_singleton_registry,
    get_singleton_registry,
    reset_singleton,
    singleton,
)

__all__ = [
    "singleton",
    "SingletonMeta",
    "get_singleton_registry",
    "clear_singleton_registry",
    "reset_singleton",
]
