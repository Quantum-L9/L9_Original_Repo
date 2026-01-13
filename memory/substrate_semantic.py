"""
L9 Memory Substrate - Semantic Layer
Version: 1.0.0

Embedding generation and vector search helpers.
Provides a pluggable embedding provider interface.

# bound to memory-yaml2.0 semantic layer
"""

import asyncio
import random
import structlog
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
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
        api_key: Optional[str] = None,
        max_retries: int = 3,
        base_backoff: float = 0.5,
    ):
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
                )
        return self._client

    async def _with_retries(self, coro, *, operation: str) -> list[float] | list[list[float]]:
        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro()
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
                    error=str(exc),
                    delay=delay,
                )
                await asyncio.sleep(delay + jitter)
        raise RuntimeError(f"Embedding request failed after retries: {last_error}") from last_error

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API."""
        client = self._get_client()

        async def _embed() -> list[float]:
            response = await client.embeddings.create(
                model=self._model,
                input=text,
                dimensions=self._dimensions,
            )
            return response.data[0].embedding

        return await self._with_retries(_embed, operation="embed_text")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for batch of texts."""
        client = self._get_client()

        async def _embed() -> list[list[float]]:
            response = await client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]

        return await self._with_retries(_embed, operation="embed_batch")

    @property
    def dimensions(self) -> int:
        return self._dimensions


class StubEmbeddingProvider(EmbeddingProvider):
    """
    Stub embedding provider for testing without API calls.

    Generates deterministic pseudo-random vectors based on text hash.
    """

    def __init__(self, dimensions: int = 1536):
        self._dimensions = dimensions

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
        return self._dimensions


class SemanticService:
    """
    Service for semantic operations on the memory substrate.

    Wraps embedding provider and repository for semantic search.

    # bound to memory-yaml2.0 semantic layer (embedding_storage, semantic_recall, similarity_ranking)
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        repository: Any,  # SubstrateRepository
    ):
        """
        Initialize semantic service.

        Args:
            embedding_provider: Provider for generating embeddings
            repository: SubstrateRepository instance for DB access
        """
        self._provider = embedding_provider
        self._repository = repository

    async def embed_and_store(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> str:
        """
        Generate embedding for text and store in semantic_memory.

        Args:
            text: Text to embed
            payload: Metadata payload to store with embedding
            agent_id: Optional agent identifier

        Returns:
            embedding_id as string
        """
        logger.debug(f"Generating embedding for text: {text[:100]}...")

        # Generate embedding
        vector = await self._provider.embed_text(text)

        # Enrich payload with original text
        enriched_payload = {
            **payload,
            "_text": text,
            "_model": getattr(self._provider, "_model", "unknown"),
        }

        # Store in database
        embedding_id = await self._repository.insert_semantic_embedding(
            vector=vector,
            payload=enriched_payload,
            agent_id=agent_id,
        )

        logger.debug(f"Stored embedding {embedding_id}")
        return str(embedding_id)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search semantic memory for similar content.

        Args:
            query: Natural language query
            top_k: Number of results
            agent_id: Optional filter by agent

        Returns:
            List of hits with embedding_id, score, payload
        """
        logger.debug(f"Semantic search: {query[:100]}...")

        # Generate query embedding
        query_vector = await self._provider.embed_text(query)

        # Search database
        hits = await self._repository.search_semantic_memory(
            query_embedding=query_vector,
            top_k=top_k,
            agent_id=agent_id,
        )

        logger.debug(f"Found {len(hits)} results")
        return [hit.model_dump() for hit in hits]

    async def batch_embed_and_store(
        self,
        items: list[dict[str, Any]],
        text_key: str = "text",
        agent_id: Optional[str] = None,
    ) -> list[str]:
        """
        Embed and store multiple items.

        Args:
            items: List of dicts with text and payload
            text_key: Key in dict containing text to embed
            agent_id: Optional agent identifier

        Returns:
            List of embedding_ids
        """
        texts = [item[text_key] for item in items]
        vectors = await self._provider.embed_batch(texts)

        embedding_ids = []
        for item, vector in zip(items, vectors):
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


# =============================================================================
# Factory Functions
# =============================================================================


def create_embedding_provider(
    provider_type: str = "openai",
    model: str = "text-embedding-3-large",
    dimensions: int = 1536,
    api_key: Optional[str] = None,
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
        logger.info("Using stub embedding provider")
        return StubEmbeddingProvider(dimensions=dimensions)
    elif provider_type == "openai":
        logger.info(f"Using OpenAI embedding provider: {model}")
        return OpenAIEmbeddingProvider(
            model=model,
            dimensions=dimensions,
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


# Convenience function for direct use
async def embed_text(
    text: str,
    provider: Optional[EmbeddingProvider] = None,
    model: str = "text-embedding-3-large",
    api_key: Optional[str] = None,
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
            # Default to stub if no API key
            logger.warning("No API key provided, using stub embeddings")
            provider = StubEmbeddingProvider()

    return await provider.embed_text(text)
