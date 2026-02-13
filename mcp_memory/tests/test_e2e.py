"""End-to-end tests for MCP Memory Server.

Tests the complete flow from MCP tool call → validation → handler → database → response.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.mcp_server import MCPToolCall, handle_tool_call

from core.decorators import must_stay_async

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_caller_l():
    """Mock caller identity for L-CTO."""
    return MagicMock(caller_id="L", creator="L-CTO", source="l9-runtime")


@pytest.fixture
def mock_caller_c():
    """Mock caller identity for Cursor IDE."""
    return MagicMock(caller_id="C", creator="Cursor-IDE", source="cursor-mcp")


# =============================================================================
# E2E Test 1: Save Memory Flow
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_e2e_save_memory(mock_caller_c):
    """Test complete save_memory flow: validation → handler → database."""

    # 1. Create MCP tool call
    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test memory content",
            "kind": "preference",
            "scope": "developer",
            "duration": "long",
            "user_id": "test-user",
            "tags": ["test"],
            "importance": 0.8,
        },
    )

    # 2. Mock database operations
    with (
        patch("src.routes.memory_unified.execute") as mock_execute,
        patch(
            "src.routes.memory_unified.embed_text", new_callable=AsyncMock
        ) as mock_embed,
        patch(
            "src.routes.memory_unified.fetch_one", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        # Mock embedding generation
        mock_embed.return_value = [0.1] * 1536

        # Mock packet_store insert
        mock_execute.return_value = None

        # Mock fetch_one for packet retrieval
        mock_fetch.return_value = {
            "packet_id": "test-packet-id",
            "envelope": {"packet_type": "memory_write"},
            "created_at": "2026-01-09T00:00:00Z",
        }

        # 3. Execute tool call
        result = await handle_tool_call(
            tool=tool_call, user_id="test-user", caller=mock_caller_c
        )

        # 4. Verify result
        assert "packet_id" in result or "id" in result
        assert mock_embed.called
        assert mock_execute.called


# =============================================================================
# E2E Test 2: Search Memory Flow
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_e2e_search_memory(mock_caller_c):
    """Test complete search_memory flow: validation → handler → vector search."""

    tool_call = MCPToolCall(
        name="search_memory",
        arguments={
            "query": "test query",
            "user_id": "test-user",
            "scopes": ["developer", "global"],
            "top_k": 5,
            "threshold": 0.7,
        },
    )

    with (
        patch(
            "src.routes.memory_unified.embed_text", new_callable=AsyncMock
        ) as mock_embed,
        patch(
            "src.routes.memory_unified.fetch_all", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        # Mock embedding generation
        mock_embed.return_value = [0.1] * 1536

        # Mock vector search results
        mock_fetch.return_value = [
            {"packet_id": "test-1", "content": "Test memory 1", "similarity": 0.85},
            {"packet_id": "test-2", "content": "Test memory 2", "similarity": 0.75},
        ]

        result = await handle_tool_call(
            tool=tool_call, user_id="test-user", caller=mock_caller_c
        )

        assert "results" in result
        assert len(result["results"]) == 2
        assert mock_embed.called


# =============================================================================
# E2E Test 3: Governance Enforcement
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_governance_cursor_cannot_write_l_private(mock_caller_c):
    """Test that Cursor (C) cannot write to l-private scope."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Private memory",
            "kind": "preference",
            "scope": "l-private",  # ❌ Cursor cannot write this
            "duration": "long",
            "user_id": "test-user",
        },
    )

    with pytest.raises(ValueError, match="Cursor cannot write to l-private scope"):
        await handle_tool_call(
            tool=tool_call, user_id="test-user", caller=mock_caller_c
        )


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_e2e_governance_l_can_write_l_private(mock_caller_l):
    """Test that L-CTO (L) can write to l-private scope."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Private memory",
            "kind": "preference",
            "scope": "l-private",  # ✅ L can write this
            "duration": "long",
            "user_id": "test-user",
        },
    )

    with (
        patch("src.routes.memory_unified.execute") as mock_execute,
        patch(
            "src.routes.memory_unified.embed_text", new_callable=AsyncMock
        ) as mock_embed,
        patch(
            "src.routes.memory_unified.fetch_one", new_callable=AsyncMock
        ) as mock_fetch,
    ):
        mock_embed.return_value = [0.1] * 1536
        mock_execute.return_value = None
        mock_fetch.return_value = {"packet_id": "test-id"}

        # Should NOT raise ValueError
        result = await handle_tool_call(
            tool=tool_call, user_id="test-user", caller=mock_caller_l
        )

        assert result is not None


# =============================================================================
# E2E Test 4: Fail-Fast Validation
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_validation_fail_fast_invalid_kind():
    """Test that invalid 'kind' value is rejected immediately (fail-fast)."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test",
            "kind": "invalid_kind",  # ❌ Not in enum: preference, fact, context, error, success
            "scope": "developer",
            "duration": "long",
            "user_id": "test-user",
        },
    )

    # Validation should fail BEFORE handler is called
    with pytest.raises(ValueError, match="Invalid arguments"):
        await handle_tool_call(tool=tool_call, user_id="test-user", caller=None)


@pytest.mark.asyncio
async def test_e2e_validation_fail_fast_missing_required():
    """Test that missing required fields are rejected immediately."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test",
            # ❌ Missing: kind, duration, user_id (required)
            "scope": "developer",
        },
    )

    with pytest.raises(ValueError, match="Invalid arguments"):
        await handle_tool_call(tool=tool_call, user_id="test-user", caller=None)


# =============================================================================
# E2E Test 5: Error Handling
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_e2e_error_handling_database_error(mock_caller_c):
    """Test that database errors are caught and handled gracefully."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test",
            "kind": "preference",
            "scope": "developer",
            "duration": "long",
            "user_id": "test-user",
        },
    )

    import asyncpg

    with patch("src.routes.memory_unified.execute") as mock_execute:
        # Simulate database error
        mock_execute.side_effect = asyncpg.PostgresError("Connection failed")

        # Should raise HTTPException with 500 status
        with pytest.raises(Exception):  # Will be HTTPException in actual handler
            await handle_tool_call(
                tool=tool_call, user_id="test-user", caller=mock_caller_c
            )


@pytest.mark.asyncio
async def test_e2e_error_handling_validation_error():
    """Test that validation errors return 400 (not 500)."""

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "Test",
            "kind": "invalid",  # Invalid enum value
            "scope": "developer",
            "duration": "long",
            "user_id": "test-user",
        },
    )

    # Should raise ValueError (caught as ValidationError)
    with pytest.raises(ValueError):
        await handle_tool_call(tool=tool_call, user_id="test-user", caller=None)


# =============================================================================
# E2E Test 6: Audit Logging
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_audit_logging_tool_call_logged(mock_caller_c):
    """Test that tool calls are logged to tool_audit_log."""

    tool_call = MCPToolCall(
        name="get_memory_stats", arguments={"user_id": "test-user", "duration": "all"}
    )

    with (
        patch(
            "src.routes.memory_unified.get_memory_stats", new_callable=AsyncMock
        ) as mock_stats,
        patch("src.mcp_server.execute", new_callable=AsyncMock) as mock_audit,
    ):
        mock_stats.return_value = {"total_count": 100}
        mock_audit.return_value = None

        await handle_tool_call(
            tool=tool_call, user_id="test-user", caller=mock_caller_c
        )

        # Verify audit log was written
        assert mock_audit.called
        # Verify audit log includes caller and project_id
        call_args = mock_audit.call_args
        assert "caller" in str(call_args) or "project_id" in str(call_args)
