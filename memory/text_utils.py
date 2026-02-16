"""
L9 Memory — Canonical Text Extraction Utilities.

Single source of truth for:
- Extracting embeddable text from packet payloads
- Determining if content should skip embedding (GMP-42)

All ingestion and retrieval code MUST use these functions.
Every other inline payload.get("text") or payload.get("content") cascade
is a bug waiting to happen — route through here.
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "Text Extraction Utilities",
    "module_version": "1.0.0",
    "created_by": "L9_Pipeline_Unification",
    "created_at": "2026-02-12T20:00:00Z",
    "updated_at": "2026-02-12T20:00:00Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "text_utils",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.substrate_dag",
            "memory.retrieval",
            "memory.substrate_service",
        ],
    },
}

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ============================================================================
# Canonical Field Priority (ADR-UNIFIED-TEXT)
# ============================================================================
# This ordering is the SINGLE SOURCE OF TRUTH for all text extraction.
# Changing this order affects embedding consistency across ALL pipelines.
# If you change this, you MUST re-embed all existing packets.

EMBEDDABLE_FIELD_PRIORITY: tuple[str, ...] = (
    "text",
    "content",
    "description",
    "summary",
    "message",
)

MINIMUM_EMBEDDABLE_LENGTH: int = 10

# ============================================================================
# Skip Patterns (GMP-42: Filter low-value content from semantic index)
# ============================================================================

SKIP_EMBEDDING_PATTERNS: frozenset[str] = frozenset(
    {
        "Sorry, I encountered a temporary error. Please try again.",
        "Sorry, I encountered an error processing your command.",
        "No response generated.",
        "This message has already been processed.",
        "L9 agent executor not available. Please try again later.",
        "Mac agent is not available on this server.",
    }
)

SKIP_EMBEDDING_PREFIXES: tuple[str, ...] = (
    "Sorry, I encountered",
    "❌ Mac command error:",
    "❌ Please provide a command",
)


def extract_embeddable_text(payload: dict[str, Any]) -> str | None:
    """
    Extract the best text candidate for embedding from a packet payload.

    Uses the canonical field priority order. Returns None if no suitable
    text is found or text is below minimum length.

    Args:
        payload: Packet payload dictionary.

    Returns:
        Extracted text string or None if no embeddable content exists.
    """
    if not payload or not isinstance(payload, dict):
        return None

    for field_name in EMBEDDABLE_FIELD_PRIORITY:
        value = payload.get(field_name)
        if value is not None:
            text = str(value) if not isinstance(value, str) else value
            if len(text.strip()) >= MINIMUM_EMBEDDABLE_LENGTH:
                return text.strip()

    return None


def should_skip_embedding(text: str | None) -> bool:
    """
    Determine if text matches known low-value patterns that pollute semantic search.

    GMP-42: These patterns carry no semantic information and waste embedding compute.

    Args:
        text: The text content to check.

    Returns:
        True if text should NOT be embedded, False if embedding is appropriate.
    """
    if not text:
        return True

    text_stripped = text.strip()

    if len(text_stripped) < MINIMUM_EMBEDDABLE_LENGTH:
        return True

    if text_stripped in SKIP_EMBEDDING_PATTERNS:
        return True

    for prefix in SKIP_EMBEDDING_PREFIXES:
        if text_stripped.startswith(prefix):
            return True

    return False


__all__ = [
    "EMBEDDABLE_FIELD_PRIORITY",
    "MINIMUM_EMBEDDABLE_LENGTH",
    "SKIP_EMBEDDING_PATTERNS",
    "SKIP_EMBEDDING_PREFIXES",
    "extract_embeddable_text",
    "should_skip_embedding",
]
