# ============================================================================
__dora_meta__ = {
    "component_name": "Router",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T12:08:12Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "router",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["POST /test", "POST /packet", "POST /semantic/search"],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

L9 Memory API Router
Version: 1.1.0

Memory substrate API endpoints using MemorySubstrateService.
All packets are automatically ingested via canonical ingest_packet().
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from api.auth import verify_api_key
from typing import Optional, List
from uuid import UUID
import structlog

from memory.substrate_service import get_service
from memory.substrate_models import PacketEnvelopeIn, SemanticSearchRequest
from memory.ingestion import ingest_packet
from memory.retrieval import get_retrieval_pipeline
from memory.housekeeping import get_housekeeping_engine
from orchestrators.memory.interface import MemoryRequest, MemoryOperation
from orchestrators.memory.orchestrator import MemoryOrchestrator
from memory.reasoning_replay import ReasoningReplayPipeline
from memory.consolidation import ConsolidationPipeline

logger = structlog.get_logger(__name__)

router = APIRouter()

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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "api-gateway", "async", "auth", "endpoint", "logging", "messaging", "operations", "pydantic", "router"],
    "keywords": ["create", "memory", "orchestrator", "packet", "router", "search", "semantic", "test"],
    "business_value": "Utility module for router",
    "last_modified": "2026-01-14T12:10:12Z",
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
