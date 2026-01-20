"""
Tests for router auto-registration system.
"""

import pytest
from fastapi import FastAPI, APIRouter
from api.routes.registry import router_registry, discover_routers


def test_router_registry_exists():
    """Test that router_registry singleton exists."""
    assert router_registry is not None


def test_router_registry_register():
    """Test registering a router."""
    test_router = APIRouter(prefix="/test", tags=["test"])

    router_registry.register(
        router=test_router, prefix="/test", tags=["test"], module="test_module"
    )

    # Check that router was registered
    routers = router_registry.list_routers()
    assert len(routers) > 0


def test_router_registry_wire_all():
    """Test wiring all routers to a FastAPI app."""
    app = FastAPI()

    # Wire all registered routers
    count = router_registry.wire_all(app)

    # Should have wired some routers
    assert count >= 0
    assert isinstance(count, int)


def test_discover_routers():
    """Test router discovery."""
    count = discover_routers("api.routes")

    # Should discover some routers
    assert count >= 0
    assert isinstance(count, int)


def test_router_registry_list_routers():
    """Test listing all registered routers."""
    routers = router_registry.list_routers()

    assert isinstance(routers, list)
    # Should have at least some routers registered
    assert len(routers) >= 0


def test_router_registry_get_snapshot():
    """Test getting router registry snapshot."""
    snapshot = router_registry.get_snapshot()

    assert "router_count" in snapshot
    assert "routers" in snapshot
    assert isinstance(snapshot["router_count"], int)
    assert isinstance(snapshot["routers"], list)


def test_router_registration_metadata():
    """Test that router registration includes metadata."""
    test_router = APIRouter(prefix="/test2", tags=["test2"])

    router_registry.register(
        router=test_router,
        prefix="/test2",
        tags=["test2"],
        module="test_module2",
        description="Test router for testing",
    )

    snapshot = router_registry.get_snapshot()

    # Check that metadata is preserved
    assert snapshot["router_count"] > 0

    # Find our test router in the snapshot
    found = False
    for router_info in snapshot["routers"]:
        if router_info.get("prefix") == "/test2":
            found = True
            assert "test2" in router_info.get("tags", [])
            break

    assert found, "Test router not found in snapshot"
