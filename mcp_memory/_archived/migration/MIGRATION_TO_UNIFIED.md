# MCP Memory Server → Unified L9 Substrate Migration

## Status: IN PROGRESS

**Goal:** Migrate MCP memory server from deprecated `memory.*` tables to unified L9 substrate (`packet_store` + `memory_embeddings`).

## What's Done

✅ Core save/search handlers rewritten (`memory_unified.py`)
- `save_memory_handler()` - Writes to `packet_store` + `memory_embeddings`
- `search_memory_handler()` - Vector search with packet_store join
- Scope mapping: MCP scopes → DB scopes

## What's Remaining

### 1. Complete Unified Handlers
- [ ] `get_memory_stats()` - Query packet_store instead of memory.* tables
- [ ] `delete_expired_memories()` - Delete from packet_store where ttl < now
- [ ] `compound_similar_memories()` - Use memory_embeddings for similarity
- [ ] `apply_importance_decay()` - Update packet_store.importance_score
- [ ] `cleanup_task()` - Background cleanup for expired packets

### 2. 10X Memory Tools (Can Reuse Unified Search)
- [ ] `get_context_injection()` - Use unified search
- [ ] `extract_session_learnings()` - Use unified save
- [ ] `get_proactive_suggestions()` - Use unified search
- [ ] `query_temporal()` - Query packet_store by timestamp
- [ ] `save_memory_with_confidence()` - Use unified save with confidence metadata

### 3. Infrastructure Wiring
- [ ] Update `main.py` to import from `memory_unified` instead of `memory`
- [ ] Update `mcp_server.py` handlers to use unified functions
- [ ] Wire Caddy to route `/mcp/*` to MCP server (port 9001)
- [ ] Create systemd service file
- [ ] Update Cursor `mcp.json` with MCP server config

### 4. Testing & Validation
- [ ] Test save/search with scope filtering (Cursor = developer/global only)
- [ ] Test governance enforcement (L can write l-private, C cannot)
- [ ] Test embedding generation and vector search
- [ ] Test cleanup and decay operations

## Scope Mapping

| MCP Scope | DB Scope | Who Can Access |
|-----------|----------|----------------|
| `developer` | `shared` | L + Cursor (both) |
| `l-private` | `l-private` | L only (Cursor blocked) |
| `global` | `shared` | L + Cursor (both, cross-project) |

**Note:** After full migration, DB scopes should be updated to match MCP scopes exactly. For now, mapping works.

## Database Schema

### packet_store (Central Event Log)
```sql
packet_id UUID PRIMARY KEY
packet_type TEXT  -- e.g., "memory_write_preference"
envelope JSONB    -- Full PacketEnvelope
timestamp TIMESTAMPTZ
thread_id UUID
tags TEXT[]
ttl TIMESTAMP     -- Expiration (NULL = permanent)
scope TEXT         -- 'shared', 'l-private'
importance_score FLOAT
access_count INT
last_accessed TIMESTAMPTZ
```

### memory_embeddings (Vector Storage)
```sql
embedding_id UUID PRIMARY KEY
packet_id UUID REFERENCES packet_store
embedding_type TEXT  -- 'content', 'context', 'entity', 'summary'
vector VECTOR(1536)
chunk_text TEXT
metadata JSONB
```

## Next Steps

1. Complete unified handlers (stats, cleanup, compound, decay)
2. Replace `memory.py` with `memory_unified.py`
3. Update imports in `main.py` and `mcp_server.py`
4. Wire Caddy routing
5. Deploy to VPS
6. Update Cursor mcp.json
7. Test end-to-end

## Files Modified

- `mcp_memory/src/routes/memory_unified.py` - NEW unified handlers
- `mcp_memory/src/routes/memory.py` - TO BE REPLACED
- `mcp_memory/src/main.py` - TO BE UPDATED (imports)
- `mcp_memory/src/mcp_server.py` - TO BE UPDATED (handlers)

## Deployment

See: `mcp_memory/deploy/` for deployment scripts and systemd service files.

