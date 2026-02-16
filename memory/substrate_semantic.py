"""
L9 Memory Substrate - Semantic Layer
Version: 1.0.0

Embedding generation and vector search helpers.
Provides a pluggable embedding provider interface.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Semantic Layer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "substrate_semantic",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.__init__",
            "memory.substrate_service",
            "tests.memory.test_substrate_semantic",
            "tests.test_memory_substrate_basic",
        ],
    },
}
# ============================================================================

import asyncio
import os
import random
from abc import (  # noqa: ADR-0026 - ABC provides shared implementation
    ABC,
    abstractmethod,
)
from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

EMBEDDING_DIMENSIONS = 1536


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    @must_stay_async("callers use await")
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (list of floats)
        """
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-large.

    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-large",
        dimensions: int = 1536,
        api_key: str | None = None,
        max_retries: int = 3,
        base_backoff: float = 0.5,
    ):
        """
        Initializes an OpenAI embedding provider for generating text embeddings using the specified model and configuration.
        Args:
            model: Name of the embedding model, defaults to "text-embedding-3-large".
            dimensions: Size of the embedding vectors, typically 1536.
            api_key: Optional API key for OpenAI authentication; uses environment variable if None.
            max_retries: Number of retry attempts for API calls.
            base_backoff: Initial backoff time in seconds between retries.
        """
        self._model = model
        self._dimensions = dimensions
        self._api_key = api_key
        self._client = None
        self._max_retries = max_retries
        self._base_backoff = base_backoff

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "openai package required for OpenAI embeddings. "
                    "Install with: pip install openai"
                ) from None
        return self._client

    async def _with_retries(self, coro_func, *, operation: str):
        """
        Execute async function with exponential backoff retry logic.

        Args:
            coro_func: Async function to execute (called each attempt)
            operation: Name of operation for logging

        Returns:
            Result from successful coro_func() call

        Raises:
            RuntimeError: If all retries exhausted
        """
        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro_func()
            except Exception as exc:
                last_error = exc
                if attempt == self._max_retries:
                    break
                delay = self._base_backoff * (2 ** (attempt - 1))
                jitter = random.random() * 0.1
                logger.warning(
                    "Embedding request failed, retrying",
                    operation=operation,
                    attempt=attempt,
                    max_retries=self._max_retries,
                    error=str(exc),
                    delay=round(delay + jitter, 3),
                )
                await asyncio.sleep(delay + jitter)
        raise RuntimeError(
            f"Embedding request failed after {self._max_retries} retries: {last_error}"
        ) from last_error

    @must_stay_async("callers use await")
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API with retry logic."""
        client = self._get_client()

        async def _embed() -> list[float]:
            """Inner function to call OpenAI embeddings API."""
            response = await client.embeddings.create(
                model=self._model,
                input=text,
                dimensions=self._dimensions,
            )
            return response.data[0].embedding

        return await self._with_retries(_embed, operation="embed_text")

    @must_stay_async("callers use await")
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for batch of texts with retry logic."""
        client = self._get_client()

        async def _embed() -> list[list[float]]:
            """Inner function to call OpenAI batch embeddings API."""
            response = await client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]

        return await self._with_retries(_embed, operation="embed_batch")

    @property
    def dimensions(self) -> int:
        """
        Returns the dimensionality of the embedding vectors used by the provider.

        Args: None

        Returns:
            An integer representing the size of the embedding vectors.
        """
        return self._dimensions


class StubEmbeddingProvider(EmbeddingProvider):
    """
    Stub embedding provider for testing without API calls.

    Generates deterministic pseudo-random vectors based on text hash.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        """Initialize stub provider with specified dimensions."""
        self._dimensions = dimensions

    @must_stay_async("callers use await")
    async def embed_text(self, text: str) -> list[float]:
        """Generate stub embedding from text hash."""
        import hashlib

        # Create deterministic seed from text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)

        # Generate pseudo-random vector
        import random

        rng = random.Random(seed)
        vector = [rng.gauss(0, 1) for _ in range(self._dimensions)]

        # Normalize to unit vector
        magnitude = sum(v * v for v in vector) ** 0.5
        return [v / magnitude for v in vector]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate stub embeddings for batch."""
        return [await self.embed_text(text) for text in texts]

    @property
    def dimensions(self) -> int:
        """Returns the number of dimensions used in the embedding vectors for semantic representations."""
        return self._dimensions


class SemanticService:
    """
    Service for semantic operations on the memory substrate.

    Wraps embedding provider and repository for semantic search.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        repository: Any | None = None,  # SubstrateRepository
    ):
        """
        Initialize semantic service.

        Args:
            embedding_provider: Provider for generating embeddings (uses stub if not provided)
            repository: SubstrateRepository instance for DB access (optional)
        """
        if embedding_provider is None:
            if os.getenv("L9_ALLOW_STUB_EMBEDDINGS") == "1":
                logger.warning(
                    "Using stub embeddings due to L9_ALLOW_STUB_EMBEDDINGS=1"
                )
                embedding_provider = StubEmbeddingProvider(
                    dimensions=EMBEDDING_DIMENSIONS
                )
            else:
                raise RuntimeError(
                    "Embedding provider required; refusing implicit stub fallback. "
                    "Set L9_ALLOW_STUB_EMBEDDINGS=1 for explicit local-only stub mode."
                )

        if embedding_provider.dimensions != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, "
                f"got {embedding_provider.dimensions}"
            )

        self._provider = embedding_provider
        self._repository = repository

    @must_stay_async("callers use await")
    async def embed_and_store(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: str | None = None,
        scope: str = "cursor",  # RLS scope: developer, global, cursor, l-private, agent
    ) -> str:
        """
        Generate embedding for text and store in semantic_memory.

        Args:
            text: Text to embed
            payload: Metadata payload to store with embedding
            agent_id: Optional agent identifier
            scope: RLS scope ('developer', 'global', 'shared', 'l-private')

        Returns:
            embedding_id as string

        Raises:
            RuntimeError: If embedding generation fails or returns null/empty
        """
        logger.debug(f"Generating embedding for text: {text[:100]}...")

        # Generate embedding
        vector = await self._provider.embed_text(text)

        # VALIDATION: Reject null/empty embeddings (GMP-132)
        if vector is None or len(vector) == 0:
            logger.error(
                "Attempted to store null/empty embedding, skipping",
                payload=payload,
                text_preview=text[:100],
            )
            raise RuntimeError("Embedding generation returned null/empty vector")
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(vector)}"
            )

        # Enrich payload with original text
        enriched_payload = {
            **payload,
            "_text": text,
            "_model": getattr(self._provider, "_model", "unknown"),
        }

        # Store in database with explicit scope for RLS
        embedding_id = await self._repository.insert_semantic_embedding(
            vector=vector,
            payload=enriched_payload,
            agent_id=agent_id,
            scope=scope,
        )

        logger.debug(f"Stored embedding {embedding_id} with scope={scope}")
        return str(embedding_id)

    async def generate_embedding(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: str | None = None,
    ) -> tuple[list[float], dict[str, Any], str | None]:
        """
        Generate an embedding and return vector + enriched payload.

        This is useful for transactional write paths where insertion is deferred.

        Returns:
            tuple of (vector, enriched_payload, agent_id)

        Raises:
            RuntimeError: If embedding generation returns null/empty vector
        """
        vector = await self._provider.embed_text(text)

        # VALIDATION: Reject null/empty embeddings (GMP-132)
        if vector is None or len(vector) == 0:
            logger.error(
                "generate_embedding returned null/empty vector",
                payload=payload,
                text_preview=text[:100],
            )
            raise RuntimeError("Embedding generation returned null/empty vector")

        enriched_payload = {
            **payload,
            "_text": text,
            "_model": getattr(self._provider, "_model", "unknown"),
        }
        return vector, enriched_payload, agent_id

    @must_stay_async("callers use await")
    async def search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: str | None = None,
        tags_include: list[str] | None = None,
        tags_boost: list[str] | None = None,
        tag_boost_factor: float = 1.15,
    ) -> list[dict[str, Any]]:
        """
        Search semantic memory for similar content.

        Optionally filter and/or boost by tags for increased retrieval accuracy.

        Args:
            query: Natural language query
            top_k: Number of results
            agent_id: Optional filter by agent
            tags_include: Only return memories whose packet has at least one of these tags
            tags_boost: Boost score when hit has any of these tags (multiply by tag_boost_factor)
            tag_boost_factor: Score multiplier for tag matches (default 1.15)

        Returns:
            List of hits with embedding_id, score, payload
        """
        logger.debug(f"Semantic search: {query[:100]}...")

        # Generate query embedding
        query_vector = await self._provider.embed_text(query)
        if len(query_vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Query embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(query_vector)}"
            )

        # Search database (repository applies tag filter and boost)
        hits = await self._repository.search_semantic_memory(
            query_embedding=query_vector,
            top_k=top_k,
            agent_id=agent_id,
            tags_include=tags_include,
            tags_boost=tags_boost,
            tag_boost_factor=tag_boost_factor,
        )

        logger.debug(f"Found {len(hits)} results")
        return [hit.model_dump() for hit in hits]

    @must_stay_async("callers use await")
    async def batch_embed_and_store(
        self,
        items: list[dict[str, Any]],
        text_key: str = "text",
        agent_id: str | None = None,
    ) -> list[str]:
        """
        Embed and store multiple items.

        Args:
            items: List of dicts with text and payload
            text_key: Key in dict containing text to embed
            agent_id: Optional agent identifier

        Returns:
            List of embedding_ids

        Raises:
            RuntimeError: If any embedding generation returns null/empty vector
        """
        texts = [item[text_key] for item in items]
        vectors = await self._provider.embed_batch(texts)

        # VALIDATION: Reject null/empty embeddings (GMP-132)
        for idx, vector in enumerate(vectors):
            if vector is None or len(vector) == 0:
                logger.error(
                    "batch_embed_and_store returned null/empty vector",
                    item_index=idx,
                    text_preview=texts[idx][:100],
                )
                raise RuntimeError(
                    f"Embedding generation returned null/empty vector for item {idx}"
                )

        embedding_ids = []
        for item, vector in zip(items, vectors, strict=False):
            text = item.pop(text_key)
            enriched_payload = {
                **item,
                "_text": text,
                "_model": getattr(self._provider, "_model", "unknown"),
            }
            embedding_id = await self._repository.insert_semantic_embedding(
                vector=vector,
                payload=enriched_payload,
                agent_id=agent_id,
            )
            embedding_ids.append(str(embedding_id))

        return embedding_ids

    # =========================================================================
    # Spec v3.0 Required Methods (memory_spec_v3.0.yaml compliance)
    # =========================================================================

    @must_stay_async("callers use await")
    async def store_embedding(
        self,
        vector: list[float],
        metadata: dict[str, Any],
        embedding_type: str = "content",
    ) -> str:
        """
        Store a pre-computed embedding vector with metadata.

        Spec: semantic.embedding_storage.store_embedding

        Args:
            vector: Pre-computed embedding vector
            metadata: Metadata to store with embedding
            embedding_type: Type of embedding (content, entity, summary, reasoning)

        Returns:
            embedding_id as string (UUID)
        """
        enriched_payload = {
            **metadata,
            "_embedding_type": embedding_type,
            "_model": getattr(self._provider, "_model", "unknown"),
        }

        embedding_id = await self._repository.insert_semantic_embedding(
            vector=vector,
            payload=enriched_payload,
            agent_id=metadata.get("agent_id"),
        )

        logger.debug(f"Stored embedding {embedding_id} (type={embedding_type})")
        return str(embedding_id)

    async def recall_similar(
        self,
        query_vector: list[float],
        top_k: int = 10,
        embedding_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recall similar embeddings by vector similarity.

        Spec: semantic.embedding_storage.recall_similar

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            embedding_type: Optional filter by embedding type

        Returns:
            List of hits with embedding_id, score, payload
        """
        hits = await self._repository.search_semantic_memory(
            query_embedding=query_vector,
            top_k=top_k,
            agent_id=None,  # No agent filter for recall
        )

        results = []
        for hit in hits:
            hit_dict = hit.model_dump()
            # Filter by embedding_type if specified
            if embedding_type:
                payload = hit_dict.get("payload", {})
                if payload.get("_embedding_type") != embedding_type:
                    continue
            results.append(hit_dict)

        logger.debug(f"Recalled {len(results)} similar embeddings")
        return results

    @must_stay_async("callers use await")
    async def batch_store_embeddings(
        self,
        embeddings: list[dict[str, Any]],
    ) -> list[str]:
        """
        Store multiple pre-computed embeddings.

        Spec: semantic.embedding_storage.batch_store_embeddings

        Args:
            embeddings: List of dicts with 'vector', 'metadata', optional 'embedding_type'

        Returns:
            List of embedding_ids
        """
        embedding_ids = []
        for emb in embeddings:
            vector = emb["vector"]
            metadata = emb.get("metadata", {})
            embedding_type = emb.get("embedding_type", "content")

            emb_id = await self.store_embedding(
                vector=vector,
                metadata=metadata,
                embedding_type=embedding_type,
            )
            embedding_ids.append(emb_id)

        logger.debug(f"Batch stored {len(embedding_ids)} embeddings")
        return embedding_ids

    @must_stay_async("callers use await")
    async def hybrid_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search combining semantic similarity with metadata filters.

        Spec: semantic.semantic_recall.hybrid_search

        Args:
            query: Natural language query
            filters: Optional metadata filters (e.g., {"agent_id": "...", "packet_type": "..."})
            top_k: Number of results

        Returns:
            List of hits with embedding_id, score, payload
        """
        # Generate query embedding
        query_vector = await self._provider.embed_text(query)

        # Get semantic results
        hits = await self._repository.search_semantic_memory(
            query_embedding=query_vector,
            top_k=top_k * 2,  # Over-fetch for filtering
            agent_id=filters.get("agent_id") if filters else None,
        )

        results = []
        for hit in hits:
            hit_dict = hit.model_dump()
            payload = hit_dict.get("payload", {})

            # Apply metadata filters
            if filters:
                match = True
                for key, value in filters.items():
                    if key == "agent_id":
                        continue  # Already filtered in query
                    if payload.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(hit_dict)
            if len(results) >= top_k:
                break

        logger.debug(f"Hybrid search found {len(results)} results for: {query[:50]}...")
        return results

    @must_stay_async("callers use await")
    async def rerank_by_relevance(
        self,
        hits: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Rerank search hits by relevance to context.

        Spec: semantic.similarity_ranking.rerank_by_relevance

        Uses a simple heuristic reranking based on:
        - Recency (newer = higher)
        - Embedding type match
        - Agent match

        Args:
            hits: List of search hits to rerank
            context: Context dict with optional 'preferred_embedding_type', 'agent_id', 'recency_weight'

        Returns:
            Reranked list of hits (highest relevance first)
        """
        preferred_type = context.get("preferred_embedding_type")
        preferred_agent = context.get("agent_id")
        recency_weight = context.get("recency_weight", 0.1)

        def score_hit(hit: dict[str, Any]) -> float:
            """
            Calculates a relevance score for a search hit based on embedding type and payload attributes.

            Args:
                hit: Dictionary representing a search result hit with score and payload data.

            Returns:
                A float representing the computed relevance score for the hit.
            """
            base_score = hit.get("score", 0.5)
            payload = hit.get("payload", {})

            # Boost for matching embedding type
            if preferred_type and payload.get("_embedding_type") == preferred_type:
                base_score += 0.1

            # Boost for matching agent
            if preferred_agent and payload.get("agent_id") == preferred_agent:
                base_score += 0.05

            # Recency boost (if timestamp available)
            timestamp = payload.get("timestamp") or payload.get("created_at")
            if timestamp and recency_weight > 0:
                # Simple recency: more recent = small boost
                # This is a placeholder - production would use actual time diff
                base_score += recency_weight * 0.1

            return base_score

        # Sort by computed relevance score
        ranked = sorted(hits, key=score_hit, reverse=True)
        logger.debug(f"Reranked {len(ranked)} hits")
        return ranked


# =============================================================================
# Factory Functions
# =============================================================================


def create_embedding_provider(
    provider_type: str = "openai",
    model: str = "text-embedding-3-large",
    dimensions: int = EMBEDDING_DIMENSIONS,
    api_key: str | None = None,
) -> EmbeddingProvider:
    """
    Factory function to create embedding provider.

    Args:
        provider_type: "openai" or "stub"
        model: Model name for OpenAI
        dimensions: Vector dimensions
        api_key: API key for OpenAI

    Returns:
        EmbeddingProvider instance
    """
    if provider_type == "stub":
        raise RuntimeError("Stub embedding provider is not allowed in enforcement mode")
    if provider_type == "openai":
        logger.info(f"Using OpenAI embedding provider: {model}")
        return OpenAIEmbeddingProvider(
            model=model,
            dimensions=dimensions,
            api_key=api_key,
        )
    raise ValueError(f"Unknown provider type: {provider_type}")


# Convenience function for direct use
@must_stay_async("callers use await")
async def embed_text(
    text: str,
    provider: EmbeddingProvider | None = None,
    model: str = "text-embedding-3-large",
    api_key: str | None = None,
) -> list[float]:
    """
    Standalone function to embed text.

    Creates a provider if not provided.

    Args:
        text: Text to embed
        provider: Optional pre-configured provider
        model: Model name if creating provider
        api_key: API key if creating provider

    Returns:
        Embedding vector
    """
    if provider is None:
        if api_key:
            provider = OpenAIEmbeddingProvider(model=model, api_key=api_key)
        else:
            raise RuntimeError("Embedding provider required; missing API key")

    return await provider.embed_text(text)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-026",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "batch-processing",
        "debugging",
        "learning",
        "llm",
        "logging",
        "memory-substrate",
        "security",
        "service",
    ],
    "keywords": [
        "batch",
        "create",
        "dimensions",
        "embed",
        "embedding",
        "embeddings",
        "generate",
        "hit",
    ],
    "business_value": "Provides a pluggable embedding provider interface.",
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
