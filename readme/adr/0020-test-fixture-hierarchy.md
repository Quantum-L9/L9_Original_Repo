# ADR 0020: Test Fixture Hierarchy

## Status

Accepted

## Pattern

Shared fixtures in `tests/conftest.py`; domain mocks in `tests/mocks/`; no network in unit tests.

## Files

- `tests/conftest.py` - Root fixtures (308+ fixtures)
- `tests/mocks/kernel_mocks.py` - Kernel state mocks
- `tests/mocks/memory_mocks.py` - Memory adapter mocks
- `tests/mocks/orchestrator_mocks.py` - Orchestrator mocks

## Import Block

```python
# In test files
import pytest
from tests.mocks.memory_mocks import MockSubstrateService
from tests.mocks.kernel_mocks import mock_kernel_state

# Fixtures auto-discovered from conftest.py
```

## Minimal Implementation

```python
# tests/conftest.py — Root fixtures
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_substrate_service():
    """Mock memory substrate service."""
    service = AsyncMock()
    service.write_packet = AsyncMock(return_value={"status": "ok"})
    service.search = AsyncMock(return_value=[])
    return service

@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client

@pytest.fixture
async def test_db_session():
    """Async database session for integration tests."""
    # Setup
    session = await create_test_session()
    yield session
    # Teardown
    await session.rollback()
    await session.close()


# tests/mocks/memory_mocks.py — Domain-specific mocks
class MockSubstrateService:
    """Mock for MemorySubstrateService."""

    def __init__(self):
        self.packets_written: list[dict] = []

    async def write_packet(self, packet: dict) -> dict:
        self.packets_written.append(packet)
        return {"status": "ok", "packet_id": "test-id"}

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        return []
```

## Usage Example

```python
# tests/memory/test_ingestion.py
import pytest
from memory.ingestion import IngestionPipeline

class TestIngestionPipeline:
    """Tests for ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_ingest_packet(self, mock_substrate_service):
        """Test packet ingestion with mock service."""
        # Arrange
        pipeline = IngestionPipeline(service=mock_substrate_service)
        packet = {"type": "test", "payload": {}}

        # Act
        result = await pipeline.ingest(packet)

        # Assert
        assert result["status"] == "ok"
        mock_substrate_service.write_packet.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_with_validation_error(self, mock_substrate_service):
        """Test validation error handling."""
        # Arrange
        mock_substrate_service.write_packet.side_effect = ValueError("Invalid")
        pipeline = IngestionPipeline(service=mock_substrate_service)

        # Act & Assert
        with pytest.raises(ValueError):
            await pipeline.ingest({"invalid": True})
```

## Anti-Pattern Example

```python
# ❌ WRONG — Inline mock (duplicates across tests)
async def test_something():
    mock_service = AsyncMock()
    mock_service.method = AsyncMock(return_value=True)
    # 50 tests all create same mock...

# ❌ WRONG — Real network call in unit test
async def test_api_call():
    result = await httpx.get("https://api.example.com")  # Flaky!

# ❌ WRONG — Fixture not in conftest.py
# tests/memory/test_foo.py
@pytest.fixture
def mock_service():  # Should be in conftest.py
    ...

# ✅ CORRECT — Use shared fixture
async def test_something(mock_substrate_service):  # From conftest.py
    result = await mock_substrate_service.search("query")
```

## Directory Structure

```
tests/
├── conftest.py              ← Root fixtures (ALL shared fixtures here)
├── mocks/
│   ├── __init__.py
│   ├── kernel_mocks.py      ← Kernel-specific mocks
│   ├── memory_mocks.py      ← Memory service mocks
│   └── orchestrator_mocks.py← Orchestrator mocks
├── unit/                    ← Unit tests (no network)
├── integration/             ← Integration tests (may use test DB)
└── {domain}/                ← Domain-specific tests
    └── conftest.py          ← Domain-specific fixtures
```

## Rules

1. Unit tests MUST NOT access network
2. Shared fixtures MUST go in `tests/conftest.py`
3. Domain mocks MUST go in `tests/mocks/`
4. Use `@pytest.mark.asyncio` for async tests
5. Clean up resources in fixture teardown

## AI Guidance

**DO:**

- Use existing fixtures from `conftest.py`
- Add new mocks to `tests/mocks/`
- Use `AsyncMock` for async methods
- Include setup and teardown in fixtures

**DO NOT:**

- Create inline mocks (use `tests/mocks/`)
- Access network in unit tests
- Duplicate fixtures across test files
- Skip fixture teardown/cleanup
