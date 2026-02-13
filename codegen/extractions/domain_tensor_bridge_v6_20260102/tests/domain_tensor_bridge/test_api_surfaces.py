#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for API surfaces - process_packet and status endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from domain_tensor_bridge.agent_controller import AgentController
from l9.core.schemas import PacketEnvelope, PacketKind


@pytest.fixture
def controller():
    """Create controller for API testing."""
    return AgentController()


class TestProcessPacketEndpoint:
    """Tests for process_packet API."""

    @pytest.mark.asyncio
    async def test_valid_packet_processed(self, controller):
        """Test valid packet is processed."""
        await controller.initialize()

        packet = PacketEnvelope(
            source_id="api_client",
            kind=PacketKind.REASONING,
            payload={"test": True},
        )

        result = await controller.process_packet(packet)

        assert result is not None
        assert result.source_id == "domain_tensor_bridge"

    @pytest.mark.asyncio
    async def test_response_format(self, controller):
        """Test response has correct format."""
        await controller.initialize()

        packet = PacketEnvelope(
            source_id="api_client",
            kind=PacketKind.REASONING,
            payload={"test": True},
        )

        result = await controller.process_packet(packet)

        assert hasattr(result, "source_id")
        assert hasattr(result, "kind")
        assert hasattr(result, "payload")


class TestStatusEndpoint:
    """Tests for status/health endpoint."""

    @pytest.mark.asyncio
    async def test_initialized_status(self, controller):
        """Test status reflects initialization."""
        assert not controller._initialized

        await controller.initialize()

        assert controller._initialized
