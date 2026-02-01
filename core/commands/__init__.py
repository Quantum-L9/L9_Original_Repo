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

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0 (GMP-11)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API", "Slack API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-190",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.commands.executor",
        "core.commands.intent_extractor",
        "core.commands.parser",
        "core.commands.schemas",
    ],
    "tags": ["async", "core", "foundation", "service"],
    "keywords": [
        "command",
        "confirm",
        "execute",
        "extract",
        "igor",
        "intent",
        "parse",
        "state",
    ],
    "business_value": "Provides structured command syntax and NLP-based intent extraction for Igor to instruct L imperatively. @L propose gmp: <description> @L analyze <entity> @L approve <task_id> @L rollback <change_id> O",
    "last_modified": "2026-01-31T22:21:47Z",
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
