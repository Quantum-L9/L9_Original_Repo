"""
Tests for L9RetryablePostgresSaver and checkpoint resilience.

GMP-105: LangGraph Checkpoint Resilience — Batch 1
Tests for:
- T1: Retry wrapper functionality
- T2: list() method implementation
- T3: get_pool_stats() method
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory.checkpoint.postgres_saver import L9PostgresSaver, L9RetryablePostgresSaver

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository():
    """Create mock SubstrateRepository."""
    repo = MagicMock()
    repo.save_checkpoint = AsyncMock(return_value="checkpoint-123")
    repo.get_checkpoint = AsyncMock(return_value=None)
    repo.list_checkpoints_by_agent = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def retryable_saver(mock_repository):
    """Create L9RetryablePostgresSaver with mock repository."""
    return L9RetryablePostgresSaver(
        repository=mock_repository,
        max_retries=3,
        base_retry_delay=0.01,  # Fast retries for testing
    )


@pytest.fixture
def basic_saver(mock_repository):
    """Create basic L9PostgresSaver with mock repository."""
    return L9PostgresSaver(repository=mock_repository)


@pytest.fixture
def valid_config():
    """Valid LangGraph config with thread_id."""
    return {"configurable": {"thread_id": "test-thread-123"}}


@pytest.fixture
def valid_checkpoint():
    """Valid checkpoint data."""
    return {"messages": [], "step": 1}


@pytest.fixture
def valid_metadata():
    """Valid checkpoint metadata."""
    return {"source": "test", "step": 1}


# ============================================================================
# L9RetryablePostgresSaver Tests
# ============================================================================


class TestL9RetryablePostgresSaverInit:
    """Test L9RetryablePostgresSaver initialization."""

    def test_init_with_defaults(self, mock_repository):
        """Test initialization with default parameters."""
        saver = L9RetryablePostgresSaver(repository=mock_repository)

        assert saver.max_retries == 3
        assert saver.base_retry_delay == 0.1
        assert saver._repository is mock_repository

    def test_init_with_custom_params(self, mock_repository):
        """Test initialization with custom parameters."""
        saver = L9RetryablePostgresSaver(
            repository=mock_repository,
            max_retries=5,
            base_retry_delay=0.5,
        )

        assert saver.max_retries == 5
        assert saver.base_retry_delay == 0.5


class TestExecuteWithRetry:
    """Test _execute_with_retry method."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, retryable_saver):
        """Test successful execution on first attempt."""
        mock_func = AsyncMock(return_value="success")

        result = await retryable_saver._execute_with_retry(
            "test_op", mock_func, "arg1", kwarg1="value"
        )

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value")

    @pytest.mark.asyncio
    async def test_success_after_retry(self, retryable_saver):
        """Test successful execution after transient failure."""
        mock_func = AsyncMock(
            side_effect=[
                Exception("Transient error"),
                "success",
            ]
        )

        result = await retryable_saver._execute_with_retry("test_op", mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self, retryable_saver):
        """Test that exhausted retries raises the last exception."""
        mock_func = AsyncMock(side_effect=Exception("Persistent error"))

        with pytest.raises(Exception, match="Persistent error"):
            await retryable_saver._execute_with_retry("test_op", mock_func)

        assert mock_func.call_count == retryable_saver.max_retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, mock_repository):
        """Test that retry delays follow exponential backoff."""
        saver = L9RetryablePostgresSaver(
            repository=mock_repository,
            max_retries=3,
            base_retry_delay=0.01,
        )

        delays = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Minimal actual sleep

        mock_func = AsyncMock(side_effect=Exception("Error"))

        with patch("asyncio.sleep", mock_sleep), pytest.raises(Exception):
            await saver._execute_with_retry("test_op", mock_func)

        # Should have 2 delays (before retry 2 and 3)
        assert len(delays) == 2
        # Delays should be exponential: 0.01, 0.02
        assert delays[0] == pytest.approx(0.01, rel=0.1)
        assert delays[1] == pytest.approx(0.02, rel=0.1)


class TestRetryablePut:
    """Test put() with retry."""

    @pytest.mark.asyncio
    async def test_put_success(
        self,
        retryable_saver,
        mock_repository,
        valid_config,
        valid_checkpoint,
        valid_metadata,
    ):
        """Test successful put operation."""
        result = await retryable_saver.put(
            valid_config, valid_checkpoint, valid_metadata, {}
        )

        assert "checkpoint_id" in result
        mock_repository.save_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_put_with_retry(
        self,
        retryable_saver,
        mock_repository,
        valid_config,
        valid_checkpoint,
        valid_metadata,
    ):
        """Test put operation succeeds after retry."""
        mock_repository.save_checkpoint.side_effect = [
            Exception("Transient"),
            "checkpoint-456",
        ]

        result = await retryable_saver.put(
            valid_config, valid_checkpoint, valid_metadata, {}
        )

        assert result["checkpoint_id"] == "checkpoint-456"
        assert mock_repository.save_checkpoint.call_count == 2


class TestRetryableGet:
    """Test get() with retry."""

    @pytest.mark.asyncio
    async def test_get_not_found(self, retryable_saver, mock_repository, valid_config):
        """Test get returns None when checkpoint not found."""
        mock_repository.get_checkpoint.return_value = None

        result = await retryable_saver.get(valid_config)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_retry(self, retryable_saver, mock_repository, valid_config):
        """Test get operation succeeds after retry."""
        mock_checkpoint = MagicMock()
        mock_checkpoint.graph_state = {"checkpoint": {"messages": []}}

        mock_repository.get_checkpoint.side_effect = [
            Exception("Transient"),
            mock_checkpoint,
        ]

        result = await retryable_saver.get(valid_config)

        assert result == {"messages": []}
        assert mock_repository.get_checkpoint.call_count == 2


# ============================================================================
# list() Method Tests
# ============================================================================


class TestListCheckpoints:
    """Test list() method implementation."""

    @pytest.mark.asyncio
    async def test_list_empty_config(self, basic_saver):
        """Test list returns empty for config without thread_id."""
        result = await basic_saver.list({})

        assert result == []

    @pytest.mark.asyncio
    async def test_list_no_thread_id(self, basic_saver):
        """Test list returns empty for config with empty configurable."""
        result = await basic_saver.list({"configurable": {}})

        assert result == []

    @pytest.mark.asyncio
    async def test_list_success(self, basic_saver, mock_repository, valid_config):
        """Test successful list operation."""
        mock_repository.list_checkpoints_by_agent.return_value = [
            {"checkpoint_id": "cp-1", "created_at": "2026-01-20"},
            {"checkpoint_id": "cp-2", "created_at": "2026-01-19"},
        ]

        result = await basic_saver.list(valid_config)

        assert len(result) == 2
        mock_repository.list_checkpoints_by_agent.assert_called_once_with(
            agent_id="cursor:test-thread-123",
            limit=100,
        )

    @pytest.mark.asyncio
    async def test_list_with_limit(self, basic_saver, mock_repository, valid_config):
        """Test list respects limit parameter."""
        mock_repository.list_checkpoints_by_agent.return_value = []

        await basic_saver.list(valid_config, limit=10)

        mock_repository.list_checkpoints_by_agent.assert_called_once_with(
            agent_id="cursor:test-thread-123",
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_list_fallback_on_missing_method(self, basic_saver, valid_config):
        """Test graceful fallback when repository lacks list method."""
        # Remove the list method
        del basic_saver._repository.list_checkpoints_by_agent

        result = await basic_saver.list(valid_config)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_handles_exception(
        self, basic_saver, mock_repository, valid_config
    ):
        """Test list handles exceptions gracefully."""
        mock_repository.list_checkpoints_by_agent.side_effect = Exception("DB Error")

        result = await basic_saver.list(valid_config)

        assert result == []


# ============================================================================
# get_pool_stats() Method Tests
# ============================================================================


class TestGetPoolStats:
    """Test get_pool_stats() method."""

    def test_pool_stats_no_repository_support(self):
        """Test pool stats when repository doesn't support it."""
        # Create repository without get_pool_stats method
        repo = MagicMock(spec=["save_checkpoint", "get_checkpoint"])
        saver = L9RetryablePostgresSaver(
            repository=repo,
            max_retries=3,
            base_retry_delay=0.01,
        )

        stats = saver.get_pool_stats()

        assert stats["monitoring_available"] is False
        assert stats["pool_size"] == -1
        assert "timestamp" in stats

    def test_pool_stats_with_repository_support(self, mock_repository):
        """Test pool stats when repository provides them."""
        mock_repository.get_pool_stats.return_value = {
            "pool_size": 10,
            "pool_available": 7,
            "requests_waiting": 0,
        }

        saver = L9RetryablePostgresSaver(repository=mock_repository)
        stats = saver.get_pool_stats()

        assert stats["monitoring_available"] is True
        assert stats["pool_size"] == 10
        assert stats["pool_available"] == 7
        assert stats["requests_waiting"] == 0

    def test_pool_stats_handles_exception(self, mock_repository):
        """Test pool stats handles exception from repository."""
        mock_repository.get_pool_stats.side_effect = Exception("Pool error")

        saver = L9RetryablePostgresSaver(repository=mock_repository)
        stats = saver.get_pool_stats()

        assert stats["monitoring_available"] is False


# ============================================================================
# Integration-Style Tests
# ============================================================================


class TestRetryableIntegration:
    """Integration-style tests for L9RetryablePostgresSaver."""

    @pytest.mark.asyncio
    async def test_full_checkpoint_lifecycle(
        self,
        retryable_saver,
        mock_repository,
        valid_config,
        valid_checkpoint,
        valid_metadata,
    ):
        """Test complete put → get → list cycle."""
        # Setup mock to return checkpoint on get
        mock_checkpoint = MagicMock()
        mock_checkpoint.graph_state = {"checkpoint": valid_checkpoint}
        mock_repository.get_checkpoint.return_value = mock_checkpoint

        # Put
        put_result = await retryable_saver.put(
            valid_config, valid_checkpoint, valid_metadata, {}
        )
        assert "checkpoint_id" in put_result

        # Get
        get_result = await retryable_saver.get(valid_config)
        assert get_result == valid_checkpoint

        # List
        mock_repository.list_checkpoints_by_agent.return_value = [
            {"checkpoint_id": put_result["checkpoint_id"]}
        ]
        list_result = await retryable_saver.list(valid_config)
        assert len(list_result) == 1
