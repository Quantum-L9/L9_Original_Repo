"""
L9 Core Boundary - Enforcer
===========================

PRIVATE_BOUNDARY enforcement stub for L9.

This module provides the boundary enforcement mechanism that ensures
private information doesn't leak to public interfaces.

Current Implementation (Phase 1 - Stub):
- Loads PRIVATE_BOUNDARY.md specification
- Provides enforcement hooks (currently pass-through)
- Logs enforcement actions

Future Implementation (Phase 2):
- Parse PRIVATE_BOUNDARY.md for redaction rules
- Apply automatic redaction to prompts/responses
- Support for domain-specific boundary rules

Usage:
    from core.boundary.enforcer import enforce_boundary, BoundaryEnforcer

    # Simple function
    safe_prompt = enforce_boundary(raw_prompt)

    # Class-based for configuration
    enforcer = BoundaryEnforcer()
    safe_prompt = enforcer.enforce(raw_prompt)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Enforcer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "enforcer",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.boundary.__init__", "core.boundary.enforcer"],
    },
}
# ============================================================================

import structlog
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

BOUNDARY_FILE = Path("PRIVATE_BOUNDARY.md")

# Default redaction patterns (Phase 2 will parse from PRIVATE_BOUNDARY.md)
DEFAULT_REDACTION_PATTERNS = [
    # API keys and secrets
    (
        r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[\w-]+["\']?',
        r"\1=[REDACTED]",
    ),
    # Email addresses (optional, conservative)
    # (r'[\w.+-]+@[\w-]+\.[\w.-]+', '[EMAIL]'),
]


# =============================================================================
# Boundary Specification
# =============================================================================


class BoundarySpec:
    """
    Parsed PRIVATE_BOUNDARY specification.

    Contains rules for what information should be protected
    at the orchestrator boundary.
    """

    def __init__(
        self,
        raw_content: str = "",
        redaction_patterns: Optional[List[tuple]] = None,
        protected_fields: Optional[List[str]] = None,
    ):
        self.raw_content = raw_content
        self.redaction_patterns = redaction_patterns or []
        self.protected_fields = protected_fields or []
        self._compiled_patterns: List[tuple] = []

        # Compile patterns
        for pattern, replacement in self.redaction_patterns:
            try:
                self._compiled_patterns.append((re.compile(pattern), replacement))
            except re.error as e:
                logger.warning(f"Invalid redaction pattern '{pattern}': {e}")

    def apply_redactions(self, text: str) -> str:
        """Apply all redaction patterns to text."""
        result = text
        for pattern, replacement in self._compiled_patterns:
            result = pattern.sub(replacement, result)
        return result


def load_boundary_spec(boundary_file: Optional[Path] = None) -> str:
    """
    Load the PRIVATE_BOUNDARY.md specification file.

    Args:
        boundary_file: Path to boundary file (defaults to PRIVATE_BOUNDARY.md)

    Returns:
        Raw content of boundary file, empty string if not found
    """
    boundary_file = boundary_file or BOUNDARY_FILE

    if not boundary_file.exists():
        logger.debug(f"No boundary file found at {boundary_file}")
        return ""

    try:
        return boundary_file.read_text()
    except (IOError, OSError) as e:
        logger.warning(f"Failed to read boundary file: {e}")
        return ""


def parse_boundary_spec(content: str) -> BoundarySpec:
    """
    Parse PRIVATE_BOUNDARY.md content into a BoundarySpec.

    Phase 1: Returns basic spec with default patterns
    Phase 2: Will parse markdown for rules and patterns

    Args:
        content: Raw boundary file content

    Returns:
        Parsed BoundarySpec
    """
    # Phase 1: Simple stub implementation
    # Phase 2 will parse the markdown for structured rules

    return BoundarySpec(
        raw_content=content,
        redaction_patterns=DEFAULT_REDACTION_PATTERNS.copy(),
        protected_fields=[],
    )


# =============================================================================
# Enforcement Functions
# =============================================================================


def enforce_boundary(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Apply PRIVATE_BOUNDARY enforcement to a prompt.

    Phase 1: Pass-through stub with logging
    Phase 2: Full enforcement with redaction

    Args:
        prompt: Raw prompt text
        context: Optional context for enforcement decisions

    Returns:
        Enforced/redacted prompt (same as input in Phase 1)
    """
    context = context or {}

    # Load spec if available
    spec_content = load_boundary_spec()

    if not spec_content:
        # No boundary file, pass through
        logger.debug("No PRIVATE_BOUNDARY spec, passing through")
        return prompt

    # Phase 1: Stub - just log and pass through
    # Phase 2: Parse spec and apply redactions
    logger.debug(f"Boundary enforcement called (stub) on {len(prompt)} chars")

    # Optional: Apply default patterns even in Phase 1
    # spec = parse_boundary_spec(spec_content)
    # return spec.apply_redactions(prompt)

    return prompt


def enforce_response_boundary(
    response: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Apply PRIVATE_BOUNDARY enforcement to a response.

    Ensures private information doesn't leak in responses.

    Args:
        response: Raw response text
        context: Optional context for enforcement decisions

    Returns:
        Enforced/redacted response
    """
    # Same implementation as prompt enforcement for now
    return enforce_boundary(response, context)


def enforce_payload_boundary(
    payload: Dict[str, Any],
    protected_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Apply PRIVATE_BOUNDARY enforcement to a payload dict.

    Redacts or removes protected fields from payload.

    Args:
        payload: Raw payload dict
        protected_fields: List of field names to protect

    Returns:
        Enforced payload with protected fields redacted
    """
    protected_fields = protected_fields or []

    if not protected_fields:
        return payload

    result = payload.copy()

    for field in protected_fields:
        if field in result:
            result[field] = "[REDACTED]"

    return result


# =============================================================================
# Enforcer Class
# =============================================================================


class BoundaryEnforcer:
    """
    Stateful boundary enforcer with caching and configuration.

    Use this class for repeated enforcement with the same configuration.

    Attributes:
        spec: Loaded boundary specification
        enabled: Whether enforcement is active
        log_enforcement: Whether to log enforcement actions
    """

    def __init__(
        self,
        boundary_file: Optional[Path] = None,
        enabled: bool = True,
        log_enforcement: bool = True,
    ):
        """
        Initialize the enforcer.

        Args:
            boundary_file: Path to boundary spec file
            enabled: Whether enforcement is active
            log_enforcement: Whether to log enforcement actions
        """
        self.boundary_file = boundary_file or BOUNDARY_FILE
        self.enabled = enabled
        self.log_enforcement = log_enforcement

        # Load spec on init
        self._spec: Optional[BoundarySpec] = None
        self._load_spec()

    def _load_spec(self) -> None:
        """Load the boundary specification."""
        content = load_boundary_spec(self.boundary_file)
        if content:
            self._spec = parse_boundary_spec(content)
            if self.log_enforcement:
                logger.info(f"Loaded boundary spec from {self.boundary_file}")
        else:
            self._spec = None

    def reload_spec(self) -> None:
        """Reload the boundary specification from disk."""
        self._load_spec()

    def enforce(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Apply boundary enforcement to text.

        Args:
            text: Text to enforce
            context: Optional context

        Returns:
            Enforced text
        """
        if not self.enabled:
            return text

        if self.log_enforcement:
            logger.debug(f"Enforcing boundary on {len(text)} chars")

        if self._spec:
            return self._spec.apply_redactions(text)

        return text

    def enforce_dict(
        self,
        data: Dict[str, Any],
        string_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply boundary enforcement to string fields in a dict.

        Args:
            data: Dict to process
            string_fields: List of field names to enforce (None = all strings)

        Returns:
            Dict with enforced string fields
        """
        if not self.enabled:
            return data

        result = {}

        for key, value in data.items():
            if isinstance(value, str):
                if string_fields is None or key in string_fields:
                    result[key] = self.enforce(value)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.enforce_dict(value, string_fields)
            elif isinstance(value, list):
                result[key] = [
                    self.enforce(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    @property
    def has_spec(self) -> bool:
        """Check if a boundary spec is loaded."""
        return self._spec is not None


# =============================================================================
# Singleton Instance
# =============================================================================

_default_enforcer: Optional[BoundaryEnforcer] = None


def get_default_enforcer() -> BoundaryEnforcer:
    """Get the default singleton enforcer instance."""
    global _default_enforcer
    if _default_enforcer is None:
        _default_enforcer = BoundaryEnforcer()
    return _default_enforcer


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Functions
    "load_boundary_spec",
    "parse_boundary_spec",
    "enforce_boundary",
    "enforce_response_boundary",
    "enforce_payload_boundary",
    "get_default_enforcer",
    # Classes
    "BoundarySpec",
    "BoundaryEnforcer",
    # Constants
    "BOUNDARY_FILE",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-030",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "core",
        "debugging",
        "filesystem",
        "foundation",
        "logging",
        "security",
        "utility",
    ],
    "keywords": [
        "apply",
        "boundary",
        "boundaryenforcer",
        "core",
        "default",
        "enforce",
        "enforcement",
        "enforcer",
    ],
    "business_value": "This module provides the boundary enforcement mechanism that ensures private information doesn't leak to public interfaces. Loads PRIVATE_BOUNDARY.md specification Provides enforcement hooks (currentl",
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
