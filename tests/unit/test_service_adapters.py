"""
Unit tests for high-level service adapters (GMP-115, GMP-116).

Tests:
- MemoryServiceAdapter: store, retrieve, search
- LLMService: OpenAILLMService, MockLLMService
- DI container integration

Version: 1.0.0
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

# Test UUIDs
TEST_SESSION_ID = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
TEST_AGENT_ID = "agent-456"

# ============================================================================
# Test Fixtures
# ============================================================================


class MockSubstrateService:
    """Mock MemorySubstrateService for testing."""

    def __init__(self):
        self._packets: dict[str, dict[str, Any]] = {}
        self._embeddings: list[dict[str, Any]] = []

    @must_stay_async("callers use await")
    async def write_packet(self, packet_in: Any) -> MagicMock:
        """Mock write_packet."""
        result = MagicMock()
        result.status = "ok"
        result.written_tables = ["packets", "semantic_memory"]
        result.error_message = None

        # Store the packet - use str() for packet_id since it may be UUID
        packet_id = str(packet_in.packet_id)
        self._packets[packet_id] = {
            "packet_id": packet_id,
            "packet_type": str(packet_in.packet_type),
            "thread_id": str(packet_in.thread_id) if packet_in.thread_id else None,
            "agent_id": packet_in.payload.get("agent_id"),
            "payload": packet_in.payload,
            "timestamp": "2026-01-24T00:00:00Z",
        }

        return result

    @must_stay_async("callers use await")
    async def get_packet(self, packet_id: str) -> dict[str, Any] | None:
        """Mock get_packet."""
        return self._packets.get(packet_id)

    @must_stay_async("callers use await")
    async def semantic_search(self, request: Any) -> MagicMock:
        """Mock semantic_search."""
        result = MagicMock()

        # Create mock hits
        hit1 = MagicMock()
        hit1.embedding_id = "emb-001"
        hit1.score = 0.95
        hit1.payload = {"content": "Test content 1", "metadata": {}}

        hit2 = MagicMock()
        hit2.embedding_id = "emb-002"
        hit2.score = 0.85
        hit2.payload = {"content": "Test content 2", "metadata": {"key": "value"}}

        result.hits = [hit1, hit2]
        return result


@pytest.fixture
def mock_substrate():
    """Create mock substrate service."""
    return MockSubstrateService()


# ============================================================================
# MemoryServiceAdapter Tests
# ============================================================================


class TestMemoryServiceAdapter:
    """Tests for MemoryServiceAdapter."""

    def test_adapter_init(self, mock_substrate):
        """Test adapter initialization."""
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)
        assert adapter._substrate is mock_substrate

    @pytest.mark.asyncio
    async def test_store_success(self, mock_substrate):
        """Test storing content returns memory ID."""
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)

        memory_id = await adapter.store(
            "Important fact to remember",
            session_id=TEST_SESSION_ID,
            agent_id=TEST_AGENT_ID,
            metadata={"priority": "high"},
        )

        # Should return a UUID string
        assert memory_id is not None
        assert len(memory_id) == 36  # UUID format

        # Verify packet was stored
        assert memory_id in mock_substrate._packets
        packet = mock_substrate._packets[memory_id]
        assert packet["payload"]["content"] == "Important fact to remember"
        assert packet["thread_id"] == TEST_SESSION_ID

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_store_failure(self, mock_substrate):
        """Test store raises error on failure."""
        from memory.service_adapter import MemoryServiceAdapter

        # Make write_packet return error
        async def failing_write(packet_in):
            result = MagicMock()
            result.status = "error"
            result.error_message = "Database connection failed"
            return result

        mock_substrate.write_packet = failing_write
        adapter = MemoryServiceAdapter(mock_substrate)

        with pytest.raises(RuntimeError, match="Failed to store memory"):
            await adapter.store("Content", session_id=TEST_SESSION_ID)

    @pytest.mark.asyncio
    async def test_retrieve_existing(self, mock_substrate):
        """Test retrieving existing memory."""
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)

        # Store first
        memory_id = await adapter.store("Test content", session_id=TEST_SESSION_ID)

        # Retrieve
        result = await adapter.retrieve(memory_id, session_id=TEST_SESSION_ID)

        assert result is not None
        assert result["memory_id"] == memory_id
        assert result["content"] == "Test content"
        assert result["thread_id"] == TEST_SESSION_ID

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, mock_substrate):
        """Test retrieving non-existent memory returns None."""
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)

        result = await adapter.retrieve("nonexistent-id", session_id=TEST_SESSION_ID)

        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, mock_substrate):
        """Test semantic search."""
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)

        results = await adapter.search(
            "find test content",
            session_id=TEST_SESSION_ID,
            limit=10,
            min_similarity=0.7,
        )

        assert len(results) == 2
        assert results[0]["memory_id"] == "emb-001"
        assert results[0]["similarity"] == 0.95
        assert results[0]["content"] == "Test content 1"
        assert results[1]["memory_id"] == "emb-002"
        assert results[1]["similarity"] == 0.85


# ============================================================================
# LLMService Tests
# ============================================================================


class TestMockLLMService:
    """Tests for MockLLMService."""

    def test_mock_init(self):
        """Test MockLLMService initialization."""
        from core.llm import MockLLMService

        mock = MockLLMService()
        assert mock._default_completion == "[mock completion]"
        assert len(mock._default_embedding) == 1536

    def test_mock_init_custom(self):
        """Test MockLLMService with custom defaults."""
        from core.llm import MockLLMService

        custom_embedding = [1.0, 2.0, 3.0]
        mock = MockLLMService(
            default_completion="custom response",
            default_embedding=custom_embedding,
        )

        assert mock._default_completion == "custom response"
        assert mock._default_embedding == custom_embedding

    @pytest.mark.asyncio
    async def test_mock_complete(self):
        """Test MockLLMService.complete."""
        from core.llm import MockLLMService

        mock = MockLLMService()
        result = await mock.complete("Test prompt")

        assert "[mock completion]" in result
        assert "prompt_length=11" in result

    @pytest.mark.asyncio
    async def test_mock_chat(self):
        """Test MockLLMService.chat."""
        from core.llm import MockLLMService

        mock = MockLLMService()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]
        result = await mock.chat(messages)

        assert "[mock completion]" in result
        assert "messages=3" in result

    @pytest.mark.asyncio
    async def test_mock_embed(self):
        """Test MockLLMService.embed."""
        from core.llm import MockLLMService

        mock = MockLLMService()
        embedding = await mock.embed("Some text to embed")

        assert len(embedding) == 1536
        assert all(v == 0.0 for v in embedding)

    @pytest.mark.asyncio
    async def test_mock_embed_custom(self):
        """Test MockLLMService.embed with custom embedding."""
        from core.llm import MockLLMService

        custom = [1.0, 2.0, 3.0]
        mock = MockLLMService(default_embedding=custom)

        embedding = await mock.embed("Text")

        assert embedding == custom
        # Verify it's a copy
        embedding[0] = 999.0
        assert mock._default_embedding[0] == 1.0


class TestOpenAILLMService:
    """Tests for OpenAILLMService."""

    def test_init_no_api_key(self):
        """Test OpenAILLMService requires API key."""
        from core.llm import OpenAILLMService

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="OpenAI API key required"):
                OpenAILLMService()

    def test_init_with_api_key(self):
        """Test OpenAILLMService initializes with API key."""
        from core.llm import OpenAILLMService

        service = OpenAILLMService(api_key="sk-test-key")

        assert service._api_key == "sk-test-key"
        assert service._default_model == "gpt-4o"
        assert service._client is None  # Lazy initialization

    def test_init_with_env_key(self):
        """Test OpenAILLMService reads from env."""
        from core.llm import OpenAILLMService

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"}):
            service = OpenAILLMService()
            assert service._api_key == "sk-env-key"

    @pytest.mark.asyncio
    async def test_complete_calls_openai(self):
        """Test complete() calls OpenAI API."""
        from core.llm import OpenAILLMService

        service = OpenAILLMService(api_key="sk-test")

        # Mock the client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        service._client = mock_client

        result = await service.complete("Test prompt")

        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_validates_messages(self):
        """Test chat() validates message format."""
        from core.llm import OpenAILLMService

        service = OpenAILLMService(api_key="sk-test")

        # Mock the client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        service._client = mock_client

        # Invalid message format
        with pytest.raises(ValueError, match="role"):
            await service.chat([{"content": "Missing role"}])

    @pytest.mark.asyncio
    async def test_embed_calls_openai(self):
        """Test embed() calls OpenAI embeddings API."""
        from core.llm import OpenAILLMService

        service = OpenAILLMService(api_key="sk-test")

        # Mock the client
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536

        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        service._client = mock_client

        result = await service.embed("Test text")

        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once()


class TestLLMServiceFactory:
    """Tests for create_llm_service factory."""

    def test_create_mock(self):
        """Test creating mock service."""
        from core.llm import create_llm_service
        from core.llm.llm_service import MockLLMService

        service = create_llm_service(provider="mock")
        assert isinstance(service, MockLLMService)

    def test_create_openai(self):
        """Test creating OpenAI service."""
        from core.llm import create_llm_service
        from core.llm.llm_service import OpenAILLMService

        service = create_llm_service(provider="openai", api_key="sk-test")
        assert isinstance(service, OpenAILLMService)

    def test_create_invalid(self):
        """Test invalid provider raises error."""
        from core.llm import create_llm_service

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_service(provider="invalid")


# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestProtocolCompliance:
    """Test that implementations satisfy protocols."""

    def test_memory_adapter_is_memory_service(self, mock_substrate):
        """Test MemoryServiceAdapter implements MemoryService."""
        from core.protocols.service_protocols import MemoryService
        from memory.service_adapter import MemoryServiceAdapter

        adapter = MemoryServiceAdapter(mock_substrate)

        # Protocol is @runtime_checkable
        assert isinstance(adapter, MemoryService)

    def test_mock_llm_is_llm_service(self):
        """Test MockLLMService implements LLMService."""
        from core.llm import MockLLMService
        from core.protocols.service_protocols import LLMService

        mock = MockLLMService()

        # Protocol is @runtime_checkable
        assert isinstance(mock, LLMService)

    def test_openai_llm_is_llm_service(self):
        """Test OpenAILLMService implements LLMService."""
        from core.llm import OpenAILLMService
        from core.protocols.service_protocols import LLMService

        service = OpenAILLMService(api_key="sk-test")

        # Protocol is @runtime_checkable
        assert isinstance(service, LLMService)


# ============================================================================
# DI Container Integration Tests
# ============================================================================


class TestDIBootstrapIntegration:
    """Test DI bootstrap integration (isolated)."""

    def test_bootstrap_registers_services(self):
        """Test bootstrap registers MemoryService and LLMService."""
        from core.di import DIContainer
        from core.di.bootstrap import bootstrap_di_container

        container = DIContainer()

        # Run bootstrap
        stats = bootstrap_di_container(container)

        # Should have registered some services
        assert stats["total_registered"] > 0

        # Note: Actual resolution depends on infrastructure availability
        # This test verifies registration logic works without exceptions
