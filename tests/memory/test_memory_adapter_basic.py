"""
L9 Tests - Memory Adapter Basic Behavior

Expectations:
- Uses the real memory adapter module from the repo.
- Does NOT hit real DB; uses stub or in-memory mock.
- Verifies basic write_packet contract and error handling.
"""

import sys
from pathlib import Path

# Add project root to path before any imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

# Adapted import to match actual repo path - use absolute path
# Use absolute path to project root
abs_project_root = str(Path(__file__).parent.parent.parent.absolute())
if abs_project_root not in sys.path:
    sys.path.insert(0, abs_project_root)

from clients.memory_client import MemoryClient, PacketWriteResult


class FakeResponse:
    """Fake httpx response for testing."""

    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.mark.asyncio
async def test_memory_write_packet_contract():
    """Test that write_packet sends correct request and parses response."""
    client = MemoryClient(base_url="http://test:8080")

    fake_packet_id = uuid4()
    fake_response = FakeResponse(
        status_code=200,
        json_data={
            "status": "ok",
            "packet_id": str(fake_packet_id),
            "written_tables": ["packets", "embeddings"],
            "error_message": None,
        },
    )

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = fake_response
        mock_get_client.return_value = mock_http_client

        result = await client.write_packet(
            packet_type="test_event",
            payload={"data": "test_value"},
            metadata={"source": "test"},
        )

        # Verify the write was called
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "/api/v1/memory/packet" in call_args[0][0]

        # Verify result structure
        assert isinstance(result, PacketWriteResult)
        assert result.status == "ok"
        assert result.packet_id == fake_packet_id
        assert "packets" in result.written_tables


@pytest.mark.asyncio
async def test_memory_client_context_manager():
    """Test that MemoryClient works as async context manager."""
    async with MemoryClient(base_url="http://test:8080") as client:
        assert client is not None
        assert isinstance(client, MemoryClient)


@pytest.mark.asyncio
async def test_memory_client_handles_errors_gracefully():
    """Test that errors are properly propagated."""
    client = MemoryClient(base_url="http://test:8080")

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = Exception("Connection refused")
        mock_get_client.return_value = mock_http_client

        with pytest.raises(Exception) as exc_info:
            await client.write_packet(
                packet_type="test",
                payload={"key": "value"},
            )

        assert "Connection refused" in str(exc_info.value)
