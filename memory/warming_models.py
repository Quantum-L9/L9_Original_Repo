"""
L9 Memory - Predictive Warming Data Models
Version: 1.0.0

Stage 5: Predictive Memory Warming System
Data models for gap detection, caching, and reasoning loop.

Research source: Perplexity deep_research (2026-01-15)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Predictive Warming Data Models",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "warming_models",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "memory.__init__",
            "memory.gap_detector",
            "memory.predictive_cache",
            "memory.warming_service",
            "tests.memory.test_predictive_warming",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Gap Detection Models
# =============================================================================


class GapSeverity(str, Enum):
    """Enumeration of knowledge gap severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KnowledgeGap:
    """Represents a detected knowledge gap with metadata for prioritization."""

    gap_id: str
    gap_type: str  # "entity_missing", "relationship_missing", "attention_uncertainty"
    severity: GapSeverity
    entity_ids: list[str]
    attention_entropy: float | None = None
    confidence_score: float = 0.0
    related_layer: int | None = None
    related_head: int | None = None
    timestamp_detected_ms: float = 0


class AttentionConfig(BaseModel):
    """Configuration for attention-based gap detection."""

    entropy_threshold_low: float = Field(0.5, ge=0.0, le=2.0)
    entropy_threshold_high: float = Field(1.5, ge=0.0, le=2.0)
    min_attention_span_tokens: int = Field(3, ge=1)
    max_entropy_history_len: int = Field(100, ge=10)
    entropy_percentile_for_gap: float = Field(75.0, ge=50.0, le=99.0)


# =============================================================================
# Cache Models
# =============================================================================


class SubgraphEntry(BaseModel):
    """Represents a cached subgraph entry."""

    entity_id: str
    neighbors: dict[str, dict[str, Any]]  # neighbor_id -> properties
    relationship_types: dict[str, list[str]]  # rel_type -> [neighbor_ids]
    cached_at_ms: float
    accessed_count: int = 0


class CacheMetrics(BaseModel):
    """Metrics tracking cache performance."""

    cache_hits: int = 0
    cache_misses: int = 0
    total_warming_calls: int = 0
    avg_warming_latency_ms: float = 0.0
    current_cache_size: int = 0
    evicted_entries: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


# =============================================================================
# Reasoning Loop Models
# =============================================================================


class ReasoningPhase(str, Enum):
    """Phases of the reasoning cycle."""

    ACTION = "action"
    THINK = "think"
    MEMORY = "memory"
    REFINE = "refine"


@dataclass
class ActionProposal:
    """Proposed action with rationale."""

    action_description: str
    action_params: dict[str, Any]
    confidence_score: float  # 0.0 to 1.0
    rationale: str
    dependencies: list[str] = field(default_factory=list)
    required_entities: list[str] = field(default_factory=list)


@dataclass
class ThinkingOutput:
    """Output from thinking phase."""

    goal_progress_assessment: str
    moves_toward_goal: bool
    identified_gaps: list[str]
    uncertainty_level: float  # 0.0 to 1.0
    required_memory_entities: list[str]
    attention_entropy: float | None = None


@dataclass
class MemoryContext:
    """Retrieved and warmed memory context."""

    retrieved_entities: dict[str, Any]
    entity_relationships: dict[str, set[str]]
    cache_hit_ratio: float
    warming_latency_ms: float


# =============================================================================
# Cache Configuration
# =============================================================================


class PredictiveCacheConfig(BaseModel):
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = Field(300, ge=10, le=3600)
    max_subgraph_neighbors: int = Field(20, ge=5, le=100)
    max_cache_entries: int = Field(1000, ge=100, le=100000)
    max_connection_pool_size: int = Field(10, ge=1, le=50)
    enable_metrics_tracking: bool = True
    refresh_ttl_on_hit: bool = True


# End of harvested models

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "data-models",
        "dataclass",
        "learning",
        "metrics",
        "pydantic",
        "validation",
    ],
    "keywords": [
        "action",
        "attention",
        "cache",
        "detection",
        "entry",
        "gap",
        "hit",
        "knowledge",
    ],
    "business_value": "Provides warming models components including GapSeverity, KnowledgeGap, AttentionConfig",
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
