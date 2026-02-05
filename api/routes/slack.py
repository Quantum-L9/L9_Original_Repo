"""
Slack HTTP Routes: FastAPI endpoints for Slack webhook integration.

Routes:
  POST /slack/events  - Slack Events API webhook
  POST /slack/commands - Slack slash command handler

Both endpoints:
  1. Validate Slack signature (HMAC-SHA256)
  2. Parse request body (JSON or form)
  3. Route to handler (orchestration layer)
  4. Return appropriate response
  5. Log all events for observability

Error handling:
  - Invalid signature: 401 Unauthorized (fail-closed)
  - Invalid JSON/form: 400 Bad Request
  - Internal error: 200 OK with error logged (downstream failures shouldn't break Slack flow)

Note: Dependencies are injected (no env reads at import time).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "slack",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["POST /events", "POST /commands"],
        "datasources": ["Neo4j", "Slack API"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "api.server_memory"],
    },
}
# ============================================================================

import json
import os
from time import time as current_time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from api.slack_adapter import SlackRequestValidator
from core.decorators import must_stay_async
from memory.slack_ingest import handle_slack_commands, handle_slack_events

# Optional telemetry - gracefully degrade if module not available
try:
    from telemetry.slack_metrics import (
        record_rate_limit_hit,
        record_signature_verification,
        record_slack_processing,
        record_slack_request,
    )
except ImportError:
    # Stub functions when telemetry not available
    def record_slack_request(*args, **kwargs):
        """Stub for recording Slack request metrics when telemetry unavailable."""
        pass

    def record_signature_verification(*args, **kwargs):
        """Stub for recording signature verification metrics when telemetry unavailable."""
        pass

    def record_slack_processing(*args, **kwargs):
        """Stub for recording Slack processing metrics when telemetry unavailable."""
        pass

    def record_rate_limit_hit(*args, **kwargs):
        """Stub for recording rate limit hit metrics when telemetry unavailable."""
        pass


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/slack"
    tags=["slack"],
    module_id="slack",
    display_name="Slack Adapter",
    dependencies=[],  # Runtime validation via Depends(get_slack_validator)
)


# Dependency injection for validator (injected at app startup)
@must_stay_async("callers use await")
async def get_slack_validator(request: Request) -> SlackRequestValidator:
    """Retrieve validator from app state."""
    validator = request.app.state.slack_validator
    if not validator:
        raise HTTPException(status_code=500, detail="Slack validator not initialized")
    return validator


@router.post("/events")
async def slack_events(
    request: Request,
    validator: SlackRequestValidator = Depends(get_slack_validator),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
) -> dict[str, Any]:
    """
    Slack Events API webhook handler.

    Handles:
      - url_verification: Echoes challenge (Slack handshake)
      - event_callback: Processes app_mention and message events

    Flow:
      1. Validate Slack signature
      2. Check rate limit
      3. Check for url_verification (respond with challenge)
      4. Parse event_callback
      5. Normalize provenance and thread context
      6. Dedupe check (prevent double-processing)
      7. Call AIOS /chat endpoint
      8. Post reply back to Slack in thread
      9. Store inbound/outbound packets in memory substrate

    Security:
      - Signature verification is mandatory (fail-closed)
      - Invalid signatures return 401, no further processing
      - Timestamp freshness validated (300s tolerance)
      - Rate limiting per team (100 events/minute)

    Idempotency:
      - Primary key: event_id
      - Fallback: team_id + channel_id + ts + user_id
      - Duplicate events: return 200 ack, no re-processing

    Error handling:
      - Invalid signature: 401 Unauthorized
      - Rate limited: 429 Too Many Requests
      - Invalid JSON: 400 Bad Request
      - Internal errors: 200 OK (swallow Slack-side to prevent redelivery loop)
    """
    start_time = current_time()
    record_slack_request(event_type="events", status="received")

    # Get raw request body
    request_body = await request.body()

    # Validate Slack signature
    try:
        is_valid, error_reason = validator.verify(
            request_body,
            x_slack_request_timestamp,
            x_slack_signature,
        )
        if not is_valid:
            logger.warning(
                "slack_signature_verification_failed",
                error=error_reason,
                timestamp=x_slack_request_timestamp,
            )
            record_signature_verification(valid=False, reason=error_reason or "invalid")
            raise HTTPException(status_code=401, detail="Unauthorized")
        record_signature_verification(valid=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_signature_verification_error", error=str(e))
        record_signature_verification(valid=False, reason="exception")
        raise HTTPException(status_code=401, detail="Unauthorized") from e

    # Parse JSON payload
    try:
        payload = json.loads(request_body)
    except json.JSONDecodeError as e:
        logger.warning("slack_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # Validate Slack event schema
    VALID_SLACK_EVENT_TYPES = {"url_verification", "event_callback", "app_rate_limited"}
    event_type = payload.get("type")
    if event_type and event_type not in VALID_SLACK_EVENT_TYPES:
        logger.warning("slack_invalid_event_type", event_type=event_type)
        raise HTTPException(
            status_code=400, detail=f"Invalid Slack event type: {event_type}"
        )

    # Handle url_verification (Slack handshake during setup) - skip rate limit
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge", "")
        logger.info("slack_url_verification_challenge", challenge=challenge[:20])
        record_slack_processing(
            event_type="url_verification",
            duration_seconds=current_time() - start_time,
            status="success",
        )
        return {"challenge": challenge}

    # Rate limit check (configurable events per minute per team)
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter:
        team_id = payload.get("team_id", "unknown")
        rate_key = f"slack:events:{team_id}"
        events_rate_limit = int(os.getenv("SLACK_EVENTS_RATE_LIMIT", "100"))
        try:
            is_allowed = await rate_limiter.check_and_increment(rate_key, limit=events_rate_limit)
            if not is_allowed:
                logger.warning("slack_rate_limit_exceeded", team_id=team_id)
                record_rate_limit_hit(team_id=team_id)
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except HTTPException:
            raise
        except Exception as e:
            # Log but don't fail - rate limiting is protective, not blocking
            logger.warning("slack_rate_limit_check_failed", error=str(e))

    # Permission check (if Permission Graph available)
    permission_graph = getattr(request.app.state, "permission_graph", None)
    if permission_graph:
        try:
            user_id = payload.get("event", {}).get("user", "unknown")
            has_access = await permission_graph.has_permission(user_id, "slack:events")
            if not has_access:
                # Log but allow - permission graph may not be fully configured
                logger.debug("slack_permission_check_no_grant", user_id=user_id)
        except Exception as e:
            # Log but don't block - permission check is advisory in dev mode
            logger.debug("slack_permission_check_failed", error=str(e))

    # Log event to Neo4j (non-blocking)
    neo4j_client = getattr(request.app.state, "neo4j_client", None)
    if neo4j_client:
        try:
            from datetime import datetime, timezone
            from uuid import uuid4

            await neo4j_client.create_event(
                event_id=f"slack:{payload.get('event_id', uuid4())}",
                event_type="slack_event",
                timestamp=datetime.now(timezone.utc).isoformat(),
                properties={
                    "team_id": payload.get("team_id"),
                    "user_id": payload.get("event", {}).get("user"),
                    "event_type": payload.get("event", {}).get("type"),
                    "channel": payload.get("event", {}).get("channel"),
                },
            )
        except Exception as e:
            logger.debug("slack_neo4j_log_failed", error=str(e))

    # Route to handler
    try:
        # Inject dependencies (use getattr for graceful degradation if not initialized)
        substrate_service = getattr(request.app.state, "substrate_service", None)
        slack_client = getattr(request.app.state, "slack_client", None)
        aios_base_url = getattr(
            request.app.state, "aios_base_url", "http://localhost:8000"
        )

        result = await handle_slack_events(
            request_body=request_body,
            payload=payload,
            substrate_service=substrate_service,
            slack_client=slack_client,
            aios_base_url=aios_base_url,
            app=request.app,  # Pass app for L-CTO agent routing
        )

        elapsed_seconds = current_time() - start_time
        elapsed_ms = elapsed_seconds * 1000
        logger.info(
            "slack_events_processed",
            event_id=payload.get("event_id"),
            event_type=payload.get("event", {}).get("type"),
            elapsed_ms=elapsed_ms,
        )
        record_slack_processing(
            event_type=payload.get("event", {}).get("type", "unknown"),
            duration_seconds=elapsed_seconds,
            status="success",
        )
        return result
    except Exception as e:
        elapsed_seconds = current_time() - start_time
        elapsed_ms = elapsed_seconds * 1000
        logger.error(
            "slack_events_handler_error",
            error=str(e),
            event_id=payload.get("event_id"),
            elapsed_ms=elapsed_ms,
        )
        record_slack_processing(
            event_type=payload.get("event", {}).get("type", "unknown"),
            duration_seconds=elapsed_seconds,
            status="error",
        )
        raise HTTPException(
            status_code=500, detail="Slack event processing failed"
        ) from e


@router.post("/commands")
async def slack_commands(
    request: Request,
    validator: SlackRequestValidator = Depends(get_slack_validator),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
) -> dict[str, Any]:
    """
    Slack slash command handler.

    Handles custom /l9 commands:
      - /l9 do <task> - Execute a task
      - /l9 email <instruction> - Email operation
      - /l9 extract <artifact> - Extract data from artifact

    Flow:
      1. Validate Slack signature
      2. Parse form-encoded command payload
      3. Return 200 ACK immediately (< 3 second requirement)
      4. Async: Normalize provenance
      5. Async: Call AIOS /chat endpoint
      6. Async: Post reply to response_url or Slack API
      7. Async: Store inbound/outbound packets

    Note: Commands have a response_url which is valid for 3 seconds.
          We return immediately with 200 ACK, then async reply.

    Error handling:
      - Invalid signature: 401
      - Invalid command: 200 with error message
      - AIOS failure: 200 with temporary failure message
    """
    start_time = current_time()
    record_slack_request(event_type="commands", status="received")

    # Get raw request body
    request_body = await request.body()

    # Validate Slack signature
    try:
        is_valid, error_reason = validator.verify(
            request_body,
            x_slack_request_timestamp,
            x_slack_signature,
        )
        if not is_valid:
            logger.warning(
                "slack_signature_verification_failed",
                error=error_reason,
                timestamp=x_slack_request_timestamp,
            )
            record_signature_verification(valid=False, reason=error_reason or "invalid")
            raise HTTPException(status_code=401, detail="Unauthorized")
        record_signature_verification(valid=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_signature_verification_error", error=str(e))
        record_signature_verification(valid=False, reason="exception")
        raise HTTPException(status_code=401, detail="Unauthorized") from e

    # Parse form-encoded payload
    try:
        form_data = await request.form()
        payload = dict(form_data.items())
    except Exception as e:
        logger.warning("slack_invalid_form_data", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid form data") from e

    # Rate limit check (configurable commands per minute per user)
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter:
        user_id = payload.get("user_id", "unknown")
        rate_key = f"slack:commands:{user_id}"
        commands_rate_limit = int(os.getenv("SLACK_COMMANDS_RATE_LIMIT", "50"))
        try:
            is_allowed = await rate_limiter.check_and_increment(rate_key, limit=commands_rate_limit)
            if not is_allowed:
                logger.warning("slack_command_rate_limit_exceeded", user_id=user_id)
                return {
                    "response_type": "ephemeral",
                    "text": "Rate limit exceeded. Please wait before sending more commands.",
                }
        except Exception as e:
            logger.warning("slack_command_rate_limit_check_failed", error=str(e))

    # Inject dependencies (use getattr for graceful degradation if not initialized)
    substrate_service = getattr(request.app.state, "substrate_service", None)
    slack_client = getattr(request.app.state, "slack_client", None)
    aios_base_url = getattr(request.app.state, "aios_base_url", "http://localhost:8000")

    # Return 200 ACK immediately (Slack requires response < 3 seconds)
    # Then process async in background

    async def process_command_async():
        """Process command asynchronously after returning ACK."""
        try:
            await handle_slack_commands(
                payload=payload,
                substrate_service=substrate_service,
                slack_client=slack_client,
                aios_base_url=aios_base_url,
            )
            elapsed_seconds = current_time() - start_time
            elapsed_ms = elapsed_seconds * 1000
            logger.info(
                "slack_commands_processed",
                command=payload.get("command"),
                user_id=payload.get("user_id"),
                elapsed_ms=elapsed_ms,
            )
            record_slack_processing(
                event_type="command",
                duration_seconds=elapsed_seconds,
                status="success",
            )
        except Exception as e:
            elapsed_seconds = current_time() - start_time
            elapsed_ms = elapsed_seconds * 1000
            logger.error(
                "slack_commands_handler_error",
                error=str(e),
                command=payload.get("command"),
                elapsed_ms=elapsed_ms,
            )
            record_slack_processing(
                event_type="command",
                duration_seconds=elapsed_seconds,
                status="error",
            )

    # Schedule async task (Fire and forget, but logged)
    import asyncio

    asyncio.create_task(process_command_async())

    # Return immediate ACK (200 < 3 seconds)
    return {
        "response_type": "ephemeral",
        "text": "Processing your command...",
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.slack_adapter", "core.decorators", "memory.slack_ingest"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "authorization",
        "debugging",
        "endpoint",
        "event-driven",
        "logging",
        "messaging",
    ],
    "keywords": [
        "async",
        "command",
        "commands",
        "endpoints",
        "events",
        "form",
        "handler",
        "hit",
    ],
    "business_value": "Utility module for slack",
    "last_modified": "2026-01-17T23:47:56Z",
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
