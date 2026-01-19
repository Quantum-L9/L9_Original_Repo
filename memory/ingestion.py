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
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Ingestion Pipeline",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "ingestion",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "api.agent_routes",
            "api.memory.router",
            "api.server",
            "api.server_memory",
            "api.webhook_mac_agent",
            "core.agents.executor",
            "core.singleton_registry",
            "email_agent.router",
            "memory.__init__",
            "memory.smoke_test",
        ],
    },
}
# ============================================================================

import structlog
from functools import lru_cache
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    import asyncpg
    from memory.substrate_dag import SubstrateDAG

from core.schemas import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult
from memory.substrate_service import MemorySubstrateService
from memory.graph_client import get_neo4j_client
from memory.validators.packet_validator import PacketValidator, PacketValidationError
from memory.audit_utils import prepare_packet_for_ingest
from core.decorators import must_stay_async
from memory.governance_gate import (
    enforce_packet_governance,
    require_governance_context,
)

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
        # DAG enrichment params (v2.1.0 - GMP-67 unified pipeline)
        dag: Optional["SubstrateDAG"] = None,
        enable_enrichment: bool = False,
        enrichment_timeout: float = 30.0,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService for embeddings
            agent_persistence: AgentPersistenceService for checkpoint triggers
            auto_embed: Automatically embed text content
            auto_tag: Automatically generate tags from content
            dag: Optional SubstrateDAG for enrichment (facts, insights, world model)
            enable_enrichment: Whether to run DAG enrichment after core writes
            enrichment_timeout: Max seconds for enrichment (timeout = log + continue)
        """
        self._repository = repository
        self._semantic_service = semantic_service
        self._agent_persistence = agent_persistence
        self._auto_embed = auto_embed
        self._auto_tag = auto_tag

        # DAG enrichment (v2.1.0 - GMP-67)
        self._dag = dag
        self._enable_enrichment = enable_enrichment
        self._enrichment_timeout = enrichment_timeout

        logger.info(
            "IngestionPipeline initialized",
            enable_enrichment=enable_enrichment,
            enrichment_timeout=enrichment_timeout,
        )

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_semantic_service(self, service) -> None:
        """Set or update the semantic service reference."""
        self._semantic_service = service

    def set_agent_persistence(self, service) -> None:
        """Set or update the agent persistence service reference."""
        self._agent_persistence = service

    def set_dag(self, dag: "SubstrateDAG") -> None:
        """Set or update the DAG reference for enrichment (v2.1.0)."""
        self._dag = dag

    def set_enable_enrichment(self, enable: bool) -> None:
        """Enable or disable DAG enrichment (v2.1.0)."""
        self._enable_enrichment = enable

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
        """
        # GMP-70: Governance enforcement (fail-closed)
        ctx = require_governance_context("ingestion.ingest")
        packet_in = enforce_packet_governance(packet_in, ctx)

        logger.info(f"Ingesting packet: type={packet_in.packet_type}")

        should_embed = embed if embed is not None else self._auto_embed
        should_tag = generate_tags if generate_tags is not None else self._auto_tag

        # Security audit: detect injection markers before processing
        packet_in, audit_report = prepare_packet_for_ingest(packet_in)

        # Disable embedding if injection markers detected (security hardening)
        if audit_report.has_security_concerns:
            should_embed = False
            logger.warning(
                "Injection markers detected; disabling embedding for packet",
                packet_id=str(audit_report.packet_id),
                concern_count=audit_report.concern_count,
                markers=list(audit_report.injection_markers)[:3],
            )

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
            # Use model_copy() since PacketEnvelope is frozen (immutable)
            envelope = envelope.model_copy(
                update={"tags": list(set(envelope.tags + auto_tags))}
            )

        embedding_payload = None
        if should_embed and self._semantic_service:
            try:
                embedding_payload = await self._prepare_embedding(envelope)
            except Exception as e:
                logger.error(f"Failed to generate embedding vector: {e}")
                errors.append(f"embedding: {str(e)}")

        # Core writes in transaction (atomic)
        # Wrap packet_store and agent_memory_events in transaction for atomicity
        # GMP-80: Pass RLS UUIDs from governance context to enable row-level security
        if self._repository:
            try:
                async with self._repository.transaction(
                    tenant_id=ctx.tenant_id,
                    org_id=ctx.org_id,
                    user_id=ctx.user_id,
                    role=ctx.role,
                ) as conn:
                    # Store structured packet (uses transaction connection)
                    await self._store_packet_with_connection(envelope, conn)
                    written_tables.append("packet_store")

                    # Store memory event (uses same transaction connection)
                    await self._store_memory_event_with_connection(envelope, conn)
                    written_tables.append("agent_memory_events")

                    if embedding_payload:
                        vector, payload, agent_id = embedding_payload
                        # Extract scope from envelope metadata for RLS
                        metadata = (
                            envelope.metadata.model_dump()
                            if hasattr(envelope.metadata, "model_dump")
                            else (envelope.metadata or {})
                        )
                        scope = metadata.get("db_scope") or metadata.get("scope") or "shared"
                        await self._repository.insert_semantic_embedding(
                            vector=vector,
                            payload=payload,
                            agent_id=agent_id,
                            scope=scope,
                        )
                        written_tables.append("semantic_memory")

                    # Transaction commits here (or rolls back on exception)
            except Exception as e:
                logger.error(f"Transaction failed for core writes: {e}")
                errors.append(f"transaction: {str(e)}")
                # Transaction auto-rolls back on exception
        else:
            # Fallback if repository not available (should not happen)
            logger.warning("Repository not available for transactional writes")
            errors.append("repository: not available")

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
        if (
            status in ("ok", "partial")
            and packet_in.packet_type in self.CRITICAL_PACKET_TYPES
        ):
            await self._trigger_critical_checkpoint(envelope)

        # =================================================================
        # DAG Enrichment (v2.1.0 - GMP-67 unified pipeline)
        # Runs AFTER core writes complete. NO RETRY on failure - just log.
        # =================================================================
        enrichment_status = "not_attempted"
        enrichment_error = None
        enrichment_facts_count = 0

        if self._enable_enrichment and self._dag and status in ("ok", "partial"):
            import asyncio

            try:
                # Run enrichment with timeout (NO RETRY on failure)
                enrichment_result = await asyncio.wait_for(
                    self._dag.enrich(envelope),
                    timeout=self._enrichment_timeout,
                )
                enrichment_status = "success"
                enrichment_facts_count = enrichment_result.facts_inserted

                # Add enrichment tables to written_tables
                if enrichment_facts_count > 0:
                    written_tables.append("knowledge_facts")
                if enrichment_result.reasoning_trace:
                    written_tables.append("reasoning_traces")

                logger.info(
                    "DAG enrichment succeeded",
                    packet_id=str(envelope.packet_id),
                    facts_count=enrichment_facts_count,
                    duration_ms=enrichment_result.enrichment_duration_ms,
                )
            except asyncio.TimeoutError:
                enrichment_status = "failed"
                enrichment_error = (
                    f"Enrichment timed out after {self._enrichment_timeout}s"
                )
                logger.warning(
                    enrichment_error,
                    packet_id=str(envelope.packet_id),
                )
                # NO RETRY - core write succeeded, just log and continue
            except Exception as e:
                enrichment_status = "failed"
                enrichment_error = str(e)
                logger.error(
                    "DAG enrichment failed (non-blocking)",
                    packet_id=str(envelope.packet_id),
                    error=enrichment_error,
                )
                # NO RETRY - core write succeeded, just log and continue
        elif not self._enable_enrichment:
            enrichment_status = "disabled"

        # Determine write tier used
        write_tier_used = "full" if enrichment_status == "success" else "core_only"
        warnings_list = [enrichment_error] if enrichment_error else []

        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=written_tables,
            status=status,
            error_message="; ".join(errors) if errors else None,
            # Enrichment fields (v2.1.0 - GMP-67)
            enrichment_status=enrichment_status,
            enrichment_error=enrichment_error,
            enrichment_facts_count=enrichment_facts_count,
            write_tier_used=write_tier_used,
            warnings=warnings_list,
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
                "timestamp": envelope.timestamp.isoformat()
                if envelope.timestamp
                else None,
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
        Validate packet structure using centralized PacketValidator.

        Uses PacketValidator for:
        - Pydantic structural validation
        - packet_type allowed list check (warns for unknown)
        - TTL future check
        - Confidence score range check

        Additionally checks:
        - Required fields (packet_type, payload)
        - packet_type max length

        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Critical field checks (fail fast before full validation)
        if not packet.packet_type:
            errors.append("packet_type is required")

        if not packet.payload:
            errors.append("payload is required")

        if packet.packet_type and len(packet.packet_type) > 100:
            errors.append("packet_type exceeds maximum length (100)")

        # Use centralized PacketValidator for remaining checks
        try:
            PacketValidator.validate(packet)
        except PacketValidationError as exc:
            errors.append(str(exc))

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

    async def _prepare_embedding(
        self, envelope: PacketEnvelope
    ) -> Optional[tuple[list[float], dict[str, Any], Optional[str]]]:
        """
        Generate embedding vector and payload for packet content.

        Returns (vector, payload, agent_id) if embedding is created.
        """
        if self._semantic_service is None:
            return None

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
            return None

        if not isinstance(text_to_embed, str):
            text_to_embed = str(text_to_embed)

        # Minimum text length
        if len(text_to_embed) < 10:
            return None

        agent_id = envelope.metadata.agent if envelope.metadata else None

        return await self._semantic_service.generate_embedding(
            text=text_to_embed,
            payload={
                "packet_id": str(envelope.packet_id),
                "packet_type": envelope.packet_type,
                "thread_id": str(envelope.thread_id) if envelope.thread_id else None,
                "timestamp": envelope.timestamp.isoformat(),
            },
            agent_id=agent_id,
        )

    @must_stay_async("callers use await")
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


@lru_cache(maxsize=1)
def get_ingestion_pipeline() -> IngestionPipeline:
    """Get or create the ingestion pipeline singleton. CACHED."""
    return IngestionPipeline()


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

    SIMPLIFIED PATH (2026-01-13):
    Routes through IngestionPipeline ONLY (no DAG) for reliability.
    DAG path (reasoning, insight extraction) can be wired in later
    once the core pipeline is stable.

    Args:
        packet_in: PacketEnvelopeIn to ingest
        service: Optional MemorySubstrateService (uses singleton if not provided)

    Returns:
        PacketWriteResult with status and written tables

    Raises:
        RuntimeError: If memory system is not initialized
    """
    # GMP-70: Governance enforcement (defense in depth)
    ctx = require_governance_context("ingestion.ingest_packet")
    packet_in = enforce_packet_governance(packet_in, ctx)

    from memory.substrate_service import get_service

    if service is None:
        try:
            service = await get_service()
        except RuntimeError:
            raise RuntimeError(
                "Memory system not initialized. Call memory.init_service() at startup."
            )

    # SIMPLIFIED: Use IngestionPipeline directly (no DAG)
    # This path includes: validation, embedding, packet_store, neo4j sync, checkpoints
    # DAG features (reasoning, insights, world model) can be added later
    pipeline = get_ingestion_pipeline()
    pipeline.set_repository(service._repository)
    pipeline.set_semantic_service(service._semantic_service)

    # Wire agent persistence for critical checkpoints
    agent_persistence = service.get_agent_persistence()
    if agent_persistence:
        pipeline.set_agent_persistence(agent_persistence)

    return await pipeline.ingest(packet_in)


# =============================================================================
# Active Memory Encoding (GMP-80-A7)
# =============================================================================


async def on_task_completion(
    task_id: str,
    task_type: str = "general",
    description: str = "",
    outcome_text: str = "",
    success: bool = True,
    learnings: Optional[list[str]] = None,
    entities: Optional[list[str]] = None,
    impact_score: float = 0.5,
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Process task completion and trigger active memory encoding.

    This is the frontier-grade approach where the system automatically
    decides what to encode from task outcomes.

    Args:
        task_id: Unique identifier for the task
        task_type: Type of task (e.g., "code_review", "planning")
        description: Task description
        outcome_text: What happened / result description
        success: Whether the task succeeded
        learnings: Explicit learnings to encode
        entities: Entities involved in the task
        impact_score: Impact score 0.0-1.0
        agent_id: Agent that completed the task
        project_id: Project context
        session_id: Session context
        metadata: Additional metadata

    Returns:
        Dict with encoding results
    """
    from uuid import UUID
    from memory.active_encoder import (
        get_active_encoder,
        TaskOutcome,
    )

    logger.info(
        "Processing task completion for active encoding",
        task_id=task_id,
        task_type=task_type,
    )

    # Build TaskOutcome
    outcome = TaskOutcome(
        task_id=UUID(task_id) if isinstance(task_id, str) else task_id,
        task_type=task_type,
        description=description,
        outcome_text=outcome_text,
        success=success,
        learnings=learnings or [],
        entities_involved=entities or [],
        impact_score=impact_score,
        agent_id=agent_id,
        project_id=project_id,
        session_id=UUID(session_id) if session_id else None,
        metadata=metadata or {},
    )

    # Get encoder and process
    encoder = get_active_encoder()

    # Wire repository if available
    if encoder._repository is None:
        try:
            from memory.substrate_service import get_service

            service = await get_service()
            encoder.set_repository(service._repository)
        except Exception as e:
            logger.warning(f"Could not wire repository to encoder: {e}")

    # Process task completion
    result = await encoder.on_task_completion(outcome)

    return {
        "task_id": task_id,
        "facts_created": result.facts_created,
        "facts_updated": result.facts_updated,
        "episodes_created": result.episodes_created,
        "links_created": result.links_created,
        "consolidation_triggered": result.consolidation_triggered,
        "execution_time_ms": result.execution_time_ms,
        "errors": result.errors,
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-004",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.schemas",
        "memory.active_encoder",
        "memory.audit_utils",
        "memory.governance_gate",
    ],
    "tags": [
        "async",
        "batch-processing",
        "caching",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "postgres",
    ],
    "keywords": [
        "agent",
        "assignment",
        "batch",
        "completion",
        "dag",
        "enable",
        "enrichment",
        "ingest",
    ],
    "business_value": "Implements IngestionPipeline for ingestion functionality",
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
