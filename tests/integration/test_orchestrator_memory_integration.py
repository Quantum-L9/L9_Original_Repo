"""
Orchestrator → Memory Integration Tests

Tests the flow: Orchestrator Action → Memory Write → Verification
"""

from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


class MockSubstrateService:
    """Mock substrate for integration testing."""

    def __init__(self):
        self.packets = []

    async def write_packet(self, packet):
        self.packets.append(packet)
        return {"packet_id": str(uuid4())}

    async def search_packets(self, **kwargs):
        return self.packets


class TestOrchestratorMemoryIntegration:
    """Test orchestrator to memory integration."""

    @pytest.mark.asyncio
    async def test_memory_orchestrator_writes_packet(self):
        """Memory orchestrator can write to substrate."""
        from orchestrators.memory.interface import (MemoryOperation,
                                                    MemoryRequest)
        from orchestrators.memory.orchestrator import MemoryOrchestrator

        orchestrator = MemoryOrchestrator()

        request = MemoryRequest(
            operation=MemoryOperation.BATCH_WRITE,
            packets=[{"type": "test", "data": {"key": "value"}}],
        )

        # Execute should succeed
        response = await orchestrator.execute(request)

        assert response.success is True
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_housekeeping_runs(self):
        """Housekeeping module executes without error."""
        from orchestrators.memory.housekeeping import Housekeeping

        housekeeping = Housekeeping()

        # Should not raise
        result = await housekeeping.run()

        assert result is not None
        assert result.get("success") is True

    def test_memory_orchestrator_interface(self):
        """Memory orchestrator has required interface."""
        from orchestrators.memory import interface

        assert interface is not None
        assert hasattr(interface, "IMemoryOrchestrator")
