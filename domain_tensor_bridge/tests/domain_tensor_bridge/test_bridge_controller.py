#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for AgentController - happy path packet dispatch and routing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from domain_tensor_bridge.agent_controller import AgentController, process_packet
from core.schemas import PacketEnvelope, PacketKind


@pytest.fixture
def mock_packet():
    """Create mock packet."""
    return PacketEnvelope(
        source_id="test_agent",
        kind=PacketKind.REASONING,
        payload={"entity_id": "test_123", "action": "test"},
    )


@pytest.fixture
def controller():
    """Create controller with mocked dependencies."""
    reasoning = AsyncMock()
    reasoning.execute = AsyncMock(return_value={"confidence": 0.9})
    
    router = AsyncMock()
    router.validate = AsyncMock(return_value=MagicMock(valid=True, errors=[]))
    router.route = AsyncMock(return_value={"routed": True})
    
    governance = AsyncMock()
    governance.check = AsyncMock(return_value=MagicMock(approved=True))
    
    return AgentController(
        reasoning_engine=reasoning,
        packet_router=router,
        governance_bridge=governance,
    )


class TestAgentController:
    """Tests for AgentController."""
    
    @pytest.mark.asyncio
    async def test_happy_path_packet_dispatch(self, controller, mock_packet):
        """Test successful packet processing."""
        await controller.initialize()
        
        result = await controller.process_packet(mock_packet)
        
        assert result is not None
        assert result.source_id == "domain_tensor_bridge"
        assert result.kind == PacketKind.DECISION
    
    @pytest.mark.asyncio
    async def test_routing_decision(self, controller, mock_packet):
        """Test routing is called correctly."""
        await controller.initialize()
        
        await controller.process_packet(mock_packet)
        
        controller.packet_router.validate.assert_called_once()
        controller.packet_router.route.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_governance_check(self, controller, mock_packet):
        """Test governance is checked."""
        await controller.initialize()
        
        await controller.process_packet(mock_packet)
        
        controller.governance_bridge.check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_failure(self, controller, mock_packet):
        """Test validation failure handling."""
        controller.packet_router.validate = AsyncMock(
            return_value=MagicMock(valid=False, errors=["Missing field"])
        )
        await controller.initialize()
        
        with pytest.raises(ValueError):
            await controller.process_packet(mock_packet)
    
    @pytest.mark.asyncio
    async def test_governance_blocked(self, controller, mock_packet):
        """Test governance blocking."""
        controller.governance_bridge.check = AsyncMock(
            return_value=MagicMock(approved=False, reason="Blocked by policy")
        )
        await controller.initialize()
        
        result = await controller.process_packet(mock_packet)
        
        assert result.payload.get("status") == "blocked"


class TestProcessPacketFunction:
    """Tests for convenience function."""
    
    @pytest.mark.asyncio
    async def test_process_packet_creates_controller(self, mock_packet):
        """Test convenience function creates controller."""
        # This would need mocking of the controller creation
        pass


