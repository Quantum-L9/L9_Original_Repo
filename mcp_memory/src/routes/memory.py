"""Memory CRUD, search, compounding, and decay routes."""

import structlog
import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
import asyncio

from src.db import fetch_all, fetch_one, execute
from src.embeddings import embed_text
from src.models import (
    SaveMemoryRequest,
    MemoryResponse,
    SearchMemoryRequest,
    SearchMemoryResponse,
    MemoryStatsResponse,
)
from src.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/save", response_model=MemoryResponse)
async def save_memory(req: SaveMemoryRequest) -> MemoryResponse:
    return await save_memory_handler(
        user_id=req.user_id,
        content=req.content,
        kind=req.kind,
        scope=req.scope,
        duration=req.duration,
        tags=req.tags,
        importance=req.importance,
        metadata=req.metadata,
    )


async def save_memory_handler(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "user",
    duration: str = "long",
    tags: Optional[List[str]] = None,
    importance: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
    # Governance fields (enforced server-side, not client-provided)
    caller_id: str = "unknown",
    creator: str = "unknown",
    source: str = "unknown",
) -> Dict[str, Any]:
    """Save memory with caller-enforced governance.
    
    See: mcp_memory/memory-setup-instructions.md for governance spec.
    
    Args:
        caller_id: "L" or "C" (from API key)
        creator: "L-CTO" or "Cursor-IDE" (server-enforced)
        source: "l9-kernel" or "cursor-ide" (server-enforced)
    """
    try:
        embedding_list = await embed_text(content)
        # Convert embedding list to pgvector string format: '[1.0, 2.0, ...]'
        embedding = f"[{','.join(str(x) for x in embedding_list)}]"
        
        # Enforce governance metadata (never trust client-provided values)
        governed_metadata = metadata.copy() if metadata else {}
        governed_metadata["creator"] = creator  # Enforced
        governed_metadata["source"] = source    # Enforced
        governed_metadata["caller"] = caller_id
        
        if duration == "short":
            table = "memory.short_term"
            expires_at = datetime.utcnow() + timedelta(
                hours=settings.MEMORY_SHORT_TERM_HOURS
            )
        elif duration == "medium":
            table = "memory.medium_term"
            expires_at = datetime.utcnow() + timedelta(
                hours=settings.MEMORY_MEDIUM_TERM_HOURS
            )
        else:
            table = "memory.long_term"
            expires_at = None

        if duration in ["short", "medium"]:
            query = f"""
            INSERT INTO {table} (user_id, kind, content, embedding, importance, metadata, expires_at)
            VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
            RETURNING id, user_id, kind, content, importance, created_at;
            """
            result = await fetch_one(
                query,
                user_id,
                kind,
                content,
                embedding,
                importance,
                json.dumps(governed_metadata),
                expires_at,
            )
        else:
            query = """
            INSERT INTO memory.long_term (user_id, scope, kind, content, embedding, importance, tags, metadata)
            VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8)
            RETURNING id, user_id, kind, content, importance, tags, created_at;
            """
            result = await fetch_one(
                query,
                user_id,
                scope,
                kind,
                content,
                embedding,
                importance,
                tags or [],
                json.dumps(governed_metadata),
            )

        # Audit log with caller for governance trail
        await execute(
            "INSERT INTO memory.audit_log (operation, table_name, memory_id, user_id, status, details) VALUES ($1, $2, $3, $4, $5, $6)",
            "INSERT",
            table,
            result["id"],
            user_id,
            "success",
            json.dumps({
                "duration": duration,
                "kind": kind,
                "caller": caller_id,
                "creator": creator,
                "source": source,
            }),
        )
        return result
    except Exception as e:
        logger.exception("Error saving memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(req: SearchMemoryRequest) -> SearchMemoryResponse:
    return await search_memory_handler(
        user_id=req.user_id,
        query=req.query,
        scopes=req.scopes,
        kinds=req.kinds,
        top_k=req.top_k,
        threshold=req.threshold,
        duration=req.duration,
    )


async def search_memory_handler(
    user_id: str,
    query: str,
    scopes: Optional[List[str]] = None,
    kinds: Optional[List[str]] = None,
    top_k: int = 5,
    threshold: float = 0.7,
    duration: str = "all",
) -> Dict[str, Any]:
    try:
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000

        search_start = time.time()
        results = []
        durations = ["short", "medium", "long"] if duration == "all" else [duration]

        for dur in durations:
            if dur == "short":
                table, where = "memory.short_term", "AND expires_at > CURRENT_TIMESTAMP"
            elif dur == "medium":
                table, where = (
                    "memory.medium_term",
                    "AND expires_at > CURRENT_TIMESTAMP",
                )
            else:
                table, where = "memory.long_term", ""

            params = [user_id]
            param_idx = 2
            scope_clause, kind_clause = "", ""

            if scopes and dur == "long":
                scope_clause = f"AND scope IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(scopes))])})"
                params.extend(scopes)
                param_idx += len(scopes)

            if kinds:
                kind_clause = f"AND kind IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(kinds))])})"
                params.extend(kinds)
                param_idx += len(kinds)

            cols = (
                "id, user_id, kind, content, importance, tags, created_at"
                if dur == "long"
                else "id, user_id, kind, content, importance, created_at"
            )
            params.extend([query_embedding, threshold, top_k])

            query_sql = f"""
            SELECT {cols}, 1 - (embedding <-> ${param_idx}::vector) as similarity
            FROM {table}
            WHERE user_id = $1 {where} {scope_clause} {kind_clause}
            AND 1 - (embedding <-> ${param_idx}::vector) >= ${param_idx + 1}
            ORDER BY similarity DESC LIMIT ${param_idx + 2};
            """
            rows = await fetch_all(query_sql, *params)

            if dur == "long" and rows:
                await execute(
                    "UPDATE memory.long_term SET last_accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE id = ANY($1::bigint[]);",
                    [r["id"] for r in rows],
                )

            results.extend(rows)

        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        results = results[:top_k]
        search_time_ms = (time.time() - search_start) * 1000

        await execute(
            "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "SEARCH",
            user_id,
            "success",
            json.dumps({"query": query, "results_count": len(results)}),
        )

        return {
            "results": results,
            "query_embedding_time_ms": embed_time_ms,
            "search_time_ms": search_time_ms,
            "total_results": len(results),
        }
    except Exception as e:
        logger.exception("Error searching memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    user_id: Optional[str] = Query(None), duration: str = Query("all")
) -> MemoryStatsResponse:
    try:
        short_count = medium_count = long_count = unique_users = 0
        avg_importance = 0.0

        if duration in ["all", "short"]:
            q = (
                "SELECT COUNT(*) as cnt FROM memory.short_term WHERE expires_at > CURRENT_TIMESTAMP"
                + (f" AND user_id = '{user_id}'" if user_id else "")
            )
            r = await fetch_one(q)
            short_count = r["cnt"] if r else 0

        if duration in ["all", "medium"]:
            q = (
                "SELECT COUNT(*) as cnt FROM memory.medium_term WHERE expires_at > CURRENT_TIMESTAMP"
                + (f" AND user_id = '{user_id}'" if user_id else "")
            )
            r = await fetch_one(q)
            medium_count = r["cnt"] if r else 0

        if duration in ["all", "long"]:
            q = (
                "SELECT COUNT(*) as cnt, COUNT(DISTINCT user_id) as users, AVG(importance) as avg_imp FROM memory.long_term"
                + (f" WHERE user_id = '{user_id}'" if user_id else "")
            )
            r = await fetch_one(q)
            if r:
                long_count, unique_users = r["cnt"], r["users"]
                avg_importance = float(r["avg_imp"]) if r["avg_imp"] else 0.0

        return MemoryStatsResponse(
            short_term_count=short_count,
            medium_term_count=medium_count,
            long_term_count=long_count,
            total_count=short_count + medium_count + long_count,
            unique_users=unique_users,
            avg_importance=avg_importance,
        )
    except Exception as e:
        logger.exception("Error getting stats")
        raise HTTPException(status_code=500, detail=str(e))


async def delete_expired_memories(dry_run: bool = True) -> Dict[str, Any]:
    short_r = await fetch_one(
        "SELECT COUNT(*) as cnt FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP"
    )
    medium_r = await fetch_one(
        "SELECT COUNT(*) as cnt FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP"
    )
    short_expired, medium_expired = (
        short_r["cnt"] if short_r else 0,
        medium_r["cnt"] if medium_r else 0,
    )

    if not dry_run:
        await execute(
            "DELETE FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP"
        )
        await execute(
            "DELETE FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP"
        )
        await execute(
            "INSERT INTO memory.audit_log (operation, status, details) VALUES ($1, $2, $3)",
            "CLEANUP",
            "success",
            json.dumps(
                {"short_deleted": short_expired, "medium_deleted": medium_expired}
            ),
        )

    return {
        "dry_run": dry_run,
        "short_term_expired": short_expired,
        "medium_term_expired": medium_expired,
        "total_expired": short_expired + medium_expired,
        "action": "deleted" if not dry_run else "would_delete",
    }


async def compound_similar_memories(
    user_id: str, threshold: float = 0.92
) -> Dict[str, Any]:
    if not settings.COMPOUNDING_ENABLED:
        return {"status": "disabled", "message": "Memory compounding is disabled"}

    memories = await fetch_all(
        "SELECT id, content, embedding, importance, access_count, created_at, tags FROM memory.long_term WHERE user_id = $1 ORDER BY created_at DESC;",
        user_id,
    )
    if len(memories) < 2:
        return {
            "status": "skipped",
            "message": "Not enough memories",
            "memories_analyzed": len(memories),
        }

    similar_pairs, processed_ids = [], set()
    for i, mem1 in enumerate(memories):
        if mem1["id"] in processed_ids:
            continue
        cluster = [mem1]
        for mem2 in memories[i + 1 :]:
            if mem2["id"] in processed_ids:
                continue
            sim = await fetch_one(
                "SELECT 1 - ($1::vector <-> $2::vector) as similarity;",
                mem1["embedding"],
                mem2["embedding"],
            )
            if sim and sim["similarity"] >= threshold:
                cluster.append(mem2)
                processed_ids.add(mem2["id"])
        if len(cluster) >= settings.COMPOUNDING_MIN_COUNT:
            similar_pairs.append(cluster)
            processed_ids.add(mem1["id"])

    merged_count = 0
    for cluster in similar_pairs:
        primary, duplicates = cluster[0], cluster[1:]
        combined_importance = min(1.0, sum(m["importance"] for m in cluster))
        combined_access = sum(m["access_count"] for m in cluster)
        merged_tags = set()
        for m in cluster:
            if m["tags"]:
                merged_tags.update(m["tags"])
        await execute(
            "UPDATE memory.long_term SET importance = $1, access_count = $2, tags = $3, updated_at = CURRENT_TIMESTAMP WHERE id = $4;",
            combined_importance,
            combined_access,
            list(merged_tags),
            primary["id"],
        )
        await execute(
            "DELETE FROM memory.long_term WHERE id = ANY($1::bigint[]);",
            [m["id"] for m in duplicates],
        )
        merged_count += len(duplicates)

    await execute(
        "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
        "COMPOUND",
        user_id,
        "success",
        json.dumps(
            {"clusters_found": len(similar_pairs), "memories_merged": merged_count}
        ),
    )

    return {
        "status": "completed",
        "memories_analyzed": len(memories),
        "clusters_found": len(similar_pairs),
        "memories_merged": merged_count,
        "threshold_used": threshold,
    }


async def apply_importance_decay(dry_run: bool = True) -> Dict[str, Any]:
    if not settings.DECAY_ENABLED:
        return {"status": "disabled", "message": "Importance decay is disabled"}

    decay_factor = 1.0 - settings.DECAY_RATE_PER_DAY
    count_r = await fetch_one(
        "SELECT COUNT(*) as cnt FROM memory.long_term WHERE last_accessed_at < NOW() - INTERVAL '1 day';"
    )
    affected = count_r["cnt"] if count_r else 0

    if not dry_run:
        await execute(
            f"UPDATE memory.long_term SET importance = importance * POWER({decay_factor}, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400), updated_at = CURRENT_TIMESTAMP WHERE last_accessed_at < NOW() - INTERVAL '1 day';"
        )
        await execute(
            "INSERT INTO memory.audit_log (operation, status, details) VALUES ($1, $2, $3)",
            "DECAY",
            "success",
            json.dumps({"memories_affected": affected, "decay_factor": decay_factor}),
        )

    return {
        "status": "completed" if not dry_run else "dry_run",
        "memories_affected": affected,
        "decay_factor": decay_factor,
        "action": "decayed" if not dry_run else "would_decay",
    }


async def cleanup_task():
    while True:
        try:
            await asyncio.sleep(settings.MEMORY_CLEANUP_INTERVAL_MINUTES * 60)
            await execute(
                "DELETE FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP;"
            )
            await execute(
                "DELETE FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP;"
            )
            if settings.DECAY_ENABLED:
                await apply_importance_decay(dry_run=False)
            logger.info("Cleanup task completed")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


# =============================================================================
# 10x Memory Upgrade Handlers
# =============================================================================


async def get_context_injection(
    task_description: str,
    user_id: str,
    top_k: int = 5,
    include_recent: bool = True,
    kinds: Optional[List[str]] = None,
    allowed_scopes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Auto-retrieve relevant memories for context injection before a task.
    This is the key leverage point - automatically surface relevant context.
    
    Args:
        allowed_scopes: If provided, restricts search to these scopes only.
                       Cursor gets ["user", "project", "global"] (no l-private).
                       L gets None (all scopes including l-private).
    """
    start_time = time.time()
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["user", "project", "global", "l-private"]
    
    try:
        # 1. Get semantically relevant memories for the task
        relevant_result = await search_memory_handler(
            user_id=user_id,
            query=task_description,
            scopes=search_scopes,
            kinds=kinds,
            top_k=top_k,
            threshold=0.6,  # Lower threshold for context injection
            duration="long",  # Focus on long-term memories
        )
        relevant_memories = relevant_result.get("results", [])
        
        # 2. Get recent context (last 24h) if requested
        recent_memories = []
        if include_recent:
            recent_query = """
            SELECT id, user_id, kind, content, importance, tags, created_at
            FROM memory.long_term
            WHERE user_id = $1 
            AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 5;
            """
            recent_memories = await fetch_all(recent_query, user_id)
            
            # Also check medium-term for very recent context
            medium_query = """
            SELECT id, user_id, kind, content, importance, created_at
            FROM memory.medium_term
            WHERE user_id = $1 
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC
            LIMIT 3;
            """
            medium_recent = await fetch_all(medium_query, user_id)
            recent_memories.extend(medium_recent)
        
        retrieval_time_ms = (time.time() - start_time) * 1000
        
        # Audit the context injection
        await execute(
            "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "CONTEXT_INJECTION",
            user_id,
            "success",
            json.dumps({
                "task": task_description[:100],
                "relevant_count": len(relevant_memories),
                "recent_count": len(recent_memories),
            }),
        )
        
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
) -> Dict[str, Any]:
    """
    Extract and store learnings from a completed session.
    This is the cross-session learning loop - every session makes us smarter.
    """
    try:
        memory_ids = []
        kinds_created = []
        
        # 1. Store the session summary as context
        summary_result = await save_memory_handler(
            user_id=user_id,
            content=f"[Session {session_id}] {session_summary}",
            kind="context",
            scope="user",
            duration="long",
            tags=["session:summary"],
            importance=0.8,
            metadata={"session_id": session_id, "type": "session_summary"},
        )
        memory_ids.append(summary_result["id"])
        kinds_created.append("context")
        
        # 2. Store key decisions
        if key_decisions:
            for decision in key_decisions:
                dec_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Decision] {decision}",
                    kind="decision",
                    scope="user",
                    duration="long",
                    tags=["session:decision"],
                    importance=0.9,
                    metadata={"session_id": session_id, "type": "decision"},
                )
                memory_ids.append(dec_result["id"])
                if "decision" not in kinds_created:
                    kinds_created.append("decision")
        
        # 3. Store error/fix pairs (critical for proactive recall)
        if errors_encountered:
            for error in errors_encountered:
                err_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Error+Fix] {error}",
                    kind="error",
                    scope="user",
                    duration="long",
                    tags=["session:error", "debug:fix"],
                    importance=0.95,  # High importance for error fixes
                    metadata={"session_id": session_id, "type": "error_fix"},
                )
                memory_ids.append(err_result["id"])
                if "error" not in kinds_created:
                    kinds_created.append("error")
        
        # 4. Store successes (what worked well)
        if successes:
            for success in successes:
                suc_result = await save_memory_handler(
                    user_id=user_id,
                    content=f"[Success] {success}",
                    kind="success",
                    scope="user",
                    duration="long",
                    tags=["session:success"],
                    importance=0.85,
                    metadata={"session_id": session_id, "type": "success"},
                )
                memory_ids.append(suc_result["id"])
                if "success" not in kinds_created:
                    kinds_created.append("success")
        
        # Audit
        await execute(
            "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "EXTRACT_LEARNINGS",
            user_id,
            "success",
            json.dumps({
                "session_id": session_id,
                "learnings_stored": len(memory_ids),
                "kinds": kinds_created,
            }),
        )
        
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
    Surfaces relevant past experiences, error fixes, and preferences.
    
    Args:
        allowed_scopes: If provided, restricts search to these scopes only.
                       Cursor gets ["user", "project", "global"] (no l-private).
                       L gets None (all scopes including l-private).
    """
    start_time = time.time()
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["user", "project", "global", "l-private"]
    
    try:
        suggestions = []
        error_fix_pairs = []
        relevant_preferences = []
        
        # 1. Get semantically similar memories
        search_result = await search_memory_handler(
            user_id=user_id,
            query=current_context,
            scopes=search_scopes,
            kinds=None,  # All kinds
            top_k=top_k * 2,  # Get more, then filter
            threshold=0.65,
            duration="long",
        )
        suggestions = search_result.get("results", [])[:top_k]
        
        # 2. Get relevant error/fix pairs
        if include_error_fixes:
            # Filter scopes for error search (respect allowed_scopes)
            error_scopes = [s for s in ["user", "project"] if s in search_scopes]
            error_search = await search_memory_handler(
                user_id=user_id,
                query=current_context,
                scopes=error_scopes if error_scopes else ["user", "project"],
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
                    "memory_id": mem.get("id"),
                })
        
        # 3. Get relevant preferences
        if include_preferences:
            # Filter scopes for preference search (respect allowed_scopes)
            pref_scopes = [s for s in ["user"] if s in search_scopes]
            pref_search = await search_memory_handler(
                user_id=user_id,
                query=current_context,
                scopes=pref_scopes if pref_scopes else ["user"],
                kinds=["preference"],
                top_k=3,
                threshold=0.5,  # Lower threshold for preferences
                duration="long",
            )
            relevant_preferences = pref_search.get("results", [])
        
        recall_time_ms = (time.time() - start_time) * 1000
        
        # Audit
        await execute(
            "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "PROACTIVE_RECALL",
            user_id,
            "success",
            json.dumps({
                "context": current_context[:100],
                "suggestions_count": len(suggestions),
                "error_fixes_count": len(error_fix_pairs),
                "preferences_count": len(relevant_preferences),
            }),
        )
        
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
    Query memory changes over time.
    Answer 'what changed since X' or 'show timeline of Y'.
    """
    try:
        # Parse datetime strings
        since_dt = datetime.fromisoformat(since) if since else datetime.utcnow() - timedelta(days=7)
        until_dt = datetime.fromisoformat(until) if until else datetime.utcnow()
        
        # Build WHERE clause
        where_parts = ["user_id = $1", "created_at >= $2", "created_at <= $3"]
        params = [user_id, since_dt, until_dt]
        param_idx = 4
        
        if kinds:
            kind_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(kinds))])
            where_parts.append(f"kind IN ({kind_placeholders})")
            params.extend(kinds)
        
        where_clause = " AND ".join(where_parts)
        
        if operation == "changes":
            # Get all memories created or updated in the period
            query = f"""
            SELECT id, user_id, kind, content, importance, tags, created_at, updated_at
            FROM memory.long_term
            WHERE {where_clause}
            ORDER BY created_at DESC;
            """
            memories = await fetch_all(query, *params)
            
            # Count created vs updated
            created_count = sum(1 for m in memories if m.get("created_at") == m.get("updated_at"))
            updated_count = len(memories) - created_count
            
        elif operation == "timeline":
            # Get timeline of memory creation
            query = f"""
            SELECT id, user_id, kind, content, importance, tags, created_at
            FROM memory.long_term
            WHERE {where_clause}
            ORDER BY created_at ASC;
            """
            memories = await fetch_all(query, *params)
            created_count = len(memories)
            updated_count = 0
            
        else:  # diff
            # Get memories with differences (updated != created)
            query = f"""
            SELECT id, user_id, kind, content, importance, tags, created_at, updated_at
            FROM memory.long_term
            WHERE {where_clause} AND updated_at > created_at
            ORDER BY updated_at DESC;
            """
            memories = await fetch_all(query, *params)
            created_count = 0
            updated_count = len(memories)
        
        # Check audit log for deletes
        delete_query = """
        SELECT COUNT(*) as cnt FROM memory.audit_log
        WHERE user_id = $1 AND operation = 'DELETE' 
        AND created_at >= $2 AND created_at <= $3;
        """
        delete_result = await fetch_one(delete_query, user_id, since_dt, until_dt)
        deleted_count = delete_result["cnt"] if delete_result else 0
        
        return {
            "memories": memories,
            "created_count": created_count,
            "updated_count": updated_count,
            "deleted_count": deleted_count,
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
    scope: str = "user",
    duration: str = "long",
    confidence: float = 1.0,
    source: str = "cursor",  # Now enforced server-side
    related_memory_ids: Optional[List[int]] = None,
    tags: Optional[List[str]] = None,
    importance: float = 1.0,
    # Governance fields (enforced server-side)
    caller_id: str = "unknown",
    creator: str = "unknown",
) -> Dict[str, Any]:
    """
    Save a memory with explicit confidence scoring and relationship linking.
    
    See: mcp_memory/memory-setup-instructions.md for governance spec.
    source and creator are enforced server-side based on caller identity.
    """
    try:
        # Add confidence and source to metadata
        metadata = {
            "confidence": confidence,
            "source": source,  # Enforced from caller identity
            "related_memory_ids": related_memory_ids or [],
        }
        
        # Scale importance by confidence (lower confidence = lower effective importance)
        effective_importance = importance * confidence
        
        # Add confidence tag
        all_tags = list(tags or [])
        if confidence >= 0.9:
            all_tags.append("confidence:high")
        elif confidence >= 0.7:
            all_tags.append("confidence:medium")
        else:
            all_tags.append("confidence:low")
        
        # Save using existing handler with governance fields
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
        
        # If there are related memories, log the relationship
        if related_memory_ids:
            for related_id in related_memory_ids:
                await execute(
                    "INSERT INTO memory.audit_log (operation, table_name, memory_id, user_id, status, details) VALUES ($1, $2, $3, $4, $5, $6)",
                    "LINK",
                    "memory.long_term",
                    result["id"],
                    user_id,
                    "success",
                    json.dumps({"related_to": related_id, "relationship": "related"}),
                )
        
        return result
    except Exception as e:
        logger.exception("Error saving memory with confidence")
        raise HTTPException(status_code=500, detail=str(e))
