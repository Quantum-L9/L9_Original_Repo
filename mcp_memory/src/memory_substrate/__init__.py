"""L9 Memory Substrate - Semantic Storage & Retrieval.

Bounded Context: Memory Substrate
Domain: Semantic/vector search, graph storage, working memory.
Owner: L (CTO)

Memory Substrate is responsible for:
  1. Vector embeddings (OpenAI/local models)
  2. Semantic search over knowledge bases
  3. Temporal memory operations (decay, TTL)
  4. Graph relationships (Neo4j integration)
  5. Memory lifecycle (save, search, delete, compound)

Memory Substrate MUST implement:
  - SubstrateService interface
  - Adapter pattern for embedding providers
  - Abstract repository layer (no direct SQL)

Memory Substrate MUST NOT:
  - Enforce safety policies (Safety does that)
  - Implement business logic (Orchestrator does that)
  - Manage user auth (Kernel/Safety do that)

Memory operations flow through PacketEnvelope (kernel.protocol).
"""

from memory_substrate.service import SubstrateService, SubstrateConfig
from memory_substrate.repository import AbstractMemoryRepository

__all__ [
    "SubstrateService",
    "SubstrateConfig",
    "AbstractMemoryRepository",
]
