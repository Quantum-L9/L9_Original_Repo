# ADR 0012: Memory DAG Pipeline

## Status

Accepted (Revised 2026-01-25 — GMP-125)

## Pattern

All packets processed through SubstrateDAG with ordered nodes; each node transforms/enriches data. EnrichmentDAG provides 3-tier fallback for resilient writes.

## Files

- `memory/substrate_dag.py` - Primary DAG implementation
- `memory/enrichment_dag.py` - 3-tier fallback enrichment (GMP-125)
- `memory/substrate_service.py` - `write_packet()` entry point
- `memory/ingestion.py` - `ingest_packet()` convenience function

## Pipeline Flow

```
PacketEnvelopeIn
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  SubstrateDAG.run(envelope)                         │
│                                                     │
│  ┌──────────────┐                                  │
│  │ intake_node  │ Validate, normalize, dedupe      │
│  └──────┬───────┘                                  │
│         ▼                                          │
│  ┌──────────────────┐                              │
│  │ reasoning_node   │ Extract reasoning blocks     │
│  └──────┬───────────┘                              │
│         ▼                                          │
│  ┌──────────────────┐                              │
│  │ memory_write_node│ Write to PostgreSQL          │
│  └──────┬───────────┘                              │
│         ▼                                          │
│  ┌──────────────────────┐                          │
│  │ semantic_embed_node  │ Generate embeddings      │
│  └──────┬───────────────┘                          │
│         ▼                                          │
│  ┌────────────────────────┐                        │
│  │ extract_insights_node  │ Extract facts/insights │
│  └──────┬─────────────────┘                        │
│         ▼                                          │
│  ┌─────────────────────┐                           │
│  │ store_insights_node │ Persist insights          │
│  └──────┬──────────────┘                           │
│         ▼                                          │
│  ┌────────────────────────────┐                    │
│  │ world_model_trigger_node   │ Update world model │
│  └──────┬─────────────────────┘                    │
│         ▼                                          │
│  ┌─────────────────┐                               │
│  │ checkpoint_node │ Save agent state              │
│  └─────────────────┘                               │
└─────────────────────────────────────────────────────┘
       │
       ▼
PacketWriteResult(status, packet_id, written_tables)
```

## 3-Tier Fallback Pattern (GMP-125)

EnrichmentDAG implements automatic degradation when enrichment fails:

```
┌─────────────────────────────────────────────────────────────────┐
│  EnrichmentDAG.run(envelope)                                    │
│                                                                 │
│  Circuit Breaker Check ─────► If OPEN, skip to Tier 2           │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ TIER 1: Full Enrichment                                 │   │
│  │ • Semantic embedding + search                           │   │
│  │ • Entity extraction → knowledge_facts                   │   │
│  │ • Graph enrichment via SagaExecutor                     │   │
│  │ • Write packet to repository                            │   │
│  │                                                         │   │
│  │ written_tables: [packets, knowledge_facts, relationships]│   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│              On failure/timeout                                 │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ TIER 2: Core Only                                       │   │
│  │ • Skip semantic, entity extraction, graph               │   │
│  │ • Write packet to repository only                       │   │
│  │                                                         │   │
│  │ written_tables: [packets]                               │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│              On failure/timeout                                 │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ TIER 3: Direct DB                                       │   │
│  │ • Raw INSERT bypassing ORM                              │   │
│  │ • Emergency fallback for maximum reliability            │   │
│  │                                                         │   │
│  │ written_tables: [packets]                               │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│              On failure                                         │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DEAD-LETTER QUEUE                                       │   │
│  │ • Push failed packet to DLQ for later reprocessing      │   │
│  │ • Return error result                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## EnrichmentDAG Usage

```python
from memory.enrichment_dag import EnrichmentDAG, EnrichmentConfig

# Initialize with dependencies
dag = EnrichmentDAG(
    repository=substrate_repository,
    semantic_service=semantic_service,
    saga_executor=saga_executor,  # Optional
    config=EnrichmentConfig(
        enable_semantic_enrichment=True,
        enable_entity_extraction=True,
        enable_graph_enrichment=True,
        enable_fallback_tiers=True,  # Enable 3-tier fallback
        enable_dlq=True,
        cb_failure_threshold=5,
        cb_window_seconds=60,
    ),
)

# Run enrichment
result = await dag.run(envelope)
# Returns: PacketWriteResult with enrichment_status, write_tier_used
```

## Node Responsibilities

| Node                | Input          | Output             | Side Effect        |
| ------------------- | -------------- | ------------------ | ------------------ |
| intake              | PacketEnvelope | Validated envelope | Dedup check        |
| reasoning           | Envelope       | Reasoning blocks   | None               |
| memory_write        | Envelope       | Write result       | PostgreSQL write   |
| semantic_embed      | Envelope       | Embedding ID       | pgvector insert    |
| extract_insights    | Envelope       | Insights list      | None               |
| store_insights      | Insights       | Store result       | PostgreSQL write   |
| world_model_trigger | Envelope       | Update result      | World model update |
| checkpoint          | Envelope       | Checkpoint ID      | State snapshot     |

## Enrichment Tiers

| Tier | Name        | Written Tables                          | When Used               |
| ---- | ----------- | --------------------------------------- | ----------------------- |
| 1    | Full        | packets, knowledge_facts, relationships | Normal operation        |
| 2    | Core Only   | packets                                 | Tier 1 fails/times out  |
| 3    | Direct DB   | packets                                 | Tier 2 fails, emergency |
| DLQ  | Dead-Letter | none                                    | All tiers failed        |

## Rules

1. Packets MUST flow through full DAG
2. Node failure emits error packet, continues to next
3. Circuit breaker wraps entire DAG execution
4. Each node logs start/end with timing
5. Written tables tracked in result
6. **3-tier fallback ensures packet persistence** (GMP-125)
7. **DLQ captures failures for reprocessing** (GMP-125)

## Validation Enforcement

Packet validation occurs in `intake_node` via `PacketValidator.validate()`.

**Canonical Validation Location:**

- File: `memory/substrate_dag.py` → `intake_node()`
- Validator: `memory/validators/packet_validator.py` → `PacketValidator`
- Schema: `core/schemas/packet_envelope_v2.py` → `PacketEnvelopeIn`

**DO NOT duplicate validation elsewhere:**

- Extractors do NOT validate packets (they may not emit packets at all)
- API routes do NOT validate packets (they pass to ingestion)
- Services do NOT validate packets (they call `ingest_packet()`)

**Single Pipeline Principle:**
All packets flow through `ingest_packet()` → `SubstrateDAG.run()` → `intake_node` validates.
This ensures single enforcement point, no duplicate paths, consistent audit trail.

## AI Guidance

**DO:**

- Add new processing as a new node
- Maintain node execution order
- Return proper result from each node
- Log node execution metrics
- Use `ingest_packet()` for ALL packet writes
- Use `EnrichmentDAG` for writes needing resilience (GMP-125)
- Configure fallback tiers based on criticality (GMP-125)

**DO NOT:**

- Bypass DAG for "fast" writes
- Skip nodes for "simple" packets
- Modify node order without analysis
- Catch exceptions silently in nodes
- Duplicate validation outside `intake_node`
- Create parallel validation pipelines
- Disable fallback tiers in production (GMP-125)
