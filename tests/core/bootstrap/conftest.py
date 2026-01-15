"""
Test fixtures for core/agents tests.

Provides mocks for Neo4j, MemorySubstrateService, and other dependencies
to enable isolated testing of bootstrap phases without external services.
"""

from __future__ import annotations

# Pre-import memory.graph_client to ensure it's available for lazy imports
# This MUST happen before any bootstrap modules are imported
import importlib.util

# Force-load memory.graph_client into sys.modules
# (fixes pytest import resolution for lazy imports inside bootstrap phases)
try:
    spec = importlib.util.find_spec("memory.graph_client")
    if spec:
        import memory.graph_client  # noqa: F401
except Exception:
    pass  # Ignore if unavailable - tests will fail gracefully

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest


# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockAgentConfig:
    """Mock AgentConfig for testing."""

    agent_id: str = "test-agent"
    name: str = "Test Agent"
    kernel_refs: list = field(
        default_factory=lambda: [
            "01_master_kernel.yaml",
            "02_identity_kernel.yaml",
            "07_execution_kernel.yaml",
            "08_safety_kernel.yaml",
        ]
    )


class MockNeo4jSession:
    """Mock Neo4j session for testing."""

    def __init__(self):
        self.queries_run = []

    async def run(self, query: str, params: Optional[Dict] = None):
        """Record query and return mock result."""
        self.queries_run.append({"query": query, "params": params})
        return MockNeo4jResult()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockNeo4jResult:
    """Mock Neo4j query result."""

    def __init__(self, records: Optional[list] = None):
        self._records = records or []
        self._index = 0

    async def single(self):
        """Return single record or None."""
        if self._records:
            return self._records[0]
        return {"kernel_count": 4, "tool_count": 4}

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._index]
        self._index += 1
        return record


class MockNeo4jClient:
    """Mock Neo4j client for testing."""

    def __init__(self):
        self._session = MockNeo4jSession()

    def session(self):
        return self._session


class MockSubstrateService:
    """Mock MemorySubstrateService for testing."""

    def __init__(self):
        self.postgres_pool = MockPostgresPool()
        self.tool_registry = MagicMock()
        self.packets_written = []

    async def write_packet(self, packet: Any) -> None:
        """Record packet write."""
        self.packets_written.append(packet)


class MockPostgresPool:
    """Mock asyncpg pool for testing."""

    def acquire(self):
        return MockPostgresConnection()


class MockPostgresConnection:
    """Mock asyncpg connection."""

    async def execute(self, query: str):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_config():
    """Provide a mock AgentConfig."""
    return MockAgentConfig()


@pytest.fixture
def mock_substrate_service():
    """Provide a mock MemorySubstrateService."""
    return MockSubstrateService()


@pytest.fixture
def mock_neo4j_client():
    """Provide a mock Neo4j client."""
    return MockNeo4jClient()


@pytest.fixture
def mock_neo4j_none():
    """Fixture that returns None for Neo4j client (offline mode)."""

    async def _get_none():
        return None

    return _get_none


@pytest.fixture
def patch_neo4j_client(mock_neo4j_client):
    """
    Patch get_neo4j_client to return mock client.

    Usage:
        async def test_something(patch_neo4j_client):
            with patch_neo4j_client:
                # Neo4j calls will use mock
                pass
    """

    async def _get_mock():
        return mock_neo4j_client

    return patch(
        "memory.graph_client.get_neo4j_client",
        side_effect=_get_mock,
    )


@pytest.fixture
def patch_neo4j_offline():
    """
    Patch get_neo4j_client to return None (offline mode).

    Usage:
        async def test_offline(patch_neo4j_offline):
            with patch_neo4j_offline:
                # Neo4j will appear offline
                pass
    """

    async def _get_none():
        return None

    return patch(
        "memory.graph_client.get_neo4j_client",
        side_effect=_get_none,
    )


@pytest.fixture
def mock_kernels():
    """Provide mock kernel data."""
    return {
        "01_master_kernel": {
            "name": "Master Kernel",
            "version": "1.0.0",
            "hash": "abc123",
        },
        "02_identity_kernel": {
            "name": "Identity Kernel",
            "version": "1.0.0",
            "hash": "def456",
        },
        "07_execution_kernel": {
            "name": "Execution Kernel",
            "version": "1.0.0",
            "hash": "ghi789",
        },
        "08_safety_kernel": {
            "name": "Safety Kernel",
            "version": "1.0.0",
            "hash": "jkl012",
        },
    }


@pytest.fixture
def mock_bootstrap_instance(mock_agent_config):
    """Provide a mock BootstrapInstanceData."""
    from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData

    return BootstrapInstanceData(
        instance_id="test-instance-123",
        agent_id=mock_agent_config.agent_id,
        name=mock_agent_config.name,
        config=mock_agent_config,
        kernel_state="LOADING",
        status="INITIALIZING",
        created_at=datetime.utcnow(),
    )
