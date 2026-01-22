"""
Email Inbox Triage and Daily Digest
===================================

Functions for summarizing inbox, extracting priorities, and generating daily digests.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Triage",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "triage",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Gmail API", "OpenAI API"],
        "memory_layers": [],
        "imported_by": ["email_agent.__init__", "tests.email_agent.test_email_triage"],
    },
}
# ============================================================================

from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)

try:
    from openai import OpenAI

    from email_agent.gmail_client import GmailClient

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.warning("Gmail client or OpenAI not available")


def summarize_inbox(limit: int = 20) -> Dict[str, Any]:
    """
    Summarize recent inbox messages using LLM.

    Args:
        limit: Maximum number of messages to analyze

    Returns:
        Dictionary with:
        - urgent_items: List of urgent messages
        - replies_needed: List of messages requiring replies
        - attachments_detected: Count and list of messages with attachments
        - deadlines: Extracted deadlines/action items
        - summary: Overall inbox summary
    """
    if not GMAIL_AVAILABLE:
        return {
            "error": "Gmail client not available",
            "urgent_items": [],
            "replies_needed": [],
            "attachments_detected": [],
            "deadlines": [],
            "summary": "",
        }

    try:
        client = GmailClient()

        # Fetch recent messages
        messages = client.list_messages(query="is:unread OR is:important", limit=limit)

        if not messages:
            return {
                "urgent_items": [],
                "replies_needed": [],
                "attachments_detected": [],
                "deadlines": [],
                "summary": "No unread or important messages",
            }

        # Get full content for a subset
        message_details = []
        for msg in messages[:10]:  # Analyze first 10 in detail
            try:
                full_msg = client.get_message(msg["id"])
                if full_msg:
                    message_details.append(
                        {
                            "id": msg["id"],
                            "from": msg.get("from", ""),
                            "subject": msg.get("subject", ""),
                            "snippet": msg.get("snippet", ""),
                            "body": full_msg.get("body_plain", "")[
                                :500
                            ],  # First 500 chars
                            "attachments": len(full_msg.get("attachments", [])),
                            "date": msg.get("date", ""),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get full message {msg['id']}: {e}")

        # Use LLM to analyze and categorize
        try:
            api_key = __import__("os").getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, skipping LLM analysis")
                return _simple_summary(message_details)

            openai_client = OpenAI(api_key=api_key)

            # Build prompt
            messages_text = "\n\n".join(
                [
                    f"From: {m['from']}\nSubject: {m['subject']}\n{m['body']}"
                    for m in message_details
                ]
            )

            prompt = f"""Analyze these email messages and extract:
1. Urgent items (time-sensitive, requires immediate attention)
2. Replies needed (messages that likely need a response)
3. Attachments detected (messages with file attachments)
4. Deadlines/action items (dates, deadlines, action items mentioned)

Messages:
{messages_text}

Return JSON format:
{{
  "urgent_items": [{{"id": "...", "subject": "...", "reason": "..."}}],
  "replies_needed": [{{"id": "...", "subject": "...", "from": "..."}}],
  "attachments_detected": [{{"id": "...", "subject": "...", "count": N}}],
  "deadlines": [{{"id": "...", "subject": "...", "deadline": "...", "description": "..."}}],
  "summary": "Brief overall summary"
}}"""

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an email triage assistant. Analyze emails and extract priorities.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            analysis = json.loads(response.choices[0].message.content)

            # Add full message IDs from our data
            id_map = {m["subject"]: m["id"] for m in message_details}
            for item in analysis.get("urgent_items", []):
                if "id" not in item and item.get("subject") in id_map:
                    item["id"] = id_map[item["subject"]]
            for item in analysis.get("replies_needed", []):
                if "id" not in item and item.get("subject") in id_map:
                    item["id"] = id_map[item["subject"]]
            for item in analysis.get("attachments_detected", []):
                if "id" not in item and item.get("subject") in id_map:
                    item["id"] = id_map[item["subject"]]
            for item in analysis.get("deadlines", []):
                if "id" not in item and item.get("subject") in id_map:
                    item["id"] = id_map[item["subject"]]

            return analysis

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            return _simple_summary(message_details)

    except Exception as e:
        logger.error(f"Inbox triage failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "urgent_items": [],
            "replies_needed": [],
            "attachments_detected": [],
            "deadlines": [],
            "summary": "",
        }


def _simple_summary(message_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback simple summary without LLM."""
    urgent = []
    replies_needed = []
    attachments = []

    for msg in message_details:
        subject_lower = msg.get("subject", "").lower()
        body_lower = msg.get("body", "").lower()

        # Check for urgency keywords
        if any(
            kw in subject_lower or kw in body_lower
            for kw in ["urgent", "asap", "immediate", "critical"]
        ):
            urgent.append(
                {
                    "id": msg["id"],
                    "subject": msg["subject"],
                    "reason": "Contains urgency keywords",
                }
            )

        # Check for reply indicators
        if any(
            kw in subject_lower or kw in body_lower
            for kw in ["?", "question", "please", "request"]
        ):
            replies_needed.append(
                {"id": msg["id"], "subject": msg["subject"], "from": msg["from"]}
            )

        # Check attachments
        if msg.get("attachments", 0) > 0:
            attachments.append(
                {
                    "id": msg["id"],
                    "subject": msg["subject"],
                    "count": msg["attachments"],
                }
            )

    return {
        "urgent_items": urgent,
        "replies_needed": replies_needed,
        "attachments_detected": attachments,
        "deadlines": [],
        "summary": f"Found {len(urgent)} urgent items, {len(replies_needed)} needing replies, {len(attachments)} with attachments",
    }


def run_daily_digest() -> str:
    """
    Generate daily email digest for Slack.

    Returns:
        Formatted Slack message string
    """
    if not GMAIL_AVAILABLE:
        return "❌ Gmail client not available"

    try:
        triage_result = summarize_inbox(limit=30)

        # Format for Slack
        lines = ["📧 *Daily Email Digest*\n"]

        # Urgent items
        urgent = triage_result.get("urgent_items", [])
        if urgent:
            lines.append(f"🔴 *Urgent ({len(urgent)}):*")
            for item in urgent[:5]:  # Top 5
                lines.append(f"  • {item.get('subject', 'No subject')}")
                if item.get("reason"):
                    lines.append(f"    _{item['reason']}_")
            if len(urgent) > 5:
                lines.append(f"  ... and {len(urgent) - 5} more")
            lines.append("")

        # Replies needed
        replies = triage_result.get("replies_needed", [])
        if replies:
            lines.append(f"✉️ *Replies Needed ({len(replies)}):*")
            for item in replies[:5]:
                lines.append(
                    f"  • {item.get('subject', 'No subject')} from {item.get('from', 'Unknown')}"
                )
            if len(replies) > 5:
                lines.append(f"  ... and {len(replies) - 5} more")
            lines.append("")

        # Attachments
        attachments = triage_result.get("attachments_detected", [])
        if attachments:
            lines.append(f"📎 *Attachments ({len(attachments)}):*")
            for item in attachments[:5]:
                lines.append(
                    f"  • {item.get('subject', 'No subject')} ({item.get('count', 0)} files)"
                )
            if len(attachments) > 5:
                lines.append(f"  ... and {len(attachments) - 5} more")
            lines.append("")

        # Deadlines
        deadlines = triage_result.get("deadlines", [])
        if deadlines:
            lines.append(f"📅 *Deadlines/Actions ({len(deadlines)}):*")
            for item in deadlines[:5]:
                lines.append(f"  • {item.get('subject', 'No subject')}")
                if item.get("deadline"):
                    lines.append(f"    Deadline: {item['deadline']}")
                if item.get("description"):
                    lines.append(f"    _{item['description']}_")
            if len(deadlines) > 5:
                lines.append(f"  ... and {len(deadlines) - 5} more")
            lines.append("")

        # Summary
        summary = triage_result.get("summary", "")
        if summary:
            lines.append(f"*Summary:* {summary}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Daily digest failed: {e}", exc_info=True)
        return f"❌ Error generating digest: {str(e)}"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "email-integration",
        "integration",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "utility",
    ],
    "keywords": ["daily", "digest", "inbox", "summarize", "triage"],
    "business_value": "Utility module for triage",
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
