"""
L9 Memory Substrate - Ingestion Pipeline
Version: 1.1.0

Real PacketEnvelope ingestion with:
- Validation
- Embedding generation via substrate_semantic
- Structured packet storage
- Vector storage
- Artifact handling
- Lineage tracking
- Tag assignment

All operations are async-safe with proper logging.

# bound to memory-yaml2.0 ingestion pipeline (entrypoint: ingestion.py)
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    import asyncpg

from memory.substrate_models import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketWriteResult,
)
from memory.substrate_service import MemorySubstrateService
from memory.graph_client import get_neo4j_client

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    """
    PacketEnvelope ingestion pipeline.

    Handles the full lifecycle of packet ingestion:
    1. Validation
    2. Content embedding
    3. Structured storage
    4. Vector storage
    5. Lineage updates
    6. Tag assignment
    """

    # Critical packet types that trigger checkpoints per memory_spec_v3.0.yaml
    CRITICAL_PACKET_TYPES = {
        "critical_decision",
        "igor_approval",
        "governance_action",
        "deployment",
        "rollback",
    }

    def __init__(
        self,
        repository=None,
        semantic_service=None,
        agent_persistence=None,
        auto_embed: bool = True,
        auto_tag: bool = True,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService for embeddings
            agent_persistence: AgentPersistenceService for checkpoint triggers
            auto_embed: Automatically embed text content
            auto_tag: Automatically generate tags from content
        """
        self._repository = repository
        self._semantic_service = semantic_service
        self._agent_persistence = agent_persistence
        self._auto_embed = auto_embed
        self._auto_tag = auto_tag
        logger.info("IngestionPipeline initialized")

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_semantic_service(self, service) -> None:
        """Set or update the semantic service reference."""
        self._semantic_service = service

    def set_agent_persistence(self, service) -> None:
        """Set or update the agent persistence service reference."""
        self._agent_persistence = service

    async def ingest(
        self,
        packet_in: PacketEnvelopeIn,
        embed: Optional[bool] = None,
        generate_tags: Optional[bool] = None,
    ) -> PacketWriteResult:
        """
        Ingest a PacketEnvelope into the memory substrate.

        Full pipeline:
        1. Validate packet structure
        2. Convert to full envelope
        3. Store structured packet
        4. Generate and store embedding (if applicable)
        5. Store artifacts
        6. Update lineage graph
        7. Generate and assign tags

        Args:
            packet_in: Input packet envelope
            embed: Override auto_embed setting
            generate_tags: Override auto_tag setting

        Returns:
            PacketWriteResult with status and written tables

        # bound to memory-yaml2.0 ingestion stages: normalize_input, persist_message, enqueue_embedding, enqueue_graph_sync
        """
        logger.info(f"Ingesting packet: type={packet_in.packet_type}")

        should_embed = embed if embed is not None else self._auto_embed
        should_tag = generate_tags if generate_tags is not None else self._auto_tag

        written_tables = []
        errors = []

        # Validate
        validation_errors = self._validate_packet(packet_in)
        if validation_errors:
            return PacketWriteResult(
                packet_id=packet_in.packet_id or uuid4(),
                written_tables=[],
                status="error",
                error_message="; ".join(validation_errors),
            )

        # Convert to envelope
        envelope = packet_in.to_envelope()

        # Auto-generate tags if enabled
        if should_tag:
            auto_tags = self._generate_tags(envelope)
            envelope.tags = list(set(envelope.tags + auto_tags))

        # Core writes in transaction (atomic)
        # Wrap packet_store and agent_memory_events in transaction for atomicity
        if self._repository:
            try:
                async with self._repository.transaction() as conn:
                    # Store structured packet (uses transaction connection)
                    await self._store_packet_with_connection(envelope, conn)
                    written_tables.append("packet_store")
                    
                    # Store memory event (uses same transaction connection)
                    await self._store_memory_event_with_connection(envelope, conn)
                    written_tables.append("agent_memory_events")
                    
                    # Transaction commits here (or rolls back on exception)
            except Exception as e:
                logger.error(f"Transaction failed for core writes: {e}")
                errors.append(f"transaction: {str(e)}")
                # Transaction auto-rolls back on exception
        else:
            # Fallback if repository not available (should not happen)
            logger.warning("Repository not available for transactional writes")
            errors.append("repository: not available")

        # Generate and store embedding
        if should_embed and self._semantic_service:
            try:
                embedded = await self._embed_content(envelope)
                if embedded:
                    written_tables.append("semantic_memory")
            except Exception as e:
                logger.error(f"Failed to embed content: {e}")
                errors.append(f"embedding: {str(e)}")

        # Store artifacts
        try:
            artifact_count = await self._store_artifacts(envelope)
            if artifact_count > 0:
                written_tables.append("artifacts")
        except Exception as e:
            logger.error(f"Failed to store artifacts: {e}")
            errors.append(f"artifacts: {str(e)}")

        # Update lineage
        try:
            await self._update_lineage(envelope)
        except Exception as e:
            logger.error(f"Failed to update lineage: {e}")
            errors.append(f"lineage: {str(e)}")

        # Sync to Neo4j knowledge graph (non-blocking, best-effort)
        try:
            await self._sync_to_graph(envelope)
            written_tables.append("neo4j_graph")
        except Exception as e:
            logger.warning(f"Neo4j graph sync failed (non-critical): {e}")
            # Don't add to errors - Neo4j is optional enhancement

        status = "ok" if not errors else "partial" if written_tables else "error"

        logger.info(
            f"Ingestion complete: packet_id={envelope.packet_id}, status={status}"
        )

        # Trigger checkpoint for critical packets per memory_spec_v3.0.yaml
        if status in ("ok", "partial") and packet_in.packet_type in self.CRITICAL_PACKET_TYPES:
            await self._trigger_critical_checkpoint(envelope)

        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=written_tables,
            status=status,
            error_message="; ".join(errors) if errors else None,
        )

    async def _trigger_critical_checkpoint(self, envelope: PacketEnvelope) -> None:
        """
        Trigger checkpoint for critical packet ingestion.

        Per memory_spec_v3.0.yaml checkpoint trigger: on_critical_decision.
        Creates checkpoint when critical packets (decisions, approvals, etc.) are ingested.

        Args:
            envelope: The ingested packet envelope
        """
        if self._agent_persistence is None:
            logger.debug("No persistence service - skipping critical checkpoint")
            return

        try:
            agent_id = envelope.agent_id or "ingestion"

            state = {
                "packet_id": str(envelope.packet_id),
                "packet_type": envelope.packet_type,
                "source_id": envelope.source_id,
                "thread_id": str(envelope.thread_id) if envelope.thread_id else None,
                "timestamp": envelope.timestamp.isoformat() if envelope.timestamp else None,
            }

            checkpoint_id = await self._agent_persistence.create_checkpoint(
                agent_id=agent_id,
                state=state,
                reason="on_critical_decision",
            )

            logger.debug(
                "Critical checkpoint created",
                checkpoint_id=str(checkpoint_id),
                packet_id=str(envelope.packet_id),
                packet_type=envelope.packet_type,
            )

        except Exception as e:
            # Best-effort: don't fail ingestion due to checkpoint failure
            logger.warning(
                "Failed to create critical checkpoint",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )

    def _validate_packet(self, packet: PacketEnvelopeIn) -> list[str]:
        """
        Validate packet structure.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        if not packet.packet_type:
            errors.append("packet_type is required")

        if not packet.payload:
            errors.append("payload is required")

        if packet.packet_type and len(packet.packet_type) > 100:
            errors.append("packet_type exceeds maximum length (100)")

        # Validate TTL is in future
        if packet.ttl and packet.ttl < datetime.utcnow():
            errors.append("ttl must be in the future")

        # Validate confidence score range
        if packet.confidence:
            score = packet.confidence.score
            if score is not None and (score < 0 or score > 1):
                errors.append("confidence.score must be between 0 and 1")

        return errors

    def _generate_tags(self, envelope: PacketEnvelope) -> list[str]:
        """
        Auto-generate tags from packet content.

        Heuristic tag generation:
        - packet_type as tag
        - agent as tag
        - domain as tag
        - Extract keywords from payload
        """
        tags = []

        # Add packet type as tag
        if envelope.packet_type:
            tags.append(f"type:{envelope.packet_type}")

        # Add agent as tag
        if envelope.metadata and envelope.metadata.agent:
            tags.append(f"agent:{envelope.metadata.agent}")

        # Add domain as tag
        if envelope.metadata and envelope.metadata.domain:
            tags.append(f"domain:{envelope.metadata.domain}")

        # Extract keywords from payload keys
        payload = envelope.payload
        for key in list(payload.keys())[:5]:  # Limit to first 5 keys
            if isinstance(key, str) and len(key) < 30:
                tags.append(f"field:{key}")

        return tags

    async def _store_packet(self, envelope: PacketEnvelope) -> None:
        """Store packet in packet_store table."""
        if self._repository is None:
            raise RuntimeError("Repository not configured")

        await self._repository.insert_packet(envelope)

    async def _store_packet_with_connection(
        self, envelope: PacketEnvelope, conn: "asyncpg.Connection"
    ) -> None:
        """Store packet using provided connection (for transactions)."""
        if self._repository is None:
            raise RuntimeError("Repository not configured")
        
        # Use repository's insert_packet which will detect RLS connection from context
        # The connection is stored in context variable by transaction()
        await self._repository.insert_packet(envelope)

    async def _store_memory_event(self, envelope: PacketEnvelope) -> None:
        """Store memory event in agent_memory_events table."""
        if self._repository is None:
            return

        agent_id = envelope.metadata.agent if envelope.metadata else "default"

        await self._repository.insert_memory_event(
            agent_id=agent_id or "default",
            event_type=envelope.packet_type,
            content=envelope.payload,
            packet_id=envelope.packet_id,
            timestamp=envelope.timestamp,
        )

    async def _store_memory_event_with_connection(
        self, envelope: PacketEnvelope, conn: "asyncpg.Connection"
    ) -> None:
        """Store memory event using provided connection (for transactions)."""
        if self._repository is None:
            return

        agent_id = envelope.metadata.agent if envelope.metadata else "default"

        # Use repository's insert_memory_event which will detect RLS connection from context
        # The connection is stored in context variable by transaction()
        await self._repository.insert_memory_event(
            agent_id=agent_id or "default",
            event_type=envelope.packet_type,
            content=envelope.payload,
            packet_id=envelope.packet_id,
            timestamp=envelope.timestamp,
        )

    async def _embed_content(self, envelope: PacketEnvelope) -> bool:
        """
        Generate and store embedding for packet content.

        Returns True if embedding was created.
        """
        if self._semantic_service is None:
            return False

        # Determine text to embed
        payload = envelope.payload
        text_to_embed = (
            payload.get("text")
            or payload.get("content")
            or payload.get("description")
            or payload.get("summary")
            or payload.get("message")
        )

        if not text_to_embed:
            # Skip packets without embeddable text
            return False

        if not isinstance(text_to_embed, str):
            text_to_embed = str(text_to_embed)

        # Minimum text length
        if len(text_to_embed) < 10:
            return False

        # Generate and store embedding
        agent_id = envelope.metadata.agent if envelope.metadata else None

        await self._semantic_service.embed_and_store(
            text=text_to_embed,
            payload={
                "packet_id": str(envelope.packet_id),
                "packet_type": envelope.packet_type,
                "thread_id": str(envelope.thread_id) if envelope.thread_id else None,
                "timestamp": envelope.timestamp.isoformat(),
            },
            agent_id=agent_id,
        )

        return True

    async def _store_artifacts(self, envelope: PacketEnvelope) -> int:
        """
        Store any artifacts associated with the packet.

        Artifacts are extracted from payload.artifacts field.

        Returns count of stored artifacts.
        """
        artifacts = envelope.payload.get("artifacts", [])

        if not artifacts or not isinstance(artifacts, list):
            return 0

        # For now, artifacts are stored inline in packet payload
        # Future: separate artifact storage
        return len(artifacts)

    async def _update_lineage(self, envelope: PacketEnvelope) -> None:
        """
        Update lineage graph for the packet.

        If packet has parent_ids, verify they exist and update
        the lineage tracking.
        """
        if not envelope.lineage:
            return

        parent_ids = envelope.lineage.parent_ids
        if not parent_ids:
            return

        # Verify parent packets exist (logging only, don't fail)
        if self._repository:
            for parent_id in parent_ids:
                parent = await self._repository.get_packet(parent_id)
                if parent is None:
                    logger.warning(
                        f"Lineage parent {parent_id} not found for packet {envelope.packet_id}"
                    )

    async def _sync_to_graph(self, envelope: PacketEnvelope) -> None:
        """
        Sync packet to Neo4j knowledge graph.

        Creates:
        - Event node for the packet
        - Relationships to agent, thread, and parent events

        This is best-effort - failures don't block ingestion.
        """
        neo4j = await get_neo4j_client()
        if not neo4j:
            return  # Neo4j not available, skip silently

        packet_id = str(envelope.packet_id)
        agent_id = envelope.metadata.agent if envelope.metadata else None
        thread_id = str(envelope.thread_id) if envelope.thread_id else None

        # Extract parent event ID from lineage
        parent_event_id = None
        if envelope.lineage and envelope.lineage.parent_ids:
            parent_event_id = str(envelope.lineage.parent_ids[0])

        # Create event node for this packet
        await neo4j.create_event(
            event_id=packet_id,
            event_type=envelope.packet_type,
            timestamp=envelope.timestamp.isoformat(),
            properties={
                "packet_type": envelope.packet_type,
                "agent": agent_id,
                "thread_id": thread_id,
                "tags": envelope.tags,
            },
            parent_event_id=parent_event_id,
        )

        # Link to agent entity (create if not exists)
        if agent_id:
            await neo4j.create_entity(
                entity_type="Agent",
                entity_id=agent_id,
                properties={"name": agent_id, "type": "agent"},
            )
            await neo4j.create_relationship(
                from_type="Event",
                from_id=packet_id,
                to_type="Agent",
                to_id=agent_id,
                rel_type="PROCESSED_BY",
            )

        # Link to thread (conversation grouping)
        if thread_id:
            await neo4j.create_entity(
                entity_type="Thread",
                entity_id=thread_id,
                properties={"id": thread_id, "type": "conversation"},
            )
            await neo4j.create_relationship(
                from_type="Event",
                from_id=packet_id,
                to_type="Thread",
                to_id=thread_id,
                rel_type="PART_OF",
            )

        logger.debug(f"Synced packet {packet_id} to Neo4j graph")

    async def ingest_batch(
        self,
        packets: list[PacketEnvelopeIn],
    ) -> list[PacketWriteResult]:
        """
        Ingest multiple packets in batch.

        Args:
            packets: List of input packets

        Returns:
            List of results for each packet
        """
        results = []

        for packet in packets:
            result = await self.ingest(packet)
            results.append(result)

        success_count = sum(1 for r in results if r.status == "ok")
        logger.info(
            f"Batch ingestion complete: {success_count}/{len(packets)} succeeded"
        )

        return results


# =============================================================================
# Singleton / Factory
# =============================================================================

_pipeline: Optional[IngestionPipeline] = None


def get_ingestion_pipeline() -> IngestionPipeline:
    """Get or create the ingestion pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline


def init_ingestion_pipeline(repository, semantic_service=None) -> IngestionPipeline:
    """Initialize the ingestion pipeline with dependencies."""
    pipeline = get_ingestion_pipeline()
    pipeline.set_repository(repository)
    if semantic_service:
        pipeline.set_semantic_service(semantic_service)
    return pipeline


# =============================================================================
# Canonical Ingestion Entrypoint (PRODUCTION WIRING)
# =============================================================================


async def ingest_packet(
    packet_in: PacketEnvelopeIn,
    service: Optional[MemorySubstrateService] = None,
) -> PacketWriteResult:
    """
    Canonical packet ingestion entrypoint.

    This is the SINGLE POINT OF ENTRY for all packet ingestion.
    All runtime packets MUST pass through this function.

    Args:
        packet_in: PacketEnvelopeIn to ingest
        service: Optional MemorySubstrateService (uses singleton if not provided)

    Returns:
        PacketWriteResult with status and written tables

    Raises:
        RuntimeError: If memory system is not initialized
    """
    from memory.substrate_service import get_service

    if service is None:
        try:
            service = await get_service()
        except RuntimeError:
            raise RuntimeError(
                "Memory system not initialized. Call memory.init_service() at startup."
            )

    # Use service.write_packet which runs full DAG pipeline
    return await service.write_packet(packet_in)
