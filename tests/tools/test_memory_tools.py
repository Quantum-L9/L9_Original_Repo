"""
Unit Tests: Memory Tools
========================

Tests for memory substrate tools.

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemorySearch:
    """Tests for memory_search tool."""

    @pytest.mark.asyncio
    async def test_memory_search_success(self):
        """memory_search returns hits on success."""
        from memory.tools import memory_search

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.hits = [
            MagicMock(embedding_id="uuid-1", score=0.95, payload={"text": "test"}),
            MagicMock(embedding_id="uuid-2", score=0.85, payload={"text": "test2"}),
        ]
        mock_client.semantic_search = AsyncMock(return_value=mock_result)

        with patch("memory.tools.get_memory_client", return_value=mock_client):
            result = await memory_search(query="test query", segment="all", limit=10)

        assert result["query"] == "test query"
        assert result["segment"] == "all"
        assert len(result["hits"]) == 2
        assert result["hits"][0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_memory_search_error_returns_empty_hits(self):
        """memory_search returns error with empty hits on failure."""
        from memory.tools import memory_search

        with patch("memory.tools.get_memory_client", side_effect=Exception("Connection failed")):
            result = await memory_search(query="test", segment="all", limit=10)

        assert "error" in result
        assert result["hits"] == []


class TestMemoryWrite:
    """Tests for memory_write tool."""

    @pytest.mark.asyncio
    async def test_memory_write_success(self):
        """memory_write returns packet_id on success."""
        from memory.tools import memory_write

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.packet_id = "uuid-123"
        mock_result.written_tables = ["packets", "embeddings"]
        mock_client.write_packet = AsyncMock(return_value=mock_result)

        with patch("memory.tools.get_memory_client", return_value=mock_client):
            result = await memory_write(
                packet={"packet_type": "test", "payload": {"data": "value"}},
                segment="session",
            )

        assert result["status"] == "success"
        assert result["packet_id"] == "uuid-123"
        assert result["segment"] == "session"

    @pytest.mark.asyncio
    async def test_memory_write_error(self):
        """memory_write returns error status on failure."""
        from memory.tools import memory_write

        with patch("memory.tools.get_memory_client", side_effect=Exception("Write failed")):
            result = await memory_write(packet={}, segment="test")

        assert result["status"] == "error"
        assert "error" in result


class TestMemoryGetPacket:
    """Tests for memory_get_packet tool."""

    @pytest.mark.asyncio
    async def test_memory_get_packet_found(self):
        """memory_get_packet returns packet when found."""
        from memory.tools import memory_get_packet

        mock_substrate = MagicMock()
        mock_packet = MagicMock()
        mock_packet.model_dump = MagicMock(return_value={"id": "uuid-123", "data": "test"})
        mock_substrate.get_packet = AsyncMock(return_value=mock_packet)

        with patch("memory.tools.get_substrate_service", return_value=mock_substrate):
            result = await memory_get_packet(packet_id="uuid-123")

        assert result["status"] == "success"
        assert result["packet"]["id"] == "uuid-123"

    @pytest.mark.asyncio
    async def test_memory_get_packet_not_found(self):
        """memory_get_packet returns not_found when packet missing."""
        from memory.tools import memory_get_packet

        mock_substrate = MagicMock()
        mock_substrate.get_packet = AsyncMock(return_value=None)

        with patch("memory.tools.get_substrate_service", return_value=mock_substrate):
            result = await memory_get_packet(packet_id="nonexistent")

        assert result["status"] == "not_found"
        assert result["packet_id"] == "nonexistent"


class TestMemoryHealthCheck:
    """Tests for memory_health_check tool."""

    @pytest.mark.asyncio
    async def test_memory_health_check_success(self):
        """memory_health_check returns health status."""
        from memory.tools import memory_health_check

        mock_substrate = MagicMock()
        mock_substrate.health_check = AsyncMock(
            return_value={"postgres": "healthy", "redis": "healthy", "neo4j": "healthy"}
        )

        with patch("memory.tools.MemorySubstrateService") as MockService:
            MockService.get_service.return_value = mock_substrate
            result = await memory_health_check()

        assert result["status"] == "success"
        assert "health" in result
