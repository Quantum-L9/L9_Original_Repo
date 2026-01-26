"""
L9 Telemetry - Memory Metrics
=============================

Prometheus metrics for L9 memory substrate observability.
Tracks memory writes, searches, tool invocations, and latencies.

These metrics integrate with the L9 /metrics endpoint via
the prometheus_client library.

Version: 1.0.0
Author: L9 Enterprise

Usage:
    from telemetry.memory_metrics import (
        record_memory_write,
        record_memory_search,
        record_tool_invocation,
    )

    # After memory write:
    record_memory_write(segment="tool_audit", status="ok")

    # After memory search:
    record_memory_search(segment="session_context", hit_count=5)

    # After tool invocation:
    record_tool_invocation(tool_id="memory_search", status="success", duration_ms=42)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Metrics",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-13T13:49:43Z",
    "layer": "operations",
    "domain": "observability",
    "module_name": "memory_metrics",
    "type": "tracker",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [
            "api.server",
            "memory.substrate_service",
            "memory.tool_audit",
            "telemetry.memory_metrics",
            "tests.integration.test_tool_observability_integration",
            "tests.telemetry.conftest",
            "tests.telemetry.test_memory_metrics",
        ],
    },
}
# ============================================================================


import structlog

logger = structlog.get_logger(__name__)

# Try to import prometheus_client, gracefully degrade if not available
try:
    from prometheus_client import REGISTRY, Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed - metrics disabled")

# =============================================================================
# Metric Definitions
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Memory write metrics
    MEMORY_WRITE_TOTAL = Counter(
        "l9_memory_write_total",
        "Total number of memory write operations",
        ["segment", "status"],
    )

    MEMORY_WRITE_DURATION = Histogram(
        "l9_memory_write_duration_seconds",
        "Duration of memory write operations in seconds",
        ["segment"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # Memory search metrics
    MEMORY_SEARCH_TOTAL = Counter(
        "l9_memory_search_total",
        "Total number of memory search operations",
        ["segment", "search_type"],
    )

    MEMORY_SEARCH_HITS = Histogram(
        "l9_memory_search_hits",
        "Number of hits returned by memory searches",
        ["segment"],
        buckets=(0, 1, 2, 5, 10, 20, 50, 100),
    )

    # Tool invocation metrics
    TOOL_INVOCATION_TOTAL = Counter(
        "l9_tool_invocation_total",
        "Total number of tool invocations",
        ["tool_id", "status"],
    )

    TOOL_INVOCATION_DURATION = Histogram(
        "l9_tool_invocation_duration_ms",
        "Duration of tool invocations in milliseconds",
        ["tool_id"],
        buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
    )

    # Memory substrate health
    MEMORY_SUBSTRATE_HEALTHY = Gauge(
        "l9_memory_substrate_healthy",
        "Whether the memory substrate is healthy (1=healthy, 0=unhealthy)",
    )

    # Current packet store size (updated periodically)
    PACKET_STORE_SIZE = Gauge(
        "l9_packet_store_size",
        "Current number of packets in packet_store",
        ["segment"],
    )

    # ==========================================================================
    # Audit Mode Metrics (v2.0)
    # ==========================================================================

    # Ingestion counters
    MEMORY_INGEST_TOTAL = Counter(
        "l9_memory_ingested_total",
        "Total number of ingested packets",
        ["status"],
    )

    MEMORY_DEDUP_TOTAL = Counter(
        "l9_memory_deduplicated_total",
        "Total number of deduplicated packets",
        ["reason"],
    )

    MEMORY_QUARANTINED_TOTAL = Counter(
        "l9_memory_quarantined_total",
        "Total number of quarantined packets",
        ["reason"],
    )

    MEMORY_POISON_SUSPECT_TOTAL = Counter(
        "l9_memory_poison_suspect_total",
        "Total number of packets flagged as potential poisoning attempts",
        ["signal"],
    )

    # Retrieval quality metrics
    MEMORY_RECALL_AT_K = Gauge(
        "l9_memory_recall_at_k",
        "Recall@k for memory retrieval evaluation",
        ["k"],
    )

    MEMORY_MRR = Gauge(
        "l9_memory_mrr",
        "Mean reciprocal rank for memory retrieval evaluation",
    )

    MEMORY_NDCG = Gauge(
        "l9_memory_ndcg",
        "Normalized discounted cumulative gain for memory retrieval evaluation",
        ["k"],
    )

    # Latency metrics by pipeline stage
    MEMORY_DAG_LATENCY = Histogram(
        "l9_memory_dag_latency_seconds",
        "DAG pipeline latency in seconds",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )

    MEMORY_EMBED_LATENCY = Histogram(
        "l9_memory_embed_latency_seconds",
        "Embedding latency in seconds",
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    )

    MEMORY_SEARCH_LATENCY = Histogram(
        "l9_memory_search_latency_seconds",
        "Search latency in seconds",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )

    MEMORY_FUSION_LATENCY = Histogram(
        "l9_memory_fusion_latency_seconds",
        "Hybrid fusion latency in seconds",
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
    )

    # Vector index size
    VECTOR_INDEX_SIZE = Gauge(
        "l9_memory_vector_index_size",
        "Current number of vectors in semantic index",
        ["segment"],
    )

    # ==========================================================================
    # Enrichment DAG Metrics (SUPERPROMPTPACK)
    # ==========================================================================

    MEMORY_ENRICHMENT_TOTAL = Counter(
        "l9_memory_enrichment_total",
        "Total number of enrichment operations by status and tier",
        ["status", "tier"],
    )

    MEMORY_ENRICHMENT_DURATION = Histogram(
        "l9_memory_enrichment_duration_ms",
        "Duration of enrichment operations in milliseconds",
        ["tier"],
        buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 15000),
    )

    MEMORY_ENRICHMENT_FACTS = Histogram(
        "l9_memory_enrichment_facts_count",
        "Number of facts extracted during enrichment",
        buckets=(0, 1, 2, 5, 10, 20, 50),
    )

    # Tool Feedback Learning Metrics (GMP-TFL-001)
from prometheus_client import Counter, Gauge, Histogram

tool_feedback_recorded = Counter(
    "l9_tool_feedback_recorded_total",
    "Total tool execution outcomes recorded",
    ["tool_name", "success"],
)

tool_success_rate_current = Gauge(
    "l9_tool_success_rate",
    "Current success rate per tool (24h window)",
    ["tool_name", "task_type"],
)

tool_discovery_rerank_latency = Histogram(
    "l9_tool_discovery_rerank_seconds",
    "Latency for feedback-based re-ranking",
)

tool_learning_alerts = Counter(
    "l9_tool_learning_alerts_total",
    "Alerts generated by learning engine",
    ["tool_name", "alert_type", "severity"],
)

# =============================================================================
# Recording Functions
# =============================================================================


def record_memory_write(
    segment: str,
    status: str = "ok",
    duration_seconds: float | None = None,
) -> None:
    """
    Record a memory write operation.

    Args:
        segment: Memory segment (governance_meta, project_history, tool_audit, session_context)
        status: Write status (ok, partial, error)
        duration_seconds: Optional write duration in seconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_WRITE_TOTAL.labels(segment=segment, status=status).inc()
        if duration_seconds is not None:
            MEMORY_WRITE_DURATION.labels(segment=segment).observe(duration_seconds)
    except Exception as e:
        logger.warning("Failed to record memory write metric", error=str(e))


def record_memory_search(
    segment: str,
    hit_count: int = 0,
    search_type: str = "semantic",
) -> None:
    """
    Record a memory search operation.

    Args:
        segment: Memory segment searched
        hit_count: Number of results returned
        search_type: Type of search (semantic, exact, hybrid)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_SEARCH_TOTAL.labels(segment=segment, search_type=search_type).inc()
        MEMORY_SEARCH_HITS.labels(segment=segment).observe(hit_count)
    except Exception as e:
        logger.warning("Failed to record memory search metric", error=str(e))


def record_tool_invocation(
    tool_id: str,
    status: str,
    duration_ms: int = 0,
) -> None:
    """
    Record a tool invocation.

    Args:
        tool_id: Canonical tool identifier
        status: Invocation status (success, failure, denied, timeout)
        duration_ms: Execution duration in milliseconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        TOOL_INVOCATION_TOTAL.labels(tool_id=tool_id, status=status).inc()
        TOOL_INVOCATION_DURATION.labels(tool_id=tool_id).observe(duration_ms)
    except Exception as e:
        logger.warning("Failed to record tool invocation metric", error=str(e))


def set_memory_substrate_health(healthy: bool) -> None:
    """
    Set the memory substrate health gauge.

    Args:
        healthy: Whether the memory substrate is healthy
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_SUBSTRATE_HEALTHY.set(1 if healthy else 0)
    except Exception as e:
        logger.warning("Failed to set memory substrate health", error=str(e))


def update_packet_store_size(segment: str, count: int) -> None:
    """
    Update the packet store size gauge for a segment.

    Args:
        segment: Memory segment
        count: Current packet count
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        PACKET_STORE_SIZE.labels(segment=segment).set(count)
    except Exception as e:
        logger.warning("Failed to update packet store size", error=str(e))


# =============================================================================
# Audit Mode Recording Functions (v2.0)
# =============================================================================


def record_memory_ingest(status: str = "ok") -> None:
    """Record a memory ingest operation."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_INGEST_TOTAL.labels(status=status).inc()
    except Exception as e:
        logger.warning("Failed to record memory ingest metric", error=str(e))


def record_memory_dedup(reason: str, count: int = 1) -> None:
    """Record deduplication events."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_DEDUP_TOTAL.labels(reason=reason).inc(count)
    except Exception as e:
        logger.warning("Failed to record memory dedup metric", error=str(e))


def record_memory_quarantine(reason: str, count: int = 1) -> None:
    """Record quarantined packet events."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_QUARANTINED_TOTAL.labels(reason=reason).inc(count)
    except Exception as e:
        logger.warning("Failed to record memory quarantine metric", error=str(e))


def record_memory_poison_suspect(signal: str, count: int = 1) -> None:
    """Record potential poisoning signals."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_POISON_SUSPECT_TOTAL.labels(signal=signal).inc(count)
    except Exception as e:
        logger.warning("Failed to record memory poison metric", error=str(e))


def record_retrieval_quality(
    recall_at_k: dict[int, float],
    mrr: float,
    ndcg_at_k: dict[int, float],
) -> None:
    """Record retrieval quality metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        for k, value in recall_at_k.items():
            MEMORY_RECALL_AT_K.labels(k=str(k)).set(value)
        for k, value in ndcg_at_k.items():
            MEMORY_NDCG.labels(k=str(k)).set(value)
        MEMORY_MRR.set(mrr)
    except Exception as e:
        logger.warning("Failed to record retrieval quality metrics", error=str(e))


def record_latency(metric: str, duration_seconds: float) -> None:
    """
    Record latency for DAG/embed/search/fusion stages.

    Args:
        metric: One of "dag", "embed", "search", "fusion"
        duration_seconds: Duration in seconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        if metric == "dag":
            MEMORY_DAG_LATENCY.observe(duration_seconds)
        elif metric == "embed":
            MEMORY_EMBED_LATENCY.observe(duration_seconds)
        elif metric == "search":
            MEMORY_SEARCH_LATENCY.observe(duration_seconds)
        elif metric == "fusion":
            MEMORY_FUSION_LATENCY.observe(duration_seconds)
    except Exception as e:
        logger.warning("Failed to record latency metric", error=str(e))


def update_vector_index_size(segment: str, count: int) -> None:
    """Update vector index size gauge for a segment."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        VECTOR_INDEX_SIZE.labels(segment=segment).set(count)
    except Exception as e:
        logger.warning("Failed to update vector index size", error=str(e))


# =============================================================================
# Enrichment DAG Recording Functions (SUPERPROMPTPACK)
# =============================================================================


def record_memory_enrichment(
    status: str,
    tier: str,
    facts_count: int = 0,
    duration_ms: float = 0.0,
) -> None:
    """
    Record an enrichment DAG operation.

    Called by EnrichmentDAG after each write attempt to track:
    - Success/failure rates by tier (full, core_only, direct_db, all_failed)
    - Latency distribution by tier
    - Facts extraction counts

    Args:
        status: Enrichment status (success, failed, timeout, skipped, disabled)
        tier: Write tier used (full, core_only, direct_db, all_failed)
        facts_count: Number of facts extracted during enrichment
        duration_ms: Duration of enrichment operation in milliseconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        MEMORY_ENRICHMENT_TOTAL.labels(status=status, tier=tier).inc()
        MEMORY_ENRICHMENT_DURATION.labels(tier=tier).observe(duration_ms)
        if facts_count > 0:
            MEMORY_ENRICHMENT_FACTS.observe(facts_count)
    except Exception as e:
        logger.warning(
            "Failed to record memory enrichment metric",
            error=str(e),
            status=status,
            tier=tier,
        )


# =============================================================================
# Initialization
# =============================================================================


def init_metrics() -> bool:
    """
    Initialize memory metrics.

    Returns:
        True if metrics are available, False otherwise
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus metrics not available - install prometheus_client")
        return False

    # Set initial substrate health to healthy
    set_memory_substrate_health(True)

    logger.info("Memory metrics initialized")
    return True


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "PROMETHEUS_AVAILABLE",
    # Core metrics
    "record_memory_write",
    "record_memory_search",
    "record_tool_invocation",
    "set_memory_substrate_health",
    "update_packet_store_size",
    "init_metrics",
    # Audit mode metrics (v2.0)
    "record_memory_ingest",
    "record_memory_dedup",
    "record_memory_quarantine",
    "record_memory_poison_suspect",
    "record_retrieval_quality",
    "record_latency",
    "update_vector_index_size",
    # Enrichment DAG metrics (SUPERPROMPTPACK)
    "record_memory_enrichment",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEL-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "event-driven",
        "logging",
        "metrics",
        "observability",
        "operations",
        "tracker",
    ],
    "keywords": [
        "after",
        "dedup",
        "health",
        "index",
        "ingest",
        "invocation",
        "latency",
        "memory",
    ],
    "business_value": "the prometheus_client library. Version: 1.0.0 Author: L9 Enterprise from telemetry.memory_metrics import ( record_memory_write, record_memory_search, record_tool_invocation, ) record_memory_write(segm",
    "last_modified": "2026-01-13T13:49:43Z",
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
