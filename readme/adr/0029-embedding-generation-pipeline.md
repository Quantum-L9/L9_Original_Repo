# ADR 0029: Embedding Generation Pipeline

## Status
Accepted

## Pattern
Embeddings via OpenAI `text-embedding-3-small`; 1536 dimensions; stored in pgvector.

## Files
- `mcp_memory/src/embeddings.py` - Embedding generation
- `memory/substrate_semantic.py` - Semantic operations
- `core/tools/tool_embeddings.py` - Tool embeddings
- `config/memory_substrate_settings.py` - Config

## Import Block
```python
from openai import AsyncOpenAI
import numpy as np
from typing import Sequence
```

## Minimal Implementation
```python
from openai import AsyncOpenAI
from typing import Sequence
import structlog

logger = structlog.get_logger(__name__)

# Configuration constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 100

# Singleton client
_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get OpenAI client singleton."""
    global _client
    if _client is None:
        _client = AsyncOpenAI()  # Uses OPENAI_API_KEY env var
    return _client


async def embed_text(text: str) -> list[float]:
    """
    Generate embedding for single text.
    
    Args:
        text: Text to embed
    
    Returns:
        1536-dimensional embedding vector
    """
    client = get_openai_client()
    
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    
    embedding = response.data[0].embedding
    
    logger.debug(
        "embedding.generated",
        model=EMBEDDING_MODEL,
        dimensions=len(embedding),
    )
    
    return embedding


async def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    """
    Generate embeddings for batch of texts.
    
    Args:
        texts: Texts to embed (max 100 per batch)
    
    Returns:
        List of 1536-dimensional embedding vectors
    """
    if len(texts) > EMBEDDING_BATCH_SIZE:
        raise ValueError(
            f"Batch size {len(texts)} exceeds max {EMBEDDING_BATCH_SIZE}"
        )
    
    client = get_openai_client()
    
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=list(texts),
        dimensions=EMBEDDING_DIMENSIONS,
    )
    
    embeddings = [e.embedding for e in response.data]
    
    logger.info(
        "embedding.batch_generated",
        count=len(embeddings),
        model=EMBEDDING_MODEL,
    )
    
    return embeddings


async def embed_large_batch(texts: Sequence[str]) -> list[list[float]]:
    """Embed large batch by chunking into smaller batches."""
    all_embeddings = []
    
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        embeddings = await embed_batch(batch)
        all_embeddings.extend(embeddings)
    
    return all_embeddings
```

## Usage Example
```python
from mcp_memory.src.embeddings import embed_text, embed_batch

# Single embedding
text = "User prefers dark mode and vim keybindings"
embedding = await embed_text(text)
# Returns: [0.123, -0.456, ...] (1536 floats)

# Batch embedding (up to 100)
texts = [
    "First document",
    "Second document",
    "Third document",
]
embeddings = await embed_batch(texts)
# Returns: [[...], [...], [...]] (3 x 1536 floats)

# Store in pgvector
await conn.execute(
    """
    INSERT INTO semantic_memory (content, vector, embedding_type)
    VALUES ($1, $2, $3)
    """,
    text,
    embedding,  # pgvector accepts list[float]
    "content",
)

# Similarity search
results = await conn.fetch(
    """
    SELECT content, 1 - (vector <=> $1) as similarity
    FROM semantic_memory
    WHERE 1 - (vector <=> $1) > 0.7
    ORDER BY similarity DESC
    LIMIT 10
    """,
    query_embedding,
)
```

## Anti-Pattern Example
```python
# ❌ WRONG — Different embedding model
await client.embeddings.create(
    model="text-embedding-ada-002",  # Wrong model!
    input=text,
)

# ❌ WRONG — Different dimensions
await client.embeddings.create(
    model="text-embedding-3-small",
    input=text,
    dimensions=512,  # Wrong dimensions!
)

# ❌ WRONG — Batch too large
texts = ["text"] * 200  # 200 > 100 max!
await embed_batch(texts)

# ❌ WRONG — Sync call
response = client.embeddings.create(...)  # Missing await!

# ✅ CORRECT — Standard config
await client.embeddings.create(
    model="text-embedding-3-small",
    input=text,
    dimensions=1536,
)
```

## Storage Schema
```sql
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Semantic memory table
CREATE TABLE semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    vector vector(1536) NOT NULL,  -- 1536 dimensions
    embedding_type TEXT DEFAULT 'content',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX ON semantic_memory 
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Embedding Types
| Type | Purpose | Table |
|------|---------|-------|
| content | Main text content | semantic_memory |
| summary | Condensed summaries | memory_summaries |
| entity | Entity names | entity_relationships |
| reasoning | Reasoning traces | reasoning_traces |
| tool | Tool descriptions | tool_embeddings |

## Rules
1. ALWAYS use `text-embedding-3-small`
2. ALWAYS use 1536 dimensions
3. Batch embeddings when possible (max 100)
4. Store `embedding_type` for filtering
5. Use cosine similarity (`<=>`) for search

## AI Guidance
**DO:**
- Use `text-embedding-3-small` model
- Set `dimensions=1536` explicitly
- Batch requests (max 100 texts)
- Store embedding_type metadata

**DO NOT:**
- Use other embedding models
- Change dimension count
- Generate embeddings synchronously
- Skip batching for large sets
