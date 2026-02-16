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

from core.decorators import must_stay_async

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

import os
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
# Slack File Upload Tests (GMP: slack_file_tools)
# =============================================================================


@pytest.mark.asyncio
async def test_slack_file_upload_success(tmp_path):
    """Test successful file upload to a channel."""
    # Create a temporary test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    from runtime.l_tools import slack_file_upload

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.upload_file_to_slack") as mock_upload:
            mock_upload.return_value = {
                "file_id": "F12345",
                "url": "https://files.slack.com/...",
                "channel": "C12345678",
                "ts": "1234567890.123456",
                "title": "test.txt",
            }

            result = await slack_file_upload(
                channel="C12345678",
                file_path=str(test_file),
                title="Test File",
            )

    assert result["status"] == "success"
    assert result["file_id"] == "F12345"
    assert result["channel"] == "C12345678"


@pytest.mark.asyncio
async def test_slack_file_upload_missing_token(tmp_path):
    """Test error handling when SLACK_BOT_TOKEN is not configured."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    from runtime.l_tools import slack_file_upload

    with patch.dict(os.environ, {}, clear=True):
        # Ensure SLACK_BOT_TOKEN is not set
        os.environ.pop("SLACK_BOT_TOKEN", None)
        result = await slack_file_upload(
            channel="C12345678",
            file_path=str(test_file),
        )

    assert result["status"] == "error"
    assert result["error"] == "SLACK_BOT_TOKEN not configured"


@pytest.mark.asyncio
async def test_slack_file_upload_file_not_found():
    """Test error handling when file doesn't exist."""
    from runtime.l_tools import slack_file_upload

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.upload_file_to_slack") as mock_upload:
            mock_upload.side_effect = ValueError(
                "File not found: /nonexistent/file.txt"
            )

            result = await slack_file_upload(
                channel="C12345678",
                file_path="/nonexistent/file.txt",
            )

    assert result["status"] == "error"
    assert "File not found" in result["error"]


# =============================================================================
# Slack File Fetch Tests (GMP: slack_file_tools)
# =============================================================================


@pytest.mark.asyncio
async def test_slack_file_fetch_success():
    """Test successful file fetch by ID."""
    from runtime.l_tools import slack_file_fetch

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.fetch_file_by_id") as mock_fetch:
            mock_fetch.return_value = {
                "file_id": "F12345",
                "filename": "report.pdf",
                "mimetype": "application/pdf",
                "size_bytes": 102400,
                "url_private": "https://files.slack.com/...",
                "artifact": {"path": "/path/to/saved/file.pdf"},
            }

            result = await slack_file_fetch(
                file_id="F12345",
                save_locally=True,
                enrich=True,
            )

    assert result["status"] == "success"
    assert result["file_id"] == "F12345"
    assert result["filename"] == "report.pdf"
    assert "artifact" in result


@pytest.mark.asyncio
async def test_slack_file_fetch_missing_token():
    """Test error handling when SLACK_BOT_TOKEN is not configured."""
    from runtime.l_tools import slack_file_fetch

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SLACK_BOT_TOKEN", None)
        result = await slack_file_fetch(file_id="F12345")

    assert result["status"] == "error"
    assert result["error"] == "SLACK_BOT_TOKEN not configured"


@pytest.mark.asyncio
async def test_slack_file_fetch_invalid_file_id():
    """Test error handling for invalid file ID."""
    from runtime.l_tools import slack_file_fetch

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.fetch_file_by_id") as mock_fetch:
            mock_fetch.side_effect = Exception("file_not_found")

            result = await slack_file_fetch(file_id="F_INVALID")

    assert result["status"] == "error"
    assert "file_not_found" in result["error"]


# =============================================================================
# Slack File List Tests (GMP: slack_file_tools)
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_slack_file_list_success():
    """Test successful file listing for a channel."""
    from runtime.l_tools import slack_file_list

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.list_channel_files") as mock_list:
            mock_list.return_value = [
                {
                    "file_id": "F12345",
                    "name": "report.pdf",
                    "mimetype": "application/pdf",
                    "size": 102400,
                    "created": 1234567890,
                },
                {
                    "file_id": "F67890",
                    "name": "image.png",
                    "mimetype": "image/png",
                    "size": 51200,
                    "created": 1234567891,
                },
            ]

            result = await slack_file_list(
                channel="C12345678",
                count=20,
            )

    assert result["status"] == "success"
    assert result["count"] == 2
    assert len(result["files"]) == 2
    assert result["files"][0]["file_id"] == "F12345"


@pytest.mark.asyncio
async def test_slack_file_list_missing_token():
    """Test error handling when SLACK_BOT_TOKEN is not configured."""
    from runtime.l_tools import slack_file_list

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SLACK_BOT_TOKEN", None)
        result = await slack_file_list(channel="C12345678")

    assert result["status"] == "error"
    assert result["error"] == "SLACK_BOT_TOKEN not configured"


@pytest.mark.asyncio
async def test_slack_file_list_empty_channel():
    """Test successful listing for channel with no files."""
    from runtime.l_tools import slack_file_list

    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        with patch("runtime.l_tools.list_channel_files") as mock_list:
            mock_list.return_value = []

            result = await slack_file_list(channel="C12345678")

    assert result["status"] == "success"
    assert result["count"] == 0
    assert result["files"] == []


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
