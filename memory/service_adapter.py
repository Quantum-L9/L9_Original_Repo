"""
L9 MemoryService Adapter

Adapter that wraps MemorySubstrateService to implement the MemoryService protocol.

This provides a high-level, agent-friendly interface while delegating to the
existing substrate service for actual operations.

Architecture:
- MemoryService (Protocol) <- MemoryServiceAdapter (Implementation)
- MemoryServiceAdapter wraps MemorySubstrateService
- Provides simplified store/retrieve/search vs raw packet operations

Version: 1.0.0
GMP: GMP-115-memory-service-adapter
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "MemoryService Adapter",
    "module_version": "1.0.0",
    "created_by": "GMP-115",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-01-24T00:00:00Z",
    "layer": "service",
    "domain": "memory_substrate",
    "module_name": "service_adapter",
    "type": "adapter",
    "status": "active",
    "adr": ["ADR-0026"],
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "Neo4j", "Redis", "pgvector"],
        "memory_layers": ["semantic_memory", "working_memory", "episodic_memory"],
        "imported_by": [
            "memory.__init__",
            "core.di.container",
            "agents.cursor.integrations",
        ],
    },
}
# ============================================================================

import uuid
from typing import TYPE_CHECKING, Any

import structlog

from core.schemas import (
    PacketEnvelopeIn,
    PacketKind,
    SemanticSearchRequest,
)

if TYPE_CHECKING:
    from core.protocols import MemoryService
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class MemoryServiceAdapter:
    """
    Adapter implementing MemoryService protocol via MemorySubstrateService.

    This class bridges the high-level MemoryService protocol with the
    low-level packet-based operations of MemorySubstrateService.

    Usage:
        from memory.substrate_service import create_substrate_service
        from memory.service_adapter import MemoryServiceAdapter

        substrate = await create_substrate_service(...)
        memory = MemoryServiceAdapter(substrate)

        # Now use the simple interface
        memory_id = await memory.store("Important fact", session_id="...")
        result = await memory.search("find facts", session_id="...")
    """

    def __init__(self, substrate_service: MemorySubstrateService) -> None:
        """
        Initialize adapter with substrate service.

        Args:
            substrate_service: The underlying MemorySubstrateService instance
        """
        self._substrate = substrate_service
        logger.info("MemoryServiceAdapter initialized")

    @must_stay_async("callers use await")
    async def store(
        self,
        content: str,
        *,
        session_id: str,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store content in memory.

        Creates a MEMORY packet and processes it through the substrate DAG.

        Args:
            content: Content to store
            session_id: Session identifier (maps to thread_id)
            agent_id: Optional agent identifier
            metadata: Optional metadata dict

        Returns:
            Memory ID (packet_id) of stored content
        """
        packet_id = str(uuid.uuid4())

        # Build packet payload
        payload: dict[str, Any] = {
            "content": content,
            "source": "memory_service_adapter",
        }
        if agent_id:
            payload["agent_id"] = agent_id
        if metadata:
            payload["metadata"] = metadata

        # Create packet envelope
        packet_in = PacketEnvelopeIn(
            packet_id=packet_id,
            packet_type=PacketKind.MEMORY_WRITE,
            thread_id=session_id,
            payload=payload,
        )

        logger.debug(
            "memory_service_store",
            packet_id=packet_id,
            session_id=session_id,
            agent_id=agent_id,
            content_length=len(content),
        )

        # Write through substrate
        result = await self._substrate.write_packet(packet_in)

        if result.status == "error":
            logger.error(
                "memory_service_store_failed",
                packet_id=packet_id,
                error=result.error_message,
            )
            raise RuntimeError(f"Failed to store memory: {result.error_message}")

        logger.info(
            "memory_service_stored",
            packet_id=packet_id,
            written_tables=result.written_tables,
        )

        return packet_id

    @must_stay_async("callers use await")
    async def retrieve(
        self,
        memory_id: str,
        *,
        session_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve content by memory ID.

        Args:
            memory_id: Memory identifier (packet_id)
            session_id: Session identifier (for RLS context)

        Returns:
            Memory content dict or None if not found
        """
        logger.debug(
            "memory_service_retrieve",
            memory_id=memory_id,
            session_id=session_id,
        )

        # Retrieve packet from substrate
        packet = await self._substrate.get_packet(memory_id)

        if packet is None:
            logger.debug(
                "memory_service_retrieve_not_found",
                memory_id=memory_id,
            )
            return None

        # Transform to simple dict format
        return {
            "memory_id": memory_id,
            "content": packet.get("payload", {}).get("content"),
            "packet_type": packet.get("packet_type"),
            "agent_id": packet.get("agent_id"),
            "thread_id": packet.get("thread_id"),
            "timestamp": packet.get("timestamp"),
            "metadata": packet.get("payload", {}).get("metadata", {}),
        }

    @must_stay_async("callers use await")
    async def search(
        self,
        query: str,
        *,
        session_id: str,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Search memory using semantic similarity.

        Args:
            query: Search query
            session_id: Session identifier (for RLS context)
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of matching memory items with similarity scores
        """
        logger.debug(
            "memory_service_search",
            query=query[:50] if len(query) > 50 else query,
            session_id=session_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        # Build search request
        request = SemanticSearchRequest(
            query=query,
            top_k=limit,
            min_score=min_similarity,
        )

        # Execute search through substrate
        result = await self._substrate.semantic_search(request)

        # Transform hits to simple dict format
        memories = []
        for hit in result.hits:
            memories.append(
                {
                    "memory_id": hit.embedding_id,
                    "similarity": hit.score,
                    "content": hit.payload.get("content") if hit.payload else None,
                    "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                }
            )

        logger.info(
            "memory_service_search_complete",
            query_length=len(query),
            hits=len(memories),
        )

        return memories


# Type assertion: MemoryServiceAdapter implements MemoryService protocol
def _check_protocol_compliance() -> None:
    """Verify MemoryServiceAdapter implements MemoryService at import time."""
    adapter: MemoryService = MemoryServiceAdapter.__new__(MemoryServiceAdapter)  # type: ignore[assignment]
    _ = adapter  # Silence unused variable warning


# Run check at module load (will raise if protocol not satisfied)
_check_protocol_compliance()


__all__ = ["MemoryServiceAdapter"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-060",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.protocols", "core.schemas", "memory.substrate_service"],
    "tags": [
        "adapter",
        "adapter-pattern",
        "async",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "service",
    ],
    "keywords": [
        "adapter",
        "agent",
        "memory",
        "memoryservice",
        "memoryserviceadapter",
        "memorysubstrateservice",
        "operations",
        "protocol",
    ],
    "business_value": "This provides a high-level, agent-friendly interface while delegating to the existing substrate service for actual operations. MemoryService (Protocol) <- MemoryServiceAdapter (Implementation) MemoryS",
    "last_modified": "2026-01-24T15:21:11Z",
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
