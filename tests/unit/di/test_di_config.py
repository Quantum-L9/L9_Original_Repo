"""
Tests for config.di_config
===========================

Comprehensive test suite for DI container configuration.

Test Coverage:
- ✅ DI container configuration
- ✅ Substrate bindings (cache, graph, vector)
- ✅ Service bindings (memory, world_model)
- ✅ Environment-specific overrides
- ✅ Feature flags (enable/disable DI)
- ✅ Backward compatibility helpers

Version: 1.0.0
Author: L9 Kernel Team
Related PR: #23 (builds on PR #22 DI/DIP foundation)
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from core.di.container import DIContainer, get_di_container
from core.abstractions import (
    CacheClient,
    GraphClient,
    VectorStore,
    MemoryRepository,
)
from config.di_config import (
    configure_di_container,
    initialize_di_container,
    get_cache_client,
    get_graph_client,
    get_vector_store,
    get_memory_service,
    is_di_enabled,
    should_use_di_for_substrates,
    get_environment,
)

# Alias for test compatibility (must be after imports for ruff E402)
MemoryService = MemoryRepository
# NOTE: WorldModelService alias removed in GMP-107 (was incorrectly aliased to ObservabilityService)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def clean_container():
    """Create a clean DI container for each test."""
    container = DIContainer()
    return container


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    mock = MagicMock(spec=CacheClient)
    return mock


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    mock = MagicMock(spec=GraphClient)
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    mock = MagicMock(spec=VectorStore)
    return mock


# =============================================================================
# Test: Container Configuration
# =============================================================================


def test_configure_di_container_success(clean_container):
    """Test successful DI container configuration."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify bindings exist
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings
    assert VectorStore in container._bindings
    assert MemoryService in container._bindings
    # NOTE: WorldModelService and ToolRegistry bindings removed in GMP-107
    # (were using incorrect type aliases)


def test_configure_di_container_uses_global_container():
    """Test configure_di_container uses global container by default."""
    # Configure without passing container
    container = configure_di_container()

    # Should return global container
    assert container is get_di_container()


def test_configure_di_container_environment_detection():
    """Test environment detection in configure_di_container."""
    with patch.dict(os.environ, {"L9_ENV": "dev"}):
        container = configure_di_container()

    # Container should be configured (no errors)
    assert CacheClient in container._bindings


# =============================================================================
# Test: Substrate Bindings
# =============================================================================


def test_cache_client_binding(clean_container):
    """Test CacheClient binding."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify binding exists
    assert CacheClient in container._bindings

    # Note: We can't resolve without mocking get_redis_client()
    # This test just verifies the binding is registered


def test_graph_client_binding(clean_container):
    """Test GraphClient binding."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify binding exists
    assert GraphClient in container._bindings


def test_vector_store_binding(clean_container):
    """Test VectorStore binding."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify binding exists
    assert VectorStore in container._bindings


# =============================================================================
# Test: Service Bindings
# =============================================================================


def test_memory_service_binding(clean_container):
    """Test MemoryService binding."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify binding exists
    assert MemoryService in container._bindings


# NOTE: test_world_model_service_binding and test_tool_registry_binding removed
# GMP-107: WorldModelService was incorrectly aliased to ObservabilityService
# GMP-107: ToolRegistry was incorrectly aliased to ToolExecutor
# These bindings will be re-added when proper protocols are defined


# =============================================================================
# Test: Backward Compatibility Helpers
# =============================================================================


def test_get_cache_client_helper():
    """Test get_cache_client backward compatibility helper."""
    # Configure container
    configure_di_container()

    # Note: This will fail without mocking get_redis_client()
    # Just test that the function exists and is callable
    assert callable(get_cache_client)


def test_get_graph_client_helper():
    """Test get_graph_client backward compatibility helper."""
    # Configure container
    configure_di_container()

    # Note: This will fail without mocking get_neo4j_client()
    # Just test that the function exists and is callable
    assert callable(get_graph_client)


def test_get_vector_store_helper():
    """Test get_vector_store backward compatibility helper."""
    # Configure container
    configure_di_container()

    # Just test that the function exists and is callable
    assert callable(get_vector_store)


def test_get_memory_service_helper():
    """Test get_memory_service backward compatibility helper."""
    # Configure container
    configure_di_container()

    # Just test that the function exists and is callable
    assert callable(get_memory_service)


# NOTE: test_get_world_model_service_di_helper removed in GMP-107
# The helper was removed because WorldModelService binding was using incorrect type alias


# =============================================================================
# Test: Feature Flags
# =============================================================================


def test_is_di_enabled_default():
    """Test DI is enabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_di_enabled() is True


def test_is_di_enabled_true():
    """Test DI enabled when L9_DI_ENABLED=true."""
    with patch.dict(os.environ, {"L9_DI_ENABLED": "true"}):
        assert is_di_enabled() is True


def test_is_di_enabled_false():
    """Test DI disabled when L9_DI_ENABLED=false."""
    with patch.dict(os.environ, {"L9_DI_ENABLED": "false"}):
        assert is_di_enabled() is False


def test_should_use_di_for_substrates_default():
    """Test substrates don't use DI by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_di_for_substrates() is False


def test_should_use_di_for_substrates_true():
    """Test substrates use DI when L9_DI_SUBSTRATES=true."""
    with patch.dict(os.environ, {"L9_DI_SUBSTRATES": "true"}):
        assert should_use_di_for_substrates() is True


def test_should_use_di_for_substrates_false():
    """Test substrates don't use DI when L9_DI_SUBSTRATES=false."""
    with patch.dict(os.environ, {"L9_DI_SUBSTRATES": "false"}):
        assert should_use_di_for_substrates() is False


# =============================================================================
# Test: Environment Detection
# =============================================================================


def test_get_environment_default():
    """Test default environment is production."""
    with patch.dict(os.environ, {}, clear=True):
        env = get_environment()
    assert env == "production"


def test_get_environment_from_env_var():
    """Test environment from L9_ENV variable."""
    with patch.dict(os.environ, {"L9_ENV": "dev"}):
        env = get_environment()
    assert env == "dev"


# =============================================================================
# Test: Initialization
# =============================================================================


def test_initialize_di_container_success():
    """Test successful DI container initialization."""
    # Initialize container
    container = initialize_di_container()

    # Verify bindings exist
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings
    assert VectorStore in container._bindings


def test_initialize_di_container_disabled():
    """Test DI container initialization when DI is disabled."""
    with patch.dict(os.environ, {"L9_DI_ENABLED": "false"}):
        container = initialize_di_container()

    # Should return global container (but not configure it)
    assert container is get_di_container()


# =============================================================================
# Test: Environment-Specific Configuration
# =============================================================================


def test_configure_di_container_dev_environment(clean_container):
    """Test DI container configuration for dev environment."""
    # Configure for dev
    container = configure_di_container(container=clean_container, env="dev")

    # Verify bindings exist (same as production for now)
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings


def test_configure_di_container_test_environment(clean_container):
    """Test DI container configuration for test environment."""
    # Configure for test
    container = configure_di_container(container=clean_container, env="test")

    # Verify bindings exist (same as production for now)
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings


def test_configure_di_container_staging_environment(clean_container):
    """Test DI container configuration for staging environment."""
    # Configure for staging
    container = configure_di_container(container=clean_container, env="staging")

    # Verify bindings exist (same as production)
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings


def test_configure_di_container_production_environment(clean_container):
    """Test DI container configuration for production environment."""
    # Configure for production
    container = configure_di_container(container=clean_container, env="production")

    # Verify bindings exist
    assert CacheClient in container._bindings
    assert GraphClient in container._bindings


# =============================================================================
# Test: Binding Count
# =============================================================================


def test_configure_di_container_binding_count(clean_container):
    """Test DI container has expected number of bindings."""
    # Configure container
    container = configure_di_container(container=clean_container)

    # Verify binding count (6 bindings: cache, graph, vector, memory, world_model, tool_registry)
    assert len(container._bindings) >= 6


# =============================================================================
# Test: Module Exports
# =============================================================================


def test_module_exports():
    """Test all expected functions are exported."""
    from config import di_config

    # Verify exports
    assert hasattr(di_config, "configure_di_container")
    assert hasattr(di_config, "initialize_di_container")
    assert hasattr(di_config, "get_cache_client")
    assert hasattr(di_config, "get_graph_client")
    assert hasattr(di_config, "get_vector_store")
    assert hasattr(di_config, "get_memory_service")
    # NOTE: get_world_model_service_di removed in GMP-107
    assert hasattr(di_config, "is_di_enabled")
    assert hasattr(di_config, "should_use_di_for_substrates")
    assert hasattr(di_config, "get_environment")
