# Architecture Decision: MCP Memory Server and Ingestion Pipeline Integration

**Date:** 2026-01-09  
**Status:** Active  
**Decision Type:** Integration Architecture

---

## Context

The L9 memory substrate has a canonical ingestion entrypoint: `memory.ingestion.ingest_packet()` which processes PacketEnvelope objects through a DAG pipeline (Neo4j graph updates, embeddings, audit logging, etc.).

The MCP Memory Server (`mcp_memory/`) is an **external service** that provides memory access via the Model Context Protocol (MCP) for Cursor IDE and other MCP clients.

**Question:** Should the MCP Memory Server use the canonical `ingest_packet()` entrypoint, or write directly to the database?

---

## Decision

**The MCP Memory Server writes directly to `packet_store` and `memory_embeddings` tables, bypassing the canonical ingestion pipeline.**

### Rationale

1. **External Service Design**
   - MCP Memory Server is a standalone FastAPI service, not part of the L9 core runtime
   - It runs as a separate process (systemd service `l9-mcp`) on port 9001
   - It should not have dependencies on L9's internal ingestion DAG

2. **Performance & Latency**
   - MCP tool calls require fast response times (< 500ms for most operations)
   - The ingestion DAG includes multiple async steps (Neo4j updates, graph relationships, etc.)
   - Direct database writes are faster for MCP's use case

3. **Separation of Concerns**
   - **L9 Core Runtime:** Uses `ingest_packet()` for agent-generated packets (reasoning, tool calls, decisions)
   - **MCP Memory Server:** Handles external client requests (Cursor IDE, other MCP clients)
   - Different entry points for different use cases

4. **Data Consistency**
   - Both paths write to the same unified substrate (`packet_store` + `memory_embeddings`)
   - Both paths enforce governance rules (scope, caller, project_id)
   - Both paths log to `tool_audit_log` for audit trail
   - **Result:** Data consistency maintained without shared code path

5. **Future Flexibility**
   - MCP server can evolve independently (rate limiting, caching, etc.)
   - L9 ingestion pipeline can evolve independently (new DAG steps, etc.)
   - No tight coupling between external API and internal runtime

---

## Implementation Details

### MCP Server Write Path

```python
# mcp_memory/src/routes/memory_unified.py
async def save_memory_handler(...):
    # 1. Generate PacketEnvelope JSONB
    envelope = {
        "source_id": source,
        "agent_id": user_id,
        "thread_id": session_id,
        "kind": "MEMORY",
        "payload": {...},
        "metadata": {...}
    }
    
    # 2. Write directly to packet_store
    await execute(
        "INSERT INTO packet_store (packet_id, envelope, ...) VALUES (...)"
    )
    
    # 3. Generate embedding and write to memory_embeddings
    embedding = await embed_text(content)
    await execute(
        "INSERT INTO memory_embeddings (packet_id, embedding, ...) VALUES (...)"
    )
    
    # 4. Log to tool_audit_log (in mcp_server.py handle_tool_call)
```

### L9 Core Runtime Write Path

```python
# memory/substrate_service.py
async def ingest_packet(packet: PacketEnvelope):
    # 1. Write to packet_store
    # 2. Generate embedding → memory_embeddings
    # 3. Update Neo4j graph (entity relationships)
    # 4. Update memory_summaries (if applicable)
    # 5. Trigger DAG pipeline steps
    # 6. Log to tool_audit_log
```

### Shared Substrate

Both paths write to:
- `packet_store` (canonical event log)
- `memory_embeddings` (vector store)
- `tool_audit_log` (audit trail)

**Result:** Unified memory substrate, multiple entry points.

---

## Trade-offs

### ✅ Advantages

- **Performance:** Direct writes are faster (no DAG overhead)
- **Independence:** MCP server can evolve without affecting L9 core
- **Simplicity:** MCP server doesn't need to import L9 ingestion modules
- **Flexibility:** Each path can optimize for its use case

### ⚠️ Disadvantages

- **Code Duplication:** Both paths generate PacketEnvelope and embeddings
- **Maintenance:** Changes to substrate schema must be updated in both places
- **Missing DAG Steps:** MCP writes don't trigger Neo4j graph updates (if needed)

### Mitigation

1. **Code Duplication:** Acceptable trade-off for service independence
2. **Schema Changes:** Documented in `migrations/` - both services read same schema
3. **Neo4j Updates:** MCP server can call Neo4j directly if needed (future enhancement)

---

## Future Considerations

### Option 1: Shared Library (Future)

Create a shared library `memory/substrate_writer.py` that both services use:

```python
# memory/substrate_writer.py
async def write_packet_to_substrate(envelope: dict, embedding: list):
    """Shared write logic for packet_store + memory_embeddings."""
    # Used by both MCP server and L9 ingestion pipeline
```

**When to implement:** If code duplication becomes a maintenance burden.

### Option 2: MCP → Ingestion Pipeline (Future)

If MCP server needs full DAG processing:

```python
# mcp_memory/src/routes/memory_unified.py
from memory.substrate_service import ingest_packet

async def save_memory_handler(...):
    packet = PacketEnvelope(...)
    await ingest_packet(packet)  # Use canonical entrypoint
```

**When to implement:** If MCP server needs Neo4j graph updates or other DAG steps.

### Option 3: Hybrid Approach (Current + Future)

- **Simple writes:** Direct database writes (current)
- **Complex writes:** Call `ingest_packet()` for full DAG processing (future)

**When to implement:** If MCP server needs both fast simple writes and complex DAG processing.

---

## Conclusion

**Current decision:** MCP Memory Server writes directly to the unified substrate, bypassing the canonical ingestion pipeline.

**Rationale:** External service design, performance, separation of concerns, and future flexibility.

**Status:** This decision is **active and working**. No changes needed unless requirements change.

---

## References

- `memory/substrate_service.py` - L9 canonical ingestion pipeline
- `mcp_memory/src/routes/memory_unified.py` - MCP server write handlers
- `migrations/0001_init_memory_substrate.sql` - Unified substrate schema
- `migrations/0008_memory_substrate_10x.sql` - Enhanced substrate schema

