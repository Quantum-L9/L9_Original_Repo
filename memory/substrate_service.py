"""
L9 Memory Substrate - Service Layer
Version: 1.0.0

Orchestrating service that coordinates repository, semantic, and graph layers.
Provides a unified interface for substrate operations.
"""

import structlog
from datetime import datetime
from uuid import uuid4
from typing import Any, Optional

from memory.substrate_models import (
    PacketEnvelopeIn,
    PacketWriteResult,
    SemanticSearchRequest,
    SemanticSearchResult,
    SemanticHit,
)
from memory.substrate_repository import SubstrateRepository
from memory.substrate_semantic import (
    SemanticService,
    EmbeddingProvider,
    StubEmbeddingProvider,
    create_embedding_provider,
)
from memory.substrate_graph import SubstrateDAG
from memory.query_classifier import QueryClassifier, get_query_classifier
from memory.reasoning_replay import ReasoningReplayPipeline
from memory.consolidation import ConsolidationPipeline
from memory.agent_persistence import AgentPersistenceService
from memory.audit_utils import prepare_packet_for_ingest
from memory.validators.packet_validator import PacketValidator, PacketValidationError
from telemetry.memory_metrics import (
    record_memory_write,
    record_memory_search,
    set_memory_substrate_health,
    record_memory_quarantine,
    record_memory_ingest,
)
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = structlog.get_logger(__name__)


class MemorySubstrateService:
    """
    Main service class for the Memory Substrate.

    Coordinates all substrate operations:
    - Packet ingestion and DAG processing
    - Semantic search
    - Memory retrieval
    - Health monitoring
    """

    def __init__(
        self,
        repository: SubstrateRepository,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        """
        Initialize the substrate service.

        Args:
            repository: Database repository instance
            embedding_provider: Embedding provider (defaults to stub if not provided)
        """
        self._repository = repository

        # Initialize embedding provider
        if embedding_provider is None:
            logger.warning("No embedding provider specified, using stub provider")
            embedding_provider = StubEmbeddingProvider()
        self._embedding_provider = embedding_provider

        # Initialize semantic service
        self._semantic_service = SemanticService(
            embedding_provider=embedding_provider,
            repository=repository,
        )

        # Initialize DAG
        self._dag = SubstrateDAG(
            repository=repository,
            semantic_service=self._semantic_service,
        )

        # Initialize circuit breaker for DAG operations
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                window_seconds=60,
                reset_timeout=30,
                name="memory_dag",
            )
        )

        # Initialize v3.1 modules (lazy initialization)
        self._query_classifier: Optional[QueryClassifier] = None
        self._reasoning_replay: Optional[ReasoningReplayPipeline] = None
        self._consolidation: Optional[ConsolidationPipeline] = None
        self._agent_persistence: Optional[AgentPersistenceService] = None

        logger.info("MemorySubstrateService initialized")

    # =========================================================================
    # RLS Session Scope
    # =========================================================================

    async def set_session_scope(
        self,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str = "end_user",
    ) -> None:
        """
        Set PostgreSQL session variables for RLS (Row-Level Security).

        Calls l9_set_scope() SQL function to set:
        - app.tenant_id
        - app.org_id
        - app.user_id
        - app.role

        CRITICAL: Must be called before every database query to enforce tenant isolation.

        Args:
            tenant_id: Tenant UUID for isolation
            org_id: Organization UUID for isolation
            user_id: User UUID for isolation
            role: User role (platform_admin, tenant_admin, org_admin, end_user)

        Raises:
            RuntimeError: If session scope setting fails
        """
        try:
            async with self._repository.acquire() as conn:
                await conn.execute(
                    """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                    tenant_id,
                    org_id,
                    user_id,
                    role,
                )
            logger.debug(
                "RLS session scope set",
                tenant_id=tenant_id,
                org_id=org_id,
                user_id=user_id,
                role=role,
            )
        except Exception as e:
            logger.error(f"Failed to set RLS session scope: {e}", exc_info=True)
            raise RuntimeError(f"RLS scope initialization failed: {e}") from e

    # =========================================================================
    # Packet Operations
    # =========================================================================

    async def write_packet(
        self,
        packet_in: PacketEnvelopeIn,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
        audit_mode: bool = True,
    ) -> PacketWriteResult:
        """
        Submit a packet to the substrate for processing.

        Runs the full DAG pipeline:
        1. Intake validation
        2. Reasoning block generation
        3. Memory writes
        4. Semantic embedding
        5. Checkpoint

        Args:
            packet_in: Input packet envelope
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            PacketWriteResult with status and written tables
        """
        logger.info(f"Processing packet: type={packet_in.packet_type}")

        if audit_mode:
            packet_in, audit_report = prepare_packet_for_ingest(packet_in)
            if audit_report.injection_markers:
                record_memory_quarantine(
                    reason="injection_markers",
                    count=1,
                )
                logger.warning(
                    "Audit quarantine markers detected",
                    packet_id=str(audit_report.packet_id),
                    markers=list(audit_report.injection_markers),
                )
        else:
            audit_report = None

        try:
            PacketValidator.validate(packet_in)
        except PacketValidationError as exc:
            packet_id = packet_in.packet_id or uuid4()
            logger.error(
                "Packet validation failed",
                error=str(exc),
                packet_id=str(packet_id),
            )
            return PacketWriteResult(
                status="error",
                packet_id=packet_id,
                written_tables=[],
                error_message=str(exc),
            )

        # Set RLS scope if provided
        if tenant_id and org_id and user_id:
            await self.set_session_scope(tenant_id, org_id, user_id, role)
        else:
            logger.warning(
                "RLS scope not provided for write_packet - queries may be restricted"
            )

        # Convert input to full envelope
        envelope = packet_in.to_envelope()

        # Circuit breaker check before DAG execution
        if self._circuit_breaker.is_open():
            cb_stats = self._circuit_breaker.get_stats()
            logger.error(
                "memory_substrate_circuit_breaker_open",
                packet_type=packet_in.packet_type,
                circuit_state=cb_stats["state"],
                failures_in_window=cb_stats["failures_in_window"],
            )
            # Return error result without attempting DAG
            return PacketWriteResult(
                status="error",
                packet_id=envelope.packet_id,
                written_tables=[],
                error_message=f"Circuit breaker open: {cb_stats['failures_in_window']} failures in {cb_stats['window_seconds']}s",
            )

        # Run through DAG with circuit breaker tracking
        try:
            result = await self._dag.run(envelope)
            # Record success for non-error results
            if result.status == "ok":
                self._circuit_breaker.record_success()
            else:
                # DAG returned error status
                self._circuit_breaker.record_failure(
                    result.error_message or "DAG returned error status"
                )
        except Exception as dag_error:
            # DAG threw exception - record failure and re-raise
            self._circuit_breaker.record_failure(str(dag_error))
            logger.error(
                "memory_substrate_dag_exception",
                packet_id=str(envelope.packet_id),
                error=str(dag_error),
                circuit_state=self._circuit_breaker.get_state(),
            )
            raise

        # Record Prometheus metrics for memory write
        record_memory_write(
            segment=packet_in.packet_type or "unknown",
            status=result.status,
        )
        record_memory_ingest(status=result.status)

        logger.info(
            f"Packet {envelope.packet_id} processed: "
            f"status={result.status}, tables={result.written_tables}"
        )

        return result

    async def get_packet(self, packet_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a packet by ID.

        Args:
            packet_id: UUID string of the packet

        Returns:
            Packet envelope as dict or None if not found
        """
        from uuid import UUID

        try:
            row = await self._repository.get_packet(UUID(packet_id))
            if row:
                return row.envelope
            return None
        except Exception as e:
            logger.error(f"Error retrieving packet {packet_id}: {e}")
            return None

    async def search_packets_by_thread(
        self,
        thread_id: str,
        packet_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search for packets by thread ID.

        Args:
            thread_id: Thread UUID string
            packet_type: Optional filter by packet type
            limit: Maximum packets to return

        Returns:
            List of packet envelopes as dicts
        """
        from uuid import UUID

        try:
            rows = await self._repository.search_packets_by_thread(
                thread_id=UUID(thread_id),
                packet_type=packet_type,
                limit=limit,
            )
            results = [row.envelope for row in rows]

            # Record Prometheus metrics for search
            record_memory_search(
                segment=packet_type or "all",
                hit_count=len(results),
                search_type="thread",
            )

            return results
        except Exception as e:
            logger.error(f"Error searching packets by thread {thread_id}: {e}")
            return []

    async def search_packets_by_type(
        self,
        packet_type: str,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search for packets by type.

        Args:
            packet_type: Packet type to search for
            agent_id: Optional filter by agent
            limit: Maximum packets to return

        Returns:
            List of packet envelopes as dicts
        """
        try:
            rows = await self._repository.search_packets_by_type(
                packet_type=packet_type,
                agent_id=agent_id,
                limit=limit,
            )
            results = [row.envelope for row in rows]

            # Record Prometheus metrics for search
            record_memory_search(
                segment=packet_type,
                hit_count=len(results),
                search_type="type",
            )

            return results
        except Exception as e:
            logger.error(f"Error searching packets by type {packet_type}: {e}")
            return []

    async def query_packets(
        self,
        packet_types: Optional[list[str]] = None,
        limit: int = 50,
        since: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Query packets for world model ingestion.

        Fetches packets matching the specified types, ordered by timestamp.
        Used by WorldModelRuntime.MemorySubstratePacketSource for proactive
        world model updates.

        Args:
            packet_types: List of packet types to fetch (None = all)
            limit: Maximum packets to return
            since: Only fetch packets after this timestamp
            agent_id: Optional filter by agent
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            Dict with 'packets' list and metadata
        """
        try:
            # Set RLS scope if provided
            if tenant_id and org_id and user_id:
                await self.set_session_scope(tenant_id, org_id, user_id, role)

            all_packets = []

            if packet_types:
                # Fetch each type and combine
                for ptype in packet_types:
                    rows = await self._repository.search_packets_by_type(
                        packet_type=ptype,
                        agent_id=agent_id,
                        limit=limit,
                        since=since,
                    )
                    all_packets.extend([row.envelope for row in rows])
            else:
                # No type filter - get recent packets
                # Use a common packet type as fallback
                for ptype in ["insight", "reflection", "ir_graph", "execution_plan"]:
                    rows = await self._repository.search_packets_by_type(
                        packet_type=ptype,
                        agent_id=agent_id,
                        limit=limit // 4,  # Split limit across types
                        since=since,
                    )
                    all_packets.extend([row.envelope for row in rows])

            # Sort by timestamp descending and limit
            all_packets.sort(
                key=lambda p: p.get("timestamp", p.get("created_at", "")), reverse=True
            )
            all_packets = all_packets[:limit]

            logger.debug(f"query_packets: fetched {len(all_packets)} packets")

            return {
                "packets": all_packets,
                "count": len(all_packets),
                "since": since.isoformat() if since else None,
            }

        except Exception as e:
            logger.error(f"Error querying packets: {e}")
            # Log to error telemetry
            try:
                from core.error_tracking import log_error_to_graph
                import asyncio

                asyncio.create_task(
                    log_error_to_graph(
                        error=e,
                        context={"packet_types": packet_types, "limit": limit},
                        source="memory.substrate_service.query_packets",
                    )
                )
            except ImportError:
                pass
            return {"packets": [], "count": 0, "error": str(e)}

    # =========================================================================
    # Semantic Search Operations
    # =========================================================================

    async def semantic_search(
        self, request: SemanticSearchRequest
    ) -> SemanticSearchResult:
        """
        Search semantic memory for similar content.

        Args:
            request: Search request with query and parameters

        Returns:
            SemanticSearchResult with hits
        """
        logger.info(f"Semantic search: query='{request.query[:50]}...', min_score={request.min_score}")

        # Get more results to allow filtering by min_score
        hits = await self._semantic_service.search(
            query=request.query,
            top_k=request.top_k * 2,  # Get more to allow filtering
            agent_id=request.agent_id,
        )

        # Filter by min_score threshold
        filtered_hits = [h for h in hits if h.get("score", 0.0) >= request.min_score]
        
        # Limit to top_k after filtering
        filtered_hits = filtered_hits[:request.top_k]

        # Record Prometheus metrics for semantic search
        record_memory_search(
            segment="semantic",
            hit_count=len(filtered_hits),
            search_type="semantic",
        )

        return SemanticSearchResult(
            query=request.query,
            hits=[
                SemanticHit(
                    embedding_id=h["embedding_id"],
                    score=h["score"],
                    payload=h["payload"],
                )
                for h in filtered_hits
            ],
        )

    async def embed_text(
        self, text: str, payload: dict[str, Any], agent_id: Optional[str] = None
    ) -> str:
        """
        Directly embed and store text in semantic memory.

        Args:
            text: Text to embed
            payload: Metadata payload
            agent_id: Optional agent identifier

        Returns:
            embedding_id
        """
        return await self._semantic_service.embed_and_store(
            text=text,
            payload=payload,
            agent_id=agent_id,
        )

    # =========================================================================
    # Memory Event Operations
    # =========================================================================

    async def get_memory_events(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve memory events for an agent.

        Args:
            agent_id: Agent identifier
            event_type: Optional event type filter
            limit: Maximum events to return

        Returns:
            List of memory events as dicts
        """
        rows = await self._repository.get_memory_events(
            agent_id=agent_id,
            event_type=event_type,
            limit=limit,
        )
        return [row.model_dump(mode="json") for row in rows]

    # =========================================================================
    # Reasoning Trace Operations
    # =========================================================================

    async def get_reasoning_traces(
        self,
        agent_id: Optional[str] = None,
        packet_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve reasoning traces.

        Args:
            agent_id: Optional agent filter
            packet_id: Optional packet filter
            limit: Maximum traces to return

        Returns:
            List of reasoning traces as dicts
        """
        from uuid import UUID

        pid = UUID(packet_id) if packet_id else None

        rows = await self._repository.get_reasoning_traces(
            agent_id=agent_id,
            packet_id=pid,
            limit=limit,
        )
        return [row.model_dump(mode="json") for row in rows]

    # =========================================================================
    # Checkpoint Operations
    # =========================================================================

    async def get_checkpoint(self, agent_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve the latest checkpoint for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Checkpoint state as dict or None
        """
        row = await self._repository.get_checkpoint(agent_id)
        if row:
            return row.model_dump(mode="json")
        return None

    # =========================================================================
    # Insight & Knowledge Operations (v1.1.0+)
    # =========================================================================

    async def write_insights(
        self,
        insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Write extracted insights to the substrate.

        Persists insights and associated facts to knowledge_facts table.

        Args:
            insights: List of ExtractedInsight dicts

        Returns:
            Status dict with counts
        """
        facts_written = 0

        for insight in insights:
            # Write associated facts
            for fact in insight.get("facts", []):
                await self._repository.insert_knowledge_fact(
                    subject=fact.get("subject", "unknown"),
                    predicate=fact.get("predicate", "unknown"),
                    object_value=fact.get("object"),
                    confidence=fact.get("confidence"),
                    source_packet=insight.get("source_packet"),
                )
                facts_written += 1

        return {
            "status": "ok",
            "insights_processed": len(insights),
            "facts_written": facts_written,
        }

    async def trigger_world_model_update(
        self,
        insights: list[dict[str, Any]],
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Trigger world model update from insights.

        Calls WorldModelService.update_from_insights() to propagate
        insights to the world model with DB persistence.

        Args:
            insights: List of insights to propagate
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            Status dict with update results
        """
        logger.info(f"World model update triggered with {len(insights)} insights")

        # Set RLS scope for world model operations
        if tenant_id and org_id and user_id:
            await self.set_session_scope(tenant_id, org_id, user_id, role)

        # Filter to insights that should trigger updates
        triggering = [i for i in insights if i.get("trigger_world_model", False)]

        if not triggering:
            return {
                "status": "skipped",
                "reason": "no_triggering_insights",
            }

        try:
            # Lazy import to avoid circular dependencies
            from world_model.service import get_world_model_service

            # Get singleton service instance (DB-backed)
            if not hasattr(self, "_world_model_service"):
                self._world_model_service = get_world_model_service()

            # Delegate to service
            result = await self._world_model_service.update_from_insights(triggering)

            logger.info(f"World model updated: {result}")
            return result

        except Exception as e:
            logger.error(f"World model update failed: {e}")
            # Log to error telemetry (non-blocking)
            try:
                from core.error_tracking import log_error_to_graph
                import asyncio

                asyncio.create_task(
                    log_error_to_graph(
                        error=e,
                        context={"insights_count": len(triggering)},
                        source="memory.substrate_service.world_model_update",
                    )
                )
            except ImportError:
                pass
            return {
                "status": "error",
                "error": str(e),
                "insights_attempted": len(triggering),
            }

    async def get_facts_by_subject(
        self,
        subject: Optional[str],
        predicate: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve knowledge facts by subject.

        Args:
            subject: Subject to search for (None or empty returns all facts)
            predicate: Optional predicate filter
            limit: Maximum facts to return

        Returns:
            List of facts as dicts
        """
        rows = await self._repository.get_facts_by_subject(
            subject=subject or "",
            predicate=predicate,
            limit=limit,
        )
        return [row.model_dump(mode="json") for row in rows]

    # =========================================================================
    # Health & Status
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all substrate components.

        Returns:
            Health status dict
        """
        db_health = await self._repository.health_check()

        # Update Prometheus health gauge
        is_healthy = db_health["status"] == "healthy"
        set_memory_substrate_health(is_healthy)

        return {
            "status": db_health["status"],
            "components": {
                "database": db_health,
                "embedding_provider": {
                    "type": type(self._embedding_provider).__name__,
                    "dimensions": self._embedding_provider.dimensions,
                },
                "dag": {
                    "status": "ready",
                },
            },
        }

    # =========================================================================
    # v3.1 Module Accessors
    # =========================================================================

    def get_query_classifier(self) -> Optional[QueryClassifier]:
        """
        Get query classifier instance (lazy initialization).
        
        Returns:
            QueryClassifier instance, or None if unavailable
        """
        if self._query_classifier is None:
            try:
                self._query_classifier = get_query_classifier()
            except Exception as e:
                logger.warning("Failed to initialize query classifier", error=str(e))
                return None
        return self._query_classifier

    def get_reasoning_replay(self) -> Optional[ReasoningReplayPipeline]:
        """
        Get reasoning replay pipeline instance (lazy initialization).
        
        Returns:
            ReasoningReplayPipeline instance, or None if unavailable
        """
        if self._reasoning_replay is None:
            try:
                self._reasoning_replay = ReasoningReplayPipeline(repository=self._repository)
            except Exception as e:
                logger.warning("Failed to initialize reasoning replay", error=str(e))
                return None
        return self._reasoning_replay

    def get_consolidation(self, dry_run: bool = False) -> Optional[ConsolidationPipeline]:
        """
        Get consolidation pipeline instance (lazy initialization).
        
        Args:
            dry_run: If True, consolidation runs in dry-run mode
            
        Returns:
            ConsolidationPipeline instance, or None if unavailable
        """
        if self._consolidation is None:
            try:
                self._consolidation = ConsolidationPipeline(
                    repository=self._repository,
                    dry_run=dry_run,
                )
            except Exception as e:
                logger.warning("Failed to initialize consolidation", error=str(e))
                return None
        return self._consolidation

    def get_agent_persistence(self) -> Optional[AgentPersistenceService]:
        """
        Get agent persistence service instance (lazy initialization).
        
        Returns:
            AgentPersistenceService instance, or None if unavailable
        """
        if self._agent_persistence is None:
            try:
                self._agent_persistence = AgentPersistenceService(
                    service=self,
                    repository=self._repository,
                )
            except Exception as e:
                logger.warning("Failed to initialize agent persistence", error=str(e))
                return None
        return self._agent_persistence


# =============================================================================
# Factory Function
# =============================================================================


async def create_substrate_service(
    database_url: str,
    embedding_provider_type: str = "openai",
    embedding_model: str = "text-embedding-3-large",
    openai_api_key: Optional[str] = None,
    db_pool_size: int = 5,
    db_max_overflow: int = 10,
) -> MemorySubstrateService:
    """
    Factory function to create a fully configured MemorySubstrateService.

    Args:
        database_url: Postgres DSN
        embedding_provider_type: "openai" or "stub"
        embedding_model: Model name for OpenAI
        openai_api_key: API key for OpenAI
        db_pool_size: Connection pool size
        db_max_overflow: Pool overflow limit

    Returns:
        Configured MemorySubstrateService
    """
    # Create repository
    repository = SubstrateRepository(
        database_url=database_url,
        pool_size=db_pool_size,
        max_overflow=db_max_overflow,
    )
    await repository.connect()

    # Create embedding provider
    embedding_provider = create_embedding_provider(
        provider_type=embedding_provider_type,
        model=embedding_model,
        api_key=openai_api_key,
    )

    # Create and return service
    return MemorySubstrateService(
        repository=repository,
        embedding_provider=embedding_provider,
    )


# Singleton instance
_service: Optional[MemorySubstrateService] = None


async def get_service() -> MemorySubstrateService:
    """Get service singleton (must be initialized first)."""
    if _service is None:
        raise RuntimeError("Service not initialized. Call init_service() first.")
    return _service


async def init_service(
    database_url: str,
    **kwargs,
) -> MemorySubstrateService:
    """Initialize the service singleton."""
    global _service
    _service = await create_substrate_service(database_url, **kwargs)
    return _service


async def close_service() -> None:
    """Close the service and release resources."""
    global _service
    if _service:
        await _service._repository.disconnect()
        _service = None
