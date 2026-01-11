"""Embedding tests."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_embed_text_returns_vector():
    """embed_text must return 1536-dim vector."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

    with patch(
        "src.embeddings.client.embeddings.create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        from src.embeddings import embed_text

        result = await embed_text("test")

        assert len(result) == 1536
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_embed_texts_batch():
    """embed_texts must handle batch requests."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 1536, index=0),
        MagicMock(embedding=[0.2] * 1536, index=1),
    ]

    with patch(
        "src.embeddings.client.embeddings.create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        from src.embeddings import embed_texts

        result = await embed_texts(["test1", "test2"])

        assert len(result) == 2
        assert len(result[0]) == 1536
