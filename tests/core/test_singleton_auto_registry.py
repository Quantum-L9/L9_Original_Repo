"""
Tests for L9 Singleton Service Auto-Registration System
"""

import pytest

from core.singleton_auto_registry import (
    get_all_singleton_services,
    get_singleton_services_by_category,
    register_singleton,
    register_singleton_closer,
    singleton_service_registry,
    wire_singletons_to_registry,
)
from core.singleton_registry import SingletonLifecycle, SingletonRegistry


@pytest.fixture(autouse=True)
def _clear_registries():
    """Clear all registries before and after each test."""
    singleton_service_registry.clear()
    yield
    singleton_service_registry.clear()


def test_register_singleton_decorator():
    """Test that @register_singleton decorator registers a service."""

    @register_singleton(category="test", description="Test service")
    def get_my_test_service():
        return "test_service_instance"

    services = get_all_singleton_services()

    assert "my_test_service" in services
    config = services["my_test_service"]
    assert config.name == "my_test_service"
    assert config.category == "test"
    assert config.description == "Test service"
    assert config.getter() == "test_service_instance"


def test_register_singleton_with_closer():
    """Test that @register_singleton_closer attaches a closer."""

    @register_singleton(category="test")
    def get_another_service():
        return "another_instance"

    @register_singleton_closer("another_service")
    def close_another_service():
        return "closed"

    services = get_all_singleton_services()

    assert "another_service" in services
    config = services["another_service"]
    assert config.closer is not None
    assert config.closer() == "closed"


def test_wire_singletons_to_main_registry():
    """Test that auto-registered singletons can be wired to the main registry."""

    @register_singleton(category="core", lifecycle=SingletonLifecycle.STARTUP)
    def get_core_service():
        return "core_instance"

    @register_singleton(category="memory", dependencies=["core_service"])
    def get_memory_service():
        return "memory_instance"

    main_registry = SingletonRegistry()
    wired_count = wire_singletons_to_registry(main_registry)

    assert wired_count == 2

    core_entry = main_registry._singletons.get("core_service")
    assert core_entry is not None
    assert core_entry.lifecycle == SingletonLifecycle.STARTUP

    memory_entry = main_registry._singletons.get("memory_service")
    assert memory_entry is not None
    assert memory_entry.dependencies == ["core_service"]


def test_get_services_by_category():
    """Test filtering singleton services by category."""

    @register_singleton(category="cat1")
    def get_service1():
        pass

    @register_singleton(category="cat2")
    def get_service2():
        pass

    @register_singleton(category="cat1")
    def get_service3():
        pass

    cat1_services = get_singleton_services_by_category("cat1")
    assert len(cat1_services) == 2
    assert "service1" in cat1_services
    assert "service3" in cat1_services

    cat2_services = get_singleton_services_by_category("cat2")
    assert len(cat2_services) == 1
    assert "service2" in cat2_services
