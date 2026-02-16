"""
L9 Memory Adapter for Domain Tensor Bridge
============================================

Maps DTB's MemoryBridge interface to actual L9 memory services:

  MemoryBridge method         ->  L9 Service
  -------------------------       ---------------------------------
  get_working_memory()        ->  WorkingMemoryService.hydrate()
  set_working_memory()        ->  WorkingMemoryService.update()
  query_episodic_memory()     ->  MemorySubstrateService.query_packets()
  store_episodic_event()      ->  MemorySubstrateService.write_packet()
  query_semantic_graph()      ->  Neo4jClient.run_query()
  query_causal_graph()        ->  (not implemented — HyperGraphDB absent)

This adapter is the ONLY integration seam between DTB and L9 memory.
DTB components should never import L9 memory services directly.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from domain_tensor_bridge.memory_bridge import EpisodicEvent, MemoryBridge, Node

if TYPE_CHECKING:
    from memory.graph_client import Neo4jClient
    from memory.substrate_service import MemorySubstrateService
    from memory_cache.working_memory_service import WorkingMemoryService

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# DORA header
# ---------------------------------------------------------------------------
__dora_meta__ = {
    "component_name": "L9 Memory Adapter",
    "module_version": "1.0.0",
    "created_by": "GMP-Wiring",
    "created_at": "2026-02-14T00:00:00Z",
    "updated_at": "2026-02-14T00:00:00Z",
    "layer": "foundation",
    "domain": "domain_tensor_bridge",
    "module_name": "l9_memory_adapter",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "Neo4j", "Redis"],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": ["domain_tensor_bridge.memory_bridge"],
    },
}


class L9MemoryAdapter(MemoryBridge):
    """
    Concrete adapter wiring DTB's MemoryBridge to L9 services.

    Accepts optional service instances via DI.  Any service that is ``None``
    degrades gracefully — the corresponding MemoryBridge method returns an
    empty/default result and logs a warning.
    """

    def __init__(
        self,
        substrate_service: MemorySubstrateService | None = None,
        working_memory_service: WorkingMemoryService | None = None,
        neo4j_client: Neo4jClient | None = None,
        *,
        repo_id: str = "l9-default",
        branch: str = "main",
    ) -> None:
        # Do NOT call super().__init__ with substrate_service because the
        # parent stores it as self.substrate and tries to call non-existent
        # methods on it.  We override every method instead.
        super().__init__(substrate_service=None)

        self._substrate = substrate_service
        self._working_memory = working_memory_service
        self._neo4j = neo4j_client
        self._repo_id = repo_id
        self._branch = branch
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Mark adapter as ready.  Underlying services manage their own init."""
        self._initialized = True
        logger.info(
            "l9_memory_adapter_ready",
            has_substrate=self._substrate is not None,
            has_working_memory=self._working_memory is not None,
            has_neo4j=self._neo4j is not None,
        )

    # ------------------------------------------------------------------
    # Working Memory  (Redis via WorkingMemoryService)
    # ------------------------------------------------------------------

    async def get_working_memory(self, key: str) -> dict[str, Any] | None:
        if self._working_memory is None:
            logger.warning("l9_adapter_no_working_memory_service")
            return None
        try:
            data = await self._working_memory.hydrate(self._repo_id, self._branch)
            return data.get(key) if isinstance(data, dict) else None
        except Exception:
            logger.warning(
                "l9_adapter_working_memory_get_failed", key=key, exc_info=True
            )
            return None

    async def set_working_memory(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int = 300,
    ) -> bool:
        if self._working_memory is None:
            logger.warning("l9_adapter_no_working_memory_service")
            return False
        try:
            await self._working_memory.update(
                repo_id=self._repo_id,
                branch=self._branch,
                patch={key: value},
            )
            return True
        except Exception:
            logger.warning(
                "l9_adapter_working_memory_set_failed", key=key, exc_info=True
            )
            return False

    # ------------------------------------------------------------------
    # Episodic Memory  (Postgres via MemorySubstrateService)
    # ------------------------------------------------------------------

    async def query_episodic_memory(
        self,
        filters: dict[str, Any],
    ) -> list[EpisodicEvent]:
        if self._substrate is None:
            logger.warning("l9_adapter_no_substrate_service")
            return []
        try:
            result = await self._substrate.query_packets(
                packet_types=filters.get("event_types") or filters.get("packet_types"),
                limit=filters.get("limit", 50),
                agent_id=filters.get("agent_id"),
            )
            packets = result.get("packets", [])
            return [
                EpisodicEvent(
                    event_id=str(p.get("id", "")),
                    timestamp=str(p.get("created_at", "")),
                    event_type=str(p.get("packet_type", "")),
                    payload=p.get("payload", {}),
                    metadata=p.get("metadata", {}),
                )
                for p in packets
            ]
        except Exception:
            logger.warning("l9_adapter_query_episodic_failed", exc_info=True)
            return []

    async def store_episodic_event(self, event: EpisodicEvent) -> bool:
        if self._substrate is None:
            logger.warning("l9_adapter_no_substrate_service")
            return False
        try:
            from memory.substrate_models import PacketEnvelopeIn

            packet_in = PacketEnvelopeIn(
                source_id="domain_tensor_bridge",
                agent_id="dtb_adapter",
                packet_type=event.event_type,
                payload=json.dumps(event.payload)
                if isinstance(event.payload, dict)
                else str(event.payload),
                metadata=event.metadata,
                thread_id=event.metadata.get("thread_id", "dtb-default"),
            )
            await self._substrate.write_packet(packet_in)
            return True
        except Exception:
            logger.warning("l9_adapter_store_episodic_failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Semantic Graph  (Neo4j via Neo4jClient)
    # ------------------------------------------------------------------

    async def query_semantic_graph(self, query: str) -> list[Node]:
        if self._neo4j is None:
            logger.warning("l9_adapter_no_neo4j_client")
            return []
        try:
            raw = await self._neo4j.run_query(query)
            return [
                Node(
                    node_id=str(r.get("id", "")),
                    node_type=str(
                        r.get(
                            "type",
                            r.get("labels", ["Unknown"])[0]
                            if isinstance(r.get("labels"), list)
                            else "Unknown",
                        )
                    ),
                    properties={
                        k: v
                        for k, v in r.items()
                        if k not in ("id", "type", "labels", "edges")
                    },
                    edges=r.get("edges", []),
                )
                for r in raw
            ]
        except Exception:
            logger.warning("l9_adapter_query_graph_failed", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Causal Graph  (HyperGraphDB — NOT available in L9)
    # ------------------------------------------------------------------

    async def query_causal_graph(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """HyperGraphDB is not implemented in L9.  Returns empty subgraph."""
        logger.debug("l9_adapter_causal_graph_not_available", entity_id=entity_id)
        return {"nodes": [], "edges": []}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = ["L9MemoryAdapter"]

# ---------------------------------------------------------------------------
# DORA footer
# ---------------------------------------------------------------------------
__dora_footer__ = {
    "component_id": "FND-DTB-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.substrate_service",
        "memory.graph_client",
        "memory_cache.working_memory_service",
    ],
    "tags": ["adapter", "domain-tensor-bridge", "memory", "foundation"],
    "keywords": ["adapter", "bridge", "l9", "memory", "neo4j", "redis", "substrate"],
    "business_value": "Bridges DTB reasoning to L9 memory stack without tight coupling",
    "last_modified": "2026-02-14T00:00:00Z",
    "modified_by": "GMP-Wiring",
    "change_summary": "Initial creation — maps DTB MemoryBridge to L9 services",
}
