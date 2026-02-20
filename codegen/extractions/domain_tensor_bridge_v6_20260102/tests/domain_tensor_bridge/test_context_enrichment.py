#!/usr/bin/env python3
"""
Tests for ContextEnricher - world model query and context building.
"""

from unittest.mock import AsyncMock

import pytest
from l9.core.schemas import PacketEnvelope, PacketKind

from domain_bridge.context_enricher import ContextEnricher, EnrichedContext
from domain_bridge.memory_bridge import EpisodicEvent
from domain_bridge.world_model_bridge import CausalFactor


@pytest.fixture
def mock_packet():
    """Create mock packet."""
    return PacketEnvelope(
        source_id="test_agent",
        kind=PacketKind.REASONING,
        payload={"entity_id": "test_123"},
    )


@pytest.fixture
def enricher():
    """Create context enricher with mocks."""
    world_model = AsyncMock()
    world_model.query_causal_factors = AsyncMock(
        return_value=[CausalFactor("cf_1", "influence", 0.8, "positive")]
    )

    memory = AsyncMock()
    memory.query_episodic_memory = AsyncMock(
        return_value=[EpisodicEvent("e1", "2026-01-02", "test", {})]
    )

    return ContextEnricher(
        world_model_bridge=world_model,
        memory_bridge=memory,
    )


class TestWorldModelQuery:
    """Tests for world model querying."""

    @pytest.mark.asyncio
    async def test_causal_factors_queried(self, enricher, mock_packet):
        """Test causal factors are queried."""
        context = await enricher.enrich_context(mock_packet)

        assert len(context.causal_factors) == 1
        enricher.world_model.query_causal_factors.assert_called_once_with("test_123")

    @pytest.mark.asyncio
    async def test_episodic_memory_queried(self, enricher, mock_packet):
        """Test episodic memory is queried."""
        context = await enricher.enrich_context(mock_packet)

        assert len(context.episodic_context) == 1


class TestContextBuilding:
    """Tests for context construction."""

    @pytest.mark.asyncio
    async def test_enriched_context_structure(self, enricher, mock_packet):
        """Test enriched context has correct structure."""
        context = await enricher.enrich_context(mock_packet)

        assert isinstance(context, EnrichedContext)
        assert context.original_payload == mock_packet.payload

    @pytest.mark.asyncio
    async def test_without_dependencies(self, mock_packet):
        """Test enricher works without dependencies."""
        enricher = ContextEnricher()

        context = await enricher.enrich_context(mock_packet)

        assert context.original_payload == mock_packet.payload
        assert len(context.causal_factors) == 0
