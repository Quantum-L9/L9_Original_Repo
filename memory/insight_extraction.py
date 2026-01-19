"""
L9 Memory Substrate - Insight Extraction Pipeline
Version: 1.1.0

Heuristic insight extraction (no ML dependencies):
- Basic insight rule matching
- Entity extraction from payloads
- Inference detection from reasoning blocks
- Knowledge fact generation and storage
- Source packet linking

All operations are async-safe with proper logging.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Insight Extraction Pipeline",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "insight_extraction",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["core.singleton_registry", "memory.__init__"],
    },
}
# ============================================================================

import structlog
import re
from functools import lru_cache
from typing import Any
from uuid import UUID

from core.schemas import PacketEnvelope
from memory.substrate_models import ExtractedInsight, KnowledgeFact

logger = structlog.get_logger(__name__)


# =============================================================================
# Insight Rule Definitions
# =============================================================================

# Patterns that suggest conclusive statements
CONCLUSION_PATTERNS = [
    r"therefore[,:]?\s+(.+)",
    r"in conclusion[,:]?\s+(.+)",
    r"as a result[,:]?\s+(.+)",
    r"this means[,:]?\s+(.+)",
    r"indicates that\s+(.+)",
    r"suggests that\s+(.+)",
    r"we can conclude[,:]?\s+(.+)",
]

# Patterns that suggest entity mentions
ENTITY_PATTERNS = [
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",  # Capitalized phrases
    r"\b(the\s+\w+)\s+(?:is|was|has|have)",  # "the X is/was..."
]

# Patterns for numeric facts
FACT_PATTERNS = [
    r"(\w+)\s+(?:is|was|equals?|=)\s+(\d+(?:\.\d+)?)",
    r"(\w+):\s*(\d+(?:\.\d+)?)",
    r"has\s+(\d+)\s+(\w+)",
]


class InsightExtractionPipeline:
    """
    Heuristic insight extraction from packet content.

    Extracts:
    - Conclusions and inferences
    - Entities and relationships
    - Numeric facts and measurements
    - Patterns and anomalies
    """

    def __init__(self, repository=None):
        """
        Initialize insight extraction pipeline.

        Args:
            repository: SubstrateRepository instance for storing insights
        """
        self._repository = repository
        self._stats = {
            "packets_processed": 0,
            "insights_extracted": 0,
            "facts_extracted": 0,
        }
        logger.info("InsightExtractionPipeline initialized")

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    @property
    def stats(self) -> dict[str, int]:
        """Return extraction statistics."""
        return self._stats.copy()

    async def extract_from_packet(
        self,
        envelope: PacketEnvelope,
        store_results: bool = True,
    ) -> dict[str, Any]:
        """
        Extract insights and facts from a packet.

        Args:
            envelope: PacketEnvelope to process
            store_results: Whether to persist extracted items

        Returns:
            Dict with extracted insights and facts
        """
        logger.debug(f"Extracting insights from packet {envelope.packet_id}")

        self._stats["packets_processed"] += 1

        insights = []
        facts = []

        # Extract from payload
        payload_insights, payload_facts = self._extract_from_payload(envelope)
        insights.extend(payload_insights)
        facts.extend(payload_facts)

        # Extract from reasoning block
        if envelope.reasoning_block:
            reasoning_insights, reasoning_facts = self._extract_from_reasoning(
                envelope.reasoning_block,
                envelope.packet_id,
            )
            insights.extend(reasoning_insights)
            facts.extend(reasoning_facts)

        # Store results if requested
        if store_results and self._repository:
            await self._store_insights(insights, envelope.packet_id)
            await self._store_facts(facts)

        self._stats["insights_extracted"] += len(insights)
        self._stats["facts_extracted"] += len(facts)

        return {
            "packet_id": str(envelope.packet_id),
            "insights": [i.model_dump(mode="json") for i in insights],
            "facts": [f.model_dump(mode="json") for f in facts],
        }

    def _extract_from_payload(
        self,
        envelope: PacketEnvelope,
    ) -> tuple[list[ExtractedInsight], list[KnowledgeFact]]:
        """Extract insights and facts from packet payload."""
        insights = []
        facts = []
        payload = envelope.payload
        packet_id = envelope.packet_id

        # Extract text content
        text_content = (
            payload.get("text")
            or payload.get("content")
            or payload.get("description")
            or payload.get("message")
            or ""
        )

        if isinstance(text_content, str) and len(text_content) > 20:
            # Extract conclusions
            for pattern in CONCLUSION_PATTERNS:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    insights.append(
                        ExtractedInsight(
                            insight_type="conclusion",
                            content=match.strip()[:500],
                            entities=self._extract_entities(match),
                            confidence=0.7,
                            source_packet=packet_id,
                            trigger_world_model=True,
                        )
                    )

            # Extract entities
            entities = self._extract_entities(text_content)
            if entities:
                insights.append(
                    ExtractedInsight(
                        insight_type="pattern",
                        content=f"Detected entities: {', '.join(entities[:10])}",
                        entities=entities[:10],
                        confidence=0.6,
                        source_packet=packet_id,
                        trigger_world_model=False,
                    )
                )

        # Extract structured facts from payload keys
        for key, value in payload.items():
            if key in ("id", "timestamp", "created_at", "updated_at"):
                continue

            # Skip complex objects
            if isinstance(value, (dict, list)) and len(str(value)) > 200:
                continue

            # Create fact from key-value pair
            subject = (
                payload.get("entity")
                or payload.get("name")
                or payload.get("subject")
                or envelope.packet_type
            )

            facts.append(
                KnowledgeFact(
                    subject=str(subject),
                    predicate=key,
                    object=value,
                    confidence=0.8,
                    source_packet=packet_id,
                )
            )

        # Extract numeric facts from text
        if isinstance(text_content, str):
            for pattern in FACT_PATTERNS:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        facts.append(
                            KnowledgeFact(
                                subject=match[0],
                                predicate="value",
                                object=match[1],
                                confidence=0.7,
                                source_packet=packet_id,
                            )
                        )

        return insights, facts

    def _extract_from_reasoning(
        self,
        reasoning_block: dict[str, Any],
        packet_id: UUID,
    ) -> tuple[list[ExtractedInsight], list[KnowledgeFact]]:
        """Extract insights from reasoning block."""
        insights = []
        facts = []

        # Extract from decision tokens
        decision_tokens = reasoning_block.get("decision_tokens", [])
        confidence_scores = reasoning_block.get("confidence_scores", {})

        for token in decision_tokens:
            if ":" in token:
                key, value = token.split(":", 1)
                key = key.strip()
                value = value.strip()

                # High-confidence decisions become insights
                confidence = confidence_scores.get(
                    key, confidence_scores.get("routing", 0.7)
                )

                if confidence >= 0.7:
                    insights.append(
                        ExtractedInsight(
                            insight_type="conclusion",
                            content=f"Decision: {key} = {value}",
                            entities=[],
                            confidence=confidence,
                            source_packet=packet_id,
                            trigger_world_model=key
                            in ("action", "route_to", "update_model"),
                        )
                    )

        # Extract from inference steps
        inference_steps = reasoning_block.get("inference_steps", [])

        for step in inference_steps:
            if isinstance(step, dict):
                action = step.get("action", "")
                result = step.get("result", "")

                if action and result:
                    facts.append(
                        KnowledgeFact(
                            subject="reasoning",
                            predicate=action,
                            object=result,
                            confidence=0.8,
                            source_packet=packet_id,
                        )
                    )

        # Extract from extracted features
        features = reasoning_block.get("extracted_features", {})

        for key, value in features.items():
            facts.append(
                KnowledgeFact(
                    subject="packet",
                    predicate=key,
                    object=value,
                    confidence=0.9,
                    source_packet=packet_id,
                )
            )

        return insights, facts

    def _extract_entities(self, text: str) -> list[str]:
        """Extract entity mentions from text."""
        entities = set()

        for pattern in ENTITY_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, str) and 2 < len(match) < 50:
                    # Filter out common words
                    if match.lower() not in ("the", "this", "that", "these", "those"):
                        entities.add(match)

        return list(entities)[:20]

    async def _store_insights(
        self,
        insights: list[ExtractedInsight],
        source_packet: UUID,
    ) -> None:
        """Store extracted insights as insight packets."""
        if not insights or not self._repository:
            return

        for insight in insights:
            # Store insight as a packet
            from core.schemas import PacketEnvelope, PacketMetadata

            insight_packet = PacketEnvelope(
                packet_type="insight",
                payload={
                    "insight_id": str(insight.insight_id),
                    "insight_type": insight.insight_type,
                    "content": insight.content,
                    "entities": insight.entities,
                    "confidence": insight.confidence,
                    "source_packet": str(source_packet),
                    "trigger_world_model": insight.trigger_world_model,
                },
                metadata=PacketMetadata(
                    schema_version="1.1.0",
                    agent="insight_extractor",
                ),
                lineage=None,
            )

            try:
                await self._repository.insert_packet(insight_packet)
            except Exception as e:
                logger.error(f"Failed to store insight: {e}")

    async def _store_facts(self, facts: list[KnowledgeFact]) -> None:
        """Store extracted facts to knowledge_facts table."""
        if not facts or not self._repository:
            return

        for fact in facts:
            try:
                await self._repository.insert_knowledge_fact(
                    subject=fact.subject,
                    predicate=fact.predicate,
                    object_value=fact.object,
                    confidence=fact.confidence,
                    source_packet=fact.source_packet,
                    fact_id=str(fact.fact_id),
                )
            except Exception as e:
                logger.error(f"Failed to store fact: {e}")

    async def detect_anomalies(
        self,
        packet: PacketEnvelope,
        historical_window: int = 100,
    ) -> list[ExtractedInsight]:
        """
        Detect anomalies by comparing packet to recent history.

        Simple heuristics:
        - Unusual packet types
        - High deviation from average confidence
        - Unusually large payloads

        Args:
            packet: Current packet to analyze
            historical_window: Number of recent packets to compare

        Returns:
            List of anomaly insights
        """
        anomalies = []

        if not self._repository:
            return anomalies

        # Get recent packet stats
        async with self._repository.acquire() as conn:
            # Get packet type distribution
            type_counts = await conn.fetch(
                """
                SELECT packet_type, COUNT(*) as count
                FROM packet_store
                ORDER BY timestamp DESC
                LIMIT $1
                """,
                historical_window,
            )

            type_dist = {r["packet_type"]: r["count"] for r in type_counts}
            total = sum(type_dist.values())

            # Check if current packet type is rare
            current_type_count = type_dist.get(packet.packet_type, 0)
            if total > 10 and current_type_count < total * 0.05:
                anomalies.append(
                    ExtractedInsight(
                        insight_type="anomaly",
                        content=f"Rare packet type detected: {packet.packet_type}",
                        entities=[packet.packet_type],
                        confidence=0.8,
                        source_packet=packet.packet_id,
                        trigger_world_model=True,
                    )
                )

        # Check payload size
        payload_size = len(str(packet.payload))
        if payload_size > 10000:
            anomalies.append(
                ExtractedInsight(
                    insight_type="anomaly",
                    content=f"Large payload detected: {payload_size} bytes",
                    entities=[],
                    confidence=0.6,
                    source_packet=packet.packet_id,
                    trigger_world_model=False,
                )
            )

        return anomalies


# =============================================================================
# Singleton / Factory
# =============================================================================


@lru_cache(maxsize=1)
def get_insight_pipeline() -> InsightExtractionPipeline:
    """Get or create the insight extraction pipeline singleton. CACHED."""
    return InsightExtractionPipeline()


def init_insight_pipeline(repository) -> InsightExtractionPipeline:
    """Initialize the insight extraction pipeline with a repository."""
    pipeline = get_insight_pipeline()
    pipeline.set_repository(repository)
    return pipeline


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-050",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_models"],
    "tags": [
        "api",
        "async",
        "caching",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "service",
    ],
    "keywords": [
        "anomalies",
        "detect",
        "detection",
        "extract",
        "extraction",
        "heuristic",
        "insight",
        "memory",
    ],
    "business_value": "Implements InsightExtractionPipeline for insight extraction functionality",
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
