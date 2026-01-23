"""
Singleton Pattern Implementation (ADR-0004)

Provides @singleton decorator and SingletonMeta metaclass for enforcing
singleton pattern across L9 codebase.

Usage:
    @singleton
    class MyService:
        def __init__(self):
            self.data = []

    # Both return same instance
    service1 = MyService()
    service2 = MyService()
    assert service1 is service2
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "SingletonPattern",
    "module_version": "1.0.0",
    "layer": "Core/Patterns",
    "adr": "ADR-0004",
    "criticality": "high",
    "observability": {
        "metrics": ["singleton_instances_created", "singleton_registry_size"],
        "logs": ["singleton_created", "singleton_reused"],
    },
}
# ============================================================================

import functools
import threading
from typing import Any, Callable, Dict, Type, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")

# Global singleton registry
_singleton_registry: Dict[Type, Any] = {}
_singleton_lock = threading.Lock()


class SingletonMeta(type):
    """
    Metaclass for implementing singleton pattern.
    
    Thread-safe singleton implementation using double-checked locking.
    
    Usage:
        class MyService(metaclass=SingletonMeta):
            pass
    """

    _instances: Dict[Type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """Create or return existing instance."""
        # Fast path: instance already exists
        if cls in cls._instances:
            logger.debug(
                "singleton_reused",
                class_name=cls.__name__,
                instance_id=id(cls._instances[cls]),
            )
            return cls._instances[cls]

        # Slow path: create new instance with lock
        with cls._lock:
            # Double-check: another thread may have created it
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
                
                # Register in global registry
                _singleton_registry[cls] = instance
                
                logger.info(
                    "singleton_created",
                    class_name=cls.__name__,
                    instance_id=id(instance),
                    registry_size=len(_singleton_registry),
                )
            
            return cls._instances[cls]


def singleton(cls: Type[T]) -> Type[T]:
    """
    Decorator to make a class a singleton.
    
    Thread-safe singleton implementation. The first instantiation creates
    the instance, subsequent calls return the same instance.
    
    Args:
        cls: The class to make a singleton
        
    Returns:
        The singleton-wrapped class
        
    Example:
        @singleton
        class DatabaseConnection:
            def __init__(self, url: str):
                self.url = url
                self.connected = False
                
        # Both return same instance
        db1 = DatabaseConnection("postgres://localhost")
        db2 = DatabaseConnection("postgres://localhost")
        assert db1 is db2
    """
    
    @functools.wraps(cls, updated=())
    class SingletonWrapper(cls):  # type: ignore
        _instance = None
        _lock = threading.Lock()

        def __new__(cls_inner, *args, **kwargs):
            """Create or return existing instance."""
            # Fast path: instance already exists
            if cls_inner._instance is not None:
                logger.debug(
                    "singleton_reused",
                    class_name=cls.__name__,
                    instance_id=id(cls_inner._instance),
                )
                return cls_inner._instance

            # Slow path: create new instance with lock
            with cls_inner._lock:
                # Double-check: another thread may have created it
                if cls_inner._instance is None:
                    instance = super(SingletonWrapper, cls_inner).__new__(cls_inner)
                    cls_inner._instance = instance
                    
                    # Register in global registry
                    _singleton_registry[cls] = instance
                    
                    logger.info(
                        "singleton_created",
                        class_name=cls.__name__,
                        instance_id=id(instance),
                        registry_size=len(_singleton_registry),
                    )
                
                return cls_inner._instance

        def __init__(self, *args, **kwargs):
            """Initialize instance only once."""
            # Only initialize if not already initialized
            if not hasattr(self, "_initialized"):
                super().__init__(*args, **kwargs)
                self._initialized = True

    # Preserve class name and module
    SingletonWrapper.__name__ = cls.__name__
    SingletonWrapper.__qualname__ = cls.__qualname__
    SingletonWrapper.__module__ = cls.__module__
    
    return SingletonWrapper  # type: ignore


def get_singleton_registry() -> Dict[Type, Any]:
    """
    Get the global singleton registry.
    
    Returns:
        Dictionary mapping singleton classes to their instances
        
    Example:
        registry = get_singleton_registry()
        print(f"Active singletons: {len(registry)}")
        for cls, instance in registry.items():
            print(f"  {cls.__name__}: {id(instance)}")
    """
    return _singleton_registry.copy()


def clear_singleton_registry() -> None:
    """
    Clear the global singleton registry.
    
    WARNING: This is primarily for testing. Clearing the registry
    in production can lead to unexpected behavior.
    
    Example:
        # In test teardown
        clear_singleton_registry()
    """
    global _singleton_registry
    
    with _singleton_lock:
        count = len(_singleton_registry)
        _singleton_registry.clear()
        
        logger.warning(
            "singleton_registry_cleared",
            instances_cleared=count,
        )


def reset_singleton(cls: Type[T]) -> None:
    """
    Reset a specific singleton instance.
    
    WARNING: This is primarily for testing. Resetting singletons
    in production can lead to unexpected behavior.
    
    Args:
        cls: The singleton class to reset
        
    Example:
        @singleton
        class MyService:
            pass
            
        # In test
        service1 = MyService()
        reset_singleton(MyService)
        service2 = MyService()
        assert service1 is not service2
    """
    with _singleton_lock:
        if cls in _singleton_registry:
            del _singleton_registry[cls]
            
        # Also clear from metaclass registry if using SingletonMeta
        if isinstance(cls, SingletonMeta):
            if cls in SingletonMeta._instances:
                del SingletonMeta._instances[cls]
                
        # Clear from decorator wrapper
        if hasattr(cls, "_instance"):
            cls._instance = None
            
        logger.info(
            "singleton_reset",
            class_name=cls.__name__,
        )


# Export public API
__all__ = [
    "singleton",
    "SingletonMeta",
    "get_singleton_registry",
    "clear_singleton_registry",
    "reset_singleton",
]
