# L9 Memory Substrate v3.1

Hybrid memory + structured reasoning substrate for L9 using PostgreSQL + pgvector + Neo4j + LangGraph.

## Components

| File | Purpose |
|------|---------|
| `substrate_models.py` | Pydantic models (PacketEnvelope, DTOs, state) |
| `substrate_repository.py` | Async database accessors (asyncpg) |
| `substrate_graph.py` | LangGraph DAG for packet processing |
| `substrate_service.py` | Service facade for API layer |
| `substrate_semantic.py` | Semantic embedding operations |
| `query_classifier.py` | Query pattern classification for adaptive retrieval (v3.1) |
| `reasoning_replay.py` | Decision chain reconstruction and explainability (v3.1) |
| `consolidation.py` | Memory consolidation pipeline (v3.1) |
| `agent_persistence.py` | Agent checkpoint management (v3.1) |

## Schema Version

**v3.1.0** — Includes:
- `thread_id`, `parent_ids`, `tags`, `ttl` for enhanced threading and lineage
- Multi-resolution embeddings (content, entity, summary, reasoning)
- Adaptive retrieval with query classification
- Reasoning replay for decision explainability
- Memory consolidation (deduplication, archival, summarization, TTL expiration)
- Agent persistence with checkpoint management

## v3.1 Features

### Query Classification

Automatic query pattern detection for adaptive retrieval weighting:

- **entity_lookup**: "Who is X?", "What is Y?" → Higher weight on graph_context
- **reasoning_trace**: "Why did agent decide X?" → Higher weight on recent packets
- **temporal**: "What happened last week?" → Higher weight on recent packets
- **exploratory**: "Tell me about X" → Higher weight on semantic_hits
- **factual**: "What is the value of X?" → Higher weight on facts
- **default**: Fallback pattern with balanced weights

```python
from memory.query_classifier import get_query_classifier

classifier = get_query_classifier()
pattern = classifier.classify_query("Why did the agent approve this?")
# Returns: "reasoning_trace"

weights = classifier.get_weight_overrides(pattern)
# Returns: {"recent": 0.6, "graph_context": 0.2, ...}
```

### Reasoning Replay

Reconstruct decision chains and explain decisions:

```python
from memory.reasoning_replay import ReasoningReplayPipeline

replay = service.get_reasoning_replay()

# Reconstruct full chain
chain = await replay.reconstruct_chain(packet_id)

# Explain decision in multiple formats
explanation = await replay.explain_decision(
    packet_id,
    format="narrative"  # or "json", "graph_viz", "mermaid"
)

# Verify lineage integrity
is_valid = await replay.verify_lineage_integrity(packet_id)
```

### Memory Consolidation

Automatic memory hygiene (weekly schedule: Saturday 2am UTC):

- **Deduplication**: Merge similar packets (similarity ≥ 0.95)
- **Archival**: Archive old, low-access packets (age ≥ 90 days, access < 3, importance < 0.3)
- **Summarization**: Summarize frequently accessed packets (access ≥ 10)
- **TTL Expiration**: Remove expired packets (grace period: 24 hours)

```python
from memory.consolidation import ConsolidationPipeline

consolidation = service.get_consolidation(dry_run=False)
report = await consolidation.run_consolidation(
    batch_size=1000,
    sleep_between_batches_ms=100,
)

# Report includes: deduplication_count, archived_count, summarized_count, expired_count
```

### Agent Persistence

Checkpoint management for agent state recovery:

```python
from memory.agent_persistence import AgentPersistenceService

persistence = service.get_agent_persistence()

# Create checkpoint
checkpoint_id = await persistence.create_checkpoint(
    agent_id="my_agent",
    state={"step": 5, "data": {...}},
    reason="on_critical_decision",  # or "on_agent_shutdown", "on_session_boundary", "scheduled_hourly"
)

# Restore checkpoint
state = await persistence.restore_checkpoint(agent_id="my_agent")

# Serialize/deserialize agent state
serialized = persistence.serialize_agent_state(agent_object)
restored = persistence.deserialize_agent_state(serialized)
```

## Migrations

Apply in order:

```bash
psql $DATABASE_URL -f migrations/0001_init_memory_substrate.sql
psql $DATABASE_URL -f migrations/0002_enhance_packet_store.sql
psql $DATABASE_URL -f migrations/0003_init_tasks.sql
```

## Usage

```python
from memory.substrate_models import PacketEnvelope
from memory.substrate_service import MemorySubstrateService

# Submit a packet
envelope = PacketEnvelope(
    packet_type="event",
    payload={"action": "user_query", "content": "..."}
)
result = await service.write_packet(envelope)

# Access v3.1 modules
classifier = service.get_query_classifier()
replay = service.get_reasoning_replay()
consolidation = service.get_consolidation()
persistence = service.get_agent_persistence()
```

## API Endpoints (v3.1)

- `POST /api/v1/memory/reasoning/replay` — Reconstruct decision chain
- `POST /api/v1/memory/consolidation/run` — Manual consolidation trigger

## Related Docs

- [PacketEnvelope Reference](../docs/memory/PacketEnvelope.md)
- [Schema Spec](../core/schemas/Memory.yaml)
- [Memory Spec v3.0](../memory/memory_spec_v3.0.yaml)

