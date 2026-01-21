# ADR 0012: Memory DAG Pipeline

## Status
Accepted

## Pattern
All packets processed through SubstrateDAG with ordered nodes; each node transforms/enriches data.

## Files
- `memory/substrate_dag.py` - DAG implementation
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

## Node Responsibilities
| Node | Input | Output | Side Effect |
|------|-------|--------|-------------|
| intake | PacketEnvelope | Validated envelope | Dedup check |
| reasoning | Envelope | Reasoning blocks | None |
| memory_write | Envelope | Write result | PostgreSQL write |
| semantic_embed | Envelope | Embedding ID | pgvector insert |
| extract_insights | Envelope | Insights list | None |
| store_insights | Insights | Store result | PostgreSQL write |
| world_model_trigger | Envelope | Update result | World model update |
| checkpoint | Envelope | Checkpoint ID | State snapshot |

## Rules
1. Packets MUST flow through full DAG
2. Node failure emits error packet, continues to next
3. Circuit breaker wraps entire DAG execution
4. Each node logs start/end with timing
5. Written tables tracked in result

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

**DO NOT:**
- Bypass DAG for "fast" writes
- Skip nodes for "simple" packets
- Modify node order without analysis
- Catch exceptions silently in nodes
- Duplicate validation outside `intake_node`
- Create parallel validation pipelines
