"""
L9 Core Tools - Tool Embeddings Service
========================================

GMP-78: Semantic Tool Retrieval (Tool RAG)

Provides semantic search over tool definitions using pgvector embeddings.
Instead of exposing all 100+ tools to the LLM, this service enables
retrieval of only the 3-5 most relevant tools per query.

Key Functions:
- embed_tool_description(): Generate embedding vector for a tool description
- store_tool_embedding(): Store a tool's embedding in pgvector
- find_relevant_tools(): Semantic search to find tools relevant to a query
- sync_all_tool_embeddings(): Bulk sync all tool definitions to embeddings table

Architecture:
- Uses OpenAI text-embedding-3-small (1536 dimensions)
- Stores in PostgreSQL with pgvector extension
- Cosine similarity for retrieval
- Integrates with ExecutorToolRegistry for governance filtering

Version: 1.0.0
Created: 2026-01-15
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Embeddings Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "tool_embeddings",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "api.server",
            "core.tools.base_registry",
            "core.tools.registry_adapter",
        ],
    },
}
# ============================================================================

import os
from dataclasses import dataclass
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Embedding model configuration
EMBEDDING_MODEL = os.getenv("TOOL_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small dimension


@dataclass
class ToolEmbeddingResult:
    """Result from tool embedding search."""

    tool_name: str
    description: str
    category: str
    similarity: float
    negative_constraints: list[str]
    metadata: dict[str, Any]


@must_stay_async("callers use await")
async def _get_openai_client():
    """Get OpenAI client for embeddings."""
    try:
        from openai import AsyncOpenAI

        return AsyncOpenAI()
    except ImportError as exc:
        raise RuntimeError("OpenAI client not available") from exc


async def _get_db_pool():
    """Get database connection pool via the repository singleton."""
    try:
        # Import the correct singleton accessor
        from memory.substrate_repository import get_repository

        # Get the initialized repository instance
        repository = get_repository()

        # Return the underlying asyncpg pool
        if repository._pool is None:
            # Pool not initialized - repository.connect() must be called at startup
            await repository.connect()

        return repository._pool

    except (ImportError, RuntimeError) as exc:
        logger.error(
            "Failed to get database pool for tool embeddings",
            error=str(exc),
            exc_info=True,
        )
        raise RuntimeError("Database pool not available for tool embeddings") from exc


async def embed_tool_description(description: str) -> list[float] | None:
    """
    Generate embedding vector for a tool description.

    Args:
        description: Tool description text

    Returns:
        List of floats (embedding vector) or None if failed
    """
    client = await _get_openai_client()

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=description,
            dimensions=EMBEDDING_DIMENSION,  # Truncate to match DB VECTOR(1536) schema
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to embed tool description: {e}")
        raise


async def store_tool_embedding(
    tool_name: str,
    description: str,
    category: str = "general",
    negative_constraints: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Store a tool's embedding in the database.

    Args:
        tool_name: Unique tool identifier
        description: Tool description (used for embedding)
        category: Tool category for filtering
        negative_constraints: List of "don't use when X" guidance
        metadata: Additional tool metadata

    Returns:
        True if stored successfully
    """
    pool = await _get_db_pool()

    # Generate embedding
    embedding = await embed_tool_description(description)

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tool_embeddings
                    (tool_name, description, category, embedding, negative_constraints, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tool_name) DO UPDATE SET
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    embedding = EXCLUDED.embedding,
                    negative_constraints = EXCLUDED.negative_constraints,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                tool_name,
                description,
                category,
                str(embedding),  # pgvector accepts string representation
                negative_constraints or [],
                metadata or {},
            )

        logger.debug(f"Stored embedding for tool: {tool_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to store tool embedding: {e}")
        raise


async def find_relevant_tools(
    query: str,
    top_k: int = 5,
    exclude_categories: list[str] | None = None,
    min_similarity: float = 0.3,
) -> list[ToolEmbeddingResult]:
    """
    Find tools relevant to a query using semantic search.

    Args:
        query: User query or task description
        top_k: Maximum number of tools to return
        exclude_categories: Categories to exclude from results
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of ToolEmbeddingResult ordered by relevance
    """
    pool = await _get_db_pool()

    # Generate query embedding
    query_embedding = await embed_tool_description(query)

    try:
        async with pool.acquire() as conn:
            # Build query with optional category exclusion
            exclude_clause = ""
            params = [str(query_embedding), top_k * 2]  # Fetch more, filter later

            if exclude_categories:
                exclude_clause = "AND category != ALL($3)"
                params.append(exclude_categories)

            rows = await conn.fetch(
                f"""
                SELECT
                    tool_name,
                    description,
                    category,
                    1 - (embedding <=> $1) as similarity,
                    negative_constraints,
                    metadata
                FROM tool_embeddings
                WHERE embedding IS NOT NULL
                {exclude_clause}
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                *params,
            )

        results = []
        for row in rows:
            similarity = float(row["similarity"])
            if similarity >= min_similarity:
                results.append(
                    ToolEmbeddingResult(
                        tool_name=row["tool_name"],
                        description=row["description"],
                        category=row["category"],
                        similarity=similarity,
                        negative_constraints=row["negative_constraints"] or [],
                        metadata=row["metadata"] or {},
                    )
                )

        # Return top_k after filtering
        return results[:top_k]

    except Exception as e:
        logger.error(f"Failed to search tool embeddings: {e}")
        raise


async def find_tools_keyword(
    query: str,
    top_k: int = 10,
    min_rank: float = 0.0,
) -> list[ToolEmbeddingResult]:
    """
    Find tools using BM25 keyword search (PostgreSQL full-text).

    Adapted from: Tool Discovery research (harvested 1_semantic_discovery.py)

    Args:
        query: Search query (keywords)
        top_k: Maximum results
        min_rank: Minimum ts_rank threshold

    Returns:
        List of ToolEmbeddingResult ordered by BM25 rank
    """
    pool = await _get_db_pool()

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    tool_name,
                    description,
                    category,
                    ts_rank(
                        search_vector,
                        plainto_tsquery('english', $1)
                    ) as rank,
                    negative_constraints,
                    metadata
                FROM tool_embeddings
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
                """,
                query,
                top_k,
            )

        results = []
        for row in rows:
            rank = float(row["rank"])
            if rank >= min_rank:
                results.append(
                    ToolEmbeddingResult(
                        tool_name=row["tool_name"],
                        description=row["description"],
                        category=row["category"],
                        similarity=rank,  # Use rank as similarity proxy
                        negative_constraints=row["negative_constraints"] or [],
                        metadata=row["metadata"] or {},
                    )
                )

        logger.debug(f"Keyword search for '{query}': {len(results)} tools")
        return results

    except Exception as e:
        logger.warning(f"Keyword search failed (may need migration 0026): {e}")
        return []  # Graceful fallback


async def find_tools_hybrid(
    query: str,
    top_k: int = 5,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
    min_similarity: float = 0.3,
) -> list[ToolEmbeddingResult]:
    """
    Hybrid tool discovery combining semantic + keyword (BM25) search.

    Adapted from: Tool Discovery research (harvested 1_semantic_discovery.py)

    Uses weighted combination of:
    - Semantic search (pgvector cosine similarity)
    - Keyword search (PostgreSQL BM25 full-text)

    Args:
        query: Search query
        top_k: Maximum results
        semantic_weight: Weight for semantic scores (default 0.6)
        keyword_weight: Weight for keyword scores (default 0.4)
        min_similarity: Minimum combined score threshold

    Returns:
        List of ToolEmbeddingResult with hybrid ranking
    """
    # Semantic search
    semantic_results = await find_relevant_tools(
        query, top_k=top_k * 2, min_similarity=0.1
    )
    semantic_scores = {r.tool_name: r.similarity for r in semantic_results}

    # Keyword search (BM25)
    keyword_results = await find_tools_keyword(query, top_k=top_k * 2)
    # Normalize BM25 ranks to 0-1 range
    max_rank = max((r.similarity for r in keyword_results), default=1.0) or 1.0
    keyword_scores = {r.tool_name: r.similarity / max_rank for r in keyword_results}

    # Hybrid fusion
    all_tools = set(semantic_scores.keys()) | set(keyword_scores.keys())

    hybrid_scores = {}
    for tool_name in all_tools:
        sem_score = semantic_scores.get(tool_name, 0.0)
        kw_score = keyword_scores.get(tool_name, 0.0)
        hybrid_scores[tool_name] = (
            semantic_weight * sem_score + keyword_weight * kw_score
        )

    # Sort by hybrid score
    sorted_tools = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)

    # Build results from semantic_results (has full data)
    tool_data = {r.tool_name: r for r in semantic_results}
    tool_data.update({r.tool_name: r for r in keyword_results})

    results = []
    for tool_name, score in sorted_tools[:top_k]:
        if score < min_similarity:
            continue
        if tool_name in tool_data:
            base = tool_data[tool_name]
            results.append(
                ToolEmbeddingResult(
                    tool_name=base.tool_name,
                    description=base.description,
                    category=base.category,
                    similarity=score,
                    negative_constraints=base.negative_constraints,
                    metadata={**base.metadata, "discovery_method": "hybrid"},
                )
            )

    logger.info(f"Hybrid search for '{query[:50]}': {len(results)} tools")
    return results


async def sync_all_tool_embeddings() -> int:
    """
    Sync all tool definitions to the embeddings table.

    Reads from L_INTERNAL_TOOLS and stores embeddings for each.
    Should be called at startup to ensure embeddings are current.

    Returns:
        Number of tools synced
    """
    try:
        from core.tools.tool_graph import L9_TOOLS, L_INTERNAL_TOOLS

        all_tools = L_INTERNAL_TOOLS + L9_TOOLS
        count = 0

        for tool in all_tools:
            # Build enriched description for better semantic matching
            enriched_description = tool.description
            if tool.category:
                enriched_description = f"[{tool.category}] {enriched_description}"

            # Get negative constraints if available
            negative_constraints = getattr(tool, "negative_constraints", [])

            # Build metadata
            metadata = {
                "scope": getattr(tool, "scope", "internal"),
                "risk_level": getattr(tool, "risk_level", "low"),
                "is_destructive": getattr(tool, "is_destructive", False),
                "requires_igor_approval": getattr(
                    tool, "requires_igor_approval", False
                ),
                "agent_id": getattr(tool, "agent_id", None),
            }

            success = await store_tool_embedding(
                tool_name=tool.name,
                description=enriched_description,
                category=tool.category,
                negative_constraints=negative_constraints,
                metadata=metadata,
            )

            if success:
                count += 1

        logger.info(f"Synced {count}/{len(all_tools)} tool embeddings")
        return count

    except ImportError as e:
        raise RuntimeError(f"Could not import tool definitions: {e}") from e
    except Exception as e:
        logger.error(f"Failed to sync tool embeddings: {e}")
        raise


async def get_tool_embedding(tool_name: str) -> ToolEmbeddingResult | None:
    """
    Get a single tool's embedding data.

    Args:
        tool_name: Tool identifier

    Returns:
        ToolEmbeddingResult or None if not found
    """
    pool = await _get_db_pool()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tool_name, description, category, negative_constraints, metadata
                FROM tool_embeddings
                WHERE tool_name = $1
                """,
                tool_name,
            )

        if not row:
            return None

        return ToolEmbeddingResult(
            tool_name=row["tool_name"],
            description=row["description"],
            category=row["category"],
            similarity=1.0,  # Exact match
            negative_constraints=row["negative_constraints"] or [],
            metadata=row["metadata"] or {},
        )

    except Exception as e:
        logger.error(f"Failed to get tool embedding: {e}")
        raise


async def delete_tool_embedding(tool_name: str) -> bool:
    """
    Delete a tool's embedding from the database.

    Args:
        tool_name: Tool identifier

    Returns:
        True if deleted successfully
    """
    pool = await _get_db_pool()

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tool_embeddings WHERE tool_name = $1",
                tool_name,
            )

        return "DELETE 1" in result

    except Exception as e:
        logger.error(f"Failed to delete tool embedding: {e}")
        raise


__all__ = [
    "EMBEDDING_DIMENSION",
    "EMBEDDING_MODEL",
    "ToolEmbeddingResult",
    "delete_tool_embedding",
    "embed_tool_description",
    "find_relevant_tools",
    "get_tool_embedding",
    "store_tool_embedding",
    "sync_all_tool_embeddings",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-013",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.tools.tool_graph",
        "memory.substrate_repository",
    ],
    "tags": [
        "async",
        "dataclass",
        "debugging",
        "foundation",
        "llm",
        "logging",
        "tool-registry",
    ],
    "keywords": [
        "all",
        "definitions",
        "delete",
        "description",
        "embed",
        "embedding",
        "embeddings",
        "find",
    ],
    "business_value": "Provides semantic search over tool definitions using pgvector embeddings. Instead of exposing all 100+ tools to the LLM, this service enables retrieval of only the 3-5 most relevant tools per query. e",
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
