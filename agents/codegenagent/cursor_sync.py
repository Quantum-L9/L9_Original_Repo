"""
CodeGenAgent Cursor Sync (Simplified)
=====================================

Bi-directional sync between CodeGenAgent memory state
and Cursor-visible session history or instruction stack.

Lightweight version - for full sync use cursor_context_sync_engine.py

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cursor Sync",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:27:48Z",
    "updated_at": "2026-01-15T23:27:48Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "cursor_sync",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================


DEFAULT_CONTEXT_FILE = "cursor_context_envelope.json"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class CursorCapsule:
    """Cursor context capsule for a module."""

    module: str
    files: list[str] = field(default_factory=list)
    summary: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the CursorCapsule, including module, files, summary, and timestamp in ISO format."""
        return {
            "module": self.module,
            "files": self.files,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ContextEnvelope:
    """Context envelope for Cursor sync."""

    capsules: list[CursorCapsule] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the ContextEnvelope, including capsules, last update timestamp, and session ID, for cursor synchronization purposes."""
        return {
            "capsules": [c.to_dict() for c in self.capsules],
            "last_updated": self.last_updated.isoformat(),
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextEnvelope:
        """Create from dictionary."""
        env = cls(
            session_id=data.get("session_id"),
        )
        if data.get("last_updated"):
            env.last_updated = datetime.fromisoformat(data["last_updated"])

        for cap_data in data.get("capsules", []):
            capsule = CursorCapsule(
                module=cap_data["module"],
                files=cap_data.get("files", []),
                summary=cap_data.get("summary", ""),
            )
            if cap_data.get("timestamp"):
                capsule.timestamp = datetime.fromisoformat(cap_data["timestamp"])
            env.capsules.append(capsule)

        return env


# =============================================================================
# CURSOR SYNC FUNCTIONS
# =============================================================================


def sync_with_cursor(
    meta: dict[str, Any],
    output_files: dict[str, str],
    context_path: str | None = None,
) -> ContextEnvelope:
    """
    Sync generation results with Cursor context.

    Creates/updates a context envelope file that Cursor can read
    to understand what was generated.

    Args:
        meta: Meta specification used for generation
        output_files: Generated files (path -> content)
        context_path: Optional path for context file

    Returns:
        Updated ContextEnvelope
    """
    context_file = Path(context_path) if context_path else Path(DEFAULT_CONTEXT_FILE)

    # Load existing envelope or create new
    if context_file.exists():
        try:
            with open(context_file) as f:
                envelope = ContextEnvelope.from_dict(json.load(f))
        except Exception:
            envelope = ContextEnvelope()
    else:
        envelope = ContextEnvelope()

    # Create capsule for this generation
    module_name = meta.get("name") or meta.get("filename", "unknown")

    capsule = CursorCapsule(
        module=module_name,
        files=list(output_files.keys()),
        summary=meta.get("description", f"Generated {len(output_files)} files"),
    )

    # Update envelope
    update_cursor_state(module_name, capsule, envelope)

    # Persist
    envelope.last_updated = datetime.now(UTC)

    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(envelope.to_dict(), f, indent=2)

    logger.info(
        "cursor_sync_complete",
        module=module_name,
        files=len(output_files),
        context_file=str(context_file),
    )

    return envelope


def update_cursor_state(
    module_name: str,
    capsule: CursorCapsule,
    envelope: ContextEnvelope | None = None,
) -> ContextEnvelope:
    """
    Update Cursor state with a new capsule.

    Replaces existing capsule for the same module or adds new one.

    Args:
        module_name: Module name
        capsule: New capsule data
        envelope: Optional existing envelope

    Returns:
        Updated ContextEnvelope
    """
    if envelope is None:
        envelope = ContextEnvelope()

    # Remove existing capsule for this module
    envelope.capsules = [c for c in envelope.capsules if c.module != module_name]

    # Add new capsule
    envelope.capsules.append(capsule)

    # Keep only last N capsules
    MAX_CAPSULES = 20
    if len(envelope.capsules) > MAX_CAPSULES:
        envelope.capsules = envelope.capsules[-MAX_CAPSULES:]

    logger.debug(
        "cursor_state_updated",
        module=module_name,
        total_capsules=len(envelope.capsules),
    )

    return envelope


def get_cursor_context(
    context_path: str | None = None,
) -> ContextEnvelope | None:
    """
    Get current Cursor context.

    Args:
        context_path: Optional path to context file

    Returns:
        ContextEnvelope or None if not found
    """
    context_file = Path(context_path) if context_path else Path(DEFAULT_CONTEXT_FILE)

    if not context_file.exists():
        return None

    try:
        with open(context_file) as f:
            return ContextEnvelope.from_dict(json.load(f))
    except Exception as e:
        logger.warning("cursor_context_load_error", error=str(e))
        return None


def clear_cursor_context(context_path: str | None = None) -> bool:
    """
    Clear Cursor context file.

    Args:
        context_path: Optional path to context file

    Returns:
        True if cleared, False if not found
    """
    context_file = Path(context_path) if context_path else Path(DEFAULT_CONTEXT_FILE)

    if context_file.exists():
        context_file.unlink()
        logger.info("cursor_context_cleared", path=str(context_file))
        return True

    return False


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-012",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "agent-execution",
        "dataclass",
        "debugging",
        "filesystem",
        "intelligence",
        "logging",
        "serialization",
    ],
    "keywords": [
        "capsule",
        "clear",
        "codegenagent",
        "cursor",
        "envelope",
        "memory",
        "state",
        "sync",
    ],
    "business_value": "Provides cursor sync components including CursorCapsule, ContextEnvelope",
    "last_modified": "2026-01-15T23:27:48Z",
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
