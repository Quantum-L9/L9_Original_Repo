"""
Pytest Configuration
====================

Shared fixtures for all tests.

Version: 2.0.0
"""

from __future__ import annotations

from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock = MagicMock()
    mock.is_available.return_value = True
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock(return_value=True)
    mock.keys = AsyncMock(return_value=[])
    mock.enqueue_task = AsyncMock(return_value="task-uuid")
    mock.dequeue_task = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_memory_client():
    """Mock memory client for testing."""
    mock = MagicMock()

    mock_result = MagicMock()
    mock_result.hits = []
    mock.semantic_search = AsyncMock(return_value=mock_result)

    mock_write_result = MagicMock()
    mock_write_result.status = "success"
    mock_write_result.packet_id = "uuid-123"
    mock_write_result.written_tables = []
    mock.write_packet = AsyncMock(return_value=mock_write_result)

    return mock


@pytest.fixture
def mock_substrate_service():
    """Mock substrate service for testing."""
    mock = MagicMock()
    mock.get_packet = AsyncMock(return_value=None)
    mock.query_packets = AsyncMock(return_value=[])
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    mock = MagicMock()
    mock._servers = {}
    mock.is_server_available.return_value = False
    mock.list_tools = AsyncMock(return_value=[])
    mock.call_tool = AsyncMock(
        return_value={"success": False, "error": "Not configured"}
    )
    mock.get_allowed_tools = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for testing."""
    mock = MagicMock()
    mock.is_available.return_value = True
    mock.run_query = AsyncMock(return_value=[])
    return mock


# ============================================================================
# PATCH FIXTURES
# ============================================================================


@pytest.fixture
def patch_redis(mock_redis_client):
    """Patch get_redis_client to return mock."""
    with patch(
        "runtime.redis_client.get_redis_client",
        AsyncMock(return_value=mock_redis_client),
    ):
        yield mock_redis_client


@pytest.fixture
def patch_memory(mock_memory_client):
    """Patch get_memory_client to return mock."""
    with patch(
        "clients.memory_client.get_memory_client", return_value=mock_memory_client
    ):
        yield mock_memory_client


@pytest.fixture
def patch_substrate(mock_substrate_service):
    """Patch get_substrate_service to return mock."""
    with patch(
        "memory.substrate_service.get_substrate_service",
        return_value=mock_substrate_service,
    ):
        yield mock_substrate_service


@pytest.fixture
def patch_mcp(mock_mcp_client):
    """Patch get_mcp_client to return mock."""
    with patch("runtime.mcp_client.get_mcp_client", return_value=mock_mcp_client):
        yield mock_mcp_client


@pytest.fixture
def patch_neo4j(mock_neo4j_client):
    """Patch get_neo4j_client to return mock."""
    with patch(
        "memory.graph_client.get_neo4j_client",
        AsyncMock(return_value=mock_neo4j_client),
    ):
        yield mock_neo4j_client


# ============================================================================
# ENV FIXTURES
# ============================================================================


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "OPENAI_API_KEY": "test-key",
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "L9_LLM_MODEL": "gpt-4o-mini",
        "NEO4J_URI": "bolt://localhost:7687",
        "REDIS_URL": "redis://localhost:6379",
    }
    with patch.dict("os.environ", env_vars):
        yield env_vars


# ============================================================================
# TOOL REGISTRY FIXTURES
# ============================================================================


@pytest.fixture
def clean_tool_registry():
    """Provide a clean tool registry for each test."""
    try:
        from runtime.tool_registry import _registry, clear_registry

        clear_registry()
        yield _registry
        clear_registry()
    except ImportError:
        yield {}
