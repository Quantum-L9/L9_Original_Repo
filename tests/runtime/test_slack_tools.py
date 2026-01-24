"""
L9 Tests - Slack Tools Test Suite
==================================

Comprehensive test suite for Slack integration tools, including:
- slack_send: Send messages to Slack channels or DMs
- Error handling and edge cases
- Integration with SlackAPIClient

Version: 1.0.0
Author: L9 Testing Team
Created: 2026-01-21
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Tools Test Suite",
    "module_version": "1.0.0",
    "created_by": "L9 Testing Team",
    "created_at": "2026-01-21T00:00:00Z",
    "updated_at": "2026-01-21T00:00:00Z",
    "layer": "tests",
    "domain": "runtime",
    "module_name": "test_slack_tools",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "tested_modules": ["runtime.l_tools"],
        "dependencies": ["api.slack_client"],
    },
}
# ============================================================================

from unittest.mock import AsyncMock, patch

import pytest

from api.slack_client import SlackClientError
# Import the tool under test
from runtime.l_tools import slack_send

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_slack_client():
    """Mock SlackAPIClient for testing."""
    client = AsyncMock()
    client.post_message = AsyncMock()
    return client


@pytest.fixture
def mock_env_with_token(monkeypatch):
    """Set SLACK_BOT_TOKEN environment variable."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token-12345")


@pytest.fixture
def mock_env_without_token(monkeypatch):
    """Remove SLACK_BOT_TOKEN environment variable."""
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)


# =============================================================================
# Happy Path Tests
# =============================================================================


@pytest.mark.asyncio
async def test_slack_send_success(mock_env_with_token, mock_slack_client):
    """Test successful message send to a channel."""
    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123456",
        "channel": "C12345678",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(
                channel="C12345678", text="Hello from L9!", thread_ts=None
            )

    # Assertions
    assert result["status"] == "success"
    assert result["channel"] == "C12345678"
    assert result["ts"] == "1234567890.123456"
    assert result["message"] == "Message sent successfully"

    # Verify SlackAPIClient was called correctly
    mock_slack_client.post_message.assert_called_once_with(
        channel="C12345678", text="Hello from L9!", thread_ts=None
    )


@pytest.mark.asyncio
async def test_slack_send_with_thread(mock_env_with_token, mock_slack_client):
    """Test successful message send in a thread."""
    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123457",
        "channel": "C12345678",
        "thread_ts": "1234567890.123456",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(
                channel="C12345678",
                text="Thread reply",
                thread_ts="1234567890.123456",
            )

    # Assertions
    assert result["status"] == "success"
    assert result["ts"] == "1234567890.123457"

    # Verify thread_ts was passed correctly
    mock_slack_client.post_message.assert_called_once_with(
        channel="C12345678", text="Thread reply", thread_ts="1234567890.123456"
    )


@pytest.mark.asyncio
async def test_slack_send_dm(mock_env_with_token, mock_slack_client):
    """Test successful DM send to a user."""
    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123458",
        "channel": "D12345678",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="U12345678", text="Direct message")

    # Assertions
    assert result["status"] == "success"
    # Note: Slack API may return a different channel ID for DMs
    assert "ts" in result


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_slack_send_missing_token(mock_env_without_token):
    """Test error handling when SLACK_BOT_TOKEN is not configured."""
    result = await slack_send(channel="C12345678", text="Test message")

    # Assertions
    assert result["status"] == "error"
    assert result["error"] == "SLACK_BOT_TOKEN not configured"


@pytest.mark.asyncio
async def test_slack_send_slack_client_error(mock_env_with_token, mock_slack_client):
    """Test error handling when SlackAPIClient raises SlackClientError."""
    # Setup mock to raise error
    mock_slack_client.post_message.side_effect = SlackClientError(
        "channel_not_found", "Channel not found"
    )

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="C_INVALID", text="Test message")

    # Assertions
    assert result["status"] == "error"
    assert "channel_not_found" in result["error"]


@pytest.mark.asyncio
async def test_slack_send_generic_exception(mock_env_with_token, mock_slack_client):
    """Test error handling for generic exceptions."""
    # Setup mock to raise generic exception
    mock_slack_client.post_message.side_effect = Exception("Unexpected network error")

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="C12345678", text="Test message")

    # Assertions
    assert result["status"] == "error"
    assert "Unexpected network error" in result["error"]


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_slack_send_empty_text(mock_env_with_token, mock_slack_client):
    """Test sending an empty message (should still call API)."""
    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123459",
        "channel": "C12345678",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="C12345678", text="")

    # Assertions
    assert result["status"] == "success"
    mock_slack_client.post_message.assert_called_once_with(
        channel="C12345678", text="", thread_ts=None
    )


@pytest.mark.asyncio
async def test_slack_send_long_text(mock_env_with_token, mock_slack_client):
    """Test sending a very long message (Slack has a 40k char limit)."""
    long_text = "A" * 5000  # 5k chars, well within limit

    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123460",
        "channel": "C12345678",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="C12345678", text=long_text)

    # Assertions
    assert result["status"] == "success"
    mock_slack_client.post_message.assert_called_once()


@pytest.mark.asyncio
async def test_slack_send_special_characters(mock_env_with_token, mock_slack_client):
    """Test sending a message with special characters and emojis."""
    special_text = "Hello! 👋 <@U12345> Check this: https://example.com & more"

    # Setup mock response
    mock_slack_client.post_message.return_value = {
        "ok": True,
        "ts": "1234567890.123461",
        "channel": "C12345678",
    }

    # Patch SlackAPIClient
    with patch("runtime.l_tools.SlackAPIClient", return_value=mock_slack_client):
        with patch("runtime.l_tools.httpx.AsyncClient"):
            result = await slack_send(channel="C12345678", text=special_text)

    # Assertions
    assert result["status"] == "success"
    mock_slack_client.post_message.assert_called_once_with(
        channel="C12345678", text=special_text, thread_ts=None
    )


# =============================================================================
# Integration Tests (require actual Slack API or mock server)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_slack_send_integration():
    """
    Integration test for slack_send with real Slack API.

    NOTE: This test is marked as 'integration' and requires:
    - SLACK_BOT_TOKEN environment variable
    - A valid Slack workspace with a test channel
    - Network connectivity

    Run with: pytest -m integration
    """
    pytest.skip("Integration test requires real Slack API credentials")
    # Uncomment and configure for actual integration testing
    # result = await slack_send(
    #     channel="C_TEST_CHANNEL",
    #     text="Integration test message from L9"
    # )
    # assert result["status"] == "success"


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEST-SLACK-TOOLS",
    "governance_level": "standard",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-21T00:00:00Z",
    "test_coverage": "comprehensive",
}
# ============================================================================
