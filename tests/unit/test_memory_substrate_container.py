"""
Unit Tests for MemorySubstrateContainer

Tests container initialization, singleton creation, dependency wiring, and lifecycle.

Version: 1.0.0
Created: 2026-01-24
GMP: 116 (PR #52)
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.di.container import DIContainerError, MemorySubstrateContainer

# ============================================================================
# Mock Classes
# ============================================================================


class MockSubstrateRepository:
    """Mock implementation of SubstrateRepository."""

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False


class MockEmbeddingProvider:
    """Mock implementation of EmbeddingProvider."""

    def __init__(
        self, provider_type: str = "openai", model: str = "test", api_key: str | None = None
    ):
        self.provider_type = provider_type
        self.model = model
        self.api_key = api_key

    @property
    def dimensions(self) -> int:
        return 1536

    async def embed_text(self, text: str) -> list[float]:
        return [0.1] * 1536


class MockSemanticService:
    """Mock implementation of SemanticService."""

    def __init__(self, embedding_provider, repository):
        self.embedding_provider = embedding_provider
        self.repository = repository


class MockSubstrateDAG:
    """Mock implementation of SubstrateDAG."""

    def __init__(self, repository, semantic_service):
        self.repository = repository
        self.semantic_service = semantic_service


class MockMemorySubstrateService:
    """Mock implementation of MemorySubstrateService."""

    def __init__(self, repository, embedding_provider, semantic_service, dag):
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.semantic_service = semantic_service
        self.dag = dag


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_config() -> dict[str, Any]:
    """Valid container configuration."""
    return {
        "database_url": "postgresql://localhost/test",
        "db_pool_size": 5,
        "db_max_overflow": 10,
        "embedding_provider_type": "openai",
        "embedding_model": "text-embedding-3-large",
        "openai_api_key": "test-key",
    }


@pytest.fixture
def minimal_config() -> dict[str, Any]:
    """Minimal container configuration."""
    return {
        "database_url": "postgresql://localhost/test",
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_container_initialization(valid_config):
    """Test that container initializes with valid config."""
    container = MemorySubstrateContainer(valid_config)

    assert container._config == valid_config
    assert container._repository is None
    assert container._embedding_provider is None
    assert container._semantic_service is None
    assert container._dag is None
    assert container._service is None


def test_container_initialization_minimal_config(minimal_config):
    """Test that container initializes with minimal config."""
    container = MemorySubstrateContainer(minimal_config)

    assert container._config["database_url"] == "postgresql://localhost/test"


# ============================================================================
# Repository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_repository_creates_singleton(valid_config):
    """Test that get_repository() returns singleton."""
    container = MemorySubstrateContainer(valid_config)

    # Mock the import
    import sys

    mock_module = MagicMock()
    mock_module.SubstrateRepository = MockSubstrateRepository
    sys.modules["memory.substrate_repository"] = mock_module

    try:
        repo1 = await container.get_repository()
        repo2 = await container.get_repository()

        assert repo1 is repo2
        assert repo1.connected
    finally:
        del sys.modules["memory.substrate_repository"]


@pytest.mark.asyncio
async def test_get_repository_raises_on_missing_database_url():
    """Test that get_repository() raises when database_url missing."""
    container = MemorySubstrateContainer({})

    with pytest.raises(DIContainerError):
        await container.get_repository()


# ============================================================================
# Embedding Provider Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_embedding_provider_creates_singleton(valid_config):
    """Test that get_embedding_provider() returns singleton."""
    container = MemorySubstrateContainer(valid_config)

    # Mock the import
    import sys

    mock_module = MagicMock()
    mock_module.create_embedding_provider = lambda **kwargs: MockEmbeddingProvider(
        **kwargs
    )
    sys.modules["memory.substrate_semantic"] = mock_module

    try:
        provider1 = await container.get_embedding_provider()
        provider2 = await container.get_embedding_provider()

        assert provider1 is provider2
        assert provider1.dimensions == 1536
    finally:
        del sys.modules["memory.substrate_semantic"]


# ============================================================================
# Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close_disconnects_repository(valid_config):
    """Test that close() disconnects repository."""
    container = MemorySubstrateContainer(valid_config)

    # Create mock repository
    mock_repo = MockSubstrateRepository(valid_config["database_url"])
    mock_repo.connected = True
    container._repository = mock_repo

    await container.close()

    assert mock_repo.connected is False
    assert container._repository is None
    assert container._service is None
    assert container._dag is None
    assert container._semantic_service is None
    assert container._embedding_provider is None


@pytest.mark.asyncio
async def test_close_handles_no_repository():
    """Test that close() handles case when no repository exists."""
    container = MemorySubstrateContainer({})

    # Should not raise
    await container.close()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_repository_wraps_exceptions(valid_config):
    """Test that get_repository() wraps exceptions in DIContainerError."""
    container = MemorySubstrateContainer(valid_config)

    # Mock the import to raise
    import sys

    mock_module = MagicMock()
    mock_module.SubstrateRepository = MagicMock(side_effect=ValueError("Test error"))
    sys.modules["memory.substrate_repository"] = mock_module

    try:
        with pytest.raises(DIContainerError, match="Failed to initialize repository"):
            await container.get_repository()
    finally:
        del sys.modules["memory.substrate_repository"]
