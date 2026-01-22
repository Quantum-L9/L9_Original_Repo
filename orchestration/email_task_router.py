"""
L9 Email Task Router
====================

Converts Slack messages into Email Agent task structures.

This router ONLY creates email_task types. Mac Agent tasks use slack_task_router.py.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Email Task Router",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-12T14:26:37Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "email_task_router",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["memory.slack_ingest"],
    },
}
# ============================================================================

import json
import os
from typing import Any, Dict, List

import structlog
from openai import OpenAI

logger = structlog.get_logger(__name__)

MODEL = os.getenv("L9_LLM_MODEL", "gpt-4o-mini")


def get_client() -> OpenAI:
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def route_email_task(
    text: str, artifacts: List[Dict[str, Any]], user: str
) -> Dict[str, Any]:
    """
    Convert Slack message + file artifacts into Email Agent task structure.

    Args:
        text: User message text
        artifacts: List of file artifact dictionaries from slack_files.py
        user: Slack user ID

    Returns:
        Task dictionary with type="email_task", steps, artifacts, and metadata
    """
    client = get_client()

    system_prompt = """You are L9 Email Planner. Convert user requests into Email Agent task structures.

You must ALWAYS output valid JSON with type="email_task" only.

Output format MUST be:
{
  "type": "email_task",
  "steps": [
     {"action": "list_messages", "query": "...", "max_results": 10},
     {"action": "get_message", "message_id": "..."},
     {"action": "draft_email", "to": "...", "subject": "...", "body": "..."},
     {"action": "send_email", "draft_id": "..."}  // or {"action": "send_email", "to": "...", "subject": "...", "body": "..."}
     {"action": "reply_to_email", "message_id": "...", "body": "..."},
     {"action": "forward_email", "message_id": "...", "to": "...", "body": "..."}
  ],
  "artifacts": [...],
  "metadata": {
     "user": "<slack_user>",
     "instructions": "<raw user text>"
  }
}

No other keys allowed. Type MUST be "email_task".

Available email_task actions:
- list_messages: Search emails (query: Gmail search string, max_results: number)
- get_message: Get full message (message_id: Gmail message ID)
- draft_email: Create draft (to, subject, body)
- send_email: Send email (draft_id OR to/subject/body)
- reply_to_email: Reply to message (message_id, body)
- forward_email: Forward message (message_id, to, body)

When files are attached, reference them in the email body or as attachments.
If artifacts contain OCR/PDF/transcription data, use that information in your steps.

NOTE: This router ONLY creates email_task types. Browser automation should use slack_task_router.py."""

    # Build user message with artifact context
    user_message = f"User request: {text}\n\n"

    if artifacts:
        user_message += "Attached files:\n"
        for artifact in artifacts:
            user_message += f"- {artifact.get('name', 'unknown')} ({artifact.get('type', 'unknown')}) at {artifact.get('path', 'unknown')}\n"

            # Include OCR data if available
            if artifact.get("ocr"):
                ocr_data = artifact["ocr"]
                user_message += f"  OCR text: {ocr_data.get('text', '')[:200]}...\n"
                user_message += (
                    f"  OCR confidence: {ocr_data.get('confidence', 0):.1f}%\n"
                )

            # Include PDF data if available
            if artifact.get("pdf"):
                pdf_data = artifact["pdf"]
                user_message += f"  PDF summary: {pdf_data.get('summary', '')}\n"
                if pdf_data.get("fields"):
                    user_message += f"  PDF fields: {pdf_data.get('fields')}\n"

            # Include transcription if available
            if artifact.get("transcription"):
                trans_data = artifact["transcription"]
                user_message += (
                    f"  Transcription: {trans_data.get('text', '')[:200]}...\n"
                )

        user_message += "\n"

    user_message += "Generate the email task JSON structure based on the user's intent."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            response_format=(
                {"type": "json_object"} if MODEL.startswith("gpt-4") else None
            ),
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        # Try to extract JSON if wrapped in markdown
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        task_dict = json.loads(content)

        # Validate structure - only email_task allowed
        task_type = task_dict.get("type")
        if task_type != "email_task":
            logger.warning(
                f"Task type is not 'email_task', got: {task_type}. "
                f"Mac Agent tasks should use slack_task_router.py. "
                f"Fixing to email_task."
            )
            task_dict["type"] = "email_task"

        # Ensure required fields
        if "steps" not in task_dict:
            task_dict["steps"] = []
        if "artifacts" not in task_dict:
            task_dict["artifacts"] = artifacts
        if "metadata" not in task_dict:
            task_dict["metadata"] = {}

        task_dict["metadata"]["user"] = user
        task_dict["metadata"]["instructions"] = text

        logger.info(
            f"Routed Slack message to email_task with {len(task_dict.get('steps', []))} steps"
        )
        return task_dict

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.error(f"Response was: {content[:500]}")
        # Return minimal valid structure
        return {
            "type": "email_task",
            "steps": [],
            "artifacts": artifacts,
            "metadata": {
                "user": user,
                "instructions": text,
            },
        }
    except Exception as e:
        logger.error(f"Error routing email task: {e}", exc_info=True)
        # Return minimal valid structure
        return {
            "type": "email_task",
            "steps": [],
            "artifacts": artifacts,
            "metadata": {
                "user": user,
                "instructions": text,
            },
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "orchestration",
        "router",
        "serialization",
    ],
    "keywords": ["agent", "client", "email", "route", "router", "task"],
    "business_value": "This router ONLY creates email_task types. Mac Agent tasks use slack_task_router.py.",
    "last_modified": "2026-01-12T14:26:37Z",
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
