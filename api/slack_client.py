"""
Slack API Client: Async wrapper for posting messages back to Slack.

This module provides a thin async wrapper around the Slack Web API
for posting messages (chat.postMessage) with full thread support.

It is NOT a full Slack SDK; it only implements the subset needed for
the L9 Slack adapter:
  - chat.postMessage (reply in thread)
  - Basic error handling
  - No connection pooling (relies on httpx at app level)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Client",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "error_handling",
    "module_name": "slack_client",
    "type": "exception",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Slack API"],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "api.server_memory",
            "api.webhook_mac_agent",
            "mac_agent.runner",
            "memory.slack_ingest",
            "orchestrators.agent_execution.orchestrator",
            "services.slack_files",
            "tests.api.test_slack_adapter",
            "tests.test_slack_adapter",
        ],
    },
}
# ============================================================================

import os
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

SLACK_API_BASE = "https://slack.com/api"
SLACK_CHAT_POST_MESSAGE_ENDPOINT = f"{SLACK_API_BASE}/chat.postMessage"
SLACK_FILES_UPLOAD_ENDPOINT = f"{SLACK_API_BASE}/files.uploadV2"
SLACK_FILES_INFO_ENDPOINT = f"{SLACK_API_BASE}/files.info"


class SlackClientError(Exception):
    """Raised when Slack API call fails."""


class SlackAPIClient:
    """
    Async Slack API client for posting messages.

    Requires shared httpx client (not owned by this class).

    Usage:
        client = SlackAPIClient(bot_token="xoxb-...", http_client=shared_httpx_client)
        await client.post_message(
            channel="C123",
            text="Hello",
            thread_ts="1234567890.123456"
        )
    """

    def __init__(self, bot_token: str, http_client: httpx.AsyncClient):
        """
        Args:
            bot_token: Slack bot token (from Settings > Install App)
            http_client: Shared httpx.AsyncClient (managed by app lifespan)
        """
        if not bot_token or not bot_token.strip():
            raise ValueError("SLACK_BOT_TOKEN is required and cannot be empty")
        if not http_client:
            raise ValueError("http_client (httpx.AsyncClient) is required")

        self.bot_token = bot_token
        self.http_client = http_client

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reply_broadcast: bool = False,
    ) -> Dict[str, Any]:
        """
        Post a message to Slack.

        Args:
            channel: Channel ID (C...) or user ID (U...)
            text: Plain text message content
            thread_ts: Optional; if provided, post as reply in thread
            blocks: Optional; rich formatting blocks (Block Kit)
            metadata: Optional; message metadata (for searchability)
            reply_broadcast: If True and thread_ts provided, also post to channel

        Returns:
            Slack API response dict:
              {
                "ok": true,
                "channel": "C...",
                "ts": "1234567890.123456",
                "message": {...}
              }

        Raises:
            SlackClientError: If API call fails

        Note: httpx.AsyncClient.post() returns a Response directly (not an async context manager).
        """
        payload = {
            "channel": channel,
            "text": text,
        }

        if blocks:
            payload["blocks"] = blocks

        if thread_ts:
            payload["thread_ts"] = thread_ts
            payload["reply_broadcast"] = reply_broadcast

        if metadata:
            payload["metadata"] = metadata

        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

        try:
            # httpx.AsyncClient.post() returns Response directly (not async context manager)
            resp = await self.http_client.post(
                SLACK_CHAT_POST_MESSAGE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()

            response_data = resp.json()

            if not response_data.get("ok"):
                error = response_data.get("error", "unknown error")
                raise SlackClientError(f"Slack API error: {error}")

            logger.info(
                "slack_message_posted",
                channel=channel,
                ts=response_data.get("ts"),
                thread_ts=thread_ts,
            )

            return response_data

        except httpx.TimeoutException:
            raise SlackClientError("Slack API request timed out (10s)")
        except httpx.HTTPStatusError as e:
            raise SlackClientError(
                f"Slack API HTTP error {e.response.status_code}: {e}"
            )
        except Exception as e:
            raise SlackClientError(f"HTTP error posting to Slack: {e}")

    async def upload_file(
        self,
        channel: str,
        file_path: str,
        filename: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack using files.uploadV2 API.

        Args:
            channel: Channel ID (C...) or user ID (U...)
            file_path: Path to file to upload
            filename: Optional filename (defaults to basename of file_path)
            title: Optional title for the file

        Returns:
            Slack API response dict with file information

        Raises:
            SlackClientError: If API call fails
            FileNotFoundError: If file_path doesn't exist
        """
        import os

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not filename:
            filename = os.path.basename(file_path)

        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Prepare multipart form data
        files = {
            "file": (filename, file_content),
        }
        data = {
            "channel_id": channel,
        }
        if title:
            data["title"] = title

        headers = {
            "Authorization": f"Bearer {self.bot_token}",
        }

        try:
            resp = await self.http_client.post(
                SLACK_FILES_UPLOAD_ENDPOINT,
                data=data,
                files=files,
                headers=headers,
                timeout=30.0,  # File uploads may take longer
            )
            resp.raise_for_status()

            response_data = resp.json()

            if not response_data.get("ok"):
                error = response_data.get("error", "unknown error")
                raise SlackClientError(f"Slack API error: {error}")

            logger.info(
                "slack_file_uploaded",
                channel=channel,
                filename=filename,
                file_id=response_data.get("file", {}).get("id"),
            )

            return response_data

        except httpx.TimeoutException:
            raise SlackClientError("Slack API request timed out (30s)")
        except httpx.HTTPStatusError as e:
            raise SlackClientError(
                f"Slack API HTTP error {e.response.status_code}: {e}"
            )
        except Exception as e:
            raise SlackClientError(f"HTTP error uploading file to Slack: {e}")

    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata from Slack using files.info API.

        Args:
            file_id: Slack file ID

        Returns:
            File info dictionary from Slack API:
              {
                "ok": true,
                "file": {
                  "id": "...",
                  "name": "...",
                  "mimetype": "...",
                  "url_private": "...",
                  ...
                }
              }

        Raises:
            SlackClientError: If API call fails
        """
        params = {"file": file_id}

        headers = {
            "Authorization": f"Bearer {self.bot_token}",
        }

        try:
            resp = await self.http_client.get(
                SLACK_FILES_INFO_ENDPOINT,
                params=params,
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()

            response_data = resp.json()

            if not response_data.get("ok"):
                error = response_data.get("error", "unknown error")
                raise SlackClientError(f"Slack API error: {error}")

            logger.info(
                "slack_file_info_retrieved",
                file_id=file_id,
                filename=response_data.get("file", {}).get("name"),
            )

            return response_data

        except httpx.TimeoutException:
            raise SlackClientError("Slack API request timed out (10s)")
        except httpx.HTTPStatusError as e:
            raise SlackClientError(
                f"Slack API HTTP error {e.response.status_code}: {e}"
            )
        except Exception as e:
            raise SlackClientError(f"HTTP error getting file info from Slack: {e}")


async def post_result_async(
    user: str,
    task: dict,
    result: dict,
    slack_client: Optional[SlackAPIClient] = None,
) -> Optional[Dict[str, Any]]:
    """
    Post execution summary + screenshots back to Slack (async version).

    Args:
        user: Slack user ID (for DM) or channel ID
        task: Task dictionary with metadata
        result: Execution result dictionary with status, logs, screenshots
        slack_client: Optional SlackAPIClient instance. If None, creates one from env.

    Returns:
        Slack API response dict or None if posting failed/disabled

    Note: This is the async replacement for services.slack_client.post_result()
    """
    # Create client if not provided
    if slack_client is None:
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        slack_app_enabled = os.getenv("SLACK_APP_ENABLED", "true").lower() == "true"

        if not slack_app_enabled or not slack_bot_token:
            logger.debug("[SLACK] No client; skipping result post")
            return None

        http_client = httpx.AsyncClient()
        slack_client = SlackAPIClient(
            bot_token=slack_bot_token, http_client=http_client
        )

    try:
        task_id = task.get(
            "task_id", task.get("metadata", {}).get("task_id", "unknown")
        )
        status = result.get("status", "unknown")
        logs = result.get("logs", [])
        screenshots = result.get("screenshots", [])
        # Backward compatibility: check screenshot_path if screenshots not available
        if not screenshots and result.get("screenshot_path"):
            screenshots = [result.get("screenshot_path")]

        steps = task.get("steps", [])
        steps_count = len(steps)

        # Count successes and failures from structured logs
        successes = sum(
            1
            for log in logs
            if isinstance(log, dict) and log.get("status") == "success"
        )
        failures = sum(
            1 for log in logs if isinstance(log, dict) and log.get("status") == "error"
        )

        # Build formatted message
        message_parts = []

        # Add warning emoji for errors
        if status == "error":
            message_parts.append("⚠️ Automation failed")

        message_parts.extend(
            [
                f"Task <{task_id}> completed.",
                f"Status: {status}",
                "",
                "Summary:",
                f"• Steps: {steps_count}",
                f"• Successes: {successes}",
                f"• Failures: {failures}",
            ]
        )

        # Add first 3 log details
        if logs:
            message_parts.append("")
            message_parts.append("Details:")
            log_details = []
            for log in logs[:3]:
                if isinstance(log, dict):
                    action = log.get("action", "unknown")
                    log_status = log.get("status", "unknown")
                    details = log.get("details", "")
                    log_details.append(
                        f"• {action}: {log_status}"
                        + (f" - {details[:50]}" if details else "")
                    )
                else:
                    log_details.append(f"• {str(log)[:100]}")
            message_parts.extend(log_details)

        # Add task-specific previews
        task_type = task.get("type", "mac_task")

        # Email task: enhanced formatting
        if task_type == "email_task":
            message_parts.append("")
            message_parts.append("📧 *Email Result:*")

            # Extract operation from steps
            steps = task.get("steps", [])
            operation = None
            for step in steps:
                action = step.get("action")
                if action in [
                    "list_messages",
                    "get_message",
                    "draft_email",
                    "send_email",
                    "reply_to_email",
                ]:
                    operation = action
                    break

            if operation:
                operation_display = {
                    "list_messages": "Search",
                    "get_message": "Read",
                    "draft_email": "Draft",
                    "send_email": "Send",
                    "reply_to_email": "Reply",
                }.get(operation, operation)
                message_parts.append(f"Operation: {operation_display}")

            # Show email details from result data
            result_data = result.get("data", {})

            # Messages found
            if "messages" in result_data:
                messages = result_data["messages"]
                message_parts.append(f"Found {len(messages)} message(s):")
                for msg in messages[:3]:  # Show first 3
                    message_parts.append(
                        f"  • {msg.get('subject', 'No subject')} from {msg.get('from', 'Unknown')}"
                    )
                if len(messages) > 3:
                    message_parts.append(f"  ... and {len(messages) - 3} more")

            # Message retrieved
            if "message" in result_data:
                msg = result_data["message"]
                message_parts.append("")
                message_parts.append(f"*Subject:* {msg.get('subject', 'No subject')}")
                message_parts.append(f"*From:* {msg.get('from', 'Unknown')}")
                message_parts.append(f"*To:* {msg.get('to', 'Unknown')}")
                if msg.get("attachments"):
                    message_parts.append(
                        f"*Attachments:* {len(msg['attachments'])} file(s)"
                    )
                body_preview = msg.get("body_plain", msg.get("body_html", ""))[:200]
                if body_preview:
                    message_parts.append(f"*Preview:* {body_preview}...")

            # Draft created
            if "draft_id" in result_data:
                message_parts.append("")
                message_parts.append(f"✅ Draft created: {result_data['draft_id']}")
                # Show draft details from steps
                for step in steps:
                    if step.get("action") == "draft_email":
                        message_parts.append(f"To: {step.get('to', 'N/A')}")
                        message_parts.append(f"Subject: {step.get('subject', 'N/A')}")
                        body_preview = step.get("body", "")[:150]
                        if body_preview:
                            message_parts.append(f"Body: {body_preview}...")
                        break

            # Email sent
            if "message_id" in result_data:
                message_parts.append("")
                message_parts.append("✅ Email sent successfully")
                message_parts.append(f"Message ID: {result_data['message_id']}")
                if result_data.get("thread_id"):
                    message_parts.append(f"Thread ID: {result_data['thread_id']}")

            # Reply sent
            if operation == "reply_to_email" and result.get("status") == "success":
                message_parts.append("")
                message_parts.append("✅ Reply sent successfully")

            # Fallback: show step details if no data
            if not result_data and steps:
                for step in steps:
                    if step.get("action") == "draft_email":
                        message_parts.append("")
                        message_parts.append("Email Draft:")
                        message_parts.append(f"To: {step.get('to', 'N/A')}")
                        message_parts.append(f"Subject: {step.get('subject', 'N/A')}")
                        message_parts.append(f"Body: {step.get('body', '')[:100]}...")
                        break

        # OCR/PDF preview from artifacts
        artifacts = task.get("artifacts", [])
        for artifact in artifacts[:2]:  # Show first 2 artifacts
            artifact_name = artifact.get("name", "unknown")

            if artifact.get("ocr"):
                ocr_data = artifact["ocr"]
                ocr_text = ocr_data.get("text", "")
                if ocr_text:
                    preview = ocr_text[:100].replace("\n", " ")
                    message_parts.append("")
                    message_parts.append(f"OCR ({artifact_name}): {preview}...")

            if artifact.get("pdf"):
                pdf_data = artifact["pdf"]
                summary = pdf_data.get("summary", "")
                if summary:
                    message_parts.append("")
                    message_parts.append(f"PDF ({artifact_name}): {summary}")
                elif pdf_data.get("fields"):
                    fields_preview = ", ".join(list(pdf_data["fields"].keys())[:3])
                    message_parts.append("")
                    message_parts.append(
                        f"PDF Fields ({artifact_name}): {fields_preview}..."
                    )

            if artifact.get("transcription"):
                trans_data = artifact["transcription"]
                trans_text = trans_data.get("text", "")
                if trans_text:
                    preview = trans_text[:100].replace("\n", " ")
                    message_parts.append("")
                    message_parts.append(
                        f"Transcription ({artifact_name}): {preview}..."
                    )

        message = "\n".join(message_parts)

        # Upload screenshots
        uploaded_files = []
        for screenshot_path in screenshots:
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    file_response = await slack_client.upload_file(
                        channel=user,
                        file_path=screenshot_path,
                        filename=os.path.basename(screenshot_path),
                        title=f"Task {task_id} screenshot",
                    )
                    uploaded_files.append(file_response)
                    logger.info(
                        f"[SLACK] Uploaded screenshot: {os.path.basename(screenshot_path)}"
                    )
                except Exception as e:
                    logger.error(
                        f"[SLACK] Failed to upload screenshot {screenshot_path}: {e}"
                    )

        # If no screenshots were uploaded but we have screenshot_path (backward compat)
        if (
            not uploaded_files
            and result.get("screenshot_path")
            and os.path.exists(result.get("screenshot_path"))
        ):
            try:
                file_response = await slack_client.upload_file(
                    channel=user,
                    file_path=result["screenshot_path"],
                    filename=os.path.basename(result["screenshot_path"]),
                    title=f"Task {task_id} screenshot",
                )
                uploaded_files.append(file_response)
            except Exception as e:
                logger.error(f"[SLACK] Failed to upload screenshot: {e}")

        # Post message
        response = await slack_client.post_message(channel=user, text=message)
        logger.info(
            f"[SLACK] Posted result for task {task_id} to {user} ({len(uploaded_files)} screenshots)"
        )
        return response

    except Exception as e:
        logger.error(f"[SLACK] Error posting result: {e}", exc_info=True)
        # Don't raise - fail silently (matching legacy behavior)
        return None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "auth",
        "client",
        "debugging",
        "error-handling",
        "exception",
        "http-client",
        "logging",
        "messaging",
    ],
    "keywords": [
        "async",
        "chat",
        "client",
        "full",
        "messages",
        "module",
        "post",
        "posting",
    ],
    "business_value": "This module provides a thin async wrapper around the Slack Web API for posting messages (chat.postMessage) with full thread support. It is NOT a full Slack SDK; it only implements the subset needed fo",
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
