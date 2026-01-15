

api/memory/router.py
api/memory/router.py
+49
-5

"""
L9 Memory API Router
Version: 1.1.0

Memory substrate API endpoints using MemorySubstrateService.
All packets are automatically ingested via canonical ingest_packet().
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from api.auth import verify_api_key
from typing import Optional, List
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

router = APIRouter()
async def memory_governance_context_dependency(
    _: bool = Depends(verify_api_key),
) -> AsyncGenerator[None, None]:
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
@@ -136,62 +159,83 @@ async def create_packet(
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
            packet_count = await conn.fetchval("SELECT COUNT(*) FROM packet_store")
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=1, table_alias="packet_store"
            )
            packet_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM packet_store WHERE TRUE {filter_clause}",
                *params,
            )
            embedding_count = await conn.fetchval(
                "SELECT COUNT(*) FROM semantic_memory"
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
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


@router.get("/packet/{packet_id}")
async def get_packet(
    packet_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
core/compliance/audit_log.py
core/compliance/audit_log.py
+1
-2

@@ -277,51 +277,51 @@ class AuditLogger:
        Returns:
            True if logged successfully, False otherwise
        """
        timestamp = timestamp or datetime.utcnow().isoformat()

        audit_entry = {
            "audit_type": "memory_write",
            "agent_id": agent_id,
            "segment": segment,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "packet_type": packet_type,
            "thread_id": thread_id,
            "timestamp": timestamp,
        }

        logger.info(
            "Audit memory write",
            agent_id=agent_id,
            segment=segment,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        if self._substrate is None:
            return True
            return False

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="audit_memory_write",
                payload=audit_entry,
                metadata={
                    "immutable": True,
                    "retention_years": 7,
                    "source": "memory-substrate",
                },
            )

            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.error("Failed to write memory audit to substrate", error=str(e))
            return False


async def log_command_to_audit(
    substrate_service: Any,
    command_id: str,
@@ -345,26 +345,25 @@ async def log_command_to_audit(
        risk_level: Risk level of the command
        raw_text: Original command text
        result: Optional result data
        error: Optional error message

    Returns:
        True if logged successfully, False otherwise
    """
    audit_logger = AuditLogger(substrate_service)
    return await audit_logger.log_command(
        command_id=command_id,
        command_type=command_type,
        user_id=user_id,
        action=action,
        risk_level=risk_level,
        raw_text=raw_text,
        result=result,
        error=error,
    )


__all__ = [
    "AuditLogger",
    "log_command_to_audit",
]

mcp_memory/src/config.py
mcp_memory/src/config.py
+3
-0

@@ -59,50 +59,53 @@ class Settings(BaseSettings):

    # Authentication - Dual API Keys for L and C
    # See: mcp_memory/memory-setup-instructions.md for governance spec
    # Primary keys (required):
    # - MCP_API_KEY_L: L-CTO kernel (full read/write/delete)
    # - MCP_API_KEY_C: Cursor IDE (read all, write/delete own only)
    # Legacy fallbacks (optional, for backward compatibility):
    # - MCP_API_KEY: Shared fallback (maps to L if MCP_API_KEY_L not set)
    # - MCPL9MEMORYKEY: Legacy alias (same as MCP_API_KEY)
    # - MCP_API_KEYL: Legacy alias for MCP_API_KEY_L
    # - MCP_API_KEYC: Legacy alias for MCP_API_KEY_C
    MCP_API_KEY_L: str = ""  # L-CTO API key (required, but allow empty for validation)
    MCP_API_KEY_C: str = ""  # Cursor IDE API key (required, but allow empty for validation)
    
    # Legacy fallback keys (optional)
    MCP_API_KEY: str = ""  # Shared fallback (legacy)
    MCPL9MEMORYKEY: str = ""  # Legacy alias (same as MCP_API_KEY)
    MCP_API_KEYL: str = ""  # Legacy alias for MCP_API_KEY_L
    MCP_API_KEYC: str = ""  # Legacy alias for MCP_API_KEY_C

    # Shared User Identity (L and C operate in same semantic space)
    # Separation is enforced via metadata.creator and caller identity
    # See: memory-setup-instructions.md → userid_strategy
    L_CTO_USER_ID: str = "l9-shared"  # Shared userid for L + Cursor collaboration

    # Project isolation (server-derived, not client-supplied)
    MCP_PROJECT_ID: str = "l9"

    # Redis (optional)
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_api_key_l() -> str:
    """Get L-CTO API key with legacy fallback support.
    
    Priority:
    1. MCP_API_KEY_L (primary)
    2. MCP_API_KEYL (legacy alias)
    3. MCP_API_KEY (shared fallback)
    4. MCPL9MEMORYKEY (legacy alias)
    """
    if settings.MCP_API_KEY_L:
        return settings.MCP_API_KEY_L
    if settings.MCP_API_KEYL:
mcp_memory/src/db.py
mcp_memory/src/db.py
+5
-0

"""
PostgreSQL async client with pgvector support.
"""

import asyncpg
import json
import structlog
from typing import List, Dict, Any, Optional
from src.config import settings
from memory.governance_gate import require_governance_context

logger = structlog.get_logger(__name__)
pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.MEMORY_DSN,
        min_size=5,
        max_size=20,
        command_timeout=60,
        init=_init_connection,  # Register JSON codecs on each connection
    )
    await pool.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    logger.info("Database pool initialized with JSON codecs")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")


async def execute(query: str, *args) -> Any:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.execute")
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_one")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_all")
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def insert_many(query: str, args_list: List[tuple]) -> int:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.insert_many")
    async with pool.acquire() as conn:
        result = await conn.executemany(query, args_list)
    count = int(result.split()[-1]) if result else 0
    return count
mcp_memory/src/mcp_server.py
mcp_memory/src/mcp_server.py
+226
-85

@@ -295,74 +295,89 @@ def get_mcp_tools() -> List[MCPTool]:
                "required": ["content", "kind", "duration", "user_id"],
            },
        ),
    ]


async def handle_tool_call(
    tool: MCPToolCall, 
    user_id: str, 
    caller: Any = None,
    substrate_service: Any = None,  # Optional: MemorySubstrateService for main pipeline
) -> Dict[str, Any]:
    """Handle MCP tool call with caller-enforced governance.
    
    Args:
        tool: The tool call request
        user_id: Shared user_id (L_CTO_USER_ID)
        caller: CallerIdentity with caller_id, creator, source (L or C)
    
    See: mcp_memory/memory-setup-instructions.md for governance spec.
    
    Raises:
        ValidationError: If tool arguments don't match expected schema
        ValueError: If governance rules are violated (e.g., Cursor writing l-private)
    """
    import time
    import json
    from src.db import execute
    from src.models import (
import time
import json
from src.db import execute
from src.config import settings
from src.models import (
        SaveMemoryArgs,
        SearchMemoryArgs,
        GetMemoryStatsArgs,
        DeleteExpiredMemoriesArgs,
        CompoundMemoriesArgs,
        ApplyDecayArgs,
        GetContextArgs,
        ExtractSessionLearningsArgs,
        GetProactiveSuggestionsArgs,
        QueryTemporalArgs,
        SaveMemoryWithConfidenceArgs,
    )
)
from memory.governance_gate import build_governance_context, governance_context
    
    # Extract caller metadata for enforcement
    caller_id = caller.caller_id if caller else "unknown"
    creator = caller.creator if caller else "unknown"
    source = caller.source if caller else "unknown"
    
    # Determine project_id (default: 'l9' for developer/l-private scope)
    project_id = "l9"  # Default for L9 repo
    # Determine project_id (server-derived only)
    project_id = settings.MCP_PROJECT_ID

    default_allowed_scopes = ["developer", "global", "l-private"]
    if caller_id == "C":
        default_allowed_scopes = ["developer", "global"]
    governance_ctx = build_governance_context(
        caller_id=caller_id,
        role="end_user",
        scope="developer",
        project_id=project_id,
        allowed_scopes=default_allowed_scopes,
        creator=creator,
        source=source,
    )
    
    # Track execution time for audit
    start_time = time.time()
    
    result = None
    error = None
    
    # =============================================================================
    # INPUT VALIDATION: Validate tool arguments using Pydantic models
    # =============================================================================
    # Fail-fast contract: Validate before any processing to catch invalid inputs early
    try:
        if tool.name == "save_memory":
            validated_args = SaveMemoryArgs(**tool.arguments)
        elif tool.name == "search_memory":
            validated_args = SearchMemoryArgs(**tool.arguments)
        elif tool.name == "get_memory_stats":
            validated_args = GetMemoryStatsArgs(**tool.arguments)
        elif tool.name == "delete_expired_memories":
            validated_args = DeleteExpiredMemoriesArgs(**tool.arguments)
        elif tool.name == "compound_memories":
            validated_args = CompoundMemoriesArgs(**tool.arguments)
        elif tool.name == "apply_decay":
            validated_args = ApplyDecayArgs(**tool.arguments)
        elif tool.name == "get_context":
@@ -370,225 +385,351 @@ async def handle_tool_call(
        elif tool.name == "extract_session_learnings":
            validated_args = ExtractSessionLearningsArgs(**tool.arguments)
        elif tool.name == "get_proactive_suggestions":
            validated_args = GetProactiveSuggestionsArgs(**tool.arguments)
        elif tool.name == "query_temporal":
            validated_args = QueryTemporalArgs(**tool.arguments)
        elif tool.name == "save_memory_with_confidence":
            validated_args = SaveMemoryWithConfidenceArgs(**tool.arguments)
        else:
            raise ValueError(f"Unknown tool: {tool.name}")
    except ValidationError as e:
        # Fail-fast: Invalid input detected, reject immediately
        error_msg = f"Invalid arguments for tool '{tool.name}': {e.errors()}"
        logger.warning(error_msg, tool_name=tool.name, validation_errors=e.errors())
        raise ValueError(error_msg) from e
    
    try:
        if tool.name == "save_memory":
            from src.routes.memory_unified import save_memory_handler

            requested_scope = tool.arguments.get("scope", "developer")  # MCP scope: developer/l-private/global
            
            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError("Cursor cannot write to l-private scope. Only L-CTO can write private memories.")
            
            result = await save_memory_handler(
                user_id=user_id,
                content=tool.arguments.get("content"),
                kind=tool.arguments.get("kind"),
                scope=requested_scope,
                duration=tool.arguments.get("duration"),
                tags=tool.arguments.get("tags", []),
                importance=tool.arguments.get("importance", 1.0),

            allowed_scopes = ["developer", "global", "l-private"]
            if caller_id == "C":
                allowed_scopes = ["developer", "global"]

            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope=requested_scope,
                project_id=project_id,
                allowed_scopes=allowed_scopes,
                creator=creator,
                source=source,
                substrate_service=substrate_service,  # Pass service for main pipeline
            )
            async with governance_context(governance_ctx):
                result = await save_memory_handler(
                    user_id=user_id,
                    content=tool.arguments.get("content"),
                    kind=tool.arguments.get("kind"),
                    scope=requested_scope,
                    duration=tool.arguments.get("duration"),
                    tags=tool.arguments.get("tags", []),
                    importance=tool.arguments.get("importance", 1.0),
                    substrate_service=substrate_service,  # Pass service for main pipeline
                )
        elif tool.name == "search_memory":
            from src.routes.memory_unified import search_memory_handler

            requested_scopes = tool.arguments.get("scopes", ["developer", "global"])  # MCP scopes
            
            # Enforce: Cursor CANNOT see l-private scope (filter it out)
            if caller_id == "C" and "l-private" in requested_scopes:
                requested_scopes = [s for s in requested_scopes if s != "l-private"]
            
            # L gets all scopes including l-private
            if caller_id == "L" and "l-private" not in requested_scopes:
                # L can explicitly request l-private, but default includes it
                pass  # Don't auto-add, respect explicit request
            
            result = await search_memory_handler(
                user_id=user_id,
                query=tool.arguments.get("query"),
                scopes=requested_scopes,
                kinds=tool.arguments.get("kinds"),
                top_k=tool.arguments.get("top_k", 5),
                threshold=tool.arguments.get("threshold", 0.7),
                duration=tool.arguments.get("duration", "all"),
                caller_id=caller_id,  # Perplexity: pass caller for audit logging
            allowed_scopes = ["developer", "global", "l-private"]
            if caller_id == "C":
                allowed_scopes = ["developer", "global"]

            effective_scopes = [s for s in requested_scopes if s in allowed_scopes]
            scope_for_context = effective_scopes[0] if effective_scopes else allowed_scopes[0]

            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope=scope_for_context,
                project_id=project_id,
                allowed_scopes=allowed_scopes,
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await search_memory_handler(
                    user_id=user_id,
                    query=tool.arguments.get("query"),
                    scopes=effective_scopes,
                    kinds=tool.arguments.get("kinds"),
                    top_k=tool.arguments.get("top_k", 5),
                    threshold=tool.arguments.get("threshold", 0.7),
                    duration=tool.arguments.get("duration", "all"),
                )
        elif tool.name == "get_memory_stats":
            from src.routes.memory_unified import get_memory_stats

            result = await get_memory_stats(
                user_id=tool.arguments.get("user_id"),
                duration=tool.arguments.get("duration", "all"),
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await get_memory_stats(
                    user_id=tool.arguments.get("user_id"),
                    duration=tool.arguments.get("duration", "all"),
                )
        elif tool.name == "delete_expired_memories":
            from src.routes.memory_unified import delete_expired_memories

            result = await delete_expired_memories(
                dry_run=tool.arguments.get("dry_run", True)
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await delete_expired_memories(
                    dry_run=tool.arguments.get("dry_run", True)
                )
        elif tool.name == "compound_memories":
            from src.routes.memory_unified import compound_similar_memories

            result = await compound_similar_memories(
                user_id=tool.arguments.get("user_id"),
                threshold=tool.arguments.get("threshold", 0.92),
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await compound_similar_memories(
                    user_id=tool.arguments.get("user_id"),
                    threshold=tool.arguments.get("threshold", 0.92),
                )
        elif tool.name == "apply_decay":
            from src.routes.memory_unified import apply_importance_decay

            result = await apply_importance_decay(dry_run=tool.arguments.get("dry_run", True))
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await apply_importance_decay(
                    dry_run=tool.arguments.get("dry_run", True)
                )
        # =============================================================================
        # 10x Memory Upgrade Tool Handlers
        # =============================================================================
        elif tool.name == "get_context":
            from src.routes.memory_unified import get_context_injection

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None
            
            result = await get_context_injection(
                task_description=tool.arguments.get("task_description"),
                user_id=user_id,
                top_k=tool.arguments.get("top_k", 5),
                include_recent=tool.arguments.get("include_recent", True),
                kinds=tool.arguments.get("kinds"),
                allowed_scopes=allowed_scopes,

            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=allowed_scopes or ["developer", "global", "l-private"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await get_context_injection(
                    task_description=tool.arguments.get("task_description"),
                    user_id=user_id,
                    top_k=tool.arguments.get("top_k", 5),
                    include_recent=tool.arguments.get("include_recent", True),
                    kinds=tool.arguments.get("kinds"),
                    allowed_scopes=allowed_scopes,
                )
        elif tool.name == "extract_session_learnings":
            from src.routes.memory_unified import extract_session_learnings

            result = await extract_session_learnings(
                user_id=user_id,
                session_id=tool.arguments.get("session_id"),
                session_summary=tool.arguments.get("session_summary"),
                key_decisions=tool.arguments.get("key_decisions"),
                errors_encountered=tool.arguments.get("errors_encountered"),
                successes=tool.arguments.get("successes"),
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await extract_session_learnings(
                    user_id=user_id,
                    session_id=tool.arguments.get("session_id"),
                    session_summary=tool.arguments.get("session_summary"),
                    key_decisions=tool.arguments.get("key_decisions"),
                    errors_encountered=tool.arguments.get("errors_encountered"),
                    successes=tool.arguments.get("successes"),
                )
        elif tool.name == "get_proactive_suggestions":
            from src.routes.memory_unified import get_proactive_suggestions

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None
            
            result = await get_proactive_suggestions(
                current_context=tool.arguments.get("current_context"),
                user_id=user_id,
                include_error_fixes=tool.arguments.get("include_error_fixes", True),
                include_preferences=tool.arguments.get("include_preferences", True),
                top_k=tool.arguments.get("top_k", 3),
                allowed_scopes=allowed_scopes,

            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=allowed_scopes or ["developer", "global", "l-private"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await get_proactive_suggestions(
                    current_context=tool.arguments.get("current_context"),
                    user_id=user_id,
                    include_error_fixes=tool.arguments.get("include_error_fixes", True),
                    include_preferences=tool.arguments.get("include_preferences", True),
                    top_k=tool.arguments.get("top_k", 3),
                    allowed_scopes=allowed_scopes,
                )
        elif tool.name == "query_temporal":
            from src.routes.memory_unified import query_temporal

            result = await query_temporal(
                user_id=user_id,
                since=tool.arguments.get("since"),
                until=tool.arguments.get("until"),
                kinds=tool.arguments.get("kinds"),
                operation=tool.arguments.get("operation", "changes"),
            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope="developer",
                project_id=project_id,
                allowed_scopes=["developer", "global", "l-private"]
                if caller_id == "L"
                else ["developer", "global"],
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await query_temporal(
                    user_id=user_id,
                    since=tool.arguments.get("since"),
                    until=tool.arguments.get("until"),
                    kinds=tool.arguments.get("kinds"),
                    operation=tool.arguments.get("operation", "changes"),
                )
        elif tool.name == "save_memory_with_confidence":
            from src.routes.memory_unified import save_memory_with_confidence

            requested_scope = tool.arguments.get("scope", "developer")  # MCP scope
            
            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError("Cursor cannot write to l-private scope. Only L-CTO can write private memories.")
            
            result = await save_memory_with_confidence(
                user_id=user_id,
                content=tool.arguments.get("content"),
                kind=tool.arguments.get("kind"),
                scope=requested_scope,
                duration=tool.arguments.get("duration"),
                confidence=tool.arguments.get("confidence", 1.0),
                # Source is enforced server-side, not from client
                source=source,  # From caller identity, not payload
                related_memory_ids=tool.arguments.get("related_memory_ids"),
                tags=tool.arguments.get("tags", []),
                importance=tool.arguments.get("importance", 1.0),

            allowed_scopes = ["developer", "global", "l-private"]
            if caller_id == "C":
                allowed_scopes = ["developer", "global"]

            governance_ctx = build_governance_context(
                caller_id=caller_id,
                role="end_user",
                scope=requested_scope,
                project_id=project_id,
                allowed_scopes=allowed_scopes,
                creator=creator,
                source=source,
            )
            async with governance_context(governance_ctx):
                result = await save_memory_with_confidence(
                    user_id=user_id,
                    content=tool.arguments.get("content"),
                    kind=tool.arguments.get("kind"),
                    scope=requested_scope,
                    duration=tool.arguments.get("duration"),
                    confidence=tool.arguments.get("confidence", 1.0),
                    # Source is enforced server-side, not from client
                    source=source,  # From caller identity, not payload
                    related_memory_ids=tool.arguments.get("related_memory_ids"),
                    tags=tool.arguments.get("tags", []),
                    importance=tool.arguments.get("importance", 1.0),
                )
        else:
            raise ValueError(f"Unknown tool: {tool.name}")
        
        # Calculate execution time
        duration_ms = (time.time() - start_time) * 1000
        
        # Audit logging: Log to tool_audit_log (L9 substrate)
        try:
        if governance_ctx is None:
            raise RuntimeError("Governance context missing for audit logging")
        async with governance_context(governance_ctx):
            await execute(
                """
                INSERT INTO tool_audit_log (
                    tool_name, agent_id, caller, project_id,
                    input_data, output_data, duration_ms, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                tool.name,  # tool_name
                user_id,  # agent_id
                caller_id,  # caller ('L' or 'C')
                project_id,  # project_id ('l9' or NULL)
                project_id,  # project_id
                json.dumps(tool.arguments),  # input_data
                json.dumps(result) if result else json.dumps({"error": "No result"}),  # output_data
                duration_ms,  # duration_ms
            )
        except Exception as audit_err:
            # Don't fail if tool_audit_log table doesn't exist yet (migration 0013 may not be applied)
            logger.debug(f"Audit logging skipped (table may not exist): {audit_err}")
        
        return result
        
    except Exception as e:
        # Calculate execution time even on error
        duration_ms = (time.time() - start_time) * 1000
        error = str(e)
        
        # Audit logging: Log error to tool_audit_log
        try:
        if governance_ctx is None:
            raise RuntimeError("Governance context missing for audit logging")
        async with governance_context(governance_ctx):
            await execute(
                """
                INSERT INTO tool_audit_log (
                    tool_name, agent_id, caller, project_id,
                    input_data, output_data, duration_ms, error, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                tool.name,
                user_id,
                caller_id,
                project_id,
                json.dumps(tool.arguments),
                json.dumps({"error": error}),
                duration_ms,
                error,
            )
        except Exception as audit_err:
            logger.debug(f"Audit logging skipped (table may not exist): {audit_err}")
        
        raise
mcp_memory/src/routes/memory.py
mcp_memory/src/routes/memory.py
+6
-2

"""Memory CRUD, search, compounding, and decay routes."""

import structlog
import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi import APIRouter, HTTPException, Query, Depends
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
def _legacy_memory_disabled() -> None:
    raise HTTPException(status_code=410, detail="Legacy memory routes disabled")


router = APIRouter(dependencies=[Depends(_legacy_memory_disabled)])


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
mcp_memory/src/routes/memory_unified.py
mcp_memory/src/routes/memory_unified.py
+135
-138

"""Memory CRUD using unified L9 substrate (packet_store + memory_embeddings).

This replaces the deprecated memory.* tables with the unified L9 memory substrate.
Uses packet_store for event log and memory_embeddings for vector storage.

NOW USES MAIN L9 INGESTION PIPELINE:
- Routes through MemorySubstrateService.write_packet() for full DAG pipeline
- Gets graph sync (Neo4j), fact extraction, reasoning traces automatically
- Uses same OpenAI embeddings and processing as L agent
- Falls back to direct DB access if service not initialized
"""

import structlog
import time
import json
import uuid
import asyncpg
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi import APIRouter, HTTPException, Query
import asyncio

from src.db import fetch_all, fetch_one, execute
from src.embeddings import embed_text
from src.config import settings
from memory.governance_gate import ensure_governance_context, require_governance_context

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_substrate_service(request: Request):
    """Get MemorySubstrateService from app state (if initialized)."""
    return getattr(request.app.state, "substrate_service", None)


def map_mcp_scope_to_db_scope(mcp_scope: str) -> str:
    """
    Map MCP governance scopes to DB scope values.
    
    MCP scopes: 'developer', 'l-private', 'global'
    DB scopes: 'shared', 'l-private' (current), 'developer', 'global' (target after migration)
    
    For now, map:
    - 'developer' → 'shared' (shared between L and Cursor)
    - 'l-private' → 'l-private' (L only)
    - 'global' → 'shared' (cross-project, shared)
    - 'developer' → 'developer'
    - 'l-private' → 'l-private'
    - 'global' → 'global'
    """
    mapping = {
        "developer": "shared",  # Shared developer collaboration
        "l-private": "l-private",  # L's private operations
        "global": "shared",  # Cross-project shared knowledge
    }
    return mapping.get(mcp_scope, "shared")
    return mcp_scope


def map_db_scope_to_mcp_scope(db_scope: str) -> str:
    """Reverse mapping: DB scope → MCP scope."""
    # For now, 'shared' maps to 'developer' (most common case)
    # 'l-private' stays the same
    if db_scope == "l-private":
        return "l-private"
    return "developer"  # Default 'shared' → 'developer'
    return db_scope


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
    # Optional: substrate service from app state (for main ingestion pipeline)
    substrate_service: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Save memory with tiered fallback (v2.1.0 - GMP-67 corrected).
    
    Tier 1: Try full pipeline (core + enrichment if enabled)
            - Enrichment failure = 200 with enrichment_status="failed" (NO RETRY)
            - Core failure = fall to Tier 2
    Tier 2: Try direct DB (emergency fallback)
            - Success = 200 with tier_used="direct_db"
            - Failure = fall to Tier 3
    Tier 3: Return 503 Service Unavailable
    
    KEY INVARIANT: Enrichment is NEVER retried. If it fails, core write already persisted.
    
    Args:
        scope: MCP scope ('developer', 'l-private', 'global')
        caller_id: "L" or "C" (from API key)
        creator: "L-CTO" or "Cursor-IDE" (server-enforced)
        source: "l9-kernel" or "cursor-ide" (server-enforced)
        substrate_service: Optional MemorySubstrateService instance
    """
    ctx = require_governance_context("mcp_memory.save_memory")
    if scope != ctx.scope:
        raise HTTPException(status_code=403, detail="Scope not authorized")
    pipeline_error = None
    
    # Tier 1: Full pipeline (preferred path)
    if substrate_service:
        try:
            result = await _save_via_main_pipeline(
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
            
            # Enrichment failure is NOT a tier failure - core write succeeded
            # Just return 200 with enrichment_status="failed" (already set in result)
            return result
            
        except Exception as e:
            pipeline_error = str(e)
            logger.warning(
                "Full pipeline failed, falling back to direct DB",
                error=pipeline_error,
            )
            # Fall through to Tier 2
    
    # Tier 2: Direct DB (emergency fallback)
    try:
        logger.debug("Using direct DB access (substrate service unavailable or failed)")
        result = await _save_via_direct_db(
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
        )
        # Mark as fallback tier
        result["tier_used"] = "direct_db"
        result["warnings"] = ["pipeline_unavailable", "enrichment_skipped", "neo4j_skipped"]
        result["enrichment_status"] = "not_attempted"
        logger.info("Saved via direct DB fallback", packet_id=result.get("packet_id"))
        return result
        
    except Exception as direct_db_error:
        # Tier 3: 503
        logger.error(
            "All fallbacks exhausted",
            pipeline_error=pipeline_error,
            direct_db_error=str(direct_db_error),
        )
        raise HTTPException(
            status_code=503,
            detail="Memory substrate unavailable. All fallbacks exhausted.",
        )


async def _save_via_main_pipeline(
    user_id: str,
    content: str,
    kind: str,
    scope: str,
    duration: str,
    tags: Optional[List[str]],
    importance: float,
    metadata: Optional[Dict[str, Any]],
    caller_id: str,
    creator: str,
    source: str,
    substrate_service: Any,
) -> Dict[str, Any]:
    """Save memory via main L9 ingestion pipeline (full DAG)."""
    from core.schemas import PacketEnvelopeIn, PacketMetadata, PacketProvenance
    from datetime import timedelta
    ctx = require_governance_context("mcp_memory.save_memory.pipeline")
    
    # Map MCP scope to DB scope
    db_scope = map_mcp_scope_to_db_scope(scope)
    
    # Determine project_id
    project_id = None
    if metadata:
        project_id = metadata.get("project_id")
    if project_id is None:
        project_id = "l9" if scope != "global" else None
    project_id = ctx.project_id
    
    # Calculate TTL based on duration
    ttl = None
    if duration == "short":
        ttl = datetime.utcnow() + timedelta(hours=settings.MEMORY_SHORT_TERM_HOURS)
    elif duration == "medium":
        ttl = datetime.utcnow() + timedelta(hours=settings.MEMORY_MEDIUM_TERM_HOURS)
    
    # Build metadata dict (not PacketMetadata model - that's for envelope metadata)
    sanitized_metadata = (
        {}
        if metadata is None
        else {
            k: v
            for k, v in metadata.items()
            if k
            not in {
                "caller",
                "creator",
                "source",
                "project_id",
                "scope",
                "db_scope",
                "agent",
            }
        }
    )

    envelope_metadata = {
        "creator": creator,
        "source": source,
        "caller": caller_id,
        "agent": "l-cto" if caller_id == "L" else "cursor-ide",
        "creator": ctx.creator or "unknown",
        "source": ctx.source or "unknown",
        "caller": ctx.caller_id,
        "agent": "l-cto" if ctx.caller_id == "L" else "cursor-ide",
        "user_id": user_id,
        "project_id": project_id,
        "importance": importance,
        "duration": duration,
        "scope": scope,  # MCP scope preserved
        "db_scope": db_scope,  # DB scope for filtering
        **(metadata or {}),
        **sanitized_metadata,
    }
    
    # Build provenance
    provenance = PacketProvenance(
        source=source,
        source_agent="l-cto" if caller_id == "L" else "cursor-ide",
        source=ctx.source or "unknown",
        source_agent="l-cto" if ctx.caller_id == "L" else "cursor-ide",
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
            "project_id": project_id,
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
    result = await substrate_service.write_packet(packet_in)
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
        caller=ctx.caller_id,
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
        "created_at": datetime.utcnow().isoformat(),
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


async def _save_via_direct_db(
    user_id: str,
    content: str,
    kind: str,
    scope: str,
    duration: str,
    tags: Optional[List[str]],
    importance: float,
    metadata: Optional[Dict[str, Any]],
    caller_id: str,
    creator: str,
    source: str,
) -> Dict[str, Any]:
    """Fallback: Save memory via direct DB access (legacy path)."""
    ctx = require_governance_context("mcp_memory.save_memory.direct_db")
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
    project_id = None
    if metadata:
        project_id = metadata.get("project_id")
    if project_id is None:
        project_id = "l9" if scope != "global" else None
    project_id = ctx.project_id
    
    envelope = {
        "packet_id": str(packet_id),
        "packet_type": f"memory_write_{kind}",
        "timestamp": timestamp.isoformat(),
        "payload": {
            "content": content,
            "kind": kind,
            "scope": scope,
            "project_id": project_id,
        },
        "metadata": {
            "creator": creator,
            "source": source,
            "caller": caller_id,
            "agent": "l-cto" if caller_id == "L" else "cursor-ide",
            "creator": ctx.creator or "unknown",
            "source": ctx.source or "unknown",
            "caller": ctx.caller_id,
            "agent": "l-cto" if ctx.caller_id == "L" else "cursor-ide",
            "user_id": user_id,
            "project_id": project_id,
            "importance": importance,
            "duration": duration,
            **({} if metadata is None else {k: v for k, v in metadata.items() if k != "project_id"}),
            **({} if metadata is None else {k: v for k, v in metadata.items() if k not in {"project_id", "caller", "creator", "source", "scope"}}),
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
@@ -400,152 +383,164 @@ async def _save_via_direct_db(
        "kind": kind,
        "scope": scope,
        "duration": duration,
        "importance": importance,
        "embed_time_ms": embed_time_ms,
    }
    
    # Convert embedding vector to string format for pgvector
    vector_str = f"[{','.join(str(v) for v in embedding_vector)}]"
    
    embedding_result = await fetch_one(
        insert_embedding_query,
        packet_id,
        "content",
        vector_str,
        content[:500],
        json.dumps(embedding_metadata),
    )
    
    logger.info(
        "Memory saved via direct DB (fallback)",
        packet_id=str(packet_id),
        scope=scope,
        db_scope=db_scope,
        kind=kind,
        caller=caller_id,
        caller=ctx.caller_id,
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
        "pipeline": "direct_db",  # Indicates fallback path was used
    }


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
        ctx = require_governance_context("mcp_memory.search_memory")
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000
        
        # Convert embedding vector to string format for pgvector
        # pgvector expects format: '[1.0,2.0,3.0]'
        query_embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"
        
        # Map MCP scopes to DB scopes
        db_scopes = [map_mcp_scope_to_db_scope(s) for s in (scopes or ["developer", "global"])]
        requested_scopes = scopes or ["developer", "global"]
        db_scopes = [
            map_mcp_scope_to_db_scope(s)
            for s in requested_scopes
            if s in ctx.allowed_scopes
        ]
        if not db_scopes:
            raise HTTPException(status_code=403, detail="No authorized scopes available")
        
        search_start = time.time()
        
        # Build WHERE clause for scope filtering
        # Build WHERE clause for scope + project filtering
        scope_filter = ""
        params = [query_embedding_str, threshold, top_k]
        param_idx = 4
        
        if db_scopes:
            scope_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(db_scopes))])
            scope_filter = f"AND ps.scope IN ({scope_placeholders})"
            params.extend(db_scopes)
            param_idx += len(db_scopes)

        project_filter = f"AND ps.envelope->'metadata'->>'project_id' = ${param_idx}"
        params.append(ctx.project_id)
        param_idx += 1
        
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
        {project_filter}
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
@@ -583,251 +578,247 @@ async def search_memory_handler(
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
async def save_memory_route(
    req: Dict[str, Any],
    request: Request,
) -> Dict[str, Any]:
    """REST endpoint for saving memory."""
    substrate_service = get_substrate_service(request)
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
        substrate_service=substrate_service,
    )
    raise HTTPException(status_code=410, detail="Legacy REST memory routes disabled")


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
    raise HTTPException(status_code=410, detail="Legacy REST memory routes disabled")


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
        ctx = require_governance_context("mcp_memory.get_memory_stats")
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
            AND scope = ANY(${param_idx})
            AND envelope->'metadata'->>'project_id' = ${param_idx + 1}
            """
            r = await fetch_one(query, *params)
            r = await fetch_one(query, *params, ctx.allowed_scopes, ctx.project_id)
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
            AND scope = ANY(${param_idx})
            AND envelope->'metadata'->>'project_id' = ${param_idx + 1}
            """
            r = await fetch_one(query, *params)
            r = await fetch_one(query, *params, ctx.allowed_scopes, ctx.project_id)
            medium_count = r["cnt"] if r else 0
        
        if duration in ["all", "long"]:
            # Count unique callers (L or C), not user_id (which is shared as l9-shared)
            query = f"""
            SELECT 
                COUNT(*) as cnt,
                COUNT(DISTINCT envelope->'metadata'->>'caller') as users,
                AVG(importance_score) as avg_imp
            FROM packet_store
            WHERE packet_type LIKE 'memory_write_%'
            AND (ttl IS NULL OR ttl > CURRENT_TIMESTAMP + INTERVAL '7 days')
            {user_filter}
            AND scope = ANY(${param_idx})
            AND envelope->'metadata'->>'project_id' = ${param_idx + 1}
            """
            r = await fetch_one(query, *params)
            r = await fetch_one(query, *params, ctx.allowed_scopes, ctx.project_id)
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
        ctx = require_governance_context("mcp_memory.delete_expired_memories")
        # Count expired packets
        count_query = """
        SELECT COUNT(*) as cnt
        FROM packet_store
        WHERE packet_type LIKE 'memory_write_%'
        AND ttl IS NOT NULL
        AND ttl < CURRENT_TIMESTAMP
        AND scope = ANY($1)
        AND envelope->'metadata'->>'project_id' = $2
        """
        count_r = await fetch_one(count_query)
        count_r = await fetch_one(count_query, ctx.allowed_scopes, ctx.project_id)
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
                AND scope = ANY($1)
                AND envelope->'metadata'->>'project_id' = $2
                """,
                ctx.allowed_scopes,
                ctx.project_id,
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
        ctx = require_governance_context("mcp_memory.compound_similar_memories")
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
        AND ps.scope = ANY($2)
        AND ps.envelope->'metadata'->>'project_id' = $3
        ORDER BY ps.timestamp DESC
        LIMIT 1000
        """
        memories = await fetch_all(memories_query, user_id)
        memories = await fetch_all(
            memories_query, user_id, ctx.allowed_scopes, ctx.project_id
        )
        
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
@@ -852,383 +843,392 @@ async def compound_similar_memories(
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
                AND scope = ANY($6)
                AND envelope->'metadata'->>'project_id' = $7
                """,
                json.dumps(primary_envelope),
                combined_importance,
                combined_access,
                list(merged_tags),
                primary["packet_id"],
                ctx.allowed_scopes,
                ctx.project_id,
            )
            
            # Delete duplicate packets (embeddings deleted via CASCADE)
            duplicate_ids = [m["packet_id"] for m in duplicates]
            await execute(
                "DELETE FROM packet_store WHERE packet_id = ANY($1::uuid[])",
                """
                DELETE FROM packet_store
                WHERE packet_id = ANY($1::uuid[])
                AND scope = ANY($2)
                AND envelope->'metadata'->>'project_id' = $3
                """,
                duplicate_ids,
                ctx.allowed_scopes,
                ctx.project_id,
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
        ctx = require_governance_context("mcp_memory.apply_importance_decay")
        decay_factor = 1.0 - settings.DECAY_RATE_PER_DAY
        
        # Count affected packets
        count_query = """
        SELECT COUNT(*) as cnt
        FROM packet_store
        WHERE packet_type LIKE 'memory_write_%'
        AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '1 day')
        AND importance_score > 0.01
        AND scope = ANY($1)
        AND envelope->'metadata'->>'project_id' = $2
        """
        count_r = await fetch_one(count_query)
        count_r = await fetch_one(count_query, ctx.allowed_scopes, ctx.project_id)
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
                AND scope = ANY($1)
                AND envelope->'metadata'->>'project_id' = $2
                """,
                ctx.allowed_scopes,
                ctx.project_id,
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

            async with ensure_governance_context("mcp_memory.cleanup_task"):
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
    ctx = require_governance_context("mcp_memory.get_context_injection")
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["developer", "global", "l-private"]
    search_scopes = allowed_scopes if allowed_scopes else list(ctx.allowed_scopes)
    search_scopes = [s for s in search_scopes if s in ctx.allowed_scopes]
    
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
            AND ps.scope = ANY($2)
            AND ps.envelope->'metadata'->>'project_id' = $3
            AND ps.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY ps.timestamp DESC
            LIMIT 5
            """
            recent_rows = await fetch_all(recent_query, user_id)
            recent_rows = await fetch_all(
                recent_query, user_id, search_scopes, ctx.project_id
            )
            
            for row in recent_rows:
                envelope = row["envelope"]
                # Defensive: Handle case where envelope is returned as string
                if isinstance(envelope, str):
                    try:
                        envelope = json.loads(envelope)
                    except json.JSONDecodeError:
                        envelope = {}
                payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
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
    ctx = require_governance_context("mcp_memory.get_proactive_suggestions")
    
    # Default scopes if not restricted
    search_scopes = allowed_scopes if allowed_scopes else ["developer", "global", "l-private"]
    search_scopes = allowed_scopes if allowed_scopes else list(ctx.allowed_scopes)
    search_scopes = [s for s in search_scopes if s in ctx.allowed_scopes]
    
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
@@ -1263,63 +1263,66 @@ async def get_proactive_suggestions(
        
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
        ctx = require_governance_context("mcp_memory.query_temporal")
        # Parse datetime strings
        since_dt = datetime.fromisoformat(since) if since else datetime.utcnow() - timedelta(days=7)
        until_dt = datetime.fromisoformat(until) if until else datetime.utcnow()
        
        # Build WHERE clause
        where_parts = [
            "ps.packet_type LIKE 'memory_write_%'",
            "ps.envelope->>'metadata'->>'user_id' = $1",
            "ps.timestamp >= $2",
            "ps.timestamp <= $3",
            "ps.scope = ANY($4)",
            "ps.envelope->'metadata'->>'project_id' = $5",
        ]
        params = [user_id, since_dt, until_dt]
        param_idx = 4
        params = [user_id, since_dt, until_dt, ctx.allowed_scopes, ctx.project_id]
        param_idx = 6
        
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
@@ -1383,86 +1386,80 @@ async def query_temporal(
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
        require_governance_context("mcp_memory.save_memory_with_confidence")
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

memory/__init__.py
memory/__init__.py
+9
-0

@@ -80,50 +80,59 @@ from memory.retrieval import (
    RetrievalPipeline,
    get_retrieval_pipeline,
    init_retrieval_pipeline,
)

from memory.insight_extraction import (
    InsightExtractionPipeline,
    get_insight_pipeline,
    init_insight_pipeline,
)

# Audit Utilities (GMP-58: Security hardening, v2.0: PII + normalization)
from memory.audit_utils import (
    AuditReport,
    has_injection_markers,
    detect_injection_markers,
    prepare_packet_for_ingest,
    # PII detection (v2.0)
    detect_pii_types,
    redact_pii,
    # Normalization (v2.0)
    normalize_text,
    normalize_payload,
)

# Governance Gate (single enforcement layer)
from memory.governance_gate import (
    MemoryGovernanceContext,
    build_governance_context,
    ensure_governance_context,
    governance_context,
    require_governance_context,
)

# Strategy Memory (Phase 0)
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyMemoryService,
    StrategyCandidate,
    StrategyRetrievalRequest,
    StrategyFeedback,
)

# Cypher Templates (GMP-55: Parameterized queries)
from memory.cypher_templates import (
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    get_template_library,
    execute_template,
)

# Schema Introspection (GMP-55: Dynamic schema discovery)
from memory.schema_introspection import (
    SchemaIntrospector,
    PostgresIntrospector,
    Neo4jIntrospector,
    get_schema_introspector,
)
memory/governance_gate.py
memory/governance_gate.py
New
+186
-0

"""
Memory Governance Gate
======================

Single, non-bypassable governance gate for all memory operations.
Enforces:
- Authenticated caller identity (server-derived)
- Project isolation (project_id)
- Scope restrictions (including l-private protections)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Sequence
import os


@dataclass(frozen=True)
class MemoryGovernanceContext:
    """Immutable governance context for memory operations."""

    caller_id: str
    role: str
    scope: str
    project_id: str
    allowed_scopes: tuple[str, ...]
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    creator: Optional[str] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.caller_id:
            raise RuntimeError("caller_id is required for governance enforcement")
        if not self.project_id:
            raise RuntimeError("project_id is required for governance enforcement")
        if not self.allowed_scopes:
            raise RuntimeError("allowed_scopes cannot be empty")
        if self.scope not in self.allowed_scopes:
            raise RuntimeError("scope must be included in allowed_scopes")
        if self.caller_id == "C" and "l-private" in self.allowed_scopes:
            raise RuntimeError("Cursor cannot access l-private scope")


_governance_context: ContextVar[Optional[MemoryGovernanceContext]] = ContextVar(
    "memory_governance_context", default=None
)


def build_governance_context(
    *,
    caller_id: str,
    role: str,
    scope: str,
    project_id: str,
    allowed_scopes: Sequence[str],
    tenant_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    creator: Optional[str] = None,
    source: Optional[str] = None,
) -> MemoryGovernanceContext:
    """Build a validated governance context (server-derived only)."""
    return MemoryGovernanceContext(
        caller_id=caller_id,
        role=role,
        scope=scope,
        project_id=project_id,
        allowed_scopes=tuple(allowed_scopes),
        tenant_id=tenant_id,
        org_id=org_id,
        user_id=user_id,
        creator=creator,
        source=source,
    )


def set_governance_context(ctx: MemoryGovernanceContext):
    """Set governance context in the current contextvar."""
    return _governance_context.set(ctx)


def reset_governance_context(token) -> None:
    """Reset governance context."""
    _governance_context.reset(token)


def require_governance_context(operation: str) -> MemoryGovernanceContext:
    """Require an active governance context or fail closed."""
    ctx = _governance_context.get()
    if ctx is None:
        raise RuntimeError(
            f"Governance context required for memory operation: {operation}"
        )
    return ctx


def _fallback_context() -> MemoryGovernanceContext:
    caller_id = os.getenv("L9_MEMORY_CALLER_ID")
    project_id = os.getenv("L9_PROJECT_ID")
    scope = os.getenv("L9_MEMORY_SCOPE", "shared")
    if not caller_id or not project_id:
        raise RuntimeError("Fallback governance context requires L9_MEMORY_CALLER_ID and L9_PROJECT_ID")
    return build_governance_context(
        caller_id=caller_id,
        role="end_user",
        scope=scope,
        project_id=project_id,
        allowed_scopes=[scope],
    )


@asynccontextmanager
async def ensure_governance_context(
    operation: str,
) -> AsyncGenerator[MemoryGovernanceContext, None]:
    """Ensure governance context is set, with fallback to server identity."""
    ctx = _governance_context.get()
    if ctx is not None:
        yield ctx
        return
    fallback = _fallback_context()
    async with governance_context(fallback):
        yield fallback


@asynccontextmanager
async def governance_context(
    ctx: MemoryGovernanceContext,
) -> AsyncGenerator[MemoryGovernanceContext, None]:
    """Async context manager to enforce governance context."""
    token = set_governance_context(ctx)
    try:
        yield ctx
    finally:
        reset_governance_context(token)


def enforce_packet_governance(packet_in, ctx: MemoryGovernanceContext):
    """Validate/override packet metadata + payload with governance constraints."""
    metadata = dict(packet_in.metadata or {})
    payload = dict(packet_in.payload or {})

    enforced_fields = {
        "caller": ctx.caller_id,
        "project_id": ctx.project_id,
        "scope": ctx.scope,
    }
    if ctx.creator is not None:
        enforced_fields["creator"] = ctx.creator
    if ctx.source is not None:
        enforced_fields["source"] = ctx.source

    for key, value in enforced_fields.items():
        if key in metadata and metadata[key] != value:
            raise RuntimeError(
                f"Client-supplied metadata '{key}' is not allowed"
            )
        metadata[key] = value

    for key in ("scope", "project_id"):
        if key in payload and payload[key] != enforced_fields[key]:
            raise RuntimeError(f"Client-supplied payload '{key}' is not allowed")
        payload[key] = enforced_fields[key]

    return packet_in.model_copy(update={"metadata": metadata, "payload": payload})


def build_scope_project_filter(
    ctx: MemoryGovernanceContext,
    *,
    param_idx: int,
    table_alias: str = "packet_store",
    envelope_column: str = "envelope",
) -> tuple[str, list, int]:
    """Build SQL scope + project filter clause with params."""
    clause = (
        f"AND {table_alias}.scope = ANY(${param_idx}) "
        f"AND {table_alias}.{envelope_column}->'metadata'->>'project_id' = ${param_idx + 1}"
    )
    params = [list(ctx.allowed_scopes), ctx.project_id]
    return clause, params, param_idx + 2
memory/ingestion.py
memory/ingestion.py
+44
-14

@@ -8,50 +8,55 @@ Real PacketEnvelope ingestion with:
- Structured packet storage
- Vector storage
- Artifact handling
- Lineage tracking
- Tag assignment

All operations are async-safe with proper logging.
"""

from __future__ import annotations

import structlog
from functools import lru_cache
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    import asyncpg
    from memory.substrate_dag import SubstrateDAG

from core.schemas import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult
from memory.substrate_service import MemorySubstrateService
from memory.graph_client import get_neo4j_client
from memory.validators.packet_validator import PacketValidator, PacketValidationError
from memory.audit_utils import prepare_packet_for_ingest
from memory.governance_gate import (
    enforce_packet_governance,
    ensure_governance_context,
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
@@ -122,97 +127,104 @@ class IngestionPipeline:
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
        ctx = require_governance_context("ingest")
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

        # Core writes in transaction (atomic)
        # Wrap packet_store and agent_memory_events in transaction for atomicity
        if self._repository:
            try:
                async with self._repository.transaction() as conn:
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
                    
                    # Transaction commits here (or rolls back on exception)
            except Exception as e:
                logger.error(f"Transaction failed for core writes: {e}")
                errors.append(f"transaction: {str(e)}")
                # Transaction auto-rolls back on exception
        else:
            # Fallback if repository not available (should not happen)
            logger.warning("Repository not available for transactional writes")
            errors.append("repository: not available")

        # Generate and store embedding
        if should_embed and self._semantic_service:
            try:
                embedded = await self._embed_content(envelope)
                if embedded:
                    written_tables.append("semantic_memory")
            except Exception as e:
@@ -707,38 +719,56 @@ async def ingest_packet(
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
    async with ensure_governance_context("ingest_packet"):
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

        result = await pipeline.ingest(packet_in)

        if result.status in {"ok", "partial"} and packet_in.packet_type != "audit_memory_write":
            from core.compliance.audit_log import AuditLogger

            audit_logger = AuditLogger(service)
            logged = await audit_logger.log_memory_write(
                agent_id=(packet_in.metadata or {}).get("agent", "unknown"),
                segment=packet_in.packet_type or "unknown",
                content_type=packet_in.packet_type or "unknown",
                size_bytes=len(str(packet_in.payload or "")),
                packet_type=packet_in.packet_type,
                thread_id=str(packet_in.thread_id) if packet_in.thread_id else None,
            )
            if not logged:
                raise RuntimeError("Memory write audit logging failed")

        return result
memory/retrieval.py
memory/retrieval.py
+102
-58

@@ -8,50 +8,55 @@ Hybrid and structured search features:
- Reciprocal rank fusion (multi-source ranking)
- Temporal decay (recency weighting)
- Thread reconstruction
- Lineage traversal
- Fact/insight retrieval
- Replay chain reconstruction

All operations are async-safe with proper logging.

Changelog:
- v1.2.0: Added reciprocal_rank_fusion, apply_temporal_decay
- v1.1.0: Initial hybrid search
"""

from __future__ import annotations

import math
import structlog
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

from core.schemas import SemanticHit, SemanticSearchResult
from memory.substrate_models import KnowledgeFactRow, PacketStoreRow
from memory.governance_gate import (
    build_scope_project_filter,
    ensure_governance_context,
    require_governance_context,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Ranking Utilities
# =============================================================================


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> dict[str, float]:
    """
    Combine multiple rankings using Reciprocal Rank Fusion (RRF).
    
    RRF is effective for combining results from different retrieval systems
    (e.g., semantic search + keyword search + graph traversal).
    
    Formula: RRF(d) = Σ 1 / (k + rank(d))
    
    Args:
        rankings: List of rankings, each is a list of item IDs in ranked order
        k: Constant to prevent high ranks from dominating (default 60)
        
@@ -326,269 +331,303 @@ class RetrievalPipeline:

    async def fetch_thread(
        self,
        thread_id: UUID,
        limit: int = 100,
        order: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Reconstruct a conversation thread.

        Fetches all packets belonging to a thread in chronological order.

        Args:
            thread_id: Thread UUID
            limit: Maximum packets to return
            order: "asc" (oldest first) or "desc" (newest first)

        Returns:
            List of packets in thread order
        """
        logger.debug(f"Fetching thread: {thread_id}")

        if self._repository is None:
            return []

        ctx = require_governance_context("retrieval.fetch_thread")
        async with self._repository.acquire() as conn:
            order_clause = "ASC" if order == "asc" else "DESC"
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )

            rows = await conn.fetch(
                f"""
                SELECT * FROM packet_store
                WHERE thread_id = $1
                {filter_clause}
                ORDER BY timestamp {order_clause}
                LIMIT $2
                """,
                thread_id,
                limit,
                *params,
            )

            return [
                {
                    "packet_id": str(r["packet_id"]),
                    "packet_type": r["packet_type"],
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                    "envelope": r["envelope"],
                    "tags": r.get("tags", []),
                }
                for r in rows
            ]

    # =========================================================================
    # Lineage Traversal
    # =========================================================================

    async def fetch_lineage(
        self,
        packet_id: UUID,
        direction: str = "ancestors",
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Traverse packet lineage graph.

        Args:
            packet_id: Starting packet UUID
            direction: "ancestors" (parents) or "descendants" (children)
            max_depth: Maximum traversal depth

        Returns:
            Dict with lineage chain and graph structure
        """
        logger.debug(f"Fetching lineage: {packet_id}, direction={direction}")

        if self._repository is None:
            return {"packet_id": str(packet_id), "chain": [], "depth": 0}

        ctx = require_governance_context("retrieval.fetch_lineage")
        chain = []
        visited = set()
        queue = [(packet_id, 0)]

        while queue and len(chain) < 100:
            current_id, depth = queue.pop(0)

            if depth > max_depth or current_id in visited:
                continue

            visited.add(current_id)

            packet = await self._repository.get_packet(current_id)
            if packet is None:
                continue

            chain.append(
                {
                    "packet_id": str(current_id),
                    "packet_type": packet.packet_type,
                    "timestamp": packet.timestamp.isoformat()
                    if packet.timestamp
                    else None,
                    "depth": depth,
                }
            )

            if direction == "ancestors":
                # Traverse up to parents
                parent_ids = packet.parent_ids or []
                for pid in parent_ids:
                    queue.append((pid, depth + 1))
            else:
                # Traverse down to children
                async with self._repository.acquire() as conn:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=2, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        """
                        f"""
                        SELECT packet_id FROM packet_store
                        WHERE $1 = ANY(parent_ids)
                        {filter_clause}
                        """,
                        current_id,
                        *params,
                    )
                    for r in rows:
                        queue.append((r["packet_id"], depth + 1))

        return {
            "packet_id": str(packet_id),
            "direction": direction,
            "chain": chain,
            "depth": max(c["depth"] for c in chain) if chain else 0,
        }

    # =========================================================================
    # Knowledge Facts & Insights
    # =========================================================================

    async def fetch_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        source_packet: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch knowledge facts from the substrate.

        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            source_packet: Filter by source packet
            limit: Maximum facts to return

        Returns:
            List of knowledge facts
        """
        logger.debug(f"Fetching facts: subject={subject}, predicate={predicate}")

        if self._repository is None:
            return []

        if source_packet:
            facts = await self._repository.get_facts_by_packet(source_packet, limit)
        elif subject:
            facts = await self._repository.get_facts_by_subject(
                subject, predicate, limit
            )
        else:
            ctx = require_governance_context("retrieval.fetch_facts")
            # Fetch recent facts
            async with self._repository.acquire() as conn:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM knowledge_facts
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                    *params,
                )
                facts = [
                    KnowledgeFactRow(
                        fact_id=r["fact_id"],
                        subject=r["subject"],
                        predicate=r["predicate"],
                        object=r["object"],
                        confidence=r["confidence"],
                        source_packet=r["source_packet"],
                        created_at=r["created_at"],
                    )
                    for r in rows
                ]

        return [f.model_dump(mode="json") for f in facts]

    async def fetch_insights(
        self,
        packet_id: Optional[UUID] = None,
        insight_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch extracted insights from the substrate.

        Args:
            packet_id: Filter by source packet
            insight_type: Filter by insight type
            limit: Maximum insights to return

        Returns:
            List of insights (stored as insight-type packets)
        """
        logger.debug(f"Fetching insights: packet_id={packet_id}, type={insight_type}")

        if self._repository is None:
            return []

        ctx = require_governance_context("retrieval.fetch_insights")
        async with self._repository.acquire() as conn:
            filter_clause, params, param_idx = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            if packet_id:
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    AND envelope->>'source_packet' = $1
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    str(packet_id),
                    limit,
                    *params,
                )
            elif insight_type:
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    AND envelope->'payload'->>'insight_type' = $1
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    insight_type,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $1
                    """,
                    limit,
                    *params,
                )

        return [
            {
                "packet_id": str(r["packet_id"]),
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                "envelope": r["envelope"],
            }
            for r in rows
        ]

    # =========================================================================
    # Replay Chain
    # =========================================================================

    async def replay_chain(
        self,
        start_packet_id: UUID,
        end_packet_id: Optional[UUID] = None,
        include_reasoning: bool = True,
    ) -> dict[str, Any]:
        """
        Reconstruct the event/action chain between two packets.

        Useful for debugging and understanding agent decision paths.
@@ -674,81 +713,86 @@ async def get_governance_patterns(
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve governance patterns for adaptive prompting.

    Searches the governance_patterns segment for patterns matching
    the specified criteria, enabling L to learn from past decisions.

    Args:
        tool_name: Filter by tool name (e.g., "gmprun", "git_commit")
        task_type: Filter by task type (e.g., "infrastructure_change")
        decision: Filter by decision ("approved" or "rejected")
        limit: Maximum number of patterns to return

    Returns:
        List of governance pattern dicts sorted by relevance/recency
    """

    pipeline = get_retrieval_pipeline()

    if pipeline._repository is None:
        logger.warning("Retrieval pipeline not initialized, cannot get patterns")
        return []

    try:
        # Query governance_pattern packets
        async with pipeline._repository.acquire() as conn:
            # Build query with filters
            # Note: packet_store uses packet_id (not id), envelope (not payload), timestamp (not created_at)
            query = """
                SELECT packet_id, packet_type, envelope, provenance, timestamp
                FROM packet_store
                WHERE packet_type = 'governance_pattern'
            """
            params = []
            param_idx = 1

            if tool_name:
                query += f" AND envelope->'payload'->>'tool_name' = ${param_idx}"
                params.append(tool_name)
                param_idx += 1

            if task_type:
                query += f" AND envelope->'payload'->>'task_type' = ${param_idx}"
                params.append(task_type)
                param_idx += 1

            if decision:
                query += f" AND envelope->'payload'->>'decision' = ${param_idx}"
                params.append(decision)
                param_idx += 1

            query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
            params.append(limit)

            rows = await conn.fetch(query, *params)

            patterns = []
            for row in rows:
                try:
                    envelope = row["envelope"]
                    if isinstance(envelope, str):
                        import json

                        envelope = json.loads(envelope)
                    # Extract payload from envelope
                    payload = envelope.get("payload", envelope)
                    patterns.append(payload)
                except Exception as e:
                    logger.warning(f"Failed to parse pattern: {e}")

            logger.info(
                f"Retrieved {len(patterns)} governance patterns",
                tool_name=tool_name,
                task_type=task_type,
            )
            return patterns
        async with ensure_governance_context("retrieval.get_governance_patterns") as ctx:
            # Query governance_pattern packets
            async with pipeline._repository.acquire() as conn:
                # Build query with filters
                # Note: packet_store uses packet_id (not id), envelope (not payload), timestamp (not created_at)
                query = """
                    SELECT packet_id, packet_type, envelope, provenance, timestamp
                    FROM packet_store
                    WHERE packet_type = 'governance_pattern'
                """
                params = []
                filter_clause, filter_params, param_idx = build_scope_project_filter(
                    ctx, param_idx=1, table_alias="packet_store"
                )
                params.extend(filter_params)
                query += f" {filter_clause}"

                if tool_name:
                    query += f" AND envelope->'payload'->>'tool_name' = ${param_idx}"
                    params.append(tool_name)
                    param_idx += 1

                if task_type:
                    query += f" AND envelope->'payload'->>'task_type' = ${param_idx}"
                    params.append(task_type)
                    param_idx += 1

                if decision:
                    query += f" AND envelope->'payload'->>'decision' = ${param_idx}"
                    params.append(decision)
                    param_idx += 1

                query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
                params.append(limit)

                rows = await conn.fetch(query, *params)

                patterns = []
                for row in rows:
                    try:
                        envelope = row["envelope"]
                        if isinstance(envelope, str):
                            import json

                            envelope = json.loads(envelope)
                        # Extract payload from envelope
                        payload = envelope.get("payload", envelope)
                        patterns.append(payload)
                    except Exception as e:
                        logger.warning(f"Failed to parse pattern: {e}")

                logger.info(
                    f"Retrieved {len(patterns)} governance patterns",
                    tool_name=tool_name,
                    task_type=task_type,
                )
                return patterns

    except Exception as e:
        logger.error(f"Failed to retrieve governance patterns: {e}")
        return []
memory/substrate_repository.py
memory/substrate_repository.py
+232
-47

@@ -16,50 +16,54 @@ from uuid import UUID, uuid4

import asyncpg


async def _init_json_codecs(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )

# Context variable for RLS-scoped connection (used within transactions)
_current_rls_connection: ContextVar[Optional[asyncpg.Connection]] = ContextVar(
    "_current_rls_connection", default=None
)

from core.schemas import PacketEnvelope, SemanticHit
from memory.governance_gate import (
    build_scope_project_filter,
    require_governance_context,
)
from memory.substrate_models import (
    AgentMemoryEventRow,
    GraphCheckpointRow,
    KnowledgeFactRow,
    PacketStoreRow,
    ReasoningTraceRow,
    StructuredReasoningBlock,
)

logger = structlog.get_logger(__name__)


class SubstrateRepository:
    """
    Repository for memory substrate database operations.

    Uses asyncpg for async Postgres access with pgvector support.
    """

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10):
        """
        Initialize repository with database URL.

        Args:
            database_url: Postgres DSN (postgresql://user:pass@host:port/db)
@@ -72,131 +76,142 @@ class SubstrateRepository:
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=self._pool_size,
                max_size=self._pool_size + self._max_overflow,
                init=_init_json_codecs,  # Register JSON codecs for JSONB columns
            )
            logger.info("Database connection pool initialized with JSON codecs")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        require_governance_context("repository.acquire")
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(
        self,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Acquire a connection and start a transaction with RLS scope.
        
        Sets RLS session variables using SET LOCAL within the transaction,
        so the scope persists for all operations in the transaction.
        
        The connection is stored in a context variable so repository methods
        can use it instead of acquiring a new connection.
        
        Args:
            tenant_id: Optional tenant UUID for RLS isolation
            org_id: Optional organization UUID for RLS isolation
            user_id: Optional user UUID for RLS isolation
            role: User role for RLS policy enforcement
            
        Yields:
            Connection within a transaction with RLS scope set
        """
        if self._pool is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        ctx = require_governance_context("repository.transaction")
        if tenant_id and tenant_id != ctx.tenant_id:
            raise RuntimeError("tenant_id must be derived server-side")
        if org_id and org_id != ctx.org_id:
            raise RuntimeError("org_id must be derived server-side")
        if user_id and user_id != ctx.user_id:
            raise RuntimeError("user_id must be derived server-side")
        if role != ctx.role:
            raise RuntimeError("role must be derived server-side")
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Set RLS scope within transaction (SET LOCAL makes it transaction-scoped)
                if tenant_id and org_id and user_id:
                if ctx.tenant_id and ctx.org_id and ctx.user_id:
                    await conn.execute(
                        """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                        tenant_id,
                        org_id,
                        user_id,
                        role,
                        ctx.tenant_id,
                        ctx.org_id,
                        ctx.user_id,
                        ctx.role,
                    )
                
                # Store connection in context variable for repository methods to use
                token = _current_rls_connection.set(conn)
                try:
                    yield conn
                finally:
                    # Restore previous context (or clear if None)
                    _current_rls_connection.reset(token)

    # =========================================================================
    # Packet Store Operations
    # =========================================================================

    async def insert_packet(self, envelope: PacketEnvelope) -> UUID:
        """
        Insert a PacketEnvelope into packet_store.

        Returns:
            The packet_id of the inserted record.
        """
        # Extract fields from envelope for dedicated columns (v2.0 support)
        thread_id = envelope.thread_id
        tags = envelope.tags if envelope.tags else []
        ttl = envelope.ttl
        # Extract parent_ids from lineage (DAG support)
        parent_ids = envelope.lineage.parent_ids if envelope.lineage else []
        # Extra fields may be in metadata dict (extra="allow" in PacketMetadata)
        metadata_dict = envelope.metadata.model_dump() if envelope.metadata else {}
        content_hash = metadata_dict.get("content_hash")
        session_id = metadata_dict.get("session_id")
        scope = metadata_dict.get("scope", "shared")
        trace_id = metadata_dict.get("trace_id")
        # importance_score: prefer metadata, fallback to confidence.score
        importance_score = metadata_dict.get("importance")
        if importance_score is None and envelope.confidence:
            importance_score = envelope.confidence.score
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_packet")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            conn = rls_conn
            # Execute directly without context manager
            await self._insert_packet_with_connection(conn, envelope, thread_id, tags, ttl, parent_ids, metadata_dict, content_hash, session_id, scope, trace_id, importance_score)
            return envelope.packet_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._insert_packet_with_connection(conn, envelope, thread_id, tags, ttl, parent_ids, metadata_dict, content_hash, session_id, scope, trace_id, importance_score)
                return envelope.packet_id
    
    async def _insert_packet_with_connection(
        self,
        conn: asyncpg.Connection,
        envelope: PacketEnvelope,
        thread_id,
        tags,
        ttl,
        parent_ids,
        metadata_dict,
        content_hash,
        session_id,
        scope,
@@ -229,144 +244,167 @@ class SubstrateRepository:
            envelope.packet_type,
            json.dumps(envelope.model_dump(mode="json")),
            envelope.timestamp,
            json.dumps(
                {"agent": envelope.metadata.agent if envelope.metadata else None}
            ),
            json.dumps(
                envelope.provenance.model_dump(mode="json")
                if envelope.provenance
                else None
            ),
            thread_id,
            parent_ids,
            tags,
            ttl,
            content_hash,
            session_id,
            scope,
            trace_id,
            importance_score,
        )
        logger.debug(f"Inserted packet {envelope.packet_id} with thread_id={thread_id}, parent_ids={parent_ids}, importance={importance_score}")

    async def get_packet(self, packet_id: UUID) -> Optional[PacketStoreRow]:
        """Retrieve a packet by ID."""
        ctx = require_governance_context("repository.get_packet")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=2, table_alias="packet_store"
            )
            row = await conn.fetchrow(
                "SELECT * FROM packet_store WHERE packet_id = $1", packet_id
                f"SELECT * FROM packet_store WHERE packet_id = $1 {filter_clause}",
                packet_id,
                *params,
            )
            if row:
                return self._row_to_packet_store(row)
            return None

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PacketStoreRow]:
        """
        Search for packets by thread ID.

        Args:
            thread_id: Thread UUID to search for
            packet_type: Optional filter by packet type
            limit: Maximum packets to return
            offset: Offset for pagination

        Returns:
            List of PacketStoreRow sorted by timestamp ascending
        """
        ctx = require_governance_context("repository.search_packets_by_thread")
        async with self.acquire() as conn:
            if packet_type:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=5, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1 AND packet_type = $2
                    {filter_clause}
                    ORDER BY timestamp ASC
                    LIMIT $3 OFFSET $4
                    """,
                    thread_id,
                    packet_type,
                    limit,
                    offset,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1
                    {filter_clause}
                    ORDER BY timestamp ASC
                    LIMIT $2 OFFSET $3
                    """,
                    thread_id,
                    limit,
                    offset,
                    *params,
                )
            return [self._row_to_packet_store(r) for r in rows]

    async def search_packets_by_type(
        self,
        packet_type: str,
        agent_id: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[PacketStoreRow]:
        """
        Search for packets by type.

        Args:
            packet_type: Packet type to search for
            agent_id: Optional filter by agent
            limit: Maximum packets to return
            since: Optional filter by timestamp

        Returns:
            List of PacketStoreRow sorted by timestamp descending
        """
        ctx = require_governance_context("repository.search_packets_by_type")
        async with self.acquire() as conn:
            conditions = ["packet_type = $1"]
            params: list[Any] = [packet_type]
            param_idx = 2

            if agent_id:
                conditions.append(f"routing->>'agent' = ${param_idx}")
                params.append(agent_id)
                param_idx += 1

            if since:
                conditions.append(f"timestamp > ${param_idx}")
                params.append(since)
                param_idx += 1

            filter_clause, filter_params, param_idx = build_scope_project_filter(
                ctx, param_idx=param_idx, table_alias="packet_store"
            )
            params.extend(filter_params)
            params.append(limit)

            query = f"""
                SELECT * FROM packet_store 
                WHERE {" AND ".join(conditions)}
                {filter_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
            """

            rows = await conn.fetch(query, *params)
            return [self._row_to_packet_store(r) for r in rows]

    def _row_to_packet_store(self, row: Any) -> PacketStoreRow:
        """Convert a database row to PacketStoreRow (all 22 columns from migrations 0001, 0002, 0008)."""
        return PacketStoreRow(
            # Core fields (migration 0001)
            packet_id=row["packet_id"],
            packet_type=row["packet_type"],
            envelope=json.loads(row["envelope"])
            if isinstance(row["envelope"], str)
            else row["envelope"],
            timestamp=row["timestamp"],
            routing=json.loads(row["routing"])
            if row["routing"] and isinstance(row["routing"], str)
            else row["routing"],
            provenance=json.loads(row["provenance"])
            if row["provenance"] and isinstance(row["provenance"], str)
            else row["provenance"],
            # Threading & lineage (migration 0002)
            thread_id=row.get("thread_id"),
@@ -388,201 +426,252 @@ class SubstrateRepository:
            tenant_id=row.get("tenant_id"),
            org_id=row.get("org_id"),
            user_id=row.get("user_id"),
            correlation_id=row.get("correlation_id"),
            # Tracing (migration 0008)
            session_id=row.get("session_id"),
            trace_id=row.get("trace_id"),
        )

    # =========================================================================
    # Agent Memory Events Operations
    # =========================================================================

    async def insert_memory_event(
        self,
        agent_id: str,
        event_type: str,
        content: dict[str, Any],
        packet_id: Optional[UUID] = None,
        timestamp: Optional[datetime] = None,
    ) -> UUID:
        """Insert a memory event."""
        event_id = uuid4()
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_memory_event")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await rls_conn.execute(
                """
                INSERT INTO agent_memory_events (event_id, agent_id, timestamp, packet_id, event_type, content)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                event_id,
                agent_id,
                timestamp or datetime.utcnow(),
                packet_id,
                event_type,
                json.dumps(content),
            )
            logger.debug(f"Inserted memory event {event_id} for agent {agent_id}")
            return event_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_memory_events (event_id, agent_id, timestamp, packet_id, event_type, content)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    event_id,
                    agent_id,
                    timestamp or datetime.utcnow(),
                    packet_id,
                    event_type,
                    json.dumps(content),
                )
                logger.debug(f"Inserted memory event {event_id} for agent {agent_id}")
                return event_id

    async def get_memory_events(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AgentMemoryEventRow]:
        """Retrieve memory events for an agent."""
        ctx = require_governance_context("repository.get_memory_events")
        async with self.acquire() as conn:
            if event_type:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM agent_memory_events 
                    WHERE agent_id = $1 AND event_type = $2
                    f"""
                    SELECT ame.*
                    FROM agent_memory_events ame
                    LEFT JOIN packet_store ON packet_store.packet_id = ame.packet_id
                    WHERE ame.agent_id = $1 AND ame.event_type = $2
                    {filter_clause}
                    ORDER BY timestamp DESC LIMIT $3
                    """,
                    agent_id,
                    event_type,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM agent_memory_events 
                    WHERE agent_id = $1
                    f"""
                    SELECT ame.*
                    FROM agent_memory_events ame
                    LEFT JOIN packet_store ON packet_store.packet_id = ame.packet_id
                    WHERE ame.agent_id = $1
                    {filter_clause}
                    ORDER BY timestamp DESC LIMIT $2
                    """,
                    agent_id,
                    limit,
                    *params,
                )
            return [
                AgentMemoryEventRow(
                    event_id=r["event_id"],
                    agent_id=r["agent_id"],
                    timestamp=r["timestamp"],
                    packet_id=r["packet_id"],
                    event_type=r["event_type"],
                    content=json.loads(r["content"])
                    if isinstance(r["content"], str)
                    else r["content"],
                )
                for r in rows
            ]

    # =========================================================================
    # Reasoning Traces Operations
    # =========================================================================

    async def insert_reasoning_block(self, block: StructuredReasoningBlock) -> UUID:
        """Insert a reasoning block into reasoning_traces."""
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_reasoning_block")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._insert_reasoning_block_with_connection(rls_conn, block)
            return block.block_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._insert_reasoning_block_with_connection(conn, block)
                return block.block_id
    
    async def _insert_reasoning_block_with_connection(
        self, conn: asyncpg.Connection, block: StructuredReasoningBlock
    ) -> None:
        """Helper method to insert reasoning block using provided connection."""
        # Extract agent_id from block metadata or use default
        agent_id = "unknown"
        if hasattr(block, "agent_id"):
            agent_id = block.agent_id

        await conn.execute(
            """
            INSERT INTO reasoning_traces (
                trace_id, agent_id, packet_id, steps, extracted_features,
                inference_steps, reasoning_tokens, decision_tokens, 
                confidence_scores, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            block.block_id,
            agent_id,
            block.packet_id,
            json.dumps({"steps": block.inference_steps}),
            json.dumps(block.extracted_features),
            json.dumps(block.inference_steps),
            json.dumps(block.reasoning_tokens),
            json.dumps(block.decision_tokens),
            json.dumps(block.confidence_scores),
            block.timestamp,
        )
        logger.debug(f"Inserted reasoning block {block.block_id}")

    async def get_reasoning_traces(
        self,
        agent_id: Optional[str] = None,
        packet_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[ReasoningTraceRow]:
        """Retrieve reasoning traces with optional filters."""
        ctx = require_governance_context("repository.get_reasoning_traces")
        async with self.acquire() as conn:
            if packet_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces WHERE packet_id = $1 ORDER BY created_at DESC LIMIT $2",
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE rt.packet_id = $1
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $2
                    """,
                    packet_id,
                    limit,
                    *params,
                )
            elif agent_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE rt.agent_id = $1
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $2
                    """,
                    agent_id,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces ORDER BY created_at DESC LIMIT $1",
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $1
                    """,
                    limit,
                    *params,
                )
            return [
                ReasoningTraceRow(
                    trace_id=r["trace_id"],
                    agent_id=r["agent_id"],
                    packet_id=r["packet_id"],
                    steps=json.loads(r["steps"])
                    if r["steps"] and isinstance(r["steps"], str)
                    else r["steps"],
                    extracted_features=json.loads(r["extracted_features"])
                    if r["extracted_features"]
                    and isinstance(r["extracted_features"], str)
                    else r["extracted_features"],
                    inference_steps=json.loads(r["inference_steps"])
                    if r["inference_steps"] and isinstance(r["inference_steps"], str)
                    else r["inference_steps"],
                    reasoning_tokens=json.loads(r["reasoning_tokens"])
                    if r["reasoning_tokens"] and isinstance(r["reasoning_tokens"], str)
                    else r["reasoning_tokens"],
                    decision_tokens=json.loads(r["decision_tokens"])
                    if r["decision_tokens"] and isinstance(r["decision_tokens"], str)
                    else r["decision_tokens"],
                    confidence_scores=json.loads(r["confidence_scores"])
                    if r["confidence_scores"]
                    and isinstance(r["confidence_scores"], str)
@@ -612,50 +701,51 @@ class SubstrateRepository:
        to prevent duplicate facts from same packet. This ensures:
        - Same packet enriched twice = no duplicates
        - Fact updates are atomic
        
        Args:
            fact_id: UUID for the fact (used for insert)
            subject: Entity or concept being described
            predicate: Relationship or attribute type
            object_value: Value, entity, or structured data
            confidence: Extraction confidence (0.0-1.0)
            source_packet: Source packet ID (foreign key)
            
        Returns:
            KnowledgeFactRow with assigned/existing fact_id
            
        Raises:
            Exception: DB error (caller decides whether to propagate or log)
        """
        created_at = datetime.utcnow()
        
        # Serialize object_value to JSON (always required for JSONB column)
        # Even strings must be JSON-encoded (wrapped in quotes) for PostgreSQL
        object_json = json.dumps(object_value)
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_knowledge_fact")
        rls_conn = _current_rls_connection.get()
        
        if rls_conn:
            row = await self._insert_knowledge_fact_with_connection(
                rls_conn, fact_id, subject, predicate, object_json,
                confidence, source_packet, created_at
            )
        else:
            async with self.acquire() as conn:
                row = await self._insert_knowledge_fact_with_connection(
                    conn, fact_id, subject, predicate, object_json,
                    confidence, source_packet, created_at
                )
        
        return row

    async def _insert_knowledge_fact_with_connection(
        self,
        conn: asyncpg.Connection,
        fact_id: UUID,
        subject: str,
        predicate: str,
        object_json: str,
        confidence: float,
        source_packet: Optional[UUID],
@@ -695,214 +785,239 @@ class SubstrateRepository:
            subject=row["subject"],
            predicate=row["predicate"],
            object=json.loads(row["object"]) if isinstance(row["object"], str) else row["object"],
            confidence=row["confidence"],
            source_packet=row["source_packet"],
            created_at=row["created_at"],
        )

    async def get_knowledge_facts(
        self,
        source_packet: Optional[UUID] = None,
        subject: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts with optional filters.
        
        Args:
            source_packet: Filter by source packet ID
            subject: Filter by subject (exact match)
            limit: Maximum results to return
            
        Returns:
            List of KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_knowledge_facts")
        async with self.acquire() as conn:
            conditions = ["deprecated = FALSE OR deprecated IS NULL"]
            params: list[Any] = []
            param_idx = 1
            
            if source_packet:
                conditions.append(f"source_packet = ${param_idx}")
                params.append(source_packet)
                param_idx += 1
            
            if subject:
                conditions.append(f"subject = ${param_idx}")
                params.append(subject)
                param_idx += 1
            
            filter_clause, filter_params, param_idx = build_scope_project_filter(
                ctx, param_idx=param_idx, table_alias="packet_store"
            )
            params.extend(filter_params)
            params.append(limit)
            

            query = f"""
                SELECT * FROM knowledge_facts
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE {" AND ".join(conditions)}
                {filter_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
            """
            
            rows = await conn.fetch(query, *params)
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"]) if isinstance(r["object"], str) else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # =========================================================================
    # Semantic Memory Operations (pgvector)
    # =========================================================================

    async def insert_semantic_embedding(
        self,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> UUID:
        """
        Insert a semantic embedding into semantic_memory.

        Args:
            vector: Embedding vector (1536 dimensions for text-embedding-3-large)
            payload: JSON payload associated with this embedding
            agent_id: Optional agent identifier

        Returns:
            embedding_id of the inserted record
        """
        embedding_id = uuid4()
        require_governance_context("repository.insert_semantic_embedding")
        async with self.acquire() as conn:
            # pgvector expects vector as string format '[x,y,z,...]'
            vector_str = f"[{','.join(str(v) for v in vector)}]"
            await conn.execute(
                """
                INSERT INTO semantic_memory (embedding_id, agent_id, vector, payload, created_at)
                VALUES ($1, $2, $3::vector, $4, $5)
                """,
                embedding_id,
                agent_id,
                vector_str,
                json.dumps(payload),
                datetime.utcnow(),
            )
            logger.debug(f"Inserted semantic embedding {embedding_id}")
            return embedding_id

    async def search_semantic_memory(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[SemanticHit]:
        """
        Search semantic memory using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            agent_id: Optional filter by agent

        Returns:
            List of SemanticHit with embedding_id, score, payload
        """
        ctx = require_governance_context("repository.search_semantic_memory")
        async with self.acquire() as conn:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            if agent_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT 
                        embedding_id, 
                        payload,
                        1 - (vector <=> $1::vector) as score
                    FROM semantic_memory
                    WHERE agent_id = $2
                    ORDER BY vector <=> $1::vector
                        sm.embedding_id, 
                        sm.payload,
                        1 - (sm.vector <=> $1::vector) as score
                    FROM semantic_memory sm
                    INNER JOIN packet_store ON packet_store.packet_id = (sm.payload->>'packet_id')::uuid
                    WHERE sm.agent_id = $2
                    {filter_clause}
                    ORDER BY sm.vector <=> $1::vector
                    LIMIT $3
                    """,
                    vector_str,
                    agent_id,
                    top_k,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    f"""
                    SELECT 
                        embedding_id, 
                        payload,
                        1 - (vector <=> $1::vector) as score
                    FROM semantic_memory
                    ORDER BY vector <=> $1::vector
                        sm.embedding_id, 
                        sm.payload,
                        1 - (sm.vector <=> $1::vector) as score
                    FROM semantic_memory sm
                    INNER JOIN packet_store ON packet_store.packet_id = (sm.payload->>'packet_id')::uuid
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY sm.vector <=> $1::vector
                    LIMIT $2
                    """,
                    vector_str,
                    top_k,
                    *params,
                )

            return [
                SemanticHit(
                    embedding_id=r["embedding_id"],
                    score=float(r["score"]),
                    payload=json.loads(r["payload"])
                    if isinstance(r["payload"], str)
                    else r["payload"],
                )
                for r in rows
            ]

    # =========================================================================
    # Graph Checkpoint Operations
    # =========================================================================

    async def save_checkpoint(
        self,
        agent_id: str,
        graph_state: dict[str, Any],
        reason: str = "manual",
    ) -> UUID:
        """
        Save a graph checkpoint.

        After migration 0014, supports multi-checkpoint per agent.
        Falls back to upsert if 'reason' column doesn't exist (pre-0014 schema).

        Args:
            agent_id: Agent identifier
            graph_state: State dict to persist
            reason: Checkpoint trigger reason

        Returns:
            Checkpoint UUID
        """
        checkpoint_id = uuid4()
        ctx = require_governance_context("repository.save_checkpoint")
        graph_state = {**graph_state, "project_id": ctx.project_id}
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._save_checkpoint_with_connection(rls_conn, checkpoint_id, agent_id, graph_state, reason)
            return checkpoint_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._save_checkpoint_with_connection(conn, checkpoint_id, agent_id, graph_state, reason)
                return checkpoint_id
    
    async def _save_checkpoint_with_connection(
        self,
        conn: asyncpg.Connection,
        checkpoint_id: UUID,
        agent_id: str,
        graph_state: dict[str, Any],
        reason: str,
    ) -> None:
        """Helper method to save checkpoint using provided connection."""
        # Try INSERT with reason column (post-0014 schema)
        try:
            await conn.execute(
@@ -919,442 +1034,512 @@ class SubstrateRepository:
        except Exception as e:
            # Fallback: pre-0014 schema without reason column (upsert)
            if "reason" in str(e).lower() or "column" in str(e).lower():
                logger.debug("Falling back to upsert (pre-0014 schema)")
                await conn.execute(
                    """
                    INSERT INTO graph_checkpoints (checkpoint_id, agent_id, graph_state, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (agent_id)
                    DO UPDATE SET
                        graph_state = EXCLUDED.graph_state,
                        updated_at = EXCLUDED.updated_at
                    """,
                    checkpoint_id,
                    agent_id,
                    json.dumps(graph_state),
                    datetime.utcnow(),
                )
            else:
                raise

        logger.debug(f"Saved checkpoint for agent {agent_id}", reason=reason)

    async def get_checkpoint(self, agent_id: str) -> Optional[GraphCheckpointRow]:
        """Retrieve the latest checkpoint for an agent."""
        ctx = require_governance_context("repository.get_checkpoint")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM graph_checkpoints WHERE agent_id = $1 ORDER BY updated_at DESC LIMIT 1",
                """
                SELECT * FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                ORDER BY updated_at DESC LIMIT 1
                """,
                agent_id,
                ctx.project_id,
            )
            if row:
                return GraphCheckpointRow(
                    checkpoint_id=row["checkpoint_id"],
                    agent_id=row["agent_id"],
                    graph_state=json.loads(row["graph_state"])
                    if isinstance(row["graph_state"], str)
                    else row["graph_state"],
                    updated_at=row["updated_at"],
                )
            return None

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> list[GraphCheckpointRow]:
        """
        List checkpoints for an agent.

        Supports both pre-0014 (single checkpoint) and post-0014 (multi-checkpoint) schemas.

        Args:
            agent_id: Agent identifier
            limit: Maximum checkpoints to return

        Returns:
            List of GraphCheckpointRow ordered by updated_at DESC
        """
        ctx = require_governance_context("repository.list_checkpoints")
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                ORDER BY updated_at DESC
                LIMIT $2
                LIMIT $3
                """,
                agent_id,
                ctx.project_id,
                limit,
            )
            checkpoints = []
            for row in rows:
                # Parse graph_state
                graph_state = row["graph_state"]
                if isinstance(graph_state, str):
                    graph_state = json.loads(graph_state)

                # Handle optional fields (post-0014 schema)
                reason = row.get("reason") if "reason" in row.keys() else None
                checkpoint_number = row.get("checkpoint_number") if "checkpoint_number" in row.keys() else None

                checkpoints.append(
                    GraphCheckpointRow(
                        checkpoint_id=row["checkpoint_id"],
                        agent_id=row["agent_id"],
                        graph_state=graph_state,
                        updated_at=row["updated_at"],
                        reason=reason,
                        checkpoint_number=checkpoint_number,
                    )
                )
            return checkpoints

    async def delete_checkpoint(self, agent_id: str) -> bool:
        """
        Delete all checkpoints for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if any checkpoint was deleted, False if none found
        """
        ctx = require_governance_context("repository.delete_checkpoint")
        async with self.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM graph_checkpoints WHERE agent_id = $1",
                """
                DELETE FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                """,
                agent_id,
                ctx.project_id,
            )
            deleted = result.split()[-1] != "0"
            if deleted:
                logger.debug(f"Deleted checkpoints for agent {agent_id}")
            return deleted

    async def delete_old_checkpoints(
        self,
        agent_id: str,
        keep_last: int = 10,
    ) -> int:
        """
        Delete old checkpoints, keeping the most recent N.

        For retention policy: keeps most recent checkpoints, deletes older ones.

        Args:
            agent_id: Agent identifier
            keep_last: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        ctx = require_governance_context("repository.delete_old_checkpoints")
        async with self.acquire() as conn:
            # Delete all checkpoints except the most recent keep_last
            result = await conn.execute(
                """
                DELETE FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $3
                AND checkpoint_id NOT IN (
                    SELECT checkpoint_id
                    FROM graph_checkpoints
                    WHERE agent_id = $1
                    AND graph_state->>'project_id' = $3
                    ORDER BY updated_at DESC
                    LIMIT $2
                )
                """,
                agent_id,
                keep_last,
                ctx.project_id,
            )
            # Parse "DELETE N" to get count
            deleted_count = int(result.split()[-1])
            if deleted_count > 0:
                logger.debug(
                    f"Deleted {deleted_count} old checkpoints for agent {agent_id}",
                    keep_last=keep_last,
                )
            return deleted_count

    # =========================================================================
    # Agent Log Operations
    # =========================================================================

    async def insert_log(
        self,
        agent_id: str,
        level: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """Insert a log entry."""
        log_id = uuid4()
        require_governance_context("repository.insert_log")
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_log (log_id, timestamp, agent_id, level, message, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                log_id,
                datetime.utcnow(),
                agent_id,
                level.upper(),
                message,
                json.dumps(metadata) if metadata else None,
            )
            return log_id

    async def get_facts_by_subject(
        self,
        subject: str,
        predicate: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts by subject.

        Args:
            subject: Subject to search for (empty string returns all facts)
            predicate: Optional predicate filter
            limit: Maximum facts to return

        Returns:
            List of KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_facts_by_subject")
        async with self.acquire() as conn:
            # If subject is empty, return all facts
            if not subject:
                if predicate:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=3, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        """
                        SELECT * FROM knowledge_facts 
                        f"""
                        SELECT knowledge_facts.*
                        FROM knowledge_facts
                        INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                        WHERE predicate = $1
                        {filter_clause}
                        ORDER BY created_at DESC LIMIT $2
                        """,
                        predicate,
                        limit,
                        *params,
                    )
                else:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=2, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        """
                        SELECT * FROM knowledge_facts 
                        f"""
                        SELECT knowledge_facts.*
                        FROM knowledge_facts
                        INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                        WHERE TRUE
                        {filter_clause}
                        ORDER BY created_at DESC LIMIT $1
                        """,
                        limit,
                        *params,
                    )
            elif predicate:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM knowledge_facts 
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE subject = $1 AND predicate = $2
                    {filter_clause}
                    ORDER BY created_at DESC LIMIT $3
                    """,
                    subject,
                    predicate,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM knowledge_facts 
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE subject = $1
                    {filter_clause}
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    subject,
                    limit,
                    *params,
                )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"])
                    if isinstance(r["object"], str)
                    else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def get_facts_by_packet(
        self,
        packet_id: UUID,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts by source packet.

        Args:
            packet_id: Source packet UUID
            limit: Maximum facts to return

        Returns:
            List of KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_facts_by_packet")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            rows = await conn.fetch(
                """
                SELECT * FROM knowledge_facts 
                f"""
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE source_packet = $1
                {filter_clause}
                ORDER BY created_at DESC LIMIT $2
                """,
                packet_id,
                limit,
                *params,
            )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"])
                    if isinstance(r["object"], str)
                    else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # =========================================================================
    # Spec v3.0 Required Methods - Fact Deprecation & Contradiction Tracking
    # =========================================================================

    async def deprecate_fact(
        self,
        fact_id: UUID,
        reason: str,
    ) -> bool:
        """
        Soft-deprecate a knowledge fact.

        Spec: state.contradiction_tracking.deprecate_fact

        Args:
            fact_id: UUID of fact to deprecate
            reason: Reason for deprecation

        Returns:
            True if deprecated, False if not found
        """
        require_governance_context("repository.deprecate_fact")
        async with self.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE knowledge_facts
                SET deprecated = TRUE,
                    deprecated_at = NOW(),
                    deprecated_reason = $2
                WHERE fact_id = $1 AND deprecated = FALSE
                """,
                fact_id,
                reason,
            )
            # Check if any row was updated
            return "UPDATE 1" in result

    async def increment_contradiction_count(
        self,
        fact_id: UUID,
    ) -> int:
        """
        Increment contradiction count for a fact.

        Args:
            fact_id: UUID of fact

        Returns:
            New contradiction count
        """
        require_governance_context("repository.increment_contradiction_count")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE knowledge_facts
                SET contradiction_count = contradiction_count + 1
                WHERE fact_id = $1
                RETURNING contradiction_count
                """,
                fact_id,
            )
            return row["contradiction_count"] if row else 0

    async def get_active_facts(
        self,
        subject: str,
        min_confidence: float = 0.0,
    ) -> list[KnowledgeFactRow]:
        """
        Get active (non-deprecated) facts for a subject.

        Spec: state.contradiction_tracking.get_active_facts

        Args:
            subject: Subject to get facts for
            min_confidence: Minimum confidence threshold

        Returns:
            List of active KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_active_facts")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            rows = await conn.fetch(
                """
                SELECT * FROM knowledge_facts 
                f"""
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE subject = $1 
                  AND deprecated = FALSE
                  AND confidence >= $2
                {filter_clause}
                ORDER BY confidence DESC, created_at DESC
                """,
                subject,
                min_confidence,
                *params,
            )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"])
                    if isinstance(r["object"], str)
                    else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def get_contradiction_count(
        self,
        fact_id: UUID,
    ) -> int:
        """
        Get contradiction count for a fact.

        Spec: state.contradiction_tracking.get_contradiction_count

        Args:
            fact_id: UUID of fact

        Returns:
            Contradiction count (0 if not found)
        """
        require_governance_context("repository.get_contradiction_count")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT contradiction_count FROM knowledge_facts
                WHERE fact_id = $1
                """,
                fact_id,
            )
            return row["contradiction_count"] if row else 0

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity and return status."""
        try:
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return {
                    "status": "healthy",
                    "database": "connected",
                    "pool_size": self._pool.get_size() if self._pool else 0,
                }
        except Exception as e:
memory/substrate_service.py
memory/substrate_service.py
+52
-9

@@ -17,50 +17,51 @@ from core.schemas import (
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
from memory.governance_gate import enforce_packet_governance, require_governance_context
from telemetry.memory_metrics import (
    record_memory_write,
    record_memory_search,
    set_memory_substrate_health,
    record_memory_quarantine,
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
@@ -179,106 +180,118 @@ class MemorySubstrateService:
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
        ctx = require_governance_context("write_packet")
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
            logger.error("packet_validation_failed", error=str(e), packet_type=packet_in.packet_type)
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

        # Run through DAG with RLS scope if provided
        # Use transaction with RLS scope to ensure all operations use same connection
        result: PacketWriteResult
        if tenant_id and org_id and user_id:
        if ctx.tenant_id and ctx.org_id and ctx.user_id:
            # Use transaction with RLS scope - all DAG operations will use same connection
            async with self._repository.transaction(
                tenant_id=tenant_id,
                org_id=org_id,
                user_id=user_id,
                role=role,
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
        else:
            logger.warning(
                "RLS scope not provided for write_packet - queries may be restricted"
@@ -289,135 +302,153 @@ class MemorySubstrateService:
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

        if result.status == "ok" and packet_in.packet_type != "audit_memory_write":
            from core.compliance.audit_log import AuditLogger

            audit_logger = AuditLogger(self)
            logged = await audit_logger.log_memory_write(
                agent_id=(packet_in.metadata or {}).get("agent", "unknown"),
                segment=packet_in.packet_type or "unknown",
                content_type=packet_in.packet_type or "unknown",
                size_bytes=len(str(packet_in.payload or "")),
                packet_type=packet_in.packet_type,
                thread_id=str(packet_in.thread_id) if packet_in.thread_id else None,
            )
            if not logged:
                raise RuntimeError("Memory write audit logging failed")

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
            require_governance_context("get_packet")
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
            require_governance_context("search_packets_by_thread")
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
            require_governance_context("search_packets_by_type")
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
@@ -425,53 +456,56 @@ class MemorySubstrateService:
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
            ctx = require_governance_context("query_packets")
            # Set RLS scope if provided
            if tenant_id and org_id and user_id:
                await self.set_session_scope(tenant_id, org_id, user_id, role)
            if ctx.tenant_id and ctx.org_id and ctx.user_id:
                await self.set_session_scope(
                    ctx.tenant_id, ctx.org_id, ctx.user_id, ctx.role
                )

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

@@ -501,50 +535,51 @@ class MemorySubstrateService:
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
        require_governance_context("semantic_search")
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
@@ -576,176 +611,183 @@ class MemorySubstrateService:
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
        require_governance_context("get_memory_events")
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

        require_governance_context("get_reasoning_traces")
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
        require_governance_context("get_checkpoint")
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
        require_governance_context("write_insights")
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
        ctx = require_governance_context("trigger_world_model_update")
        logger.info(f"World model update triggered with {len(insights)} insights")

        # Set RLS scope for world model operations
        if tenant_id and org_id and user_id:
            await self.set_session_scope(tenant_id, org_id, user_id, role)
        if ctx.tenant_id and ctx.org_id and ctx.user_id:
            await self.set_session_scope(
                ctx.tenant_id, ctx.org_id, ctx.user_id, ctx.role
            )

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
@@ -765,50 +807,51 @@ class MemorySubstrateService:
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
        require_governance_context("get_facts_by_subject")
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
runtime/memory_helpers.py
runtime/memory_helpers.py
+65
-40

"""
L9 Runtime - Memory Segment Helpers
====================================

Helper APIs for memory segmentation and usage rules.

Provides:
- memory_search(segment, query, agent_id)
- memory_write(segment, payload, agent_id)

Memory segments:
- governance_meta: Rules, authority, policies
- project_history: Project decisions, milestones, context
- tool_audit: Tool call logs and audit trail
- session_context: Current session state and context

Version: 1.0.0
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, List, Optional
import os

logger = structlog.get_logger(__name__)

from memory.governance_gate import build_governance_context, governance_context

# Memory segment constants
MEMORY_SEGMENT_GOVERNANCE_META = "governance_meta"
MEMORY_SEGMENT_PROJECT_HISTORY = "project_history"
MEMORY_SEGMENT_TOOL_AUDIT = "tool_audit"
MEMORY_SEGMENT_SESSION_CONTEXT = "session_context"

ALL_SEGMENTS = [
    MEMORY_SEGMENT_GOVERNANCE_META,
    MEMORY_SEGMENT_PROJECT_HISTORY,
    MEMORY_SEGMENT_TOOL_AUDIT,
    MEMORY_SEGMENT_SESSION_CONTEXT,
]


async def memory_search(
    segment: str,
    query: str,
    agent_id: str = "L",
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search memory within a specific segment.

    Args:
        segment: Memory segment name (governance_meta, project_history, tool_audit, session_context)
        query: Search query string
        agent_id: Agent identifier (default: "L")
        top_k: Number of results to return (default: 10)

    Returns:
        List of matching memory entries

    Usage:
        # Search governance rules
        results = await memory_search("governance_meta", "approval requirements", agent_id="L")

        # Search project history
        results = await memory_search("project_history", "architecture decisions", agent_id="L")
    """
    if segment not in ALL_SEGMENTS:
        logger.warning(f"Unknown memory segment: {segment}, using default search")

    try:
        from memory.substrate_service import get_service
        from core.schemas import SemanticSearchRequest

        service = get_service()
        if not service:
            logger.warning("Memory service not available")
            return []

        # Use semantic search with segment tag
        # The segment is encoded in the packet_type or tags
        request = SemanticSearchRequest(
            query=query,
            top_k=top_k,
            agent_id=agent_id,
        scope = os.getenv("L9_MEMORY_SCOPE", "shared")
        project_id = os.getenv("L9_PROJECT_ID", "l9")
        ctx = build_governance_context(
            caller_id="runtime",
            role="end_user",
            scope=scope,
            project_id=project_id,
            allowed_scopes=[scope],
        )

        result = await service.semantic_search(request)
        async with governance_context(ctx):
            service = await get_service()
            if not service:
                logger.warning("Memory service not available")
                return []

            # Use semantic search with segment tag
            # The segment is encoded in the packet_type or tags
            request = SemanticSearchRequest(
                query=query,
                top_k=top_k,
                agent_id=agent_id,
            )

            result = await service.semantic_search(request)

        # Filter by segment tag
        filtered = []
        for hit in result.hits if result and hasattr(result, "hits") else []:
            payload = hit.payload if hasattr(hit, "payload") else hit
            if isinstance(payload, dict):
                tags = payload.get("tags", [])
                packet_type = payload.get("packet_type", "")
                envelope = payload.get("envelope", {})
                if isinstance(envelope, dict):
                    envelope_tags = envelope.get("tags", [])
                    envelope_type = envelope.get("packet_type", "")
                    if (
                        segment in tags
                        or segment in envelope_tags
                        or f"memory_{segment}" in packet_type
                        or f"memory_{segment}" in envelope_type
                    ):
                        filtered.append(payload)
            else:
                # Include if we can't determine segment (backward compatibility)
                logger.warning(
                    f"memory_search: Segment filtering ambiguous for query '{query}' "
                    f"(segment '{segment}' not clearly marked). "
                    f"Returning result for backward compatibility. "
                    f"Recommend explicit segment metadata in payload."
                )
                filtered.append(payload)

        return filtered
            return filtered

    except ImportError:
        logger.warning("Memory service not available - returning empty results")
        return []
    except Exception as e:
        logger.error(f"Memory search failed: {e}", exc_info=True)
        return []


async def memory_write(
    segment: str,
    payload: Dict[str, Any],
    agent_id: str = "L",
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Write to memory within a specific segment.

    Args:
        segment: Memory segment name (governance_meta, project_history, tool_audit, session_context)
        payload: Data to write
        agent_id: Agent identifier (default: "L")
        metadata: Optional additional metadata

    Returns:
        Packet ID if successful, None otherwise

    Usage:
        # Write governance rule
        await memory_write("governance_meta", {"rule": "GMP requires Igor approval"}, agent_id="L")

        # Write project decision
        await memory_write("project_history", {"decision": "Use FastAPI", "rationale": "..."}, agent_id="L")
    """
    if segment not in ALL_SEGMENTS:
        logger.warning(f"Unknown memory segment: {segment}, writing anyway")

    try:
        from memory.ingestion import ingest_packet
        from core.schemas import PacketEnvelopeIn, PacketMetadata

        # Create metadata with segment and agent
        packet_metadata = PacketMetadata(
            agent=agent_id,
            domain="l9_internal",
        )

        # Merge with additional metadata if provided
        if metadata:
            if packet_metadata.model_dump(exclude_none=True):
                packet_metadata_dict = packet_metadata.model_dump(exclude_none=True)
                packet_metadata_dict.update(metadata)
                packet_metadata = PacketMetadata(**packet_metadata_dict)

        # Create packet with segment encoded in packet_type
        packet_in = PacketEnvelopeIn(
            packet_type=f"memory_{segment}",
            payload=payload,
            metadata=packet_metadata,
            tags=[segment, agent_id],  # Tag with segment for filtering
        scope = os.getenv("L9_MEMORY_SCOPE", "shared")
        project_id = os.getenv("L9_PROJECT_ID", "l9")
        ctx = build_governance_context(
            caller_id="runtime",
            role="end_user",
            scope=scope,
            project_id=project_id,
            allowed_scopes=[scope],
        )

        result = await ingest_packet(packet_in)
        async with governance_context(ctx):
            # Create metadata with segment and agent
            packet_metadata = PacketMetadata(
                agent=agent_id,
                domain="l9_internal",
            )

        if result and result.packet_id:
            logger.info(
                f"Wrote to memory segment {segment}: packet_id={result.packet_id}"
            # Merge with additional metadata if provided
            if metadata:
                if packet_metadata.model_dump(exclude_none=True):
                    packet_metadata_dict = packet_metadata.model_dump(exclude_none=True)
                    packet_metadata_dict.update(metadata)
                    packet_metadata = PacketMetadata(**packet_metadata_dict)

            # Create packet with segment encoded in packet_type
            packet_in = PacketEnvelopeIn(
                packet_type=f"memory_{segment}",
                payload=payload,
                metadata=packet_metadata,
                tags=[segment, agent_id],  # Tag with segment for filtering
            )
            return str(result.packet_id)
        else:
            logger.warning(f"Memory write to {segment} returned no packet_id")
            return None

            result = await ingest_packet(packet_in)

            if result and result.packet_id:
                logger.info(
                    f"Wrote to memory segment {segment}: packet_id={result.packet_id}"
                )
                return str(result.packet_id)
            else:
                logger.warning(f"Memory write to {segment} returned no packet_id")
                return None

    except ImportError:
        logger.warning("Memory ingestion not available - skipping write")
        return None
    except Exception as e:
        logger.error(f"Memory write failed: {e}", exc_info=True)
        return None


# =============================================================================
# L Usage Rules (Documented)
# =============================================================================

"""
L Memory Usage Rules
====================

L should use memory segments as follows:

1. governance_meta:
   - Use memory_search(governance_meta, ...) to look up rules, authority, policies
   - Use memory_write(governance_meta, ...) to record new governance rules (rare)
   - Example: "What are the approval requirements for GMP runs?"

2. project_history:
tests/integration/test_compliance_audit.py
tests/integration/test_compliance_audit.py
+1
-2

@@ -58,51 +58,51 @@ class TestAuditLogger:
        
        result = await logger.log_tool_execution(
            tool_name="memory_write",
            agent_id="L",
            input_data={"segment": "test"},
            output_data={"success": True},
            success=True,
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_log_memory_write_without_substrate(self):
        """Test logging memory write without substrate."""
        from core.compliance.audit_log import AuditLogger
        
        logger = AuditLogger(substrate_service=None)
        
        result = await logger.log_memory_write(
            agent_id="L",
            segment="governance_patterns",
            content_type="pattern",
            size_bytes=1024,
        )
        
        assert result is True
        assert result is False

    @pytest.mark.asyncio
    async def test_log_command_with_substrate(self):
        """Test logging command with mock substrate."""
        from core.compliance.audit_log import AuditLogger
        
        # Mock substrate
        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock(return_value=True)
        
        logger = AuditLogger(substrate_service=mock_substrate)
        
        with patch.dict('sys.modules', {'memory.substrate_models': MagicMock()}):
            result = await logger.log_command(
                command_id="cmd-002",
                command_type="propose_gmp",
                user_id="Igor",
                action="execute",
                risk_level="high",
                raw_text="@L propose gmp: add feature",
            )
        
        # Should call write_packet
        assert mock_substrate.write_packet.called or result is True

@@ -355,26 +355,25 @@ class TestDateRangeFiltering:


class TestAuditLoggerConvenience:
    """Test audit logger convenience functions."""

    @pytest.mark.asyncio
    async def test_log_command_to_audit(self):
        """Test convenience function for logging commands."""
        from core.compliance.audit_log import log_command_to_audit
        
        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock(return_value=True)
        
        with patch.dict('sys.modules', {'memory.substrate_models': MagicMock()}):
            result = await log_command_to_audit(
                substrate_service=mock_substrate,
                command_id="cmd-convenience-001",
                command_type="analyze",
                user_id="Igor",
                action="execute",
                risk_level="low",
                raw_text="@L analyze",
            )
        
        assert result is True or mock_substrate.write_packet.called

tests/test_memory_governance_gate.py
tests/test_memory_governance_gate.py
New
+61
-0

import sys
from pathlib import Path
import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.schemas import PacketEnvelopeIn

_gate_spec = importlib.util.spec_from_file_location(
    "l9_memory_governance_gate", ROOT / "memory" / "governance_gate.py"
)
_gate_module = importlib.util.module_from_spec(_gate_spec)
sys.modules[_gate_spec.name] = _gate_module
assert _gate_spec.loader is not None
_gate_spec.loader.exec_module(_gate_module)

build_governance_context = _gate_module.build_governance_context
enforce_packet_governance = _gate_module.enforce_packet_governance
ensure_governance_context = _gate_module.ensure_governance_context


def test_build_governance_context_blocks_cursor_private_scope():
    with pytest.raises(RuntimeError):
        build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            project_id="l9",
            allowed_scopes=["developer", "l-private"],
        )


def test_enforce_packet_governance_rejects_client_metadata():
    ctx = build_governance_context(
        caller_id="L",
        role="end_user",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer"],
    )
    packet = PacketEnvelopeIn(
        packet_type="memory.test",
        payload={"content": "hello"},
        metadata={"caller": "C"},
    )
    with pytest.raises(RuntimeError):
        enforce_packet_governance(packet, ctx)


@pytest.mark.asyncio
async def test_ensure_governance_context_uses_env_fallback(monkeypatch):
    monkeypatch.setenv("L9_MEMORY_CALLER_ID", "system")
    monkeypatch.setenv("L9_PROJECT_ID", "l9")
    monkeypatch.setenv("L9_MEMORY_SCOPE", "shared")

    async with ensure_governance_context("test"):
        pass