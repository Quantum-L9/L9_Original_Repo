# PacketEnvelope & PacketStore Architecture

**Version:** 2.0.0
**Updated:** 2026-01-13
**Spec:** `memory_spec_v3.0.yaml`

---

## Overview

**PacketEnvelope** is L9's canonical immutable event container. Every piece of data flowing through the memory system—events, insights, reasoning traces, tool calls—is wrapped in a `PacketEnvelope` and stored in the `packet_store` table.

**PacketStore** is the PostgreSQL table that serves as the central event log for all memory operations.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              L9 MEMORY SUBSTRATE ARCHITECTURE                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────────┐
                                    │   ENTRY POINTS   │
                                    └────────┬─────────┘
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        │                                    │                                    │
        ▼                                    ▼                                    ▼
┌───────────────────┐            ┌───────────────────┐            ┌───────────────────┐
│   HTTP API        │            │   MCP-Memory      │            │   Agent Direct    │
│ POST /api/memory  │            │   Server (stdio)  │            │   l_cto.py        │
│     /packet       │            │   save_memory()   │            │   base_agent.py   │
└─────────┬─────────┘            └─────────┬─────────┘            └─────────┬─────────┘
          │                                │                                │
          └────────────────────────────────┼────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  CANONICAL ENTRYPOINT                                           │
│                                                                                                 │
│                              ┌─────────────────────────────┐                                    │
│                              │     ingest_packet()         │                                    │
│                              │  memory/ingestion.py:557    │                                    │
│                              └──────────────┬──────────────┘                                    │
│                                             │                                                   │
│                                             ▼                                                   │
│                              ┌─────────────────────────────┐                                    │
│                              │  PacketEnvelopeIn.to_       │                                    │
│                              │     envelope()              │                                    │
│                              │  (Creates immutable packet) │                                    │
│                              └──────────────┬──────────────┘                                    │
└─────────────────────────────────────────────┼───────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               MEMORY SUBSTRATE SERVICE                                          │
│                                                                                                 │
│                              ┌─────────────────────────────┐                                    │
│                              │  MemorySubstrateService     │                                    │
│                              │  .write_packet()            │                                    │
│                              │  memory/substrate_service   │                                    │
│                              └──────────────┬──────────────┘                                    │
│                                             │                                                   │
│                                             ▼                                                   │
│                              ┌─────────────────────────────┐                                    │
│                              │     PacketValidator         │                                    │
│                              │  .validate()                │                                    │
│                              │  (Whitelist enforcement)    │                                    │
│                              └──────────────┬──────────────┘                                    │
└─────────────────────────────────────────────┼───────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               LANGGRAPH DAG PIPELINE                                            │
│                               (memory/substrate_dag.py)                                         │
│                                                                                                 │
│    ┌─────────┐    ┌─────────────┐    ┌─────────────────┐    ┌───────────────┐    ┌──────────┐  │
│    │ intake  │───▶│  reasoning  │───▶│  memory_write   │───▶│ semantic_embed│───▶│checkpoint│  │
│    │  node   │    │    node     │    │      node       │    │     node      │    │   node   │  │
│    └─────────┘    └─────────────┘    └────────┬────────┘    └───────┬───────┘    └────┬─────┘  │
│         │               │                     │                     │                  │        │
│         │               │                     │                     │                  │        │
│         ▼               ▼                     ▼                     ▼                  ▼        │
│    Parse packet    Add reasoning      Write to DB          Generate embeddings   Save state    │
│    Validate        block if needed    via Repository       Store in pgvector     to checkpoint │
└─────────────────────────────────────────────┼───────────────────────┼──────────────────┼────────┘
                                              │                       │                  │
                                              ▼                       ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   REPOSITORY LAYER                                              │
│                              (memory/substrate_repository.py)                                   │
│                                                                                                 │
│    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────────┐           │
│    │  insert_packet()    │    │  insert_embedding() │    │  save_checkpoint()      │           │
│    │  get_packet()       │    │  semantic_search()  │    │  get_checkpoint()       │           │
│    │  search_packets()   │    │  batch_embed()      │    │  list_checkpoints()     │           │
│    └──────────┬──────────┘    └──────────┬──────────┘    └───────────┬─────────────┘           │
└───────────────┼──────────────────────────┼───────────────────────────┼──────────────────────────┘
                │                          │                           │
                ▼                          ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    POSTGRESQL DATABASE                                          │
│                                                                                                 │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────┐  ┌───────────────────────┐│
│  │   packet_store   │  │ memory_embeddings │  │  knowledge_facts   │  │   graph_checkpoints   ││
│  │   (Event Log)    │  │ (Vector Store)    │  │  (S-P-O Triples)   │  │   (Agent State)       ││
│  │                  │  │                   │  │                    │  │                       ││
│  │  22 columns      │  │  VECTOR(1536)     │  │  deprecated cols   │  │  Multi-checkpoint     ││
│  │  Multi-tenant    │  │  HNSW indexes     │  │  (migration 0010)  │  │  (migration 0014)     ││
│  │  (migration 0008)│  │  (migration 0008) │  │                    │  │                       ││
│  └────────┬─────────┘  └─────────┬─────────┘  └──────────┬─────────┘  └───────────┬───────────┘│
│           │                      │                       │                        │            │
│           └──────────────────────┴───────────────────────┴────────────────────────┘            │
│                                           │                                                    │
│                                           ▼                                                    │
│                              ┌─────────────────────────────┐                                   │
│                              │      pgvector extension     │                                   │
│                              │   Cosine similarity search  │                                   │
│                              └─────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DOWNSTREAM CONSUMERS                                          │
│                                                                                                 │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────┐  ┌───────────────────────┐│
│  │  Semantic Search │  │  Insight Extract  │  │   World Model      │  │   Reasoning Replay    ││
│  │  retrieval.py    │  │  insight_extract  │  │   world_model/     │  │   reasoning_replay.py ││
│  └──────────────────┘  └───────────────────┘  └────────────────────┘  └───────────────────────┘│
│                                                                                                 │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────┐  ┌───────────────────────┐│
│  │  State Manager   │  │  Agent Persistence│  │   Graph Client     │  │   Consolidation       ││
│  │  state_manager.py│  │  agent_persist    │  │   graph_client.py  │  │   consolidation.py    ││
│  └──────────────────┘  └───────────────────┘  └────────────────────┘  └───────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Relationships

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                     PacketEnvelope                              │
                    │              (core/schemas/packet_envelope_v2.py)               │
                    │                                                                 │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
                    │  │  packet_id  │  │ packet_type │  │        payload          │ │
                    │  │   (UUID)    │  │   (str)     │  │   (dict[str, Any])      │ │
                    │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
                    │  │  timestamp  │  │  metadata   │  │       provenance        │ │
                    │  │ (datetime)  │  │(Metadata)   │  │  (source, derive_type)  │ │
                    │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
                    │  │  thread_id  │  │   lineage   │  │         tags            │ │
                    │  │   (UUID)    │  │(parent_ids) │  │      (list[str])        │ │
                    │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
                    │  │     ttl     │  │ confidence  │  │     content_hash        │ │
                    │  │ (datetime)  │  │(0.0 - 1.0)  │  │      (SHA-256)          │ │
                    │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
                    │                                                                 │
                    │  IMMUTABLE: frozen=True | Mutations via with_mutation()        │
                    └──────────────────────────────────┬──────────────────────────────┘
                                                       │
                                                       │ Serialized to JSONB
                                                       ▼
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                       packet_store TABLE                        │
                    │                   (PostgreSQL - 22 columns)                     │
                    │                                                                 │
                    │  ┌─────────────────────────────────────────────────────────────┐│
                    │  │ CORE COLUMNS (migrations 0001, 0002)                        ││
                    │  │ ─────────────────────────────────────                       ││
                    │  │ packet_id (PK)   │ packet_type      │ envelope (JSONB)      ││
                    │  │ timestamp        │ routing          │ provenance (JSONB)    ││
                    │  │ thread_id        │ parent_ids[]     │ tags[]                ││
                    │  │ ttl                                                         ││
                    │  └─────────────────────────────────────────────────────────────┘│
                    │  ┌─────────────────────────────────────────────────────────────┐│
                    │  │ 10X ENHANCEMENTS (migration 0008)                           ││
                    │  │ ───────────────────────────────                             ││
                    │  │ scope             │ importance_score │ access_count         ││
                    │  │ last_accessed     │ contradiction_count │ chunk_count       ││
                    │  │ is_chunked        │ content_hash (UNIQUE) │ processing_status││
                    │  └─────────────────────────────────────────────────────────────┘│
                    │  ┌─────────────────────────────────────────────────────────────┐│
                    │  │ MULTI-TENANT (migration 0008)                               ││
                    │  │ ───────────────────────────                                 ││
                    │  │ tenant_id         │ org_id           │ user_id              ││
                    │  │ correlation_id    │ session_id       │ trace_id             ││
                    │  └─────────────────────────────────────────────────────────────┘│
                    └─────────────────────────────────────────────────────────────────┘
```

---

## PacketEnvelope Schema (v2.0.0)

```python
class PacketEnvelope(BaseModel):
    """
    Canonical immutable event container for L9 Memory Substrate.

    Contracts:
    - IMMUTABLE once created (frozen=True enforced)
    - Modifications use with_mutation() creating new packet with lineage
    - Schema version 2.0.0
    """

    # Primary Key
    packet_id: UUID                    # Auto-generated unique ID

    # Required Fields
    packet_type: str                   # event, memory_write, reasoning_trace, etc.
    payload: dict[str, Any]            # Flexible JSON payload
    timestamp: datetime                # UTC timestamp (auto-generated)

    # Optional Fields
    metadata: PacketMetadata           # schema_version, agent, domain
    provenance: PacketProvenance       # source, tool, derive_type
    confidence: PacketConfidence       # score (0-1), rationale
    reasoning_block: dict              # StructuredReasoningBlock inline

    # v1.1.0+ Fields
    thread_id: UUID                    # Conversation/task thread
    lineage: PacketLineage             # parent_ids[], derivation_type, generation
    tags: list[str]                    # Lightweight labels
    ttl: datetime                      # Expiration for GC

    # v2.0.0 Fields
    content_hash: str                  # SHA-256 for integrity verification
```

---

## PacketStore Table Schema

| Column                | Type        | Migration | Description              |
| --------------------- | ----------- | --------- | ------------------------ |
| `packet_id`           | UUID PK     | 0001      | Primary key              |
| `packet_type`         | TEXT        | 0001      | Event classification     |
| `envelope`            | JSONB       | 0001      | Full PacketEnvelope      |
| `timestamp`           | TIMESTAMPTZ | 0001      | Event time               |
| `routing`             | JSONB       | 0001      | Agent routing metadata   |
| `provenance`          | JSONB       | 0001      | Source/derivation info   |
| `thread_id`           | UUID        | 0002      | Thread identifier        |
| `parent_ids`          | UUID[]      | 0002      | Multi-parent lineage     |
| `tags`                | TEXT[]      | 0002      | Labels                   |
| `ttl`                 | TIMESTAMP   | 0002      | Expiration               |
| `scope`               | TEXT        | 0008      | shared/cursor/l-private  |
| `importance_score`    | FLOAT       | 0008      | Learned importance (0-1) |
| `access_count`        | INT         | 0008      | Retrieval counter        |
| `last_accessed`       | TIMESTAMPTZ | 0008      | Last access time         |
| `contradiction_count` | INT         | 0008      | Times contradicted       |
| `chunk_count`         | INT         | 0008      | Number of chunks         |
| `is_chunked`          | BOOLEAN     | 0008      | Was content chunked?     |
| `content_hash`        | TEXT        | 0008      | Deduplication hash       |
| `processing_status`   | TEXT        | 0008      | Status tracking          |
| `tenant_id`           | UUID        | 0008      | Multi-tenant             |
| `org_id`              | UUID        | 0008      | Organization             |
| `user_id`             | UUID        | 0008      | User                     |

---

## Key Interactions

### Write Path

```
PacketEnvelopeIn                    → Creates immutable PacketEnvelope
    ↓
MemorySubstrateService.write_packet → Validates and orchestrates
    ↓
SubstrateDAG.run()                  → LangGraph processing pipeline
    ├── intake_node                 → Parse and validate
    ├── reasoning_node              → Add reasoning block
    ├── memory_write_node           → Insert to packet_store
    ├── semantic_embed_node         → Generate embeddings
    └── checkpoint_node             → Save state
    ↓
SubstrateRepository.insert_packet   → SQL INSERT to packet_store
```

### Read Path

```
SubstrateRepository.get_packet      → SQL SELECT from packet_store
    ↓
PacketStoreRow                      → DTO with all 22 columns
    ↓
PacketEnvelope (reconstituted)      → From envelope JSONB column
```

### Semantic Search Path

```
Query text
    ↓
SemanticService.search()            → Generate query embedding
    ↓
SubstrateRepository.semantic_search → pgvector cosine similarity
    ↓
memory_embeddings table             → HNSW index scan
    ↓
Join packet_store                   → Get full packets
```

---

## Related Tables

| Table               | Purpose           | FK to packet_store |
| ------------------- | ----------------- | ------------------ |
| `memory_embeddings` | Vector embeddings | `packet_id`        |
| `knowledge_facts`   | S-P-O triples     | `source_packet`    |
| `reasoning_traces`  | Reasoning chains  | `packet_id`        |
| `graph_checkpoints` | Agent state       | N/A                |
| `reflection_store`  | Lessons learned   | `source_packet`    |
| `tool_audit_log`    | Tool execution    | `request_id`       |

---

## File Locations

| Component             | Path                                        | Purpose                    |
| --------------------- | ------------------------------------------- | -------------------------- |
| PacketEnvelope Schema | `core/schemas/packet_envelope_v2.py`        | Canonical model            |
| Deprecated Schema     | `memory/substrate_models.py`                | v1.1.1 (sunset 2026-04-05) |
| Repository            | `memory/substrate_repository.py`            | Database access            |
| Service               | `memory/substrate_service.py`               | Orchestration              |
| DAG Pipeline          | `memory/substrate_dag.py`                   | LangGraph nodes            |
| Ingestion             | `memory/ingestion.py`                       | Entry point                |
| Validator             | `memory/validators/packet_validator.py`     | Whitelist                  |
| API Router            | `api/memory/router.py`                      | HTTP endpoints             |
| MCP Routes            | `mcp_memory/src/routes/memory_unified.py`   | MCP server                 |
| Migration 0001        | `migrations/0001_init_memory_substrate.sql` | Core tables                |
| Migration 0002        | `migrations/0002_enhance_packet_store.sql`  | Threading                  |
| Migration 0008        | `migrations/0008_memory_substrate_10x.sql`  | 10X upgrade                |

---

## Packet Types

| Type              | Description       | Example                   |
| ----------------- | ----------------- | ------------------------- |
| `event`           | General event     | User action, system event |
| `memory_write`    | Memory storage    | Saved fact, preference    |
| `reasoning_trace` | Agent reasoning   | Thought chain             |
| `tool_call`       | Tool invocation   | MCP tool execution        |
| `tool_result`     | Tool output       | Tool response             |
| `tool_audit`      | Tool audit log    | Governance record         |
| `insight`         | Extracted insight | Pattern, lesson           |
| `message`         | Chat message      | Conversation turn         |

---

## Immutability Contract

```python
# ❌ Cannot modify - raises ValidationError
packet.payload = {"new": "data"}

# ✅ Create derived packet with lineage
new_packet = packet.with_mutation(
    payload={"new": "data"},
    tags=["updated"]
)
# new_packet.lineage.parent_ids = [packet.packet_id]
# new_packet.lineage.generation = packet.lineage.generation + 1
```

---

## See Also

- `migrations/SCHEMA_DIAGRAM.txt` — Full schema diagram
- `memory/memory_spec_v3.0.yaml` — Memory specification
- `reports/AUDIT_PacketEnvelope_PacketStore_Integration.md` — Integration audit
- `memory/README.md` — Memory module overview
