#!/usr/bin/env python3
"""
================================================================================
Module: Memory Bridge
Purpose: Interface to all L9 memory layers (Redis, Postgres, Neo4j, HyperGraphDB)
================================================================================

Summary:
    Unified memory access layer connecting Domain-Tensor Bridge to L9's
    memory substrate. Provides working memory (Redis), episodic memory
    (Postgres), semantic graph (Neo4j), and causal graph (HyperGraphDB).

Extended Metadata:
    See __footer_meta__ at module footer. Runtime trace in __l9_trace__.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: FND-DTB-001
# layer: foundation
# domain: memory
# governance_level: critical
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Bridge",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "operations",
    "domain": "domain_tensor_bridge",
    "module_name": "memory_bridge",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [
            "domain_tensor_bridge.tests.domain_tensor_bridge.test_context_enrichment",
            "domain_tensor_bridge.tests.domain_tensor_bridge.test_memory_integration",
        ],
    },
}
# ============================================================================

import os
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.decorators import must_stay_async

# Expected imports from L9 memory
from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


@dataclass
class EpisodicEvent:
    """Event from episodic memory."""

    event_id: str
    timestamp: str
    event_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """Node from semantic graph."""

    node_id: str
    node_type: str
    properties: dict[str, Any]
    edges: list[str] = field(default_factory=list)


class MemoryBridge:
    """
    Unified interface to L9 memory layers.

    Memory topology:
    - Working Memory (Redis): Fast, ephemeral, session context
    - Episodic Memory (Postgres): Event logs, packet history
    - Semantic Graph (Neo4j): Entity relationships, knowledge
    - Causal Graph (HyperGraphDB): Causal reasoning, interventions

    **Integration note:** For L9 production use, instantiate via
    ``L9MemoryAdapter`` (``domain_tensor_bridge.l9_memory_adapter``)
    which maps this interface to real L9 services (MemorySubstrateService,
    WorkingMemoryService, Neo4jClient).  Passing a raw
    ``MemorySubstrateService`` here will NOT work because this class
    calls methods (``redis_get``, ``query_events``, ``cypher_query``)
    that do not exist on that service.
    """

    def __init__(
        self,
        substrate_service: MemorySubstrateService | None = None,
    ):
        self.substrate = substrate_service
        self._redis_dsn = os.environ.get("L9_REDIS_URL")
        self._postgres_dsn = os.environ.get("L9_POSTGRES_URL")
        self._neo4j_dsn = os.environ.get("L9_NEO4J_URL")
        self._hypergraph_dsn = os.environ.get("L9_HYPERGRAPH_URL")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize memory connections."""
        logger.info(
            "memory_bridge_initializing",
            redis=bool(self._redis_dsn),
            postgres=bool(self._postgres_dsn),
            neo4j=bool(self._neo4j_dsn),
        )

        if self.substrate:
            await self.substrate.initialize()

        self._initialized = True
        logger.info("memory_bridge_ready")

    # =========================================================================
    # Working Memory (Redis)
    # =========================================================================

    async def get_working_memory(self, key: str) -> dict[str, Any] | None:
        """
        Get value from working memory (Redis).

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        logger.debug("get_working_memory", key=key)

        if self.substrate:
            return await self.substrate.redis_get(key)

        logger.warning("no_substrate_configured")
        return None

    @must_stay_async("callers use await")
    async def set_working_memory(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int = 300,
    ) -> bool:
        """
        Set value in working memory (Redis).

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (default 5 min)

        Returns:
            True if successful
        """
        logger.debug("set_working_memory", key=key, ttl=ttl_seconds)

        if self.substrate:
            return await self.substrate.redis_set(key, value, ttl=ttl_seconds)

        logger.warning("no_substrate_configured")
        return False

    # =========================================================================
    # Episodic Memory (Postgres)
    # =========================================================================

    async def query_episodic_memory(
        self,
        filters: dict[str, Any],
    ) -> list[EpisodicEvent]:
        """
        Query episodic memory (Postgres) for events.

        Args:
            filters: Query filters (event_type, time_range, entity_id, etc.)

        Returns:
            List of matching events
        """
        logger.debug("query_episodic_memory", filters=filters)

        if self.substrate:
            raw_events = await self.substrate.query_events(filters)
            return [
                EpisodicEvent(
                    event_id=e.get("id", ""),
                    timestamp=e.get("timestamp", ""),
                    event_type=e.get("type", ""),
                    payload=e.get("payload", {}),
                    metadata=e.get("metadata", {}),
                )
                for e in raw_events
            ]

        logger.warning("no_substrate_configured")
        return []

    async def store_episodic_event(
        self,
        event: EpisodicEvent,
    ) -> bool:
        """Store event in episodic memory."""
        logger.debug("store_episodic_event", event_type=event.event_type)

        if self.substrate:
            return await self.substrate.store_event(
                event_type=event.event_type,
                payload=event.payload,
                metadata=event.metadata,
            )

        return False

    # =========================================================================
    # Semantic Graph (Neo4j)
    # =========================================================================

    async def query_semantic_graph(self, query: str) -> list[Node]:
        """
        Query semantic graph (Neo4j).

        Args:
            query: Cypher query string

        Returns:
            List of matching nodes
        """
        logger.debug("query_semantic_graph", query=query[:50])

        if self.substrate:
            raw_nodes = await self.substrate.cypher_query(query)
            return [
                Node(
                    node_id=n.get("id", ""),
                    node_type=n.get("type", ""),
                    properties=n.get("properties", {}),
                    edges=n.get("edges", []),
                )
                for n in raw_nodes
            ]

        logger.warning("no_substrate_configured")
        return []

    # =========================================================================
    # Causal Graph (HyperGraphDB)
    # =========================================================================

    async def query_causal_graph(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """
        Query causal graph for entity relationships.

        Args:
            entity_id: Entity to query
            depth: Traversal depth (default 2)

        Returns:
            Causal subgraph
        """
        logger.debug("query_causal_graph", entity_id=entity_id, depth=depth)

        if self.substrate and hasattr(self.substrate, "hypergraph_query"):
            return await self.substrate.hypergraph_query(entity_id, depth)

        return {"nodes": [], "edges": []}


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================

__footer_meta__ = {
    "component_id": "FND-DTB-001",
    "component_name": "Memory Bridge",
    "module_version": "1.0.0",
    "created_at": "2026-01-02T03:35:00Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "foundation",
    "domain": "memory",
    "type": "bridge",
    "status": "active",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Interface to all L9 memory layers",
    "summary": "Unified memory access layer connecting to Redis (working), Postgres (episodic), Neo4j (semantic), and HyperGraphDB (causal).",
    "dependencies": [
        "structlog",
        "l9.memory.substrate_service",
        "os",
    ],
}

__all__ = [
    "EpisodicEvent",
    "MemoryBridge",
    "Node",
    "__footer_meta__",
    "__l9_trace__",
]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "DOM-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_service"],
    "tags": [
        "async",
        "caching",
        "dataclass",
        "debugging",
        "domain-tensor-bridge",
        "event-driven",
        "logging",
        "operations",
        "tracing",
    ],
    "keywords": [
        "bridge",
        "causal",
        "episodic",
        "event",
        "graph",
        "initialize",
        "memory",
        "query",
    ],
    "business_value": "Provides memory bridge components including EpisodicEvent, Node, MemoryBridge",
    "last_modified": "2026-01-24T13:02:52Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
