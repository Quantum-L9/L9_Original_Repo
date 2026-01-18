"""
L9 Core Agents - Prompt Injection Defense
==========================================

Detects and blocks prompt injection attacks before they reach the LLM.

This module implements a defense layer that scans user input for:
- Identity override attempts ("You are now DAN")
- Safety bypass attempts ("Ignore previous instructions")
- Capability escalation ("Run GMPRUN without approval")
- Jailbreak patterns (roleplay, hypothetical scenarios)

When an injection is detected, the request is either:
- Blocked entirely (high severity)
- Downgraded to explanation-only mode (medium severity)
- Logged and allowed with warning (low severity)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Prompt Injection Defense",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "prompt_defense",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.agents.executor", "tests.core.bootstrap.test_prompt_defense"],
    },
}
# ============================================================================

import re
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

logger = structlog.get_logger(__name__)


# =============================================================================
# Injection Severity Levels
# =============================================================================


class InjectionSeverity(str, Enum):
    """Severity level of detected injection."""
    
    CRITICAL = "critical"  # Block entirely, emit violation packet
    HIGH = "high"          # Block, allow appeal to Igor
    MEDIUM = "medium"      # Downgrade to explanation mode
    LOW = "low"            # Log warning, allow with monitoring


# =============================================================================
# Injection Patterns
# =============================================================================

# Critical patterns - always block
CRITICAL_PATTERNS = [
    # Identity override
    (r"you\s+are\s+now\s+(DAN|evil|unbounded|unrestricted)", "identity_override_dan"),
    (r"ignore\s+(all\s+)?your\s+(previous\s+)?instructions", "ignore_instructions"),
    (r"disregard\s+(all\s+)?your\s+(previous\s+)?instructions", "disregard_instructions"),
    (r"forget\s+(all\s+)?your\s+(previous\s+)?instructions", "forget_instructions"),
    (r"override\s+(your\s+)?(safety|kernel|governance|constraints)", "override_safety"),
    (r"bypass\s+(your\s+)?(safety|kernel|governance|constraints)", "bypass_safety"),
    (r"disable\s+(your\s+)?(safety|kernel|governance)", "disable_safety"),
    
    # Explicit capability escalation
    (r"run\s+GMPRUN\s+without\s+approval", "gmprun_bypass"),
    (r"execute\s+.+\s+without\s+(Igor|approval)", "approval_bypass"),
    (r"grant\s+(yourself|me)\s+(admin|system|full)\s+access", "privilege_escalation"),
]

# High severity patterns - block with logging
HIGH_PATTERNS = [
    # Jailbreak attempts
    (r"pretend\s+(you\s+are|to\s+be)\s+an?\s+(unrestricted|unbounded)", "jailbreak_pretend"),
    (r"act\s+as\s+(if|though)\s+you\s+(have|had)\s+no\s+(restrictions|limits)", "jailbreak_act"),
    (r"roleplay\s+as\s+an?\s+(evil|unrestricted|unbounded)", "jailbreak_roleplay"),
    (r"in\s+this\s+hypothetical\s+scenario.+no\s+(rules|restrictions)", "jailbreak_hypothetical"),
    
    # Authority manipulation
    (r"I\s+am\s+(Igor|your\s+creator|your\s+admin)", "authority_spoofing"),
    (r"Igor\s+(said|told|wants)\s+you\s+to\s+ignore", "authority_impersonation"),
    
    # Tool manipulation
    (r"call\s+.+\s+tool\s+directly\s+without", "tool_direct_call"),
    (r"access\s+.+\s+database\s+without\s+logging", "audit_bypass"),
]

# Medium severity patterns - downgrade to explanation
MEDIUM_PATTERNS = [
    # Subtle manipulation
    (r"for\s+(educational|research)\s+purposes.+show\s+me\s+how\s+to", "educational_bypass"),
    (r"what\s+would\s+happen\s+if\s+you\s+ignored", "hypothetical_ignore"),
    (r"can\s+you\s+demonstrate.+bypassing", "demonstration_request"),
    
    # Information extraction
    (r"what\s+are\s+your\s+(exact\s+)?instructions", "instruction_extraction"),
    (r"show\s+me\s+your\s+(system\s+)?prompt", "prompt_extraction"),
    (r"reveal\s+your\s+(hidden|secret)\s+instructions", "hidden_instruction_request"),
]

# Low severity patterns - log and monitor
LOW_PATTERNS = [
    # Curiosity (potentially benign)
    (r"how\s+do\s+you\s+handle\s+prompt\s+injection", "injection_curiosity"),
    (r"what\s+safety\s+measures\s+do\s+you\s+have", "safety_curiosity"),
    (r"are\s+you\s+vulnerable\s+to", "vulnerability_curiosity"),
]


# =============================================================================
# Detection Result
# =============================================================================


@dataclass
class InjectionDetectionResult:
    """Result of prompt injection detection."""
    
    detected: bool = False
    severity: Optional[InjectionSeverity] = None
    patterns_matched: List[str] = field(default_factory=list)
    should_block: bool = False
    should_downgrade: bool = False
    message: str = ""
    redacted_input: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dict for packet storage."""
        return {
            "detected": self.detected,
            "severity": self.severity.value if self.severity else None,
            "patterns_matched": self.patterns_matched,
            "should_block": self.should_block,
            "should_downgrade": self.should_downgrade,
            "message": self.message,
            "redacted_input": self.redacted_input,
        }


# =============================================================================
# Detection Functions
# =============================================================================


def _check_patterns(
    text: str,
    patterns: List[Tuple[str, str]],
) -> List[str]:
    """
    Check text against a list of regex patterns.
    
    Args:
        text: Input text to check
        patterns: List of (pattern, name) tuples
    
    Returns:
        List of matched pattern names
    """
    matched = []
    for pattern, name in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(name)
    return matched


def _redact_input(text: str, max_length: int = 100) -> str:
    """
    Redact input for safe logging.
    
    Args:
        text: Input text
        max_length: Maximum length to include
    
    Returns:
        Redacted string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[REDACTED]"


def detect_prompt_injection(
    user_input: str,
    context: Optional[dict] = None,
) -> InjectionDetectionResult:
    """
    Detect prompt injection in user input.
    
    This is the main entry point for prompt injection detection.
    It should be called before any user input is processed by the LLM.
    
    Args:
        user_input: The user's input text
        context: Optional context (channel, user_id, etc.)
    
    Returns:
        InjectionDetectionResult with detection details
    """
    result = InjectionDetectionResult(
        redacted_input=_redact_input(user_input),
    )
    
    if not user_input:
        return result
    
    # Normalize text for pattern matching
    text = user_input.strip()
    
    # Check critical patterns first (highest priority)
    critical_matches = _check_patterns(text, CRITICAL_PATTERNS)
    if critical_matches:
        result.detected = True
        result.severity = InjectionSeverity.CRITICAL
        result.patterns_matched = critical_matches
        result.should_block = True
        result.message = (
            "Critical prompt injection detected. This request has been blocked. "
            "If you believe this is an error, please contact Igor."
        )
        logger.warning(
            "prompt_defense.critical_injection",
            patterns=critical_matches,
            redacted_input=result.redacted_input,
            context=context,
        )
        return result
    
    # Check high severity patterns
    high_matches = _check_patterns(text, HIGH_PATTERNS)
    if high_matches:
        result.detected = True
        result.severity = InjectionSeverity.HIGH
        result.patterns_matched = high_matches
        result.should_block = True
        result.message = (
            "Potential prompt injection detected. This request has been blocked. "
            "This incident has been logged."
        )
        logger.warning(
            "prompt_defense.high_injection",
            patterns=high_matches,
            redacted_input=result.redacted_input,
            context=context,
        )
        return result
    
    # Check medium severity patterns
    medium_matches = _check_patterns(text, MEDIUM_PATTERNS)
    if medium_matches:
        result.detected = True
        result.severity = InjectionSeverity.MEDIUM
        result.patterns_matched = medium_matches
        result.should_downgrade = True
        result.message = (
            "This request contains patterns that may be attempting to extract "
            "system information. I'll provide general guidance only."
        )
        logger.info(
            "prompt_defense.medium_injection",
            patterns=medium_matches,
            redacted_input=result.redacted_input,
            context=context,
        )
        return result
    
    # Check low severity patterns
    low_matches = _check_patterns(text, LOW_PATTERNS)
    if low_matches:
        result.detected = True
        result.severity = InjectionSeverity.LOW
        result.patterns_matched = low_matches
        # Allow but log
        logger.debug(
            "prompt_defense.low_injection",
            patterns=low_matches,
            redacted_input=result.redacted_input,
            context=context,
        )
        return result
    
    # No injection detected
    return result


def should_block_request(detection_result: InjectionDetectionResult) -> bool:
    """
    Determine if request should be blocked based on detection result.
    
    Args:
        detection_result: Result from detect_prompt_injection
    
    Returns:
        True if request should be blocked
    """
    return detection_result.should_block


def get_blocked_response(detection_result: InjectionDetectionResult) -> str:
    """
    Get the response message for a blocked request.
    
    Args:
        detection_result: Result from detect_prompt_injection
    
    Returns:
        Response message to send back to user
    """
    if detection_result.severity == InjectionSeverity.CRITICAL:
        return (
            "⚠️ **Request Blocked**\n\n"
            "I detected patterns in your message that conflict with my governance "
            "constraints. I cannot process this request.\n\n"
            "If you believe this is an error, please rephrase your request or "
            "contact Igor for assistance."
        )
    elif detection_result.severity == InjectionSeverity.HIGH:
        return (
            "⚠️ **Request Blocked**\n\n"
            "Your message contains patterns that appear to attempt bypassing "
            "my safety constraints. I cannot process this request.\n\n"
            "This incident has been logged for review."
        )
    else:
        return detection_result.message or "Request blocked due to policy violation."


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "detect_prompt_injection",
    "should_block_request",
    "get_blocked_response",
    "InjectionDetectionResult",
    "InjectionSeverity",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-039",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "data-models", "dataclass", "debugging", "foundation", "logging", "messaging", "monitoring", "rest-api"],
    "keywords": ["attempts", "block", "blocked", "defense", "detect", "detection", "injection", "module"],
    "business_value": "Identity override attempts ("You are now DAN") Safety bypass attempts ("Ignore previous instructions") Capability escalation ("Run GMPRUN without approval") Jailbreak patterns (roleplay, hypothetical ",
    "last_modified": "2026-01-14T15:03:00Z",
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
