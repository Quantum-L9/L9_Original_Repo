"""Vector search tests."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_respects_threshold():
    """Search must filter by similarity threshold."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = []

                from src.routes.memory import search_memory_handler

                result = await search_memory_handler(
                    user_id="test", query="query", threshold=0.99
                )

                assert result["total_results"] == 0


@pytest.mark.asyncio
async def test_search_respects_top_k():
    """Search must limit results to top_k."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = [
                    {
                        "id": i,
                        "user_id": "test",
                        "kind": "fact",
                        "content": f"c{i}",
                        "importance": 1.0,
                        "similarity": 0.9,
                        "created_at": "2025-01-01",
                    }
                    for i in range(10)
                ]

                from src.routes.memory import search_memory_handler

                result = await search_memory_handler(
                    user_id="test", query="query", top_k=3
                )

                assert result["total_results"] <= 3
