"""
L9 OS Test Suite - Root Configuration
=====================================

Shared fixtures for all test modules.
No network access required - all mocks are local.
"""

import sys
from pathlib import Path

import pytest

from core.decorators import must_stay_async

# Add project root and tests directory to path
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_ROOT = Path(__file__).parent

# CRITICAL: Insert project root FIRST for real imports to work
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

# Import mocks
from mocks.kernel_mocks import KernelState, load_kernels
from mocks.memory_mocks import MockMemoryAdapter, MockPostgresCursor
from mocks.orchestrator_mocks import MockRedis, MockToolRegistry
from mocks.world_model_mocks import MockWorldModel

# =============================================================================
# Kernel Fixtures
# =============================================================================


@pytest.fixture
def kernel_state() -> KernelState:
    """Provide a fresh kernel state."""
    return load_kernels()


@pytest.fixture
def governance_kernel() -> dict:
    """Provide governance kernel config."""
    return {
        "rules": {"truth": "strict", "safety": "maximum"},
        "memory": {"max_in_state_size_kb": 1024},
        "constraints": {"no_hallucination": True},
    }


@pytest.fixture
def agent_kernel() -> dict:
    """Provide agent kernel config."""
    return {
        "rules": {"truth": "loose", "adaptability": "high"},
        "capabilities": {"web_search": True},
    }


# =============================================================================
# Memory Fixtures (Sync)
# =============================================================================


@pytest.fixture
def memory_adapter() -> MockMemoryAdapter:
    """Provide a mock memory adapter."""
    return MockMemoryAdapter(
        max_vectors=25000,
        blob_threshold_kb=512,
    )


@pytest.fixture
def postgres_cursor() -> MockPostgresCursor:
    """Provide a mock PostgreSQL cursor."""
    return MockPostgresCursor()


@pytest.fixture
def adapter(memory_adapter) -> MockMemoryAdapter:
    """Alias for memory_adapter fixture."""
    return memory_adapter


# =============================================================================
# Memory Fixtures (Async)
# =============================================================================


@pytest.fixture
@must_stay_async("callers use await")
async def async_redis():
    """Async Redis mock with in-memory store."""

    class AsyncMockRedis:
        def __init__(self):
            self.store = {}  # Instance-level to prevent test pollution

        @must_stay_async("callers use await")
        async def get(self, k):
            return self.store.get(k)

        @must_stay_async("callers use await")
        async def set(self, k, v):
            self.store[k] = v

        @must_stay_async("callers use await")
        async def incr(self, k):
            self.store[k] = self.store.get(k, 0) + 1
            return self.store[k]

    return AsyncMockRedis()


@pytest.fixture
def async_postgres_cursor():
    """Postgres cursor mock returning ivfflat index DDL."""

    class AsyncMockCursor:
        def __init__(self):
            self.q = None

        def execute(self, q):
            self.q = q

        def fetchone(self):
            return ["CREATE INDEX memory_vectors_idx ON memory USING ivfflat"]

    return AsyncMockCursor()


@pytest.fixture
@must_stay_async("callers use await")
async def async_memory_adapter():
    """Async memory adapter with blob storage and packet management."""

    class AsyncMockMemory:
        def __init__(self):
            self.blobs = {}  # Instance-level
            self.packets = {}  # Instance-level
            self.idx = 0  # Instance-level

        @must_stay_async("callers use await")
        async def store_blob(self, content):
            k = f"blob-{len(self.blobs)}"
            self.blobs[k] = content
            return k

        @must_stay_async("callers use await")
        async def ingest(self, data):
            self.idx += 1
            pid = f"p{self.idx}"
            self.packets[pid] = data
            return {"packet_id": pid, **data}

        @must_stay_async("callers use await")
        async def retrieve(self, pid):
            return self.packets.get(pid)

        @must_stay_async("callers use await")
        async def run_pruning(self):
            # Simulate pruning to 20000 vectors
            return {"active_vectors": 20000}

    return AsyncMockMemory()


# =============================================================================
# World Model Fixtures
# =============================================================================


@pytest.fixture
def world_model() -> MockWorldModel:
    """Provide a mock world model."""
    return MockWorldModel()


@pytest.fixture
@must_stay_async("callers use await")
async def async_world_model():
    """Async world model mock with node/edge graph operations."""

    class AsyncMockWM:
        def __init__(self):
            self.nodes = {}  # Instance-level
            self.edges = []  # Instance-level

        @must_stay_async("callers use await")
        async def create_node(self, t, data):
            nid = len(self.nodes)
            self.nodes[nid] = {"type": t, **data}
            return nid

        @must_stay_async("callers use await")
        async def get_node(self, nid):
            return self.nodes.get(nid)

        @must_stay_async("callers use await")
        async def link(self, a, b, rel):
            self.edges.append((a, b, rel))

        @must_stay_async("callers use await")
        async def get_edges(self, nid):
            return [
                {"type": rel, "src": a, "dst": b}
                for (a, b, rel) in self.edges
                if a == nid
            ]

    return AsyncMockWM()


# =============================================================================
# Orchestrator Fixtures
# =============================================================================


@pytest.fixture
def redis() -> MockRedis:
    """Provide a mock Redis client."""
    return MockRedis()


@pytest.fixture
def tool_registry(redis) -> MockToolRegistry:
    """Provide a mock tool registry."""
    registry = MockToolRegistry(redis=redis)

    # Register some default tools
    registry.register_tool("echo", lambda x: x, rate_limit=1000)
    registry.register_tool("google", lambda q: {"results": []}, rate_limit=100)
    registry.register_tool("openai", lambda p: {"completion": ""}, rate_limit=500)

    return registry


# =============================================================================
# Async Support
# =============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_packet() -> dict:
    """Provide a sample packet for testing."""
    return {
        "content": "Test content for packet",
        "metadata": {"source": "test"},
        "tags": ["test", "sample"],
    }


@pytest.fixture
def large_content() -> str:
    """Provide large content for blob testing."""
    return "x" * (2 * 1024 * 1024)  # 2MB


@pytest.fixture
def sample_checkpoint() -> dict:
    """Provide a sample checkpoint for testing."""
    return {
        "step": 3,
        "plan": [1, 2, 3],
        "state": {"key": "value"},
    }


# =============================================================================
# Shared Mock Fixtures (from test_executor.py)
# =============================================================================


@pytest.fixture
def mock_substrate_service():
    """
    Shared mock substrate service for memory tests.

    Provides a MagicMock that simulates SubstrateService behavior.
    """
    from tests.core.agents.test_executor import MockSubstrateService

    return MockSubstrateService()


@pytest.fixture
def mock_tool_registry():
    """
    Shared mock tool registry for orchestrator tests.

    Provides a MagicMock that simulates ToolRegistry behavior.
    """
    from tests.core.agents.test_executor import MockToolRegistry

    return MockToolRegistry()


# =============================================================================
# Slack Webhook Test Fixtures
# =============================================================================

import hashlib
import hmac
import time

SLACK_TEST_SIGNING_SECRET = "test_slack_signing_secret_123"  # noqa: S105 — test fixture
SLACK_TEST_CHANNEL_ID = "C12345678"
SLACK_TEST_USER_ID = "U12345678"
SLACK_TEST_TEAM_ID = "T12345678"


@pytest.fixture
def slack_signing_secret() -> str:
    """Provide test Slack signing secret."""
    return SLACK_TEST_SIGNING_SECRET


@pytest.fixture
def slack_test_ids() -> dict:
    """Provide test Slack IDs (channel, user, team)."""
    return {
        "channel_id": SLACK_TEST_CHANNEL_ID,
        "user_id": SLACK_TEST_USER_ID,
        "team_id": SLACK_TEST_TEAM_ID,
    }


def generate_slack_signature(body: str, timestamp: str, secret: str) -> str:
    """
    Generate valid Slack HMAC-SHA256 signature for testing.

    Args:
        body: Request body as string
        timestamp: Unix timestamp as string
        secret: Slack signing secret

    Returns:
        Signature in format "v0=<hex_hash>"
    """
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return f"v0={signature}"


@pytest.fixture
def slack_signature_generator():
    """
    Provide a function to generate valid Slack signatures.

    Usage:
        sig = slack_signature_generator(body, timestamp, secret)
    """
    return generate_slack_signature


@pytest.fixture
def fresh_slack_timestamp() -> str:
    """Provide current Unix timestamp as string (fresh, within tolerance)."""
    return str(int(time.time()))


@pytest.fixture
def stale_slack_timestamp() -> str:
    """Provide timestamp > 300 seconds old (outside tolerance)."""
    return str(int(time.time()) - 400)


@pytest.fixture
def slack_enabled(monkeypatch):
    """
    Enable Slack integration for tests.

    Sets SLACK_APP_ENABLED=true and SLACK_SIGNING_SECRET.
    """
    monkeypatch.setenv("SLACK_APP_ENABLED", "true")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SLACK_TEST_SIGNING_SECRET)


@pytest.fixture
def slack_disabled(monkeypatch):
    """
    Disable Slack integration for tests.

    Sets SLACK_APP_ENABLED=false.
    """
    monkeypatch.setenv("SLACK_APP_ENABLED", "false")


# =============================================================================
# AST Caching Fixtures (Performance Optimization)
# =============================================================================

# Directories scanned by CI tests
CORE_MODULES_FOR_SCANNING = [
    "core",
    "memory",
    "orchestration",
    "runtime",
    "api",
    "agents",
]


def _get_python_files_for_cache(directories: list[str]) -> list[Path]:
    """Get all Python files in specified directories."""
    python_files: list[Path] = []
    for directory in directories:
        dir_path = PROJECT_ROOT.parent / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob("*.py"))
    return python_files


def _parse_python_file_for_cache(file_path: Path) -> tuple | None:
    """Parse Python file into AST with error handling."""
    import ast

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        return (tree, content)
    except (SyntaxError, UnicodeDecodeError):
        return None


@pytest.fixture(scope="session")
def parsed_codebase() -> dict[Path, tuple | None]:
    """
    Parse all Python files ONCE per test session.

    This fixture provides a cached AST + content for all Python files
    in core modules. Tests that scan the codebase should use this
    instead of parsing files themselves.

    Usage:
        def test_something(parsed_codebase):
            for file_path, parsed in parsed_codebase.items():
                if parsed is None:
                    continue
                tree, content = parsed
                # Use tree and content...

    Performance: ~10x speedup for CI tests that scan codebase.
    """
    files = _get_python_files_for_cache(CORE_MODULES_FOR_SCANNING)
    return {f: _parse_python_file_for_cache(f) for f in files}


@pytest.fixture(scope="session")
def python_files_list() -> list[Path]:
    """
    Get list of all Python files in core modules.

    Use this when you only need file paths, not parsed AST.
    """
    return _get_python_files_for_cache(CORE_MODULES_FOR_SCANNING)
