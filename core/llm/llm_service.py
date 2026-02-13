"""
L9 LLMService Implementations

Unified LLM interfaces implementing the LLMService protocol.

Provides:
- OpenAILLMService: OpenAI GPT models
- MockLLMService: Testing implementation

Version: 1.0.0
GMP: GMP-116-llm-service-implementation
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "LLMService Implementations",
    "module_version": "1.0.0",
    "created_by": "GMP-116",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-01-24T00:00:00Z",
    "layer": "service",
    "domain": "llm",
    "module_name": "llm_service",
    "type": "service",
    "status": "active",
    "adr": ["ADR-0026"],
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI", "Anthropic"],
        "memory_layers": [],
        "imported_by": [
            "core.llm.__init__",
            "core.di.container",
            "agents",
            "orchestrators",
        ],
    },
}
# ============================================================================

import asyncio
import os
from typing import TYPE_CHECKING, Any

import structlog

from core.protocols import LLMService

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)

# Default models
DEFAULT_CHAT_MODEL = "gpt-4o"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"


def get_default_model() -> str:
    """Get the default chat model."""
    return os.getenv("OPENAI_MODEL", DEFAULT_CHAT_MODEL)


class OpenAILLMService:
    """
    LLMService implementation using OpenAI API.

    Provides unified interface for:
    - Text completion (chat completions API)
    - Chat completion (multi-turn conversations)
    - Text embeddings

    Usage:
        from core.llm import OpenAILLMService

        llm = OpenAILLMService()
        response = await llm.complete("Explain quantum computing")
        embedding = await llm.embed("Some text to embed")
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        default_embedding_model: str | None = None,
    ) -> None:
        """
        Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            default_model: Default chat model (defaults to gpt-4o)
            default_embedding_model: Default embedding model
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self._api_key:
            raise RuntimeError(
                "OpenAI API key required. Set OPENAI_API_KEY or pass api_key parameter."
            )

        self._default_model = default_model or get_default_model()
        self._default_embedding_model = default_embedding_model or os.getenv(
            "OPENAI_EMBED_MODEL", DEFAULT_EMBEDDING_MODEL
        )

        # Lazy client initialization with thread-safe lock
        self._client: AsyncOpenAI | None = None
        self._client_lock = asyncio.Lock()

        logger.info(
            "OpenAILLMService initialized",
            default_model=self._default_model,
            embedding_model=self._default_embedding_model,
        )

    @must_stay_async("callers use await")
    async def _get_client(self) -> AsyncOpenAI:
        """Get or create AsyncOpenAI client (thread-safe)."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    try:
                        from openai import AsyncOpenAI

                        self._client = AsyncOpenAI(api_key=self._api_key)
                    except ImportError as e:
                        raise RuntimeError(
                            "openai package required for OpenAILLMService. "
                            "Install with: pip install openai"
                        ) from e
        return self._client

    async def close(self) -> None:
        """Close the underlying OpenAI client to release resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("OpenAILLMService client closed")

    @must_stay_async("callers use await")
    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            model: Model identifier (uses default if None)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        client = self._get_client()
        model_name = model or self._default_model

        logger.debug(
            "llm_complete_request",
            model=model_name,
            prompt_length=len(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = response.choices[0].message.content or ""

        logger.info(
            "llm_complete_response",
            model=model_name,
            response_length=len(result),
            usage_prompt=response.usage.prompt_tokens if response.usage else None,
            usage_completion=(
                response.usage.completion_tokens if response.usage else None
            ),
        )

        return result

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model identifier (uses default if None)
            temperature: Sampling temperature

        Returns:
            Generated response text
        """
        client = await self._get_client()
        model_name = model or self._default_model

        logger.debug(
            "llm_chat_request",
            model=model_name,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Validate message format
        validated_messages: list[dict[str, Any]] = []
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content' keys")
            validated_messages.append(
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

        response = await client.chat.completions.create(
            model=model_name,
            messages=validated_messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = response.choices[0].message.content or ""

        logger.info(
            "llm_chat_response",
            model=model_name,
            response_length=len(result),
            usage_prompt=response.usage.prompt_tokens if response.usage else None,
            usage_completion=(
                response.usage.completion_tokens if response.usage else None
            ),
        )

        return result

    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """
        Generate text embedding vector.

        Args:
            text: Input text to embed
            model: Embedding model identifier (uses default if None)

        Returns:
            Embedding vector as list of floats
        """
        client = await self._get_client()
        model_name = model or self._default_embedding_model

        logger.debug(
            "llm_embed_request",
            model=model_name,
            text_length=len(text),
        )

        response = await client.embeddings.create(
            model=model_name,
            input=text,
            dimensions=1536,  # Truncate to match DB VECTOR(1536) schema
        )

        embedding = response.data[0].embedding

        logger.info(
            "llm_embed_response",
            model=model_name,
            embedding_dimensions=len(embedding),
        )

        return embedding


class MockLLMService:
    """
    Mock LLMService for testing.

    Returns predictable responses without calling any external API.

    Usage:
        llm = MockLLMService()
        response = await llm.complete("Test prompt")  # Returns "[mock completion]..."
    """

    def __init__(
        self,
        default_completion: str = "[mock completion]",
        default_embedding: list[float] | None = None,
    ) -> None:
        """
        Initialize mock LLM service.

        Args:
            default_completion: Default text to return for completions
            default_embedding: Default embedding vector (generates zeros if None)
        """
        self._default_completion = default_completion
        # text-embedding-3 has 1536 dimensions
        self._default_embedding = default_embedding or [0.0] * 1536

        logger.info("MockLLMService initialized")

    @must_stay_async("callers use await")
    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Return mock completion."""
        return f"{self._default_completion} (prompt_length={len(prompt)})"

    @must_stay_async("callers use await")
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Return mock chat response."""
        return f"{self._default_completion} (messages={len(messages)})"

    @must_stay_async("callers use await")
    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """Return mock embedding."""
        return self._default_embedding.copy()


def create_llm_service(
    provider: str = "openai",
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMService:
    """
    Factory function to create LLMService implementation.

    Args:
        provider: LLM provider ("openai", "mock")
        api_key: API key for the provider
        **kwargs: Additional provider-specific arguments

    Returns:
        LLMService implementation

    Raises:
        ValueError: If provider is not supported
    """
    if provider == "openai":
        return OpenAILLMService(api_key=api_key, **kwargs)
    if provider == "mock":
        return MockLLMService(**kwargs)
    raise ValueError(f"Unsupported LLM provider: {provider}")


# Type assertion: implementations satisfy LLMService protocol
def _check_protocol_compliance() -> None:
    """Verify implementations satisfy LLMService protocol at import time."""
    openai_impl: LLMService = OpenAILLMService.__new__(OpenAILLMService)  # type: ignore[assignment]
    mock_impl: LLMService = MockLLMService.__new__(MockLLMService)  # type: ignore[assignment]
    _ = (openai_impl, mock_impl)


_check_protocol_compliance()


__all__ = [
    "DEFAULT_CHAT_MODEL",
    "DEFAULT_EMBEDDING_MODEL",
    "MockLLMService",
    "OpenAILLMService",
    "create_llm_service",
    "get_default_model",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-031",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.protocols"],
    "tags": [
        "api",
        "async",
        "core",
        "debugging",
        "foundation",
        "llm",
        "logging",
        "messaging",
        "mocking",
        "service",
    ],
    "keywords": [
        "chat",
        "complete",
        "create",
        "default",
        "embed",
        "implementation",
        "llm",
        "llmservice",
    ],
    "business_value": "OpenAILLMService: OpenAI GPT models MockLLMService: Testing implementation Version: 1.0.0 GMP: GMP-116-llm-service-implementation",
    "last_modified": "2026-01-24T15:21:11Z",
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
