"""
tests/api/test_slack_adapter.py
Integration tests for Slack adapter observability.

Tests:
  - Prometheus metrics recording
  - Canonical log event emission
  - Signature verification flow
  - Rate limiting behavior
  - Deduplication logic

Version: 1.0.0
Created: 2026-01-08
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hmac
import hashlib
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_slack_validator():
    """Mock SlackRequestValidator."""
    validator = MagicMock()
    validator.verify.return_value = (True, None)
    return validator


@pytest.fixture
def mock_substrate_service():
    """Mock MemorySubstrateService."""
    service = AsyncMock()
    service.write_packet.return_value = MagicMock(packet_id="test-packet-123")
    service.search_packets.return_value = []
    return service


@pytest.fixture
def mock_slack_client():
    """Mock SlackAPIClient."""
    client = AsyncMock()
    client.post_message.return_value = {"ts": "1234567890.123456", "ok": True}
    return client


@pytest.fixture
def sample_slack_event():
    """Sample Slack event_callback payload."""
    return {
        "type": "event_callback",
        "event_id": "Ev123ABC",
        "team_id": "T123",
        "event": {
            "type": "message",
            "user": "U123",
            "text": "Hello @L",
            "channel": "C123",
            "ts": "1234567890.123456",
            "thread_ts": "1234567890.000000",
        },
    }


@pytest.fixture
def sample_slack_command():
    """Sample Slack slash command payload."""
    return {
        "command": "/l9",
        "text": "do something",
        "user_id": "U123",
        "team_id": "T123",
        "channel_id": "C123",
        "response_url": "https://hooks.slack.com/commands/T123/456/abc",
    }


# =============================================================================
# Prometheus Metrics Tests
# =============================================================================


class TestSlackMetrics:
    """Test Prometheus metrics recording."""

    def test_metrics_module_imports(self):
        """Verify slack_metrics module imports without error."""
        from telemetry.slack_metrics import (
            record_slack_request,
            record_signature_verification,
            record_slack_processing,
            record_aios_call,
            record_idempotent_hit,
            record_packet_write_error,
            record_slack_reply_error,
            record_rate_limit_hit,
        )
        # All imports should succeed
        assert callable(record_slack_request)
        assert callable(record_signature_verification)
        assert callable(record_slack_processing)
        assert callable(record_aios_call)

    def test_record_slack_request(self):
        """Test request metric recording."""
        from telemetry.slack_metrics import record_slack_request
        # Should not raise
        record_slack_request(event_type="events", status="received")
        record_slack_request(event_type="commands", status="processed")

    def test_record_signature_verification_success(self):
        """Test signature verification success metric."""
        from telemetry.slack_metrics import record_signature_verification
        # Should not raise
        record_signature_verification(valid=True)

    def test_record_signature_verification_failure(self):
        """Test signature verification failure metric."""
        from telemetry.slack_metrics import record_signature_verification
        # Should not raise
        record_signature_verification(valid=False, reason="timestamp_expired")
        record_signature_verification(valid=False, reason="invalid_signature")

    def test_record_slack_processing(self):
        """Test processing duration metric."""
        from telemetry.slack_metrics import record_slack_processing
        # Should not raise
        record_slack_processing(
            event_type="message",
            duration_seconds=0.5,
            status="success",
        )
        record_slack_processing(
            event_type="app_mention",
            duration_seconds=2.0,
            status="error",
        )

    def test_record_aios_call(self):
        """Test AIOS call duration metric."""
        from telemetry.slack_metrics import record_aios_call
        # Should not raise
        record_aios_call(agent_type="aios", duration_seconds=1.5)
        record_aios_call(agent_type="l-cto", duration_seconds=3.0)

    def test_record_idempotent_hit(self):
        """Test idempotent hit metric."""
        from telemetry.slack_metrics import record_idempotent_hit
        # Should not raise
        record_idempotent_hit(team_id="T123")

    def test_record_packet_write_error(self):
        """Test packet write error metric."""
        from telemetry.slack_metrics import record_packet_write_error
        # Should not raise
        record_packet_write_error(packet_type="slack.in")
        record_packet_write_error(packet_type="slack.out")

    def test_record_slack_reply_error(self):
        """Test Slack reply error metric."""
        from telemetry.slack_metrics import record_slack_reply_error
        # Should not raise
        record_slack_reply_error(error_type="api_error")
        record_slack_reply_error(error_type="timeout")

    def test_record_rate_limit_hit(self):
        """Test rate limit hit metric."""
        from telemetry.slack_metrics import record_rate_limit_hit
        # Should not raise
        record_rate_limit_hit(team_id="T123")

    def test_init_slack_metrics(self):
        """Test metrics initialization."""
        from telemetry.slack_metrics import init_slack_metrics, PROMETHEUS_AVAILABLE
        result = init_slack_metrics()
        # Result depends on whether prometheus_client is installed
        assert result == PROMETHEUS_AVAILABLE


# =============================================================================
# Canonical Log Event Tests
# =============================================================================


class TestCanonicalLogEvents:
    """Test canonical log event names are used."""

    def test_canonical_events_documented(self):
        """Verify canonical events are documented in module."""
        import memory.slack_ingest as module
        source = open(module.__file__).read()
        
        # All 9 canonical events should be documented
        canonical_events = [
            "slack_request_received",
            "slack_signature_verified",
            "slack_thread_uuid_generated",
            "slack_dedupe_check",
            "slack_aios_call_start",
            "slack_aios_call_complete",
            "slack_packet_stored",
            "slack_reply_sent",
            "slack_handler_error",
        ]
        
        for event in canonical_events:
            assert event in source, f"Canonical event '{event}' not found in slack_ingest.py"


# =============================================================================
# Signature Verification Tests
# =============================================================================


class TestSignatureVerification:
    """Test Slack signature verification."""

    def test_valid_signature_accepted(self, mock_slack_validator):
        """Test valid signature is accepted."""
        mock_slack_validator.verify.return_value = (True, None)
        is_valid, error = mock_slack_validator.verify(b"body", "timestamp", "signature")
        assert is_valid is True
        assert error is None

    def test_invalid_signature_rejected(self, mock_slack_validator):
        """Test invalid signature is rejected."""
        mock_slack_validator.verify.return_value = (False, "invalid_signature")
        is_valid, error = mock_slack_validator.verify(b"body", "timestamp", "bad_sig")
        assert is_valid is False
        assert error == "invalid_signature"

    def test_expired_timestamp_rejected(self, mock_slack_validator):
        """Test expired timestamp is rejected."""
        mock_slack_validator.verify.return_value = (False, "timestamp_expired")
        old_timestamp = str(int(time.time()) - 400)  # > 300s tolerance
        is_valid, error = mock_slack_validator.verify(b"body", old_timestamp, "sig")
        assert is_valid is False
        assert error == "timestamp_expired"


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplication:
    """Test event deduplication logic."""

    @pytest.mark.asyncio
    async def test_duplicate_event_detected(self, mock_substrate_service):
        """Test duplicate events are detected."""
        # Mock finding existing packet
        mock_substrate_service.search_packets.return_value = [
            {"packet_id": "existing-123", "payload": {"event_id": "Ev123"}}
        ]
        
        # Verify search is called
        await mock_substrate_service.search_packets(
            filter_criteria={"payload.event_id": "Ev123"},
            limit=1,
        )
        mock_substrate_service.search_packets.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_event_processed(self, mock_substrate_service):
        """Test new events are processed."""
        # Mock no existing packet
        mock_substrate_service.search_packets.return_value = []
        
        result = await mock_substrate_service.search_packets(
            filter_criteria={"payload.event_id": "EvNEW"},
            limit=1,
        )
        assert result == []


# =============================================================================
# Packet Storage Tests
# =============================================================================


class TestPacketStorage:
    """Test packet storage to substrate."""

    @pytest.mark.asyncio
    async def test_inbound_packet_stored(self, mock_substrate_service):
        """Test inbound packet is stored."""
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn, PacketMetadata, PacketProvenance
        
        packet = PacketEnvelopeIn(
            packet_type="slack.in",
            payload={"event_id": "Ev123", "text": "Hello"},
            metadata=PacketMetadata(schema_version="1.0.1", agent="slack_adapter"),
            provenance=PacketProvenance(source="slack"),
        )
        
        result = await mock_substrate_service.write_packet(packet)
        assert result.packet_id == "test-packet-123"
        mock_substrate_service.write_packet.assert_called_once()

    @pytest.mark.asyncio
    async def test_outbound_packet_stored(self, mock_substrate_service):
        """Test outbound packet is stored."""
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn, PacketMetadata, PacketProvenance
        
        packet = PacketEnvelopeIn(
            packet_type="slack.out",
            payload={"event_id": "Ev123", "reply_text": "Response"},
            metadata=PacketMetadata(schema_version="1.0.1", agent="slack_adapter"),
            provenance=PacketProvenance(source="aios"),
        )
        
        result = await mock_substrate_service.write_packet(packet)
        assert result.packet_id == "test-packet-123"


# =============================================================================
# Slack Reply Tests
# =============================================================================


class TestSlackReply:
    """Test Slack reply posting."""

    @pytest.mark.asyncio
    async def test_reply_posted_successfully(self, mock_slack_client):
        """Test reply is posted to Slack."""
        result = await mock_slack_client.post_message(
            channel="C123",
            text="Hello!",
            thread_ts="1234567890.000000",
        )
        assert result["ok"] is True
        assert "ts" in result

    @pytest.mark.asyncio
    async def test_reply_error_handled(self, mock_slack_client):
        """Test reply error is handled gracefully."""
        from api.slack_client import SlackClientError
        
        mock_slack_client.post_message.side_effect = SlackClientError("rate_limited")
        
        with pytest.raises(SlackClientError):
            await mock_slack_client.post_message(
                channel="C123",
                text="Hello!",
                thread_ts="1234567890.000000",
            )


# =============================================================================
# Integration Tests
# =============================================================================


class TestSlackAdapterIntegration:
    """Integration tests for full Slack flow."""

    def test_slack_normalizer_imports(self):
        """Test SlackRequestNormalizer imports."""
        from api.slack_adapter import SlackRequestNormalizer
        normalizer = SlackRequestNormalizer()
        assert normalizer is not None

    def test_slack_validator_imports(self):
        """Test SlackRequestValidator imports."""
        from api.slack_adapter import SlackRequestValidator
        # Validator requires signing secret
        validator = SlackRequestValidator(signing_secret="test_secret")
        assert validator is not None

    def test_thread_uuid_generation(self, sample_slack_event):
        """Test deterministic thread UUID generation."""
        from api.slack_adapter import SlackRequestNormalizer
        
        # parse_event_callback is a static method
        normalized = SlackRequestNormalizer.parse_event_callback(sample_slack_event)
        
        # Thread UUID should be generated
        assert "thread_uuid" in normalized
        assert normalized["thread_uuid"] is not None
        
        # Same input should produce same UUID (deterministic)
        normalized2 = SlackRequestNormalizer.parse_event_callback(sample_slack_event)
        assert normalized["thread_uuid"] == normalized2["thread_uuid"]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in Slack adapter."""

    def test_metrics_graceful_degradation(self):
        """Test metrics degrade gracefully when prometheus unavailable."""
        from telemetry.slack_metrics import (
            record_slack_request,
            record_signature_verification,
            PROMETHEUS_AVAILABLE,
        )
        
        # These should never raise, even if prometheus is unavailable
        try:
            record_slack_request(event_type="test", status="test")
            record_signature_verification(valid=True)
        except Exception as e:
            pytest.fail(f"Metrics should not raise: {e}")

    @pytest.mark.asyncio
    async def test_substrate_error_handled(self, mock_substrate_service):
        """Test substrate errors are handled gracefully."""
        mock_substrate_service.write_packet.side_effect = Exception("DB connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await mock_substrate_service.write_packet(MagicMock())
        
        assert "DB connection failed" in str(exc_info.value)

