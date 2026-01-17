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

import json
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, Depends
import structlog
from time import time as current_time

from api.slack_adapter import SlackRequestValidator
from memory.slack_ingest import handle_slack_events, handle_slack_commands
from core.decorators import must_stay_async

# Optional telemetry - gracefully degrade if module not available
try:
    from telemetry.slack_metrics import (
        record_slack_request,
        record_signature_verification,
        record_slack_processing,
        record_rate_limit_hit,
    )
except ImportError:
    # Stub functions when telemetry not available
    def record_slack_request(*args, **kwargs):
        pass

    def record_signature_verification(*args, **kwargs):
        pass

    def record_slack_processing(*args, **kwargs):
        pass

    def record_rate_limit_hit(*args, **kwargs):
        pass


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


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
) -> Dict[str, Any]:
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
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse JSON payload
    try:
        payload = json.loads(request_body)
    except json.JSONDecodeError as e:
        logger.warning("slack_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON")

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

    # Rate limit check (100 events per minute per team)
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter:
        team_id = payload.get("team_id", "unknown")
        rate_key = f"slack:events:{team_id}"
        try:
            is_allowed = await rate_limiter.check_and_increment(rate_key, limit=100)
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
            from uuid import uuid4
            from datetime import datetime

            await neo4j_client.create_event(
                event_id=f"slack:{payload.get('event_id', uuid4())}",
                event_type="slack_event",
                timestamp=datetime.utcnow().isoformat(),
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
        # Return 200 to prevent Slack redelivery, but log error for investigation
        return {"ok": True, "error_logged": True}


@router.post("/commands")
async def slack_commands(
    request: Request,
    validator: SlackRequestValidator = Depends(get_slack_validator),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
) -> Dict[str, Any]:
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
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse form-encoded payload
    try:
        form_data = await request.form()
        payload = {k: v for k, v in form_data.items()}
    except Exception as e:
        logger.warning("slack_invalid_form_data", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid form data")

    # Rate limit check (50 commands per minute per user)
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter:
        user_id = payload.get("user_id", "unknown")
        rate_key = f"slack:commands:{user_id}"
        try:
            is_allowed = await rate_limiter.check_and_increment(rate_key, limit=50)
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
            result = await handle_slack_commands(
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
