"""
L9 Memory Client Tests
======================

Tests for memory client with mocked HTTP.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.decorators import must_stay_async

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from clients.memory_client import MemoryClient, PacketEnvelopeIn
except ImportError as e:
    pytest.skip(f"Could not import clients.memory_client: {e}", allow_module_level=True)


# =============================================================================
# Test: Client initialization
# =============================================================================


def test_client_initialization():
    """
    Contract: MemoryClient can be instantiated.
    """
    client = MemoryClient(base_url="http://test:8080")
    assert client is not None
    assert client.base_url == "http://test:8080"


# =============================================================================
# Test: Write packet mock
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_write_packet_mock():
    """
    Contract: MemoryClient can write packets (mocked HTTP).
    """
    client = MemoryClient(base_url="http://test:8080")

    packet = PacketEnvelopeIn(
        packet_type="test.event",
        payload={"message": "test"},
    )

    # Mock httpx.AsyncClient
    with patch("clients.memory_client.httpx.AsyncClient") as mock_client_class:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"packet_id": "test-123", "status": "ok"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.write_packet(packet)

        assert result is not None
        # Verify HTTP call was made
        mock_client.post.assert_called_once()


# =============================================================================
# Test: Search packets mock
# =============================================================================


@pytest.mark.asyncio
async def test_search_packets_mock():
    """
    Contract: MemoryClient can search packets (mocked HTTP).
    """
    client = MemoryClient(base_url="http://test:8080")

    # Mock httpx.AsyncClient
    with patch("clients.memory_client.httpx.AsyncClient") as mock_client_class:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "hits": [{"embedding_id": "e1", "score": 0.9, "payload": {}}],
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.semantic_search(query="test", top_k=10)

        assert result is not None
        assert hasattr(result, "hits")
        # Verify HTTP call was made
        mock_client.post.assert_called_once()


# =============================================================================
# Test: All 9 Client SDK Methods (End-to-End Verification)
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_all_client_methods_mocked():
    """
    Contract: All 9 MemoryClient methods work with mocked HTTP.
    Tests: write_packet, semantic_search, hybrid_search, fetch_lineage,
           fetch_thread, fetch_facts, fetch_insights, run_gc, get_gc_stats
    """
    client = MemoryClient(base_url="http://test:8080")

    with patch("clients.memory_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 1. write_packet
        from uuid import uuid4

        test_packet_id = str(uuid4())
        mock_response.json.return_value = {
            "packet_id": test_packet_id,
            "status": "ok",
            "written_tables": [],
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await client.write_packet(
            packet_type="test.event", payload={"msg": "test"}
        )
        assert result.packet_id is not None
        assert result.status == "ok"

        # 2. semantic_search
        mock_response.json.return_value = {"query": "test", "hits": [], "total": 0}
        result = await client.semantic_search(query="test", top_k=10)
        assert result.query == "test"
        assert isinstance(result.hits, list)

        # 3. hybrid_search
        mock_response.json.return_value = {"query": "test", "results": []}
        result = await client.hybrid_search("test", filters={"packet_type": "event"})
        assert "query" in result

        # 4. fetch_lineage
        mock_response.json.return_value = {"packet_id": "p1", "chain": [], "depth": 0}
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await client.fetch_lineage("p1", direction="ancestors")
        assert "packet_id" in result

        # 5. fetch_thread
        mock_response.json.return_value = [{"packet_id": "p1"}]
        result = await client.fetch_thread("t1")
        assert isinstance(result, list)

        # 6. fetch_facts
        mock_response.json.return_value = [{"fact_id": "f1", "subject": "test"}]
        result = await client.fetch_facts(subject="test")
        assert isinstance(result, list)

        # 7. fetch_insights
        mock_response.json.return_value = [
            {"insight_id": "i1", "insight_type": "conclusion"}
        ]  # Client returns list directly
        result = await client.fetch_insights()
        assert isinstance(result, list)

        # 8. run_gc
        mock_response.json.return_value = {"status": "ok", "cleaned": {}}
        result = await client.run_gc()
        assert "status" in result

        # 9. get_gc_stats
        mock_response.json.return_value = {"pending": {}, "totals": {}}
        result = await client.get_gc_stats()
        assert "pending" in result

        # Verify all methods were called
        assert mock_client.post.call_count >= 3  # write, semantic, hybrid, gc
        assert (
            mock_client.get.call_count >= 5
        )  # lineage, thread, facts, insights, gc_stats
