"""
L9 Igor Command Interface - Intent Extractor
=============================================

Extracts intent from natural language text using LLM prompting.
Handles ambiguity resolution and high-risk confirmation flows.

Version: 1.0.0 (GMP-11)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Intent Extractor",
    "module_version": "1.0.0 (GMP-11)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "intent_extractor",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API", "Slack API"],
        "memory_layers": [],
        "imported_by": [
            "api.routes.commands",
            "core.commands.__init__",
            "memory.slack_ingest",
            "tests.integration.test_igor_commands",
        ],
    },
}
# ============================================================================

import json
from datetime import datetime
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI, OpenAI

from core.commands.schemas import (Command, CommandType, ConfirmationResult,
                                   IntentModel, IntentType, NLPPrompt,
                                   RiskLevel)

logger = structlog.get_logger(__name__)

# Intent extraction system prompt
INTENT_EXTRACTION_PROMPT = """You are an intent extraction system for L9, an autonomous AI OS.

Your job is to analyze natural language commands from Igor (the human operator) and extract structured intent.

Possible intent types:
- propose: Creating new GMP, code, or plans
- analyze: Examining entities, code, or state (read-only)
- approve: Approving pending tasks
- reject: Rejecting pending tasks
- rollback: Reverting changes
- query: Asking questions (read-only)
- deploy: Deploying code or configuration
- execute: Running commands or scripts
- unknown: Cannot determine intent

Respond with JSON only:
{
    "intent_type": "<type>",
    "confidence": <0.0-1.0>,
    "entities": {"key": "value"},
    "ambiguities": ["list of unclear elements"],
    "suggested_action": "<brief description of what L should do>"
}

Be conservative with confidence. If unclear, use confidence < 0.7."""


async def extract_intent(
    nlp_prompt: NLPPrompt,
    openai_client: Optional[AsyncOpenAI] = None,
) -> IntentModel:
    """
    Extract intent from natural language prompt using LLM.

    Args:
        nlp_prompt: NLPPrompt containing the natural language text
        openai_client: Optional AsyncOpenAI client (uses default if not provided)

    Returns:
        IntentModel with extracted intent and confidence
    """
    text = nlp_prompt.text
    logger.info("Extracting intent", text=text[:100])

    # Use provided client or create default
    if openai_client is None:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key, using rule-based fallback")
            return _rule_based_intent(text, nlp_prompt.raw_text)
        openai_client = AsyncOpenAI(api_key=api_key)

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract intent from: {text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for consistency
            max_tokens=500,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        intent_type = _parse_intent_type(data.get("intent_type", "unknown"))
        confidence = float(data.get("confidence", 0.5))
        entities = data.get("entities", {})
        ambiguities = data.get("ambiguities", [])

        # Build suggested command if high confidence
        suggested_command = None
        if confidence >= 0.8:
            suggested_command = _intent_to_command(
                intent_type, entities, nlp_prompt.raw_text
            )

        return IntentModel(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities,
            ambiguities=ambiguities,
            original_text=nlp_prompt.raw_text,
            suggested_command=suggested_command,
        )

    except Exception as e:
        logger.error("Intent extraction failed", error=str(e))
        return _rule_based_intent(text, nlp_prompt.raw_text)


def extract_intent_sync(
    nlp_prompt: NLPPrompt,
    openai_client: Optional[OpenAI] = None,
) -> IntentModel:
    """
    Synchronous version of extract_intent for non-async contexts.

    Args:
        nlp_prompt: NLPPrompt containing the natural language text
        openai_client: Optional OpenAI client (uses default if not provided)

    Returns:
        IntentModel with extracted intent and confidence
    """
    text = nlp_prompt.text
    logger.info("Extracting intent (sync)", text=text[:100])

    # Use provided client or create default
    if openai_client is None:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key, using rule-based fallback")
            return _rule_based_intent(text, nlp_prompt.raw_text)
        openai_client = OpenAI(api_key=api_key)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract intent from: {text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        intent_type = _parse_intent_type(data.get("intent_type", "unknown"))
        confidence = float(data.get("confidence", 0.5))
        entities = data.get("entities", {})
        ambiguities = data.get("ambiguities", [])

        suggested_command = None
        if confidence >= 0.8:
            suggested_command = _intent_to_command(
                intent_type, entities, nlp_prompt.raw_text
            )

        return IntentModel(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities,
            ambiguities=ambiguities,
            original_text=nlp_prompt.raw_text,
            suggested_command=suggested_command,
        )

    except Exception as e:
        logger.error("Intent extraction failed (sync)", error=str(e))
        return _rule_based_intent(text, nlp_prompt.raw_text)


async def confirm_intent(
    intent: IntentModel,
    user_context: dict[str, Any],
    slack_client: Optional[Any] = None,
) -> ConfirmationResult:
    """
    Request Igor confirmation for high-risk commands.

    For high-risk intents, generates a summary and asks Igor:
    "I understood you want to {action}. Should I proceed?"

    Args:
        intent: Extracted IntentModel
        user_context: Context including user_id, channel, etc.
        slack_client: Optional Slack client for sending confirmations

    Returns:
        ConfirmationResult with confirmed status
    """
    command = intent.suggested_command
    if command is None or not command.requires_confirmation:
        # No confirmation needed for low-risk commands
        return ConfirmationResult(
            confirmed=True,
            command_id=intent.id,
            confirmed_by="system",
            reason="Low-risk command, no confirmation required",
            timestamp=datetime.utcnow().isoformat(),
        )

    # Log confirmation request
    logger.info(
        "Requesting Igor confirmation",
        command_type=command.type.value,
        risk_level=command.risk_level.value,
        intent_id=str(intent.id),
    )

    # Build confirmation message
    action_description = _describe_action(intent)
    confirmation_message = (
        f"🔒 **Confirmation Required**\n\n"
        f"I understood you want to: **{action_description}**\n\n"
        f"Risk Level: `{command.risk_level.value.upper()}`\n"
        f"Command ID: `{command.id}`\n\n"
        f"Should I proceed? Reply with `@L approve {command.id}` or `@L reject {command.id}`"
    )

    # If Slack client available, send confirmation request
    if slack_client is not None:
        try:
            channel = user_context.get("channel")
            if channel:
                await slack_client.send_message(
                    channel=channel,
                    text=confirmation_message,
                )
                logger.info("Sent confirmation request to Slack", channel=channel)
        except Exception as e:
            logger.warning("Failed to send Slack confirmation", error=str(e))

    # For now, return pending confirmation
    # In a full implementation, this would wait for Igor's response
    return ConfirmationResult(
        confirmed=False,
        command_id=command.id,
        confirmed_by="pending",
        reason=f"Awaiting Igor confirmation: {action_description}",
        timestamp=datetime.utcnow().isoformat(),
    )


def _parse_intent_type(value: str) -> IntentType:
    """Parse intent type string to enum."""
    try:
        return IntentType(value.lower())
    except ValueError:
        return IntentType.UNKNOWN


def _intent_to_command(
    intent_type: IntentType,
    entities: dict[str, Any],
    raw_text: str,
) -> Optional[Command]:
    """Convert intent to structured command if possible."""

    type_mapping: dict[IntentType, CommandType] = {
        IntentType.PROPOSE: CommandType.PROPOSE_GMP,
        IntentType.ANALYZE: CommandType.ANALYZE,
        IntentType.APPROVE: CommandType.APPROVE,
        IntentType.ROLLBACK: CommandType.ROLLBACK,
        IntentType.QUERY: CommandType.QUERY,
    }

    risk_mapping: dict[IntentType, RiskLevel] = {
        IntentType.PROPOSE: RiskLevel.HIGH,
        IntentType.ANALYZE: RiskLevel.LOW,
        IntentType.APPROVE: RiskLevel.MEDIUM,
        IntentType.REJECT: RiskLevel.MEDIUM,
        IntentType.ROLLBACK: RiskLevel.CRITICAL,
        IntentType.QUERY: RiskLevel.LOW,
        IntentType.DEPLOY: RiskLevel.CRITICAL,
        IntentType.EXECUTE: RiskLevel.HIGH,
        IntentType.UNKNOWN: RiskLevel.LOW,
    }

    command_type = type_mapping.get(intent_type)
    if command_type is None:
        return None

    return Command(
        type=command_type,
        raw_text=raw_text,
        target=entities.get("target") or entities.get("entity"),
        description=entities.get("description"),
        parameters=entities,
        risk_level=risk_mapping.get(intent_type, RiskLevel.LOW),
    )


def _describe_action(intent: IntentModel) -> str:
    """Generate human-readable action description."""
    action_descriptions: dict[IntentType, str] = {
        IntentType.PROPOSE: "create a new GMP or proposal",
        IntentType.ANALYZE: "analyze an entity or state",
        IntentType.APPROVE: "approve a pending task",
        IntentType.REJECT: "reject a pending task",
        IntentType.ROLLBACK: "rollback recent changes",
        IntentType.QUERY: "query information",
        IntentType.DEPLOY: "deploy code or configuration",
        IntentType.EXECUTE: "execute a command or script",
        IntentType.UNKNOWN: "perform an unclear action",
    }

    base_description = action_descriptions.get(intent.intent_type, "perform an action")

    # Add entity context if available
    target = intent.entities.get("target") or intent.entities.get("entity")
    if target:
        base_description = f"{base_description} ({target})"

    return base_description


def _rule_based_intent(text: str, raw_text: str) -> IntentModel:
    """
    Rule-based intent extraction fallback when LLM unavailable.

    Uses keyword matching for basic intent classification.
    """
    text_lower = text.lower()

    # Keyword patterns
    if any(kw in text_lower for kw in ["propose", "create", "new", "gmp", "plan"]):
        intent_type = IntentType.PROPOSE
        confidence = 0.6
    elif any(
        kw in text_lower for kw in ["analyze", "check", "examine", "inspect", "state"]
    ):
        intent_type = IntentType.ANALYZE
        confidence = 0.7
    elif any(kw in text_lower for kw in ["approve", "accept", "yes", "confirm"]):
        intent_type = IntentType.APPROVE
        confidence = 0.6
    elif any(kw in text_lower for kw in ["reject", "deny", "no", "cancel"]):
        intent_type = IntentType.REJECT
        confidence = 0.6
    elif any(kw in text_lower for kw in ["rollback", "revert", "undo"]):
        intent_type = IntentType.ROLLBACK
        confidence = 0.7
    elif any(kw in text_lower for kw in ["deploy", "push", "release"]):
        intent_type = IntentType.DEPLOY
        confidence = 0.6
    elif any(kw in text_lower for kw in ["run", "execute", "shell", "command"]):
        intent_type = IntentType.EXECUTE
        confidence = 0.5
    elif "?" in text or any(
        kw in text_lower for kw in ["what", "how", "why", "when", "where"]
    ):
        intent_type = IntentType.QUERY
        confidence = 0.7
    else:
        intent_type = IntentType.UNKNOWN
        confidence = 0.3

    return IntentModel(
        intent_type=intent_type,
        confidence=confidence,
        entities={},
        ambiguities=["Rule-based extraction, may need clarification"],
        original_text=raw_text,
        suggested_command=None,
    )


__all__ = [
    "extract_intent",
    "extract_intent_sync",
    "confirm_intent",
    "IntentModel",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.commands.schemas"],
    "tags": [
        "api",
        "async",
        "core",
        "foundation",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "service",
    ],
    "keywords": ["confirm", "extract", "extractor", "intent", "sync"],
    "business_value": "Handles ambiguity resolution and high-risk confirmation flows. Version: 1.0.0 (GMP-11)",
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
