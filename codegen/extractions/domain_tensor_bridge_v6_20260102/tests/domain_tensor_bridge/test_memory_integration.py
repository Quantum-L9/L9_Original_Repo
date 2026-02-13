#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for MemoryBridge - Redis/Postgres/Neo4j/HyperGraphDB behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from domain_tensor_bridge.memory_bridge import MemoryBridge, EpisodicEvent, Node


@pytest.fixture
def memory_bridge():
    """Create memory bridge with mocked substrate."""
    substrate = AsyncMock()
    substrate.redis_get = AsyncMock(return_value={"cached": True})
    substrate.redis_set = AsyncMock(return_value=True)
    substrate.query_events = AsyncMock(
        return_value=[
            {
                "id": "e1",
                "timestamp": "2026-01-02",
                "type": "test",
                "payload": {},
                "metadata": {},
            }
        ]
    )
    substrate.cypher_query = AsyncMock(
        return_value=[{"id": "n1", "type": "entity", "properties": {}, "edges": []}]
    )

    return MemoryBridge(substrate_service=substrate)


class TestRedisReadWrite:
    """Tests for Redis (working memory) operations."""

    @pytest.mark.asyncio
    async def test_get_working_memory(self, memory_bridge):
        """Test reading from working memory."""
        result = await memory_bridge.get_working_memory("test_key")

        assert result is not None
        assert result.get("cached") is True

    @pytest.mark.asyncio
    async def test_set_working_memory(self, memory_bridge):
        """Test writing to working memory."""
        result = await memory_bridge.set_working_memory(
            "test_key",
            {"value": "test"},
            ttl_seconds=60,
        )

        assert result is True


class TestPostgresQuery:
    """Tests for Postgres (episodic memory) operations."""

    @pytest.mark.asyncio
    async def test_query_episodic_memory(self, memory_bridge):
        """Test querying episodic memory."""
        events = await memory_bridge.query_episodic_memory({"entity_id": "test"})

        assert len(events) == 1
        assert isinstance(events[0], EpisodicEvent)


class TestNeo4jQuery:
    """Tests for Neo4j (semantic graph) operations."""

    @pytest.mark.asyncio
    async def test_query_semantic_graph(self, memory_bridge):
        """Test querying semantic graph."""
        nodes = await memory_bridge.query_semantic_graph("MATCH (n) RETURN n LIMIT 1")

        assert len(nodes) == 1
        assert isinstance(nodes[0], Node)


class TestHyperGraphDBQuery:
    """Tests for HyperGraphDB (causal graph) operations."""

    @pytest.mark.asyncio
    async def test_query_causal_graph(self, memory_bridge):
        """Test querying causal graph."""
        result = await memory_bridge.query_causal_graph("entity_123", depth=2)

        assert "nodes" in result
        assert "edges" in result
