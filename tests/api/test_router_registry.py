"""
Tests for api.router_registry module.

Test suite for the router auto-registration system.
"""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.router_registry import (
    router_registry,
    register_router,
    wire_routers,
    get_router_snapshot,
)
from core.moduleregistry import ModuleRegistry

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def clean_registry():
    """Clean the router registry before each test."""
    # Save original state
    original_components = router_registry._components.copy()
    original_metadata = router_registry._metadata.copy()
    original_factories = router_registry._factories.copy()

    # Clear registry
    router_registry._components.clear()
    router_registry._metadata.clear()
    router_registry._factories.clear()

    yield router_registry

    # Restore original state
    router_registry._components = original_components
    router_registry._metadata = original_metadata
    router_registry._factories = original_factories


@pytest.fixture
def app():
    """Create a fresh FastAPI app for each test."""
    return FastAPI()


@pytest.fixture
def module_registry():
    """Create a fresh ModuleRegistry for each test."""
    return ModuleRegistry()


# =============================================================================
# Basic Registration Tests
# =============================================================================


def test_register_router_decorator(clean_registry):
    """Test registering a router with decorator."""

    @register_router(prefix="/test", name="test_router", tags=["test"])
    def create_test_router():
        router = APIRouter()

        @router.get("/hello")
        async def hello():
            return {"message": "hello"}

        return router

    # Factory should be registered
    assert "test_router" in clean_registry._factories


def test_register_router_instance(clean_registry):
    """Test registering an existing router instance."""
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    # Register the router
    registered_router = register_router(prefix="/api", name="health_router")(router)

    # Should be the same router
    assert registered_router == router


# =============================================================================
# Wiring Tests
# =============================================================================


def test_wire_routers_basic(clean_registry, app):
    """Test wiring routers to FastAPI app."""

    @register_router(prefix="/api/v1", name="test_router", tags=["test"])
    def create_router():
        router = APIRouter()

        @router.get("/ping")
        async def ping():
            return {"ping": "pong"}

        return router

    # Wire routers
    count = wire_routers(app)

    assert count == 1

    # Test the endpoint
    client = TestClient(app)
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}


def test_wire_routers_with_module_registry(clean_registry, app, module_registry):
    """Test wiring routers with ModuleRegistry integration."""

    @register_router(
        prefix="/api/test",
        name="test_module",
        module_display_name="Test Module",
    )
    def create_router():
        router = APIRouter()

        @router.get("/status")
        async def status():
            return {"status": "active"}

        return router

    # Wire with module registry
    count = wire_routers(app, module_registry)

    assert count == 1

    # Check module was registered
    definition = module_registry.get_definition("test_module")
    assert definition is not None
    assert definition.display_name == "Test Module"
    assert definition.route_prefix == "/api/test"


def test_wire_routers_priority(clean_registry, app):
    """Test routers are wired in priority order."""
    order = []

    @register_router(prefix="/low", name="low_priority", priority=1)
    def create_low():
        router = APIRouter()
        order.append("low")
        return router

    @register_router(prefix="/high", name="high_priority", priority=10)
    def create_high():
        router = APIRouter()
        order.append("high")
        return router

    @register_router(prefix="/medium", name="medium_priority", priority=5)
    def create_medium():
        router = APIRouter()
        order.append("medium")
        return router

    wire_routers(app)

    # Should be wired in priority order: high, medium, low
    assert order == ["high", "medium", "low"]


# =============================================================================
# Snapshot Tests
# =============================================================================


def test_router_snapshot(clean_registry):
    """Test getting router registry snapshot."""

    @register_router(prefix="/api/v1", name="router1", tags=["api"])
    def create_router1():
        return APIRouter()

    @register_router(prefix="/api/v2", name="router2", tags=["api"])
    def create_router2():
        return APIRouter()

    snapshot = get_router_snapshot()

    assert snapshot["registry_name"] == "api_routers"
    assert snapshot["factory_count"] == 2


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_workflow(clean_registry, app):
    """Test complete workflow: register -> wire -> test."""

    @register_router(prefix="/api/users", name="users", tags=["users"])
    def create_users_router():
        router = APIRouter()

        @router.get("/")
        async def list_users():
            return {"users": []}

        @router.get("/{user_id}")
        async def get_user(user_id: int):
            return {"user_id": user_id, "name": f"User {user_id}"}

        return router

    # Wire routers
    wire_routers(app)

    # Test endpoints
    client = TestClient(app)

    response = client.get("/api/users/")
    assert response.status_code == 200
    assert response.json() == {"users": []}

    response = client.get("/api/users/123")
    assert response.status_code == 200
    assert response.json() == {"user_id": 123, "name": "User 123"}


def test_example_autowired_router(app):
    """Test the example auto-wired router."""
    # Import the example router (triggers registration)
    from api.routes import example_autowired  # noqa: F401

    # Wire routers
    wire_routers(app)

    # Test endpoints
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/api/v1/autowired/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["autowired"] is True

    # Test echo endpoint
    response = client.post("/api/v1/autowired/echo", json={"message": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["echo"] == "test"
    assert data["autowired"] is True

    # Test info endpoint
    response = client.get("/api/v1/autowired/info")
    assert response.status_code == 200
    data = response.json()
    assert data["autowired"] is True
    assert "endpoints" in data
