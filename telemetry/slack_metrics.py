"""
L9 Telemetry - Slack Adapter Metrics
====================================

Prometheus metrics for L9 Slack adapter observability.
Tracks webhook requests, signature verification, processing latency,
AIOS calls, and error rates.

These metrics integrate with the L9 /metrics endpoint via
the prometheus_client library.

Version: 1.0.0
Author: L9 Enterprise
Created: 2026-01-08

Canonical Log Events (9 required per Module-Spec-v2.5):
  1. request_received - Webhook request received
  2. signature_verified - HMAC signature validated
  3. thread_uuid_generated - Deterministic UUID created
  4. dedupe_check - Idempotency check performed
  5. aios_call_start - AIOS/Agent call initiated
  6. aios_call_complete - AIOS/Agent call finished
  7. packet_stored - PacketEnvelope persisted
  8. reply_sent - Slack reply posted
  9. handler_error - Error during processing

Usage:
    from telemetry.slack_metrics import (
        record_slack_request,
        record_signature_verification,
        record_slack_processing,
        record_aios_call,
        record_slack_reply,
    )

    # After request received:
    record_slack_request(event_type="message", team_id="T123")

    # After signature verification:
    record_signature_verification(valid=True)

    # After processing complete:
    record_slack_processing(status="success", duration_ms=150)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Adapter Metrics",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T01:42:58Z",
    "updated_at": "2026-01-08T20:50:40Z",
    "layer": "operations",
    "domain": "observability",
    "module_name": "slack_metrics",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.e2e_slack_audit",
            "api.routes.slack",
            "memory.slack_ingest",
            "telemetry.slack_metrics",
            "tests.api.test_e2e_slack_audit",
            "tests.api.test_slack_adapter",
        ],
    },
}
# ============================================================================

import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

# Try to import prometheus_client, gracefully degrade if not available
try:
    from prometheus_client import Counter, Histogram, Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed - slack metrics disabled")

# =============================================================================
# Metric Definitions
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Request metrics
    SLACK_REQUESTS_TOTAL = Counter(
        "l9_slack_requests_total",
        "Total Slack webhook requests",
        ["event_type", "status"],
    )

    SLACK_SIGNATURE_FAILURES = Counter(
        "l9_slack_signature_failures_total",
        "Failed signature verifications",
        ["reason"],
    )

    SLACK_IDEMPOTENT_HITS = Counter(
        "l9_slack_idempotent_hits_total",
        "Duplicate events deduplicated",
        ["team_id"],
    )

    # Processing metrics
    SLACK_PROCESSING_DURATION = Histogram(
        "l9_slack_processing_duration_seconds",
        "Time to process Slack event end-to-end",
        ["event_type"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    )

    SLACK_AIOS_CALL_DURATION = Histogram(
        "l9_slack_aios_call_duration_seconds",
        "Time for AIOS/Agent chat call",
        ["agent_type"],
        buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    )

    # Error metrics
    SLACK_PACKET_WRITE_ERRORS = Counter(
        "l9_slack_packet_write_errors_total",
        "Failed packet writes to substrate",
        ["packet_type"],
    )

    SLACK_REPLY_ERRORS = Counter(
        "l9_slack_reply_errors_total",
        "Failed Slack API replies",
        ["error_type"],
    )

    # Active state
    SLACK_ACTIVE_THREADS = Gauge(
        "l9_slack_active_threads",
        "Number of active Slack threads (approximation)",
    )

    # Rate limiting
    SLACK_RATE_LIMIT_HITS = Counter(
        "l9_slack_rate_limit_hits_total",
        "Requests rejected due to rate limiting",
        ["team_id"],
    )

# =============================================================================
# Recording Functions
# =============================================================================


def record_slack_request(
    event_type: str,
    status: str = "received",
) -> None:
    """
    Record a Slack webhook request.

    Args:
        event_type: Slack event type (message, app_mention, url_verification)
        status: Request status (received, processed, error)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_REQUESTS_TOTAL.labels(event_type=event_type, status=status).inc()
    except Exception as e:
        logger.warning("Failed to record slack request metric", error=str(e))


def record_signature_verification(
    valid: bool,
    reason: Optional[str] = None,
) -> None:
    """
    Record signature verification result.

    Args:
        valid: Whether signature was valid
        reason: Failure reason if invalid
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        if not valid and reason:
            SLACK_SIGNATURE_FAILURES.labels(reason=reason).inc()
    except Exception as e:
        logger.warning("Failed to record signature verification metric", error=str(e))


def record_idempotent_hit(team_id: str) -> None:
    """
    Record a deduplicated event.

    Args:
        team_id: Slack team ID
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_IDEMPOTENT_HITS.labels(team_id=team_id).inc()
    except Exception as e:
        logger.warning("Failed to record idempotent hit metric", error=str(e))


def record_slack_processing(
    event_type: str,
    duration_seconds: float,
    status: str = "success",
) -> None:
    """
    Record Slack event processing.

    Args:
        event_type: Slack event type
        duration_seconds: Processing duration in seconds
        status: Final status (success, error)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_PROCESSING_DURATION.labels(event_type=event_type).observe(
            duration_seconds
        )
        SLACK_REQUESTS_TOTAL.labels(event_type=event_type, status=status).inc()
    except Exception as e:
        logger.warning("Failed to record slack processing metric", error=str(e))


def record_aios_call(
    agent_type: str,
    duration_seconds: float,
) -> None:
    """
    Record AIOS/Agent call duration.

    Args:
        agent_type: Agent type (l-cto, aios, legacy)
        duration_seconds: Call duration in seconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_AIOS_CALL_DURATION.labels(agent_type=agent_type).observe(duration_seconds)
    except Exception as e:
        logger.warning("Failed to record aios call metric", error=str(e))


def record_packet_write_error(packet_type: str) -> None:
    """
    Record a failed packet write.

    Args:
        packet_type: Packet type (slack.in, slack.out, slack.error)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_PACKET_WRITE_ERRORS.labels(packet_type=packet_type).inc()
    except Exception as e:
        logger.warning("Failed to record packet write error metric", error=str(e))


def record_slack_reply_error(error_type: str) -> None:
    """
    Record a failed Slack reply.

    Args:
        error_type: Error type (timeout, api_error, rate_limited)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_REPLY_ERRORS.labels(error_type=error_type).inc()
    except Exception as e:
        logger.warning("Failed to record slack reply error metric", error=str(e))


def record_rate_limit_hit(team_id: str) -> None:
    """
    Record a rate limit rejection.

    Args:
        team_id: Slack team ID
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_RATE_LIMIT_HITS.labels(team_id=team_id).inc()
    except Exception as e:
        logger.warning("Failed to record rate limit hit metric", error=str(e))


def set_active_threads(count: int) -> None:
    """
    Set the active threads gauge.

    Args:
        count: Number of active threads
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        SLACK_ACTIVE_THREADS.set(count)
    except Exception as e:
        logger.warning("Failed to set active threads gauge", error=str(e))


# =============================================================================
# Initialization
# =============================================================================


def init_slack_metrics() -> bool:
    """
    Initialize Slack metrics.

    Returns:
        True if metrics are available, False otherwise
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus metrics not available - install prometheus_client")
        return False

    # Set initial active threads to 0
    set_active_threads(0)

    logger.info("Slack metrics initialized")
    return True


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "PROMETHEUS_AVAILABLE",
    "record_slack_request",
    "record_signature_verification",
    "record_idempotent_hit",
    "record_slack_processing",
    "record_aios_call",
    "record_packet_write_error",
    "record_slack_reply_error",
    "record_rate_limit_hit",
    "set_active_threads",
    "init_slack_metrics",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEL-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "api",
        "event-driven",
        "logging",
        "messaging",
        "metrics",
        "observability",
        "operations",
        "webhooks",
    ],
    "keywords": [
        "active",
        "adapter",
        "after",
        "agent",
        "aios",
        "created",
        "hit",
        "idempotent",
    ],
    "business_value": "the prometheus_client library. Version: 1.0.0 Author: L9 Enterprise Created: 2026-01-08 1. request_received - Webhook request received 2. signature_verified - HMAC signature validated 3. thread_uuid_g",
    "last_modified": "2026-01-08T20:50:40Z",
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
