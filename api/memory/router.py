"""
L9 Memory API Router
Version: 1.2.0 (GMP-68: Governance Gate)

Memory substrate API endpoints using MemorySubstrateService.
All packets are automatically ingested via canonical ingest_packet().
"""

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "API-OPER-001",
    "component_name": "Router",
    "module_version": "1.2.0 (GMP-68: Governance Gate)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-18T01:57:26Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "router",
    "type": "router",
    "status": "active",
    "purpose": "Provides router components including PacketRequest, PacketResponse, BatchRequest",
    "integrates_with": {
        "api_endpoints": [
            "POST /test",
            "POST /packet",
            "POST /semantic/search",
            "GET /stats",
            "GET /packet/{packet_id}",
            "GET /thread/{thread_id}",
            "GET /lineage/{packet_id}",
            "POST /hybrid/search",
            "GET /facts",
            "GET /insights",
        ],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "api.server",
            "api.server_memory",
            "tests.integration.test_memory_packet_golden_path",
            "tests.memory.test_substrate_alignment",
            "tests.smoke_test",
            "tests.smoke_test_root",
        ],
    },
}
# ============================================================================

import json
import os
from collections.abc import AsyncGenerator
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from api.auth import verify_api_key
from api.routes.registry import router_registry
from core.decorators import must_stay_async
from core.observability import (
    observability_context,
    set_trace_context_from_headers,
)
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from core.schemas import PacketEnvelopeIn, SemanticSearchRequest
from memory.governance_gate import build_governance_context, governance_context
from memory.housekeeping import get_housekeeping_engine
from memory.ingestion import ingest_packet
from memory.retrieval import get_retrieval_pipeline
from memory.saga import SagaResult
from memory.substrate_service import get_service
from orchestrators.memory.interface import MemoryOperation, MemoryRequest
from orchestrators.memory.orchestrator import MemoryOrchestrator

logger = structlog.get_logger(__name__)


@must_stay_async("callers use await")
async def memory_governance_context_dependency(
    _: bool = Depends(verify_api_key),
) -> AsyncGenerator[None, None]:
    """Dependency that establishes governance context for memory routes."""
    scope = os.getenv("L9_MEMORY_SCOPE", "shared")
    project_id = os.getenv("L9_PROJECT_ID", "l9")
    ctx = build_governance_context(
        caller_id="api",
        role="end_user",
        scope=scope,
        project_id=project_id,
        allowed_scopes=[scope],
    )
    async with governance_context(ctx):
        yield


router = APIRouter(dependencies=[Depends(memory_governance_context_dependency)])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="/api/v1/memory",
    tags=["memory"],
    module_id="memory_substrate",
    display_name="Memory Substrate API",
    dependencies=["memory_service"],
)

_batch_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=10,
        window_seconds=60,
        reset_timeout=30,
        name="memory_batch",
    )
)

# ============================================================================
# Dependency: Get MemoryOrchestrator from app.state


def get_memory_orchestrator(request: Request) -> MemoryOrchestrator:
    """Get MemoryOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "memory_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="MemoryOrchestrator not initialized. Check server logs.",
        )
    return orchestrator


class PacketRequest(BaseModel):
    """Request model for packet ingestion (PacketEnvelope v2.0 compatible)."""

    packet_type: str
    payload: dict
    metadata: dict | None = None
    provenance: dict | None = None
    confidence: dict | None = None
    # v2.0 additions
    thread_id: str | None = None
    tags: list[str] | None = None
    ttl: int | None = None  # seconds until expiration


class PacketResponse(BaseModel):
    """Response model for packet ingestion."""

    packet_id: str
    status: str
    written_tables: list[str]
    error_message: str | None = None


@router.post("/test")
@must_stay_async("FastAPI/ASGI route handler")
async def memory_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify memory router is reachable."""
    return {"ok": True, "msg": "memory endpoint reachable"}


@router.post("/packet", response_model=PacketResponse)
@must_stay_async("callers use await")
async def create_packet(
    http_request: Request,
    request: PacketRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Ingest a packet into memory substrate.

    This is the canonical entrypoint for all packet ingestion.
    All packets pass through ingest_packet() which runs the full DAG pipeline.
    """
    # Extract W3C trace context from headers for distributed tracing
    set_trace_context_from_headers(dict(http_request.headers))

    async with observability_context(
        "memory_packet_ingest",
        packet_type=request.packet_type,
    ):
        try:
            # Convert thread_id string to UUID if provided
            thread_uuid = None
            if request.thread_id:
                from uuid import UUID

                try:
                    thread_uuid = UUID(request.thread_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid thread_id: {request.thread_id}",
                    ) from None

            # Convert request to PacketEnvelopeIn (v2.0 compatible)
            packet_in = PacketEnvelopeIn(
                packet_type=request.packet_type,
                payload=request.payload,
                metadata=request.metadata,
                provenance=request.provenance,
                confidence=request.confidence,
                thread_id=thread_uuid,
                tags=request.tags,
                ttl=request.ttl,
            )

            # Canonical ingestion entrypoint
            result = await ingest_packet(packet_in)

            return PacketResponse(
                packet_id=str(result.packet_id),
                status=result.status,
                written_tables=result.written_tables,
                error_message=result.error_message,
            )
        except RuntimeError as e:
            # Memory system not initialized
            logger.error(f"Memory system not initialized: {e}")
            raise HTTPException(
                status_code=503,
                detail="Memory system not available. Check server logs for initialization errors.",
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Packet ingestion failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Packet ingestion failed: {e!s}"
            ) from e


@router.post("/semantic/search")
async def semantic_search(
    http_request: Request,
    request: SemanticSearchRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Perform semantic search on memory substrate."""
    # Extract W3C trace context from headers for distributed tracing
    set_trace_context_from_headers(dict(http_request.headers))

    async with observability_context(
        "memory_semantic_search",
        query_length=len(request.query) if request.query else 0,
        top_k=request.top_k,
    ):
        try:
            service = await get_service()
            result = await service.semantic_search(request)
            return result.model_dump(mode="json")
        except RuntimeError as e:
            logger.error(f"Memory system not initialized: {e}")
            raise HTTPException(
                status_code=503, detail="Memory system not available."
            ) from e
        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


@router.get("/stats")
async def get_stats(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get memory system statistics."""
    try:
        service = await get_service()
        health = await service.health_check()

        # Get packet count
        repo = service._repository

        async with repo.acquire() as conn:
            packet_count = await conn.fetchval("SELECT COUNT(*) FROM packet_store")
            embedding_count = await conn.fetchval(
                "SELECT COUNT(*) FROM semantic_memory"
            )
            fact_count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_facts")

        return {
            "status": "operational",
            "packets": packet_count,
            "embeddings": embedding_count,
            "facts": fact_count,
            "health": health,
        }
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        return {
            "status": "unavailable",
            "error": "Memory system not initialized",
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stats failed: {e!s}") from e


@router.get("/packet/{packet_id}")
async def get_packet(
    packet_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get packet by ID."""
    try:
        service = await get_service()
        packet = await service.get_packet(packet_id)
        if packet is None:
            raise HTTPException(status_code=404, detail=f"Packet {packet_id} not found")
        return packet
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get packet failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get packet failed: {e!s}") from e


@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    limit: int = Query(100, ge=1, le=1000),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get all packets in a conversation thread."""
    try:
        pipeline = get_retrieval_pipeline()
        service = await get_service()
        pipeline.set_repository(service._repository)
        pipeline.set_semantic_service(service._semantic_service)

        thread_uuid = UUID(thread_id)
        packets = await pipeline.fetch_thread(thread_uuid, limit=limit, order=order)
        return {"thread_id": thread_id, "packets": packets, "count": len(packets)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid thread_id: {e!s}") from e
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get thread failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get thread failed: {e!s}") from e


@router.get("/lineage/{packet_id}")
async def get_lineage(
    packet_id: str,
    direction: str = Query("ancestors", pattern="^(ancestors|descendants)$"),
    max_depth: int = Query(10, ge=1, le=50),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get packet lineage graph."""
    try:
        pipeline = get_retrieval_pipeline()
        service = await get_service()
        pipeline.set_repository(service._repository)
        pipeline.set_semantic_service(service._semantic_service)

        packet_uuid = UUID(packet_id)
        return await pipeline.fetch_lineage(
            packet_uuid, direction=direction, max_depth=max_depth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {e!s}") from e
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get lineage failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get lineage failed: {e!s}") from e


@router.post("/hybrid/search")
@must_stay_async("callers use await")
async def hybrid_search(
    http_request: Request,
    query: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=100),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    agent_id: str | None = Query(None),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Perform hybrid search (semantic + structured filters).

    Client sends query params (query, top_k, agent_id, min_score) AND JSON body for filters.
    """
    # Extract W3C trace context from headers for distributed tracing
    set_trace_context_from_headers(dict(http_request.headers))

    async with observability_context(
        "memory_hybrid_search",
        query_length=len(query),
        top_k=top_k,
        agent_id=agent_id,
    ):
        try:
            # Read filters from request body (client sends filters as JSON body)
            filters = {}
            try:
                body = await http_request.json()
                if isinstance(body, dict):
                    filters = body
            except (json.JSONDecodeError, ValueError):
                # No body or invalid JSON - use empty filters
                pass

            pipeline = get_retrieval_pipeline()
            service = await get_service()
            pipeline.set_repository(service._repository)
            pipeline.set_semantic_service(service._semantic_service)

            return await pipeline.hybrid_search(
                query=query,
                top_k=top_k,
                filters=filters,
                agent_id=agent_id,
                min_score=min_score,
            )
        except RuntimeError as e:
            logger.error(f"Memory system not initialized: {e}")
            raise HTTPException(
                status_code=503, detail="Memory system not available."
            ) from e
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Hybrid search failed: {e!s}"
            ) from e


@router.get("/facts")
async def get_facts(
    subject: str | None = Query(None),
    predicate: str | None = Query(None),
    source_packet: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Query knowledge facts."""
    try:
        service = await get_service()

        # If source_packet provided, filter by it
        if source_packet:
            try:
                packet_uuid = UUID(source_packet)
                repo = service._repository
                facts_by_packet = await repo.get_facts_by_packet(packet_uuid, limit)
                facts = [f.model_dump(mode="json") for f in facts_by_packet]
            except ValueError:
                facts = []
        else:
            # If subject is None or empty, pass None to get all facts
            facts = await service.get_facts_by_subject(
                subject=subject if subject else None,
                predicate=predicate,
                limit=limit,
            )

        return {"facts": facts, "count": len(facts)}
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get facts failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get facts failed: {e!s}") from e


@router.get("/insights")
async def get_insights(
    packet_id: str | None = Query(None),
    insight_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Query extracted insights."""
    try:
        pipeline = get_retrieval_pipeline()
        service = await get_service()
        pipeline.set_repository(service._repository)
        pipeline.set_semantic_service(service._semantic_service)

        packet_uuid = UUID(packet_id) if packet_id else None
        insights = await pipeline.fetch_insights(
            packet_id=packet_uuid,
            insight_type=insight_type,
            limit=limit,
        )
        return {"insights": insights, "count": len(insights)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {e!s}") from e
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get insights failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Get insights failed: {e!s}"
        ) from e


@router.post("/gc/run")
async def run_gc(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Run garbage collection cycle."""
    try:
        service = await get_service()
        engine = get_housekeeping_engine()
        engine.set_repository(service._repository)

        return await engine.run_full_gc()
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"GC run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GC run failed: {e!s}") from e


@router.get("/gc/stats")
async def get_gc_stats(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get garbage collection statistics."""
    try:
        service = await get_service()
        engine = get_housekeeping_engine()
        engine.set_repository(service._repository)

        return await engine.get_gc_stats()
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Get GC stats failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Get GC stats failed: {e!s}"
        ) from e


@router.get("/health")
async def health_check(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Health check for memory subsystem."""
    try:
        service = await get_service()
        return await service.health_check()
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        return {
            "status": "unavailable",
            "error": "Memory system not initialized",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "degraded",
            "error": str(e),
        }


# ============================================================================
# Orchestrator-based Endpoints (Wire-Orchestrators-v1.0)


class BatchRequest(BaseModel):
    """Request model for batch packet ingestion."""

    packets: list[dict]
    batch_size: int = 100


class BatchResponse(BaseModel):
    """Response model for batch operations."""

    success: bool
    processed_count: int
    errors: list[str] = []


class CompactResponse(BaseModel):
    """Response model for compact operation."""

    success: bool
    message: str


@router.post("/batch", response_model=BatchResponse)
@must_stay_async("callers use await")
async def batch_write(
    http_request: Request,
    request: BatchRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
):
    """
    Batch write multiple packets via MemoryOrchestrator.

    This endpoint processes packets in batches for efficient bulk ingestion.
    """
    # Extract W3C trace context from headers for distributed tracing
    set_trace_context_from_headers(dict(http_request.headers))

    async with observability_context(
        "memory_batch_write",
        packet_count=len(request.packets),
        batch_size=request.batch_size,
    ):
        if _batch_circuit_breaker.is_open():
            cb_stats = _batch_circuit_breaker.get_stats()
            logger.warning(
                "batch_circuit_breaker_open",
                failures_in_window=cb_stats["failures_in_window"],
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Circuit breaker open: "
                    f"{cb_stats['failures_in_window']} failures in "
                    f"{cb_stats['window_seconds']}s"
                ),
            )

        try:
            logger.info(
                "Batch write request",
                packet_count=len(request.packets),
                batch_size=request.batch_size,
            )

            mem_request = MemoryRequest(
                operation=MemoryOperation.BATCH_WRITE,
                packets=request.packets,
            )

            result = await orchestrator.execute(mem_request)

            _batch_circuit_breaker.record_success()

            return BatchResponse(
                success=result.success,
                processed_count=result.processed_count,
                errors=result.errors,
            )
        except HTTPException:
            raise
        except Exception as e:
            _batch_circuit_breaker.record_failure(str(e))
            logger.error(f"Batch write failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Batch write failed: {e!s}"
            ) from e


@router.post("/compact", response_model=CompactResponse)
async def compact_storage(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
):
    """
    Compact/optimize memory storage via MemoryOrchestrator.

    This endpoint triggers storage optimization (vacuum, reindex, etc.).
    """
    try:
        logger.info("Compact storage request")

        mem_request = MemoryRequest(
            operation=MemoryOperation.COMPACT,
        )

        result = await orchestrator.execute(mem_request)

        return CompactResponse(
            success=result.success,
            message=result.message,
        )
    except Exception as e:
        logger.error(f"Compact failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compact failed: {e!s}") from e


# ============================================================================
# v3.1 Endpoints: Reasoning Replay & Consolidation


class ReasoningReplayRequest(BaseModel):
    """Request model for reasoning replay."""

    packet_id: str
    max_depth: int | None = None
    format: str = "narrative"  # json, narrative, graph_viz, mermaid


class ReasoningReplayResponse(BaseModel):
    """Response model for reasoning replay."""

    chain_id: str
    start_packet_id: str
    depth: int
    is_complete: bool
    explanation: str
    format: str


@router.post("/reasoning/replay", response_model=ReasoningReplayResponse)
async def reasoning_replay(
    request: ReasoningReplayRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Reconstruct and explain a decision chain (v3.1).

    Per memory_spec_v3.0.yaml pipelines.reasoning_replay:
    - reconstruct_chain(packet_id) -> ReasoningChain
    - explain_decision(packet_id, format) -> str
    """
    try:
        service = await get_service()
        replay = service.get_reasoning_replay()

        if replay is None:
            raise HTTPException(
                status_code=503,
                detail="Reasoning replay pipeline not available",
            )

        packet_id = UUID(request.packet_id)

        # Reconstruct chain
        chain = await replay.reconstruct_chain(packet_id, max_depth=request.max_depth)

        # Explain decision
        explanation = await replay.explain_decision(packet_id, format=request.format)

        return ReasoningReplayResponse(
            chain_id=str(chain.chain_id),
            start_packet_id=str(chain.start_packet_id),
            depth=chain.depth,
            is_complete=chain.is_complete,
            explanation=explanation,
            format=request.format,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {e!s}") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Reasoning replay failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Reasoning replay failed: {e!s}"
        ) from e


class ConsolidationRequest(BaseModel):
    """Request model for consolidation."""

    dry_run: bool = False
    batch_size: int = 1000
    sleep_between_batches_ms: int = 100


class ConsolidationResponse(BaseModel):
    """Response model for consolidation."""

    success: bool
    deduplication_count: int
    archived_count: int
    summarized_count: int
    expired_count: int
    errors: list[str]
    duration_seconds: float | None
    message: str


@router.post("/consolidation/run", response_model=ConsolidationResponse)
async def run_consolidation(
    request: ConsolidationRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Run memory consolidation pipeline (v3.1).

    Per memory_spec_v3.0.yaml pipelines.consolidation:
    - deduplication, archival, summarization, ttl_expiration
    - Schedule: weekly_saturday_2am_utc (manual trigger via this endpoint)
    """
    try:
        service = await get_service()
        consolidation = service.get_consolidation(dry_run=request.dry_run)

        if consolidation is None:
            raise HTTPException(
                status_code=503,
                detail="Consolidation pipeline not available",
            )

        # Run consolidation
        report = await consolidation.run_consolidation(
            batch_size=request.batch_size,
            sleep_between_batches_ms=request.sleep_between_batches_ms,
        )

        report_dict = report.to_dict()

        return ConsolidationResponse(
            success=len(report.errors) == 0,
            deduplication_count=report.deduplication_count,
            archived_count=report.archived_count,
            summarized_count=report.summarized_count,
            expired_count=report.expired_count,
            errors=report.errors,
            duration_seconds=report_dict.get("duration_seconds"),
            message=f"Consolidation complete: {report.deduplication_count} dedup, {report.archived_count} archived, {report.summarized_count} summarized, {report.expired_count} expired",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Consolidation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Consolidation failed: {e!s}"
        ) from e


# ============================================================================
# Saga Pattern Endpoints (GMP-57: Cross-DB Multi-Step Operations)


class FetchAndEnrichRequest(BaseModel):
    """Request model for fetch_and_enrich saga."""

    query: str
    limit: int = 10
    min_similarity: float = 0.5


class EnrichEntitiesRequest(BaseModel):
    """Request model for entity enrichment saga."""

    entity_ids: list[str]
    entity_type: str = "Entity"


class CorrelateTimelineRequest(BaseModel):
    """Request model for timeline correlation saga."""

    start_time: str | None = None
    end_time: str | None = None
    event_type: str | None = None
    limit: int = 50


class SagaResponse(BaseModel):
    """Response model for saga operations."""

    saga_id: str
    saga_name: str
    status: str
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    total_duration_ms: float
    output: dict | None = None
    error: str | None = None
    failed_step: str | None = None


def _saga_result_to_response(result: SagaResult) -> SagaResponse:
    """Convert SagaResult to SagaResponse."""
    return SagaResponse(
        saga_id=str(result.saga_id),
        saga_name=result.saga_name,
        status=result.status.value,
        steps_completed=result.steps_completed,
        steps_failed=result.steps_failed,
        steps_skipped=result.steps_skipped,
        total_duration_ms=result.total_duration_ms,
        output=result.output if isinstance(result.output, dict) else None,
        error=result.error,
        failed_step=result.failed_step,
    )


@router.post("/saga/fetch-and-enrich", response_model=SagaResponse)
async def saga_fetch_and_enrich(
    request: FetchAndEnrichRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute fetch_and_enrich saga (GMP-56/57).

    Cross-DB operation that:
    1. Searches vectors in Postgres for semantically similar content
    2. Extracts entity IDs from results (UUIDs, GMPs, file paths)
    3. Enriches with Neo4j graph relationships (if available)
    4. Returns combined result

    This reduces LLM reasoning steps by bundling related database
    operations into a single atomic workflow.
    """
    try:
        service = await get_service()
        result = await service.fetch_and_enrich(
            query=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity,
        )
        return _saga_result_to_response(result)
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Fetch and enrich saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {e!s}") from e


@router.post("/saga/enrich-entities", response_model=SagaResponse)
async def saga_enrich_entities(
    request: EnrichEntitiesRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute entity enrichment saga (GMP-56/57).

    For when you already have entity IDs and want graph context:
    1. Lookup entities by ID in Neo4j
    2. Discover relationships to neighboring entities
    3. Return enriched entity data with graph context
    """
    try:
        service = await get_service()
        result = await service.enrich_entities(
            entity_ids=request.entity_ids,
            entity_type=request.entity_type,
        )
        return _saga_result_to_response(result)
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Entity enrichment saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {e!s}") from e


@router.post("/saga/correlate-timeline", response_model=SagaResponse)
async def saga_correlate_timeline(
    request: CorrelateTimelineRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Execute timeline correlation saga (GMP-56/57).

    For analyzing event sequences and causal chains:
    1. Fetch events in time range from Neo4j
    2. Trace causal chains (TRIGGERED relationships)
    3. Return events with causal analysis
    """
    try:
        service = await get_service()
        result = await service.correlate_timeline(
            start_time=request.start_time,
            end_time=request.end_time,
            event_type=request.event_type,
            limit=request.limit,
        )
        return _saga_result_to_response(result)
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(
            status_code=503, detail="Memory system not available."
        ) from e
    except Exception as e:
        logger.error(f"Timeline correlation saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {e!s}") from e


# =============================================================================
# Stage 5: Predictive Memory Warming (GMP-STAGE5)


class WarmRequest(BaseModel):
    """Request for memory warming."""

    query: str
    mentioned_entities: list[str] = []
    max_gaps_to_warm: int = 10


class WarmResponse(BaseModel):
    """Response from memory warming."""

    gaps_detected: int
    gaps_addressed: int
    entities_warmed: int
    warming_latency_ms: float
    cache_metrics: dict
    error: str | None = None


@router.post("/warm", response_model=WarmResponse)
@must_stay_async("callers use await")
async def warm_memory_for_query(
    request: WarmRequest,
    req: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Predictive Memory Warming endpoint (Stage 5: GMP-STAGE5).

    Proactively warms the memory cache for an upcoming query by:
    1. Detecting knowledge gaps in mentioned entities
    2. Fetching 1-degree neighbors from Neo4j graph
    3. Caching warmed subgraphs in Redis/L1 cache

    Use this endpoint before complex agent queries to reduce
    latency by having relevant context pre-loaded.

    Args:
        query: The upcoming query text
        mentioned_entities: List of entity IDs referenced in query
        max_gaps_to_warm: Maximum number of gaps to address (default: 10)

    Returns:
        WarmResponse with gap detection stats and cache metrics
    """
    warming_service = getattr(req.app.state, "memory_warming_service", None)

    if warming_service is None:
        raise HTTPException(
            status_code=503,
            detail="Memory Warming Service not available. Check L9_MEMORY_WARMING_ENABLED.",
        )

    try:
        result = await warming_service.warm_for_query(
            query=request.query,
            mentioned_entities=request.mentioned_entities,
            max_gaps_to_warm=request.max_gaps_to_warm,
        )

        return WarmResponse(
            gaps_detected=result.get("gaps_detected", 0),
            gaps_addressed=result.get("gaps_addressed", 0),
            entities_warmed=result.get("entities_warmed", 0),
            warming_latency_ms=result.get("warming_latency_ms", 0.0),
            cache_metrics=result.get("cache_metrics", {}),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Memory warming failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Memory warming failed: {e!s}"
        ) from e


@router.get("/warm/metrics")
@must_stay_async("FastAPI/ASGI route handler")
async def get_warming_metrics(
    req: Request,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Get Memory Warming Service metrics.

    Returns comprehensive metrics including:
    - Cache hit/miss statistics
    - Warming history size
    - Entity graph size
    - L1 cache size
    """
    warming_service = getattr(req.app.state, "memory_warming_service", None)

    if warming_service is None:
        raise HTTPException(
            status_code=503,
            detail="Memory Warming Service not available. Check L9_MEMORY_WARMING_ENABLED.",
        )

    try:
        return warming_service.get_service_metrics()
    except Exception as e:
        logger.error(f"Failed to get warming metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics: {e!s}"
        ) from e


# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "API-OPER-001",
    # === GOVERNANCE ===
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": [
        "api.auth",
        "core.decorators",
        "core.observability.circuit_breaker",
        "core.schemas",
        "memory.governance_gate",
    ],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "realtime",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 50,
        "throughput_ops_per_sec": 1000,
        "availability_percent": 99.99,
        "error_rate_percent": 0.01,
    },
    # === DISCOVERY ===
    "tags": ["api-gateway", "router", "http", "operations", "rest", "api"],
    "keywords": ["router"],
    "business_value": "Provides router components including PacketRequest, PacketResponse, BatchRequest",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-18T01:57:26Z",
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
