"""Memory operations tests."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_save_memory_creates_embedding():
    """Memory save must generate embedding."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_one", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = {
                    "id": 1,
                    "user_id": "test",
                    "kind": "fact",
                    "content": "test",
                    "importance": 1.0,
                    "created_at": "2025-01-01T00:00:00Z",
                }

                from src.routes.memory import save_memory_handler

                result = await save_memory_handler(
                    user_id="test", content="test content", kind="fact", duration="long"
                )

                mock_embed.assert_called_once_with("test content")
                assert result["id"] == 1


@pytest.mark.asyncio
async def test_search_returns_similar():
    """Search must return semantically similar memories."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = [
                    {
                        "id": 1,
                        "user_id": "test",
                        "kind": "fact",
                        "content": "similar",
                        "importance": 1.0,
                        "similarity": 0.95,
                        "created_at": "2025-01-01T00:00:00Z",
                    }
                ]

                from src.routes.memory import search_memory_handler

                result = await search_memory_handler(user_id="test", query="test query")

                assert result["total_results"] == 1
                assert result["results"][0]["similarity"] == 0.95


@pytest.mark.asyncio
async def test_duplicate_memory_compounds():
    """Repeated similar memories should compound."""
    with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
        with patch(
            "src.routes.memory.fetch_one", new_callable=AsyncMock
        ) as mock_fetch_one:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                with patch("src.routes.memory.settings") as mock_settings:
                    mock_settings.COMPOUNDING_ENABLED = True
                    mock_settings.COMPOUNDING_MIN_COUNT = 2
                    mock_fetch.return_value = [
                        {
                            "id": 1,
                            "content": "a",
                            "embedding": [0.1] * 1536,
                            "importance": 0.5,
                            "access_count": 1,
                            "created_at": "2025-01-01",
                            "tags": [],
                        },
                        {
                            "id": 2,
                            "content": "a",
                            "embedding": [0.1] * 1536,
                            "importance": 0.5,
                            "access_count": 1,
                            "created_at": "2025-01-02",
                            "tags": [],
                        },
                    ]
                    mock_fetch_one.return_value = {"similarity": 0.95}

                    from src.routes.memory import compound_similar_memories

                    result = await compound_similar_memories(
                        user_id="test", threshold=0.92
                    )

                    assert result["status"] == "completed"


# =============================================================================
# 10x Memory Upgrade Tests
# =============================================================================


@pytest.mark.asyncio
async def test_context_injection_retrieves_relevant_memories():
    """Context injection should retrieve semantically relevant memories."""
    with patch("src.routes.memory.search_memory_handler", new_callable=AsyncMock) as mock_search:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_search.return_value = {
                    "results": [
                        {
                            "id": 1,
                            "user_id": "test",
                            "kind": "fact",
                            "content": "relevant context",
                            "importance": 0.9,
                            "similarity": 0.85,
                        }
                    ],
                    "total_results": 1,
                }
                mock_fetch.return_value = []  # No recent context

                from src.routes.memory import get_context_injection

                result = await get_context_injection(
                    task_description="working on authentication",
                    user_id="test",
                    top_k=5,
                    include_recent=True,
                )

                assert result["total_injected"] >= 1
                assert "retrieval_time_ms" in result


@pytest.mark.asyncio
async def test_session_learning_extraction():
    """Session learning extraction should store multiple memory types."""
    with patch("src.routes.memory.save_memory_handler", new_callable=AsyncMock) as mock_save:
        with patch("src.routes.memory.execute", new_callable=AsyncMock):
            mock_save.return_value = {"id": 1}

            from src.routes.memory import extract_session_learnings

            result = await extract_session_learnings(
                user_id="test",
                session_id="session-123",
                session_summary="Fixed auth bug and added rate limiting",
                key_decisions=["Use Redis for rate limiting"],
                errors_encountered=["Token expiry bug - fixed by refreshing"],
                successes=["Rate limiting works well"],
            )

            # Should store: 1 summary + 1 decision + 1 error + 1 success = 4
            assert result["learnings_stored"] == 4
            assert "context" in result["kinds_created"]
            assert "decision" in result["kinds_created"]


@pytest.mark.asyncio
async def test_proactive_suggestions():
    """Proactive suggestions should surface relevant past experiences."""
    with patch("src.routes.memory.search_memory_handler", new_callable=AsyncMock) as mock_search:
        with patch("src.routes.memory.execute", new_callable=AsyncMock):
            mock_search.return_value = {
                "results": [
                    {
                        "id": 1,
                        "user_id": "test",
                        "kind": "error",
                        "content": "timeout error - increase timeout",
                        "importance": 0.9,
                        "similarity": 0.8,
                    }
                ],
                "total_results": 1,
            }

            from src.routes.memory import get_proactive_suggestions

            result = await get_proactive_suggestions(
                current_context="debugging timeout issue",
                user_id="test",
                include_error_fixes=True,
                include_preferences=True,
            )

            assert "suggestions" in result
            assert "error_fix_pairs" in result
            assert "recall_time_ms" in result


@pytest.mark.asyncio
async def test_temporal_query():
    """Temporal query should return memories in time range."""
    with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
        with patch("src.routes.memory.fetch_one", new_callable=AsyncMock) as mock_fetch_one:
            mock_fetch.return_value = [
                {
                    "id": 1,
                    "user_id": "test",
                    "kind": "fact",
                    "content": "recent memory",
                    "importance": 0.8,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "tags": [],
                }
            ]
            mock_fetch_one.return_value = {"cnt": 0}

            from src.routes.memory import query_temporal

            result = await query_temporal(
                user_id="test",
                since="2025-01-01T00:00:00",
                until="2025-01-02T00:00:00",
                operation="changes",
            )

            assert len(result["memories"]) == 1
            assert "created_count" in result
            assert "period_start" in result


@pytest.mark.asyncio
async def test_save_with_confidence():
    """Save with confidence should scale importance and add tags."""
    with patch("src.routes.memory.save_memory_handler", new_callable=AsyncMock) as mock_save:
        with patch("src.routes.memory.execute", new_callable=AsyncMock):
            mock_save.return_value = {"id": 1, "importance": 0.7}

            from src.routes.memory import save_memory_with_confidence

            result = await save_memory_with_confidence(
                user_id="test",
                content="I think this is correct",
                kind="fact",
                duration="long",
                confidence=0.7,  # Medium confidence
                source="inferred",
            )

            # Verify save_memory_handler was called with scaled importance
            call_args = mock_save.call_args
            assert call_args[1]["importance"] == 0.7  # 1.0 * 0.7
            assert "confidence:medium" in call_args[1]["tags"]
