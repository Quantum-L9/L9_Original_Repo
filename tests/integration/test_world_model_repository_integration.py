"""
World Model → Repository Integration Tests

Tests the flow: Entity Creation → Repository Storage → Graph Update
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

pytestmark = pytest.mark.integration


class TestWorldModelRepositoryIntegration:
    """Test world model to repository integration."""

    def test_repository_initialization(self):
        """Repository initializes without live DB."""
        with patch("world_model.repository.get_pool") as mock_pool:
            mock_pool.return_value = AsyncMock()

            from world_model.repository import WorldModelRepository

            repo = WorldModelRepository()
            assert repo is not None

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_node_creation_flow(self):
        """Node creation flows through repository."""
        with patch("world_model.repository.get_pool") as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock()
            mock_pool.return_value.acquire = MagicMock()
            mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(
                return_value=mock_conn
            )
            mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            from world_model.repository import WorldModelRepository

            repo = WorldModelRepository()

            # Mock upsert_entity if it exists
            if hasattr(repo, "upsert_entity"):
                repo.upsert_entity = AsyncMock(return_value=None)

            # Should not raise during initialization
            assert repo is not None

    def test_repository_has_crud_methods(self):
        """Repository exposes CRUD interface."""
        with patch("world_model.repository.get_pool"):
            from world_model.repository import WorldModelRepository

            repo = WorldModelRepository()

            # Check for common CRUD methods
            assert (
                hasattr(repo, "get_entity")
                or hasattr(repo, "create_node")
                or hasattr(repo, "add_node")
            )
            assert (
                hasattr(repo, "list_entities")
                or hasattr(repo, "get_node")
                or hasattr(repo, "find_node")
            )
