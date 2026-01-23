"""
Unit tests for Singleton Pattern (ADR-0004)
"""

import pytest
import threading
from core.patterns import singleton, SingletonMeta, get_singleton_registry, clear_singleton_registry, reset_singleton


class TestSingletonDecorator:
    """Test @singleton decorator."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_singleton_registry()
    
    def test_singleton_creates_single_instance(self):
        """Test that @singleton creates only one instance."""
        @singleton
        class TestService:
            def __init__(self):
                self.value = 42
        
        instance1 = TestService()
        instance2 = TestService()
        
        assert instance1 is instance2
        assert instance1.value == 42
    
    def test_singleton_with_init_args(self):
        """Test singleton with __init__ arguments."""
        @singleton
        class ConfigService:
            def __init__(self, config_path: str):
                self.config_path = config_path
        
        service1 = ConfigService("/etc/config.yaml")
        service2 = ConfigService("/different/path.yaml")  # Ignored
        
        assert service1 is service2
        assert service1.config_path == "/etc/config.yaml"
    
    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        @singleton
        class ThreadSafeService:
            def __init__(self):
                self.counter = 0
        
        instances = []
        
        def create_instance():
            instances.append(ThreadSafeService())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All instances should be the same
        assert len(set(id(i) for i in instances)) == 1
    
    def test_singleton_registry(self):
        """Test that singletons are registered."""
        @singleton
        class RegisteredService:
            pass
        
        instance = RegisteredService()
        registry = get_singleton_registry()
        
        # Registry contains the instance
        assert len(registry) == 1
        assert instance in registry.values()
    
    def test_reset_singleton(self):
        """Test resetting a singleton."""
        @singleton
        class ResettableService:
            def __init__(self):
                self.id = id(self)
        
        service1 = ResettableService()
        id1 = service1.id
        
        reset_singleton(ResettableService)
        
        service2 = ResettableService()
        id2 = service2.id
        
        assert id1 != id2


class TestSingletonMeta:
    """Test SingletonMeta metaclass."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_singleton_registry()
    
    def test_singleton_meta_creates_single_instance(self):
        """Test that SingletonMeta creates only one instance."""
        class MetaService(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 100
        
        instance1 = MetaService()
        instance2 = MetaService()
        
        assert instance1 is instance2
        assert instance1.value == 100
    
    def test_singleton_meta_thread_safety(self):
        """Test that SingletonMeta is thread-safe."""
        class ThreadSafeMeta(metaclass=SingletonMeta):
            def __init__(self):
                self.counter = 0
        
        instances = []
        
        def create_instance():
            instances.append(ThreadSafeMeta())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All instances should be the same
        assert len(set(id(i) for i in instances)) == 1


class TestSingletonRegistry:
    """Test singleton registry functions."""
    
    def setup_method(self):
        """Clear registry before each test."""
        clear_singleton_registry()
    
    def test_get_singleton_registry(self):
        """Test getting singleton registry."""
        @singleton
        class Service1:
            pass
        
        @singleton
        class Service2:
            pass
        
        s1 = Service1()
        s2 = Service2()
        
        registry = get_singleton_registry()
        assert len(registry) == 2
        assert s1 in registry.values()
        assert s2 in registry.values()
    
    def test_clear_singleton_registry(self):
        """Test clearing singleton registry."""
        @singleton
        class ClearableService:
            pass
        
        instance = ClearableService()
        assert len(get_singleton_registry()) == 1
        
        clear_singleton_registry()
        assert len(get_singleton_registry()) == 0
