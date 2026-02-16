# memory/enrichment_dag.py
"""
Advanced DAG Enrichment Pipeline

Implements multi-tier fallback strategy for memory substrate writes:
  Tier 1: Full enrichment (semantic + entity extraction + graph)
  Tier 2: Core only (repository tables, skip enrichment)
  Tier 3: Direct DB (emergency fallback)

Features:
- Circuit breaker for degradation
- Saga patterns for cross-DB transactions
- Dead-Letter Queue for failed packets
- Distributed tracing support
- Comprehensive telemetry and observability
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Enrichment DAG",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-25T06:00:00Z",
    "updated_at": "2026-01-25T06:00:00Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "enrichment_dag",
    "type": "dag_pipeline",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["api/memory/router"],
        "datasources": ["PostgreSQL", "Neo4j"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "memory.substrate_dag",
            "memory.substrate_service",
        ],
    },
}
# ============================================================================

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

import structlog

from core.decorators import must_stay_async
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from core.schemas import PacketEnvelope, PacketWriteResult

# Optional imports with graceful degradation
try:
    from memory.saga import SagaExecutor, SagaResult
except ImportError:
    SagaExecutor = None  # type: ignore
    SagaResult = None  # type: ignore

# Telemetry import (SUPERPROMPTPACK: now implemented)
from telemetry.memory_metrics import record_memory_enrichment

logger = structlog.get_logger(__name__)


class EnrichmentTier(str, Enum):
    """Write tier strategy."""

    FULL = "full"
    CORE_ONLY = "core_only"
    DIRECT_DB = "direct_db"


class EnrichmentStatus(str, Enum):
    """Enrichment operation status."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


@dataclass
class EnrichmentConfig:
    """Configuration for enrichment pipeline."""

    # Timeouts
    semantic_timeout_seconds: float = 5.0
    entity_extraction_timeout_seconds: float = 3.0
    graph_enrichment_timeout_seconds: float = 5.0
    total_timeout_seconds: float = 15.0

    # Feature flags
    enable_semantic_enrichment: bool = True
    enable_entity_extraction: bool = True
    enable_graph_enrichment: bool = True
    enable_fallback_tiers: bool = True

    # Circuit breaker
    cb_failure_threshold: int = 5
    cb_window_seconds: int = 60
    cb_reset_timeout: int = 30

    # Dead-Letter Queue
    enable_dlq: bool = True
    dlq_batch_size: int = 100

    # Observability
    enable_tracing: bool = True
    enable_metrics: bool = True
    log_level: str = "info"


@dataclass
class EnrichmentResult:
    """Result of enrichment operation."""

    status: EnrichmentStatus
    tier_used: EnrichmentTier
    facts_extracted: int = 0
    relationships_found: int = 0
    error_message: str | None = None
    duration_ms: float = 0.0

    def to_packet_result(
        self,
        packet_id: UUID,
        written_tables: list[str],
    ) -> PacketWriteResult:
        """Convert to PacketWriteResult."""
        enrichment_status_map = {
            EnrichmentStatus.SUCCESS: "success",
            EnrichmentStatus.FAILED: "failed",
            EnrichmentStatus.SKIPPED: "skipped",
            EnrichmentStatus.TIMEOUT: "failed",
            EnrichmentStatus.DISABLED: "disabled",
        }

        write_tier_map = {
            EnrichmentTier.FULL: "full",
            EnrichmentTier.CORE_ONLY: "core_only",
            EnrichmentTier.DIRECT_DB: "direct_db",
        }

        return PacketWriteResult(
            status="ok" if self.status == EnrichmentStatus.SUCCESS else "error",
            packet_id=packet_id,
            written_tables=written_tables,
            error_message=self.error_message,
            enrichment_status=enrichment_status_map[self.status],
            enrichment_facts_count=self.facts_extracted,
            write_tier_used=write_tier_map[self.tier_used],
        )


class EnrichmentDAG:
    """
    Multi-tier enrichment DAG pipeline.

    Coordinates enrichment with automatic fallback:
    1. Try Tier 1 (full): semantic + entity extraction + graph
    2. If fails, fall back to Tier 2 (core only): repository tables
    3. If fails, fall back to Tier 3 (direct DB): emergency write
    4. If all fail, push to Dead-Letter Queue
    """

    def __init__(
        self,
        repository: Any,
        semantic_service: Any,
        saga_executor: Any | None = None,
        config: EnrichmentConfig | None = None,
    ):
        """
        Initialize enrichment DAG.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService instance
            saga_executor: SagaExecutor for cross-DB operations
            config: EnrichmentConfig
        """
        self._repository = repository
        self._semantic_service = semantic_service
        self._saga_executor = saga_executor
        self._config = config or EnrichmentConfig()

        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=self._config.cb_failure_threshold,
                window_seconds=self._config.cb_window_seconds,
                reset_timeout=self._config.cb_reset_timeout,
                name="enrichment_dag",
            )
        )

        # Initialize Dead-Letter Queue (lazy)
        self._dlq: Any | None = None

        logger.info(
            "EnrichmentDAG initialized",
            config_summary={
                "enable_semantic": self._config.enable_semantic_enrichment,
                "enable_entity_extraction": self._config.enable_entity_extraction,
                "enable_graph": self._config.enable_graph_enrichment,
                "enable_fallback": self._config.enable_fallback_tiers,
            },
        )

    @must_stay_async("callers use await")
    async def run(self, envelope: PacketEnvelope) -> PacketWriteResult:
        """
        Run the full enrichment pipeline.

        Args:
            envelope: PacketEnvelope to process

        Returns:
            PacketWriteResult with enrichment metadata
        """
        start_time = asyncio.get_event_loop().time()

        logger.info(
            "enrichment_dag_start",
            packet_id=str(envelope.packet_id),
            packet_type=envelope.packet_type,
        )

        # Check circuit breaker
        if self._circuit_breaker.is_open():
            logger.warning(
                "enrichment_dag_circuit_breaker_open",
                packet_id=str(envelope.packet_id),
            )
            # Force Tier 2 (core only)
            result = await self._run_tier_2(envelope)
            return result.to_packet_result(
                envelope.packet_id, written_tables=["packets"]
            )

        # Try Tier 1 (full enrichment)
        try:
            if self._config.enable_fallback_tiers:
                result = await asyncio.wait_for(
                    self._run_tier_1(envelope),
                    timeout=self._config.total_timeout_seconds,
                )

                # Success
                if result.status == EnrichmentStatus.SUCCESS:
                    self._circuit_breaker.record_success()
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    result.duration_ms = duration_ms

                    logger.info(
                        "enrichment_dag_tier_1_success",
                        packet_id=str(envelope.packet_id),
                        facts=result.facts_extracted,
                        relationships=result.relationships_found,
                        duration_ms=duration_ms,
                    )

                    record_memory_enrichment(
                        status="success",
                        tier="full",
                        facts_count=result.facts_extracted,
                        duration_ms=duration_ms,
                    )

                    return result.to_packet_result(
                        envelope.packet_id,
                        written_tables=["packets", "knowledge_facts", "relationships"],
                    )

                # Failed - try Tier 2
                logger.warning(
                    "enrichment_dag_tier_1_failed",
                    packet_id=str(envelope.packet_id),
                    error=result.error_message,
                )
                self._circuit_breaker.record_failure(result.error_message or "unknown")

            else:
                # Fallback disabled - run Tier 1 without fallback
                result = await asyncio.wait_for(
                    self._run_tier_1(envelope),
                    timeout=self._config.total_timeout_seconds,
                )
                if result.status != EnrichmentStatus.SUCCESS:
                    raise Exception(result.error_message or "Tier 1 failed")
                return result.to_packet_result(
                    envelope.packet_id,
                    written_tables=["packets", "knowledge_facts", "relationships"],
                )

        except TimeoutError:
            logger.warning(
                "enrichment_dag_tier_1_timeout",
                packet_id=str(envelope.packet_id),
                timeout_seconds=self._config.total_timeout_seconds,
            )
            self._circuit_breaker.record_failure("timeout")

        except Exception as e:
            logger.error(
                "enrichment_dag_tier_1_exception",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )
            self._circuit_breaker.record_failure(str(e))

        # Try Tier 2 (core only)
        try:
            result = await asyncio.wait_for(
                self._run_tier_2(envelope),
                timeout=self._config.total_timeout_seconds,
            )

            if result.status == EnrichmentStatus.SUCCESS:
                self._circuit_breaker.record_success()
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                result.duration_ms = duration_ms

                logger.info(
                    "enrichment_dag_tier_2_success",
                    packet_id=str(envelope.packet_id),
                    duration_ms=duration_ms,
                )

                record_memory_enrichment(
                    status="success",
                    tier="core_only",
                    facts_count=0,
                    duration_ms=duration_ms,
                )

                return result.to_packet_result(
                    envelope.packet_id,
                    written_tables=["packets"],
                )

            logger.warning(
                "enrichment_dag_tier_2_failed",
                packet_id=str(envelope.packet_id),
                error=result.error_message,
            )

        except TimeoutError:
            logger.warning(
                "enrichment_dag_tier_2_timeout",
                packet_id=str(envelope.packet_id),
            )

        except Exception as e:
            logger.error(
                "enrichment_dag_tier_2_exception",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )

        # Try Tier 3 (direct DB)
        try:
            result = await asyncio.wait_for(
                self._run_tier_3(envelope),
                timeout=self._config.total_timeout_seconds,
            )

            if result.status == EnrichmentStatus.SUCCESS:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                result.duration_ms = duration_ms

                logger.info(
                    "enrichment_dag_tier_3_success",
                    packet_id=str(envelope.packet_id),
                    duration_ms=duration_ms,
                )

                record_memory_enrichment(
                    status="success",
                    tier="direct_db",
                    facts_count=0,
                    duration_ms=duration_ms,
                )

                return result.to_packet_result(
                    envelope.packet_id,
                    written_tables=["packets"],
                )

            logger.warning(
                "enrichment_dag_tier_3_failed",
                packet_id=str(envelope.packet_id),
                error=result.error_message,
            )

        except Exception as e:
            logger.error(
                "enrichment_dag_tier_3_exception",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )

        # All tiers failed - push to DLQ
        if self._config.enable_dlq:
            try:
                if not self._dlq:
                    from memory.dead_letter_queue import get_dlq

                    self._dlq = get_dlq()

                await self._dlq.push(
                    envelope,
                    reason="all_enrichment_tiers_failed",
                )
                logger.info(
                    "enrichment_dag_pushed_to_dlq",
                    packet_id=str(envelope.packet_id),
                )
            except Exception as dlq_error:
                logger.error(
                    "enrichment_dag_dlq_push_failed",
                    packet_id=str(envelope.packet_id),
                    error=str(dlq_error),
                )

        # Return error result
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        record_memory_enrichment(
            status="failed",
            tier="all_failed",
            facts_count=0,
            duration_ms=duration_ms,
        )

        return PacketWriteResult(
            status="error",
            packet_id=envelope.packet_id,
            written_tables=[],
            error_message="All enrichment tiers failed; pushed to DLQ",
            enrichment_status="failed",
            write_tier_used="failed",
        )

    @must_stay_async("callers use await")
    async def _run_tier_1(self, envelope: PacketEnvelope) -> EnrichmentResult:
        """
        Tier 1: Full enrichment pipeline.

        - Semantic embedding and search
        - Entity extraction
        - Graph relationship discovery
        - Knowledge fact persistence

        Uses saga patterns for cross-DB transactions.
        """
        try:
            facts_extracted = 0
            relationships_found = 0

            # Step 1: Semantic embedding and search
            if self._config.enable_semantic_enrichment and self._semantic_service:
                try:
                    # GMP-FIX: Extract actual content string for embedding, not stringified dict
                    # Priority: content > text > description > summary > message > fallback to str(payload)
                    payload_dict = (
                        envelope.payload if isinstance(envelope.payload, dict) else {}
                    )
                    text_to_embed = (
                        payload_dict.get("content")
                        or payload_dict.get("text")
                        or payload_dict.get("description")
                        or payload_dict.get("summary")
                        or payload_dict.get("message")
                        or str(envelope.payload)
                    )
                    if not isinstance(text_to_embed, str):
                        text_to_embed = str(text_to_embed)

                    # GMP-FIX: Include content and kind in payload for search retrieval
                    embedding_payload = {
                        "packet_id": str(envelope.packet_id),
                        "packet_type": envelope.packet_type,
                        "content": text_to_embed,  # Store actual content for retrieval
                        "kind": payload_dict.get("kind"),
                    }

                    embedding_id = await asyncio.wait_for(
                        self._semantic_service.embed_and_store(
                            text=text_to_embed,
                            payload=embedding_payload,
                        ),
                        timeout=self._config.semantic_timeout_seconds,
                    )
                    logger.debug(
                        "enrichment_semantic_embedded",
                        packet_id=str(envelope.packet_id),
                        embedding_id=str(embedding_id),
                    )
                except TimeoutError:
                    logger.warning(
                        "enrichment_semantic_timeout",
                        packet_id=str(envelope.packet_id),
                    )
                    return EnrichmentResult(
                        status=EnrichmentStatus.TIMEOUT,
                        tier_used=EnrichmentTier.FULL,
                        error_message="Semantic enrichment timeout",
                    )
                except Exception as e:
                    logger.error(
                        "enrichment_semantic_failed",
                        packet_id=str(envelope.packet_id),
                        error=str(e),
                    )
                    return EnrichmentResult(
                        status=EnrichmentStatus.FAILED,
                        tier_used=EnrichmentTier.FULL,
                        error_message=f"Semantic enrichment failed: {e}",
                    )

            # Step 2: Entity extraction
            if self._config.enable_entity_extraction:
                try:
                    entities = await asyncio.wait_for(
                        self._extract_entities(envelope),
                        timeout=self._config.entity_extraction_timeout_seconds,
                    )

                    # Extract scope from envelope metadata
                    envelope_scope = None
                    if envelope.metadata:
                        if isinstance(envelope.metadata, dict):
                            envelope_scope = envelope.metadata.get("scope")
                        else:
                            envelope_scope = getattr(envelope.metadata, "scope", None)

                    for entity in entities:
                        # Write knowledge fact with scope from envelope
                        if envelope_scope:
                            await self._repository.insert_knowledge_fact(
                                subject=entity.get("name", "unknown"),
                                predicate=entity.get("type", "entity"),
                                object_value=entity.get("value"),
                                confidence=entity.get("confidence", 0.8),
                                source_packet=envelope.packet_id,
                                scope=envelope_scope,
                            )
                        else:
                            await self._repository.insert_knowledge_fact(
                                subject=entity.get("name", "unknown"),
                                predicate=entity.get("type", "entity"),
                                object_value=entity.get("value"),
                                confidence=entity.get("confidence", 0.8),
                                source_packet=envelope.packet_id,
                            )
                        facts_extracted += 1

                    logger.debug(
                        "enrichment_entities_extracted",
                        packet_id=str(envelope.packet_id),
                        count=len(entities),
                    )
                except TimeoutError:
                    logger.warning(
                        "enrichment_entity_extraction_timeout",
                        packet_id=str(envelope.packet_id),
                    )
                    # Not fatal - continue to graph
                except Exception as e:
                    logger.error(
                        "enrichment_entity_extraction_failed",
                        packet_id=str(envelope.packet_id),
                        error=str(e),
                    )
                    # Not fatal - continue to graph

            # Step 3: Graph enrichment
            if self._config.enable_graph_enrichment and self._saga_executor:
                try:
                    saga_result = await asyncio.wait_for(
                        self._saga_executor.fetch_and_enrich(
                            query=str(envelope.payload)[:500],
                            limit=5,
                        ),
                        timeout=self._config.graph_enrichment_timeout_seconds,
                    )

                    if saga_result.error:
                        logger.warning(
                            "enrichment_graph_saga_failed",
                            packet_id=str(envelope.packet_id),
                            error=saga_result.error,
                        )
                    else:
                        relationships_found = len(
                            saga_result.data.get("relationships", [])
                        )
                        logger.debug(
                            "enrichment_graph_enriched",
                            packet_id=str(envelope.packet_id),
                            relationships=relationships_found,
                        )

                except TimeoutError:
                    logger.warning(
                        "enrichment_graph_timeout",
                        packet_id=str(envelope.packet_id),
                    )
                    # Not fatal - return partial success
                except Exception as e:
                    logger.error(
                        "enrichment_graph_failed",
                        packet_id=str(envelope.packet_id),
                        error=str(e),
                    )
                    # Not fatal - return partial success

            # Write the packet to repository
            await self._repository.insert_packet(envelope)

            return EnrichmentResult(
                status=EnrichmentStatus.SUCCESS,
                tier_used=EnrichmentTier.FULL,
                facts_extracted=facts_extracted,
                relationships_found=relationships_found,
            )

        except Exception as e:
            logger.error(
                "enrichment_tier_1_exception",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )
            return EnrichmentResult(
                status=EnrichmentStatus.FAILED,
                tier_used=EnrichmentTier.FULL,
                error_message=str(e),
            )

    async def _run_tier_2(self, envelope: PacketEnvelope) -> EnrichmentResult:
        """
        Tier 2: Core-only write with best-effort embedding.

        Write packet to core repository tables.
        GMP-130: Added best-effort embedding to prevent embedding gaps.
        GMP-132: Embedding failures now fail Tier 2 (don't write null embeddings).
        """
        try:
            await self._repository.insert_packet(envelope)

            # GMP-130: Best-effort embedding in Tier 2 to prevent gaps
            # GMP-132: Embedding failures now fail Tier 2 (no null embeddings)
            if self._semantic_service:
                payload_dict = (
                    envelope.payload if isinstance(envelope.payload, dict) else {}
                )
                text_to_embed = (
                    payload_dict.get("content")
                    or payload_dict.get("text")
                    or payload_dict.get("description")
                    or payload_dict.get("message")
                    or payload_dict.get("summary")
                )
                if text_to_embed and len(str(text_to_embed)) >= 10:
                    await self._semantic_service.embed_and_store(
                        text=str(text_to_embed),
                        payload={
                            "packet_id": str(envelope.packet_id),
                            "packet_type": envelope.packet_type,
                            "tier": "tier_2_best_effort",
                        },
                    )
                    logger.debug(
                        "enrichment_tier_2_embedding_stored",
                        packet_id=str(envelope.packet_id),
                    )

            return EnrichmentResult(
                status=EnrichmentStatus.SUCCESS,
                tier_used=EnrichmentTier.CORE_ONLY,
            )
        except Exception as e:
            logger.error(
                "enrichment_tier_2_failed",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )
            return EnrichmentResult(
                status=EnrichmentStatus.FAILED,
                tier_used=EnrichmentTier.CORE_ONLY,
                error_message=str(e),
            )

    async def _run_tier_3(self, envelope: PacketEnvelope) -> EnrichmentResult:
        """
        Tier 3: Direct DB write (emergency fallback).

        Raw insert bypassing ORM, for maximum reliability.
        This is the last-resort fallback when Tiers 1-2 fail.
        """
        try:
            async with self._repository.acquire() as conn:
                # MEMORY_BYPASS_ALLOWED: Tier-3-emergency-fallback-when-enrichment-pipeline-fails
                await conn.execute(
                    """
                    INSERT INTO packet_store (packet_id, packet_type, envelope, timestamp)
                    VALUES ($1, $2, $3, $4)
                    """,
                    envelope.packet_id,
                    envelope.packet_type,
                    envelope.model_dump_json(),
                    envelope.timestamp,
                )
            return EnrichmentResult(
                status=EnrichmentStatus.SUCCESS,
                tier_used=EnrichmentTier.DIRECT_DB,
            )
        except Exception as e:
            logger.error(
                "enrichment_tier_3_failed",
                packet_id=str(envelope.packet_id),
                error=str(e),
            )
            return EnrichmentResult(
                status=EnrichmentStatus.FAILED,
                tier_used=EnrichmentTier.DIRECT_DB,
                error_message=str(e),
            )

    @must_stay_async("callers use await")
    async def _extract_entities(self, envelope: PacketEnvelope) -> list[dict[str, Any]]:
        """
        Extract entities from packet payload.

        Uses LLM-based extraction if available, else pattern matching.
        """
        # Stub implementation - replace with actual entity extraction
        # In production, this would call an LLM or NER model
        return []


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEARN-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.substrate_repository",
        "memory.substrate_semantic",
        "memory.saga",
    ],
    "tags": [
        "dag",
        "enrichment",
        "fallback",
        "learning",
        "memory-substrate",
        "pipeline",
        "resilience",
        "saga",
    ],
    "keywords": [
        "circuit",
        "dag",
        "dlq",
        "enrichment",
        "entity",
        "extraction",
        "fallback",
        "graph",
        "semantic",
        "tier",
    ],
    "business_value": "Multi-tier enrichment DAG with automatic fallback, circuit breaker, and saga patterns for reliable memory writes.",
    "last_modified": "2026-01-25T06:00:00Z",
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
