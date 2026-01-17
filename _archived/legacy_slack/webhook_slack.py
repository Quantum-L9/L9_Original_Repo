"""
⚠️ DEPRECATED - NOT USED ⚠️

This file is DEPRECATED and NOT registered in api/server.py.

**Status**: Legacy implementation - features ported to memory/slack_ingest.py
**Archive Date**: 2026-01-08
**Replacement**: api/routes/slack.py → memory/slack_ingest.py

**What uses this file**: Nothing (not wired in server.py)
**What should be used instead**: 
  - api/routes/slack.py (FastAPI routes)
  - memory/slack_ingest.py (event handling logic)

**Migration**: All features from this file have been ported to:
  - memory/slack_ingest.py (main handler)
  - orchestration/slack_task_router.py (task routing)
  - api/routes/slack.py (HTTP endpoints)

**Why archived**: 
  - Not registered in api/server.py (line 2101-2102: "NOT USED")
  - Duplicate functionality with routes/slack.py
  - All features successfully ported to slack_ingest.py

**Do not use this file** - it exists only for reference.
"""

import os
import hmac
import hashlib
import time
from typing import Optional
from collections import OrderedDict
from threading import Lock
import structlog
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from config.settings import settings

logger = structlog.get_logger(__name__)

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_APP_ENABLED = os.getenv("SLACK_APP_ENABLED", "true").lower() == "true"

# Bot user ID - used to filter out bot's own messages to prevent infinite loops
# Supports both old SLACK_BOT_USER_ID and new L_SLACK_USER_ID
SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID", "")
L_SLACK_USER_ID = os.getenv("L_SLACK_USER_ID", "l-cto")

# Combined list of user IDs to ignore (L's own messages)
L_USER_IDS = {uid.strip().lower() for uid in [SLACK_BOT_USER_ID, L_SLACK_USER_ID] if uid.strip()}


# =============================================================================
# Event Deduplication Cache
# =============================================================================
# Prevents processing the same Slack event multiple times
# (Slack retries webhooks after 3s if no 200 response)

class EventDedupeCache:
    """
    Thread-safe LRU cache for event deduplication.
    
    Stores event_ids with timestamps to prevent duplicate processing.
    Auto-evicts entries older than TTL or when max_size is exceeded.
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()
        self._max_size = max_size
        self._ttl = ttl_seconds
    
    def is_duplicate(self, event_id: str) -> bool:
        """
        Check if event_id was recently processed.
        
        Returns True if duplicate (should skip processing).
        Returns False if new (will be marked as processed).
        """
        if not event_id:
            return False  # No event_id = can't dedupe, process it
        
        now = time.time()
        
        with self._lock:
            # Check if already processed
            if event_id in self._cache:
                timestamp = self._cache[event_id]
                if now - timestamp < self._ttl:
                    logger.debug(
                        "slack_event_duplicate",
                        event_id=event_id,
                        age_seconds=round(now - timestamp, 2),
                    )
                    return True
                # Expired, remove it
                del self._cache[event_id]
            
            # Mark as processed
            self._cache[event_id] = now
            
            # Move to end (LRU)
            self._cache.move_to_end(event_id)
            
            # Evict old entries if over max_size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            
            return False
    
    def clear(self):
        """Clear the cache (for testing)."""
        with self._lock:
            self._cache.clear()


# Global deduplication cache
_event_dedupe_cache = EventDedupeCache(max_size=10000, ttl_seconds=300)

# Email command detection keywords (used in multiple handlers)
EMAIL_KEYWORDS = [
    "email:",
    "mail:",
    "send email",
    "reply to",
    "draft email",
    "search email",
    "forward email",
]
EMAIL_PHRASE_KEYWORDS = ["send email to", "reply to", "forward to"]

# Feature flag for legacy Slack routing
# When False, route Slack messages through AgentTask + AgentExecutorService
L9_ENABLE_LEGACY_SLACK_ROUTER = settings.l9_enable_legacy_slack_router


# =============================================================================
# L-CTO Agent Handler for Slack (Phase 2 prep - not yet wired)
# =============================================================================


async def handle_slack_with_l_agent(
    app,
    text: str,
    thread_uuid: str,
    team_id: str,
    channel_id: str,
    user_id: str,
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

    Returns:
        Tuple of (reply_text, status) where:
        - reply_text: The agent's response formatted for Slack
        - status: One of "completed", "duplicate", "failed", "error"

    Example:
        reply, status = await handle_slack_with_l_agent(
            app=request.app,
            text="What is the status of L9?",
            thread_uuid="slack-1234567890.123456",
            team_id="T12345678",
            channel_id="C12345678",
            user_id="U12345678",
        )
        if status == "completed":
            slack_post(channel_id, reply)
    """
    try:
        # Import here to avoid circular imports
        from core.agents.schemas import (
            AgentTask,
            TaskKind,
            ExecutionResult,
            DuplicateTaskResponse,
        )

        # Check if agent executor is available
        agent_executor = getattr(app.state, "agent_executor", None)
        if agent_executor is None:
            logger.error("handle_slack_with_l_agent: agent_executor not available")
            return ("L9 agent executor not available. Please try again later.", "error")

        # Construct AgentTask for L-CTO
        task = AgentTask(
            agent_id="l-cto",
            kind=TaskKind.CONVERSATION,
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
        )

        logger.info(
            "handle_slack_with_l_agent: task_id=%s, thread=%s, user=%s",
            str(task.id),
            thread_uuid,
            user_id,
        )

        # Execute task via AgentExecutorService
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
        return (f"Error processing message: {str(e)}", "error")


router = APIRouter()


@router.post("/slack/commands")
async def slack_commands(request: Request):
    """
    Handle Slack slash commands.

    Supported commands:
    - /l9 do <task> - Execute a task
    - /l9 email <instruction> - Email operation
    - /l9 extract <artifact> - Extract data from artifact
    """
    if not SLACK_APP_ENABLED:
        raise HTTPException(status_code=503, detail="Slack integration disabled")

    # Slash commands come as form data
    form_data = await request.form()
    command_text = form_data.get("text", "")
    command = form_data.get("command", "")
    user_id = form_data.get("user_id", "")
    channel_id = form_data.get("channel_id", "")
    response_url = form_data.get("response_url", "")

    logger.info(f"[SLACK] Slash command: {command} from {user_id} in {channel_id}")

    try:
        from orchestration.slack_task_router import route_slack_message
        from services.mac_tasks import enqueue_task

        # Parse command
        parts = command_text.split(maxsplit=1)
        subcommand = parts[0].lower() if parts else ""
        instruction = parts[1] if len(parts) > 1 else ""

        if subcommand == "do":
            # Route to task planner
            task_dict = route_slack_message(instruction, [], user_id)
            task_dict["metadata"]["channel"] = channel_id

            task_id = enqueue_task(task_dict)

            return JSONResponse(
                content={
                    "response_type": "ephemeral",
                    "text": f"Task accepted and queued (ID: {task_id}). I'll post the result here when it's done.",
                }
            )

        elif subcommand == "email":
            # Email operation - parse subcommands
            email_parts = instruction.split(maxsplit=1)
            email_subcommand = email_parts[0].lower() if email_parts else ""
            email_args = email_parts[1] if len(email_parts) > 1 else ""

            try:
                from email_agent.gmail_client import GmailClient

                client = GmailClient()

                if email_subcommand == "search":
                    # /l9 email search <query>
                    messages = client.list_messages(email_args, limit=10)
                    if messages:
                        result_text = f"Found {len(messages)} messages:\n"
                        for msg in messages[:5]:  # Show first 5
                            result_text += f"• {msg.get('subject', 'No subject')} from {msg.get('from', 'Unknown')}\n"
                        if len(messages) > 5:
                            result_text += f"... and {len(messages) - 5} more"
                    else:
                        result_text = "No messages found"

                    return JSONResponse(
                        content={"response_type": "in_channel", "text": result_text}
                    )

                elif email_subcommand == "read":
                    # /l9 email read <id>
                    message = client.get_message(email_args)
                    if message:
                        result_text = f"📧 {message.get('subject', 'No subject')}\n"
                        result_text += f"From: {message.get('from', 'Unknown')}\n"
                        result_text += f"Date: {message.get('date', 'Unknown')}\n\n"
                        body = message.get("body_plain", message.get("body_html", ""))
                        result_text += body[:500] + ("..." if len(body) > 500 else "")

                        attachments = message.get("attachments", [])
                        if attachments:
                            result_text += f"\n\n📎 {len(attachments)} attachment(s)"
                    else:
                        result_text = f"Message {email_args} not found"

                    return JSONResponse(
                        content={"response_type": "in_channel", "text": result_text}
                    )

                elif email_subcommand == "draft":
                    # /l9 email draft <natural language>
                    # Route through planner
                    task_dict = route_slack_message(
                        f"draft email: {email_args}", [], user_id
                    )
                    task_dict["metadata"]["channel"] = channel_id
                    task_id = enqueue_task(task_dict)

                    return JSONResponse(
                        content={
                            "response_type": "ephemeral",
                            "text": f"Email draft task queued (ID: {task_id}). I'll post the draft here when ready.",
                        }
                    )

                elif email_subcommand == "send":
                    # /l9 email send <draft_id>
                    # This would need to be handled via task execution
                    task_dict = route_slack_message(
                        f"send email draft: {email_args}", [], user_id
                    )
                    task_dict["metadata"]["channel"] = channel_id
                    task_id = enqueue_task(task_dict)

                    return JSONResponse(
                        content={
                            "response_type": "ephemeral",
                            "text": f"Email send task queued (ID: {task_id}). Processing...",
                        }
                    )

                else:
                    # Default: route through planner
                    task_dict = route_slack_message(
                        f"email: {instruction}", [], user_id
                    )
                    task_dict["metadata"]["channel"] = channel_id
                    task_id = enqueue_task(task_dict)

                    return JSONResponse(
                        content={
                            "response_type": "ephemeral",
                            "text": f"Email task queued (ID: {task_id}). Processing...",
                        }
                    )

            except Exception as e:
                logger.error(f"Email command error: {e}", exc_info=True)
                return JSONResponse(
                    content={
                        "response_type": "ephemeral",
                        "text": f"Email error: {str(e)}",
                    }
                )

        elif subcommand == "extract":
            # Extract from artifact (requires artifact ID or name)
            return JSONResponse(
                content={
                    "response_type": "ephemeral",
                    "text": "Extract command requires an artifact attachment. Please attach a file and use /l9 do <instruction>.",
                }
            )

        else:
            return JSONResponse(
                content={
                    "response_type": "ephemeral",
                    "text": "Unknown command. Use /l9 do <task>, /l9 email <instruction>, or /l9 extract <artifact>",
                }
            )

    except Exception as e:
        logger.error(f"[SLACK] Slash command error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "response_type": "ephemeral",
                "text": f"Error processing command: {str(e)}",
            }
        )


def verify_slack_signature(
    body: str,
    timestamp: str,
    signature: str,
    signing_secret: Optional[str] = SLACK_SIGNING_SECRET,
) -> bool:
    """
    Verify Slack request signature.
    Rejects replay attacks (>5 minutes skew).
    """
    if not signing_secret:
        return False
    if not timestamp or not signature:
        return False

    # Check timestamp to prevent replay attacks
    try:
        request_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - request_time) > 300:  # 5 minutes
            logger.warning(
                f"Slack request timestamp too old: {request_time} (current: {current_time})"
            )
            return False
    except ValueError:
        return False

    # Create signature base string
    sig_basestring = f"v0:{timestamp}:{body}"

    # Compute expected signature
    expected_signature = hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()

    expected_sig_string = f"v0={expected_signature}"

    # Compare signatures using constant-time comparison
    return hmac.compare_digest(expected_sig_string, signature)


@router.post("/slack/events")
async def slack_events(
    request: Request,
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
):
    """
    Slack Events API webhook handler.
    Handles:
    - url_verification: Echoes challenge
    - event_callback: Processes app_mention and messages containing "l9"
    """
    # Check if Slack is enabled
    if not SLACK_APP_ENABLED:
        raise HTTPException(status_code=503, detail="Slack integration disabled")

    # Read raw body for signature verification
    body_raw = await request.body()
    body_str = body_raw.decode("utf-8")

    # Verify signature
    if not SLACK_SIGNING_SECRET:
        logger.error("[SLACK] SLACK_SIGNING_SECRET not configured")
        raise HTTPException(
            status_code=500, detail="Slack signing secret not configured"
        )

    if not verify_slack_signature(
        body_str,
        x_slack_request_timestamp or "",
        x_slack_signature or "",
        SLACK_SIGNING_SECRET,
    ):
        logger.warning("[SLACK] Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse JSON payload (reuse body_str since we already read it)
    try:
        import json

        data = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"[SLACK] Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        challenge = data.get("challenge")
        if challenge:
            logger.info("[SLACK] URL verification challenge received")
            return JSONResponse(content={"challenge": challenge})
        else:
            raise HTTPException(status_code=400, detail="Missing challenge")

    # Handle event callbacks
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        event_type = event.get("type")
        event_subtype = event.get("subtype")
        event_id = data.get("event_id", "")
        
        # === DEDUPLICATION CHECK ===
        # Slack retries webhooks after 3s if no 200 response
        # This prevents processing the same event multiple times
        if _event_dedupe_cache.is_duplicate(event_id):
            logger.info(
                "slack_event_deduplicated",
                event_id=event_id,
                event_type=event_type,
            )
            return JSONResponse(content={"status": "ok"})

        # === BOT MESSAGE FILTERING ===
        # Ignore bot messages (check subtype, bot_id, AND our own user_id to prevent infinite loops)
        # This prevents the recursive "Hey! L9 here. You said:" echo bug (Dec 18, 2025)
        event_user = event.get("user", "")
        event_user_lower = event_user.lower() if event_user else ""
        
        is_bot_message = (
            event_subtype == "bot_message"
            or event.get("bot_id")
            or (L_USER_IDS and event_user_lower in L_USER_IDS)
        )
        if is_bot_message:
            logger.debug(
                "slack_ignoring_bot_message",
                bot_id=event.get("bot_id"),
                subtype=event_subtype,
                user=event_user,
                is_l_user=(event_user_lower in L_USER_IDS),
                l_user_ids=list(L_USER_IDS),
            )
            return JSONResponse(content={"status": "ok"})

        # Handle app_mention events
        if event_type == "app_mention":
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text", "")
            files = event.get("files", [])  # File attachments
            thread_ts = event.get("thread_ts") or event.get("ts", "")
            team_id = data.get("team_id", "")

            # === NEW: L-AgentTask routing when legacy flag is False ===
            if not L9_ENABLE_LEGACY_SLACK_ROUTER and channel and user and text.strip():
                try:
                    from services.slack_client import slack_post

                    # Use thread_ts as thread_uuid for conversation grouping
                    thread_uuid = (
                        f"slack-{team_id}-{channel}-{thread_ts}"
                        if thread_ts
                        else f"slack-{team_id}-{channel}"
                    )

                    # Route through L-CTO agent via AgentExecutorService
                    reply, status = await handle_slack_with_l_agent(
                        app=request.app,
                        text=text,
                        thread_uuid=thread_uuid,
                        team_id=team_id,
                        channel_id=channel,
                        user_id=user,
                    )

                    # Post reply to Slack
                    if status in ("completed", "duplicate"):
                        slack_post(
                            channel, reply, thread_ts=thread_ts if thread_ts else None
                        )
                    else:
                        slack_post(
                            channel,
                            f"⚠️ {reply}",
                            thread_ts=thread_ts if thread_ts else None,
                        )

                    logger.info(
                        f"[SLACK] L-AgentTask app_mention: status={status}, user={user}, channel={channel}"
                    )
                    return JSONResponse(content={"status": "ok"})

                except Exception as e:
                    logger.error(
                        f"[SLACK] L-AgentTask app_mention failed: {e}", exc_info=True
                    )
                    # Fall through to legacy handling

            if channel and user:
                # Process file attachments if present
                file_artifacts = []
                if files:
                    try:
                        from services.slack_files import process_file_attachments

                        file_artifacts = process_file_attachments(files)
                        logger.info(
                            f"[SLACK] Processed {len(file_artifacts)} file attachments from app_mention"
                        )
                    except Exception as e:
                        logger.error(
                            f"[SLACK] Failed to process file attachments: {e}",
                            exc_info=True,
                        )
                        # Continue processing message even if files fail

                # Check for !mac command
                if text.strip().startswith("!mac"):
                    command = text.replace("!mac", "", 1).strip()
                    if command:
                        from services.mac_tasks import enqueue_mac_task
                        from services.slack_client import slack_post

                        # Enhance command context with file artifacts if present
                        enhanced_command = command
                        if file_artifacts:
                            # Append file artifact metadata to command context
                            file_context = "\n\n[File attachments available:"
                            for artifact in file_artifacts:
                                file_context += f"\n- {artifact['name']} ({artifact['type']}) at {artifact['path']}"
                            file_context += "]"
                            enhanced_command = command + file_context
                            logger.info(
                                f"[SLACK] Enhanced command with {len(file_artifacts)} file attachments"
                            )

                        task_id = enqueue_mac_task(
                            source="slack",
                            channel=channel,
                            user=user,
                            command=enhanced_command,
                            attachments=file_artifacts if file_artifacts else None,
                        )

                        file_msg = (
                            f" ({len(file_artifacts)} file{'s' if len(file_artifacts) != 1 else ''})"
                            if file_artifacts
                            else ""
                        )
                        slack_post(
                            channel,
                            f"📨 Mac task queued (id={task_id}){file_msg}. I'll post the result here when it's done.",
                        )
                        logger.info(
                            f"[SLACK] Enqueued Mac task {task_id} from {user} in {channel}: {command}"
                        )
                    else:
                        from services.slack_client import slack_post

                        slack_post(
                            channel,
                            "❌ Please provide a command after `!mac` (e.g., `!mac echo hello`)",
                        )
                    return JSONResponse(content={"status": "ok"})

                # Check for email-related commands in app_mention
                text_lower = text.strip().lower()
                is_email_command = any(
                    text_lower.startswith(kw.lower()) for kw in EMAIL_KEYWORDS
                ) or any(kw.lower() in text_lower for kw in EMAIL_PHRASE_KEYWORDS)

                # NEW: Route app_mention through task planner if files present or email command
                if file_artifacts or is_email_command:
                    try:
                        from orchestration.slack_task_router import route_slack_message
                        from services.mac_tasks import enqueue_task
                        from services.slack_client import slack_post

                        # If email command detected, ensure proper routing
                        routing_text = text
                        if is_email_command and not text_lower.startswith("email:"):
                            routing_text = f"email: {text}"

                        # Route message + artifacts to task structure
                        task_dict = route_slack_message(
                            routing_text, file_artifacts, user
                        )

                        # Store channel in metadata for result posting
                        if "metadata" not in task_dict:
                            task_dict["metadata"] = {}
                        task_dict["metadata"]["channel"] = channel

                        # Enqueue task
                        task_id = enqueue_task(task_dict)

                        # Respond in Slack
                        task_type = task_dict.get("type", "task")
                        if task_type == "email_task":
                            slack_post(
                                channel,
                                f"📧 Email task recognized and queued (ID: {task_id}).",
                            )
                        else:
                            slack_post(
                                channel,
                                f"Task accepted and queued (ID: {task_id}). I'll let you know when it's done.",
                            )
                        logger.info(
                            f"[SLACK] Routed app_mention to {task_type} {task_id} from {user} in {channel}"
                        )
                        return JSONResponse(content={"status": "ok"})
                    except Exception as e:
                        logger.error(
                            f"[SLACK] Failed to route app_mention: {e}", exc_info=True
                        )
                        # Fall through to default response

                from services.slack_client import slack_post

                file_msg = (
                    f" I received {len(file_artifacts)} file attachment{'s' if len(file_artifacts) != 1 else ''}."
                    if file_artifacts
                    else ""
                )
                slack_post(
                    channel, f"👋 Hey <@{user}> — L9 is online and connected.{file_msg}"
                )
                logger.info(
                    f"[SLACK] Responded to app_mention from {user} in {channel}"
                )
                return JSONResponse(content={"status": "ok"})

        # Handle messages containing "l9" (case-insensitive) or !mac commands
        if event_type == "message":
            channel = event.get("channel")
            user = event.get("user")
            text_original = event.get("text", "")
            text = text_original.lower()
            files = event.get("files", [])  # File attachments
            channel_type = event.get("channel_type", "")  # "im" for DMs
            thread_ts = event.get("thread_ts") or event.get("ts", "")
            team_id = data.get("team_id", "")

            # Detect if this is a DM (direct message)
            is_dm = channel_type == "im" or (channel and channel.startswith("D"))

            # === NEW: L-AgentTask routing when legacy flag is False ===
            # Route DMs and messages containing "l9" through L-CTO agent
            should_use_l_agent = is_dm or "l9" in text

            if (
                not L9_ENABLE_LEGACY_SLACK_ROUTER
                and channel
                and user
                and text_original.strip()
                and should_use_l_agent
            ):
                # Skip !mac commands - those still go through legacy path
                if not text.strip().startswith("!mac"):
                    try:
                        from services.slack_client import slack_post

                        # Use thread_ts as thread_uuid for conversation grouping
                        thread_uuid = (
                            f"slack-{team_id}-{channel}-{thread_ts}"
                            if thread_ts
                            else f"slack-{team_id}-{channel}"
                        )

                        # Route through L-CTO agent via AgentExecutorService
                        reply, status = await handle_slack_with_l_agent(
                            app=request.app,
                            text=text_original,
                            thread_uuid=thread_uuid,
                            team_id=team_id,
                            channel_id=channel,
                            user_id=user,
                        )

                        # Post reply to Slack
                        if status in ("completed", "duplicate"):
                            slack_post(
                                channel,
                                reply,
                                thread_ts=thread_ts if thread_ts else None,
                            )
                        else:
                            slack_post(
                                channel,
                                f"⚠️ {reply}",
                                thread_ts=thread_ts if thread_ts else None,
                            )

                        logger.info(
                            f"[SLACK] L-AgentTask message: status={status}, user={user}, channel={channel}"
                        )
                        return JSONResponse(content={"status": "ok"})

                    except Exception as e:
                        logger.error(
                            f"[SLACK] L-AgentTask message failed: {e}", exc_info=True
                        )
                        # Fall through to legacy handling

            # Process file attachments if present
            file_artifacts = []
            if files:
                try:
                    from services.slack_files import process_file_attachments

                    file_artifacts = process_file_attachments(files)
                    logger.info(
                        f"[SLACK] Processed {len(file_artifacts)} file attachments from {user} in {channel}"
                    )
                except Exception as e:
                    logger.error(
                        f"[SLACK] Failed to process file attachments: {e}",
                        exc_info=True,
                    )
                    # Continue processing message even if files fail

            # Check for email-related commands (uses module-level constants)
            text_lower = text.strip().lower()
            is_email_command = any(
                text_lower.startswith(kw.lower()) for kw in EMAIL_KEYWORDS
            ) or any(kw.lower() in text_lower for kw in EMAIL_PHRASE_KEYWORDS)

            # Handle DMs: Respond to ALL messages in direct messages
            # In channels: Only respond when mentioned or "l9" in text
            should_respond = is_dm or file_artifacts or "l9" in text or is_email_command

            # For simple DMs without commands/files, give a quick conversational response
            # Only route to task planner for actionable requests
            is_simple_dm = (
                is_dm
                and not file_artifacts
                and not is_email_command
                and not text.strip().startswith("!mac")
            )

            if is_simple_dm and user and channel:
                from services.slack_client import slack_post

                # NOTE: Do NOT echo the user's message back - this caused infinite loop (Dec 18, 2025)
                # When L echoes "Hey! You said: X", Slack sends it back as event, L echoes again, etc.
                slack_post(
                    channel,
                    "👋 Hey! L9 here. How can I help?\n\nTry:\n• `!mac <command>` - Run a Mac automation\n• `email: <request>` - Email operations\n• Attach a file for processing",
                    thread_ts=thread_ts if thread_ts else None,
                )
                logger.info("slack_simple_dm_response", user=user, channel=channel)
                return JSONResponse(content={"status": "ok"})

            # NEW: Route Slack message through task planner (when files present or message directed at L9 or email command)
            if user and channel and text_original.strip() and should_respond:
                try:
                    from orchestration.slack_task_router import route_slack_message
                    from services.mac_tasks import enqueue_task
                    from services.slack_client import slack_post

                    # If email command detected, prepend "email:" to ensure routing
                    routing_text = text_original
                    if is_email_command and not text_original.lower().startswith(
                        "email:"
                    ):
                        routing_text = f"email: {text_original}"

                    # Route message + artifacts to task structure
                    task_dict = route_slack_message(routing_text, file_artifacts, user)

                    # Store channel in metadata for result posting
                    if "metadata" not in task_dict:
                        task_dict["metadata"] = {}
                    task_dict["metadata"]["channel"] = channel

                    # Enqueue task
                    task_id = enqueue_task(task_dict)

                    # Respond in Slack
                    task_type = task_dict.get("type", "task")
                    response_msg = f"Task accepted and queued (ID: {task_id}). I'll let you know when it's done."
                    if task_type == "email_task":
                        response_msg = (
                            f"📧 Email task recognized and queued (ID: {task_id})."
                        )

                    slack_post(channel, response_msg)
                    logger.info(
                        f"[SLACK] Routed message to {task_type} {task_id} from {user} in {channel}"
                    )
                    return JSONResponse(content={"status": "ok"})
                except Exception as e:
                    logger.error(f"[SLACK] Failed to route message: {e}", exc_info=True)
                    # Fall through to existing handlers

            # Check for !mac command
            if user and channel and text.strip().startswith("!mac"):
                command = text_original.replace("!mac", "", 1).strip()
                if command:
                    from services.mac_tasks import enqueue_mac_task
                    from services.slack_client import slack_post

                    # Enhance command context with file artifacts if present
                    enhanced_command = command
                    if file_artifacts:
                        # Append file artifact metadata to command context
                        file_context = "\n\n[File attachments available:"
                        for artifact in file_artifacts:
                            file_context += f"\n- {artifact['name']} ({artifact['type']}) at {artifact['path']}"
                        file_context += "]"
                        enhanced_command = command + file_context
                        logger.info(
                            f"[SLACK] Enhanced command with {len(file_artifacts)} file attachments"
                        )

                    task_id = enqueue_mac_task(
                        source="slack",
                        channel=channel,
                        user=user,
                        command=enhanced_command,
                        attachments=file_artifacts if file_artifacts else None,
                    )

                    file_msg = (
                        f" ({len(file_artifacts)} file{'s' if len(file_artifacts) != 1 else ''})"
                        if file_artifacts
                        else ""
                    )
                    slack_post(
                        channel,
                        f"📨 Mac task queued (id={task_id}){file_msg}. I'll post the result here when it's done.",
                    )
                    logger.info(
                        f"[SLACK] Enqueued Mac task {task_id} from {user} in {channel}: {command}"
                    )
                else:
                    from services.slack_client import slack_post

                    slack_post(
                        channel,
                        "❌ Please provide a command after `!mac` (e.g., `!mac echo hello`)",
                    )
                return JSONResponse(content={"status": "ok"})

            # Check if message contains "l9" in a channel (not DM - DMs handled above)
            if user and channel and "l9" in text and not is_dm:
                from services.slack_client import slack_post

                file_msg = (
                    f" I received {len(file_artifacts)} file attachment{'s' if len(file_artifacts) != 1 else ''}."
                    if file_artifacts
                    else ""
                )
                slack_post(
                    channel, f"👋 Hey <@{user}> — L9 is online and connected.{file_msg}"
                )
                logger.info(
                    f"[SLACK] Responded to message containing 'l9' from {user} in {channel}"
                )
                return JSONResponse(content={"status": "ok"})

        # Acknowledge other events
        logger.debug(f"[SLACK] Received event type: {event_type}")
        return JSONResponse(content={"status": "ok"})

    # Unknown event type
    logger.warning(f"[SLACK] Unknown event type: {data.get('type')}")
    return JSONResponse(content={"status": "ok"})
