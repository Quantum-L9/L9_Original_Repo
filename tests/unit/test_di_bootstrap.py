"""
Tests for DI Container Bootstrap Functionality

Tests the bootstrap_di_container() function and global container management.
"""

from unittest.mock import AsyncMock, patch

import pytest

from core.di.container import (
    DIContainer,
    bootstrap_di_container,
    get_global_di_container,
    set_global_di_container,
)


class TestBootstrapDIContainer:
    """Test bootstrap_di_container() function."""

    @pytest.mark.asyncio
    async def test_bootstrap_creates_container(self):
        """Test that bootstrap creates a DIContainer instance."""
        with patch("memory.postgres_client.PostgresClient") as mock_pg:
            mock_pg_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_pg_instance.connect = AsyncMock()

            with patch(
                "memory.substrate_service.create_substrate_service"
            ) as mock_substrate:
                mock_substrate.return_value = AsyncMock()

                container = await bootstrap_di_container(
                    database_url="postgresql://localhost/test"
                )

                assert isinstance(container, DIContainer)
                assert len(container._bindings) > 0

    @pytest.mark.asyncio
    async def test_bootstrap_registers_postgres_client(self):
        """Test that bootstrap registers PostgresClient."""
        with patch("memory.postgres_client.PostgresClient") as mock_pg:
            mock_pg_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_pg_instance.connect = AsyncMock()

            with patch(
                "memory.substrate_service.create_substrate_service"
            ) as mock_substrate:
                mock_substrate.return_value = AsyncMock()

                container = await bootstrap_di_container(
                    database_url="postgresql://localhost/test"
                )

                # Check that PostgresClient is registered
                from memory.postgres_client import PostgresClient

                assert container.has_binding(PostgresClient)

    @pytest.mark.asyncio
    async def test_bootstrap_registers_memory_substrate(self):
        """Test that bootstrap registers MemorySubstrateService."""
        with patch("memory.postgres_client.PostgresClient") as mock_pg:
            mock_pg_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_pg_instance.connect = AsyncMock()

            with patch(
                "memory.substrate_service.create_substrate_service"
            ) as mock_substrate:
                mock_substrate.return_value = AsyncMock()

                container = await bootstrap_di_container(
                    database_url="postgresql://localhost/test"
                )

                # Check that MemorySubstrateService is registered
                from memory.substrate_service import MemorySubstrateService

                assert container.has_binding(MemorySubstrateService)

    @pytest.mark.asyncio
    async def test_bootstrap_handles_postgres_connection_failure(self):
        """Test that bootstrap raises ConnectionError on Postgres failure."""
        with patch("memory.postgres_client.PostgresClient") as mock_pg:
            mock_pg_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_pg_instance.connect = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            with pytest.raises(ConnectionError, match="Failed to connect to Postgres"):
                await bootstrap_di_container(database_url="postgresql://localhost/test")

    @pytest.mark.asyncio
    async def test_bootstrap_handles_substrate_init_failure(self):
        """Test that bootstrap raises RuntimeError on substrate init failure."""
        with patch("memory.postgres_client.PostgresClient") as mock_pg:
            mock_pg_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_pg_instance.connect = AsyncMock()

            with patch(
                "memory.substrate_service.create_substrate_service"
            ) as mock_substrate:
                mock_substrate.side_effect = Exception("Substrate init failed")

                with pytest.raises(
                    RuntimeError, match="Failed to initialize memory substrate"
                ):
                    await bootstrap_di_container(
                        database_url="postgresql://localhost/test"
                    )

    @pytest.mark.asyncio
    async def test_bootstrap_uses_env_variables(self):
        """Test that bootstrap falls back to environment variables."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "postgresql://env/db"

            with patch("memory.postgres_client.PostgresClient") as mock_pg:
                mock_pg_instance = AsyncMock()
                mock_pg.return_value = mock_pg_instance
                mock_pg_instance.connect = AsyncMock()

                with patch(
                    "memory.substrate_service.create_substrate_service"
                ) as mock_substrate:
                    mock_substrate.return_value = AsyncMock()

                    await bootstrap_di_container()

                    # Verify env var was checked
                    mock_getenv.assert_called()


class TestGlobalContainerManagement:
    """Test global container management functions."""

    def test_get_global_container_returns_none_initially(self):
        """Test that get_global_di_container() returns None before set."""
        # Reset global state
        from core.di import container as container_module

        container_module._global_di_container = None

        result = get_global_di_container()
        assert result is None

    def test_set_and_get_global_container(self):
        """Test setting and getting global container."""
        test_container = DIContainer()

        set_global_di_container(test_container)
        result = get_global_di_container()

        assert result is test_container

    def test_set_global_container_overwrites_previous(self):
        """Test that set_global_di_container() overwrites previous value."""
        container1 = DIContainer()
        container2 = DIContainer()

        set_global_di_container(container1)
        set_global_di_container(container2)

        result = get_global_di_container()
        assert result is container2
        assert result is not container1


class TestBootstrapIntegration:
    """Integration tests for bootstrap with real components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_bootstrap_full_integration(self):
        """Test full bootstrap integration (requires real DB)."""
        # Skip if no test database available
        pytest.skip("Requires test database configuration")

        container = await bootstrap_di_container(
            database_url="postgresql://localhost/l9_test"
        )

        try:
            # Verify services are registered
            assert len(container._bindings) > 0

            # Verify can resolve services
            from memory.substrate_service import MemorySubstrateService

            service = container.resolve(MemorySubstrateService)
            assert service is not None

        finally:
            # Cleanup
            container.clear_all()
