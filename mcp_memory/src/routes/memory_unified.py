"""Memory CRUD using unified L9 substrate (packet_store + memory_embeddings).

This replaces the deprecated memory.* tables with the unified L9 memory substrate.
Uses packet_store for event log and memory_embeddings for vector storage.
"""

import structlog
import time
import json
import uuid
import asyncpg
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
import asyncio

from src.db import fetch_all, fetch_one, execute
from src.embeddings import embed_text
from src.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


def map_mcp_scope_to_db_scope(mcp_scope: str) -> str:
    """
    Map MCP governance scopes to DB scope values.
    
    MCP scopes: 'developer', 'l-private', 'global'
    DB scopes: 'shared', 'l-private' (current), 'developer', 'global' (target after migration)
    
    For now, map:
    - 'developer' → 'shared' (shared between L and Cursor)
    - 'l-private' → 'l-private' (L only)
    - 'global' → 'shared' (cross-project, shared)
    """
    mapping = {
        "developer": "shared",  # Shared developer collaboration
        "l-private": "l-private",  # L's private operations
        "global": "shared",  # Cross-project shared knowledge
    }
    return mapping.get(mcp_scope, "shared")


def map_db_scope_to_mcp_scope(db_scope: str) -> str:
    """Reverse mapping: DB scope → MCP scope."""
    # For now, 'shared' maps to 'developer' (most common case)
    # 'l-private' stays the same
    if db_scope == "l-private":
        return "l-private"
    return "developer"  # Default 'shared' → 'developer'


async def save_memory_handler(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "developer",  # MCP scope: developer/l-private/global
    duration: str = "long",
    tags: Optional[List[str]] = None,
    importance: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
    # Governance fields (enforced server-side, not client-provided)
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> Dict[str, Any]:
    """
    Save memory to unified L9 substrate (packet_store + memory_embeddings).
    
    Uses:
    - packet_store: Central event log with PacketEnvelope JSONB
    - memory_embeddings: Vector storage with packet_id FK
    
    See: mcp_memory/memory-setup-instructions.md for governance spec.
    
    Args:
        scope: MCP scope ('developer', 'l-private', 'global')
        caller_id: "L" or "C" (from API key)
        creator: "L-CTO" or "Cursor-IDE" (server-enforced)
        source: "l9-kernel" or "cursor-ide" (server-enforced)
    """
    try:
        # Generate packet ID
        packet_id = uuid.uuid4()
        thread_id = uuid.uuid4()  # Daily session thread (could be passed in)
        timestamp = datetime.utcnow()
        
        # Map MCP scope to DB scope
        db_scope = map_mcp_scope_to_db_scope(scope)
        
        # Generate embedding
        embed_start = time.time()
        embedding_vector = await embed_text(content)
        embed_time_ms = (time.time() - embed_start) * 1000
        
        # Build PacketEnvelope structure
        # See: memory/substrate_models.py for PacketEnvelope schema
        # Perplexity integration: Add project_id (default: 'l9' for L9 repo, NULL for global)
        project_id = None
        if metadata:
            project_id = metadata.get("project_id")
        if project_id is None:
            # Default: 'l9' for developer/l-private scope, NULL for global
            project_id = "l9" if scope != "global" else None
        
        envelope = {
            "packet_id": str(packet_id),
            "packet_type": f"memory_write_{kind}",  # e.g., "memory_write_preference"
            "timestamp": timestamp.isoformat(),
            "payload": {
                "content": content,
                "kind": kind,
                "scope": scope,  # MCP scope preserved in payload
                "project_id": project_id,  # Perplexity: multi-project isolation
            },
            "metadata": {
                "creator": creator,  # Enforced server-side
                "source": source,    # Enforced server-side
                "caller": caller_id,
                "agent": "l-cto" if caller_id == "L" else "cursor-ide",
                "user_id": user_id,
                "project_id": project_id,  # Perplexity: store in metadata for querying
                "importance": importance,
                "duration": duration,
                **({} if metadata is None else {k: v for k, v in metadata.items() if k != "project_id"}),
            },
            "thread_id": str(thread_id),
            "tags": tags or [],
        }
        
        # Calculate TTL based on duration
        ttl = None
        if duration == "short":
            ttl = timestamp + timedelta(hours=settings.MEMORY_SHORT_TERM_HOURS)
        elif duration == "medium":
            ttl = timestamp + timedelta(hours=settings.MEMORY_MEDIUM_TERM_HOURS)
        # long duration: no TTL (permanent)
        
        # Insert into packet_store
        insert_packet_query = """
        INSERT INTO packet_store (
            packet_id, packet_type, envelope, timestamp,
            thread_id, tags, ttl, scope, importance_score,
            session_id, content_hash
        )
        VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING packet_id, timestamp;
        """
        
        # Compute content hash for deduplication
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        packet_result = await fetch_one(
            insert_packet_query,
            packet_id,
            envelope["packet_type"],
            json.dumps(envelope),
            timestamp,
            thread_id,
            tags or [],
            ttl,
            db_scope,
            importance,
            metadata.get("session_id") if metadata else None,
            content_hash,
        )
        
        # Insert embedding into memory_embeddings
        # See: migrations/0008_memory_substrate_10x.sql for schema
        insert_embedding_query = """
        INSERT INTO memory_embeddings (
            packet_id, embedding_type, vector, chunk_text, metadata
        )
        VALUES ($1, $2, $3::vector, $4, $5::jsonb)
        RETURNING embedding_id;
        """
        
        embedding_metadata = {
            "kind": kind,
            "scope": scope,
            "duration": duration,
            "importance": importance,
            "embed_time_ms": embed_time_ms,
        }
        
        # Convert embedding vector to string format for pgvector
        # pgvector expects format: '[1.0,2.0,3.0]'
        vector_str = f"[{','.join(str(v) for v in embedding_vector)}]"
        
        embedding_result = await fetch_one(
            insert_embedding_query,
            packet_id,
            "content",  # embedding_type: 'content', 'context', 'entity', 'summary', 'reasoning'
            vector_str,
            content[:500],  # chunk_text (first 500 chars for debugging)
            json.dumps(embedding_metadata),
        )
        
        # Audit logging: Use packet_store metadata (already stored above)
        # The packet_store entry IS the audit log - metadata contains caller, project_id, scope
        # For tool execution audit, use tool_audit_log (see mcp_server.py handle_tool_call)
        
        logger.info(
            "Memory saved to unified substrate",
            packet_id=str(packet_id),
            scope=scope,
            db_scope=db_scope,
            kind=kind,
            caller=caller_id,
            project_id=project_id,
        )
        
        return {
            "packet_id": str(packet_id),
            "embedding_id": str(embedding_result["embedding_id"]),
            "user_id": user_id,
            "kind": kind,
            "scope": scope,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "importance": importance,
            "created_at": timestamp.isoformat(),
            "embed_time_ms": embed_time_ms,
        }
        
    except asyncpg.PostgresError as e:
        error_code = getattr(e, 'code', None)
        logger.error("Database error saving memory", error=str(e), error_code=error_code)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except ValueError as e:
        logger.warning("Validation error saving memory", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error saving memory to unified substrate", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def search_memory_handler(
    user_id: str,
    query: str,
    scopes: Optional[List[str]] = None,  # MCP scopes: ['developer', 'global'] for Cursor
    kinds: Optional[List[str]] = None,
    top_k: int = 5,
    threshold: float = 0.7,
    duration: str = "all",
    caller_id: str = "unknown",  # Perplexity: for audit logging
) -> Dict[str, Any]:
    """
    Search unified L9 substrate using memory_embeddings with packet_store join.
    
    Uses vector similarity search on memory_embeddings, then joins to packet_store
    for full envelope data and scope filtering.
    """
    try:
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000
        
        # Convert embedding vector to string format for pgvector
        # pgvector expects format: '[1.0,2.0,3.0]'
        query_embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"
        
        # Map MCP scopes to DB scopes
        db_scopes = [map_mcp_scope_to_db_scope(s) for s in (scopes or ["developer", "global"])]
        
        search_start = time.time()
        
        # Build WHERE clause for scope filtering
        scope_filter = ""
        params = [query_embedding_str, threshold, top_k]
        param_idx = 4
        
        if db_scopes:
            scope_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(db_scopes))])
            scope_filter = f"AND ps.scope IN ({scope_placeholders})"
            params.extend(db_scopes)
            param_idx += len(db_scopes)
        
        # Build WHERE clause for kind filtering (from envelope payload)
        # SECURITY: Use parameterized queries to prevent SQL injection
        kind_filter = ""
        if kinds:
            # Filter by packet_type (contains kind) or envelope->>'payload'->>'kind'
            # Use parameterized query for safety
            kind_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(kinds))])
            kind_conditions = []
            for i, kind in enumerate(kinds):
                kind_conditions.append(f"ps.packet_type LIKE '%' || ${param_idx + i} || '%'")
            kind_filter = f"AND ({' OR '.join(kind_conditions)})"
            params.extend(kinds)
            param_idx += len(kinds)
        
        # Build WHERE clause for duration (TTL-based)
        duration_filter = ""
        if duration == "short":
            duration_filter = "AND ps.ttl > CURRENT_TIMESTAMP AND ps.ttl < CURRENT_TIMESTAMP + INTERVAL '24 hours'"
        elif duration == "medium":
            duration_filter = "AND ps.ttl > CURRENT_TIMESTAMP AND ps.ttl < CURRENT_TIMESTAMP + INTERVAL '7 days'"
        elif duration == "long":
            duration_filter = "AND (ps.ttl IS NULL OR ps.ttl > CURRENT_TIMESTAMP + INTERVAL '7 days')"
        # "all" = no duration filter
        
        # Perplexity integration: SQL-level scope enforcement (defense in depth)
        # Vector similarity search with packet_store join
        # Enforce scope filtering in SQL (not just Python) per Perplexity recommendation
        search_query = f"""
        SELECT 
            ps.packet_id,
            ps.packet_type,
            ps.envelope,
            ps.scope as db_scope,
            ps.timestamp,
            ps.importance_score,
            ps.tags,
            me.embedding_id,
            me.chunk_text,
            1 - (me.vector <-> $1::vector) as similarity
        FROM memory_embeddings me
        INNER JOIN packet_store ps ON me.packet_id = ps.packet_id
        WHERE me.embedding_type = 'content'
        {scope_filter}  -- Perplexity: SQL-level scope enforcement
        {kind_filter}
        {duration_filter}
        AND 1 - (me.vector <-> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT $3;
        """
        
        rows = await fetch_all(search_query, *params)
        
        # Update access tracking
        if rows:
            packet_ids = [r["packet_id"] for r in rows]
            await execute(
                """
                UPDATE packet_store 
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE packet_id = ANY($1::uuid[]);
                """,
                packet_ids,
            )
        
        # Format results
        results = []
        for row in rows:
            envelope = row["envelope"]
            payload = envelope.get("payload", {})
            mcp_scope = map_db_scope_to_mcp_scope(row["db_scope"])
            
            results.append({
                "packet_id": str(row["packet_id"]),
                "embedding_id": str(row["embedding_id"]),
                "content": payload.get("content", row.get("chunk_text", "")),
                "kind": payload.get("kind", "unknown"),
                "scope": mcp_scope,
                "similarity": float(row["similarity"]),
                "importance": float(row["importance_score"]) if row["importance_score"] else 0.5,
                "tags": row["tags"] or [],
                "created_at": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
            })
        
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
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REST Route Handlers (for backward compatibility)
# =============================================================================

@router.post("/save")
async def save_memory_route(req: Dict[str, Any]) -> Dict[str, Any]:
    """REST endpoint for saving memory."""
    return await save_memory_handler(
        user_id=req.get("user_id", settings.L_CTO_USER_ID),
        content=req["content"],
        kind=req["kind"],
        scope=req.get("scope", "developer"),
        duration=req.get("duration", "long"),
        tags=req.get("tags", []),
        importance=req.get("importance", 1.0),
        metadata=req.get("metadata"),
        caller_id=req.get("caller_id", "unknown"),
        creator=req.get("creator", "unknown"),
        source=req.get("source", "unknown"),
    )


@router.post("/search")
async def search_memory_route(req: Dict[str, Any]) -> Dict[str, Any]:
    """REST endpoint for searching memory."""
    return await search_memory_handler(
        user_id=req.get("user_id", settings.L_CTO_USER_ID),
        query=req["query"],
        scopes=req.get("scopes", ["developer", "global"]),
        kinds=req.get("kinds"),
        top_k=req.get("top_k", 5),
        threshold=req.get("threshold", 0.7),
        duration=req.get("duration", "all"),
    )


# =============================================================================
# Stats and Maintenance Handlers
# =============================================================================

@router.get("/stats")
async def get_memory_stats(
    user_id: Optional[str] = Query(None),
    duration: str = Query("all")
) -> Dict[str, Any]:
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
            WHERE packet_type LIKE 'memory_write_%'
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
            WHERE packet_type LIKE 'memory_write_%'
            AND ttl IS NOT NULL
            AND ttl > CURRENT_TIMESTAMP
            AND ttl < CURRENT_TIMESTAMP + INTERVAL '7 days'
            AND ttl >= CURRENT_TIMESTAMP + INTERVAL '24 hours'
            {user_filter}
            """
            r = await fetch_one(query, *params)
            medium_count = r["cnt"] if r else 0
        
        if duration in ["all", "long"]:
            query = f"""
            SELECT 
                COUNT(*) as cnt,
                COUNT(DISTINCT envelope->'metadata'->>'user_id') as users,
                AVG(importance_score) as avg_imp
            FROM packet_store
            WHERE packet_type LIKE 'memory_write_%'
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
        error_code = getattr(e, 'code', None)
        logger.error("Database error getting stats", error=str(e), error_code=error_code)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error getting stats from unified substrate", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def delete_expired_memories(dry_run: bool = True) -> Dict[str, Any]:
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
        WHERE packet_type LIKE 'memory_write_%'
        AND ttl IS NOT NULL
        AND ttl < CURRENT_TIMESTAMP
        """
        count_r = await fetch_one(count_query)
        expired_count = count_r["cnt"] if count_r else 0
        
        if not dry_run and expired_count > 0:
            # Delete expired packets (embeddings deleted via CASCADE)
            await execute(
                """
                DELETE FROM packet_store
                WHERE packet_type LIKE 'memory_write_%'
                AND ttl IS NOT NULL
                AND ttl < CURRENT_TIMESTAMP
                """
            )
            logger.info(f"Deleted {expired_count} expired memories")
        
        return {
            "dry_run": dry_run,
            "expired_count": expired_count,
            "action": "deleted" if not dry_run else "would_delete",
        }
    except Exception as e:
        logger.exception("Error deleting expired memories")
        raise HTTPException(status_code=500, detail=str(e))


async def compound_similar_memories(
    user_id: str,
    threshold: float = 0.92
) -> Dict[str, Any]:
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
        WHERE ps.packet_type LIKE 'memory_write_%'
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
            for mem2 in memories[i + 1:]:
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
            combined_importance = min(1.0, sum(
                float(m["envelope"].get("metadata", {}).get("importance", 0.5))
                for m in cluster
            ))
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
        raise HTTPException(status_code=500, detail=str(e))


async def apply_importance_decay(dry_run: bool = True) -> Dict[str, Any]:
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
        WHERE packet_type LIKE 'memory_write_%'
        AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
        AND importance_score > 0.01
        """
        count_r = await fetch_one(count_query)
        affected = count_r["cnt"] if count_r else 0
        
        if not dry_run and affected > 0:
            # Apply decay: importance *= decay_factor^(days_since_access)
            await execute(
                f"""
                UPDATE packet_store
                SET importance_score = importance_score * POWER(
                    {decay_factor},
                    EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed, timestamp))) / 86400
                )
                WHERE packet_type LIKE 'memory_write_%'
                AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
                AND importance_score > 0.01
                """
            )
            logger.info(f"Applied decay to {affected} memories")
        
        return {
            "status": "completed" if not dry_run else "dry_run",
            "memories_affected": affected,
            "decay_factor": decay_factor,
            "action": "decayed" if not dry_run else "would_decay",
        }
        
    except asyncpg.PostgresError as e:
        error_code = getattr(e, 'code', None)
        logger.error("Database error applying decay", error=str(e), error_code=error_code)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error applying importance decay", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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

async def get_context_injection(
    task_description: str,
    user_id: str,
    top_k: int = 5,
    include_recent: bool = True,
    kinds: Optional[List[str]] = None,
    allowed_scopes: Optional[List[str]] = None,
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> Dict[str, Any]:
    """
    Auto-retrieve relevant memories for context injection before a task.
    
    Uses unified search to find semantically relevant memories plus recent context.
    
    Args:
        allowed_scopes: MCP scopes allowed for this caller.
                       Cursor gets ["developer", "global"] (no l-private).
                       L gets None (all scopes including l-private).
    """
    start_time = time.time()
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["developer", "global", "l-private"]
    
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
            WHERE ps.packet_type LIKE 'memory_write_%'
            AND ps.envelope->'metadata'->>'user_id' = $1
            AND ps.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY ps.timestamp DESC
            LIMIT 5
            """
            recent_rows = await fetch_all(recent_query, user_id)
            
            for row in recent_rows:
                envelope = row["envelope"]
                payload = envelope.get("payload", {})
                recent_memories.append({
                    "packet_id": str(row["packet_id"]),
                    "content": payload.get("content", ""),
                    "kind": payload.get("kind", "unknown"),
                    "scope": payload.get("scope", "developer"),
                    "importance": float(row["importance_score"]) if row["importance_score"] else 0.5,
                    "tags": row["tags"] or [],
                    "created_at": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
                })
        
        retrieval_time_ms = (time.time() - start_time) * 1000
        
        return {
            "memories": relevant_memories,
            "recent_context": recent_memories,
            "total_injected": len(relevant_memories) + len(recent_memories),
            "retrieval_time_ms": retrieval_time_ms,
        }
    except Exception as e:
        logger.exception("Error in context injection")
        raise HTTPException(status_code=500, detail=str(e))


async def extract_session_learnings(
    user_id: str,
    session_id: str,
    session_summary: str,
    key_decisions: Optional[List[str]] = None,
    errors_encountered: Optional[List[str]] = None,
    successes: Optional[List[str]] = None,
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> Dict[str, Any]:
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
        raise HTTPException(status_code=500, detail=str(e))


async def get_proactive_suggestions(
    current_context: str,
    user_id: str,
    include_error_fixes: bool = True,
    include_preferences: bool = True,
    top_k: int = 3,
    allowed_scopes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get proactive memory suggestions based on current context.
    
    Uses unified search to surface relevant past experiences, error fixes, preferences.
    """
    start_time = time.time()
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["developer", "global", "l-private"]
    
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
                error_fix_pairs.append({
                    "error": mem.get("content", ""),
                    "fix": "See memory content",
                    "confidence": mem.get("similarity", 0.0),
                    "memory_id": mem.get("packet_id"),
                })
        
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
        raise HTTPException(status_code=500, detail=str(e))


async def query_temporal(
    user_id: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    kinds: Optional[List[str]] = None,
    operation: str = "changes",
) -> Dict[str, Any]:
    """
    Query memory changes over time in unified substrate.
    
    Answers 'what changed since X' or 'show timeline of Y'.
    """
    try:
        # Parse datetime strings
        since_dt = datetime.fromisoformat(since) if since else datetime.utcnow() - timedelta(days=7)
        until_dt = datetime.fromisoformat(until) if until else datetime.utcnow()
        
        # Build WHERE clause
        where_parts = [
            "ps.packet_type LIKE 'memory_write_%'",
            "ps.envelope->>'metadata'->>'user_id' = $1",
            "ps.timestamp >= $2",
            "ps.timestamp <= $3",
        ]
        params = [user_id, since_dt, until_dt]
        param_idx = 4
        
        if kinds:
            kind_conditions = []
            for kind in kinds:
                kind_conditions.append(f"ps.packet_type LIKE '%{kind}%'")
            where_parts.append(f"({' OR '.join(kind_conditions)})")
        
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
                1 for m in memories
                if m.get("last_accessed") is None or m["last_accessed"] == m["timestamp"]
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
            payload = envelope.get("payload", {})
            formatted_memories.append({
                "packet_id": str(m["packet_id"]),
                "content": payload.get("content", ""),
                "kind": payload.get("kind", "unknown"),
                "scope": payload.get("scope", "developer"),
                "importance": float(m["importance_score"]) if m["importance_score"] else 0.5,
                "tags": m["tags"] or [],
                "created_at": m["timestamp"].isoformat() if isinstance(m["timestamp"], datetime) else str(m["timestamp"]),
            })
        
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
        raise HTTPException(status_code=500, detail=str(e))


async def save_memory_with_confidence(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "developer",
    duration: str = "long",
    confidence: float = 1.0,
    source: str = "cursor",
    related_memory_ids: Optional[List[Any]] = None,  # Can be UUIDs (str) or ints (legacy)
    tags: Optional[List[str]] = None,
    importance: float = 1.0,
    caller_id: str = "unknown",
    creator: str = "unknown",
) -> Dict[str, Any]:
    """
    Save memory with explicit confidence scoring and relationship linking.
    
    Uses unified save_memory_handler with confidence metadata.
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
        
        # Save using unified handler
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
        raise HTTPException(status_code=500, detail=str(e))

