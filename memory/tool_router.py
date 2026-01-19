"""
L9 Memory - Semantic Tool Router
================================

pgvector-backed semantic search for dynamic tool discovery.

Instead of injecting all 50+ tools into every prompt, agents can search
for the most relevant tools by semantic similarity.

Workflow:
1. Tool descriptions are embedded and stored in pgvector
2. Agent query → semantic search for relevant tools
3. Only top-k matching tools injected into context

Benefits:
- Reduces prompt bloat (50 tools → 5 relevant tools)
- Enables dynamic tool discovery
- Tools can be added/updated without code changes

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Semantic Tool Router",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "tool_router",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["memory.__init__", "tests.memory.test_tool_router"],
    },
}
# ============================================================================

import hashlib
import asyncio
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToolEmbedding:
    """Embedded tool for semantic search."""

    tool_name: str
    description: str
    category: str
    embedding_id: UUID = field(default_factory=uuid4)

    # Metadata
    risk_level: str = "low"
    is_destructive: bool = False
    requires_confirmation: bool = False
    external_apis: list[str] = field(default_factory=list)

    # Embedding state
    embedded_at: Optional[datetime] = None
    content_hash: Optional[str] = None

    def to_searchable_text(self) -> str:
        """Generate text for embedding."""
        parts = [
            f"Tool: {self.tool_name}",
            f"Description: {self.description}",
            f"Category: {self.category}",
        ]
        if self.external_apis:
            parts.append(f"Uses: {', '.join(self.external_apis)}")
        return "\n".join(parts)

    def compute_hash(self) -> str:
        """Compute content hash for change detection."""
        content = f"{self.tool_name}:{self.description}:{self.category}"
        # Use SHA256 instead of MD5 for better security
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ToolMatch:
    """Result from semantic tool search."""

    tool_name: str
    description: str
    category: str
    similarity: float

    # Metadata
    risk_level: str = "low"
    is_destructive: bool = False
    external_apis: list[str] = field(default_factory=list)

    def to_prompt_format(self) -> str:
        """Format for prompt injection."""
        risk_indicator = "⚠️ " if self.is_destructive else ""
        return f"- {risk_indicator}{self.tool_name}: {self.description}"


@dataclass
class ToolSearchResult:
    """Complete result from tool search."""

    query: str
    matches: list[ToolMatch]
    search_time_ms: float
    total_tools: int

    def to_prompt_context(self) -> str:
        """Generate context string for prompt injection."""
        if not self.matches:
            return "No relevant tools found."

        lines = ["## Available Tools (most relevant):", ""]
        for match in self.matches:
            lines.append(match.to_prompt_format())

        return "\n".join(lines)


# =============================================================================
# Tool Router
# =============================================================================


class ToolRouter:
    """
    Semantic router for dynamic tool discovery.

    Uses pgvector to store and search tool descriptions.

    Usage:
        router = ToolRouter(embedding_provider, repository)
        await router.embed_tools(L_INTERNAL_TOOLS)

        # Find relevant tools for a query
        result = await router.find_relevant_tools(
            "How do I search memory?",
            limit=5,
        )

        # Get formatted context for prompt
        context = result.to_prompt_context()
    """

    # Agent ID used for tool embeddings
    TOOL_AGENT_ID = "tool_router"

    def __init__(
        self,
        embedding_provider: Optional[Any] = None,
        repository: Optional[Any] = None,
        cache_embeddings: bool = True,
    ):
        """
        Initialize tool router.

        Args:
            embedding_provider: EmbeddingProvider for generating embeddings
            repository: SubstrateRepository for pgvector storage
            cache_embeddings: Whether to cache embeddings in memory
        """
        self._provider = embedding_provider
        self._repository = repository
        self._cache_embeddings = cache_embeddings

        # In-memory cache for testing without DB
        self._tool_cache: dict[str, ToolEmbedding] = {}
        self._embedding_cache: dict[str, list[float]] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_version = 0

        # Track if tools have been embedded
        self._tools_embedded = False

        logger.info("ToolRouter initialized", cache_enabled=cache_embeddings)

    async def embed_tool(self, tool: Any) -> Optional[ToolEmbedding]:
        """
        Embed a single tool definition.

        Args:
            tool: ToolDefinition from core.tools.tool_graph

        Returns:
            ToolEmbedding if successful
        """
        # Extract fields from ToolDefinition
        tool_name = getattr(tool, "name", str(tool))
        description = getattr(tool, "description", "")
        category = getattr(tool, "category", "general")
        risk_level = getattr(tool, "risk_level", "low")
        is_destructive = getattr(tool, "is_destructive", False)
        requires_confirmation = getattr(tool, "requires_confirmation", False)
        external_apis = getattr(tool, "external_apis", [])

        # Create embedding record
        embedding = ToolEmbedding(
            tool_name=tool_name,
            description=description,
            category=category,
            risk_level=risk_level,
            is_destructive=is_destructive,
            requires_confirmation=requires_confirmation,
            external_apis=external_apis,
        )

        embedding.content_hash = embedding.compute_hash()

        # Check if already embedded with same content
        async with self._cache_lock:
            cached = self._tool_cache.get(tool_name)
        if cached and cached.content_hash == embedding.content_hash:
            logger.debug(f"Tool already embedded: {tool_name}")
            return cached

        # Generate embedding
        searchable_text = embedding.to_searchable_text()

        vector = None
        if self._provider:
            try:
                vector = await self._provider.embed_text(searchable_text)

                # Store in pgvector if repository available
                if self._repository:
                    await self._store_embedding(embedding, vector)

                # Cache
            except Exception as e:
                logger.error(f"Failed to embed tool {tool_name}: {e}")
                return None

        async with self._cache_lock:
            cached = self._tool_cache.get(tool_name)
            if cached and cached.content_hash == embedding.content_hash:
                return cached
            if vector is not None and self._cache_embeddings:
                self._embedding_cache[tool_name] = vector
            embedding.embedded_at = datetime.utcnow()
            self._tool_cache[tool_name] = embedding
            self._cache_version += 1

        logger.debug(f"Embedded tool: {tool_name}")
        return embedding

    async def embed_tools(self, tools: list[Any]) -> int:
        """
        Embed multiple tool definitions.

        Args:
            tools: List of ToolDefinition objects

        Returns:
            Number of tools successfully embedded
        """
        count = 0
        for tool in tools:
            result = await self.embed_tool(tool)
            if result:
                count += 1

        async with self._cache_lock:
            self._tools_embedded = True
            self._cache_version += 1
        logger.info(f"Embedded {count}/{len(tools)} tools")
        return count

    async def _store_embedding(
        self,
        tool: ToolEmbedding,
        vector: list[float],
    ) -> None:
        """Store tool embedding in pgvector."""
        if not self._repository:
            return

        try:
            # Use semantic_memory table with tool_router agent_id
            await self._repository.insert_semantic_embedding(
                vector=vector,
                payload={
                    "tool_name": tool.tool_name,
                    "description": tool.description,
                    "category": tool.category,
                    "risk_level": tool.risk_level,
                    "is_destructive": tool.is_destructive,
                    "external_apis": tool.external_apis,
                    "content_hash": tool.content_hash,
                    "embedding_id": str(tool.embedding_id),
                },
                agent_id=self.TOOL_AGENT_ID,
            )
        except Exception as e:
            logger.error(f"Failed to store embedding for {tool.tool_name}: {e}")

    async def find_relevant_tools(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.3,
        category_filter: Optional[str] = None,
    ) -> ToolSearchResult:
        """
        Find tools most relevant to a query.

        Args:
            query: Natural language query
            limit: Maximum tools to return
            min_similarity: Minimum similarity threshold
            category_filter: Optional category to filter by

        Returns:
            ToolSearchResult with matching tools
        """
        import time

        start_time = time.time()

        matches: list[ToolMatch] = []

        # Try pgvector search first
        if self._provider and self._repository:
            try:
                query_vector = await self._provider.embed_text(query)

                results = await self._repository.search_semantic_memory(
                    query_embedding=query_vector,
                    agent_id=self.TOOL_AGENT_ID,
                    top_k=limit * 2,  # Get extra for filtering
                )

                for hit in results:
                    if hit.get("score", 0) < min_similarity:
                        continue

                    payload = hit.get("payload", {})

                    # Apply category filter
                    if category_filter and payload.get("category") != category_filter:
                        continue

                    matches.append(
                        ToolMatch(
                            tool_name=payload.get("tool_name", "unknown"),
                            description=payload.get("description", ""),
                            category=payload.get("category", "general"),
                            similarity=hit.get("score", 0.0),
                            risk_level=payload.get("risk_level", "low"),
                            is_destructive=payload.get("is_destructive", False),
                            external_apis=payload.get("external_apis", []),
                        )
                    )

                    if len(matches) >= limit:
                        break

            except Exception as e:
                logger.warning(f"pgvector search failed, falling back to cache: {e}")

        tool_cache, _, _, _ = await self._snapshot_cache()

        # Fallback to in-memory cache search
        if not matches and tool_cache:
            matches = await self._search_cache(
                query, limit, min_similarity, category_filter
            )

        search_time = (time.time() - start_time) * 1000

        return ToolSearchResult(
            query=query,
            matches=matches,
            search_time_ms=search_time,
            total_tools=len(tool_cache),
        )

    async def _search_cache(
        self,
        query: str,
        limit: int,
        min_similarity: float,
        category_filter: Optional[str],
    ) -> list[ToolMatch]:
        """Search in-memory cache (fallback)."""
        tool_cache, embedding_cache, _, _ = await self._snapshot_cache()
        if not self._provider:
            # Without embeddings, do simple text matching
            return self._text_match_cache(tool_cache, query, limit, category_filter)

        try:
            query_vector = await self._provider.embed_text(query)
        except Exception:
            return self._text_match_cache(tool_cache, query, limit, category_filter)

        # Compute similarities
        scored: list[tuple[float, ToolEmbedding]] = []

        for tool_name, tool in tool_cache.items():
            if category_filter and tool.category != category_filter:
                continue

            if tool_name in embedding_cache:
                tool_vector = embedding_cache[tool_name]
                similarity = self._cosine_similarity(query_vector, tool_vector)

                if similarity >= min_similarity:
                    scored.append((similarity, tool))

        # Sort by similarity
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            ToolMatch(
                tool_name=tool.tool_name,
                description=tool.description,
                category=tool.category,
                similarity=score,
                risk_level=tool.risk_level,
                is_destructive=tool.is_destructive,
                external_apis=tool.external_apis,
            )
            for score, tool in scored[:limit]
        ]

    async def _snapshot_cache(
        self,
    ) -> tuple[dict[str, ToolEmbedding], dict[str, list[float]], bool, int]:
        async with self._cache_lock:
            return (
                dict(self._tool_cache),
                dict(self._embedding_cache),
                self._tools_embedded,
                self._cache_version,
            )

    def _text_match_cache(
        self,
        tool_cache: dict[str, ToolEmbedding],
        query: str,
        limit: int,
        category_filter: Optional[str],
    ) -> list[ToolMatch]:
        """Simple text matching fallback."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored: list[tuple[int, ToolEmbedding]] = []

        for tool in tool_cache.values():
            if category_filter and tool.category != category_filter:
                continue

            # Count word matches
            tool_text = f"{tool.tool_name} {tool.description}".lower()
            score = sum(1 for word in query_words if word in tool_text)

            if score > 0:
                scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            ToolMatch(
                tool_name=tool.tool_name,
                description=tool.description,
                category=tool.category,
                similarity=float(score) / len(query_words) if query_words else 0.0,
                risk_level=tool.risk_level,
                is_destructive=tool.is_destructive,
                external_apis=tool.external_apis,
            )
            for score, tool in scored[:limit]
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_tool_context(
        self,
        result: ToolSearchResult,
        include_metadata: bool = False,
    ) -> str:
        """
        Format search result for prompt injection.

        Args:
            result: ToolSearchResult from find_relevant_tools
            include_metadata: Whether to include risk/API info

        Returns:
            Formatted string for prompt context
        """
        if not result.matches:
            return "No relevant tools found for this query."

        lines = [
            "## Relevant Tools",
            f'(Top {len(result.matches)} matches for: "{result.query}")',
            "",
        ]

        for match in result.matches:
            if include_metadata:
                risk = (
                    f" [risk: {match.risk_level}]" if match.risk_level != "low" else ""
                )
                apis = (
                    f" (uses: {', '.join(match.external_apis)})"
                    if match.external_apis
                    else ""
                )
                lines.append(
                    f"- **{match.tool_name}**{risk}: {match.description}{apis}"
                )
            else:
                lines.append(f"- **{match.tool_name}**: {match.description}")

        return "\n".join(lines)

    async def get_tools_for_task(
        self,
        task_description: str,
        limit: int = 5,
    ) -> str:
        """
        Convenience method: search and format in one call.

        Args:
            task_description: What the agent is trying to do
            limit: Max tools to return

        Returns:
            Formatted tool context string
        """
        result = await self.find_relevant_tools(task_description, limit=limit)
        return self.get_tool_context(result)

    async def list_embedded_tools(self) -> list[str]:
        """List all embedded tool names."""
        tool_cache, _, _, _ = await self._snapshot_cache()
        return list(tool_cache.keys())

    async def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        (
            tool_cache,
            embedding_cache,
            tools_embedded,
            cache_version,
        ) = await self._snapshot_cache()
        categories = {}
        for tool in tool_cache.values():
            categories[tool.category] = categories.get(tool.category, 0) + 1

        return {
            "total_tools": len(tool_cache),
            "tools_with_embeddings": len(embedding_cache),
            "categories": categories,
            "is_ready": tools_embedded,
            "cache_version": cache_version,
        }


# =============================================================================
# Singleton Factory
# =============================================================================


_router: Optional[ToolRouter] = None


@must_stay_async("callers use await")
async def get_tool_router(
    embedding_provider: Optional[Any] = None,
    repository: Optional[Any] = None,
) -> ToolRouter:
    """Get or create singleton tool router."""
    global _router

    if _router is None:
        _router = ToolRouter(
            embedding_provider=embedding_provider,
            repository=repository,
        )

    return _router


async def init_tool_router(
    tools: list[Any],
    embedding_provider: Optional[Any] = None,
    repository: Optional[Any] = None,
) -> ToolRouter:
    """
    Initialize tool router with tools.

    Convenience function for startup.
    """
    router = await get_tool_router(embedding_provider, repository)
    await router.embed_tools(tools)
    return router


async def find_tools(
    query: str,
    limit: int = 5,
) -> ToolSearchResult:
    """
    Convenience function to find relevant tools.

    Uses singleton router (must be initialized first).
    """
    router = await get_tool_router()
    return await router.find_relevant_tools(query, limit=limit)


__all__ = [
    # Data classes
    "ToolEmbedding",
    "ToolMatch",
    "ToolSearchResult",
    # Main class
    "ToolRouter",
    # Factory functions
    "get_tool_router",
    "init_tool_router",
    "find_tools",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-022",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "caching",
        "dataclass",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "routing",
        "security",
    ],
    "keywords": [
        "agent",
        "compute",
        "discovery",
        "dynamic",
        "embed",
        "embedded",
        "embedding",
        "find",
    ],
    "business_value": "Provides tool router components including ToolEmbedding, ToolMatch, ToolSearchResult",
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
