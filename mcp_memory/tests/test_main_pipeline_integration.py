"""Tests for main L9 ingestion pipeline integration.

Verifies that MCP memory uses MemorySubstrateService.write_packet() when available,
which routes through the full DAG pipeline (graph sync, fact extraction, etc.).
"""

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.routes.memory_unified import (
    _save_via_direct_db,
    _save_via_main_pipeline,
    save_memory_handler,
)

from core.schemas import PacketWriteResult

# =============================================================================
# Test: Main Pipeline Integration
# =============================================================================


@pytest.mark.asyncio
async def test_save_memory_uses_main_pipeline_when_service_available():
    """Test that save_memory_handler uses main pipeline when substrate_service is provided."""

    # Mock MemorySubstrateService
    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()

    # Mock successful write result
    mock_result = PacketWriteResult(
        packet_id=uuid4(),
        status="ok",
        written_tables=[
            "packet_store",
            "memory_embeddings",
            "knowledge_facts",
            "reasoning_traces",
        ],
        error_message=None,
    )
    mock_service.write_packet.return_value = mock_result

    # Call save_memory_handler with service
    result = await save_memory_handler(
        user_id="test-user",
        content="Test memory content",
        kind="preference",
        scope="developer",
        duration="long",
        tags=["test"],
        importance=0.8,
        caller_id="C",
        creator="Cursor-IDE",
        source="cursor",
        substrate_service=mock_service,  # ✅ Service provided
    )

    # Verify main pipeline was used
    assert result["pipeline"] == "main_dag"
    assert "written_tables" in result
    assert "packet_store" in result["written_tables"]
    assert "knowledge_facts" in result["written_tables"]  # ✅ Fact extraction happened
    assert "reasoning_traces" in result["written_tables"]  # ✅ Reasoning traces created

    # Verify write_packet was called (not direct DB)
    mock_service.write_packet.assert_called_once()
    call_args = mock_service.write_packet.call_args[0][0]
    assert call_args.packet_type == "memory.preference"
    assert call_args.payload["content"] == "Test memory content"
    assert call_args.metadata.agent == "cursor"


@pytest.mark.asyncio
async def test_save_memory_falls_back_to_direct_db_when_service_unavailable():
    """Test that save_memory_handler falls back to direct DB when substrate_service is None."""

    with (
        patch(
            "src.routes.memory_unified.embed_text", new_callable=AsyncMock
        ) as mock_embed,
        patch(
            "src.routes.memory_unified.fetch_one", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "src.routes.memory_unified.execute", new_callable=AsyncMock
        ) as mock_execute,
    ):
        # Mock embedding generation
        mock_embed.return_value = [0.1] * 1536

        # Mock database inserts
        mock_fetch.side_effect = [
            {
                "packet_id": uuid4(),
                "timestamp": "2026-01-09T00:00:00Z",
            },  # packet_store insert
            {"embedding_id": uuid4()},  # memory_embeddings insert
        ]
        mock_execute.return_value = None

        # Call save_memory_handler WITHOUT service (None)
        result = await save_memory_handler(
            user_id="test-user",
            content="Test memory content",
            kind="preference",
            scope="developer",
            duration="long",
            tags=["test"],
            importance=0.8,
            caller_id="C",
            creator="Cursor-IDE",
            source="cursor",
            substrate_service=None,  # ❌ No service - should fallback
        )

        # Verify fallback path was used
        assert result["pipeline"] == "direct_db"
        assert "embedding_id" in result  # Direct DB includes embedding_id

        # Verify direct DB operations were called
        mock_embed.assert_called_once_with("Test memory content")
        assert mock_fetch.call_count == 2  # packet_store + memory_embeddings


@pytest.mark.asyncio
async def test_save_via_main_pipeline_creates_correct_packet_envelope():
    """Test that _save_via_main_pipeline creates PacketEnvelopeIn with correct structure."""

    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()

    mock_result = PacketWriteResult(
        packet_id=uuid4(),
        status="ok",
        written_tables=["packet_store", "memory_embeddings"],
        error_message=None,
    )
    mock_service.write_packet.return_value = mock_result

    result = await _save_via_main_pipeline(
        user_id="test-user",
        content="Test content",
        kind="lesson",
        scope="developer",
        duration="long",
        tags=["test", "lesson"],
        importance=0.9,
        metadata={"session_id": "session-123"},
        caller_id="L",
        creator="L-CTO",
        source="l9-kernel",
        substrate_service=mock_service,
    )

    # Verify write_packet was called with correct structure
    call_args = mock_service.write_packet.call_args[0][0]

    # Check packet_type
    assert call_args.packet_type == "memory.lesson"

    # Check payload
    assert call_args.payload["content"] == "Test content"
    assert call_args.payload["kind"] == "lesson"
    assert call_args.payload["scope"] == "developer"

    # Check metadata
    assert call_args.metadata.agent == "l-cto"
    assert call_args.metadata.domain == "l9"
    assert call_args.metadata.creator == "L-CTO"  # Extra field allowed

    # Check provenance
    assert call_args.provenance.source == "l9-kernel"
    assert call_args.provenance.source_agent == "l-cto"

    # Check tags
    assert "test" in call_args.tags
    assert "lesson" in call_args.tags

    # Verify result
    assert result["pipeline"] == "main_dag"
    assert result["kind"] == "lesson"


@pytest.mark.asyncio
async def test_save_via_main_pipeline_handles_ttl_correctly():
    """Test that _save_via_main_pipeline calculates TTL based on duration."""

    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()

    mock_result = PacketWriteResult(
        packet_id=uuid4(),
        status="ok",
        written_tables=["packet_store"],
        error_message=None,
    )
    mock_service.write_packet.return_value = mock_result

    # Test short duration
    from datetime import datetime, timedelta, timezone

    from src.config import settings

    await _save_via_main_pipeline(
        user_id="test-user",
        content="Short-term memory",
        kind="context",
        scope="developer",
        duration="short",  # Should set TTL
        tags=[],
        importance=0.5,
        metadata=None,
        caller_id="C",
        creator="Cursor-IDE",
        source="cursor",
        substrate_service=mock_service,
    )

    call_args = mock_service.write_packet.call_args[0][0]
    assert call_args.ttl is not None
    # TTL should be approximately now + MEMORY_SHORT_TERM_HOURS
    expected_ttl = datetime.now(UTC) + timedelta(hours=settings.MEMORY_SHORT_TERM_HOURS)
    assert abs((call_args.ttl - expected_ttl).total_seconds()) < 5  # Within 5 seconds


@pytest.mark.asyncio
async def test_save_via_main_pipeline_handles_errors_gracefully():
    """Test that _save_via_main_pipeline raises HTTPException on write failure."""

    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()

    # Mock failed write
    mock_result = PacketWriteResult(
        packet_id=uuid4(),
        status="error",
        written_tables=[],
        error_message="Circuit breaker open",
    )
    mock_service.write_packet.return_value = mock_result

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await _save_via_main_pipeline(
            user_id="test-user",
            content="Test",
            kind="preference",
            scope="developer",
            duration="long",
            tags=[],
            importance=1.0,
            metadata=None,
            caller_id="C",
            creator="Cursor-IDE",
            source="cursor",
            substrate_service=mock_service,
        )

    assert exc_info.value.status_code == 500
    assert "Circuit breaker open" in exc_info.value.detail


@pytest.mark.asyncio
async def test_save_via_direct_db_still_works():
    """Test that _save_via_direct_db fallback still works correctly."""

    with (
        patch(
            "src.routes.memory_unified.embed_text", new_callable=AsyncMock
        ) as mock_embed,
        patch(
            "src.routes.memory_unified.fetch_one", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_embed.return_value = [0.1] * 1536
        mock_fetch.side_effect = [
            {"packet_id": uuid4(), "timestamp": "2026-01-09T00:00:00Z"},
            {"embedding_id": uuid4()},
        ]

        result = await _save_via_direct_db(
            user_id="test-user",
            content="Fallback test",
            kind="fact",
            scope="developer",
            duration="long",
            tags=["fallback"],
            importance=0.7,
            metadata=None,
            caller_id="C",
            creator="Cursor-IDE",
            source="cursor",
        )

        assert result["pipeline"] == "direct_db"
        assert "packet_id" in result
        assert "embedding_id" in result
        assert result["kind"] == "fact"
        mock_embed.assert_called_once()


# =============================================================================
# Test: Integration with MCP Tool Handler
# =============================================================================


@pytest.mark.asyncio
async def test_mcp_tool_call_passes_substrate_service():
    """Test that handle_tool_call passes substrate_service to save_memory_handler."""

    from unittest.mock import MagicMock

    from src.mcp_server import MCPToolCall, handle_tool_call

    mock_caller = MagicMock(
        caller_id="C",
        creator="Cursor-IDE",
        source="cursor",
    )

    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()
    mock_service.write_packet.return_value = PacketWriteResult(
        packet_id=uuid4(),
        status="ok",
        written_tables=["packet_store", "memory_embeddings"],
        error_message=None,
    )

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test via MCP tool",
            "kind": "preference",
            "scope": "developer",
            "duration": "long",
        },
    )

    with patch(
        "src.routes.memory_unified.save_memory_handler", new_callable=AsyncMock
    ) as mock_save:
        mock_save.return_value = {
            "packet_id": str(uuid4()),
            "pipeline": "main_dag",
            "written_tables": ["packet_store", "memory_embeddings"],
        }

        await handle_tool_call(
            tool=tool_call,
            user_id="test-user",
            caller=mock_caller,
            substrate_service=mock_service,  # ✅ Service passed through
        )

        # Verify save_memory_handler was called with substrate_service
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["substrate_service"] == mock_service
        assert call_kwargs["caller_id"] == "C"
        assert call_kwargs["creator"] == "Cursor-IDE"


# =============================================================================
# Test: Scope Mapping
# =============================================================================


@pytest.mark.asyncio
async def test_main_pipeline_preserves_mcp_scope_in_payload():
    """Test that MCP scope (developer/l-private/global) is preserved in packet payload."""

    mock_service = MagicMock()
    mock_service.write_packet = AsyncMock()
    mock_service.write_packet.return_value = PacketWriteResult(
        packet_id=uuid4(),
        status="ok",
        written_tables=["packet_store"],
        error_message=None,
    )

    # Test l-private scope
    await _save_via_main_pipeline(
        user_id="test-user",
        content="Private memory",
        kind="preference",
        scope="l-private",  # MCP scope
        duration="long",
        tags=[],
        importance=1.0,
        metadata=None,
        caller_id="L",
        creator="L-CTO",
        source="l9-kernel",
        substrate_service=mock_service,
    )

    call_args = mock_service.write_packet.call_args[0][0]
    # MCP scope should be preserved in payload
    assert call_args.payload["scope"] == "l-private"
    # DB scope should be mapped (l-private → l-private)
    assert call_args.metadata.db_scope == "l-private"
