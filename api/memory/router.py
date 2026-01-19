"""
L9 Memory API Router
Version: 1.1.0

Memory substrate API endpoints using MemorySubstrateService.
All packets are automatically ingested via canonical ingest_packet().
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from api.auth import CallerIdentity, verify_api_key
from typing import Optional, List, AsyncGenerator
from uuid import UUID
import structlog
import os

from memory.substrate_service import get_service
from core.schemas import PacketEnvelopeIn, SemanticSearchRequest
from memory.ingestion import ingest_packet
from memory.retrieval import get_retrieval_pipeline
from memory.housekeeping import get_housekeeping_engine
from orchestrators.memory.interface import MemoryRequest, MemoryOperation
from orchestrators.memory.orchestrator import MemoryOrchestrator
from memory.saga import SagaResult
from memory.governance_gate import (
    build_governance_context,
    build_scope_project_filter,
    governance_context,
    require_governance_context,
)

logger = structlog.get_logger(__name__)

async def memory_governance_context_dependency(
    caller: CallerIdentity = Depends(verify_api_key),
) -> AsyncGenerator[None, None]:
    """
    Establish a governance context for all /api/memory routes
    based on the authenticated caller identity.
    """
    scope = os.getenv("L9_MEMORY_SCOPE", "developer")
    if scope not in caller.allowed_scopes:
        scope = (
            "developer"
            if "developer" in caller.allowed_scopes
            else caller.allowed_scopes[0]
        )
    project_id = os.getenv("L9_PROJECT_ID", "l9")

    ctx = build_governance_context(
        caller_id=caller.caller_id,
        role="end_user",
        scope=scope,
        project_id=project_id,
        allowed_scopes=list(caller.allowed_scopes),
        creator=caller.creator,
        source=caller.source,
    )
    async with governance_context(ctx):
        yield


router = APIRouter(dependencies=[Depends(memory_governance_context_dependency)])


# ============================================================================
# Dependency: Get MemoryOrchestrator from app.state
# ============================================================================


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
    metadata: Optional[dict] = None
    provenance: Optional[dict] = None
    confidence: Optional[dict] = None
    # v2.0 additions
    thread_id: Optional[str] = None
    tags: Optional[List[str]] = None
    ttl: Optional[int] = None  # seconds until expiration


class PacketResponse(BaseModel):
    """Response model for packet ingestion."""

    packet_id: str
    status: str
    written_tables: List[str]
    error_message: Optional[str] = None


@router.post("/test")
async def memory_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify memory router is reachable."""
    return {"ok": True, "msg": "memory endpoint reachable"}


@router.post("/packet", response_model=PacketResponse)
async def create_packet(
    request: PacketRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Ingest a packet into memory substrate.

    This is the canonical entrypoint for all packet ingestion.
    All packets pass through ingest_packet() which runs the full DAG pipeline.
    """
    try:
        # Convert thread_id string to UUID if provided
        thread_uuid = None
        if request.thread_id:
            from uuid import UUID as UUIDType
            try:
                thread_uuid = UUIDType(request.thread_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid thread_id: {request.thread_id}")
        
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
        )
    except Exception as e:
        logger.error(f"Packet ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Packet ingestion failed: {str(e)}"
        )


@router.post("/semantic/search")
async def semantic_search(
    request: SemanticSearchRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Perform semantic search on memory substrate."""
    try:
        service = await get_service()
        result = await service.semantic_search(request)
        return result.model_dump(mode="json")
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats")
async def get_stats(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get memory system statistics."""
    try:
        ctx = require_governance_context("memory.stats")
        service = await get_service()
        health = await service.health_check()

        # Get packet count
        repo = service._repository

        async with repo.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=1, table_alias="packet_store"
            )
            packet_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM packet_store WHERE TRUE {filter_clause}",
                *params,
            )
            embedding_count = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM semantic_memory
                INNER JOIN packet_store ON packet_store.packet_id = (semantic_memory.payload->>'packet_id')::uuid
                WHERE TRUE {filter_clause}
                """,
                *params,
            )
            fact_count = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE TRUE {filter_clause}
                """,
                *params,
            )

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
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


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
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get packet failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get packet failed: {str(e)}")


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
        raise HTTPException(status_code=400, detail=f"Invalid thread_id: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get thread failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get thread failed: {str(e)}")


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
        lineage = await pipeline.fetch_lineage(
            packet_uuid, direction=direction, max_depth=max_depth
        )
        return lineage
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get lineage failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get lineage failed: {str(e)}")


@router.post("/hybrid/search")
async def hybrid_search(
    request: Request,
    query: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=100),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    agent_id: Optional[str] = Query(None),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Perform hybrid search (semantic + structured filters).

    Client sends query params (query, top_k, agent_id, min_score) AND JSON body for filters.
    """
    try:
        # Read filters from request body (client sends filters as JSON body)
        filters = {}
        try:
            body = await request.json()
            if isinstance(body, dict):
                filters = body
        except (json.JSONDecodeError, ValueError):
            # No body or invalid JSON - use empty filters
            pass

        pipeline = get_retrieval_pipeline()
        service = await get_service()
        pipeline.set_repository(service._repository)
        pipeline.set_semantic_service(service._semantic_service)

        result = await pipeline.hybrid_search(
            query=query,
            top_k=top_k,
            filters=filters,
            agent_id=agent_id,
            min_score=min_score,
        )
        return result
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.get("/facts")
async def get_facts(
    subject: Optional[str] = Query(None),
    predicate: Optional[str] = Query(None),
    source_packet: Optional[str] = Query(None),
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
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get facts failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get facts failed: {str(e)}")


@router.get("/insights")
async def get_insights(
    packet_id: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
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
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get insights failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get insights failed: {str(e)}")


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

        result = await engine.run_full_gc()
        return result
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"GC run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GC run failed: {str(e)}")


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

        stats = await engine.get_gc_stats()
        return stats
    except RuntimeError as e:
        logger.error(f"Memory system not initialized: {e}")
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Get GC stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Get GC stats failed: {str(e)}")


@router.get("/health")
async def health_check(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Health check for memory subsystem."""
    try:
        service = await get_service()
        health = await service.health_check()
        return health
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
# ============================================================================


class BatchRequest(BaseModel):
    """Request model for batch packet ingestion."""

    packets: List[dict]
    batch_size: int = 100


class BatchResponse(BaseModel):
    """Response model for batch operations."""

    success: bool
    processed_count: int
    errors: List[str] = []


class CompactResponse(BaseModel):
    """Response model for compact operation."""

    success: bool
    message: str


@router.post("/batch", response_model=BatchResponse)
async def batch_write(
    request: BatchRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
):
    """
    Batch write multiple packets via MemoryOrchestrator.

    This endpoint processes packets in batches for efficient bulk ingestion.
    """
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

        return BatchResponse(
            success=result.success,
            processed_count=result.processed_count,
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"Batch write failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch write failed: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Compact failed: {str(e)}")


# ============================================================================
# v3.1 Endpoints: Reasoning Replay & Consolidation
# ============================================================================


class ReasoningReplayRequest(BaseModel):
    """Request model for reasoning replay."""
    
    packet_id: str
    max_depth: Optional[int] = None
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
        raise HTTPException(status_code=400, detail=f"Invalid packet_id: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Reasoning replay failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reasoning replay failed: {str(e)}")


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
    errors: List[str]
    duration_seconds: Optional[float]
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
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Consolidation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Consolidation failed: {str(e)}")


# ============================================================================
# Saga Pattern Endpoints (GMP-57: Cross-DB Multi-Step Operations)
# ============================================================================


class FetchAndEnrichRequest(BaseModel):
    """Request model for fetch_and_enrich saga."""
    
    query: str
    limit: int = 10
    min_similarity: float = 0.5


class EnrichEntitiesRequest(BaseModel):
    """Request model for entity enrichment saga."""
    
    entity_ids: List[str]
    entity_type: str = "Entity"


class CorrelateTimelineRequest(BaseModel):
    """Request model for timeline correlation saga."""
    
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: Optional[str] = None
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
    output: Optional[dict] = None
    error: Optional[str] = None
    failed_step: Optional[str] = None


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
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Fetch and enrich saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {str(e)}")


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
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Entity enrichment saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {str(e)}")


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
        raise HTTPException(status_code=503, detail="Memory system not available.")
    except Exception as e:
        logger.error(f"Timeline correlation saga failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Saga failed: {str(e)}")
