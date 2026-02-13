"""
L9 Memory — Unified Entity Extraction Service.

Replaces three divergent implementations:
1. enrichment_dag.py::_extract_entities() — dead stub returning []
2. substrate_dag.py::extract_insights_node() — heuristic key-value loop
3. hybrid_rag.py::EntityExtractor — regex + optional LLM

This module provides a single EntityExtractionService used by both
ingestion-time extraction (substrate_dag) and query-time extraction
(retrieval pipeline).
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "Unified Entity Extraction Service",
    "module_version": "1.0.0",
    "created_by": "L9_Pipeline_Unification",
    "created_at": "2026-02-12T20:00:00Z",
    "updated_at": "2026-02-12T20:00:00Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "entity_extraction",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.substrate_dag",
            "memory.retrieval",
            "memory.hybrid_rag",
        ],
    },
}

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ExtractedEntity:
    """A single extracted entity reference."""

    entity_type: str
    entity_id: str
    name: str
    confidence: float
    source: str  # "metadata", "pattern", "heuristic", "llm"
    properties: dict[str, Any] = field(default_factory=dict)


class EntityExtractionService:
    """
    Unified entity extraction from packet payloads and text.

    Extraction tiers (executed in order, results merged):
    1. Metadata extraction — high-confidence IDs from structured fields
    2. Pattern extraction — regex-based entity recognition
    3. Heuristic extraction — key-value pairs from payload structure
    4. LLM extraction — optional, for rich text analysis

    All tiers deduplicate by (entity_type, entity_id).
    """

    # Compiled patterns (class-level for reuse)
    _UUID_PATTERN = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )
    _SLACK_USER_PATTERN = re.compile(r"<@([A-Z0-9]+)>")
    _GMP_PATTERN = re.compile(r"GMP-(\d+)", re.IGNORECASE)
    _FILE_PATH_PATTERN = re.compile(r"(?:/[\w.-]+)+\.(?:py|ts|js|yaml|yml|json|md)")

    def __init__(
        self,
        use_llm: bool = False,
        llm_client: Any | None = None,
    ):
        """
        Initialize entity extraction service.

        Args:
            use_llm: Enable LLM-based extraction (Tier 4).
            llm_client: OpenAI-compatible async client.
        """
        self._use_llm = use_llm
        self._llm_client = llm_client

    async def extract(
        self,
        text: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata_context: dict[str, Any] | None = None,
    ) -> list[ExtractedEntity]:
        """
        Extract entities from text, payload structure, and metadata.

        Args:
            text: Free-text content to analyze.
            payload: Structured packet payload dict.
            metadata_context: Packet metadata (agent_id, source_id, thread_id).

        Returns:
            Deduplicated list of ExtractedEntity objects, sorted by confidence desc.
        """
        entities: list[ExtractedEntity] = []

        # Tier 1: Metadata extraction (highest confidence)
        if metadata_context:
            entities.extend(self._extract_from_metadata(metadata_context))

        # Tier 2: Pattern extraction from text
        if text:
            entities.extend(self._extract_by_patterns(text))

        # Tier 3: Heuristic extraction from payload structure
        if payload:
            entities.extend(self._extract_from_payload_structure(payload))

        # Tier 4: LLM extraction (optional)
        if self._use_llm and self._llm_client and text:
            llm_entities = await self._extract_with_llm(text)
            entities.extend(llm_entities)

        # Deduplicate by (entity_type, entity_id)
        seen: set[tuple[str, str]] = set()
        unique: list[ExtractedEntity] = []
        for entity in entities:
            key = (entity.entity_type, entity.entity_id)
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        # Sort by confidence descending
        unique.sort(key=lambda e: e.confidence, reverse=True)

        return unique

    def _extract_from_metadata(
        self,
        context: dict[str, Any],
    ) -> list[ExtractedEntity]:
        """Tier 1: Extract from structured metadata fields."""
        entities: list[ExtractedEntity] = []

        if agent_id := context.get("agent_id") or context.get("agent"):
            entities.append(
                ExtractedEntity(
                    entity_type="Agent",
                    entity_id=str(agent_id),
                    name=str(agent_id),
                    confidence=1.0,
                    source="metadata",
                )
            )

        if source_id := context.get("source_id"):
            source_str = str(source_id)
            etype = "User" if source_str.startswith("user:") else "System"
            entities.append(
                ExtractedEntity(
                    entity_type=etype,
                    entity_id=source_str,
                    name=source_str,
                    confidence=1.0,
                    source="metadata",
                )
            )

        if thread_id := context.get("thread_id"):
            entities.append(
                ExtractedEntity(
                    entity_type="Thread",
                    entity_id=str(thread_id),
                    name=f"Thread:{str(thread_id)[:8]}",
                    confidence=1.0,
                    source="metadata",
                )
            )

        return entities

    def _extract_by_patterns(self, text: str) -> list[ExtractedEntity]:
        """Tier 2: Regex-based entity recognition."""
        entities: list[ExtractedEntity] = []

        for match in self._UUID_PATTERN.finditer(text):
            entities.append(
                ExtractedEntity(
                    entity_type="Entity",
                    entity_id=match.group(),
                    name=f"Entity:{match.group()[:8]}",
                    confidence=0.7,
                    source="pattern",
                )
            )

        for match in self._SLACK_USER_PATTERN.finditer(text):
            entities.append(
                ExtractedEntity(
                    entity_type="User",
                    entity_id=f"slack:{match.group(1)}",
                    name=f"Slack User {match.group(1)}",
                    confidence=0.9,
                    source="pattern",
                )
            )

        for match in self._GMP_PATTERN.finditer(text):
            entities.append(
                ExtractedEntity(
                    entity_type="GMP",
                    entity_id=f"gmp-{match.group(1)}",
                    name=f"GMP-{match.group(1)}",
                    confidence=0.95,
                    source="pattern",
                )
            )

        for match in self._FILE_PATH_PATTERN.finditer(text):
            entities.append(
                ExtractedEntity(
                    entity_type="File",
                    entity_id=match.group(),
                    name=match.group().split("/")[-1],
                    confidence=0.8,
                    source="pattern",
                )
            )

        return entities

    def _extract_from_payload_structure(
        self,
        payload: dict[str, Any],
    ) -> list[ExtractedEntity]:
        """Tier 3: Heuristic extraction from structured payload keys."""
        entities: list[ExtractedEntity] = []
        skip_keys = {"id", "timestamp", "created_at", "updated_at", "packet_id"}

        for key, value in payload.items():
            if key in skip_keys:
                continue
            if isinstance(value, dict) and len(str(value)) > 500:
                continue

            subject = (
                payload.get("subject")
                or payload.get("entity")
                or payload.get("name")
                or key
            )
            object_value = str(value) if isinstance(value, UUID) else value

            entities.append(
                ExtractedEntity(
                    entity_type="Fact",
                    entity_id=f"{subject}:{key}",
                    name=f"{subject}.{key}",
                    confidence=0.6,
                    source="heuristic",
                    properties={"predicate": key, "object": object_value},
                )
            )

        return entities

    async def _extract_with_llm(self, text: str) -> list[ExtractedEntity]:
        """Tier 4: LLM-based entity extraction."""
        if not self._llm_client:
            return []

        try:
            import json

            response = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract named entities from text. Return JSON: "
                            '{"entities": [{"type": "Person|Organization|Tool|Concept|Event", '
                            '"id": "unique_id", "name": "display_name", '
                            '"confidence": 0.0-1.0}]}\n'
                            "Be conservative — only extract clearly identifiable entities."
                        ),
                    },
                    {"role": "user", "content": text[:2000]},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            result = json.loads(content)

            return [
                ExtractedEntity(
                    entity_type=e.get("type", "Unknown"),
                    entity_id=e.get("id", ""),
                    name=e.get("name", ""),
                    confidence=float(e.get("confidence", 0.7)),
                    source="llm",
                )
                for e in result.get("entities", [])
                if e.get("id")
            ]
        except Exception as e:
            logger.warning("LLM entity extraction failed", error=str(e))
            return []


__all__ = [
    "EntityExtractionService",
    "ExtractedEntity",
]
