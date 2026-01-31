"""
Slack Event Ingestion: Core handler for Slack messages.

This module implements the orchestration layer:
  1. Dedupe check (prevent double-processing)
  2. Memory context retrieval (fetch thread history + semantic hits)
  3. L-CTO agent routing via AgentExecutorService (when legacy flag is False)
  4. AIOS /chat call fallback (when legacy flag is True)
  5. Slack API response delivery (post message in thread)
  6. Packet persistence (store inbound + outbound in substrate)

Features ported from legacy webhook_slack.py (v2.0):
  - L-CTO agent routing via AgentExecutorService
  - DM (direct message) detection and handling
  - File attachment processing (OCR, PDF, transcription)
  - !mac command routing to Mac agent
  - Email command detection and routing
  - Task routing via slack_task_router

Thread model:
  - All Slack messages belong to a thread (identified by deterministic UUID)
  - Thread UUID is generated from team_id:channel_id:thread_ts using UUIDv5
  - Human-readable string stored in metadata for observability
  - Internal operations use UUID for DB consistency

Deduplication:
  - Check event_id in packet metadata before processing
  - If found, return 200 without re-processing
  - Prevents double-replies if Slack retries delivery

Error handling:
  - Agent/AIOS call fails: Log error, store error packet, don't crash
  - Slack API call fails: Log error, store error packet, return 200 to Slack
  - Memory persistence fails: Log error, still return 200 to Slack
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Ingest",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "slack_ingest",
    "type": "engine",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "OpenAI API", "Slack API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "api.e2e_slack_audit",
            "api.routes.slack",
            "tests.api.test_e2e_slack_audit",
            "tests.api.test_slack_adapter",
        ],
    },
}
# ============================================================================

from time import time as current_time
from typing import Any

import httpx
import structlog

from api.slack_adapter import SlackRequestNormalizer
from api.slack_client import SlackAPIClient, SlackClientError
from config.settings import settings
from core.schemas import PacketEnvelopeIn, PacketMetadata, PacketProvenance
from memory.substrate_service import MemorySubstrateService

# Governance context for memory operations (required on C1 with RLS enabled)
import os
try:
    from config.rls_config import get_rls_config
    from memory.governance_gate import build_governance_context, governance_context
    _has_governance = True
except ImportError:
    _has_governance = False

# Input segmenter for multi-part directive support (harvested from tokenizer)
from orchestration.input_segmenter import get_segmenter

# Optional telemetry - gracefully degrade if module not available
try:
    from telemetry.slack_metrics import (
        record_aios_call,
        record_idempotent_hit,
        record_packet_write_error,
        record_slack_reply_error,
    )
except ImportError:
    # Stub functions when telemetry not available
    def record_aios_call(*args, **kwargs):
        """Stub for recording AIOS call metrics when telemetry unavailable."""
        pass

    def record_idempotent_hit(*args, **kwargs):
        """Stub for recording idempotent hit metrics when telemetry unavailable."""
        pass

    def record_packet_write_error(*args, **kwargs):
        """Stub for recording packet write error metrics when telemetry unavailable."""
        pass

    def record_slack_reply_error(*args, **kwargs):
        """Stub for recording Slack reply error metrics when telemetry unavailable."""
        pass


logger = structlog.get_logger(__name__)

# =============================================================================
# CANONICAL LOG EVENT NAMES (9 required per Module-Spec-v2.5)
# =============================================================================
# 1. slack_request_received - Webhook request received (logged in routes)
# 2. slack_signature_verified - HMAC signature validated (logged in routes)
# 3. slack_thread_uuid_generated - Deterministic UUID created
# 4. slack_dedupe_check - Idempotency check performed
# 5. slack_aios_call_start - AIOS/Agent call initiated
# 6. slack_aios_call_complete - AIOS/Agent call finished
# 7. slack_packet_stored - PacketEnvelope persisted
# 8. slack_reply_sent - Slack reply posted
# 9. slack_handler_error - Error during processing
# =============================================================================

# Feature flag for legacy Slack routing
# When False, route Slack messages through AgentTask + AgentExecutorService
# When True, use legacy AIOS /chat endpoint
L9_ENABLE_LEGACY_SLACK_ROUTER = getattr(
    settings, "l9_enable_legacy_slack_router", False
)

# =============================================================================
# L-CTO Agent Handler (ported from webhook_slack.py)
# =============================================================================


async def handle_slack_with_l_agent(
    app,
    text: str,
    thread_uuid: str,
    team_id: str,
    channel_id: str,
    user_id: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Route a Slack message through the L-CTO agent via AgentExecutorService.

    This helper constructs an AgentTask and executes it via the kernel-aware
    agent stack. It does NOT call OpenAI directly.

    Args:
        app: FastAPI app instance (for accessing app.state.agent_executor)
        text: Message text from Slack
        thread_uuid: Slack thread UUID for conversation grouping
        team_id: Slack workspace/team ID
        channel_id: Slack channel ID
        user_id: Slack user ID
        context: Optional dict containing thread_context and semantic_hits
                 from DAG-stored packets for conversation continuity

    Returns:
        Tuple of (reply_text, status) where:
        - reply_text: The agent's response formatted for Slack
        - status: One of "completed", "duplicate", "failed", "error"
    """
    try:
        # Import here to avoid circular imports
        from core.agents.schemas import (
            AgentTask,
            AgentType,
            DuplicateTaskResponse,
            ExecutionResult,
        )

        # Check if agent executor is available
        agent_executor = getattr(app.state, "agent_executor", None)
        if agent_executor is None:
            logger.error("handle_slack_with_l_agent: agent_executor not available")
            return ("L9 agent executor not available. Please try again later.", "error")

        # Construct AgentTask for L-CTO with DAG-retrieved context
        task = AgentTask(
            agent_id="l-cto",
            agent_type=AgentType.ASSISTANT,
            source_id="slack",
            thread_identifier=thread_uuid,
            payload={
                "message": text,
                "channel": "slack",
                "slack": {
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                },
            },
            context=context or {},
        )

        logger.info(
            "handle_slack_with_l_agent: task_id=%s, thread=%s, user=%s",
            str(task.id),
            thread_uuid,
            user_id,
        )

        # Execute task via AgentExecutorService
        # Wrap with governance context for RLS-enabled memory operations
        if _has_governance:
            rls_config = get_rls_config()
            gov_ctx = build_governance_context(
                caller_id="slack_ingest",
                role="service",
                scope="agent",
                project_id=os.getenv("L9_PROJECT_ID", "l9"),
                allowed_scopes=["agent", "memory", "slack"],
                tenant_id=rls_config.tenant_uuid,
                org_id=rls_config.org_uuid,
                user_id=rls_config.user_uuid,
                creator="slack",
                source="slack_ingest",
            )
            async with governance_context(gov_ctx):
                result = await agent_executor.start_agent_task(task)
        else:
            result = await agent_executor.start_agent_task(task)

        # Handle duplicate detection
        if isinstance(result, DuplicateTaskResponse):
            logger.info(
                "handle_slack_with_l_agent: duplicate task: %s", str(result.task_id)
            )
            return ("This message has already been processed.", "duplicate")

        # Handle ExecutionResult
        if isinstance(result, ExecutionResult):
            reply = result.result or result.error or "No response from agent."
            return (reply, result.status)

        # Fallback (should not happen)
        logger.warning(
            "handle_slack_with_l_agent: unexpected result type: %s", type(result)
        )
        return ("Unexpected result format.", "error")

    except Exception as e:
        logger.exception("handle_slack_with_l_agent: error: %s", str(e))
        return (f"Error processing message: {e!s}", "error")


# =============================================================================
# File Attachment Processing (ported from webhook_slack.py)
# =============================================================================


async def _process_file_attachments(files: list) -> list:
    """
    Process Slack file attachments (download, OCR, PDF parsing) - async.

    Returns list of file artifact dicts with name, type, path, content.
    """
    if not files:
        return []

    try:
        from services.slack_files import process_file_attachments

        return await process_file_attachments(files)
    except ImportError:
        logger.debug("slack_files service not available")
        return []
    except Exception as e:
        logger.error("_process_file_attachments error", error=str(e))
        return []


# =============================================================================
# !mac Command Handler (ported from webhook_slack.py)
# =============================================================================


async def _handle_mac_command(
    text: str,
    channel_id: str,
    user_id: str,
    file_artifacts: list,
    slack_client: SlackAPIClient,
    thread_ts: str | None = None,
) -> dict[str, Any] | None:
    """
    Handle !mac commands - route to Mac agent task queue.

    Returns response dict if handled, None if not a !mac command.
    """
    if not text.strip().lower().startswith("!mac"):
        return None

    command = text.replace("!mac", "", 1).replace("!MAC", "", 1).strip()
    if not command:
        await slack_client.post_message(
            channel=channel_id,
            text="❌ Please provide a command after `!mac` (e.g., `!mac echo hello`)",
            thread_ts=thread_ts,
        )
        return {"ok": True, "handled": "mac_empty"}

    try:
        from orchestrators.agent_execution.task_queue import enqueue_mac_task

        # Enhance command context with file artifacts if present
        enhanced_command = command
        if file_artifacts:
            file_context = "\n\n[File attachments available:"
            for artifact in file_artifacts:
                file_context += (
                    f"\n- {artifact['name']} ({artifact['type']}) at {artifact['path']}"
                )
            file_context += "]"
            enhanced_command = command + file_context

        task_id = enqueue_mac_task(
            source="slack",
            channel=channel_id,
            user=user_id,
            command=enhanced_command,
            attachments=file_artifacts if file_artifacts else None,
        )

        file_msg = (
            f" ({len(file_artifacts)} file{'s' if len(file_artifacts) != 1 else ''})"
            if file_artifacts
            else ""
        )
        await slack_client.post_message(
            channel=channel_id,
            text=f"📨 Mac task queued (id={task_id}){file_msg}. I'll post the result here when it's done.",
            thread_ts=thread_ts,
        )

        logger.info(
            "slack_mac_command_queued",
            task_id=task_id,
            user_id=user_id,
            channel_id=channel_id,
        )
        return {"ok": True, "handled": "mac", "task_id": task_id}

    except ImportError:
        logger.debug("mac_tasks service not available")
        await slack_client.post_message(
            channel=channel_id,
            text="❌ Mac agent is not available on this server.",
            thread_ts=thread_ts,
        )
        return {"ok": True, "handled": "mac_unavailable"}
    except Exception as e:
        logger.error("_handle_mac_command error", error=str(e))
        await slack_client.post_message(
            channel=channel_id,
            text=f"❌ Mac command error: {e!s}",
            thread_ts=thread_ts,
        )
        return {"ok": True, "handled": "mac_error"}


# =============================================================================
# Email Command Detection (ported from webhook_slack.py)
# =============================================================================


def _is_email_command(text: str) -> bool:
    """
    Detect if text is an email-related command.
    """
    email_keywords = [
        "email:",
        "mail:",
        "send email",
        "reply to",
        "draft email",
        "search email",
        "forward email",
    ]
    text_lower = text.strip().lower()

    # Check if text starts with any email keyword
    if any(text_lower.startswith(kw.lower()) for kw in email_keywords):
        return True

    # Check for email action phrases
    return bool(
        any(kw in text_lower for kw in ["send email to", "reply to", "forward to"])
    )


# =============================================================================
# Task Routing (ported from webhook_slack.py)
# =============================================================================


async def _route_to_mac_task(
    text: str,
    channel_id: str,
    user_id: str,
    file_artifacts: list,
    slack_client: SlackAPIClient,
    thread_ts: str | None = None,
) -> dict[str, Any] | None:
    """
    Route message to Mac Agent task planner for structured execution.

    Returns response dict if routed, None if routing not applicable/failed.
    """
    try:
        from orchestration.slack_task_router import route_slack_message
        from orchestrators.agent_execution.task_queue import enqueue_mac_task_dict

        # Route message + artifacts to mac_task structure
        task_dict = route_slack_message(text, file_artifacts, user_id)

        # Ensure it's a mac_task (safety check)
        if task_dict.get("type") != "mac_task":
            logger.warning(
                f"slack_task_router returned non-mac_task: {task_dict.get('type')}. "
                f"Fixing to mac_task."
            )
            task_dict["type"] = "mac_task"

        # Store channel in metadata for result posting
        if "metadata" not in task_dict:
            task_dict["metadata"] = {}
        task_dict["metadata"]["channel"] = channel_id

        # Enqueue mac_task
        task_id = enqueue_mac_task_dict(task_dict)

        # Respond in Slack
        response_msg = f"Task accepted and queued (ID: {task_id}). I'll let you know when it's done."

        await slack_client.post_message(
            channel=channel_id,
            text=response_msg,
            thread_ts=thread_ts,
        )

        logger.info(
            "slack_mac_task_routed",
            task_id=task_id,
            user_id=user_id,
            channel_id=channel_id,
        )
        return {"ok": True, "handled": "mac_task_routed", "task_id": task_id}

    except ImportError as e:
        logger.debug("mac task routing services not available", error=str(e))
        return None
    except Exception as e:
        logger.error("_route_to_mac_task error", error=str(e))
        return None


async def _route_to_email_task(
    text: str,
    channel_id: str,
    user_id: str,
    file_artifacts: list,
    slack_client: SlackAPIClient,
    thread_ts: str | None = None,
) -> dict[str, Any] | None:
    """
    Route message to Email Agent task planner for structured execution.

    Returns response dict if routed, None if routing not applicable/failed.
    """
    try:
        from email_agent.client import execute_email_task
        from orchestration.email_task_router import route_email_task

        # Route message + artifacts to email_task structure
        task_dict = route_email_task(text, file_artifacts, user_id)

        # Ensure it's an email_task (safety check)
        if task_dict.get("type") != "email_task":
            logger.warning(
                f"email_task_router returned non-email_task: {task_dict.get('type')}. "
                f"Fixing to email_task."
            )
            task_dict["type"] = "email_task"

        # Store channel in metadata for result posting
        if "metadata" not in task_dict:
            task_dict["metadata"] = {}
        task_dict["metadata"]["channel"] = channel_id

        # Execute email task directly (email_agent doesn't use file-based queue)
        result = execute_email_task(task_dict)

        # Respond in Slack
        if result.get("status") == "success":
            response_msg = "📧 Email task completed successfully."
        else:
            error = result.get("data", {}).get("error", "Unknown error")
            response_msg = f"📧 Email task failed: {error}"

        await slack_client.post_message(
            channel=channel_id,
            text=response_msg,
            thread_ts=thread_ts,
        )

        logger.info(
            "slack_email_task_routed",
            user_id=user_id,
            channel_id=channel_id,
            status=result.get("status"),
        )
        return {"ok": True, "handled": "email_task_executed", "result": result}

    except ImportError as e:
        logger.debug("email task routing services not available", error=str(e))
        return None
    except Exception as e:
        logger.error("_route_to_email_task error", error=str(e))
        return None


async def handle_slack_events(
    request_body: bytes,
    payload: dict[str, Any],
    substrate_service: MemorySubstrateService,
    slack_client: SlackAPIClient,
    aios_base_url: str,
    app: Any | None = None,
) -> dict[str, Any]:
    """
    Handle Slack event callback.

    Args:
        request_body: Raw request body (for audit trail)
        payload: Parsed JSON payload from Slack
        substrate_service: Memory substrate for packet persistence
        slack_client: Slack API client for posting replies
        aios_base_url: Base URL for AIOS service (e.g., http://localhost:8000)
        app: FastAPI app instance (for L-CTO agent routing via app.state.agent_executor)

    Returns:
        HTTP response dict (always 200 if we make it this far)
    """
    # Parse and normalize event
    normalized = SlackRequestNormalizer.parse_event_callback(payload)

    event_id = normalized.get("event_id")
    team_id = normalized.get("team_id")
    channel_id = normalized.get("channel_id")
    thread_ts = normalized.get("thread_ts")
    thread_uuid = normalized.get("thread_uuid")
    thread_string = normalized.get("thread_string")
    user_id = normalized.get("user_id")
    text = normalized.get("text", "")
    event_type = normalized.get("event_type")

    # CANONICAL LOG EVENT 3: Thread UUID generated
    logger.info(
        "slack_thread_uuid_generated",
        event_id=event_id,
        event_type=event_type,
        team_id=team_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        thread_uuid=thread_uuid,
        user_id=user_id,
    )

    # =========================================================================
    # CRITICAL: Ignore bot messages to prevent infinite response loops
    # =========================================================================
    event = payload.get("event", {})
    event_subtype = event.get("subtype")
    bot_id = event.get("bot_id")

    if event_subtype == "bot_message" or bot_id:
        logger.debug(
            "slack_ignoring_bot_message",
            event_id=event_id,
            bot_id=bot_id,
            subtype=event_subtype,
        )
        return {"ok": True, "ignored": "bot_message"}

    # Dedupe check: look for event_id in recent packets
    try:
        dedupe_result = await _check_duplicate(
            substrate_service=substrate_service,
            event_id=event_id,
            thread_uuid=thread_uuid,
            team_id=team_id,
            channel_id=channel_id,
            ts=normalized.get("ts"),
            user_id=user_id,
        )

        if dedupe_result.get("is_duplicate"):
            # CANONICAL LOG EVENT 4: Dedupe check - duplicate found
            logger.info(
                "slack_dedupe_check",
                event_id=event_id,
                is_duplicate=True,
                reason=dedupe_result.get("reason"),
            )
            record_idempotent_hit(team_id=team_id)
            return {"ok": True, "deduplicated": True}
    except Exception as e:
        logger.error(
            "slack_dedupe_check", error=str(e), event_id=event_id, is_duplicate=False
        )
        # Continue processing; dedupe is opportunistic

    # Retrieve memory context
    thread_context = {}
    semantic_hits = {}

    try:
        thread_context = await _retrieve_thread_context(
            substrate_service=substrate_service,
            thread_uuid=thread_uuid,
            limit=10,
        )
        logger.debug("slack_thread_context_retrieved", context_size=len(thread_context))
    except Exception as e:
        logger.warning(
            "slack_thread_context_retrieval_error",
            error=str(e),
            thread_uuid=thread_uuid,
        )

    try:
        semantic_hits = await _retrieve_semantic_hits(
            substrate_service=substrate_service,
            query=text,
            team_id=team_id,
            limit=5,
        )
        logger.debug("slack_semantic_hits_retrieved", hit_count=len(semantic_hits))
    except Exception as e:
        logger.warning("slack_semantic_hits_retrieval_error", error=str(e))

    # =========================================================================
    # @L Command Detection (GMP-11: Igor Command Interface)
    # =========================================================================
    # Check if message is an @L command and route through command interface
    is_l_command = False
    command_response = None

    try:
        from core.commands.parser import is_l_command as check_l_command
        from core.commands.parser import parse_command
        from core.commands.schemas import Command, NLPPrompt

        if check_l_command(text):
            is_l_command = True
            logger.info("slack_l_command_detected", text=text[:50], user_id=user_id)

            parsed = parse_command(text)

            if isinstance(parsed, Command):
                # Structured command - execute via command interface
                from core.commands.executor import CommandExecutor
                from core.compliance.audit_log import AuditLogger

                audit_logger = AuditLogger(substrate_service)
                executor = CommandExecutor(
                    agent_executor=None,  # Will be injected from app state if needed
                    approval_manager=None,
                    substrate_service=substrate_service,
                    audit_logger=audit_logger,
                )

                # Igor is the only authorized user for approvals
                command_user = "Igor" if user_id == "Igor" else user_id

                result = await executor.execute_command(
                    command=parsed,
                    user_id=command_user,
                    context={
                        "channel": channel_id,
                        "thread_ts": thread_ts,
                        "slack_user_id": user_id,
                    },
                )

                command_response = result.message
                logger.info(
                    "slack_l_command_executed",
                    command_type=parsed.type.value,
                    success=result.success,
                )

            elif isinstance(parsed, NLPPrompt):
                # NLP prompt - extract intent
                from core.commands.intent_extractor import extract_intent

                intent = await extract_intent(parsed)

                if intent.is_ambiguous:
                    command_response = (
                        f"I'm not sure I understood that correctly (confidence: {intent.confidence:.0%}). "
                        f"Could you please clarify?\n\n"
                        f"Detected intent: `{intent.intent_type.value}`"
                    )
                    if intent.ambiguities:
                        command_response += (
                            f"\nAmbiguities: {', '.join(intent.ambiguities)}"
                        )
                else:
                    # Forward to regular AIOS flow with intent context
                    # (intent will be used for context enrichment)
                    is_l_command = False  # Let it fall through to regular flow
                    logger.debug(
                        "slack_l_command_nlp_passthrough",
                        intent_type=intent.intent_type.value,
                        confidence=intent.confidence,
                    )

    except ImportError as e:
        logger.debug("slack_l_command_module_not_available", error=str(e))
    except Exception as e:
        logger.warning("slack_l_command_error", error=str(e))
        command_response = f"Command processing error: {e!s}"

    # If @L command was handled, use command response instead of AIOS
    if is_l_command and command_response:
        reply_text = command_response

        # Store inbound packet (with command metadata)
        try:
            inbound_packet_in = PacketEnvelopeIn(
                packet_type="slack.command",
                payload={
                    "event_id": event_id,
                    "thread_uuid": thread_uuid,
                    "thread_string": thread_string,
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "text": text,
                    "ts": normalized.get("ts"),
                    "thread_ts": thread_ts,
                    "is_l_command": True,
                },
                metadata=PacketMetadata(
                    schema_version="1.0.1",
                    agent="igor_command_interface",
                ),
                provenance=PacketProvenance(
                    source="slack",
                ),
            )

            result = await substrate_service.write_packet(inbound_packet_in)
            logger.debug(
                "slack_command_packet_stored",
                event_id=event_id,
                packet_id=result.packet_id,
            )
        except Exception as e:
            logger.error(
                "slack_command_packet_storage_error", error=str(e), event_id=event_id
            )

        # Post command response to Slack
        slack_ts = None
        slack_error = None

        try:
            slack_response_obj = await slack_client.post_message(
                channel=channel_id,
                text=reply_text,
                thread_ts=thread_ts,
                reply_broadcast=False,
            )
            slack_ts = slack_response_obj.get("ts")
            logger.info(
                "slack_command_reply_posted", event_id=event_id, slack_ts=slack_ts
            )
        except SlackClientError as e:
            slack_error = str(e)
            logger.error(
                "slack_command_post_error", event_id=event_id, error=slack_error
            )
        except Exception as e:
            slack_error = str(e)
            logger.error(
                "slack_command_post_exception", event_id=event_id, error=slack_error
            )

        # Store outbound packet
        try:
            outbound_packet_in = PacketEnvelopeIn(
                packet_type="slack.command.out",
                payload={
                    "event_id": event_id,
                    "thread_uuid": thread_uuid,
                    "thread_string": thread_string,
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "reply_text": reply_text,
                    "slack_ts": slack_ts,
                    "slack_error": slack_error,
                    "is_l_command": True,
                },
                metadata=PacketMetadata(
                    schema_version="1.0.1",
                    agent="igor_command_interface",
                ),
                provenance=PacketProvenance(
                    source="l9",
                ),
            )

            result = await substrate_service.write_packet(outbound_packet_in)
            logger.debug(
                "slack_command_outbound_stored",
                event_id=event_id,
                packet_id=result.packet_id,
            )

            # Index conversation for preferences and corrections
            try:
                await _index_slack_conversation(
                    substrate_service=substrate_service,
                    text=reply_text,
                    user_id=user_id,
                    packet_id=str(result.packet_id),
                    team_id=team_id,
                )
            except Exception as e:
                logger.debug(f"Slack indexing error (non-blocking): {e}")
        except Exception as e:
            logger.error(
                "slack_command_outbound_storage_error", error=str(e), event_id=event_id
            )

        return {"ok": True, "l_command": True}

    # =========================================================================
    # Feature Flag: L-CTO AgentTask Routing (from legacy webhook_slack.py)
    # =========================================================================
    # When L9_ENABLE_LEGACY_SLACK_ROUTER=False, route through L-CTO agent
    # This provides: DM handling, file attachments, !mac commands, email routing

    # Extract additional event details for enhanced handling
    files = payload.get("event", {}).get("files", [])
    channel_type = payload.get("event", {}).get("channel_type", "")
    is_dm = channel_type == "im" or (channel_id and channel_id.startswith("D"))

    # Process file attachments if present
    file_artifacts = await _process_file_attachments(files) if files else []
    if file_artifacts:
        logger.info(
            "slack_file_attachments_processed",
            count=len(file_artifacts),
            channel_id=channel_id,
            user_id=user_id,
        )

    # Detect email commands
    is_email_command = _is_email_command(text)

    # === !mac Command Handling ===
    if text.strip().lower().startswith("!mac"):
        mac_result = await _handle_mac_command(
            text=text,
            channel_id=channel_id,
            user_id=user_id,
            file_artifacts=file_artifacts,
            slack_client=slack_client,
            thread_ts=thread_ts,
        )
        if mac_result:
            return mac_result

    # === L-CTO Agent Routing (when legacy flag is False) ===
    should_use_l_agent = is_dm or "l9" in text.lower() or event_type == "app_mention"

    if not L9_ENABLE_LEGACY_SLACK_ROUTER and should_use_l_agent and text.strip():
        try:
            # Use app reference passed from router
            if app is not None:
                # Pass DAG-retrieved context (thread history + semantic hits) to L-CTO
                dag_context = {
                    "thread_context": thread_context,
                    "semantic_hits": semantic_hits,
                }

                # === Multi-Part Directive Support (harvested from tokenizer) ===
                # Segment input to handle compound directives like:
                # "Deploy RIL, test ToT, sync Supabase"
                segmenter = get_segmenter()
                segment_result = segmenter.segment(text)

                if segment_result.segment_count > 1:
                    # Multi-part: process each segment
                    logger.info(
                        "slack_multi_part_directive",
                        segment_count=segment_result.segment_count,
                        segments=segment_result.segments,
                    )

                    replies: list[tuple[str, str]] = []
                    for i, segment in enumerate(segment_result.segments):
                        segment_reply, segment_status = await handle_slack_with_l_agent(
                            app=app,
                            text=segment,
                            thread_uuid=str(thread_uuid),
                            team_id=team_id,
                            channel_id=channel_id,
                            user_id=user_id,
                            context={
                                **dag_context,
                                "segment_index": i,
                                "total_segments": segment_result.segment_count,
                                "from_multi_part": True,
                            },
                        )
                        replies.append((segment_reply, segment_status))

                    # Combine replies for multi-part response
                    successful = [r for r, s in replies if s == "completed"]
                    failed = [
                        r for r, s in replies if s not in ("completed", "duplicate")
                    ]

                    if failed:
                        reply = f"Processed {len(successful)}/{len(replies)} tasks:\n\n"
                        for i, (r, s) in enumerate(replies):
                            status_icon = "✅" if s == "completed" else "⚠️"
                            reply += f"{status_icon} **{segment_result.segments[i]}**: {r}\n\n"
                        status = "partial"
                    else:
                        reply = (
                            "\n\n---\n\n".join(successful)
                            if len(successful) > 1
                            else successful[0]
                            if successful
                            else "All tasks processed."
                        )
                        status = "completed"
                else:
                    # Single task: standard handling
                    reply, status = await handle_slack_with_l_agent(
                        app=app,
                        text=text,
                        thread_uuid=str(thread_uuid),
                        team_id=team_id,
                        channel_id=channel_id,
                        user_id=user_id,
                        context=dag_context,
                    )

                # Post reply to Slack
                if status in ("completed", "duplicate"):
                    await slack_client.post_message(
                        channel=channel_id,
                        text=reply,
                        thread_ts=thread_ts,
                    )
                else:
                    await slack_client.post_message(
                        channel=channel_id,
                        text=f"⚠️ {reply}",
                        thread_ts=thread_ts,
                    )

                logger.info(
                    "slack_l_agent_response",
                    status=status,
                    user_id=user_id,
                    channel_id=channel_id,
                )

                # Store outbound packet for L-CTO response
                try:
                    outbound_packet_in = PacketEnvelopeIn(
                        packet_type="slack.l_agent.out",
                        payload={
                            "event_id": event_id,
                            "thread_uuid": thread_uuid,
                            "thread_string": thread_string,
                            "team_id": team_id,
                            "channel_id": channel_id,
                            "user_id": user_id,
                            "reply_text": reply,
                            "status": status,
                            "is_dm": is_dm,
                        },
                        metadata=PacketMetadata(
                            schema_version="1.0.1",
                            agent="l-cto",
                        ),
                        provenance=PacketProvenance(
                            source="l9",
                        ),
                    )
                    await substrate_service.write_packet(outbound_packet_in)
                except Exception as e:
                    logger.error("slack_l_agent_packet_storage_error", error=str(e))

                return {"ok": True, "l_agent": True, "status": status}
            logger.warning("slack_l_agent_no_app_reference")
        except Exception as e:
            logger.error("slack_l_agent_routing_error", error=str(e))
            # Fall through to legacy AIOS flow

    # === Task Routing (files or email commands) ===
    if file_artifacts or is_email_command:
        if is_email_command:
            # Route to Email Agent
            route_result = await _route_to_email_task(
                text=text,
                channel_id=channel_id,
                user_id=user_id,
                file_artifacts=file_artifacts,
                slack_client=slack_client,
                thread_ts=thread_ts,
            )
        else:
            # Route to Mac Agent
            route_result = await _route_to_mac_task(
                text=text,
                channel_id=channel_id,
                user_id=user_id,
                file_artifacts=file_artifacts,
                slack_client=slack_client,
                thread_ts=thread_ts,
            )
        if route_result:
            return route_result

    # === Simple DM Response (when no special handling needed) ===
    if (
        is_dm
        and not file_artifacts
        and not is_email_command
        and not text.strip().startswith("!mac")
    ):
        # For simple DMs, provide a helpful response about available commands
        await slack_client.post_message(
            channel=channel_id,
            text=(
                f'👋 Hey! L9 here. You said: "{text[:100]}{"..." if len(text) > 100 else ""}"\n\n'
                "Try:\n"
                "• `!mac <command>` - Run a Mac automation\n"
                "• `email: <request>` - Email operations\n"
                "• Attach a file for processing\n"
                "• Or just chat with me!"
            ),
            thread_ts=thread_ts,
        )
        logger.info("slack_simple_dm_response", user_id=user_id, channel_id=channel_id)
        return {"ok": True, "simple_dm": True}

    # =========================================================================
    # DEPRECATED: Legacy AIOS Flow (GMP-60: Runtime Hardening)
    # =========================================================================
    # This flow bypasses AgentExecutorService and calls /chat directly.
    # It does NOT enforce:
    # - Kernel-aware system prompts
    # - Prompt injection defense
    # - Capability gating
    # - Governance approval gates
    #
    # RECOMMENDATION: Set L9_ENABLE_LEGACY_SLACK_ROUTER=false to use
    # the kernel-governed L-CTO agent flow instead.
    # =========================================================================

    # Log deprecation warning (GMP-60)
    logger.warning(
        "slack_legacy_aios_flow_deprecated",
        event_id=event_id,
        message="Legacy AIOS flow bypasses governance. Set L9_ENABLE_LEGACY_SLACK_ROUTER=false.",
        user_id=user_id,
        channel_id=channel_id,
    )

    # Call AIOS /chat endpoint
    aios_response = None
    aios_error = None
    aios_start_time = current_time()

    # CANONICAL LOG EVENT 5: AIOS call start (DEPRECATED)
    logger.info(
        "slack_aios_call_start", event_id=event_id, agent_type="aios", deprecated=True
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            system_prompt = _build_system_prompt(
                thread_context=thread_context,
                semantic_hits=semantic_hits,
                user_id=user_id,
                channel_id=channel_id,
            )

            aios_payload = {
                "message": text,
                "system_prompt": system_prompt,
            }

            aios_response_obj = await client.post(
                f"{aios_base_url}/chat",
                json=aios_payload,
            )
            aios_response_obj.raise_for_status()
            aios_response = aios_response_obj.json()

            aios_duration = current_time() - aios_start_time
            # CANONICAL LOG EVENT 6: AIOS call complete
            logger.info(
                "slack_aios_call_complete",
                event_id=event_id,
                response_length=len(aios_response.get("reply", "")),
                duration_seconds=aios_duration,
                status="success",
            )
            record_aios_call(agent_type="aios", duration_seconds=aios_duration)
    except httpx.TimeoutException:
        aios_error = "AIOS timeout (10s)"
        aios_duration = current_time() - aios_start_time
        logger.error(
            "slack_aios_call_complete",
            event_id=event_id,
            status="timeout",
            duration_seconds=aios_duration,
        )
        record_aios_call(agent_type="aios", duration_seconds=aios_duration)
    except httpx.HTTPStatusError as e:
        aios_error = f"AIOS HTTP {e.response.status_code}"
        aios_duration = current_time() - aios_start_time
        logger.error(
            "slack_aios_call_complete",
            event_id=event_id,
            status="http_error",
            http_status=e.response.status_code,
            duration_seconds=aios_duration,
        )
        record_aios_call(agent_type="aios", duration_seconds=aios_duration)
    except Exception as e:
        aios_error = str(e)
        aios_duration = current_time() - aios_start_time
        logger.error(
            "slack_aios_call_complete",
            event_id=event_id,
            status="error",
            error=aios_error,
            duration_seconds=aios_duration,
        )
        record_aios_call(agent_type="aios", duration_seconds=aios_duration)

    # Store inbound packet
    try:
        inbound_packet_in = PacketEnvelopeIn(
            packet_type="slack.in",
            payload={
                "event_id": event_id,
                "thread_uuid": thread_uuid,
                "thread_string": thread_string,
                "team_id": team_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "text": text,
                "ts": normalized.get("ts"),
                "thread_ts": thread_ts,
            },
            metadata=PacketMetadata(
                schema_version="1.0.1",
                agent="slack_adapter",
            ),
            provenance=PacketProvenance(
                source="slack",
            ),
        )

        result = await substrate_service.write_packet(inbound_packet_in)
        # CANONICAL LOG EVENT 7: Packet stored
        logger.debug(
            "slack_packet_stored",
            event_id=event_id,
            packet_id=result.packet_id,
            packet_type="slack.in",
        )

        # Index conversation for preferences and corrections
        try:
            await _index_slack_conversation(
                substrate_service=substrate_service,
                text=text,
                user_id=user_id,
                packet_id=str(result.packet_id),
                team_id=team_id,
            )
        except Exception as e:
            logger.debug(f"Slack indexing error (non-blocking): {e}")
    except Exception as e:
        # CANONICAL LOG EVENT 9: Handler error
        logger.error(
            "slack_handler_error",
            error=str(e),
            event_id=event_id,
            context="inbound_packet_storage",
        )
        record_packet_write_error(packet_type="slack.in")

    # Prepare outbound response
    reply_text = aios_response.get("reply") if aios_response else None

    if not reply_text and aios_error:
        reply_text = "Sorry, I encountered a temporary error. Please try again."

    if not reply_text:
        reply_text = "No response generated."

    # Post reply to Slack
    slack_ts = None
    slack_error = None

    try:
        slack_response = await slack_client.post_message(
            channel=channel_id,
            text=reply_text,
            thread_ts=thread_ts,
            reply_broadcast=False,
        )
        slack_ts = slack_response.get("ts")
        # CANONICAL LOG EVENT 8: Reply sent
        logger.info(
            "slack_reply_sent",
            event_id=event_id,
            slack_ts=slack_ts,
            channel_id=channel_id,
        )
    except SlackClientError as e:
        slack_error = str(e)
        logger.error(
            "slack_reply_sent", event_id=event_id, error=slack_error, status="error"
        )
        record_slack_reply_error(error_type="api_error")
    except Exception as e:
        slack_error = str(e)
        logger.error(
            "slack_reply_sent", event_id=event_id, error=slack_error, status="exception"
        )
        record_slack_reply_error(error_type="exception")

    # Store outbound packet
    try:
        outbound_packet_in = PacketEnvelopeIn(
            packet_type="slack.out",
            payload={
                "event_id": event_id,
                "thread_uuid": thread_uuid,
                "thread_string": thread_string,
                "team_id": team_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "reply_text": reply_text,
                "slack_ts": slack_ts,
                "aios_error": aios_error,
                "slack_error": slack_error,
            },
            metadata=PacketMetadata(
                schema_version="1.0.1",
                agent="slack_adapter",
            ),
            provenance=PacketProvenance(
                source="aios",
            ),
        )

        result = await substrate_service.write_packet(outbound_packet_in)
        # CANONICAL LOG EVENT 7: Packet stored (outbound)
        logger.debug(
            "slack_packet_stored",
            event_id=event_id,
            packet_id=result.packet_id,
            packet_type="slack.out",
        )

        # Index conversation for preferences and corrections
        try:
            await _index_slack_conversation(
                substrate_service=substrate_service,
                text=reply_text,
                user_id=user_id,
                packet_id=str(result.packet_id),
                team_id=team_id,
            )
        except Exception as e:
            logger.debug(f"Slack indexing error (non-blocking): {e}")
    except Exception as e:
        # CANONICAL LOG EVENT 9: Handler error
        logger.error(
            "slack_handler_error",
            error=str(e),
            event_id=event_id,
            context="outbound_packet_storage",
        )

    return {"ok": True}


async def handle_slack_commands(
    payload: dict[str, Any],
    substrate_service: MemorySubstrateService,
    slack_client: SlackAPIClient,
    aios_base_url: str,
) -> dict[str, Any]:
    """
    Handle Slack slash command (asynchronous follow-up).

    Called after returning 200 ACK to Slack.

    Args:
        payload: Form-encoded command payload from Slack
        substrate_service: Memory substrate for packet persistence
        slack_client: Slack API client for async reply
        aios_base_url: Base URL for AIOS service

    Returns:
        Response (for logging, not sent to Slack)
    """
    normalized = SlackRequestNormalizer.parse_command(payload)

    command = normalized.get("command", "")
    text = normalized.get("text", "")
    user_id = normalized.get("user_id", "")
    channel_id = normalized.get("channel_id", "")
    team_id = normalized.get("team_id", "")
    response_url = normalized.get("response_url", "")
    thread_uuid = normalized.get("thread_uuid", "")

    logger.info(
        "slack_command_received",
        command=command,
        user_id=user_id,
        channel_id=channel_id,
        text=text[:50],
    )

    # Parse command text
    # Format: /l9 do <task> | /l9 email <instruction> | /l9 extract <artifact>
    parts = text.split(None, 1)
    if len(parts) < 2:
        return {
            "response_type": "ephemeral",
            "text": "Usage: /l9 do <task> | /l9 email <instruction> | /l9 extract <artifact>",
        }

    subcommand = parts[0].lower()
    full_text = parts[1] if len(parts) > 1 else ""

    # Route to AIOS /chat
    aios_response = None
    aios_error = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            system_prompt = f"User issued command: /{command} {subcommand}"
            aios_payload = {
                "message": full_text,
                "system_prompt": system_prompt,
            }

            aios_response_obj = await client.post(
                f"{aios_base_url}/chat",
                json=aios_payload,
            )
            aios_response_obj.raise_for_status()
            aios_response = aios_response_obj.json()
            logger.info("aios_command_success", command=command, subcommand=subcommand)
    except Exception as e:
        aios_error = str(e)
        logger.error("aios_command_error", command=command, error=aios_error)

    # Build response
    reply_text = aios_response.get("reply") if aios_response else None

    if not reply_text and aios_error:
        reply_text = "Sorry, I encountered an error processing your command."

    if not reply_text:
        reply_text = "No response generated."

    # Post to response_url or Slack API
    slack_error = None

    if response_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    response_url,
                    json={
                        "response_type": "in_channel",
                        "text": reply_text,
                    },
                )
            logger.info("slack_command_response_posted_to_url", command=command)
        except Exception as e:
            slack_error = str(e)
            logger.error("slack_command_response_url_error", error=slack_error)

    # Store command packet
    try:
        command_packet_in = PacketEnvelopeIn(
            packet_type="slack.command",
            payload={
                "command": command,
                "subcommand": subcommand,
                "full_text": full_text,
                "team_id": team_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_uuid": thread_uuid,
                "aios_error": aios_error,
                "slack_error": slack_error,
            },
            metadata=PacketMetadata(
                schema_version="1.0.1",
                agent="slack_adapter",
            ),
            provenance=PacketProvenance(
                source="slack",
            ),
        )

        result = await substrate_service.write_packet(command_packet_in)
        logger.debug("slack_command_packet_stored", packet_id=result.packet_id)
    except Exception as e:
        logger.error("slack_command_packet_storage_error", error=str(e))

    return {"ok": True}


# ============================================================================
# Helper Functions


async def _check_duplicate(
    substrate_service: MemorySubstrateService,
    event_id: str,
    thread_uuid: str,
    team_id: str,
    channel_id: str,
    ts: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Check if event already processed.

    Queries packet_store for duplicate events using two strategies:
    1. Direct event_id match in payload
    2. Composite match on team_id, channel_id, ts, user_id in payload

    Returns dedupe result with is_duplicate, reason, and matched packet_id if found.

    Args:
        substrate_service: Memory substrate service instance
        event_id: Slack event ID (unique per event)
        thread_uuid: Thread UUID (for context, not used in dedupe)
        team_id: Slack workspace/team ID
        channel_id: Slack channel ID
        ts: Slack message timestamp
        user_id: Slack user ID

    Returns:
        Dict with:
            - is_duplicate: bool
            - reason: str (if duplicate found, explains why)
            - packet_id: str (if duplicate found, the matched packet ID)
    """
    try:
        # Access repository for raw SQL query
        repository = substrate_service._repository

        async with repository.acquire() as conn:
            # Query for duplicate using event_id OR composite match
            # The envelope column is JSONB, so we use -> for object access and ->> for text extraction
            row = await conn.fetchrow(
                """
                SELECT packet_id, envelope, timestamp
                FROM packet_store
                WHERE
                    (envelope->'payload'->>'event_id' = $1)
                    OR (
                        envelope->'payload'->>'team_id' = $2
                        AND envelope->'payload'->>'channel_id' = $3
                        AND envelope->'payload'->>'ts' = $4
                        AND envelope->'payload'->>'user_id' = $5
                    )
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                event_id,
                team_id,
                channel_id,
                ts,
                user_id,
            )

            if row:
                # Found a duplicate
                matched_packet_id = str(row["packet_id"])
                envelope = row["envelope"]

                # Determine reason for duplicate
                if isinstance(envelope, dict):
                    payload = envelope.get("payload", {})
                    matched_event_id = payload.get("event_id")
                    if matched_event_id == event_id:
                        reason = "event_id_match"
                    else:
                        reason = "composite_match"
                else:
                    reason = "duplicate_found"

                logger.debug(
                    "slack_duplicate_detected",
                    event_id=event_id,
                    matched_packet_id=matched_packet_id,
                    reason=reason,
                )

                return {
                    "is_duplicate": True,
                    "reason": reason,
                    "packet_id": matched_packet_id,
                }

            # No duplicate found
            return {"is_duplicate": False}

    except Exception as e:
        logger.error("dedupe_check_error", error=str(e), event_id=event_id)
        # On error, return not duplicate to allow processing (fail open)
        return {"is_duplicate": False, "reason": "dedupe_check_failed"}


async def _retrieve_thread_context(
    substrate_service: MemorySubstrateService,
    thread_uuid: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Retrieve recent packets in thread (thread context).

    Queries packet_store for packets matching the thread_uuid.
    """
    try:
        packets = await substrate_service.search_packets_by_thread(
            thread_id=thread_uuid,
            limit=limit,
        )
        return {"packets": packets}
    except Exception as e:
        logger.error(
            "thread_context_retrieval_error", error=str(e), thread_uuid=thread_uuid
        )
        # Log to error telemetry (non-blocking)
        try:
            import asyncio

            from core.error_tracking import log_error_to_graph

            asyncio.create_task(
                log_error_to_graph(
                    error=e,
                    context={"thread_uuid": thread_uuid, "limit": limit},
                    source="memory.slack_ingest.thread_context",
                )
            )
        except ImportError:
            pass
        return {"packets": [], "error": str(e)}


async def _retrieve_semantic_hits(
    substrate_service: MemorySubstrateService,
    query: str,
    team_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Retrieve semantically similar packets.

    Calls substrate_service.semantic_search for vector similarity search.
    """
    from core.schemas import SemanticSearchRequest

    try:
        request = SemanticSearchRequest(
            query=query,
            top_k=limit,
            agent_id=team_id,
        )
        result = await substrate_service.semantic_search(request)
        return {
            "results": [
                {
                    "embedding_id": str(hit.embedding_id),
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in result.hits
            ]
        }
    except Exception as e:
        logger.error(
            "semantic_search_error", error=str(e), query=query[:100], team_id=team_id
        )
        # Log to error telemetry (non-blocking)
        try:
            import asyncio

            from core.error_tracking import log_error_to_graph

            asyncio.create_task(
                log_error_to_graph(
                    error=e,
                    context={"query": query[:100], "team_id": team_id, "limit": limit},
                    source="memory.slack_ingest.semantic_search",
                )
            )
        except ImportError:
            pass
        return {"results": [], "error": str(e)}


async def _index_slack_conversation(
    substrate_service: MemorySubstrateService,
    text: str,
    user_id: str,
    packet_id: str,
    team_id: str,
) -> None:
    """
    Index Slack conversation - extract preferences and corrections, create knowledge facts and embeddings.

    Extracts:
    - User preferences (patterns like "I prefer", "I like", "use X instead of Y")
    - Corrections (patterns like "that's wrong", "should be", "actually")
    - Creates knowledge facts (subject=Igor, predicate=prefers/corrects, object=pattern)
    - Creates semantic embeddings for conversation context
    """
    try:
        import re

        # Extract preferences
        preference_patterns = [
            r"(?:I|we)\s+prefer\s+(.+?)(?:\.|$|,)",
            r"(?:I|we)\s+like\s+(.+?)(?:\.|$|,)",
            r"use\s+([^\.]+?)\s+instead\s+of",
            r"(?:I|we)\s+want\s+(.+?)(?:\.|$|,)",
        ]

        preferences = []
        for pattern in preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                pref = match.group(1).strip()
                if len(pref) > 10 and len(pref) < 200:
                    preferences.append(pref)

        # Extract corrections
        correction_patterns = [
            r"(?:that\'?s|that is)\s+wrong[:\s]+(.+?)(?:\.|$|,)",
            r"should\s+be\s+(.+?)(?:\.|$|,)",
            r"actually[,\s]+(.+?)(?:\.|$|,)",
            r"correct(?:ion|ed)?[:\s]+(.+?)(?:\.|$|,)",
        ]

        corrections = []
        for pattern in correction_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                corr = match.group(1).strip()
                if len(corr) > 10 and len(corr) < 200:
                    corrections.append(corr)

        # Create knowledge facts for preferences
        for pref in preferences[:5]:  # Limit to 5
            try:
                await substrate_service._repository.insert_knowledge_fact(
                    subject=user_id,
                    predicate="prefers",
                    object_value={
                        "preference": pref,
                        "source": "slack",
                        "team_id": team_id,
                    },
                    confidence=0.8,
                    source_packet=packet_id if packet_id else None,
                )
            except Exception as e:
                logger.debug(f"Failed to create preference fact: {e}")

        # Create knowledge facts for corrections
        for corr in corrections[:5]:  # Limit to 5
            try:
                await substrate_service._repository.insert_knowledge_fact(
                    subject=user_id,
                    predicate="corrects",
                    object_value={
                        "correction": corr,
                        "source": "slack",
                        "team_id": team_id,
                    },
                    confidence=0.85,
                    source_packet=packet_id if packet_id else None,
                )
            except Exception as e:
                logger.debug(f"Failed to create correction fact: {e}")

        # Create semantic embedding for conversation context if significant content
        if len(text) > 50 and (preferences or corrections):
            try:
                context_text = f"Slack conversation from {user_id}:\n{text}"
                if preferences:
                    context_text += f"\nPreferences: {', '.join(preferences[:3])}"
                if corrections:
                    context_text += f"\nCorrections: {', '.join(corrections[:3])}"

                await substrate_service.embed_text(
                    text=context_text,
                    payload={
                        "user_id": user_id,
                        "team_id": team_id,
                        "type": "slack_conversation",
                        "has_preferences": len(preferences) > 0,
                        "has_corrections": len(corrections) > 0,
                    },
                    agent_id=team_id,
                )
            except Exception as e:
                logger.debug(f"Failed to create conversation embedding: {e}")

    except Exception as e:
        logger.debug(f"Slack conversation indexing error: {e}")


def _build_system_prompt(
    thread_context: dict[str, Any],
    semantic_hits: dict[str, Any],
    user_id: str,
    channel_id: str,
) -> str:
    """
    Build system prompt that includes thread context and semantic hits.

    This gives the AIOS model context about the conversation thread and
    any related prior knowledge from the memory substrate.
    """
    parts = [
        "You are an AI assistant integrated with Slack. Respond helpfully and concisely.",
        f"User ID: {user_id}",
        f"Channel: {channel_id}",
    ]

    if thread_context and thread_context.get("packets"):
        parts.append("\nRecent thread context:")
        for item in thread_context.get("packets", [])[:5]:
            content = item.get("payload", {}).get("text", "")[:200]
            if content:
                parts.append(f"  - {content}")

    if semantic_hits and semantic_hits.get("results"):
        parts.append("\nRelated knowledge:")
        for item in semantic_hits.get("results", [])[:3]:
            content = item.get("payload", {}).get("text", "")[:200]
            if content:
                parts.append(f"  - {content}")

    return "\n".join(parts)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "api.slack_adapter",
        "api.slack_client",
        "core.agents.schemas",
        "core.commands.executor",
        "core.commands.intent_extractor",
    ],
    "tags": [
        "api",
        "async",
        "auth",
        "debugging",
        "engine",
        "event-driven",
        "http-client",
        "learning",
        "logging",
        "memory-substrate",
    ],
    "keywords": [
        "agent",
        "agentexecutorservice",
        "aios",
        "check",
        "command",
        "commands",
        "delivery",
        "detection",
    ],
    "business_value": "1. Dedupe check (prevent double-processing) 2. Memory context retrieval (fetch thread history + semantic hits) 3. L-CTO agent routing via AgentExecutorService (when legacy flag is False) 4. AIOS /chat",
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
