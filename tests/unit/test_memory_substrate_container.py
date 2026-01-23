"""
Unit Tests for MemorySubstrateContainer

Tests DI container for memory substrate with protocol-based wiring.

Version: 1.0.0
Created: 2026-01-22
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import container
from core.di.container import MemorySubstrateContainer, DIContainerError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Provide mock configuration for container."""
    return {
        "database_url": "postgresql://localhost/test",
        "db_pool_size": 2,
        "db_max_overflow": 5,
        "embedding_provider_type": "stub",
        "embedding_model": "text-embedding-3-large",
        "openai_api_key": "test-key",
    }


@pytest.fixture
def container(mock_config):
    """Provide MemorySubstrateContainer instance."""
    return MemorySubstrateContainer(mock_config)


# ============================================================================
# Initialization Tests
# ============================================================================


def test_container_initialization(mock_config):
    """Test that container initializes with config."""
    container = MemorySubstrateContainer(mock_config)

    assert container._config == mock_config
    assert container._repository is None
    assert container._embedding_provider is None
    assert container._semantic_service is None
    assert container._dag is None
    assert container._service is None


def test_container_initialization_minimal_config():
    """Test that container works with minimal config."""
    minimal_config = {"database_url": "postgresql://localhost/test"}
    container = MemorySubstrateContainer(minimal_config)

    assert container._config["database_url"] == "postgresql://localhost/test"


# ============================================================================
# Repository Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.SubstrateRepository")
async def test_get_repository_creates_singleton(mock_repo_class, container):
    """Test that get_repository creates singleton instance."""
    mock_repo_instance = AsyncMock()
    mock_repo_class.return_value = mock_repo_instance

    # First call creates instance
    repo1 = await container.get_repository()
    assert repo1 is mock_repo_instance
    mock_repo_instance.connect.assert_called_once()

    # Second call returns same instance
    repo2 = await container.get_repository()
    assert repo2 is repo1
    assert mock_repo_instance.connect.call_count == 1  # Not called again


@pytest.mark.asyncio
@patch("core.di.container.SubstrateRepository")
async def test_get_repository_handles_connection_failure(mock_repo_class, container):
    """Test that get_repository handles connection failures."""
    mock_repo_instance = AsyncMock()
    mock_repo_instance.connect.side_effect = Exception("Connection failed")
    mock_repo_class.return_value = mock_repo_instance

    with pytest.raises(DIContainerError, match="Failed to initialize repository"):
        await container.get_repository()


# ============================================================================
# Embedding Provider Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.create_embedding_provider")
async def test_get_embedding_provider_creates_singleton(mock_create_fn, container):
    """Test that get_embedding_provider creates singleton instance."""
    mock_provider = MagicMock()
    mock_create_fn.return_value = mock_provider

    # First call creates instance
    provider1 = await container.get_embedding_provider()
    assert provider1 is mock_provider
    mock_create_fn.assert_called_once_with(
        provider_type="stub",
        model="text-embedding-3-large",
        api_key="test-key",
    )

    # Second call returns same instance
    provider2 = await container.get_embedding_provider()
    assert provider2 is provider1
    assert mock_create_fn.call_count == 1  # Not called again


@pytest.mark.asyncio
@patch("core.di.container.create_embedding_provider")
async def test_get_embedding_provider_defaults(mock_create_fn):
    """Test that get_embedding_provider uses defaults when config missing."""
    container = MemorySubstrateContainer(
        {"database_url": "postgresql://localhost/test"}
    )
    mock_provider = MagicMock()
    mock_create_fn.return_value = mock_provider

    await container.get_embedding_provider()

    mock_create_fn.assert_called_once_with(
        provider_type="openai",  # Default
        model="text-embedding-3-large",  # Default
        api_key=None,  # Not in config
    )


# ============================================================================
# Semantic Service Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.SemanticService")
@patch("core.di.container.create_embedding_provider")
@patch("core.di.container.SubstrateRepository")
async def test_get_semantic_service_wires_dependencies(
    mock_repo_class, mock_create_provider, mock_semantic_class, container
):
    """Test that get_semantic_service wires repository + embedding provider."""
    mock_repo = AsyncMock()
    mock_provider = MagicMock()
    mock_semantic = MagicMock()

    mock_repo_class.return_value = mock_repo
    mock_create_provider.return_value = mock_provider
    mock_semantic_class.return_value = mock_semantic

    service = await container.get_semantic_service()

    assert service is mock_semantic
    mock_semantic_class.assert_called_once_with(
        embedding_provider=mock_provider,
        repository=mock_repo,
    )


# ============================================================================
# DAG Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.SubstrateDAG")
@patch("core.di.container.SemanticService")
@patch("core.di.container.create_embedding_provider")
@patch("core.di.container.SubstrateRepository")
async def test_get_dag_wires_dependencies(
    mock_repo_class,
    mock_create_provider,
    mock_semantic_class,
    mock_dag_class,
    container,
):
    """Test that get_dag wires repository + semantic service."""
    mock_repo = AsyncMock()
    mock_provider = MagicMock()
    mock_semantic = MagicMock()
    mock_dag = MagicMock()

    mock_repo_class.return_value = mock_repo
    mock_create_provider.return_value = mock_provider
    mock_semantic_class.return_value = mock_semantic
    mock_dag_class.return_value = mock_dag

    dag = await container.get_dag()

    assert dag is mock_dag
    mock_dag_class.assert_called_once_with(
        repository=mock_repo,
        semantic_service=mock_semantic,
    )


# ============================================================================
# Service Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.MemorySubstrateService")
@patch("core.di.container.SubstrateDAG")
@patch("core.di.container.SemanticService")
@patch("core.di.container.create_embedding_provider")
@patch("core.di.container.SubstrateRepository")
async def test_get_service_wires_all_dependencies(
    mock_repo_class,
    mock_create_provider,
    mock_semantic_class,
    mock_dag_class,
    mock_service_class,
    container,
):
    """Test that get_service wires all dependencies."""
    mock_repo = AsyncMock()
    mock_provider = MagicMock()
    mock_semantic = MagicMock()
    mock_dag = MagicMock()
    mock_service = MagicMock()

    mock_repo_class.return_value = mock_repo
    mock_create_provider.return_value = mock_provider
    mock_semantic_class.return_value = mock_semantic
    mock_dag_class.return_value = mock_dag
    mock_service_class.return_value = mock_service

    service = await container.get_service()

    assert service is mock_service
    mock_service_class.assert_called_once_with(
        repository=mock_repo,
        embedding_provider=mock_provider,
        semantic_service=mock_semantic,
        dag=mock_dag,
    )


# ============================================================================
# Shutdown Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.SubstrateRepository")
async def test_close_disconnects_repository(mock_repo_class, container):
    """Test that close() disconnects repository."""
    mock_repo = AsyncMock()
    mock_repo_class.return_value = mock_repo

    await container.get_repository()
    await container.close()

    mock_repo.disconnect.assert_called_once()
    assert container._repository is None


@pytest.mark.asyncio
async def test_close_handles_no_repository(container):
    """Test that close() handles case where repository was never created."""
    # Should not raise exception
    await container.close()


@pytest.mark.asyncio
@patch("core.di.container.SubstrateRepository")
async def test_close_handles_disconnect_failure(mock_repo_class, container):
    """Test that close() handles disconnect failures."""
    mock_repo = AsyncMock()
    mock_repo.disconnect.side_effect = Exception("Disconnect failed")
    mock_repo_class.return_value = mock_repo

    await container.get_repository()

    with pytest.raises(DIContainerError, match="Failed to close container"):
        await container.close()


# ============================================================================
# Thread Safety Tests
# ============================================================================


@pytest.mark.asyncio
@patch("core.di.container.SubstrateRepository")
async def test_concurrent_get_repository_creates_single_instance(mock_repo_class):
    """Test that concurrent calls to get_repository create only one instance."""
    import asyncio

    mock_repo = AsyncMock()
    mock_repo_class.return_value = mock_repo

    container = MemorySubstrateContainer(
        {"database_url": "postgresql://localhost/test"}
    )

    # Simulate concurrent calls
    results = await asyncio.gather(
        container.get_repository(),
        container.get_repository(),
        container.get_repository(),
    )

    # All should return same instance
    assert results[0] is results[1] is results[2]

    # Repository should be created only once
    assert mock_repo_class.call_count == 1
    assert mock_repo.connect.call_count == 1


# ============================================================================
# DORA FOOTER
# ============================================================================
# tags: ["container", "dependency-injection", "testing", "unit-tests"]
# keywords: ["container", "dag", "di", "embedding", "memory", "repository", "semantic"]
# last_modified: "2026-01-22T20:00:00Z"
# ============================================================================
