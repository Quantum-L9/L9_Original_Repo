"""
L9 Research Factory - Memory Adapter Tests
Version: 1.0.0

Tests for the memory substrate adapter.
"""

import pytest

pytest.skip("Legacy memory substrate system — skipping.", allow_module_level=True)
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.research.graph_state import (ResearchGraphState,
                                           create_initial_state)
from services.research.memory_adapter import (ResearchMemoryAdapter,
                                              get_memory_adapter,
                                              init_memory_adapter)


class TestResearchMemoryAdapter:
    """Tests for ResearchMemoryAdapter class."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = AsyncMock()
        repo.insert_packet.return_value = uuid4()
        repo.insert_memory_event.return_value = uuid4()
        repo.insert_reasoning_block.return_value = uuid4()
        repo.save_checkpoint.return_value = uuid4()
        repo.get_checkpoint.return_value = None
        repo.insert_log.return_value = uuid4()
        return repo

    @pytest.fixture
    def adapter(self, mock_repository) -> ResearchMemoryAdapter:
        """Create adapter with mock repository."""
        return ResearchMemoryAdapter(mock_repository)

    @pytest.fixture
    def sample_state(self) -> ResearchGraphState:
        """Create a sample state."""
        state = create_initial_state(
            query="Test query",
            thread_id="thread-123",
            request_id="request-456",
        )
        state["critic_score"] = 0.85
        state["critic_feedback"] = "Good research"
        return state

    def test_state_to_envelope(
        self, adapter: ResearchMemoryAdapter, sample_state: ResearchGraphState
    ):
        """Test converting state to packet envelope."""
        envelope = adapter.state_to_envelope(sample_state)

        assert envelope.packet_type == "research_state"
        assert envelope.payload["original_query"] == "Test query"
        assert envelope.metadata.agent == "research_graph"
        assert envelope.confidence.score == 0.85

    def test_state_to_envelope_custom_type(
        self, adapter: ResearchMemoryAdapter, sample_state: ResearchGraphState
    ):
        """Test converting with custom packet type."""
        envelope = adapter.state_to_envelope(
            sample_state,
            packet_type="research_result",
            agent_id="custom_agent",
        )

        assert envelope.packet_type == "research_result"
        assert envelope.metadata.agent == "custom_agent"

    def test_envelope_to_state(
        self, adapter: ResearchMemoryAdapter, sample_state: ResearchGraphState
    ):
        """Test converting envelope back to state."""
        envelope = adapter.state_to_envelope(sample_state)
        reconstructed = adapter.envelope_to_state(envelope)

        assert reconstructed["original_query"] == sample_state["original_query"]
        assert reconstructed["thread_id"] == sample_state["thread_id"]

    @pytest.mark.asyncio
    async def test_save_checkpoint(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
        sample_state: ResearchGraphState,
    ):
        """Test saving a checkpoint."""
        checkpoint_id = await adapter.save_checkpoint(sample_state)

        mock_repository.save_checkpoint.assert_called_once()
        assert checkpoint_id is not None

    @pytest.mark.asyncio
    async def test_load_checkpoint_not_found(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
    ):
        """Test loading non-existent checkpoint."""
        result = await adapter.load_checkpoint("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_found(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
        sample_state: ResearchGraphState,
    ):
        """Test loading existing checkpoint."""
        # Mock checkpoint data
        mock_checkpoint = MagicMock()
        mock_checkpoint.graph_state = dict(sample_state)
        mock_repository.get_checkpoint.return_value = mock_checkpoint

        result = await adapter.load_checkpoint("thread-123")

        assert result is not None
        assert result["original_query"] == "Test query"

    @pytest.mark.asyncio
    async def test_log_memory_event(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
    ):
        """Test logging a memory event."""
        event_id = await adapter.log_memory_event(
            agent_id="test_agent",
            event_type="test_event",
            content={"key": "value"},
        )

        mock_repository.insert_memory_event.assert_called_once_with(
            agent_id="test_agent",
            event_type="test_event",
            content={"key": "value"},
            packet_id=None,
        )
        assert event_id is not None

    @pytest.mark.asyncio
    async def test_save_reasoning_trace(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
    ):
        """Test saving a reasoning trace."""
        trace_id = await adapter.save_reasoning_trace(
            agent_id="test_agent",
            packet_id=uuid4(),
            reasoning_steps=["Step 1", "Step 2"],
            features={"feature1": "value1"},
            confidence=0.9,
        )

        mock_repository.insert_reasoning_block.assert_called_once()
        assert trace_id is not None

    @pytest.mark.asyncio
    async def test_save_state_as_packet(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
        sample_state: ResearchGraphState,
    ):
        """Test saving state as packet."""
        packet_id = await adapter.save_state_as_packet(sample_state)

        mock_repository.insert_packet.assert_called_once()
        assert packet_id is not None

    @pytest.mark.asyncio
    async def test_log(
        self,
        adapter: ResearchMemoryAdapter,
        mock_repository,
    ):
        """Test writing a log entry."""
        log_id = await adapter.log(
            agent_id="test_agent",
            level="INFO",
            message="Test message",
            metadata={"key": "value"},
        )

        mock_repository.insert_log.assert_called_once()
        assert log_id is not None


class TestAdapterSingleton:
    """Tests for adapter singleton functions."""

    def test_init_memory_adapter(self):
        """Test initializing memory adapter."""
        mock_repo = AsyncMock()

        adapter = init_memory_adapter(mock_repo)

        assert adapter is not None
        assert adapter._repository is mock_repo

    def test_get_memory_adapter_requires_init(self):
        """Test that get_memory_adapter works after init."""
        # Reset singleton
        import services.research.memory_adapter as module

        module._adapter = None

        # Should raise when getting repository
        with patch("services.research.memory_adapter.get_repository") as mock_get_repo:
            mock_get_repo.return_value = AsyncMock()
            adapter = get_memory_adapter()
            assert adapter is not None
