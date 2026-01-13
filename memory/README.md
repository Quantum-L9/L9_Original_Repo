# L9 Memory Substrate

> **Version:** 1.2.0  
> **Status:** Production  
> **Updated:** 2026-01-13

Hybrid memory + structured reasoning substrate for L9 using PostgreSQL + pgvector + Neo4j.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Memory Substrate v1.2                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Ingestion  │───▶│  Retrieval   │───▶│    Saga      │                  │
│  │   Pipeline   │    │   Pipeline   │    │   Patterns   │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌──────────────────────────────────────────────────────┐                  │
│  │                  MemorySubstrateService               │                  │
│  │  - write_packet()   - search()      - fetch_and_enrich()                │
│  │  - semantic_search() - health_check() - enrich_entities()               │
│  └──────────────────────────────────────────────────────┘                  │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐                      │
│  │ PostgreSQL │     │  pgvector  │     │   Neo4j    │                      │
│  │ (packets)  │     │(embeddings)│     │  (graph)   │                      │
│  └────────────┘     └────────────┘     └────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ingestion Flow (Simplified)

```
ingest_packet()
      ↓
IngestionPipeline.ingest()
      ↓
┌─────────────────────────┐
│ 1. Audit preprocessing  │  ← Injection detection, PII redaction
│ 2. Validation           │  ← PacketValidator (v2 schema)
│ 3. Auto-tagging         │
│ 4. packet_store (txn)   │  ← Transactional
│ 5. memory_events (txn)  │  ← Transactional
│ 6. Embeddings           │
│ 7. Neo4j sync           │
│ 8. Critical checkpoint  │
└─────────────────────────┘
```

> **Note:** DAG features (reasoning, insights, world model) are deferred for stability. Core pipeline only.

---

## Quick Start

```python
from memory.substrate_service import get_service
from core.schemas.packet_envelope_v2 import PacketEnvelopeIn  # v2 schema

# Get service instance (initialized at startup)
service = await get_service()

# Write a packet
packet = PacketEnvelopeIn(
    source_id="my_agent",
    agent_id="L",
    packet_type="reasoning",
    payload={"content": "Analysis of user request..."},
)
result = await service.write_packet(packet)

# Semantic search
from core.schemas.packet_envelope_v2 import SemanticSearchRequest
results = await service.semantic_search(SemanticSearchRequest(
    query="previous analysis",
    top_k=5,
))

# Cross-DB saga (vector + graph)
saga_result = await service.fetch_and_enrich(
    query="How does authentication work?",
    limit=10,
)
```

---

## Module Reference

### Core Services

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `substrate_service.py` | Main service facade | `MemorySubstrateService` |
| `substrate_repository.py` | Database access layer | `SubstrateRepository` |
| `substrate_semantic.py` | Embedding operations | `SemanticService`, `EmbeddingProvider` |
| `substrate_graph.py` | LangGraph DAG (deferred) | `SubstrateDAG` |

### Schemas (v2)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `core/schemas/packet_envelope_v2.py` | **Canonical schema** | `PacketEnvelope`, `PacketEnvelopeIn`, `PacketWriteResult` |
| `memory/substrate_models.py` | **Deprecated** (use v2) | Legacy models |

### Pipelines

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `ingestion.py` | **Primary ingestion** | `IngestionPipeline`, `ingest_packet()` |
| `retrieval.py` | Memory retrieval | `RetrievalPipeline` |
| `consolidation.py` | Memory hygiene & compaction | `ConsolidationPipeline` |
| `housekeeping.py` | Scheduled maintenance | `HousekeepingEngine` |

### Cross-DB Saga Pattern (v1.2)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `saga.py` | Multi-step execution framework | `Saga`, `SagaExecutor`, `SagaBuilder` |
| `saga_patterns.py` | Pre-built workflows | `SagaPatterns`, `fetch_and_enrich` |

### Specialized Services

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `hybrid_rag.py` | Vector + Graph search | `HybridRAGPipeline` |
| `query_classifier.py` | Adaptive query routing | `QueryClassifier` |
| `reasoning_replay.py` | Decision chain reconstruction | `ReasoningReplayPipeline` |
| `agent_persistence.py` | Agent checkpoint management | `AgentPersistenceService` |
| `strategymemory.py` | Strategy pattern storage | `StrategyMemoryService` |

### Graph & Search

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `graph_client.py` | Neo4j connection | `GraphClient` |
| `cypher_templates.py` | Parameterized Cypher queries | `CypherTemplateLibrary` |
| `schema_introspection.py` | Dynamic schema discovery | `SchemaIntrospector` |
| `semantic_search.py` | Vector similarity search | `SemanticSearchEngine` |

### Validators & Audit

| Module | Purpose |
|--------|---------|
| `validators/packet_validator.py` | Packet validation (v2 schema) |
| `audit_utils.py` | Injection detection, PII redaction |

---

## Core Concepts

### PacketEnvelope (v2 Schema)

The fundamental unit of memory storage:

```python
from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

packet = PacketEnvelopeIn(
    source_id="slack_webhook",      # Origin of the packet
    agent_id="L",                   # Which agent owns this
    thread_id="conv_123",           # Conversation thread
    packet_type="reasoning",        # Type: reasoning, tool_call, decision, etc.
    payload={                       # Arbitrary JSON payload
        "content": "...",
        "confidence": 0.95,
    },
    metadata={                      # Additional context
        "channel": "#general",
        "user": "igor",
    },
    tags=["important", "decision"], # Searchable tags
)
```

### Saga Pattern (Cross-DB Operations)

Bundles related database operations into atomic workflows:

```python
from memory.substrate_service import get_service

service = await get_service()

# Vector search → Entity extraction → Graph enrichment
result = await service.fetch_and_enrich(
    query="How does authentication work?",
    limit=10,
    min_similarity=0.5,
)

# Access results
print(f"Status: {result.status}")
print(f"Vector hits: {len(result.output['vector_hits'])}")
print(f"Entities: {len(result.output['extracted_entities'])}")
print(f"Relationships: {len(result.output['relationships'])}")
```

### Hybrid RAG

Combines vector similarity with graph relationships:

```python
from memory import hybrid_search

results = await hybrid_search(
    query="What decisions were made about authentication?",
    strategy="vector_then_graph",  # or "graph_then_vector", "parallel"
    limit=10,
)

for hit in results.hits:
    print(f"Score: {hit.score}, Content: {hit.content[:100]}")
```

### Agent Persistence

Checkpoint and restore agent state:

```python
service = await get_service()
persistence = service.get_agent_persistence()

# Create checkpoint
checkpoint_id = await persistence.create_checkpoint(
    agent_id="my_agent",
    state={"step": 5, "context": {...}},
    reason="on_critical_decision",
)

# Restore latest checkpoint
state = await persistence.restore_checkpoint(agent_id="my_agent")
```

---

## Database Schema

### PostgreSQL Tables

| Table | Purpose |
|-------|---------|
| `packet_store` | Main packet storage (22 columns) |
| `semantic_memory` | Vector embeddings (pgvector) |
| `knowledge_facts` | Extracted facts |
| `agent_checkpoints` | Agent state snapshots |
| `agent_memory_events` | Memory events log |
| `tasks` | Background task queue |

### Neo4j Node Types

| Node | Purpose |
|------|---------|
| `:Event` | Memory packets/events |
| `:Entity` | Extracted entities |
| `:Agent` | Agent nodes |
| `:Thread` | Conversation threads |
| `:Decision` | Decision records |

---

## Configuration

Environment variables:

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/l9_memory
MEMORY_DSN=postgresql://user:pass@host:5432/l9_memory

# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Embeddings
EMBEDDING_PROVIDER=openai  # or "stub" for testing
OPENAI_API_KEY=sk-...

# Redis (optional, for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## API Endpoints

Memory-related API routes (via `api/memory/router.py`):

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/memory/packet` | POST | Ingest a packet |
| `/memory/packet/{id}` | GET | Retrieve packet |
| `/memory/semantic/search` | POST | Semantic search |
| `/memory/thread/{id}` | GET | Get thread packets |
| `/memory/lineage/{id}` | GET | Get packet lineage |
| `/memory/hybrid/search` | POST | Hybrid (vector + filters) search |
| `/memory/health` | GET | Health check |
| `/memory/stats` | GET | Memory statistics |

### Saga Endpoints (v1.2)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/memory/saga/fetch-and-enrich` | POST | Vector → Entity → Graph enrichment |
| `/memory/saga/enrich-entities` | POST | Entity lookup → Relationships |
| `/memory/saga/correlate-timeline` | POST | Event timeline → Causal chains |

### Advanced Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/memory/reasoning/replay` | POST | Reconstruct decision chain |
| `/memory/consolidation/run` | POST | Trigger consolidation |
| `/memory/gc/run` | POST | Run garbage collection |
| `/memory/facts` | GET | Query knowledge facts |
| `/memory/insights` | GET | Query extracted insights |

---

## Testing

```bash
# Run memory tests
pytest tests/memory/ -v

# Run validation tests (v2 schema)
pytest tests/memory/test_packet_validation_v2.py -v

# Run saga tests
pytest tests/memory/test_saga.py -v

# Run smoke test
python -m memory.smoke_test

# Integration tests
pytest tests/integration/test_orchestrator_memory_integration.py
```

---

## Migration from substrate_models

**GMP-63** migrated 88 files from `memory.substrate_models` to `core.schemas.packet_envelope_v2`.

### Before (deprecated)
```python
from memory.substrate_models import PacketEnvelopeIn  # ❌ Deprecated
```

### After (canonical)
```python
from core.schemas.packet_envelope_v2 import PacketEnvelopeIn  # ✅ Use this
```

### Migration Script
```bash
python scripts/migrate_substrate_models.py --dry-run  # Preview
python scripts/migrate_substrate_models.py            # Execute
```

---

## Related Documentation

- [MCP Memory Capsule](../mcp_memory/README.md) — MCP server integration
- [Memory Spec v3.0](./memory_spec_v3.0.yaml) — Schema specification
- [Audit Report](../reports/AUDIT_PacketEnvelope_PacketStore_Integration.md) — Integration audit

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-01-13 | Schema migration to v2, Simplified ingestion (IngestionPipeline only), Saga pattern integration, Audit mode (injection detection) |
| 1.1.0 | 2026-01-12 | Hybrid RAG, Cypher templates, Schema introspection |
| 1.0.0 | 2026-01-01 | Initial production release |
| 0.9.0 | 2025-12-15 | Query classification, Reasoning replay |
| 0.8.0 | 2025-12-01 | Agent persistence, Consolidation |

---

*Memory Substrate — The persistent layer of L9 intelligence*
