from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agents.executor import _generate_tasks_from_query


@pytest.mark.asyncio
async def test_generate_tasks_from_query_happy_path_gmp():
    """Test _generate_tasks_from_query with a valid GMP query."""
    query = "Please run the governance process."
    expected = [
        {
            "name": "GMP Run: Please run the governance process.",
            "payload": {
                "type": "gmp_run",
                "query": query,
                "status": "pending_igor_approval",
            },
            "handler": "gmp_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_happy_path_git():
    """Test _generate_tasks_from_query with a valid Git commit query."""
    query = "Commit changes to the repository."
    expected = [
        {
            "name": "Git Commit: Commit changes to the repository.",
            "payload": {
                "type": "git_commit",
                "query": query,
                "status": "pending_igor_approval",
            },
            "handler": "git_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_happy_path_long_plan():
    """Test _generate_tasks_from_query with a valid long plan query."""
    query = "Create a long-term plan for project X."
    expected = [
        {
            "name": "Long Plan: Create a long-term plan for project X.",
            "payload": {
                "type": "long_plan",
                "goal": query,
                "status": "pending",
            },
            "handler": "long_plan_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_empty_query():
    """Test _generate_tasks_from_query with an empty query."""
    query = ""
    expected = []

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_none_query():
    """Test _generate_tasks_from_query with a None query."""
    query = None
    expected = []

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_edge_case_long_query():
    """Test _generate_tasks_from_query with a long query."""
    query = "GMP " + "a" * 1000  # Long query to test boundary
    expected = [
        {
            "name": f"GMP Run: {query[:50]}",
            "payload": {
                "type": "gmp_run",
                "query": query,
                "status": "pending_igor_approval",
            },
            "handler": "gmp_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_unrecognized_query():
    """Test _generate_tasks_from_query with an unrecognized query falls back to agent_executor."""
    query = "This query does not match any known patterns."
    # Unrecognized queries fall back to agent_executor handler
    expected = [
        {
            "name": f"Agent Task: {query}",
            "payload": {
                "type": "agent_task",
                "query": query,
                "status": "pending",
            },
            "handler": "agent_executor",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_multiple_keywords():
    """Test _generate_tasks_from_query with multiple keywords in the query."""
    query = "GMP and Git commit tasks should be processed."
    expected = [
        {
            "name": "GMP Run: GMP and Git commit tasks should be processed.",
            "payload": {
                "type": "gmp_run",
                "query": query,
                "status": "pending_igor_approval",
            },
            "handler": "gmp_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_case_insensitivity():
    """Test _generate_tasks_from_query with case-insensitive keywords."""
    query = "Please run the Governance process."
    expected = [
        {
            "name": "GMP Run: Please run the Governance process.",
            "payload": {
                "type": "gmp_run",
                "query": query,
                "status": "pending_igor_approval",
            },
            "handler": "gmp_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_tasks_from_query_leading_trailing_spaces():
    """Test _generate_tasks_from_query preserves original query including whitespace."""
    query = "   Git commit changes   "
    # Note: The function preserves original query including whitespace
    expected = [
        {
            "name": f"Git Commit: {query[:50]}",  # Uses original query with whitespace
            "payload": {
                "type": "git_commit",
                "query": query,  # Original query preserved
                "status": "pending_igor_approval",
            },
            "handler": "git_worker",
            "priority": 5,
        }
    ]

    result = await _generate_tasks_from_query(query)
    assert result == expected
