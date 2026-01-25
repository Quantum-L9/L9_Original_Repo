"""
Unit tests for async DI container.

Tests verify:
1. Container initialization/shutdown lifecycle
2. Dependency getters raise before init
3. Singleton pattern works
4. Idempotent initialization
"""

from unittest.mock import AsyncMock, patch

import pytest

from config.di_async_config import (
    AsyncDIContainer,
    get_async_di_container,
    reset_async_di_container,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fresh_container() -> AsyncDIContainer:
    """Provide a fresh AsyncDIContainer instance."""
    reset_async_di_container()
    return get_async_di_container()


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Mock Redis client."""
    client = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_neo4j_client() -> AsyncMock:
    """Mock Neo4j client."""
    client = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_memory_substrate() -> AsyncMock:
    """Mock memory substrate service."""
    service = AsyncMock()
    service.shutdown = AsyncMock()
    return service


# ============================================================================
# TESTS: Container Initialization
# ============================================================================


class TestAsyncDIContainerInitialization:
    """Test async DI container initialization."""

    def test_container_not_initialized_by_default(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that container is not initialized on creation."""
        assert not fresh_container.is_initialized

    @pytest.mark.asyncio
    async def test_container_initialization(
        self,
        fresh_container: AsyncDIContainer,
        mock_redis_client: AsyncMock,
        mock_neo4j_client: AsyncMock,
        mock_memory_substrate: AsyncMock,
    ) -> None:
        """Test successful container initialization."""
        with (
            patch(
                "config.di_async_config.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "config.di_async_config.get_neo4j_client",
                return_value=mock_neo4j_client,
            ),
            patch(
                "config.di_async_config.get_service",
                return_value=mock_memory_substrate,
            ),
        ):
            await fresh_container.initialize()
            assert fresh_container.is_initialized

    @pytest.mark.asyncio
    async def test_container_idempotent_initialization(
        self,
        fresh_container: AsyncDIContainer,
        mock_redis_client: AsyncMock,
        mock_neo4j_client: AsyncMock,
        mock_memory_substrate: AsyncMock,
    ) -> None:
        """Test that initializing twice is safe."""
        with (
            patch(
                "config.di_async_config.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "config.di_async_config.get_neo4j_client",
                return_value=mock_neo4j_client,
            ),
            patch(
                "config.di_async_config.get_service",
                return_value=mock_memory_substrate,
            ),
        ):
            await fresh_container.initialize()
            await fresh_container.initialize()  # Should not raise
            assert fresh_container.is_initialized


# ============================================================================
# TESTS: Container Shutdown
# ============================================================================


class TestAsyncDIContainerShutdown:
    """Test async DI container shutdown."""

    @pytest.mark.asyncio
    async def test_container_shutdown(
        self,
        fresh_container: AsyncDIContainer,
        mock_redis_client: AsyncMock,
        mock_neo4j_client: AsyncMock,
        mock_memory_substrate: AsyncMock,
    ) -> None:
        """Test successful container shutdown."""
        with (
            patch(
                "config.di_async_config.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "config.di_async_config.get_neo4j_client",
                return_value=mock_neo4j_client,
            ),
            patch(
                "config.di_async_config.get_service",
                return_value=mock_memory_substrate,
            ),
        ):
            await fresh_container.initialize()
            await fresh_container.shutdown()
            assert not fresh_container.is_initialized

    @pytest.mark.asyncio
    async def test_container_shutdown_when_not_initialized(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that shutdown is safe when container not initialized."""
        await fresh_container.shutdown()  # Should not raise
        assert not fresh_container.is_initialized


# ============================================================================
# TESTS: Dependency Getters
# ============================================================================


class TestAsyncDIDependencyGetters:
    """Test dependency getter methods."""

    @pytest.mark.asyncio
    async def test_get_cache_client_before_init_raises(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that getting cache client before init raises error."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await fresh_container.get_cache_client()

    @pytest.mark.asyncio
    async def test_get_neo4j_client_before_init_raises(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that getting Neo4j client before init raises error."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await fresh_container.get_neo4j_client()

    @pytest.mark.asyncio
    async def test_get_memory_substrate_before_init_raises(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that getting memory substrate before init raises error."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await fresh_container.get_memory_substrate()

    @pytest.mark.asyncio
    async def test_get_cache_client_after_init(
        self,
        fresh_container: AsyncDIContainer,
        mock_redis_client: AsyncMock,
        mock_neo4j_client: AsyncMock,
        mock_memory_substrate: AsyncMock,
    ) -> None:
        """Test that cache client is accessible after init."""
        with (
            patch(
                "config.di_async_config.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "config.di_async_config.get_neo4j_client",
                return_value=mock_neo4j_client,
            ),
            patch(
                "config.di_async_config.get_service",
                return_value=mock_memory_substrate,
            ),
        ):
            await fresh_container.initialize()
            client = await fresh_container.get_cache_client()
            assert client is mock_redis_client


# ============================================================================
# TESTS: Global Singleton
# ============================================================================


class TestAsyncDIGlobalSingleton:
    """Test global async DI container singleton."""

    def test_get_async_di_container_singleton(self) -> None:
        """Test that get_async_di_container returns same instance."""
        reset_async_di_container()

        container1 = get_async_di_container()
        container2 = get_async_di_container()

        assert container1 is container2

    def test_reset_async_di_container(self) -> None:
        """Test that reset creates new instance."""
        container1 = get_async_di_container()
        reset_async_di_container()
        container2 = get_async_di_container()

        assert container1 is not container2


# ============================================================================
# TESTS: Error Handling
# ============================================================================


class TestAsyncDIErrorHandling:
    """Test error handling in async DI container."""

    @pytest.mark.asyncio
    async def test_initialization_error_propagates(
        self, fresh_container: AsyncDIContainer
    ) -> None:
        """Test that initialization errors propagate."""
        with (
            patch(
                "config.di_async_config.get_redis_client",
                side_effect=RuntimeError("Redis init failed"),
            ),
            pytest.raises(RuntimeError, match="Redis init failed"),
        ):
            await fresh_container.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_error_logged_not_raised(
        self,
        fresh_container: AsyncDIContainer,
        mock_redis_client: AsyncMock,
        mock_neo4j_client: AsyncMock,
        mock_memory_substrate: AsyncMock,
    ) -> None:
        """Test that shutdown errors are logged but not raised."""
        # Mock a failing shutdown
        mock_memory_substrate.shutdown = AsyncMock(
            side_effect=RuntimeError("Shutdown failed")
        )

        with (
            patch(
                "config.di_async_config.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "config.di_async_config.get_neo4j_client",
                return_value=mock_neo4j_client,
            ),
            patch(
                "config.di_async_config.get_service",
                return_value=mock_memory_substrate,
            ),
        ):
            await fresh_container.initialize()
            # Should not raise despite shutdown error
            await fresh_container.shutdown()
            assert not fresh_container.is_initialized
