"""ChunkView — virtual chunking layer for retrieved memory payloads.

Normalizes payloads into deterministic, content-addressed chunk units for
consistent ranking and downstream summarization. No DB migration required.

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "ChunkView",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 64
MIN_CHUNK_LENGTH = 32


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """A single content-addressed chunk derived from a memory payload."""

    chunk_id: str
    content: str
    source_packet_id: str
    offset: int
    length: int
    tier: str = ""
    score: float = 0.0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )

    @staticmethod
    def compute_id(content: str, source_packet_id: str, offset: int) -> str:
        """Content-addressed chunk ID using SHA-256."""
        payload = f"{source_packet_id}:{offset}:{content}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ChunkConfig:
    """Configuration for the chunking algorithm."""

    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP
    min_length: int = MIN_CHUNK_LENGTH


# ---------------------------------------------------------------------------
# ChunkView
# ---------------------------------------------------------------------------


class ChunkView:
    """Virtual chunking layer — deterministic, rule-based in Phase 1.

    Splits text payloads into overlapping windows of fixed size. Each chunk
    gets a content-addressed ID for deduplication and stable references.
    """

    def __init__(self, *, config: ChunkConfig | None = None) -> None:
        self._cfg = config or ChunkConfig()
        logger.info(
            "chunk_view_initialized",
            chunk_size=self._cfg.chunk_size,
            overlap=self._cfg.overlap,
        )

    def chunk_text(
        self,
        text: str,
        *,
        source_packet_id: str = "",
        tier: str = "",
        score: float = 0.0,
    ) -> list[Chunk]:
        """Split text into overlapping chunks."""
        if not text or len(text.strip()) < self._cfg.min_length:
            return []

        chunks: list[Chunk] = []
        step = max(self._cfg.chunk_size - self._cfg.overlap, 1)
        offset = 0

        while offset < len(text):
            end = min(offset + self._cfg.chunk_size, len(text))
            segment = text[offset:end].strip()
            if len(segment) >= self._cfg.min_length:
                chunk_id = Chunk.compute_id(segment, source_packet_id, offset)
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        content=segment,
                        source_packet_id=source_packet_id,
                        offset=offset,
                        length=len(segment),
                        tier=tier,
                        score=score,
                    ),
                )
            offset += step

        logger.debug(
            "chunk_view_split",
            source_packet_id=source_packet_id,
            input_length=len(text),
            chunk_count=len(chunks),
        )
        return chunks

    def chunk_payloads(
        self,
        payloads: list[dict[str, Any]],
    ) -> list[Chunk]:
        """Chunk a batch of retrieved payloads.

        Each payload dict must contain 'content' (str) and optionally
        'packet_id', 'tier', 'score'.
        """
        all_chunks: list[Chunk] = []
        for payload in payloads:
            content = str(payload.get("content", ""))
            packet_id = str(payload.get("packet_id", ""))
            tier = str(payload.get("tier", ""))
            score = float(payload.get("score", 0.0))
            all_chunks.extend(
                self.chunk_text(
                    content,
                    source_packet_id=packet_id,
                    tier=tier,
                    score=score,
                ),
            )

        # Deduplicate by chunk_id, keeping first occurrence
        seen: set[str] = set()
        deduped: list[Chunk] = []
        for chunk in all_chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                deduped.append(chunk)

        return deduped


__all__ = [
    "Chunk",
    "ChunkConfig",
    "ChunkView",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
