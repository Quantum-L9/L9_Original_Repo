"""
Unit Tests for Slack Adapter.

Scope:
  - Signature verification (pass/fail)
  - URL verification (challenge echo)
  - Thread UUID derivation (deterministic)
  - Event parsing and normalization
  - Deduplication logic (high-level)

Forbidden:
  - No real Slack API calls
  - No real database calls
  - No integration tests with live substrate

All tests use mocks and fixtures.
"""

import sys
from pathlib import Path

# Add project root to path before any imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import hmac
import hashlib
import time
from unittest.mock import Mock, AsyncMock

# Import after path is set - use absolute path
# Use absolute path to project root
abs_project_root = str(Path(__file__).parent.parent.absolute())
if abs_project_root not in sys.path:
    sys.path.insert(0, abs_project_root)

from api.slack_adapter import (
    SlackRequestValidator,
    SlackRequestNormalizer,
)
from api.slack_client import SlackAPIClient, SlackClientError


class TestSlackSignatureVerification:
    """Test Slack HMAC-SHA256 signature verification."""

    def setup_method(self):
        self.signing_secret = "test_secret_123"
        self.validator = SlackRequestValidator(self.signing_secret)

    def test_signature_verification_success(self):
        """Valid signature should pass verification."""
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'

        signed_content = f"v0:{timestamp}:{body}"
        expected_hash = hmac.new(
            self.signing_secret.encode(), signed_content.encode(), hashlib.sha256
        ).hexdigest()
        signature = f"v0={expected_hash}"

        is_valid, error = self.validator.verify(body.encode(), timestamp, signature)

        assert is_valid is True
        assert error is None

    def test_signature_verification_failure(self):
        """Invalid signature should fail verification."""
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification"}'
        signature = "v0=invalid_hash"

        is_valid, error = self.validator.verify(body.encode(), timestamp, signature)

        assert is_valid is False
        assert error is not None

    def test_signature_verification_stale_timestamp(self):
        """Timestamp outside tolerance window should fail."""
        stale_timestamp = str(int(time.time()) - 400)  # 400 seconds ago (tolerance: 300)
        body = '{"type":"url_verification"}'

        signed_content = f"v0:{stale_timestamp}:{body}"
        expected_hash = hmac.new(
            self.signing_secret.encode(), signed_content.encode(), hashlib.sha256
        ).hexdigest()
        signature = f"v0={expected_hash}"

        is_valid, error = self.validator.verify(body.encode(), stale_timestamp, signature)

        assert is_valid is False
        assert "stale" in error.lower()

    def test_signature_verification_invalid_timestamp_format(self):
        """Non-integer timestamp should fail."""
        timestamp = "invalid_timestamp"
        body = '{"type":"url_verification"}'
        signature = "v0=hash"

        is_valid, error = self.validator.verify(body.encode(), timestamp, signature)

        assert is_valid is False
        assert "timestamp format" in error.lower()

    def test_signature_verification_missing_headers(self):
        """Missing headers should fail gracefully."""
        body = '{"type":"url_verification"}'

        # Missing timestamp
        is_valid, error = self.validator.verify(body.encode(), None, "v0=hash")
        assert is_valid is False
        assert "Missing" in error

        # Missing signature
        is_valid, error = self.validator.verify(body.encode(), str(int(time.time())), None)
        assert is_valid is False
        assert "Missing" in error


class TestSlackRequestNormalizer:
    """Test Slack request normalization."""

    def test_parse_event_callback_basic(self):
        """Parse basic event callback with message."""
        payload = {
            "team_id": "T123",
            "enterprise_id": "E456",
            "event": {
                "type": "message",
                "user": "U789",
                "text": "hello",
                "ts": "1234567890.123456",
                "channel": "C111",
            },
            "event_id": "Ev222",
        }

        result = SlackRequestNormalizer.parse_event_callback(payload)

        assert result["team_id"] == "T123"
        assert result["channel_id"] == "C111"
        assert result["user_id"] == "U789"
        assert result["text"] == "hello"
        assert result["event_id"] == "Ev222"
        assert result["thread_ts"] == "1234567890.123456"  # Falls back to ts
        assert result["channel_type"] == "public"

        # Check thread UUID is deterministic
        assert result["thread_uuid"]
        assert len(result["thread_uuid"]) == 36  # UUID string length

    def test_parse_event_callback_with_thread(self):
        """Parse event callback with thread_ts."""
        payload = {
            "team_id": "T123",
            "event": {
                "type": "message",
                "user": "U789",
                "text": "reply",
                "ts": "1234567890.654321",
                "thread_ts": "1234567890.123456",  # Thread root
                "channel": "G111",  # Private channel
            },
            "event_id": "Ev222",
        }

        result = SlackRequestNormalizer.parse_event_callback(payload)

        assert result["thread_ts"] == "1234567890.123456"  # Uses thread_ts, not ts
        assert result["channel_type"] == "private"  # G = private

    def test_parse_event_callback_unknown_channel_type(self):
        """Parse event callback with unknown channel type."""
        payload = {
            "team_id": "T123",
            "event": {
                "type": "message",
                "user": "U789",
                "text": "hello",
                "ts": "1234567890.123456",
                "channel": "D111",  # DM channel (not C or G)
            },
            "event_id": "Ev222",
        }

        result = SlackRequestNormalizer.parse_event_callback(payload)

        assert result["channel_type"] == "unknown"

    def test_thread_uuid_deterministic(self):
        """Thread UUID should be deterministic (UUIDv5)."""
        team_id = "T123"
        channel_id = "C456"
        thread_ts = "1234567890.123456"

        uuid_1 = SlackRequestNormalizer._generate_thread_uuid(team_id, channel_id, thread_ts)
        uuid_2 = SlackRequestNormalizer._generate_thread_uuid(team_id, channel_id, thread_ts)

        assert uuid_1 == uuid_2  # Deterministic
        assert len(uuid_1) == 36  # Valid UUID string

    def test_parse_command(self):
        """Parse slash command."""
        payload = {
            "team_id": "T123",
            "channel_id": "C111",
            "user_id": "U789",
            "command": "/l9",
            "text": "do make me a report",
            "response_url": "https://hooks.slack.com/...",
            "trigger_id": "trigger123",
        }

        result = SlackRequestNormalizer.parse_command(payload)

        assert result["team_id"] == "T123"
        assert result["command"] == "/l9"
        assert result["text"] == "do make me a report"
        assert result["response_url"] == "https://hooks.slack.com/..."
        assert result["thread_uuid"]  # Command has thread UUID for dedup


class TestSlackAPIClient:
    """Test Slack API client."""

    @pytest.mark.asyncio
    async def test_post_message_success(self):
        """Successful message post."""
        # httpx.AsyncClient.post() returns Response directly (not async context manager)
        mock_http = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "channel": "C111",
            "ts": "1234567890.123456",
        }
        mock_response.raise_for_status = Mock()  # No-op
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SlackAPIClient("xoxb-test", mock_http)

        result = await client.post_message(
            channel="C111",
            text="hello",
            thread_ts="1234567890.000000",
        )

        assert result["ok"] is True
        assert result["ts"] == "1234567890.123456"
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_message_failure(self):
        """Failed message post."""
        mock_http = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "channel_not_found",
        }
        mock_response.raise_for_status = Mock()  # No-op
        mock_http.post = AsyncMock(return_value=mock_response)

        client = SlackAPIClient("xoxb-test", mock_http)

        with pytest.raises(SlackClientError, match="Slack API error"):
            await client.post_message(channel="C999", text="hello")

    @pytest.mark.asyncio
    async def test_post_message_timeout(self):
        """Timeout handling."""
        import httpx

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        client = SlackAPIClient("xoxb-test", mock_http)

        with pytest.raises(SlackClientError, match="timed out"):
            await client.post_message(channel="C111", text="hello")

    def test_post_message_missing_bot_token(self):
        """Missing bot token should raise."""
        mock_http = AsyncMock()

        with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
            SlackAPIClient("", mock_http)

    def test_post_message_missing_http_client(self):
        """Missing http client should raise."""
        with pytest.raises(ValueError, match="http_client"):
            SlackAPIClient("xoxb-test", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
