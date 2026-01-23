# ADR 0006: PacketEnvelope Audit Trail

## Status
Accepted

## Pattern
ALL operations emit PacketEnvelope to memory substrate for audit trail; no fire-and-forget.

## Files
- `core/schemas/packet_envelope_v2.py` - Schema definition
- `memory/substrate_service.py` - `write_packet()` 
- `memory/ingestion.py` - `ingest_packet()`
- `memory/substrate_dag.py` - DAG processing pipeline

## PacketEnvelope Schema
```python
PacketEnvelopeIn(
    packet_type: str,          # "reasoning", "tool_call", "decision", "checkpoint"
    thread_id: UUID,           # Conversation/session thread
    payload: dict,             # Operation-specific data
    metadata: dict,            # {agent, component, schema_version}
    confidence: dict,          # {score: 0.0-1.0, level: "high"|"medium"|"low"}
)
```

## Packet Types
| Type | Purpose | Emitted By |
|------|---------|------------|
| `reasoning` | Agent thought process | AgentExecutor |
| `tool_call` | Tool invocation | ToolRegistry |
| `decision` | Approved/rejected action | ApprovalManager |
| `checkpoint` | State snapshot | AgentPersistence |
| `insight` | Extracted knowledge | InsightExtraction |
| `error` | Failure with recovery | ErrorHandler |

## DAG Pipeline Nodes
```
ingest_packet()
    │
    ▼
SubstrateDAG.run()
    ├→ intake_node
    ├→ reasoning_node
    ├→ memory_write_node
    ├→ semantic_embed_node
    ├→ extract_insights_node
    ├→ store_insights_node
    ├→ world_model_trigger_node
    └→ checkpoint_node
```

## Rules
1. ALL operations MUST emit PacketEnvelope
2. Packets flow through full DAG pipeline
3. No silent operations (even failures emit packets)
4. Packet includes `confidence` score
5. Deduplication via `dedup_key` or `packet_id`

## AI Guidance
**DO:**
- Emit packet before AND after significant operations
- Include `confidence` score in payload
- Use appropriate `packet_type` for operation
- Set `metadata.component` to identify source

**DO NOT:**
- Skip packet emission for "minor" operations
- Use print() or logger.info() instead of packets
- Bypass DAG pipeline for "fast" writes
- Omit error packets on failure
