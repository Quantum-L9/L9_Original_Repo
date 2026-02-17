"""Memory CRUD using unified L9 substrate (packet_store + memory_embeddings).

This replaces the deprecated memory.* tables with the unified L9 memory substrate.
Uses packet_store for event log and memory_embeddings for vector storage.

MANDATORY: ALL WRITES ROUTE THROUGH MAIN L9 INGESTION PIPELINE.
- Routes through MemorySubstrateService.write_packet() for full DAG pipeline
- Gets graph sync (Neo4j), fact extraction, reasoning traces automatically
- Uses same OpenAI embeddings and processing as L agent
- NO FALLBACK: If main pipeline unavailable, returns 503 (fail-closed)
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Unified",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "api_gateway",
    "module_name": "memory_unified",
    "type": "router",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": ["POST /save", "POST /search", "GET /stats"],
        "datasources": ["Neo4j", "OpenAI API", "PostgreSQL"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [
            "tests.memory.test_governance_invariants",
            "tests.memory.test_unified_pipeline",
        ],
    },
}
# ============================================================================

import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException, Query, Request

if TYPE_CHECKING:
    from src.main import CallerIdentity

import asyncio

from config.rls_config import get_rls_config
from core.config_constants import (
    ALLOWED_SCOPES_L,
    DEFAULT_SEARCH_SCOPES,
    get_allowed_scopes_for_caller,
    get_default_project_id,
    get_default_scope_for_caller,
)
from memory.governance_gate import (
    build_governance_context,
    governance_context,
    require_governance_context,
)
from src.config import settings
from src.db import execute, fetch_all, fetch_one
from src.embeddings import embed_text

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_substrate_service(request: Request):
    """Get MemorySubstrateService from app state (if initialized)."""
    return getattr(request.app.state, "substrate_service", None)


def map_mcp_scope_to_db_scope(mcp_scope: str) -> str:
    """
    Map MCP governance scopes to DB scope values.

    GOVERNANCE INVARIANT: Scope semantics must be preserved in DB.
    After migration 0016, DB supports: 'developer', 'global', 'l-private'

    MCP scopes (input): 'developer', 'l-private', 'global'
    DB scopes (output): 'developer', 'l-private', 'global'

    NOTE: 'shared' scope is deprecated after migration 0016.
    """
    mapping = {
        "developer": "developer",  # Developer collaboration (L + Cursor)
        "l-private": "l-private",  # L's private operations (L only)
        "global": "global",  # Cross-project shared knowledge
        "cursor": "cursor",  # Cursor IDE private scope (ADR-0005)
    }
    return mapping.get(mcp_scope, "developer")  # Default to developer


def map_db_scope_to_mcp_scope(db_scope: str) -> str:
    """Reverse mapping: DB scope → MCP scope.

    After migration 0016, DB scope values match MCP scope values directly.
    Legacy 'shared' scope is mapped to 'developer' for backward compatibility.
    """
    mapping = {
        "developer": "developer",
        "l-private": "l-private",
        "global": "global",
        "cursor": "cursor",  # Cursor IDE scope (ADR-0005)
        "shared": "developer",  # Legacy fallback
    }
    return mapping.get(db_scope, "developer")


@must_stay_async("callers use await")
async def save_memory_handler(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "developer",  # MCP scope: developer/l-private/global
    duration: str = "long",
    tags: list[str] | None = None,
    importance: float = 1.0,
    metadata: dict[str, Any] | None = None,
    # Governance fields (enforced server-side, not client-provided)
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
    # REQUIRED: substrate service from app state (main ingestion pipeline)
    substrate_service: Any | None = None,
) -> dict[str, Any]:
    """
    Save memory via main L9 ingestion pipeline (GMP-89: NO FALLBACK).

    All writes MUST go through MemorySubstrateService.write_packet() which runs
    the full DAG pipeline (validation, embedding, graph sync, fact extraction).

    If substrate_service is unavailable, returns 503 Service Unavailable.
    There is NO direct DB fallback - this ensures all memory writes flow through
    the canonical pipeline with full governance, audit, and enrichment.

    Args:
        scope: MCP scope ('developer', 'l-private', 'global')
        caller_id: "L" or "C" (from API key)
        creator: "L-CTO" or "Cursor-IDE" (server-enforced)
        source: "l9-kernel" or "cursor" (server-enforced)
        substrate_service: REQUIRED MemorySubstrateService instance

    Returns:
        Dict with packet_id, written_tables, enrichment_status, etc.

    Raises:
        HTTPException 503: If substrate_service unavailable (fail-closed)
        HTTPException 403: If scope not authorized
        HTTPException 500: If ingestion fails
    """
    # FAIL-CLOSED: Validate principal
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise ValueError(
            f"user_id (principal_id) REQUIRED for save_memory. "
            f"Cannot be None/empty. Received: {user_id!r}"
        )
    validated_principal = user_id.strip()

    # GMP-68: Governance enforcement
    ctx = require_governance_context("mcp_memory.save_memory")
    if scope not in ctx.allowed_scopes:
        raise HTTPException(
            status_code=403, detail=f"Scope '{scope}' not authorized for this context"
        )

    # GMP-89: FAIL-FAST - Main pipeline is REQUIRED, no fallback
    if not substrate_service:
        logger.error(
            "save_memory_handler: substrate_service not available (fail-closed)",
            caller_id=caller_id,
            scope=scope,
        )
        raise HTTPException(
            status_code=503,
            detail="Memory substrate service unavailable. MCP memory requires main pipeline.",
        )

    # Main pipeline (ONLY path - no fallback)
    try:
        return await _save_via_main_pipeline(
            user_id=user_id,
            content=content,
            kind=kind,
            scope=scope,
            duration=duration,
            tags=tags,
            importance=importance,
            metadata=metadata,
            caller_id=caller_id,
            creator=creator,
            source=source,
            substrate_service=substrate_service,
        )

        # Enrichment failure is NOT a pipeline failure - core write succeeded
        # Just return 200 with enrichment_status="failed" (already set in result)

    except HTTPException:
        # Re-raise HTTP exceptions as-is (e.g., 500 from _save_via_main_pipeline)
        raise
    except Exception as e:
        # Unexpected error - log and return 500
        logger.error(
            "Main pipeline failed unexpectedly",
            error=str(e),
            caller_id=caller_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Memory ingestion failed: {e!s}",
        ) from e


@must_stay_async("callers use await")
async def _save_via_main_pipeline(
    user_id: str,
    content: str,
    kind: str,
    scope: str,
    duration: str,
    tags: list[str] | None,
    importance: float,
    metadata: dict[str, Any] | None,
    caller_id: str,
    creator: str,
    source: str,
    substrate_service: Any,
) -> dict[str, Any]:
    """Save memory via main L9 ingestion pipeline (full DAG)."""
    from datetime import timedelta

    from core.schemas import PacketEnvelopeIn, PacketProvenance

    # Map MCP scope to DB scope
    db_scope = map_mcp_scope_to_db_scope(scope)

    # GMP-C1-GOVERNANCE: Get project_id from governance context (not hardcoded).
    # This ensures RLS isolation uses the correct project_id per environment.
    ctx = require_governance_context("mcp_memory._save_via_main_pipeline")
    project_id = ctx.project_id

    # Calculate TTL based on duration
    ttl = None
    if duration == "short":
        ttl = datetime.now(UTC) + timedelta(hours=settings.MEMORY_SHORT_TERM_HOURS)
    elif duration == "medium":
        ttl = datetime.now(UTC) + timedelta(hours=settings.MEMORY_MEDIUM_TERM_HOURS)

    # Build metadata dict (not PacketMetadata model - that's for envelope metadata)
    envelope_metadata = {
        "creator": creator,
        "source": source,
        "caller": caller_id,
        "agent": "l-cto" if caller_id == "L" else "cursor",
        "user_id": user_id,
        "project_id": project_id,  # GMP-C1-GOVERNANCE: from governance context
        "importance": importance,
        "duration": duration,
        "scope": scope,  # MCP scope preserved
        "db_scope": db_scope,  # DB scope for filtering
        **(metadata or {}),
    }

    # Build provenance
    provenance = PacketProvenance(
        source=source,
        source_agent="l-cto" if caller_id == "L" else "cursor",
    )

    # Create PacketEnvelopeIn for main ingestion pipeline
    # Note: 'agent' is already in envelope_metadata, don't pass it twice
    # PacketEnvelopeIn expects dict for metadata/provenance, not Pydantic models
    packet_in = PacketEnvelopeIn(
        packet_type=f"memory.{kind}",  # e.g., "memory.preference", "memory.lesson"
        payload={
            "content": content,
            "kind": kind,
            "scope": scope,
            "project_id": project_id,  # GMP-C1-GOVERNANCE: from governance context
        },
        metadata={
            "schema_version": "2.0.0",
            "domain": "l9",
            **envelope_metadata,  # Contains agent, creator, source, etc.
        },
        provenance=provenance.model_dump(),  # Convert Pydantic model to dict
        tags=tags or [],
        ttl=ttl,
    )

    # Use main ingestion pipeline (runs full DAG)
    start_time = time.time()
    result = await substrate_service.write_packet(packet_in, principal_id=user_id)
    ingest_time_ms = (time.time() - start_time) * 1000

    if result.status == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Memory ingestion failed: {result.error_message}",
        )

    logger.info(
        "Memory saved via main ingestion pipeline",
        packet_id=str(result.packet_id),
        scope=scope,
        kind=kind,
        caller=caller_id,
        written_tables=result.written_tables,
        ingest_time_ms=ingest_time_ms,
        enrichment_status=result.enrichment_status,
        enrichment_facts_count=result.enrichment_facts_count,
    )

    # Wire through ALL fields from PacketWriteResult (v2.1.0 - GMP-67)
    return {
        "packet_id": str(result.packet_id),
        "user_id": user_id,
        "kind": kind,
        "scope": scope,
        "content": content[:100] + "..." if len(content) > 100 else content,
        "importance": importance,
        "created_at": datetime.now(UTC).isoformat(),
        "written_tables": result.written_tables,
        "ingest_time_ms": ingest_time_ms,
        # Enrichment visibility (v2.1.0 - GMP-67)
        "enrichment_status": result.enrichment_status,
        "enrichment_error": result.enrichment_error,
        "enrichment_facts_count": result.enrichment_facts_count,
        # Tier visibility (v2.1.0 - GMP-67)
        "tier_used": result.write_tier_used,
        "warnings": result.warnings,
        "pipeline": "main_dag",
    }


# GMP-89: _save_via_direct_db REMOVED
# All writes MUST go through _save_via_main_pipeline (substrate_service.write_packet)
# No direct DB fallback - ensures all memory flows through canonical pipeline


@must_stay_async("callers use await")
async def search_memory_handler(
    user_id: str,
    query: str,
    scopes: list[str] | None = None,  # MCP scopes: ['developer', 'global'] for Cursor
    kinds: list[str] | None = None,
    top_k: int = 5,
    threshold: float = 0.7,
    duration: str = "all",
    caller_id: str = "unknown",  # For audit logging
    track_access: bool = False,
    project_id: str | None = None,  # GMP-JSONB-GOV-FIX: defaults to L9_PROJECT_ID env
) -> dict[str, Any]:
    """
    Search unified L9 substrate using memory_embeddings with packet_store join.

    Uses vector similarity search on memory_embeddings, then joins to packet_store
    for full envelope data and scope filtering.

    GOVERNANCE: Project isolation is enforced at SQL level. Results only include
    memories from the specified project_id. Uses COALESCE for backward compatibility
    with legacy packets that don't have project_id set (defaults to 'l9').
    """
    # FAIL-CLOSED: Validate principal
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise ValueError(
            f"user_id (principal_id) REQUIRED for search_memory. "
            f"Cannot be None/empty. Received: {user_id!r}"
        )
    validated_principal = user_id.strip()

    # ADR-0098: project_id from centralized config_constants (single source of truth)
    if project_id is None:
        project_id = get_default_project_id()

    ctx = require_governance_context("mcp_memory.search_memory")
    if project_id != ctx.project_id:
        raise HTTPException(
            status_code=403,
            detail="project_id must be derived from governance context",
        )

    allow_legacy_null_scope_rows = (
        os.getenv("L9_ALLOW_LEGACY_NULL_SCOPE_ROWS", "false").lower() == "true"
    )

    try:
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000

        # Convert embedding vector to string format for pgvector
        # pgvector expects format: '[1.0,2.0,3.0]'
        query_embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

        # Map MCP scopes to DB scopes
        # Also include 'shared' for backward compatibility with legacy data
        # ADR-0098: scope defaults from config_constants
        requested_scopes = [
            map_mcp_scope_to_db_scope(s) for s in (scopes or DEFAULT_SEARCH_SCOPES)
        ]
        deduped_scopes = list(dict.fromkeys(requested_scopes))
        allowed_scopes = set(ctx.allowed_scopes)
        db_scopes = [scope for scope in deduped_scopes if scope in allowed_scopes]
        if (
            allow_legacy_null_scope_rows
            and "developer" in db_scopes
            and "shared" not in db_scopes
        ):
            db_scopes.append("shared")  # Legacy compatibility for old rows
        if not db_scopes:
            raise HTTPException(
                status_code=403, detail="No authorized scopes requested"
            )

        search_start = time.time()

        # Simplified search using semantic_memory (MCP Direct path)
        # NOTE: Changed from memory_embeddings to semantic_memory (where MCP writes go)
        # semantic_memory.payload contains: packet_id, packet_type, _text, source_payload
        #
        # Params: $1=vector, $2=threshold, $3=limit, $4+=scopes then governance predicates
        params = [query_embedding_str, threshold, top_k]

        scope_start = 4
        scope_placeholders = ", ".join(
            [f"${i}" for i in range(scope_start, scope_start + len(db_scopes))]
        )
        params.extend(db_scopes)

        project_param = scope_start + len(db_scopes)
        tenant_param = project_param + 1
        org_param = tenant_param + 1
        user_param = org_param + 1
        params.extend([ctx.project_id, ctx.tenant_id, ctx.org_id, ctx.user_id])

        # GMP-FIX: Enhanced content extraction from multiple payload structures:
        # 1. payload->>'_text' - L9 DAG enriched content (raw text that was embedded)
        # 2. payload->>'content' - Direct content field from MCP save_memory
        # 3. payload->'source_payload'->>'content' - Legacy nested structure
        search_query = f"""
        SELECT
            sm.embedding_id,
            sm.payload->>'packet_id' as packet_id,
            sm.payload->>'packet_type' as packet_type,
            COALESCE(
                sm.payload->>'kind',
                sm.payload->'source_payload'->>'kind'
            ) as kind,
            COALESCE(
                sm.payload->>'_text',
                sm.payload->>'content',
                sm.payload->'source_payload'->>'content'
            ) as chunk_text,
            sm.scope as db_scope,
            sm.created_at as timestamp,
            sm.importance_score,
            1 - (sm.vector <=> $1::vector) as similarity
        FROM semantic_memory sm
        WHERE sm.vector IS NOT NULL
        AND sm.scope IN ({scope_placeholders})
        AND sm.payload->>'_project_id' = ${project_param}
        AND {"(sm.tenant_id IS NULL OR sm.tenant_id = ${tenant_param}::uuid)" if allow_legacy_null_scope_rows else f"sm.tenant_id = ${tenant_param}::uuid"}
        AND {"(sm.org_id IS NULL OR sm.org_id = ${org_param}::uuid)" if allow_legacy_null_scope_rows else f"sm.org_id = ${org_param}::uuid"}
        AND {"(sm.user_id IS NULL OR sm.user_id = ${user_param}::uuid)" if allow_legacy_null_scope_rows else f"sm.user_id = ${user_param}::uuid"}
        AND 1 - (sm.vector <=> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT $3;
        """

        rows = await fetch_all(search_query, *params)

        # Format results (simplified for semantic_memory query)
        results = []
        for row in rows:
            mcp_scope = (
                map_db_scope_to_mcp_scope(row["db_scope"])
                if row["db_scope"]
                else "developer"
            )

            results.append(
                {
                    "packet_id": str(row["packet_id"]) if row["packet_id"] else None,
                    "embedding_id": str(row["embedding_id"]),
                    "content": row.get("chunk_text", ""),
                    "kind": row.get("kind", "unknown"),
                    "scope": mcp_scope,
                    "similarity": float(row["similarity"]),
                    "importance": (
                        float(row["importance_score"])
                        if row["importance_score"]
                        else 0.5
                    ),
                    "tags": [],  # semantic_memory doesn't have tags
                    "created_at": (
                        row["timestamp"].isoformat()
                        if isinstance(row["timestamp"], datetime)
                        else str(row["timestamp"])
                    ),
                }
            )

        search_time_ms = (time.time() - search_start) * 1000

        # Audit logging: Create audit packet in packet_store for search operations
        # OR log to tool_audit_log (see mcp_server.py handle_tool_call)
        # The search itself is audited via tool_audit_log when called via MCP tool

        logger.info(
            "Memory search completed",
            query_length=len(query),
            results_count=len(results),
            scopes=scopes,
            embed_time_ms=embed_time_ms,
            search_time_ms=search_time_ms,
        )

        return {
            "results": results,
            "query_embedding_time_ms": embed_time_ms,
            "search_time_ms": search_time_ms,
            "total_results": len(results),
        }

    except Exception as e:
        logger.exception("Error searching unified substrate")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# REST Route Handlers (Governance Hardened)
# =============================================================================
# When GOVERNANCE_HARDENING_ENABLED=True, these routes require authentication
# via the router-level dependency in main.py.
# Caller identity (user_id, caller_id, creator, source) is derived from the
# authenticated CallerIdentity, NEVER from the request body.


def _get_caller_from_request(request: Request) -> CallerIdentity:
    """Get CallerIdentity from request state (set by verify_api_key dependency).

    When GOVERNANCE_HARDENING_ENABLED=True, the router has a dependency on
    verify_api_key which sets request.state.user (CallerIdentity).

    When GOVERNANCE_HARDENING_ENABLED=False (legacy mode), we return a default
    identity for backward compatibility.
    """
    # Try to get from Depends (set by authenticated router)
    caller = getattr(request.state, "user", None)
    if caller is not None:
        return caller

    # Legacy fallback: return default identity
    # This path only executes when GOVERNANCE_HARDENING_ENABLED=False
    from src.main import CallerIdentity

    return CallerIdentity(caller_id="unknown", user_id=settings.L_CTO_USER_ID)


@router.post("/save")
@must_stay_async("callers use await")
async def save_memory_route(
    req: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    """REST endpoint for saving memory.

    GOVERNANCE: Caller identity is derived from authentication token, NOT request body.
    Any caller_id/creator/source in the request body is IGNORED.
    """
    substrate_service = get_substrate_service(request)
    caller = _get_caller_from_request(request)

    # Validate scope for Cursor - cannot write l-private
    requested_scope = req.get("scope", "developer")
    if caller.caller_id == "C" and requested_scope == "l-private":
        raise HTTPException(
            status_code=403,
            detail="Cursor cannot write to l-private scope. Only L-CTO can write private memories.",
        )

    # GMP-70 + ADR-0098: Governance context from centralized config_constants
    rls = get_rls_config()
    project_id = get_default_project_id()
    allowed_scopes = get_allowed_scopes_for_caller(caller.caller_id)
    caller_scope = get_default_scope_for_caller(caller.caller_id)

    gov_ctx = build_governance_context(
        caller_id=caller.caller_id,
        role="end_user",
        scope=caller_scope,
        project_id=project_id,
        allowed_scopes=allowed_scopes,
        tenant_id=rls.tenant_uuid,
        org_id=rls.org_uuid,
        user_id=rls.user_uuid,
        creator=caller.creator,
        source="mcp_memory_rest",
    )

    async with governance_context(gov_ctx):
        return await save_memory_handler(
            # SERVER-ENFORCED: user_id from authenticated identity
            user_id=caller.user_id,
            content=req["content"],
            kind=req["kind"],
            scope=requested_scope,
            duration=req.get("duration", "long"),
            tags=req.get("tags", []),
            importance=req.get("importance", 1.0),
            metadata=req.get("metadata"),
            # SERVER-ENFORCED: caller identity from token, NEVER from request body
            caller_id=caller.caller_id,
            creator=caller.creator,
            source=caller.source,
            substrate_service=substrate_service,
        )


@router.post("/search")
@must_stay_async("callers use await")
async def search_memory_route(
    req: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    """REST endpoint for searching memory.

    GOVERNANCE: Scope filtering is enforced based on caller identity.
    Cursor cannot see l-private scope memories.
    """
    caller = _get_caller_from_request(request)

    # ADR-0098: scope defaults from config_constants
    requested_scopes = req.get("scopes", DEFAULT_SEARCH_SCOPES)
    if caller.caller_id == "C":
        # Remove l-private from requested scopes for Cursor
        requested_scopes = [s for s in requested_scopes if s != "l-private"]

    # GMP-70 + ADR-0098: Governance context from centralized config_constants
    rls = get_rls_config()
    project_id = get_default_project_id()
    allowed_scopes = get_allowed_scopes_for_caller(caller.caller_id)
    caller_scope = get_default_scope_for_caller(caller.caller_id)

    gov_ctx = build_governance_context(
        caller_id=caller.caller_id,
        role="end_user",
        scope=caller_scope,
        project_id=project_id,
        allowed_scopes=allowed_scopes,
        tenant_id=rls.tenant_uuid,
        org_id=rls.org_uuid,
        user_id=rls.user_uuid,
        creator=caller.creator,
        source="mcp_memory_rest",
    )

    async with governance_context(gov_ctx):
        return await search_memory_handler(
            user_id=caller.user_id,
            query=req["query"],
            scopes=requested_scopes,
            kinds=req.get("kinds"),
            top_k=req.get("top_k", 5),
            threshold=req.get("threshold", 0.7),
            duration=req.get("duration", "all"),
            track_access=req.get("track_access", False),
            project_id=gov_ctx.project_id,
        )


# =============================================================================
# Stats and Maintenance Handlers
# =============================================================================


@router.get("/stats")
@must_stay_async("callers use await")
async def get_memory_stats(
    user_id: str | None = Query(None), duration: str = Query("all")
) -> dict[str, Any]:
    """
    Get memory statistics from unified substrate.

    Queries packet_store instead of deprecated memory.* tables.
    """
    try:
        # Use user_id from metadata.envelope->>'metadata'->>'user_id' or filter by scope
        user_filter = ""
        params = []
        param_idx = 1

        if user_id:
            # Filter by envelope metadata (user_id is in envelope JSONB)
            user_filter = f"AND envelope->'metadata'->>'user_id' = ${param_idx}"
            params.append(user_id)
            param_idx += 1

        # Count by duration (TTL-based)
        short_count = medium_count = long_count = unique_users = 0
        avg_importance = 0.0

        if duration in ["all", "short"]:
            query = f"""
            SELECT COUNT(*) as cnt
            FROM packet_store
            WHERE packet_type LIKE 'memory.%'
            AND ttl IS NOT NULL
            AND ttl > CURRENT_TIMESTAMP
            AND ttl < CURRENT_TIMESTAMP + INTERVAL '24 hours'
            {user_filter}
            """
            r = await fetch_one(query, *params)
            short_count = r["cnt"] if r else 0

        if duration in ["all", "medium"]:
            query = f"""
            SELECT COUNT(*) as cnt
            FROM packet_store
            WHERE packet_type LIKE 'memory.%'
            AND ttl IS NOT NULL
            AND ttl > CURRENT_TIMESTAMP
            AND ttl < CURRENT_TIMESTAMP + INTERVAL '7 days'
            AND ttl >= CURRENT_TIMESTAMP + INTERVAL '24 hours'
            {user_filter}
            """
            r = await fetch_one(query, *params)
            medium_count = r["cnt"] if r else 0

        if duration in ["all", "long"]:
            # Count unique callers (L or C), not user_id (which is shared as l9-shared)
            query = f"""
            SELECT
                COUNT(*) as cnt,
                COUNT(DISTINCT envelope->'metadata'->>'caller') as users,
                AVG(importance_score) as avg_imp
            FROM packet_store
            WHERE packet_type LIKE 'memory.%'
            AND (ttl IS NULL OR ttl > CURRENT_TIMESTAMP + INTERVAL '7 days')
            {user_filter}
            """
            r = await fetch_one(query, *params)
            if r:
                long_count = r["cnt"] if r else 0
                unique_users = r["users"] if r else 0
                avg_importance = float(r["avg_imp"]) if r["avg_imp"] else 0.0

        return {
            "short_term_count": short_count,
            "medium_term_count": medium_count,
            "long_term_count": long_count,
            "total_count": short_count + medium_count + long_count,
            "unique_users": unique_users,
            "avg_importance": avg_importance,
        }
    except asyncpg.PostgresError as e:
        error_code = getattr(e, "code", None)
        logger.error(
            "Database error getting stats", error=str(e), error_code=error_code
        )
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e
    except Exception as e:
        logger.exception(
            "Unexpected error getting stats from unified substrate", error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e!s}"
        ) from e


async def delete_expired_memories(dry_run: bool = True) -> dict[str, Any]:
    """
    Delete expired memories from unified substrate.

    Deletes packets where ttl < CURRENT_TIMESTAMP.
    Also deletes associated embeddings via CASCADE.
    """
    try:
        # Count expired packets
        count_query = """
        SELECT COUNT(*) as cnt
        FROM packet_store
        WHERE packet_type LIKE 'memory.%'
        AND ttl IS NOT NULL
        AND ttl < CURRENT_TIMESTAMP
        """
        count_r = await fetch_one(count_query)
        expired_count = count_r["cnt"] if count_r else 0

        if not dry_run and expired_count > 0:
            # Delete expired packets (embeddings deleted via CASCADE)
            await execute("""
                DELETE FROM packet_store
                WHERE packet_type LIKE 'memory.%'
                AND ttl IS NOT NULL
                AND ttl < CURRENT_TIMESTAMP
                """)
            logger.info(f"Deleted {expired_count} expired memories")

        return {
            "dry_run": dry_run,
            "expired_count": expired_count,
            "action": "deleted" if not dry_run else "would_delete",
        }
    except Exception as e:
        logger.exception("Error deleting expired memories")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def compound_similar_memories(
    user_id: str, threshold: float = 0.92
) -> dict[str, Any]:
    """
    Merge highly similar memories using memory_embeddings for similarity.

    Finds clusters of similar memories and merges them into primary memory.
    """
    if not settings.COMPOUNDING_ENABLED:
        return {"status": "disabled", "message": "Memory compounding is disabled"}

    try:
        # Get all long-term memories with embeddings for this user
        memories_query = """
        SELECT
            ps.packet_id,
            ps.envelope,
            ps.importance_score,
            ps.access_count,
            ps.tags,
            ps.timestamp,
            me.embedding_id,
            me.vector
        FROM packet_store ps
        INNER JOIN memory_embeddings me ON ps.packet_id = me.packet_id
        WHERE ps.packet_type LIKE 'memory.%'
        AND (ps.ttl IS NULL OR ps.ttl > CURRENT_TIMESTAMP + INTERVAL '7 days')
        AND me.embedding_type = 'content'
        AND ps.envelope->'metadata'->>'user_id' = $1
        ORDER BY ps.timestamp DESC
        LIMIT 1000
        """
        memories = await fetch_all(memories_query, user_id)

        if len(memories) < 2:
            return {
                "status": "skipped",
                "message": "Not enough memories",
                "memories_analyzed": len(memories),
            }

        # Find similar clusters
        similar_clusters = []
        processed_ids = set()

        for i, mem1 in enumerate(memories):
            if mem1["packet_id"] in processed_ids:
                continue

            cluster = [mem1]
            for mem2 in memories[i + 1 :]:
                if mem2["packet_id"] in processed_ids:
                    continue

                # Calculate similarity
                sim_result = await fetch_one(
                    "SELECT 1 - ($1::vector <-> $2::vector) as similarity",
                    mem1["vector"],
                    mem2["vector"],
                )

                if sim_result and sim_result["similarity"] >= threshold:
                    cluster.append(mem2)
                    processed_ids.add(mem2["packet_id"])

            if len(cluster) >= settings.COMPOUNDING_MIN_COUNT:
                similar_clusters.append(cluster)
                processed_ids.add(mem1["packet_id"])

        # Merge clusters
        merged_count = 0
        for cluster in similar_clusters:
            primary = cluster[0]
            duplicates = cluster[1:]

            # Combine importance and access
            primary_envelope = primary["envelope"]
            combined_importance = min(
                1.0,
                sum(
                    float(m["envelope"].get("metadata", {}).get("importance", 0.5))
                    for m in cluster
                ),
            )
            combined_access = sum(m.get("access_count", 0) for m in cluster)

            # Merge tags
            merged_tags = set(primary.get("tags", []))
            for m in cluster:
                if m.get("tags"):
                    merged_tags.update(m["tags"])

            # Update primary packet
            primary_envelope["metadata"]["importance"] = combined_importance
            primary_envelope["tags"] = list(merged_tags)

            await execute(
                """
                UPDATE packet_store
                SET envelope = $1::jsonb,
                    importance_score = $2,
                    access_count = $3,
                    tags = $4
                WHERE packet_id = $5
                """,
                json.dumps(primary_envelope),
                combined_importance,
                combined_access,
                list(merged_tags),
                primary["packet_id"],
            )

            # Delete duplicate packets (embeddings deleted via CASCADE)
            duplicate_ids = [m["packet_id"] for m in duplicates]
            await execute(
                "DELETE FROM packet_store WHERE packet_id = ANY($1::uuid[])",
                duplicate_ids,
            )

            merged_count += len(duplicates)

        logger.info(
            "Memory compounding completed",
            clusters_found=len(similar_clusters),
            memories_merged=merged_count,
        )

        return {
            "status": "completed",
            "memories_analyzed": len(memories),
            "clusters_found": len(similar_clusters),
            "memories_merged": merged_count,
            "threshold_used": threshold,
        }

    except Exception as e:
        logger.exception("Error compounding memories")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def apply_importance_decay(dry_run: bool = True) -> dict[str, Any]:
    """
    Apply importance decay to unused memories in unified substrate.

    Decays importance_score for packets not accessed recently.
    """
    if not settings.DECAY_ENABLED:
        return {"status": "disabled", "message": "Importance decay is disabled"}

    try:
        decay_factor = 1.0 - settings.DECAY_RATE_PER_DAY

        # Count affected packets
        count_query = """
        SELECT COUNT(*) as cnt
        FROM packet_store
        WHERE packet_type LIKE 'memory.%'
        AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
        AND importance_score > 0.01
        """
        count_r = await fetch_one(count_query)
        affected = count_r["cnt"] if count_r else 0

        if not dry_run and affected > 0:
            # Apply decay: importance *= decay_factor^(days_since_access)
            await execute(
                """
                UPDATE packet_store
                SET importance_score = importance_score * POWER(
                    $1,
                    EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed, timestamp))) / 86400
                )
                WHERE packet_type LIKE 'memory.%'
                AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
                AND importance_score > 0.01
                """,
                decay_factor,
            )
            logger.info(f"Applied decay to {affected} memories")

        return {
            "status": "completed" if not dry_run else "dry_run",
            "memories_affected": affected,
            "decay_factor": decay_factor,
            "action": "decayed" if not dry_run else "would_decay",
        }

    except asyncpg.PostgresError as e:
        error_code = getattr(e, "code", None)
        logger.error(
            "Database error applying decay", error=str(e), error_code=error_code
        )
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e
    except Exception as e:
        logger.exception("Unexpected error applying importance decay", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e!s}"
        ) from e


async def cleanup_task():
    """
    Background cleanup task for unified substrate.

    Runs periodically to:
    - Delete expired packets (ttl < now)
    - Apply importance decay
    """
    while True:
        try:
            await asyncio.sleep(settings.MEMORY_CLEANUP_INTERVAL_MINUTES * 60)

            # Delete expired
            await delete_expired_memories(dry_run=False)

            # Apply decay
            if settings.DECAY_ENABLED:
                await apply_importance_decay(dry_run=False)

            logger.info("Cleanup task completed")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


# =============================================================================
# 10X Memory Upgrade Handlers
# =============================================================================


@must_stay_async("callers use await")
async def get_context_injection(
    task_description: str,
    user_id: str,
    top_k: int = 5,
    include_recent: bool = True,
    kinds: list[str] | None = None,
    allowed_scopes: list[str] | None = None,
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> dict[str, Any]:
    """
    Auto-retrieve relevant memories for context injection before a task.

    Uses unified search to find semantically relevant memories plus recent context.

    Args:
        allowed_scopes: MCP scopes allowed for this caller.
                       Cursor gets ["developer", "global"] (no l-private).
                       L gets None (all scopes including l-private).
    """
    start_time = time.time()

    # Default scopes if not restricted (ADR-0098)
    search_scopes = allowed_scopes if allowed_scopes else ALLOWED_SCOPES_L

    try:
        # 1. Get semantically relevant memories
        relevant_result = await search_memory_handler(
            user_id=user_id,
            query=task_description,
            scopes=search_scopes,
            kinds=kinds,
            top_k=top_k,
            threshold=0.6,  # Lower threshold for context injection
            duration="long",
        )
        relevant_memories = relevant_result.get("results", [])

        # 2. Get recent context (last 24h) if requested
        recent_memories = []
        if include_recent:
            recent_query = """
            SELECT
                ps.packet_id,
                ps.envelope,
                ps.timestamp,
                ps.importance_score,
                ps.tags
            FROM packet_store ps
            WHERE ps.packet_type LIKE 'memory.%'
            AND ps.envelope->'metadata'->>'user_id' = $1
            AND ps.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY ps.timestamp DESC
            LIMIT 5
            """
            recent_rows = await fetch_all(recent_query, user_id)

            for row in recent_rows:
                envelope = row["envelope"]
                # Defensive: Handle case where envelope is returned as string
                if isinstance(envelope, str):
                    try:
                        envelope = json.loads(envelope)
                    except json.JSONDecodeError:
                        envelope = {}
                payload = (
                    envelope.get("payload", {}) if isinstance(envelope, dict) else {}
                )
                recent_memories.append(
                    {
                        "packet_id": str(row["packet_id"]),
                        "content": payload.get("content", ""),
                        "kind": payload.get("kind", "unknown"),
                        "scope": payload.get("scope", "developer"),
                        "importance": (
                            float(row["importance_score"])
                            if row["importance_score"]
                            else 0.5
                        ),
                        "tags": row["tags"] or [],
                        "created_at": (
                            row["timestamp"].isoformat()
                            if isinstance(row["timestamp"], datetime)
                            else str(row["timestamp"])
                        ),
                    }
                )

        retrieval_time_ms = (time.time() - start_time) * 1000

        return {
            "memories": relevant_memories,
            "recent_context": recent_memories,
            "total_injected": len(relevant_memories) + len(recent_memories),
            "retrieval_time_ms": retrieval_time_ms,
        }
    except Exception as e:
        logger.exception("Error in context injection")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def extract_session_learnings(
    user_id: str,
    session_id: str,
    session_summary: str,
    key_decisions: list[str] | None = None,
    errors_encountered: list[str] | None = None,
    successes: list[str] | None = None,
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> dict[str, Any]:
    """
    Extract and store learnings from a completed session.

    Uses unified save_memory_handler to store session summary, decisions, errors, successes.
    """
    try:
        memory_ids = []
        kinds_created = []

        # 1. Store session summary
        summary_result = await save_memory_handler(
            user_id=user_id,
            content=f"[Session {session_id}] {session_summary}",
            kind="context",
            scope="developer",
            duration="long",
            tags=["session:summary"],
            importance=0.8,
            metadata={"session_id": session_id, "type": "session_summary"},
            caller_id=caller_id,
            creator=creator,
            source=source,
        )
        memory_ids.append(summary_result["packet_id"])
        kinds_created.append("context")

        # 2. Store key decisions
        if key_decisions:
            for decision in key_decisions:
                dec_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Decision] {decision}",
                    kind="decision",
                    scope="developer",
                    duration="long",
                    tags=["session:decision"],
                    importance=0.9,
                    metadata={"session_id": session_id, "type": "decision"},
                    caller_id=caller_id,
                    creator=creator,
                    source=source,
                )
                memory_ids.append(dec_result["packet_id"])
                if "decision" not in kinds_created:
                    kinds_created.append("decision")

        # 3. Store error/fix pairs
        if errors_encountered:
            for error in errors_encountered:
                err_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Error+Fix] {error}",
                    kind="error",
                    scope="developer",
                    duration="long",
                    tags=["session:error", "debug:fix"],
                    importance=0.95,
                    metadata={"session_id": session_id, "type": "error_fix"},
                    caller_id=caller_id,
                    creator=creator,
                    source=source,
                )
                memory_ids.append(err_result["packet_id"])
                if "error" not in kinds_created:
                    kinds_created.append("error")

        # 4. Store successes
        if successes:
            for success in successes:
                suc_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Success] {success}",
                    kind="success",
                    scope="developer",
                    duration="long",
                    tags=["session:success"],
                    importance=0.85,
                    metadata={"session_id": session_id, "type": "success"},
                    caller_id=caller_id,
                    creator=creator,
                    source=source,
                )
                memory_ids.append(suc_result["packet_id"])
                if "success" not in kinds_created:
                    kinds_created.append("success")

        return {
            "learnings_stored": len(memory_ids),
            "memory_ids": memory_ids,
            "kinds_created": kinds_created,
        }
    except Exception as e:
        logger.exception("Error extracting session learnings")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def get_proactive_suggestions(
    current_context: str,
    user_id: str,
    include_error_fixes: bool = True,
    include_preferences: bool = True,
    top_k: int = 3,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Get proactive memory suggestions based on current context.

    Uses unified search to surface relevant past experiences, error fixes, preferences.
    """
    start_time = time.time()

    # Default scopes if not restricted (ADR-0098)
    search_scopes = allowed_scopes if allowed_scopes else ALLOWED_SCOPES_L

    try:
        suggestions = []
        error_fix_pairs = []
        relevant_preferences = []

        # 1. Get semantically similar memories
        search_result = await search_memory_handler(
            user_id=user_id,
            query=current_context,
            scopes=search_scopes,
            kinds=None,
            top_k=top_k * 2,
            threshold=0.65,
            duration="long",
        )
        suggestions = search_result.get("results", [])[:top_k]

        # 2. Get relevant error/fix pairs
        if include_error_fixes:
            error_scopes = [s for s in ["developer"] if s in search_scopes]
            error_search = await search_memory_handler(
                user_id=user_id,
                query=current_context,
                scopes=error_scopes if error_scopes else ["developer"],
                kinds=["error"],
                top_k=3,
                threshold=0.6,
                duration="long",
            )
            for mem in error_search.get("results", []):
                error_fix_pairs.append(
                    {
                        "error": mem.get("content", ""),
                        "fix": "See memory content",
                        "confidence": mem.get("similarity", 0.0),
                        "memory_id": mem.get("packet_id"),
                    }
                )

        # 3. Get relevant preferences
        if include_preferences:
            pref_scopes = [s for s in ["developer"] if s in search_scopes]
            pref_search = await search_memory_handler(
                user_id=user_id,
                query=current_context,
                scopes=pref_scopes if pref_scopes else ["developer"],
                kinds=["preference"],
                top_k=3,
                threshold=0.5,
                duration="long",
            )
            relevant_preferences = pref_search.get("results", [])

        recall_time_ms = (time.time() - start_time) * 1000

        return {
            "suggestions": suggestions,
            "error_fix_pairs": error_fix_pairs,
            "relevant_preferences": relevant_preferences,
            "recall_time_ms": recall_time_ms,
        }
    except Exception as e:
        logger.exception("Error in proactive suggestions")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def query_temporal(
    user_id: str,
    since: str | None = None,
    until: str | None = None,
    kinds: list[str] | None = None,
    operation: str = "changes",
    allowed_scopes: list[str] | None = None,  # GOVERNANCE: scope filter
) -> dict[str, Any]:
    """
    Query memory changes over time in unified substrate.

    Answers 'what changed since X' or 'show timeline of Y'.

    GOVERNANCE: When allowed_scopes is provided, filters results to only include
    memories with matching scope. Cursor gets ['developer', 'global'], L-CTO gets all.
    Uses parameterized = ANY($N) to prevent SQL injection.

    GMP-115: Operation parameter validated against centralized allowlist.
    See config/policies/sql_security.yaml for allowed operations.
    """
    # GMP-115: Validate operation against centralized allowlist (defense-in-depth)
    # Operations determine query structure, not user data — must be allowlisted
    _ALLOWED_TEMPORAL_OPERATIONS: frozenset[str] = frozenset(
        {
            "changes",
            "timeline",
            "diff",
        }
    )
    if operation not in _ALLOWED_TEMPORAL_OPERATIONS:
        from core.exceptions.security import InvalidOperationError

        raise InvalidOperationError(
            operation,
            allowed=list(_ALLOWED_TEMPORAL_OPERATIONS),
            context="temporal",
        )

    try:
        # Parse datetime strings
        since_dt = (
            datetime.fromisoformat(since)
            if since
            else datetime.now(UTC) - timedelta(days=7)
        )
        until_dt = datetime.fromisoformat(until) if until else datetime.now(UTC)

        # Build WHERE clause
        where_parts = [
            "ps.packet_type LIKE 'memory.%'",
            "ps.envelope->'metadata'->>'user_id' = $1",
            "ps.timestamp >= $2",
            "ps.timestamp <= $3",
        ]
        params: list[Any] = [user_id, since_dt, until_dt]
        param_idx = 4

        # GOVERNANCE: Add scope filter using parameterized array
        # Uses = ANY($N) which is safe against SQL injection
        if allowed_scopes:
            db_scopes = [map_mcp_scope_to_db_scope(s) for s in allowed_scopes]
            where_parts.append(f"ps.scope = ANY(${param_idx})")
            params.append(db_scopes)  # PostgreSQL array parameter
            param_idx += 1

        if kinds:
            # Use parameterized queries to prevent SQL injection
            kind_placeholders = []
            for kind in kinds:
                kind_placeholders.append(
                    f"ps.packet_type LIKE '%' || ${param_idx} || '%'"
                )
                params.append(kind)
                param_idx += 1
            where_parts.append(f"({' OR '.join(kind_placeholders)})")

        where_clause = " AND ".join(where_parts)

        if operation == "changes":
            query = f"""
            SELECT
                ps.packet_id,
                ps.envelope,
                ps.timestamp,
                ps.importance_score,
                ps.tags,
                ps.last_accessed
            FROM packet_store ps
            WHERE {where_clause}
            ORDER BY ps.timestamp DESC
            """
            memories = await fetch_all(query, *params)

            # Count created vs updated (updated = has last_accessed != timestamp)
            created_count = sum(
                1
                for m in memories
                if m.get("last_accessed") is None
                or m["last_accessed"] == m["timestamp"]
            )
            updated_count = len(memories) - created_count

        elif operation == "timeline":
            query = f"""
            SELECT
                ps.packet_id,
                ps.envelope,
                ps.timestamp,
                ps.importance_score,
                ps.tags
            FROM packet_store ps
            WHERE {where_clause}
            ORDER BY ps.timestamp ASC
            """
            memories = await fetch_all(query, *params)
            created_count = len(memories)
            updated_count = 0

        else:  # diff
            query = f"""
            SELECT
                ps.packet_id,
                ps.envelope,
                ps.timestamp,
                ps.last_accessed,
                ps.importance_score,
                ps.tags
            FROM packet_store ps
            WHERE {where_clause}
            AND ps.last_accessed IS NOT NULL
            AND ps.last_accessed > ps.timestamp
            ORDER BY ps.last_accessed DESC
            """
            memories = await fetch_all(query, *params)
            created_count = 0
            updated_count = len(memories)

        # Format results
        formatted_memories = []
        for m in memories:
            envelope = m["envelope"]
            # Defensive: Handle case where envelope is returned as string
            if isinstance(envelope, str):
                try:
                    envelope = json.loads(envelope)
                except json.JSONDecodeError:
                    envelope = {}
            payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
            formatted_memories.append(
                {
                    "packet_id": str(m["packet_id"]),
                    "content": payload.get("content", ""),
                    "kind": payload.get("kind", "unknown"),
                    "scope": payload.get("scope", "developer"),
                    "importance": (
                        float(m["importance_score"]) if m["importance_score"] else 0.5
                    ),
                    "tags": m["tags"] or [],
                    "created_at": (
                        m["timestamp"].isoformat()
                        if isinstance(m["timestamp"], datetime)
                        else str(m["timestamp"])
                    ),
                }
            )

        return {
            "memories": formatted_memories,
            "created_count": created_count,
            "updated_count": updated_count,
            "deleted_count": 0,  # Deletes not tracked separately in unified substrate
            "period_start": since_dt.isoformat(),
            "period_end": until_dt.isoformat(),
        }
    except Exception as e:
        logger.exception("Error in temporal query")
        raise HTTPException(status_code=500, detail=str(e)) from e


@must_stay_async("callers use await")
async def save_memory_with_confidence(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "developer",
    duration: str = "long",
    confidence: float = 1.0,
    source: str = "cursor",
    related_memory_ids: list[Any] | None = None,  # Can be UUIDs (str) or ints (legacy)
    tags: list[str] | None = None,
    importance: float = 1.0,
    caller_id: str = "unknown",
    creator: str = "unknown",
    # GMP-89: REQUIRED substrate_service for main pipeline
    substrate_service: Any | None = None,
) -> dict[str, Any]:
    """
    Save memory with explicit confidence scoring and relationship linking.

    Uses unified save_memory_handler with confidence metadata.
    REQUIRES substrate_service for main pipeline (GMP-89: no fallback).
    """
    try:
        # Add confidence to metadata
        metadata = {
            "confidence": confidence,
            "related_memory_ids": related_memory_ids or [],
        }

        # Scale importance by confidence
        effective_importance = importance * confidence

        # Add confidence tag
        all_tags = list(tags or [])
        if confidence >= 0.9:
            all_tags.append("confidence:high")
        elif confidence >= 0.7:
            all_tags.append("confidence:medium")
        else:
            all_tags.append("confidence:low")

        # Save using unified handler (GMP-89: pass substrate_service)
        result = await save_memory_handler(
            user_id=user_id,
            content=content,
            kind=kind,
            scope=scope,
            duration=duration,
            tags=all_tags,
            importance=effective_importance,
            metadata=metadata,
            caller_id=caller_id,
            creator=creator,
            source=source,
            substrate_service=substrate_service,
        )

        # Log relationships if provided
        if related_memory_ids:
            for related_id in related_memory_ids:
                # Store relationship in envelope metadata (could also use separate table)
                logger.debug(
                    "Memory relationship logged",
                    packet_id=result["packet_id"],
                    related_to=related_id,
                )

        return result
    except Exception as e:
        logger.exception("Error saving memory with confidence")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.governance_gate"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "debugging",
        "endpoint",
        "event-driven",
        "integration",
        "logging",
        "messaging",
    ],
    "keywords": [
        "agent",
        "apply",
        "cleanup",
        "compound",
        "confidence",
        "decay",
        "delete",
        "expired",
    ],
    "business_value": "This replaces the deprecated memory.* tables with the unified L9 memory substrate. Uses packet_store for event log and memory_embeddings for vector storage. MANDATORY: ALL WRITES ROUTE THROUGH MAIN L9",
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
