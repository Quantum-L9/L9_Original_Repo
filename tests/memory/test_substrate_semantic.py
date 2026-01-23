"""
Tests for memory/substrate_semantic.py — OpenAIEmbeddingProvider retry logic.

GMP-77: Add unit tests for retry behavior added in Patches1.md.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.substrate_semantic import OpenAIEmbeddingProvider


class TestOpenAIEmbeddingProviderRetry:
    """Tests for OpenAIEmbeddingProvider retry logic."""

    @pytest.fixture
    def provider(self):
        """Create provider with short backoff for fast tests."""
        return OpenAIEmbeddingProvider(
            model="text-embedding-3-large",
            dimensions=1536,
            api_key="test-key",
            max_retries=3,
            base_backoff=0.01,  # Fast backoff for tests
        )

    @pytest.fixture
    def mock_embedding_response(self):
        """Create a mock OpenAI embedding response."""
        mock_data = MagicMock()
        mock_data.embedding = [0.1] * 1536
        mock_data.index = 0

        mock_response = MagicMock()
        mock_response.data = [mock_data]
        return mock_response

    @pytest.fixture
    def mock_batch_response(self):
        """Create a mock OpenAI batch embedding response."""
        mock_data_1 = MagicMock()
        mock_data_1.embedding = [0.1] * 1536
        mock_data_1.index = 0

        mock_data_2 = MagicMock()
        mock_data_2.embedding = [0.2] * 1536
        mock_data_2.index = 1

        mock_response = MagicMock()
        mock_response.data = [mock_data_1, mock_data_2]
        return mock_response

    @pytest.mark.asyncio
    async def test_embed_text_success_no_retry(self, provider, mock_embedding_response):
        """Test that successful first call doesn't retry."""
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.embed_text("test text")

        assert len(result) == 1536
        assert result[0] == 0.1
        # Verify create was called exactly once (no retries)
        assert mock_client.embeddings.create.call_count == 1

    @pytest.mark.asyncio
    async def test_embed_text_retry_then_success(self, provider, mock_embedding_response):
        """Test that transient failure triggers retry and succeeds."""
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        # First call fails, second succeeds
        mock_client.embeddings.create = AsyncMock(
            side_effect=[
                Exception("Transient API error"),
                mock_embedding_response,
            ]
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.embed_text("test text")

        assert len(result) == 1536
        # Verify create was called twice (1 failure + 1 success)
        assert mock_client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_text_max_retries_exceeded(self, provider):
        """Test that RuntimeError is raised after max retries exhausted."""
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        # All calls fail
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("Persistent API error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.embed_text("test text")

        assert "failed after" in str(exc_info.value)
        assert "retries" in str(exc_info.value)
        # Verify create was called max_retries times
        assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_embed_batch_retry_then_success(self, provider, mock_batch_response):
        """Test that batch embed retries on transient failure."""
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        # First call fails, second succeeds
        mock_client.embeddings.create = AsyncMock(
            side_effect=[
                Exception("Transient API error"),
                mock_batch_response,
            ]
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.embed_batch(["text 1", "text 2"])

        assert len(result) == 2
        assert len(result[0]) == 1536
        assert len(result[1]) == 1536
        # Verify create was called twice (1 failure + 1 success)
        assert mock_client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_batch_max_retries_exceeded(self, provider):
        """Test that batch embed raises RuntimeError after max retries."""
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        # All calls fail
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("Persistent API error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.embed_batch(["text 1", "text 2"])

        assert "failed after" in str(exc_info.value)
        assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_preserves_original_exception(self, provider):
        """Test that original exception is chained to RuntimeError."""
        original_error = ValueError("Original cause")
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        mock_client.embeddings.create = AsyncMock(side_effect=original_error)

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.embed_text("test text")

        # Verify exception chaining
        assert exc_info.value.__cause__ is original_error
