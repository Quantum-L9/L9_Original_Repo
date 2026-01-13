"""
MCP Memory Server - OpenAI Embedding Generation
================================================

Generates embeddings using OpenAI API with retry logic.

Version: 2.0.0
- Added retry logic with exponential backoff (3 retries, 0.5s base)
"""

import asyncio
import random
import structlog
from typing import List
from openai import AsyncOpenAI
from src.config import settings

logger = structlog.get_logger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Retry configuration
MAX_RETRIES = 3
BASE_BACKOFF = 0.5  # seconds


async def _with_retries(coro_func, *, operation: str):
    """
    Execute async function with retry logic and exponential backoff.

    Args:
        coro_func: Async function to execute
        operation: Name of operation for logging

    Returns:
        Result from successful coro_func() call

    Raises:
        RuntimeError: If all retries exhausted
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_func()
        except Exception as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            delay = BASE_BACKOFF * (2 ** (attempt - 1))
            jitter = random.random() * 0.1
            logger.warning(
                "Embedding request failed, retrying",
                operation=operation,
                attempt=attempt,
                max_retries=MAX_RETRIES,
                error=str(exc),
                delay=round(delay + jitter, 3),
            )
            await asyncio.sleep(delay + jitter)

    logger.error(
        "Embedding request failed after retries",
        operation=operation,
        attempts=MAX_RETRIES,
        error=str(last_error),
    )
    raise RuntimeError(f"Embedding request failed after {MAX_RETRIES} retries: {last_error}") from last_error


async def embed_text(text: str) -> List[float]:
    """Generate embedding for single text with retry logic."""

    async def _embed() -> List[float]:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding

    return await _with_retries(_embed, operation="embed_text")


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for batch of texts with retry logic."""

    async def _embed() -> List[List[float]]:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    return await _with_retries(_embed, operation="embed_texts")
