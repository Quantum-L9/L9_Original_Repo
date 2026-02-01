from unittest.mock import AsyncMock, MagicMock

import pytest

from memory.substrate_dag import (
    SubstrateGraphState,
    _default_state,
    _get_config_dependency,
    _should_skip_embedding,
    intake_node,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("No response generated.", True),
        ("Sorry, I encountered a temporary error. Please try again.", True),
        ("This message has already been processed.", True),
        ("L9 agent executor not available. Please try again later.", True),
        ("Mac agent is not available on this server.", True),
        ("❌ Mac command error: something went wrong", True),
        ("❌ Please provide a command", True),
        ("Valid content", False),
        ("Short", True),
        ("A valid response", False),
    ],
)
def test_should_skip_embedding(text: str, expected: bool) -> None:
    """Test _should_skip_embedding function for various input cases."""
    assert _should_skip_embedding(text) == expected


def test_get_config_dependency_with_none() -> None:
    """Test _get_config_dependency with None config."""
    result = _get_config_dependency(None, "key", "default_value")
    assert result == "default_value"


def test_get_config_dependency_with_empty_config() -> None:
    """Test _get_config_dependency with empty config."""
    result = _get_config_dependency({}, "key", "default_value")
    assert result == "default_value"


def test_get_config_dependency_with_valid_key() -> None:
    """Test _get_config_dependency with valid key."""
    config = {"configurable": {"key": "value"}}
    result = _get_config_dependency(config, "key", "default_value")
    assert result == "value"


def test_get_config_dependency_with_invalid_key() -> None:
    """Test _get_config_dependency with invalid key."""
    config = {"configurable": {}}
    result = _get_config_dependency(config, "key", "default_value")
    assert result == "default_value"


def test_default_state() -> None:
    """Test _default_state function returns the expected default state."""
    expected_state = {
        "envelope": {},
        "reasoning_block": None,
        "written_tables": [],
        "embedding_id": None,
        "saved_checkpoint_id": None,
        "insights": [],
        "facts": [],
        "world_model_triggered": False,
        "errors": [],
    }
    assert _default_state() == expected_state


@pytest.mark.asyncio
async def test_intake_node_valid_input() -> None:
    """Test intake_node with valid input."""
    state = {
        "envelope": {
            "packet_type": "test_type",
            "payload": "test_payload",
        },
        "errors": [],
    }
    config = MagicMock()
    config.get.return_value = {"repository": None}

    result = await intake_node(state, config)

    assert result["envelope"]["packet_id"] is not None
    assert "timestamp" in result["envelope"]
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_intake_node_missing_packet_type() -> None:
    """Test intake_node with missing packet_type."""
    state = {
        "envelope": {
            "payload": "test_payload",
        },
        "errors": [],
    }
    config = MagicMock()
    config.get.return_value = {"repository": None}

    result = await intake_node(state, config)

    assert "Missing required field: packet_type" in result["errors"]


@pytest.mark.asyncio
async def test_intake_node_missing_payload() -> None:
    """Test intake_node with missing payload."""
    state = {
        "envelope": {
            "packet_type": "test_type",
        },
        "errors": [],
    }
    config = MagicMock()
    config.get.return_value = {"repository": None}

    result = await intake_node(state, config)

    assert "Missing required field: payload" in result["errors"]


@pytest.mark.asyncio
async def test_intake_node_with_duplicate_packet() -> None:
    """Test intake_node with a duplicate packet."""
    state = {
        "envelope": {
            "packet_type": "test_type",
            "payload": "test_payload",
            "packet_id": "12345678-1234-5678-1234-567812345678",
        },
        "errors": [],
    }
    repository_mock = AsyncMock()
    repository_mock.check_duplicate.return_value = True
    config = MagicMock()
    config.get.return_value = {"repository": repository_mock}

    result = await intake_node(state, config)

    assert any("Duplicate packet" in err for err in result["errors"])


def test_substrate_graph_state() -> None:
    """Test instantiation of SubstrateGraphState."""
    state: SubstrateGraphState = {
        "envelope": {},
        "reasoning_block": None,
        "written_tables": [],
        "embedding_id": None,
        "saved_checkpoint_id": None,
        "insights": [],
        "facts": [],
        "world_model_triggered": False,
        "errors": [],
    }
    assert isinstance(state, dict)
    assert "envelope" in state
    assert "errors" in state
    assert "facts" in state


# DORA footer
# Tests for memory.substrate_dag module
# Version: 1.1.0
# Created by: Igor Beylin
# Last updated: 2026-01-17T23:47:56Z
