"""
L9 Slack Task Router
====================

Converts Slack messages + file artifacts into Mac Agent task structures.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Task Router",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-12T14:26:37Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "slack_task_router",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["_archived.legacy_slack.webhook_slack", "memory.slack_ingest"],
    },
}
# ============================================================================

import json
import structlog
import os
from typing import Dict, Any, List

from openai import OpenAI

logger = structlog.get_logger(__name__)

MODEL = os.getenv("L9_LLM_MODEL", "gpt-4o-mini")

def get_client() -> OpenAI:
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def route_slack_message(
    text: str, artifacts: List[Dict[str, Any]], user: str
) -> Dict[str, Any]:
    """
    Convert Slack message + file artifacts into Mac Agent task structure.

    Args:
        text: User message text
        artifacts: List of file artifact dictionaries from slack_files.py
        user: Slack user ID

    Returns:
        Task dictionary with type, steps, artifacts, and metadata
    """
    client = get_client()

    system_prompt = """You are L9 Planner v2. Convert Slack messages into Mac Agent task structures.

You must ALWAYS output valid JSON with type="mac_task" only.

Output format MUST be:
{
  "type": "mac_task",
  "steps": [
     {"action": "goto", "url": "..."},
     {"action": "click", "selector": "text=..."},
     {"action": "fill", "selector": "#field", "text": "..."},
     {"action": "upload", "selector": "#file", "file_path": "<local_path>"},
     {"action": "screenshot"},
     {"action": "wait", "selector": "...", "timeout_ms": 5000}
  ],
  "artifacts": [...],
  "metadata": {
     "user": "<slack_user>",
     "instructions": "<raw user text>"
  }
}

No other keys allowed. Type MUST be "mac_task".

Available mac_task actions:
- goto: Navigate to URL
- click: Click element (use selector like "text=Submit" or "#button-id")
- fill: Fill input field (selector, text)
- upload: Upload file (selector, file_path - use path from artifacts)
- screenshot: Take screenshot
- wait: Wait for element (selector, optional timeout_ms)

When files are attached, use their "path" field as file_path in upload actions.
If artifacts contain OCR/PDF/transcription data, use that information in your steps.

NOTE: This router ONLY creates mac_task types. Email operations should be handled through separate email task routing."""

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

    user_message += "Generate the task JSON structure based on the user's intent."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
            if MODEL.startswith("gpt-4")
            else None,
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

        # Validate structure - only mac_task allowed
        task_type = task_dict.get("type")
        if task_type != "mac_task":
            logger.warning(
                f"Task type is not 'mac_task', got: {task_type}. "
                f"Email tasks should use separate email task routing. "
                f"Fixing to mac_task."
            )
            task_dict["type"] = "mac_task"

        # Ensure required fields
        if "steps" not in task_dict:
            task_dict["steps"] = []
        if "artifacts" not in task_dict:
            task_dict["artifacts"] = artifacts
        if "metadata" not in task_dict:
            task_dict["metadata"] = {}

        task_dict["metadata"]["user"] = user
        task_dict["metadata"]["instructions"] = text

        # Replace artifact paths in steps if needed
        if artifacts and task_dict.get("steps"):
            artifact_paths = {a.get("name"): a.get("path") for a in artifacts}
            for step in task_dict["steps"]:
                if step.get("action") == "upload":
                    # Check both "file" and "file_path" keys
                    file_ref = step.get("file") or step.get("file_path")
                    if file_ref:
                        # If file is a name, replace with path
                        if file_ref in artifact_paths:
                            step["file_path"] = artifact_paths[file_ref]
                            if "file" in step:
                                del step["file"]  # Remove "file" key, use "file_path"
                        elif not os.path.exists(file_ref):
                            # If path doesn't exist, try to find by name
                            for artifact in artifacts:
                                if (
                                    artifact.get("name") == file_ref
                                    or artifact.get("path") == file_ref
                                ):
                                    step["file_path"] = artifact.get("path")
                                    if "file" in step:
                                        del step["file"]
                                    break

        logger.info(
            f"Routed Slack message to task with {len(task_dict.get('steps', []))} steps"
        )
        return task_dict

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.error(f"Response was: {content[:500]}")
        # Return minimal valid structure
        return {
            "type": "mac_task",
            "steps": [],
            "artifacts": artifacts,
            "metadata": {
                "user": user,
                "instructions": text,
            },
        }
    except Exception as e:
        logger.error(f"Error routing Slack message: {e}", exc_info=True)
        # Return minimal valid structure
        return {
            "type": "mac_task",
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
    "tags": ["api", "intelligence", "llm", "logging", "messaging", "orchestration", "router", "serialization"],
    "keywords": ["agent", "client", "route", "router", "slack", "task"],
    "business_value": "Utility module for slack task router",
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
