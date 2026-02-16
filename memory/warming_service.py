"""
L9 Memory - Warming Service Orchestrator
Version: 1.0.0

Stage 5: Predictive Memory Warming System
Orchestrates gap detection and predictive caching for AI agent memory.

The service coordinates between:
- GapDetector: Identifies missing entities and relationships
- PredictiveCache: Preloads data into Redis and L1 cache

This implements the Memory phase of the Action-Think-Memory-Refine cycle.

Research source: Perplexity deep_research (2026-01-15)
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Warming Service Orchestrator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "warming_service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "core.agents.executor",
            "memory.__init__",
            "tests.memory.test_predictive_warming",
        ],
    },
}
# ============================================================================

import time
from typing import Any

import structlog

# Import L9 components
from memory.gap_detector import GapDetector
from memory.predictive_cache import PredictiveCache

# Use harvested models
from memory.warming_models import MemoryContext, PredictiveCacheConfig

logger = structlog.get_logger(__name__)

# Prometheus metrics (optional - graceful fallback)
try:
    from prometheus_client import Counter, Histogram

    warming_service_calls = Counter(
        "l9_warming_service_calls_total",
        "Total warming service calls",
        ["operation", "status"],
    )

    warming_service_latency = Histogram(
        "l9_warming_service_latency_seconds",
        "Warming service operation latency",
        ["operation"],
        buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    )

    entities_warmed_total = Counter(
        "l9_entities_warmed_total",
        "Total entities warmed into cache",
    )

    gaps_addressed = Counter(
        "l9_gaps_addressed_total",
        "Total knowledge gaps addressed by warming",
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    logger.warning("prometheus_client not available - metrics disabled")


class MemoryWarmingService:
    """
    Orchestrates predictive memory warming for AI agent operating systems.

    The memory warming service combines knowledge gap detection with predictive
    caching to proactively warm agent memory before query execution. By analyzing
    incoming queries and their referenced entities, the service identifies likely
    knowledge gaps and preloads relevant entity data into cache.

    The service operates through three phases:
    1. Gap Detection: Identifies missing entities, relationships, and attributes
    2. Prioritization: Ranks gaps by severity and confidence
    3. Cache Warming: Preloads top-priority gaps into Redis and L1 cache

    Attributes:
        gap_detector: GapDetector instance for gap identification
        cache: PredictiveCache instance for data preloading
        entity_graph: In-memory representation of knowledge graph structure

    Example:
        >>> service = MemoryWarmingService()
        >>> await service.initialize()
        >>> service.set_entity_graph({"entity_1": {"entity_2", "entity_3"}})
        >>> result = await service.warm_for_query(
        ...     query="Find entity_1 relationships",
        ...     mentioned_entities=["entity_1", "entity_4"],
        ... )
        >>> print(f"Warmed {result['entities_warmed']} entities")
    """

    def __init__(
        self,
        gap_detector: GapDetector | None = None,
        cache: PredictiveCache | None = None,
        config: PredictiveCacheConfig | None = None,
        graph_client: Any | None = None,
    ) -> None:
        """
        Initialize the memory warming service.

        Args:
            gap_detector: Configured GapDetector instance (created if None)
            cache: Initialized PredictiveCache instance (created if None)
            config: Cache configuration (uses defaults if None)
            graph_client: Optional Neo4j graph client for traversal
        """
        self.gap_detector = gap_detector or GapDetector()
        self.cache = cache or PredictiveCache(
            config=config or PredictiveCacheConfig(),
            graph_client=graph_client,
        )
        self.entity_graph: dict[str, set[str]] = {}
        self._warming_history: dict[str, float] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the warming service and all components.

        Initializes the cache layer and sets up initial entity graph state.
        """
        try:
            await self.cache.initialize()
            self._initialized = True
            logger.info("warming_service_initialized")
        except Exception as e:
            logger.error(
                "warming_service_initialization_failed",
                error=str(e),
            )
            raise

    @must_stay_async("callers use await")
    async def warm_for_query(
        self,
        query: str,
        mentioned_entities: list[str],
        max_gaps_to_warm: int = 10,
    ) -> dict[str, Any]:
        """
        Warm memory for an incoming query.

        Detects knowledge gaps in the query's entity references, prioritizes
        them by severity and confidence, and preloads top gaps into cache.

        This method represents the main entry point for the warming service.
        It coordinates between gap detection and cache warming to prepare the
        agent's memory for query execution.

        Args:
            query: The incoming query text
            mentioned_entities: List of entity IDs referenced in query
            max_gaps_to_warm: Maximum number of gaps to address

        Returns:
            Dictionary containing:
                - gaps_detected: Count of detected gaps
                - gaps_addressed: Count of gaps actually warmed
                - entities_warmed: Count of entity IDs warmed to cache
                - warming_latency_ms: Total warming operation time
                - cache_metrics: Current cache hit/miss statistics
        """
        start_time = time.time()
        warmed_entities: list[str] = []
        gaps_to_address = 0

        try:
            logger.info(
                "warming_for_query",
                query_preview=query[:100] if len(query) > 100 else query,
                entity_count=len(mentioned_entities),
            )

            # Phase 1: Detect gaps
            detected_gaps = await self.gap_detector.detect_all_gaps(
                mentioned_entities,
                self.entity_graph,
            )

            logger.info(
                "gaps_detected",
                total_gaps=len(detected_gaps),
                critical=sum(
                    1 for g in detected_gaps if g.severity.value == "critical"
                ),
                high=sum(1 for g in detected_gaps if g.severity.value == "high"),
            )

            # Phase 2: Prioritize and select gaps to warm
            gaps_to_warm = detected_gaps[:max_gaps_to_warm]
            gaps_to_address = len(gaps_to_warm)

            # Extract entity IDs from gaps
            entity_ids_to_warm: set[str] = set()
            for gap in gaps_to_warm:
                entity_ids_to_warm.update(gap.entity_ids)

            entity_ids_list = list(entity_ids_to_warm)

            # Phase 3: Warm entities into cache
            if entity_ids_list:
                warmed_entries = await self.cache.warm_entities(entity_ids_list)
                warmed_entities = [e.entity_id for e in warmed_entries]

                # Update warming frequency statistics
                for entity_id in warmed_entities:
                    current = self._warming_history.get(entity_id, 0.0)
                    self._warming_history[entity_id] = current + 1.0

                    # Update gap detector's frequency statistics
                    self.gap_detector.update_gap_frequency(entity_id, current + 1.0)

                if _HAS_PROMETHEUS:
                    entities_warmed_total.inc(len(warmed_entities))
                    gaps_addressed.inc(gaps_to_address)

            elapsed = time.time() - start_time
            if _HAS_PROMETHEUS:
                warming_service_latency.labels(operation="warm_for_query").observe(
                    elapsed
                )
                warming_service_calls.labels(
                    operation="warm_for_query",
                    status="success",
                ).inc()

            result = {
                "gaps_detected": len(detected_gaps),
                "gaps_addressed": gaps_to_address,
                "entities_warmed": len(warmed_entities),
                "warming_latency_ms": elapsed * 1000,
                "cache_metrics": self._format_cache_metrics(),
            }

            logger.info(
                "query_warming_complete",
                gaps_detected=len(detected_gaps),
                gaps_addressed=gaps_to_address,
                entities_warmed=len(warmed_entities),
                latency_ms=elapsed * 1000,
            )

            return result

        except Exception as e:
            if _HAS_PROMETHEUS:
                warming_service_calls.labels(
                    operation="warm_for_query",
                    status="failure",
                ).inc()

            logger.error(
                "query_warming_failed",
                error=str(e),
                entity_count=len(mentioned_entities),
            )

            return {
                "gaps_detected": 0,
                "gaps_addressed": gaps_to_address,
                "entities_warmed": 0,
                "warming_latency_ms": (time.time() - start_time) * 1000,
                "error": str(e),
            }

    @must_stay_async("callers use await")
    async def get_warmed_context(
        self,
        entity_ids: list[str],
    ) -> MemoryContext:
        """
        Retrieve warmed context for specified entities.

        Fetches cached subgraph data for entities and builds a MemoryContext
        containing all retrieved entities and their relationships.

        Args:
            entity_ids: List of entity IDs to retrieve context for

        Returns:
            MemoryContext with retrieved entities and relationships
        """
        start_time = time.time()
        retrieved_entities: dict[str, Any] = {}
        entity_relationships: dict[str, set[str]] = {}
        hits = 0
        misses = 0

        for entity_id in entity_ids:
            cached = await self.cache.get_cached(entity_id)
            if cached is not None:
                hits += 1
                retrieved_entities[entity_id] = cached.neighbors
                entity_relationships[entity_id] = set(cached.neighbors.keys())
            else:
                misses += 1

        cache_hit_ratio = hits / (hits + misses) if (hits + misses) > 0 else 0.0
        warming_latency_ms = (time.time() - start_time) * 1000

        return MemoryContext(
            retrieved_entities=retrieved_entities,
            entity_relationships=entity_relationships,
            cache_hit_ratio=cache_hit_ratio,
            warming_latency_ms=warming_latency_ms,
        )

    def set_entity_graph(self, entity_graph: dict[str, set[str]]) -> None:
        """
        Update the entity graph used for gap detection.

        The entity graph maps each entity ID to the set of its neighbor entity IDs.
        This structure enables efficient gap detection by checking which entities
        and relationships exist in the knowledge graph.

        Args:
            entity_graph: Dictionary mapping entity IDs to neighbor sets
        """
        self.entity_graph = entity_graph

        logger.info(
            "entity_graph_updated",
            entity_count=len(entity_graph),
            total_relationships=sum(
                len(neighbors) for neighbors in entity_graph.values()
            ),
        )

    def get_service_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive service-level metrics.

        Returns combined metrics from both gap detection and caching layers,
        providing a complete picture of warming service health and performance.

        Returns:
            Dictionary containing:
                - cache_metrics: Cache hit/miss/latency statistics
                - warming_history: Entity warming frequency distribution
                - service_status: Overall service health status
        """
        cache_metrics = self.cache.get_metrics()

        return {
            "cache_metrics": {
                "cache_hits": cache_metrics.cache_hits,
                "cache_misses": cache_metrics.cache_misses,
                "cache_hit_ratio": cache_metrics.cache_hit_ratio,
                "avg_warming_latency_ms": cache_metrics.avg_warming_latency_ms,
                "total_warming_calls": cache_metrics.total_warming_calls,
            },
            "warming_history_size": len(self._warming_history),
            "entity_graph_size": len(self.entity_graph),
            "l1_cache_size": len(self.cache.l1_cache),
            "initialized": self._initialized,
        }

    def _format_cache_metrics(self) -> dict[str, Any]:
        """Format cache metrics for response."""
        metrics = self.cache.get_metrics()
        return {
            "hits": metrics.cache_hits,
            "misses": metrics.cache_misses,
            "hit_ratio_percent": metrics.cache_hit_ratio,
            "avg_latency_ms": metrics.avg_warming_latency_ms,
        }

    async def maintenance_cycle(self) -> None:
        """
        Execute periodic maintenance operations.

        Clears expired cache entries and updates internal statistics.
        Should be called periodically (e.g., every 60 seconds) to maintain
        cache coherence and memory efficiency.
        """
        try:
            await self.cache.clear_expired()

            logger.info(
                "maintenance_cycle_complete",
                l1_cache_size=len(self.cache.l1_cache),
            )

        except Exception as e:
            logger.error(
                "maintenance_cycle_failed",
                error=str(e),
            )

    async def shutdown(self) -> None:
        """
        Shutdown the warming service gracefully.

        Closes all resources including Redis connections and clears
        in-memory caches. Should be called on application shutdown.
        """
        try:
            await self.cache.shutdown()
            logger.info("warming_service_shutdown_complete")
        except Exception as e:
            logger.error(
                "warming_service_shutdown_failed",
                error=str(e),
            )


# Factory function for easy initialization
async def create_warming_service(
    config: PredictiveCacheConfig | None = None,
    graph_client: Any | None = None,
) -> MemoryWarmingService:
    """
    Factory function to create and initialize a MemoryWarmingService.

    Args:
        config: Optional cache configuration
        graph_client: Optional Neo4j graph client

    Returns:
        Initialized MemoryWarmingService instance

    Example:
        >>> service = await create_warming_service()
        >>> result = await service.warm_for_query("query", ["entity_1"])
    """
    service = MemoryWarmingService(config=config, graph_client=graph_client)
    await service.initialize()
    return service


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-034",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.gap_detector",
        "memory.predictive_cache",
        "memory.warming_models",
    ],
    "tags": ["async", "learning", "logging", "memory-substrate", "metrics", "service"],
    "keywords": [
        "agent",
        "cache",
        "create",
        "cycle",
        "detection",
        "entity",
        "graph",
        "initialize",
    ],
    "business_value": "Orchestrates gap detection and predictive caching for AI agent memory.",
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
