#!/usr/bin/env python3
"""
Tests for PacketRouter - routing by type and domain.
"""

from unittest.mock import AsyncMock

import pytest

from core.schemas import PacketEnvelope, PacketKind
from domain_tensor_bridge.packet_router import PacketRouter


@pytest.fixture
def router():
    """Create packet router."""
    return PacketRouter()


@pytest.fixture
def mock_packet():
    """Create mock packet."""
    return PacketEnvelope(
        source_id="test_domain_agent",
        kind=PacketKind.REASONING,
        payload={"test": True},
    )


class TestRouteByType:
    """Tests for type-based routing."""

    @pytest.mark.asyncio
    async def test_route_by_packet_kind(self, router, mock_packet):
        """Test routing by packet kind."""
        handler = AsyncMock()
        router.register_handler(PacketKind.REASONING, handler)

        handler_name = await router.route_packet(mock_packet)

        assert handler_name == "REASONING"

    @pytest.mark.asyncio
    async def test_get_handler_for_type(self, router):
        """Test getting handler by type."""
        handler = AsyncMock()
        router.register_handler(PacketKind.REASONING, handler)

        result = router.get_handler_for_type("REASONING")

        assert result == handler


class TestRouteByDomain:
    """Tests for domain-based routing."""

    @pytest.mark.asyncio
    async def test_route_by_domain(self, router):
        """Test routing by domain prefix."""
        handler = AsyncMock()
        router.register_domain_handler("plastos", handler)

        packet = PacketEnvelope(
            source_id="plastos_agent",
            kind=PacketKind.TOOL_CALL,  # Different kind
            payload={},
        )

        handler_name = await router.route_packet(packet)

        assert handler_name == "domain:plastos"

    @pytest.mark.asyncio
    async def test_fallback_routing(self, router, mock_packet):
        """Test fallback handler is used."""
        fallback = AsyncMock()
        router.set_fallback_handler(fallback)

        handler_name = await router.route_packet(mock_packet)

        assert handler_name == "fallback"
