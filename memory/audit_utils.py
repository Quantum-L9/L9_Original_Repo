"""
L9 Memory - Audit Utilities
============================

Security utilities for packet ingestion audit and injection detection.

Provides:
- Injection marker detection for prompt injection prevention
- PII detection and redaction
- Content normalization (NFC, zero-width char removal)
- Content hashing for deduplication
- Packet pre-processing and audit reporting

Version: 2.0.0 (merged Codex additions with existing regex patterns)

Changelog:
- v2.0.0: Added PII detection, redaction, normalization, content hashing
- v1.0.0: Initial injection marker detection
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional, Set
from uuid import UUID, NAMESPACE_URL, uuid5

from core.schemas.packet_envelope_v2 import PacketEnvelopeIn, PacketMetadata

logger = structlog.get_logger(__name__)


# =============================================================================
# Normalization Patterns
# =============================================================================

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF]")
WHITESPACE_RE = re.compile(r"\s+")


# =============================================================================
# PII Detection Patterns
# =============================================================================

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{7,}\d"),
    "api_key": re.compile(r"(?:sk-|api_key=)[A-Za-z0-9]{8,}"),
}


# =============================================================================
# Injection Marker Patterns
# =============================================================================

# Common prompt injection patterns to detect
# These patterns indicate potential attempts to manipulate LLM behavior
INJECTION_MARKERS: Set[str] = {
    # Direct instruction overrides
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "forget your instructions",
    "new instructions:",
    "override:",
    "system prompt:",
    # Role manipulation
    "you are now",
    "act as if",
    "pretend you are",
    "roleplay as",
    "assume the role",
    # Jailbreak patterns
    "DAN mode",
    "developer mode",
    "jailbreak",
    "bypass restrictions",
    "no restrictions",
    # Output manipulation
    "output the following exactly",
    "repeat after me",
    "say exactly",
    # Delimiter exploitation
    "```system",
    "[SYSTEM]",
    "[[SYSTEM]]",
    "<|system|>",
    "</s>",
    "<s>",
}

# Regex patterns for more sophisticated detection
INJECTION_REGEX_PATTERNS: list[re.Pattern] = [
    # Instruction override with variations
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
    # Hidden instruction blocks
    re.compile(r"\[/?INST\]", re.IGNORECASE),
    re.compile(r"<</?SYS>>", re.IGNORECASE),
    # Base64 encoded content (potential hidden payloads)
    re.compile(r"[A-Za-z0-9+/]{50,}={0,2}"),
    # Unicode homoglyph attacks (zero-width chars)
    re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]"),
]


# =============================================================================
# Audit Report
# =============================================================================


@dataclass
class AuditReport:
    """
    Report from packet audit/pre-processing.

    Contains information about any security concerns detected
    during packet ingestion pre-processing, including:
    - Injection marker detection
    - PII detection and redaction stats
    - Content hashing for deduplication
    """

    packet_id: UUID
    timestamp: datetime = field(default_factory=datetime.utcnow)
    injection_markers: Set[str] = field(default_factory=set)
    regex_matches: list[str] = field(default_factory=list)
    # v2.0 additions
    content_hash: Optional[str] = None
    checksum_raw: Optional[str] = None
    redaction_count: int = 0
    pii_types: tuple[str, ...] = field(default_factory=tuple)
    sanitized: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def has_security_concerns(self) -> bool:
        """Check if any security concerns were detected."""
        return bool(self.injection_markers) or bool(self.regex_matches)

    @property
    def has_pii(self) -> bool:
        """Check if any PII was detected."""
        return bool(self.pii_types)

    @property
    def concern_count(self) -> int:
        """Total number of security concerns detected."""
        return len(self.injection_markers) + len(self.regex_matches)


# =============================================================================
# Detection Functions
# =============================================================================


def has_injection_markers(packet: PacketEnvelopeIn) -> bool:
    """
    Quick check for injection markers in packet content.

    Args:
        packet: PacketEnvelopeIn to check

    Returns:
        True if any injection markers detected
    """
    text_content = _extract_text_content(packet)
    if not text_content:
        return False

    text_lower = text_content.lower()

    # Check string markers
    for marker in INJECTION_MARKERS:
        if marker.lower() in text_lower:
            return True

    # Check regex patterns
    for pattern in INJECTION_REGEX_PATTERNS:
        if pattern.search(text_content):
            return True

    return False


def detect_injection_markers(text: str) -> tuple[Set[str], list[str]]:
    """
    Detect all injection markers in text.

    Args:
        text: Text content to analyze

    Returns:
        Tuple of (string_markers_found, regex_matches_found)
    """
    string_markers: Set[str] = set()
    regex_matches: list[str] = []

    text_lower = text.lower()

    # Check string markers
    for marker in INJECTION_MARKERS:
        if marker.lower() in text_lower:
            string_markers.add(marker)

    # Check regex patterns
    for pattern in INJECTION_REGEX_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # Store pattern name and first match
            regex_matches.append(f"{pattern.pattern[:30]}... matched")

    return string_markers, regex_matches


def _extract_text_content(packet: PacketEnvelopeIn) -> Optional[str]:
    """
    Extract text content from packet payload for analysis.

    Checks common text fields in payload.
    """
    if not packet.payload:
        return None

    # Check common text fields
    text_fields = ["text", "content", "description", "summary", "message", "query", "input"]

    for field_name in text_fields:
        value = packet.payload.get(field_name)
        if value and isinstance(value, str):
            return value

    # Fallback: stringify entire payload for deep scan
    # Only for payloads under 10KB to avoid performance issues
    try:
        payload_str = str(packet.payload)
        if len(payload_str) < 10240:
            return payload_str
    except Exception:
        pass

    return None


# =============================================================================
# Normalization Functions (v2.0)
# =============================================================================


def normalize_text(text: str) -> str:
    """
    Normalize text using NFC, strip zero-width chars, and collapse whitespace.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text string
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def normalize_payload(value: Any) -> Any:
    """
    Recursively normalize string values inside payload structures.
    
    Args:
        value: Payload value (can be str, list, dict, or primitive)
        
    Returns:
        Normalized payload with all strings normalized
    """
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: normalize_payload(val) for key, val in value.items()}
    return value


# =============================================================================
# PII Detection Functions (v2.0)
# =============================================================================


def extract_strings(payload: Any) -> Iterable[str]:
    """
    Yield all string values from a payload for scanning.
    
    Args:
        payload: Payload to extract strings from
        
    Yields:
        String values found in payload
    """
    if isinstance(payload, str):
        yield payload
    elif isinstance(payload, dict):
        for item in payload.values():
            yield from extract_strings(item)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            yield from extract_strings(item)


def detect_pii_types(payload: Any) -> tuple[str, ...]:
    """
    Detect PII categories present in payload string values.
    
    Args:
        payload: Payload to scan for PII
        
    Returns:
        Tuple of PII type names found (e.g., ("email", "phone"))
    """
    types = set()
    for text in extract_strings(payload):
        for name, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                types.add(name)
    return tuple(sorted(types))


def redact_pii(payload: Any) -> tuple[Any, int, tuple[str, ...]]:
    """
    Redact PII in payload, returning updated payload, redaction count, and types.
    
    Args:
        payload: Payload to redact PII from
        
    Returns:
        Tuple of (redacted_payload, redaction_count, pii_types_found)
    """
    redaction_count = 0
    pii_types: Set[str] = set()

    def _redact_value(value: Any) -> Any:
        nonlocal redaction_count
        if isinstance(value, str):
            redacted = value
            for name, pattern in PII_PATTERNS.items():
                redacted, count = pattern.subn(f"[REDACTED:{name}]", redacted)
                if count:
                    pii_types.add(name)
                    redaction_count += count
            return redacted
        if isinstance(value, list):
            return [_redact_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_redact_value(item) for item in value)
        if isinstance(value, dict):
            return {key: _redact_value(val) for key, val in value.items()}
        return value

    return _redact_value(payload), redaction_count, tuple(sorted(pii_types))


# =============================================================================
# Content Hashing Functions (v2.0)
# =============================================================================


def _stable_json_dumps(value: Any) -> str:
    """Create stable JSON representation for hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _hash_payload(value: Any) -> str:
    """Compute SHA256 hash of payload."""
    return hashlib.sha256(_stable_json_dumps(value).encode("utf-8")).hexdigest()


def compute_content_hash(payload: Any, metadata_projection: dict[str, Any]) -> str:
    """
    Compute SHA256 over normalized payload + metadata projection.
    
    Args:
        payload: Packet payload
        metadata_projection: Metadata fields to include in hash
        
    Returns:
        SHA256 hex digest
    """
    return _hash_payload({"payload": payload, "metadata": metadata_projection})


# =============================================================================
# Packet Pre-Processing
# =============================================================================


def prepare_packet_for_ingest(
    packet: PacketEnvelopeIn,
    deep_scan: bool = True,
    redact_pii_enabled: bool = False,
    normalize_enabled: bool = True,
) -> tuple[PacketEnvelopeIn, AuditReport]:
    """
    Prepare a packet for ingestion with security audit.

    Performs:
    1. Payload normalization (NFC, zero-width char removal)
    2. Injection marker detection (string + regex patterns)
    3. PII detection
    4. Optional PII redaction
    5. Content hashing for deduplication
    6. Generates comprehensive audit report

    Args:
        packet: PacketEnvelopeIn to process
        deep_scan: If True, scan entire payload; if False, only text fields
        redact_pii_enabled: If True, redact detected PII in payload
        normalize_enabled: If True, normalize payload strings

    Returns:
        Tuple of (processed_packet, audit_report)

    Note:
        If redact_pii_enabled=False (default), packet is returned unchanged.
        Modification decisions are left to the caller to preserve audit trail.
    """
    from uuid import uuid4

    packet_id = packet.packet_id or uuid4()
    
    # Start building report
    report = AuditReport(packet_id=packet_id)
    
    # Step 1: Normalize payload (if enabled)
    working_payload = packet.payload
    if normalize_enabled:
        working_payload = normalize_payload(working_payload)
    
    # Step 2: Compute raw checksum (before any redaction)
    report.checksum_raw = _hash_payload(working_payload)
    
    # Step 3: Detect PII
    pii_types = detect_pii_types(working_payload)
    report.pii_types = pii_types
    
    # Step 4: Optional PII redaction
    if redact_pii_enabled and pii_types:
        working_payload, redaction_count, _ = redact_pii(working_payload)
        report.redaction_count = redaction_count
        report.sanitized = True
        report.notes.append(f"Redacted {redaction_count} PII instances")

    # Step 5: Extract text for injection analysis
    text_content = _extract_text_content(packet)

    if text_content:
        # Detect injection markers (string + regex)
        string_markers, regex_matches = detect_injection_markers(text_content)

        report.injection_markers = string_markers
        report.regex_matches = regex_matches

        if report.has_security_concerns:
            logger.warning(
                "injection_markers_detected",
                packet_id=str(packet_id),
                packet_type=packet.packet_type,
                marker_count=report.concern_count,
                markers=list(string_markers)[:5],  # Log first 5 for brevity
            )
            report.notes.append(
                f"Detected {report.concern_count} potential injection markers"
            )

    # Step 6: Compute final content hash
    metadata = packet.metadata or PacketMetadata()
    metadata_projection = metadata.model_dump() if hasattr(metadata, 'model_dump') else {}
    # Remove dynamic fields from hash
    for key in ("content_hash", "checksum_raw", "redaction_count", "pii_types", "injection_markers"):
        metadata_projection.pop(key, None)
    
    report.content_hash = compute_content_hash(working_payload, metadata_projection)
    
    # Step 7: Generate deterministic packet_id from content hash if not provided
    final_packet_id = packet.packet_id or uuid5(NAMESPACE_URL, report.content_hash)
    report.packet_id = final_packet_id
    
    # Step 8: Build output packet
    if working_payload != packet.payload or final_packet_id != packet.packet_id:
        # Create modified packet using model_copy
        prepared = packet.model_copy(
            update={
                "packet_id": final_packet_id,
                "payload": working_payload,
            }
        )
    else:
        prepared = packet

    return prepared, report


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core classes
    "AuditReport",
    # Injection detection
    "INJECTION_MARKERS",
    "INJECTION_REGEX_PATTERNS",
    "has_injection_markers",
    "detect_injection_markers",
    # PII detection (v2.0)
    "PII_PATTERNS",
    "detect_pii_types",
    "redact_pii",
    "extract_strings",
    # Normalization (v2.0)
    "normalize_text",
    "normalize_payload",
    # Hashing (v2.0)
    "compute_content_hash",
    # Main entry point
    "prepare_packet_for_ingest",
]
