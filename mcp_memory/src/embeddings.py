"""
OpenAI embedding generation.
"""

import structlog
from typing import List
from openai import AsyncOpenAI
from src.config import settings

logger = structlog.get_logger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> List[float]:
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise


async def embed_texts(texts: List[str]) -> List[List[float]]:
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        raise
