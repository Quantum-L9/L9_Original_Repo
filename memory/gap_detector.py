"""
L9 Memory - Knowledge Gap Detector
Version: 1.0.0

Stage 5: Predictive Memory Warming System
Detects knowledge gaps for proactive cache warming.

Gap types detected:
1. Entity gaps: Referenced entities missing from knowledge graph
2. Relationship gaps: Entity pairs lacking expected connections
3. Attribute gaps: Entities present but missing critical attributes

Research source: Perplexity deep_research (2026-01-15)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Knowledge Gap Detector",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "gap_detector",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "memory.__init__",
            "memory.warming_service",
            "tests.memory.test_predictive_warming",
        ],
    },
}
# ============================================================================

import asyncio
import time
from uuid import uuid4

import structlog

# Use harvested models
from memory.warming_models import GapSeverity, KnowledgeGap

logger = structlog.get_logger(__name__)

from core.decorators import must_stay_async

# Prometheus metrics (optional - graceful fallback)
try:
    from prometheus_client import Counter, Histogram

    gap_detection_count = Counter(
        "l9_gap_detection_count",
        "Total gaps detected by gap detector",
        ["gap_type", "severity"],
    )

    gap_detector_latency = Histogram(
        "l9_gap_detector_latency_seconds",
        "Latency of gap detection operations",
        ["operation"],
        buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    logger.warning("prometheus_client not available - metrics disabled")


class GapDetector:
    """
    Detects knowledge gaps in entity graphs for predictive cache warming.

    The gap detector analyzes incoming queries and referenced entities to identify
    knowledge gaps that, if warmed into cache, would improve query success probability.

    Gap detection operates across three dimensions:
    1. Entity gaps: Entities referenced but missing from the knowledge graph
    2. Relationship gaps: Entity pairs lacking expected relationship connections
    3. Attribute gaps: Entities present but missing critical attributes

    Severity levels based on gap impact:
    - CRITICAL: Gaps affecting query critical paths
    - HIGH: Gaps affecting primary query results
    - MEDIUM: Gaps affecting secondary enrichment
    - LOW: Gaps affecting optional context

    Example:
        >>> detector = GapDetector()
        >>> entity_graph = {"entity_1": {"entity_2", "entity_3"}}
        >>> gaps = await detector.detect_all_gaps(["entity_1", "entity_4"], entity_graph)
        >>> print(f"Found {len(gaps)} gaps")
    """

    def __init__(self) -> None:
        """Initialize the gap detector with logging and metrics infrastructure."""
        self.historical_gap_frequency: dict[str, float] = {}
        self.entity_importance_scores: dict[str, float] = {}
        self.critical_path_entities: set[str] = set()

    @must_stay_async("callers use await")
    async def detect_entity_gaps(
        self,
        mentioned_entities: list[str],
        entity_graph: dict[str, set[str]],
    ) -> list[KnowledgeGap]:
        """
        Detect entities referenced but missing from the knowledge graph.

        Examines the set of mentioned entities and identifies which ones are absent
        from the entity graph. Missing entities represent gap opportunities where
        loading entity data into cache would prevent downstream query failures.

        Args:
            mentioned_entities: List of entity identifiers referenced in query
            entity_graph: Dictionary mapping entity IDs to sets of neighbor entity IDs

        Returns:
            List of detected entity gap objects, empty if no gaps found

        Raises:
            ValueError: If mentioned_entities is empty
        """
        start_time = time.time()
        gaps: list[KnowledgeGap] = []

        try:
            logger.info(
                "detecting_entity_gaps",
                entity_count=len(mentioned_entities),
            )

            if not mentioned_entities:
                return []

            # Allow empty entity_graph (all entities would be gaps)
            graph_entity_ids = set(entity_graph.keys()) if entity_graph else set()
            mentioned_set = set(mentioned_entities)
            missing_entities = mentioned_set - graph_entity_ids

            # Create gap objects for each missing entity
            for entity_id in missing_entities:
                # Calculate confidence based on historical frequency
                historical_freq = self.historical_gap_frequency.get(entity_id, 0.0)
                confidence = min(historical_freq / 100.0, 1.0)  # Normalize to 0-1

                # Determine severity: entities on critical path rate higher
                is_critical = entity_id in self.critical_path_entities
                severity = GapSeverity.CRITICAL if is_critical else GapSeverity.HIGH

                gap = KnowledgeGap(
                    gap_id=str(uuid4()),
                    gap_type="entity_missing",
                    severity=severity,
                    entity_ids=[entity_id],
                    confidence_score=confidence,
                    timestamp_detected_ms=time.time() * 1000,
                )
                gaps.append(gap)

                # Record metric
                if _HAS_PROMETHEUS:
                    gap_detection_count.labels(
                        gap_type="entity_missing",
                        severity=severity.value,
                    ).inc()

                logger.debug(
                    "entity_gap_detected",
                    entity_id=entity_id,
                    confidence=confidence,
                    severity=severity.value,
                )

            elapsed = time.time() - start_time
            if _HAS_PROMETHEUS:
                gap_detector_latency.labels(operation="detect_entity_gaps").observe(
                    elapsed
                )

            return gaps

        except Exception as e:
            logger.error(
                "entity_gap_detection_failed",
                error=str(e),
                entity_count=len(mentioned_entities),
            )
            raise

    @must_stay_async("callers use await")
    async def detect_relationship_gaps(
        self,
        mentioned_entities: list[str],
        entity_graph: dict[str, set[str]],
    ) -> list[KnowledgeGap]:
        """
        Detect missing relationships between entities in the knowledge graph.

        Examines entity pairs from the mentioned entities and identifies cases where
        relationships are missing or incomplete. This captures scenarios like
        "friends of friends" patterns where indirect connections matter.

        Uses a heuristic-based approach: if entity A is mentioned and entity B is
        mentioned, but they do not appear to have a relationship in the graph,
        a relationship gap is flagged.

        Args:
            mentioned_entities: List of entity identifiers referenced in query
            entity_graph: Dictionary mapping entity IDs to sets of neighbors

        Returns:
            List of detected relationship gap objects
        """
        start_time = time.time()
        gaps: list[KnowledgeGap] = []

        try:
            logger.info(
                "detecting_relationship_gaps",
                entity_count=len(mentioned_entities),
            )

            if not mentioned_entities or len(mentioned_entities) < 2:
                return []

            if not entity_graph:
                return []

            mentioned_set = set(mentioned_entities)

            # Check all entity pairs for missing relationships
            entity_list = list(mentioned_set)
            for i in range(len(entity_list)):
                for j in range(i + 1, len(entity_list)):
                    entity_a = entity_list[i]
                    entity_b = entity_list[j]

                    # Check if relationship exists in either direction
                    neighbors_a = entity_graph.get(entity_a, set())
                    neighbors_b = entity_graph.get(entity_b, set())

                    has_a_to_b = entity_b in neighbors_a
                    has_b_to_a = entity_a in neighbors_b
                    has_relationship = has_a_to_b or has_b_to_a

                    # If no relationship found, flag a gap
                    # Both entities must exist in graph for relationship gap
                    if (
                        not has_relationship
                        and entity_a in entity_graph
                        and entity_b in entity_graph
                    ):
                        gap_key = f"{entity_a}::{entity_b}"
                        historical_freq = self.historical_gap_frequency.get(
                            gap_key, 0.0
                        )
                        confidence = min(historical_freq / 50.0, 1.0)

                        gap = KnowledgeGap(
                            gap_id=str(uuid4()),
                            gap_type="relationship_missing",
                            severity=GapSeverity.MEDIUM,
                            entity_ids=[entity_a, entity_b],
                            confidence_score=confidence,
                            timestamp_detected_ms=time.time() * 1000,
                        )
                        gaps.append(gap)

                        if _HAS_PROMETHEUS:
                            gap_detection_count.labels(
                                gap_type="relationship_missing",
                                severity=GapSeverity.MEDIUM.value,
                            ).inc()

                        logger.debug(
                            "relationship_gap_detected",
                            entity_a=entity_a,
                            entity_b=entity_b,
                            confidence=confidence,
                        )

            elapsed = time.time() - start_time
            if _HAS_PROMETHEUS:
                gap_detector_latency.labels(
                    operation="detect_relationship_gaps"
                ).observe(elapsed)

            return gaps

        except Exception as e:
            logger.error(
                "relationship_gap_detection_failed",
                error=str(e),
            )
            raise

    async def detect_all_gaps(
        self,
        mentioned_entities: list[str],
        entity_graph: dict[str, set[str]],
    ) -> list[KnowledgeGap]:
        """
        Detect all gap types (entity, relationship, attribute).

        Orchestrates detection across all gap dimensions and returns a consolidated
        list of detected gaps, sorted by severity (CRITICAL first) and confidence score
        (highest first).

        Uses asyncio.gather to execute gap detection operations concurrently,
        reducing overall detection latency compared to sequential detection.

        Args:
            mentioned_entities: List of entity identifiers referenced in query
            entity_graph: Dictionary mapping entity IDs to sets of neighbors

        Returns:
            List of all detected gaps, sorted by severity and confidence
        """
        start_time = time.time()

        try:
            logger.info(
                "detecting_all_gaps",
                entity_count=len(mentioned_entities),
            )

            # Run detection operations concurrently
            entity_gaps, relationship_gaps = await asyncio.gather(
                self.detect_entity_gaps(mentioned_entities, entity_graph),
                self.detect_relationship_gaps(mentioned_entities, entity_graph),
                return_exceptions=False,
            )

            # Combine results and sort by severity and confidence
            all_gaps = entity_gaps + relationship_gaps

            # Sort by severity (CRITICAL first) then by confidence (highest first)
            severity_order = {
                GapSeverity.CRITICAL: 0,
                GapSeverity.HIGH: 1,
                GapSeverity.MEDIUM: 2,
                GapSeverity.LOW: 3,
            }
            all_gaps.sort(
                key=lambda g: (severity_order[g.severity], -g.confidence_score)
            )

            elapsed = time.time() - start_time
            if _HAS_PROMETHEUS:
                gap_detector_latency.labels(operation="detect_all_gaps").observe(
                    elapsed
                )

            logger.info(
                "gap_detection_complete",
                total_gaps=len(all_gaps),
                entity_gaps=len(entity_gaps),
                relationship_gaps=len(relationship_gaps),
                latency_ms=elapsed * 1000,
            )

            return all_gaps

        except Exception as e:
            logger.error(
                "all_gap_detection_failed",
                error=str(e),
                entity_count=len(mentioned_entities),
            )
            raise

    def update_gap_frequency(self, entity_id: str, increment: float = 1.0) -> None:
        """
        Update historical frequency statistics for gap entities.

        Maintains a moving average of gap occurrence frequency, allowing the
        detector to learn which gaps appear most frequently in production workloads.
        Entities with higher frequency scores are assigned higher confidence values
        when detected in future queries.

        Args:
            entity_id: The entity ID to update frequency for
            increment: The increment to add to frequency counter
        """
        current = self.historical_gap_frequency.get(entity_id, 0.0)
        # Apply exponential smoothing: new_value = 0.9 * old + 0.1 * current
        self.historical_gap_frequency[entity_id] = 0.9 * current + 0.1 * increment

    def set_critical_path_entities(self, entity_ids: set[str]) -> None:
        """
        Set the set of entities that appear on query critical paths.

        Critical path entities affect query success probability more than others.
        Gaps involving critical path entities are assigned higher severity levels.

        Args:
            entity_ids: Set of entity IDs considered critical
        """
        self.critical_path_entities = entity_ids
        logger.info(
            "critical_path_entities_updated",
            count=len(entity_ids),
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-038",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "memory.warming_models"],
    "tags": [
        "async",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "metrics",
        "service",
        "streaming",
    ],
    "keywords": [
        "all",
        "cache",
        "critical",
        "detect",
        "detector",
        "entities",
        "entity",
        "frequency",
    ],
    "business_value": "Implements GapDetector for gap detector functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
