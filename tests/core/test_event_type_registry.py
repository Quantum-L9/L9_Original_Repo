"""
Tests for L9 Event Type Auto-Registration System
"""

from enum import Enum

import pytest

from core.event_type_registry import (
    create_dynamic_event_enum,
    event_type_registry,
    get_all_event_types,
    get_event_categories,
    is_event_type_registered,
    register_event_category,
    register_event_type,
)


@pytest.fixture(autouse=True)
def _clear_registries():
    """Clear all registries before and after each test."""
    event_type_registry.clear()
    yield
    event_type_registry.clear()


def test_register_event_type():
    """Test that an event type can be registered."""
    register_event_type(
        name="test_event", category="testing", description="A test event"
    )

    event_types = get_all_event_types()
    assert "test_event" in event_types
    config = event_types["test_event"]
    assert config.name == "test_event"
    assert config.category == "testing"
    assert config.description == "A test event"


def test_register_event_category():
    """Test registering multiple events in a category."""
    register_event_category("coordination", ["req", "res"], domain="test")

    event_types = get_all_event_types()
    assert "req" in event_types
    assert "res" in event_types
    assert event_types["req"].category == "coordination"
    assert event_types["res"].metadata["domain"] == "test"


def test_get_event_categories():
    """Test getting all unique event categories."""
    register_event_type(name="e1", category="c1")
    register_event_type(name="e2", category="c2")
    register_event_type(name="e3", category="c1")

    categories = get_event_categories()
    assert categories == {"c1", "c2"}


def test_create_dynamic_event_enum():
    """Test creating a dynamic enum from registered event types."""
    register_event_category("security", ["login", "logout"])
    register_event_category("data", ["create", "delete"])

    SecurityEvent = create_dynamic_event_enum("security")
    assert issubclass(SecurityEvent, Enum)
    assert SecurityEvent.LOGIN.value == "login"
    assert list(SecurityEvent) == [SecurityEvent.LOGIN, SecurityEvent.LOGOUT]

    AllEvents = create_dynamic_event_enum()
    assert len(list(AllEvents)) == 4


def test_is_event_type_registered():
    """Test checking if an event type is registered."""
    register_event_type(name="my_event", category="custom")

    assert is_event_type_registered("my_event") is True
    assert is_event_type_registered("nonexistent_event") is False
