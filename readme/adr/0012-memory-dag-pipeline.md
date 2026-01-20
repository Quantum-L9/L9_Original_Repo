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

## AI Guidance
**DO:**
- Add new processing as a new node
- Maintain node execution order
- Return proper result from each node
- Log node execution metrics

**DO NOT:**
- Bypass DAG for "fast" writes
- Skip nodes for "simple" packets
- Modify node order without analysis
- Catch exceptions silently in nodes
