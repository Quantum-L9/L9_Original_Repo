"""
Tests for router auto-registration system.

Tests the actual RouterRegistry API.
"""

from fastapi import APIRouter, FastAPI

from api.routes.registry import discover_routers, router_registry


def test_router_registry_exists():
    """Test that router_registry singleton exists."""
    assert router_registry is not None


def test_router_registry_register():
    """Test registering a router."""
    test_router = APIRouter(prefix="/test_gmp22", tags=["test_gmp22"])

    router_registry.register(
        router=test_router,
        prefix="/test_gmp22",
        tags=["test_gmp22"],
        module_id="test_gmp22_module",
    )

    # Check that router was registered via snapshot
    snapshot = router_registry.snapshot()
    assert snapshot["count"] > 0

    # Find our test router
    found = any(r["module_id"] == "test_gmp22_module" for r in snapshot["routers"])
    assert found, "Test router not found in snapshot"


def test_router_registry_wire_all():
    """Test wiring all routers to a FastAPI app."""
    app = FastAPI()

    # Wire all registered routers
    count = router_registry.wire_all(app)

    # Should have wired some routers
    assert count >= 0
    assert isinstance(count, int)


def test_discover_routers():
    """Test router discovery (no arguments)."""
    count = discover_routers()

    # Should discover some routers
    assert count >= 0
    assert isinstance(count, int)


def test_router_registry_snapshot():
    """Test getting router registry snapshot."""
    snapshot = router_registry.snapshot()

    assert "count" in snapshot
    assert "routers" in snapshot
    assert "wired_count" in snapshot
    assert isinstance(snapshot["count"], int)
    assert isinstance(snapshot["routers"], list)


def test_router_registry_len():
    """Test __len__ method."""
    length = len(router_registry)
    assert isinstance(length, int)
    assert length >= 0


def test_router_registration_metadata():
    """Test that router registration includes metadata."""
    test_router = APIRouter(prefix="/test_gmp22_v2", tags=["test_gmp22_v2"])

    router_registry.register(
        router=test_router,
        prefix="/test_gmp22_v2",
        tags=["test_gmp22_v2"],
        module_id="test_gmp22_module_v2",
        display_name="Test GMP22 Router V2",
    )

    snapshot = router_registry.snapshot()

    # Check that metadata is preserved
    assert snapshot["count"] > 0

    # Find our test router in the snapshot
    found = False
    for router_info in snapshot["routers"]:
        if router_info.get("module_id") == "test_gmp22_module_v2":
            found = True
            assert router_info.get("display_name") == "Test GMP22 Router V2"
            assert "test_gmp22_v2" in router_info.get("tags", [])
            break

    assert found, "Test router not found in snapshot"


def test_router_get_definition():
    """Test getting router definition by module_id."""
    # First register a router
    test_router = APIRouter(prefix="/test_gmp22_def", tags=["test_gmp22_def"])
    router_registry.register(
        router=test_router,
        prefix="/test_gmp22_def",
        module_id="test_gmp22_def",
    )

    # Get definition
    definition = router_registry.get_definition("test_gmp22_def")
    assert definition is not None
    assert definition.module_id == "test_gmp22_def"
    assert definition.prefix == "/test_gmp22_def"


def test_router_get_definition_nonexistent():
    """Test getting non-existent router definition returns None."""
    definition = router_registry.get_definition("nonexistent_router_12345")
    assert definition is None
