"""
L9 Igor Command Interface
=========================

Provides structured command syntax and NLP-based intent extraction
for Igor to instruct L imperatively.

Usage:
    @L propose gmp: <description>
    @L analyze <entity>
    @L approve <task_id>
    @L rollback <change_id>

Or natural language: "@L what's the current VPS state?"

Version: 1.0.0 (GMP-11)
"""


# Lazy imports to avoid circular dependencies
def parse_command(text: str):
    """Parse Igor input into structured Command or NLPPrompt."""
    from core.commands.parser import parse_command as _parse

    return _parse(text)


def is_l_command(text: str) -> bool:
    """Check if text appears to be an @L command."""
    from core.commands.parser import is_l_command as _is_l

    return _is_l(text)


async def extract_intent(nlp_prompt, openai_client=None):
    """Extract intent from natural language prompt."""
    from core.commands.intent_extractor import extract_intent as _extract

    return await _extract(nlp_prompt, openai_client)


async def confirm_intent(intent, user_context, slack_client=None):
    """Request Igor confirmation for high-risk commands."""
    from core.commands.intent_extractor import confirm_intent as _confirm

    return await _confirm(intent, user_context, slack_client)


async def execute_command(command, user_id, context=None, **kwargs):
    """Execute a structured command."""
    from core.commands.executor import execute_command as _execute

    return await _execute(command, user_id, context, **kwargs)


# Re-export schemas for type hints
from core.commands.schemas import (
    Command,
    CommandResult,
    CommandType,
    ConfirmationResult,
    IntentModel,
    IntentType,
    NLPPrompt,
    RiskLevel,
)

__all__ = [
    # Schemas
    "Command",
    "CommandResult",
    "CommandType",
    "ConfirmationResult",
    "IntentModel",
    "IntentType",
    "NLPPrompt",
    "RiskLevel",
    "confirm_intent",
    "execute_command",
    "extract_intent",
    "is_l_command",
    # Functions
    "parse_command",
]
