"""
L9 Igor Command Interface - Parser
==================================

Parses structured commands and natural language prompts from Igor input.

Structured command patterns:
    @L propose gmp: <description>
    @L analyze <entity>
    @L approve <task_id>
    @L rollback <change_id>
    @L status [task_id]
    @L help

Unrecognized patterns fall back to NLPPrompt for intent extraction.

Version: 1.0.0 (GMP-11)
"""

from __future__ import annotations



import structlog

from core.commands.schemas import (
    COMMAND_PATTERNS,
    Command,
    CommandType,
    NLPPrompt,
    RiskLevel,
)

logger = structlog.get_logger(__name__)


def parse_command(text: str) -> Command | NLPPrompt:
    """
    Parse Igor input into structured Command or NLPPrompt.

    Attempts pattern matching for recognized command syntax.
    Falls back to NLPPrompt for natural language processing.

    Args:
        text: Raw input text from Igor

    Returns:
        Command if structured pattern matched, NLPPrompt otherwise
    """
    text = text.strip()
    if not text:
        return NLPPrompt(text="", raw_text="")

    logger.debug("Parsing command", text=text[:100])

    # Try structured command patterns
    for pattern_name, pattern in COMMAND_PATTERNS.items():
        match = pattern.match(text)
        if match:
            return _build_command(pattern_name, match, text)

    # Check if it starts with @L but didn't match known patterns
    if text.lower().startswith("@l "):
        # Extract the content after @L for NLP processing
        nlp_text = text[3:].strip()
        logger.debug(
            "Unrecognized @L command, falling back to NLP", nlp_text=nlp_text[:100]
        )
        return NLPPrompt(text=nlp_text, raw_text=text)

    # Plain text - treat as NLP prompt
    return NLPPrompt(text=text, raw_text=text)


def _build_command(pattern_name: str, match, raw_text: str) -> Command:
    """Build Command from matched pattern."""

    if pattern_name == "propose_gmp":
        description = match.group(1).strip()
        return Command(
            type=CommandType.PROPOSE_GMP,
            raw_text=raw_text,
            description=description,
            risk_level=RiskLevel.HIGH,  # GMP runs are high-risk
            parameters={"gmp_description": description},
        )

    if pattern_name == "analyze":
        entity = match.group(1).strip()
        return Command(
            type=CommandType.ANALYZE,
            raw_text=raw_text,
            target=entity,
            risk_level=RiskLevel.LOW,  # Analysis is read-only
            parameters={"entity_id": entity},
        )

    if pattern_name == "approve":
        task_id = match.group(1).strip()
        return Command(
            type=CommandType.APPROVE,
            raw_text=raw_text,
            target=task_id,
            risk_level=RiskLevel.MEDIUM,  # Approvals are medium-risk
            parameters={"task_id": task_id},
        )

    if pattern_name == "rollback":
        change_id = match.group(1).strip()
        return Command(
            type=CommandType.ROLLBACK,
            raw_text=raw_text,
            target=change_id,
            risk_level=RiskLevel.CRITICAL,  # Rollbacks are critical
            parameters={"change_id": change_id},
        )

    if pattern_name == "status":
        task_id = match.group(1) if match.lastindex else None
        return Command(
            type=CommandType.STATUS,
            raw_text=raw_text,
            target=task_id.strip() if task_id else None,
            risk_level=RiskLevel.LOW,
            parameters={"task_id": task_id.strip() if task_id else None},
        )

    if pattern_name == "help":
        return Command(
            type=CommandType.HELP,
            raw_text=raw_text,
            risk_level=RiskLevel.LOW,
        )

    # Fallback (should not happen)
    logger.warning("Unknown pattern matched", pattern_name=pattern_name)
    return Command(
        type=CommandType.QUERY,
        raw_text=raw_text,
        risk_level=RiskLevel.LOW,
    )


def is_l_command(text: str) -> bool:
    """
    Check if text appears to be an @L command.

    Args:
        text: Input text to check

    Returns:
        True if text starts with @L or @l
    """
    return text.strip().lower().startswith("@l ")


__all__ = [
    "Command",
    "NLPPrompt",
    "is_l_command",
    "parse_command",
]

# Runtime execution trace - updated automatically on every execution
