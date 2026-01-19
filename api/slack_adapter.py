"""
Slack Request Adapter: Signature Verification & Inbound Normalization

This module provides core Slack webhook validation and request normalization.
All inbound Slack events are validated via HMAC-SHA256 before processing.
Implements fail-closed security posture: invalid signatures = 401, no processing.

Slack Signature Verification:
  - Algorithm: HMAC-SHA256
  - Timestamp header: X-Slack-Request-Timestamp
  - Signature header: X-Slack-Signature
  - Tolerance: 300 seconds (5 minutes) against replay attacks
  - Format: v0=<hash>
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "error_handling",
    "module_name": "slack_adapter",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.e2e_slack_audit",
            "api.routes.slack",
            "api.server",
            "api.server_memory",
            "memory.slack_ingest",
            "tests.api.test_e2e_slack_audit",
            "tests.api.test_slack_adapter",
            "tests.integration.test_slack_dispatch_integration",
            "tests.test_slack_adapter",
        ],
    },
}
# ============================================================================

import hashlib
import hmac
import time
from typing import Any, Dict, Optional, Tuple
from uuid import uuid5, NAMESPACE_DNS
import structlog

logger = structlog.get_logger(__name__)

# Slack thread namespace for deterministic UUIDs
SLACK_THREAD_NAMESPACE = uuid5(NAMESPACE_DNS, "slack.l9.internal")


class SlackSignatureVerificationError(Exception):
    """Raised when Slack signature verification fails."""

    def __init__(self, reason: str, http_status: int = 401):
        self.reason = reason
        self.http_status = http_status
        super().__init__(reason)


class SlackRequestValidator:
    """
    Validates Slack webhook requests using HMAC-SHA256.

    Slack sends three headers:
      - X-Slack-Request-Timestamp: Unix timestamp
      - X-Slack-Signature: v0=<HMAC-SHA256 hex>
      - (body): raw request body (bytes)

    Verification process:
      1. Extract timestamp and signature from headers
      2. Validate timestamp is within tolerance (no replay)
      3. Construct signed content: "v0:<timestamp>:<body>"
      4. Compute HMAC-SHA256 with signing secret
      5. Compare signatures using constant-time comparison
    """

    TOLERANCE_SECONDS: int = 300
    SIGNATURE_VERSION: str = "v0"

    def __init__(self, signing_secret: str):
        """
        Args:
            signing_secret: Slack app signing secret (from Settings > Basic Information)
                           Must NOT be empty
        """
        if not signing_secret or not signing_secret.strip():
            raise ValueError("SLACK_SIGNING_SECRET is required and cannot be empty")
        self.signing_secret = signing_secret.encode()

    def verify(
        self,
        request_body: bytes,
        timestamp_str: Optional[str],
        signature: Optional[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify Slack request signature.

        Args:
            request_body: Raw request body (bytes)
            timestamp_str: X-Slack-Request-Timestamp header value (may be None)
            signature: X-Slack-Signature header value (format: v0=<hash>, may be None)

        Returns:
            Tuple[is_valid, error_reason]
            - (True, None) if signature is valid
            - (False, reason) if signature is invalid or missing

        Note: Tolerates missing headers cleanly (returns False with reason).
        """
        # Handle missing headers gracefully
        if not timestamp_str:
            return False, "Missing X-Slack-Request-Timestamp header"

        if not signature:
            return False, "Missing X-Slack-Signature header"

        try:
            timestamp = int(timestamp_str)
        except (ValueError, TypeError):
            return False, "Invalid timestamp format"

        # Check timestamp freshness (replay attack prevention)
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.TOLERANCE_SECONDS:
            return (
                False,
                f"Request timestamp is stale (tolerance: {self.TOLERANCE_SECONDS}s)",
            )

        # Construct signed content: v0:<timestamp>:<body>
        # Use raw body text exactly (no JSON re-serialization)
        body_text = request_body.decode("utf-8")
        signed_content = f"{self.SIGNATURE_VERSION}:{timestamp_str}:{body_text}"

        # Compute expected signature
        expected_signature = hmac.new(
            self.signing_secret, signed_content.encode(), hashlib.sha256
        ).hexdigest()

        # Extract signature value (strip v0= prefix)
        if not signature.startswith("v0="):
            return False, "Signature format invalid (must start with v0=)"

        provided_hash = signature[3:]  # Strip "v0="

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(provided_hash, expected_signature)

        return (is_valid, None) if is_valid else (False, "Signature mismatch")


class SlackRequestNormalizer:
    """
    Normalize Slack webhook payloads into internal typed models.

    Slack sends different event types:
      - url_verification: Challenge handshake (return challenge immediately)
      - event_callback: Actual event (process and reply in thread)
      - command: Slash command invocation

    This normalizer extracts common fields and provides a typed interface.

    Thread ID Generation:
      - Generates deterministic UUID v5 from team_id:channel_id:thread_ts
      - Stores human-readable string in metadata for observability
    """

    @staticmethod
    def _generate_thread_uuid(team_id: str, channel_id: str, thread_ts: str) -> str:
        """Generate deterministic UUID v5 for a Slack thread."""
        thread_id = uuid5(SLACK_THREAD_NAMESPACE, f"{team_id}:{channel_id}:{thread_ts}")
        return str(thread_id)

    @staticmethod
    def parse_event_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse event_callback payload from Slack.

        Expected structure:
          {
            "token": "...",
            "team_id": "T...",
            "enterprise_id": "E...",
            "api_app_id": "A...",
            "event": {
              "type": "message" | "app_mention",
              "user": "U...",
              "text": "...",
              "ts": "1234567890.123456",  # message timestamp
              "thread_ts": "1234567890.123456",  # optional; if present, this is a thread
              "channel": "C...",
              "event_ts": "1234567890.123456"
            },
            "type": "event_callback",
            "event_id": "Ev...",  # unique event ID
            "event_time": 1234567890
          }

        Returns:
            Normalized dict with required provenance keys:
              - team_id
              - enterprise_id
              - channel_id
              - channel_type (derived from channel prefix: C=public, G=private, else unknown)
              - user_id
              - ts (message timestamp)
              - thread_ts (derived from event.thread_ts or event.ts)
              - thread_uuid (deterministic UUID v5)
              - thread_string (human-readable slack:T:C:ts format)
              - event_id
              - event_type
              - text
              - raw_event (full event object for audit trail)
        """
        event = payload.get("event", {})

        # Derive thread_ts: use event.thread_ts if present, otherwise event.ts
        thread_ts = event.get("thread_ts") or event.get("ts", "")

        # Derive channel_type from channel prefix
        channel_id = event.get("channel", "")
        if channel_id.startswith("C"):
            channel_type = "public"
        elif channel_id.startswith("G"):
            channel_type = "private"
        else:
            channel_type = "unknown"

        # Generate deterministic thread UUID
        team_id = payload.get("team_id", "")
        thread_uuid = SlackRequestNormalizer._generate_thread_uuid(
            team_id, channel_id, thread_ts
        )
        thread_string = f"slack:{team_id}:{channel_id}:{thread_ts}"

        normalized = {
            "team_id": team_id,
            "enterprise_id": payload.get("enterprise_id") or "",
            "channel_id": channel_id,
            "channel_type": channel_type,
            "user_id": event.get("user", ""),
            "ts": event.get("ts", ""),
            "thread_ts": thread_ts,
            "thread_uuid": thread_uuid,
            "thread_string": thread_string,
            "event_id": payload.get("event_id", ""),
            "event_type": event.get("type", ""),
            "text": event.get("text", ""),
            "raw_event": event,
        }

        return normalized

    @staticmethod
    def parse_command(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse slash command payload from Slack.

        Expected structure:
          {
            "token": "...",
            "team_id": "T...",
            "enterprise_id": "E...",
            "channel_id": "C...",
            "user_id": "U...",
            "command": "/l9",
            "text": "do make me a report",
            "api_app_id": "A...",
            "response_url": "https://hooks.slack.com/commands/...",
            "trigger_id": "..."
          }

        Returns:
            Normalized dict with required fields:
              - team_id
              - enterprise_id
              - channel_id
              - channel_type
              - user_id
              - command
              - text (the full command text)
              - response_url (where to post reply)
              - trigger_id (for interactive modals)
              - thread_uuid (for command dedup)
        """
        channel_id = payload.get("channel_id", "")
        if channel_id.startswith("C"):
            channel_type = "public"
        elif channel_id.startswith("G"):
            channel_type = "private"
        else:
            channel_type = "unknown"

        team_id = payload.get("team_id", "")
        user_id = payload.get("user_id", "")

        # Command dedup: use command thread UUID
        cmd_thread_ts = str(int(time.time() * 1000000))  # Microsecond precision
        thread_uuid = SlackRequestNormalizer._generate_thread_uuid(
            team_id, channel_id, cmd_thread_ts
        )

        normalized = {
            "team_id": team_id,
            "enterprise_id": payload.get("enterprise_id") or "",
            "channel_id": channel_id,
            "channel_type": channel_type,
            "user_id": user_id,
            "command": payload.get("command", ""),
            "text": payload.get("text", ""),
            "response_url": payload.get("response_url", ""),
            "trigger_id": payload.get("trigger_id", ""),
            "thread_uuid": thread_uuid,
        }

        return normalized


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "error-handling",
        "event-driven",
        "exception",
        "logging",
        "messaging",
        "operations",
        "security",
        "validation",
        "webhooks",
    ],
    "keywords": [
        "adapter",
        "callback",
        "command",
        "event",
        "header",
        "hmac",
        "inbound",
        "module",
    ],
    "business_value": "This module provides core Slack webhook validation and request normalization. All inbound Slack events are validated via HMAC-SHA256 before processing.",
    "last_modified": "2026-01-07T13:35:57Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
