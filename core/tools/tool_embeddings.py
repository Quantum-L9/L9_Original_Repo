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

import os
import structlog
from dataclasses import dataclass
from typing import Any
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
    except ImportError:
        logger.warning("OpenAI client not available")
        return None


async def _get_db_pool():
    """Get database connection pool."""
    try:
        from memory.substrate_repository import get_pool

        return await get_pool()
    except ImportError:
        logger.warning("Database pool not available")
        return None


async def embed_tool_description(description: str) -> list[float] | None:
    """
    Generate embedding vector for a tool description.

    Args:
        description: Tool description text

    Returns:
        List of floats (embedding vector) or None if failed
    """
    client = await _get_openai_client()
    if not client:
        return None

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=description,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to embed tool description: {e}")
        return None


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
    if not pool:
        return False

    # Generate embedding
    embedding = await embed_tool_description(description)
    if not embedding:
        logger.warning(f"Could not generate embedding for tool: {tool_name}")
        return False

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
        return False


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
    if not pool:
        return []

    # Generate query embedding
    query_embedding = await embed_tool_description(query)
    if not query_embedding:
        logger.warning("Could not generate query embedding")
        return []

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
        return []


async def sync_all_tool_embeddings() -> int:
    """
    Sync all tool definitions to the embeddings table.

    Reads from L_INTERNAL_TOOLS and stores embeddings for each.
    Should be called at startup to ensure embeddings are current.

    Returns:
        Number of tools synced
    """
    try:
        from core.tools.tool_graph import L_INTERNAL_TOOLS, L9_TOOLS

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
        logger.warning(f"Could not import tool definitions: {e}")
        return 0
    except Exception as e:
        logger.error(f"Failed to sync tool embeddings: {e}")
        return 0


async def get_tool_embedding(tool_name: str) -> ToolEmbeddingResult | None:
    """
    Get a single tool's embedding data.

    Args:
        tool_name: Tool identifier

    Returns:
        ToolEmbeddingResult or None if not found
    """
    pool = await _get_db_pool()
    if not pool:
        return None

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
        return None


async def delete_tool_embedding(tool_name: str) -> bool:
    """
    Delete a tool's embedding from the database.

    Args:
        tool_name: Tool identifier

    Returns:
        True if deleted successfully
    """
    pool = await _get_db_pool()
    if not pool:
        return False

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tool_embeddings WHERE tool_name = $1",
                tool_name,
            )

        return "DELETE 1" in result

    except Exception as e:
        logger.error(f"Failed to delete tool embedding: {e}")
        return False


__all__ = [
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "ToolEmbeddingResult",
    "embed_tool_description",
    "store_tool_embedding",
    "find_relevant_tools",
    "sync_all_tool_embeddings",
    "get_tool_embedding",
    "delete_tool_embedding",
]
