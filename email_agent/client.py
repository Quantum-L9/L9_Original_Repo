"""
L9 Email Agent Client (Compatibility Layer)
============================================

This module provides execute_email_task() function for Mac Agent integration.
Uses gmail_client.py for actual Gmail operations.
Supports multi-account mode via account parameter.

Version: 2.0.0
"""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)

try:
    from email_agent.gmail_client import GmailClient

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.warning("Gmail client not available")


def execute_email_task(
    task: Dict[str, Any], account: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute an email task from Mac Agent runner.

    Args:
        task: Task dictionary with type="email_task" and steps
        account: Gmail account name ("igor" or "l"). If None, uses legacy mode.

    Returns:
        Result dictionary with status, logs, screenshots, data
    """
    if not GMAIL_AVAILABLE:
        return {
            "status": "error",
            "logs": [
                {
                    "step": 0,
                    "action": "email_init",
                    "status": "error",
                    "details": "Gmail API not available",
                }
            ],
            "screenshots": [],
            "data": {"error": "Gmail API libraries not installed"},
        }

    # Get account from task if not passed directly
    if account is None:
        account = task.get("account")

    try:
        client = GmailClient(account=account)
        logs = []
        steps = task.get("steps", [])

        for i, step in enumerate(steps, 1):
            action = step.get("action")

            if action == "list_messages":
                query = step.get("query", "")
                max_results = step.get("max_results", 10)
                messages = client.list_messages(query, max_results)
                logs.append(
                    {
                        "step": i,
                        "action": action,
                        "status": "success",
                        "details": f"Found {len(messages)} messages",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                # Store messages in data
                if "data" not in locals():
                    data = {}
                data["messages"] = messages

            elif action == "get_message":
                message_id = step.get("message_id")
                if message_id:
                    message = client.get_message(message_id)
                    if message:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Retrieved message: {message.get('subject', 'No subject')}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data["message"] = message
                    else:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": f"Message {message_id} not found",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

            elif action == "draft_email":
                to = step.get("to")
                subject = step.get("subject")
                body = step.get("body")
                attachments = step.get("attachments", [])
                if all([to, subject, body]):
                    draft_id = client.draft_email(
                        to, subject, body, attachments=attachments
                    )
                    if draft_id:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Draft created: {draft_id}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data["draft_id"] = draft_id
                    else:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": "Failed to create draft",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

            elif action == "send_email":
                draft_id = step.get("draft_id")
                to = step.get("to")
                subject = step.get("subject")
                body = step.get("body")
                attachments = step.get("attachments", [])

                if draft_id:
                    # Send existing draft
                    try:
                        draft = (
                            client.service.users()
                            .drafts()
                            .get(userId="me", id=draft_id)
                            .execute()
                        )

                        sent_message = (
                            client.service.users()
                            .drafts()
                            .send(userId="me", body={"id": draft_id})
                            .execute()
                        )

                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Email sent: {sent_message.get('id')}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data["message_id"] = sent_message.get("id")
                        data["thread_id"] = sent_message.get("threadId")
                    except Exception as e:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": f"Failed to send draft: {str(e)}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                elif all([to, subject, body]):
                    result = client.send_email(
                        to, subject, body, attachments=attachments
                    )
                    if result:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Email sent: {result.get('message_id')}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data.update(result)
                    else:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": "Failed to send email",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                else:
                    logs.append(
                        {
                            "step": i,
                            "action": action,
                            "status": "error",
                            "details": "Missing required fields (to, subject, body) or draft_id",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            elif action == "reply_to_email":
                message_id = step.get("message_id")
                body = step.get("body")
                if message_id and body:
                    result = client.reply_to_email(message_id, body)
                    if result:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Reply sent: {result.get('message_id')}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data.update(result)
                    else:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": "Failed to send reply",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                else:
                    logs.append(
                        {
                            "step": i,
                            "action": action,
                            "status": "error",
                            "details": "Missing message_id or body",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            elif action == "forward_email":
                message_id = step.get("message_id")
                to = step.get("to")
                body = step.get("body", "")
                if message_id and to:
                    result = client.forward_email(message_id, to, body)
                    if result:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "success",
                                "details": f"Email forwarded: {result.get('message_id')}",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        if "data" not in locals():
                            data = {}
                        data.update(result)
                    else:
                        logs.append(
                            {
                                "step": i,
                                "action": action,
                                "status": "error",
                                "details": "Failed to forward email",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                else:
                    logs.append(
                        {
                            "step": i,
                            "action": action,
                            "status": "error",
                            "details": "Missing message_id or to",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        # Determine overall status
        status = (
            "success"
            if all(log.get("status") == "success" for log in logs)
            else "error"
        )
        if not logs:
            status = "error"

        return {
            "status": status,
            "logs": logs,
            "screenshots": [],
            "started_at": logs[0]["timestamp"]
            if logs
            else datetime.utcnow().isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
            "data": data if "data" in locals() else {"task_type": "email_task"},
        }

    except Exception as e:
        logger.error(f"Email task execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "logs": [
                {
                    "step": 0,
                    "action": "email_task",
                    "status": "error",
                    "details": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
            "screenshots": [],
            "data": {"error": str(e)},
        }
