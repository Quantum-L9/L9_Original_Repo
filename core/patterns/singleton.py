"""
Singleton Pattern Implementation for L9 AIOS

Provides a standardized Singleton decorator to ensure only one instance
of a class exists throughout the application lifecycle.

Usage:
    from core.patterns.singleton import singleton
    
    @singleton
    class MyService:
        def __init__(self):
            self.data = []
"""

from functools import wraps
from threading import RLock
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar('T')

# Global registry of singleton instances
_instances: Dict[Type, Any] = {}
_lock = RLock()


def singleton(cls: Type[T]) -> Callable[..., T]:
    """
    Singleton decorator that ensures only one instance of a class exists.
    
    Thread-safe implementation using RLock to prevent race conditions
    during instance creation.
    
    Args:
        cls: The class to be decorated as a singleton
        
    Returns:
        A wrapper function that returns the singleton instance
        
    Example:
        @singleton
        class DatabaseConnection:
            def __init__(self, host: str, port: int):
                self.host = host
                self.port = port
        
        # Both calls return the same instance
        db1 = DatabaseConnection("localhost", 5432)
        db2 = DatabaseConnection("localhost", 5432)
        assert db1 is db2  # True
    """
    
    @wraps(cls)
    def get_instance(*args, **kwargs) -> T:
        """Get or create the singleton instance"""
        if cls not in _instances:
            with _lock:
                # Double-checked locking pattern
                if cls not in _instances:
                    _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]
    
    # Preserve class attributes for introspection
    get_instance.__wrapped__ = cls
    get_instance.__name__ = cls.__name__
    get_instance.__qualname__ = cls.__qualname__
    
    return get_instance


def reset_singleton(cls: Type) -> None:
    """
    Reset a singleton instance (useful for testing).
    
    Args:
        cls: The singleton class to reset
        
    Example:
        reset_singleton(DatabaseConnection)
        db = DatabaseConnection()  # Creates a new instance
    """
    with _lock:
        if cls in _instances:
            del _instances[cls]


def reset_all_singletons() -> None:
    """
    Reset all singleton instances (useful for testing).
    
    Example:
        reset_all_singletons()
        # All singletons will be recreated on next access
    """
    with _lock:
        _instances.clear()


def get_singleton_registry() -> Dict[Type, Any]:
    """
    Get a copy of the singleton registry (for debugging/monitoring).
    
    Returns:
        Dictionary mapping singleton classes to their instances
        
    Example:
        registry = get_singleton_registry()
        print(f"Active singletons: {len(registry)}")
    """
    with _lock:
        return _instances.copy()
