"""
Slack Webhook → Task Dispatch Integration Tests

Tests the flow: Slack Event → Adapter → Normalizer → Task Router
"""

import hashlib
import hmac
import time

import pytest

pytestmark = pytest.mark.integration


class TestSlackDispatchIntegration:
    """Test Slack webhook to task dispatch integration."""

    def test_slack_adapter_normalizes_event(self):
        """Slack adapter normalizes event callback."""
        from api.slack_adapter import SlackRequestNormalizer

        normalizer = SlackRequestNormalizer()

        raw_event = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "Hello L9",
                "user": "U123",
                "channel": "C456",
                "ts": "1234567890.123456",
            },
            "team_id": "T789",
        }

        normalized = normalizer.parse_event_callback(raw_event)

        assert normalized is not None
        assert normalized.get("text") == "Hello L9"
        assert normalized.get("user_id") == "U123"

    def test_signature_verification_integration(self):
        """Signature verification works with valid signature."""
        from api.slack_adapter import SlackRequestValidator

        signing_secret = "test_secret"
        verifier = SlackRequestValidator(signing_secret)

        timestamp = str(int(time.time()))
        body = b'{"test": "body"}'

        # Create valid signature
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
            ).hexdigest()
        )

        is_valid, error = verifier.verify(body, timestamp, signature)
        assert is_valid is True
        assert error is None

    def test_invalid_signature_rejected(self):
        """Invalid signature is rejected."""
        from api.slack_adapter import SlackRequestValidator

        verifier = SlackRequestValidator("real_secret")

        is_valid, error = verifier.verify(
            b'{"test": "body"}', str(int(time.time())), "v0=invalid_signature"
        )
        assert is_valid is False
        assert error is not None
