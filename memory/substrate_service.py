"""
L9 Memory Substrate - Service Layer
Version: 1.0.0

Orchestrating service that coordinates repository, semantic, and graph layers.
Provides a unified interface for substrate operations.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Service Layer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "substrate_service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "agents.cursor.integrations.cursor_executor",
            "agents.cursor.integrations.cursor_gateway",
            "agents.l_cto",
            "api.memory.router",
            "api.routes.mcp",
            "api.server",
            "core.agents.bootstrap.orchestrator",
            "core.agents.bootstrap.phase_0_validate",
            "core.agents.bootstrap.phase_2_instantiate",
            "core.agents.bootstrap.phase_3_bind_kernels",
        ],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from typing import Any, Optional

from core.schemas import (
    PacketEnvelopeIn,
    PacketWriteResult,
    SemanticHit,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from memory.substrate_repository import SubstrateRepository
from memory.substrate_semantic import (
    SemanticService,
    EmbeddingProvider,
    StubEmbeddingProvider,
    create_embedding_provider,
)
from memory.substrate_dag import SubstrateDAG
from memory.validators.packet_validator import PacketValidator, PacketValidationError
from memory.query_classifier import QueryClassifier, get_query_classifier
from memory.reasoning_replay import ReasoningReplayPipeline
from memory.consolidation import ConsolidationPipeline
from memory.agent_persistence import AgentPersistenceService
from memory.retention_engine import RetentionEngine
from memory.saga import (
    SagaExecutor,
    SagaResult,
)
from memory.saga_patterns import (
    SagaPatterns,
)
from memory.audit_utils import prepare_packet_for_ingest
from memory.governance_gate import (
    ensure_governance_context,
    enforce_packet_governance,
    governance_context,
    require_governance_context,
)
from telemetry.memory_metrics import (
    record_memory_write,
    record_memory_search,
    set_memory_substrate_health,
    record_memory_quarantine,
    record_memory_ingest,
)
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from core.decorators import must_stay_async

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
            raise RuntimeError("Embedding provider required; missing embedding context")
        if isinstance(embedding_provider, StubEmbeddingProvider):
            raise RuntimeError("Stub embedding provider is not allowed in enforcement mode")
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
        self._retention_engine: Optional[RetentionEngine] = None

        # Initialize saga pattern (lazy initialization)
        self._saga_executor: Optional[SagaExecutor] = None
        self._saga_patterns: Optional[SagaPatterns] = None

        logger.info("MemorySubstrateService initialized")

    def _require_rls_context(self, operation: str) -> Any:
        ctx = require_governance_context(operation)
        if not ctx.tenant_id or not ctx.org_id or not ctx.user_id:
            raise RuntimeError(
                f"RLS scope required for memory operation: {operation}"
            )
        return ctx

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
            audit_mode: If True, run audit preprocessing (normalization, PII redaction, injection detection)

        Returns:
            PacketWriteResult with status and written tables
        """
        # GMP-70: Governance enforcement (fail-closed)
        ctx = self._require_rls_context("write_packet")
        if tenant_id and tenant_id != ctx.tenant_id:
            raise RuntimeError("tenant_id must be derived server-side")
        if org_id and org_id != ctx.org_id:
            raise RuntimeError("org_id must be derived server-side")
        if user_id and user_id != ctx.user_id:
            raise RuntimeError("user_id must be derived server-side")
        if role != "end_user" and role != ctx.role:
            raise RuntimeError("role must be derived server-side")
        packet_in = enforce_packet_governance(packet_in, ctx)

        logger.info(f"Processing packet: type={packet_in.packet_type}")

        # Audit mode: normalize, redact PII, detect injection markers
        audit_report = None
        if audit_mode:
            packet_in, audit_report = prepare_packet_for_ingest(packet_in)
            if audit_report.injection_markers:
                record_memory_quarantine(reason="injection_markers", count=1)
                logger.warning(
                    "Injection markers detected in packet",
                    packet_id=str(audit_report.packet_id),
                    markers=list(audit_report.injection_markers),
                )

        # Validate packet before processing (canonical chokepoint)
        try:
            PacketValidator.validate(packet_in, strict=False)
        except PacketValidationError as e:
            logger.error(
                "packet_validation_failed",
                error=str(e),
                packet_type=packet_in.packet_type,
            )
            return PacketWriteResult(
                status="error",
                packet_id=packet_in.packet_id or None,
                written_tables=[],
                error_message=f"Validation failed: {e}",
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

        # GMP-81: Always use RLS from governance context (no conditional branching)
        # RLS UUIDs are populated from rls_config.py via governance_gate._fallback_context()
        result: PacketWriteResult
        async with self._repository.transaction(
            tenant_id=ctx.tenant_id,
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            role=ctx.role,
        ):
            # Run DAG within transaction - repository methods will use RLS-scoped connection
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

        # Record Prometheus metrics for memory write (result is defined in both branches)
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

        ctx = self._require_rls_context("get_packet")
        try:
            await self.set_session_scope(
                ctx.tenant_id,
                ctx.org_id,
                ctx.user_id,
                ctx.role,
            )
            row = await self._repository.get_packet(UUID(packet_id))
            if row:
                return row.envelope
            return None
        except Exception as e:
            logger.error(f"Error retrieving packet {packet_id}: {e}")
            raise

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

        ctx = self._require_rls_context("search_packets_by_thread")
        try:
            await self.set_session_scope(
                ctx.tenant_id,
                ctx.org_id,
                ctx.user_id,
                ctx.role,
            )
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
            raise

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
            async with ensure_governance_context("search_packets_by_type") as ctx:
                await self.set_session_scope(
                    ctx.tenant_id,
                    ctx.org_id,
                    ctx.user_id,
                    ctx.role,
                )
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
            raise

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
            ctx = self._require_rls_context("query_packets")
            await self.set_session_scope(
                ctx.tenant_id,
                ctx.org_id,
                ctx.user_id,
                ctx.role,
            )

            all_packets = []

            async with governance_context(ctx):
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
                    for ptype in [
                        "insight",
                        "reflection",
                        "ir_graph",
                        "execution_plan",
                    ]:
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
            raise

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
        self._require_rls_context("semantic_search")
        logger.info(
            f"Semantic search: query='{request.query[:50]}...', min_score={request.min_score}"
        )

        # Get more results to allow filtering by min_score
        hits = await self._semantic_service.search(
            query=request.query,
            top_k=request.top_k * 2,  # Get more to allow filtering
            agent_id=request.agent_id,
        )

        # Filter by min_score threshold
        filtered_hits = [h for h in hits if h.get("score", 0.0) >= request.min_score]

        # Limit to top_k after filtering
        filtered_hits = filtered_hits[: request.top_k]

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
        self._require_rls_context("embed_text")
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

    def get_query_classifier(self) -> QueryClassifier:
        """
        Get query classifier instance (lazy initialization).

        Returns:
            QueryClassifier instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._query_classifier is not None:
            logger.debug("query_classifier already loaded")
            return self._query_classifier

        logger.info("Initializing query_classifier...")
        self._query_classifier = get_query_classifier()
        logger.info("query_classifier loaded successfully")
        return self._query_classifier

    def get_reasoning_replay(self) -> ReasoningReplayPipeline:
        """
        Get reasoning replay pipeline instance (lazy initialization).

        Returns:
            ReasoningReplayPipeline instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._reasoning_replay is not None:
            logger.debug("reasoning_replay already loaded")
            return self._reasoning_replay

        logger.info("Initializing reasoning_replay...")
        self._reasoning_replay = ReasoningReplayPipeline(repository=self._repository)
        logger.info("reasoning_replay loaded successfully")
        return self._reasoning_replay

    def get_consolidation(self, dry_run: bool = False) -> ConsolidationPipeline:
        """
        Get consolidation pipeline instance (lazy initialization).

        Args:
            dry_run: If True, consolidation runs in dry-run mode

        Returns:
            ConsolidationPipeline instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._consolidation is not None:
            logger.debug("consolidation already loaded")
            return self._consolidation

        logger.info("Initializing consolidation...", dry_run=dry_run)
        self._consolidation = ConsolidationPipeline(
            repository=self._repository,
            dry_run=dry_run,
        )
        logger.info("consolidation loaded successfully")
        return self._consolidation

    def get_agent_persistence(self) -> AgentPersistenceService:
        """
        Get agent persistence service instance (lazy initialization).

        Returns:
            AgentPersistenceService instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._agent_persistence is not None:
            logger.debug("agent_persistence already loaded")
            return self._agent_persistence

        logger.info("Initializing agent_persistence...")
        self._agent_persistence = AgentPersistenceService(
            service=self,
            repository=self._repository,
        )
        logger.info("agent_persistence loaded successfully")
        return self._agent_persistence

    def get_retention_engine(self) -> RetentionEngine:
        """
        Get retention engine instance (lazy initialization).

        The retention engine is wired with:
        - persistence: From get_agent_persistence()
        - repository: Direct reference to _repository

        Returns:
            RetentionEngine instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._retention_engine is not None:
            logger.debug("retention_engine already loaded")
            return self._retention_engine

        logger.info("Initializing retention_engine...")
        persistence = self.get_agent_persistence()
        self._retention_engine = RetentionEngine(
            persistence=persistence,
            repository=self._repository,
        )
        logger.info("retention_engine loaded successfully")
        return self._retention_engine

    # =========================================================================
    # Saga Pattern (GMP-56/57: Cross-DB Multi-Step Operations)
    # =========================================================================

    @must_stay_async("callers use await")
    async def get_saga_executor(self) -> SagaExecutor:
        """
        Get saga executor instance (lazy initialization).

        The executor is wired with:
        - postgres_pool: From repository
        - semantic_service: For vector search steps
        - neo4j_client: From graph_client (if available)

        Returns:
            SagaExecutor instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._saga_executor is not None:
            logger.debug("saga_executor already loaded")
            return self._saga_executor

        logger.info("Initializing saga_executor...")

        # Get Neo4j client if available (optional dependency)
        neo4j_client = None
        try:
            from memory.graph_client import get_graph_client

            neo4j_client = get_graph_client()
            logger.debug("Neo4j client available for saga")
        except Exception as e:
            logger.debug(f"Neo4j client not available for saga: {e}")

        self._saga_executor = SagaExecutor(
            postgres_pool=self._repository._pool,
            neo4j_client=neo4j_client,
            semantic_service=self._semantic_service,
        )
        logger.info("saga_executor loaded successfully")
        return self._saga_executor

    async def get_saga_patterns(self) -> SagaPatterns:
        """
        Get saga patterns instance (lazy initialization).

        Provides high-level API for pre-built sagas:
        - fetch_and_enrich: Vector search → Entity extraction → Graph enrichment
        - enrich_entities: Entity lookup → Relationship discovery
        - correlate_timeline: Event timeline → Causal chain analysis

        Returns:
            SagaPatterns instance

        Raises:
            Exception: If initialization fails (LOUD failure)
        """
        if self._saga_patterns is not None:
            logger.debug("saga_patterns already loaded")
            return self._saga_patterns

        logger.info("Initializing saga_patterns...")
        executor = await self.get_saga_executor()
        self._saga_patterns = SagaPatterns(executor)
        logger.info("saga_patterns loaded successfully")
        return self._saga_patterns

    async def fetch_and_enrich(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> SagaResult:
        """
        Execute fetch_and_enrich saga: Vector search → Entity extraction → Graph enrichment.

        This is the canonical cross-DB search pattern that:
        1. Searches vectors in Postgres for semantically similar content
        2. Extracts entity IDs from results (UUIDs, GMPs, file paths)
        3. Enriches with Neo4j graph relationships (if available)
        4. Returns combined result

        Args:
            query: Search query
            limit: Max vector results
            min_similarity: Minimum similarity threshold

        Returns:
            SagaResult with combined vector + graph data
        """
        patterns = await self.get_saga_patterns()
        return await patterns.fetch_and_enrich(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
        )

    async def enrich_entities(
        self,
        entity_ids: list[str],
        entity_type: str = "Entity",
    ) -> SagaResult:
        """
        Execute entity enrichment saga: Entity lookup → Relationship discovery.

        For when you already have entity IDs and want graph context.

        Args:
            entity_ids: List of entity IDs to enrich
            entity_type: Node label type (e.g., "User", "Agent", "GMP")

        Returns:
            SagaResult with entity data and relationships
        """
        patterns = await self.get_saga_patterns()
        return await patterns.enrich_entities(
            entity_ids=entity_ids,
            entity_type=entity_type,
        )

    async def correlate_timeline(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> SagaResult:
        """
        Execute timeline correlation saga: Event timeline → Causal chain analysis.

        For analyzing event sequences and causal chains in Neo4j.

        Args:
            start_time: ISO timestamp start
            end_time: ISO timestamp end
            event_type: Filter by event type
            limit: Max events

        Returns:
            SagaResult with events and causal chains
        """
        patterns = await self.get_saga_patterns()
        return await patterns.correlate_timeline(
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            limit=limit,
        )


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

    Raises:
        RuntimeError: With detailed diagnostic info if initialization fails
    """
    # === DIAGNOSTIC LOGGING ===
    logger.info(
        "substrate_service.init_start",
        database_url_set=bool(database_url),
        database_url_prefix=database_url[:30] + "..." if database_url else "NONE",
        embedding_provider_type=embedding_provider_type,
        embedding_model=embedding_model,
        openai_api_key_set=bool(openai_api_key),
        openai_api_key_prefix=openai_api_key[:8] + "..." if openai_api_key else "NONE",
        db_pool_size=db_pool_size,
    )

    # Step 1: Create repository
    try:
        logger.info("substrate_service.step1_repository_create")
        repository = SubstrateRepository(
            database_url=database_url,
            pool_size=db_pool_size,
            max_overflow=db_max_overflow,
        )
    except Exception as e:
        logger.error(
            "substrate_service.step1_repository_create_FAILED",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"SubstrateRepository creation failed: {e}") from e

    # Step 2: Connect repository to database
    try:
        logger.info("substrate_service.step2_repository_connect")
        await repository.connect()
        logger.info("substrate_service.step2_repository_connect_SUCCESS")
    except Exception as e:
        logger.error(
            "substrate_service.step2_repository_connect_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            database_url_prefix=database_url[:30] + "..." if database_url else "NONE",
        )
        raise RuntimeError(f"Database connection failed: {e}") from e

    # Step 3: Create embedding provider
    try:
        logger.info(
            "substrate_service.step3_embedding_provider_create",
            provider_type=embedding_provider_type,
            model=embedding_model,
        )
        embedding_provider = create_embedding_provider(
            provider_type=embedding_provider_type,
            model=embedding_model,
            api_key=openai_api_key,
        )
        logger.info(
            "substrate_service.step3_embedding_provider_create_SUCCESS",
            provider_class=type(embedding_provider).__name__,
        )
    except Exception as e:
        logger.error(
            "substrate_service.step3_embedding_provider_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            provider_type=embedding_provider_type,
            api_key_set=bool(openai_api_key),
        )
        raise RuntimeError(f"Embedding provider creation failed: {e}") from e

    # Step 4: Create and return service
    try:
        logger.info("substrate_service.step4_service_create")
        service = MemorySubstrateService(
            repository=repository,
            embedding_provider=embedding_provider,
        )
        logger.info("substrate_service.init_SUCCESS")
        return service
    except Exception as e:
        logger.error(
            "substrate_service.step4_service_create_FAILED",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"MemorySubstrateService creation failed: {e}") from e


# Singleton instance
_service: Optional[MemorySubstrateService] = None


@must_stay_async("callers use await")
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "MEM-LEAR-001",
    # === GOVERNANCE ===
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": [
        "core.decorators",
        "core.error_tracking",
        "core.observability.circuit_breaker",
        "core.schemas",
        "memory.agent_persistence",
    ],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 500,
        "throughput_ops_per_sec": 100,
        "availability_percent": 99.9,
        "error_rate_percent": 0.1,
    },
    # === DISCOVERY ===
    "tags": [
        "api",
        "async",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "metrics",
        "monitoring",
    ],
    "keywords": [
        "agent",
        "check",
        "checkpoint",
        "classifier",
        "close",
        "consolidation",
        "correlate",
        "create",
    ],
    "business_value": "Orchestrating service that coordinates repository, semantic, and graph layers.",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
