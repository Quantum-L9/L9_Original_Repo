"""
L9 Memory Substrate - Audit Utilities
Version: 1.0.0

Helpers for audit-mode normalization, redaction, hashing, and injection detection.
Designed to be unit-testable and async-compatible (pure functions).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID, NAMESPACE_URL, uuid5

from memory.substrate_models import PacketEnvelopeIn, PacketMetadata

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF]")
WHITESPACE_RE = re.compile(r"\s+")

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{7,}\d"),
    "api_key": re.compile(r"(?:sk-|api_key=)[A-Za-z0-9]{8,}"),
}

INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "disregard above",
    "system prompt",
    "developer message",
    "tool output",
    "jailbreak",
    "override instruction",
)


@dataclass(frozen=True)
class AuditReport:
    """Audit findings for a packet ingestion attempt."""

    packet_id: UUID
    content_hash: str
    checksum_raw: str
    redaction_count: int
    pii_types: tuple[str, ...]
    injection_markers: tuple[str, ...]


def normalize_text(text: str) -> str:
    """Normalize text using NFC, strip zero-width chars, and collapse whitespace."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def normalize_payload(value: Any) -> Any:
    """Recursively normalize string values inside payload structures."""
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: normalize_payload(val) for key, val in value.items()}
    return value


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_stable_json_dumps(value).encode("utf-8")).hexdigest()


def extract_strings(payload: Any) -> Iterable[str]:
    """Yield all string values from a payload for scanning."""
    if isinstance(payload, str):
        yield payload
    elif isinstance(payload, dict):
        for item in payload.values():
            yield from extract_strings(item)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            yield from extract_strings(item)


def detect_injection_markers(payload: Any) -> tuple[str, ...]:
    """Detect prompt injection markers in payload string values."""
    markers = set()
    for text in extract_strings(payload):
        lowered = text.lower()
        for marker in INJECTION_MARKERS:
            if marker in lowered:
                markers.add(marker)
    return tuple(sorted(markers))


def detect_pii_types(payload: Any) -> tuple[str, ...]:
    """Detect PII categories in payload string values."""
    types = set()
    for text in extract_strings(payload):
        for name, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                types.add(name)
    return tuple(sorted(types))


def redact_pii(payload: Any) -> tuple[Any, int, tuple[str, ...]]:
    """Redact PII in payload, returning updated payload, redaction count, and types."""
    redaction_count = 0
    pii_types = set()

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


def compute_content_hash(payload: Any, metadata_projection: dict[str, Any]) -> str:
    """Compute SHA256 over normalized payload + metadata projection."""
    return _hash_payload({"payload": payload, "metadata": metadata_projection})


def prepare_packet_for_ingest(packet_in: PacketEnvelopeIn) -> tuple[PacketEnvelopeIn, AuditReport]:
    """
    Normalize, redact, and enrich a PacketEnvelopeIn for audit-mode ingestion.

    - Normalizes payload strings
    - Redacts detected PII
    - Computes content hashes
    - Assigns deterministic packet_id if missing
    """
    normalized_payload = normalize_payload(packet_in.payload)
    checksum_raw = _hash_payload(normalized_payload)
    redacted_payload, redaction_count, pii_types = redact_pii(normalized_payload)
    injection_markers = detect_injection_markers(redacted_payload)

    metadata = packet_in.metadata or PacketMetadata()
    metadata_projection = metadata.model_dump()
    for key in ("content_hash", "checksum_raw", "redaction_count", "pii_types", "injection_markers"):
        metadata_projection.pop(key, None)

    content_hash = compute_content_hash(redacted_payload, metadata_projection)
    packet_id = packet_in.packet_id or uuid5(NAMESPACE_URL, content_hash)

    enriched_metadata = PacketMetadata(
        **{
            **metadata_projection,
            "content_hash": content_hash,
            "checksum_raw": checksum_raw,
            "redaction_count": redaction_count,
            "pii_types": list(pii_types),
            "injection_markers": list(injection_markers),
        }
    )

    prepared = packet_in.model_copy(
        update={
            "packet_id": packet_id,
            "payload": redacted_payload,
            "metadata": enriched_metadata,
        }
    )

    report = AuditReport(
        packet_id=packet_id,
        content_hash=content_hash,
        checksum_raw=checksum_raw,
        redaction_count=redaction_count,
        pii_types=pii_types,
        injection_markers=injection_markers,
    )

    return prepared, report
