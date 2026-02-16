# L9 Database Best Practices

**Version:** 2.0.0
**Last Updated:** February 13, 2026
**Audience:** AI agents and L9 developers

---

## 🎯 Overview

This document provides best practices for database operations in L9 to ensure optimal performance, security, and maintainability.

**Key Principles:**
1. **Avoid N+1 queries** - Batch database operations
2. **Use tenant isolation** - Always filter by tenant_id
3. **Leverage PostgreSQL features** - Use ANY(), JSONB, arrays
4. **Connection pooling** - Reuse database connections
5. **Query performance** - Monitor and optimize slow queries

---

## 🚫 Avoiding N+1 Query Patterns

### What is an N+1 Query?

An N+1 query pattern occurs when you:
1. Execute 1 query to fetch N items
2. Execute N additional queries (one per item) to fetch related data
3. Total: N+1 queries (bad for performance)

### ❌ Anti-Pattern: N+1 Query

```python
# BAD: N+1 pattern - 101 queries for 100 packets
async def get_packets_with_embeddings_bad(packet_ids: list[UUID]):
    packets = []

    # Query 1: Fetch packets one by one
    for packet_id in packet_ids:  # ❌ Loop with query inside
        packet = await conn.fetch_one(
            "SELECT * FROM packet_store WHERE packet_id = $1",
            packet_id
        )

        # Query 2-101: Fetch embeddings one by one
        embedding = await conn.fetch_one(
            "SELECT * FROM semantic_memory WHERE payload->>'packet_id' = $1::text",
            str(packet_id)
        )

        packets.append({
            "packet": packet,
            "embedding": embedding
        })

    return packets

# Performance: 100 packets = 200 queries = ~1 second
```

### ✅ Best Practice: Batch Queries

```python
# GOOD: Batch queries - 2 queries for 100 packets
async def get_packets_with_embeddings_good(packet_ids: list[UUID]):
    if not packet_ids:
        return []

    # Query 1: Fetch ALL packets in one query
    packets = await conn.fetch(
        "SELECT * FROM packet_store WHERE packet_id = ANY($1)",
        packet_ids
    )

    # Query 2: Fetch ALL embeddings in one query
    embedding_rows = await conn.fetch(
        "SELECT * FROM semantic_memory WHERE (payload->>'packet_id')::uuid = ANY($1)",
        packet_ids
    )

    # Build lookup dictionary (in-memory, fast)
    embedding_map = {UUID(row["payload"]["packet_id"]): row for row in embedding_rows}

    # Combine results (no database queries)
    return [
        {
            "packet": packet,
            "embedding": embedding_map.get(packet["packet_id"])
        }
        for packet in packets
    ]

# Performance: 100 packets = 2 queries = ~20ms (50x faster!)
```

---

## 🔧 PostgreSQL-Specific Techniques

### 1. ANY() Operator for Batch Queries

PostgreSQL's `ANY()` operator is the **preferred way** to query multiple items:

```python
# ✅ RECOMMENDED: Use ANY() with list
packet_ids = [uuid1, uuid2, uuid3]
results = await conn.fetch(
    "SELECT * FROM packet_store WHERE packet_id = ANY($1)",
    packet_ids
)

# ❌ AVOID: IN clause with string interpolation
# (SQL injection risk — violates ADR-0087)
placeholders = ','.join(['$' + str(i) for i in range(1, len(packet_ids) + 1)])
results = await conn.fetch(
    f"SELECT * FROM packet_store WHERE packet_id IN ({placeholders})",
    *packet_ids
)
```

**Why ANY() is better:**
- Type-safe (no SQL injection)
- More efficient for large lists
- Cleaner code
- PostgreSQL-native

### 2. Array Operations

Use PostgreSQL array functions for efficient operations:

```python
# Add tags to multiple packets in one query
await conn.execute(
    """
    UPDATE packet_store
    SET tags = array_cat(tags, $2)
    WHERE packet_id = ANY($1)
    """,
    packet_ids,
    ["new_tag"]
)

# Remove tags
await conn.execute(
    """
    UPDATE packet_store
    SET tags = array_remove(tags, $2)
    WHERE packet_id = ANY($1)
    """,
    packet_ids,
    "old_tag"
)

# Check if tag exists
results = await conn.fetch(
    """
    SELECT * FROM packet_store
    WHERE $1 = ANY(tags)
    """,
    "important"
)
```

### 3. JSONB Queries

Efficiently query JSONB columns:

```python
# Query by JSONB field (packet_store.envelope is JSONB)
results = await conn.fetch(
    """
    SELECT * FROM packet_store
    WHERE envelope->>'type' = $1
    AND envelope->'metadata'->>'priority' = $2
    """,
    "task",
    "high"
)

# Update JSONB field
await conn.execute(
    """
    UPDATE packet_store
    SET envelope = jsonb_set(envelope, '{metadata,status}', '"completed"')
    WHERE packet_id = $1
    """,
    packet_id
)
```

### 4. Batch Inserts with executemany()

Insert multiple rows efficiently:

```python
# ✅ GOOD: Batch insert
packets_data = [
    (uuid1, "memory.lesson", json.dumps(envelope1), timestamp1),
    (uuid2, "memory.pattern", json.dumps(envelope2), timestamp2),
    (uuid3, "memory.decision", json.dumps(envelope3), timestamp3),
]

await conn.executemany(
    """
    INSERT INTO packet_store (packet_id, packet_type, envelope, timestamp)
    VALUES ($1, $2, $3, $4)
    """,
    packets_data
)

# ❌ BAD: Insert one by one
for packet in packets:
    await conn.execute(
        "INSERT INTO packet_store (...) VALUES (...)",
        packet.id, packet.type, packet.envelope, packet.timestamp
    )
```

---

## 🔒 Tenant Isolation

### Always Filter by tenant_id

**Critical for security:** Every query MUST filter by tenant_id to prevent cross-tenant data leakage.

```python
# ✅ CORRECT: Explicit tenant filtering
async def get_packets(tenant_id: UUID, packet_ids: list[UUID]):
    return await conn.fetch(
        """
        SELECT * FROM packet_store
        WHERE packet_id = ANY($1)
        AND tenant_id = $2
        """,
        packet_ids,
        tenant_id
    )

# ❌ WRONG: Missing tenant filter
async def get_packets_bad(packet_ids: list[UUID]):
    return await conn.fetch(
        "SELECT * FROM packet_store WHERE packet_id = ANY($1)",
        packet_ids
    )
    # ⚠️ Security risk: Can access other tenants' data!
```

### Row-Level Security (RLS)

L9 uses PostgreSQL RLS for defense-in-depth. RLS is enabled on `packet_store`, `semantic_memory`, and `knowledge_facts`.

#### RLS session variables

The `l9_set_scope()` SQL function sets four session variables that RLS policies evaluate:

| Variable | Purpose | Example values |
|----------|---------|----------------|
| `app.tenant_id` | Tenant UUID | `73350468-3158-5d0f-9b8c-9b193d96fc4b` |
| `app.org_id` | Organization UUID | `14910cef-fea1-51d7-9a28-05579e6c0c18` |
| `app.user_id` | User UUID | `2f00c090-3816-51a0-806c-34d32522a070` |
| `app.role` | Caller role | `end_user`, `cursor`, `l9_system`, `platform_admin` |

UUIDs are deterministic (uuid5 from string identifiers) — see `config/rls_config.py`.

```python
# Set RLS context before queries (done by MemorySubstrateService automatically)
await conn.execute("SELECT l9_set_scope($1, $2, $3, $4)", tenant_id, org_id, user_id, role)

# Now all queries are automatically filtered by RLS
packets = await conn.fetch("SELECT * FROM packet_store")
# RLS ensures only authorized rows are returned
```

#### Scope-based access control

RLS policies gate access by `scope` column + `app.role`:

| Scope | Accessible by role |
|-------|-------------------|
| `developer`, `global`, `agent` | All roles (open) |
| `cursor` | `cursor`, `cursor_user`, `platform_admin` |
| `l-private` | `l9_system`, `platform_admin` |

#### Role assignment per caller

| Caller | `app.role` | Default write scope | Allowed read scopes |
|--------|-----------|-------------------|-------------------|
| **L** (L-CTO kernel) | `end_user` | `developer` | `developer`, `global`, `l-private`, `cursor` |
| **C** (Cursor IDE) | `end_user` | `cursor` | `cursor`, `developer`, `global` |
| **Emma / future agents** | `end_user` | `agent` | `agent`, `developer`, `global` |

**Important:** `MemorySubstrateService.write_packet()` calls `l9_set_scope()` automatically before every transaction. Agents do NOT call it directly — it's handled by the service layer.

**Best Practice:** Use explicit tenant filtering **AND** RLS for maximum security. Application-level scope filtering (in `memory_unified.py`) provides a second enforcement layer on top of database-level RLS.

---

## 🔌 Connection Pooling

### Use SubstrateRepository

Always use L9's `SubstrateRepository` for database access:

```python
from memory.substrate_repository import SubstrateRepository

# ✅ CORRECT: Use repository with connection pooling
repo = SubstrateRepository(database_url, pool_size=5, max_overflow=10)
await repo.connect()

async with repo.acquire() as conn:
    results = await conn.fetch("SELECT * FROM packets LIMIT 10")

await repo.disconnect()
```

### Don't Create New Connections

```python
# ❌ WRONG: Creating new connection every time
async def get_packet_bad(packet_id: UUID):
    conn = await asyncpg.connect(database_url)
    result = await conn.fetch_one(
        "SELECT * FROM packets WHERE packet_id = $1",
        packet_id
    )
    await conn.close()
    return result
    # ⚠️ Performance issue: Connection overhead on every call
```

---

## 📊 Query Optimization

### 1. Use Indexes

Ensure frequently-queried columns have indexes:

```sql
-- Primary key on packet_id (already exists)
-- Index on tenant_id (critical for RLS)
CREATE INDEX idx_packet_store_tenant_id ON packet_store(tenant_id);

-- Index on timestamp for time-range queries
CREATE INDEX idx_packet_store_timestamp ON packet_store(timestamp);

-- Composite index for common query patterns
CREATE INDEX idx_packet_store_tenant_timestamp
ON packet_store(tenant_id, timestamp DESC);

-- JSONB GIN index for envelope queries
CREATE INDEX idx_packet_store_envelope_gin ON packet_store USING gin(envelope);

-- pgvector HNSW index for semantic search (semantic_memory)
CREATE INDEX idx_semantic_memory_vector ON semantic_memory
USING hnsw(vector vector_cosine_ops);

-- Scope index for RLS-filtered queries
CREATE INDEX idx_packet_store_scope ON packet_store(scope);
CREATE INDEX idx_semantic_memory_scope ON semantic_memory(scope);
```

### 2. Use EXPLAIN ANALYZE

Profile slow queries:

```python
# Add EXPLAIN ANALYZE to understand query performance
query = """
EXPLAIN ANALYZE
SELECT * FROM packet_store
WHERE tenant_id = $1
AND scope IN ('developer', 'global')
AND timestamp > $2
ORDER BY timestamp DESC
LIMIT 100
"""

result = await conn.fetch(query, tenant_id, start_time)
for row in result:
    logger.info(row)  # Use structlog, not print (ADR-0019)
```

### 3. Limit Result Sets

Always use LIMIT for potentially large result sets:

```python
# ✅ GOOD: Paginated query
async def get_packets_paginated(
    tenant_id: UUID,
    limit: int = 100,
    offset: int = 0
):
    return await conn.fetch(
        """
        SELECT * FROM packet_store
        WHERE tenant_id = $1
        ORDER BY timestamp DESC
        LIMIT $2 OFFSET $3
        """,
        tenant_id,
        limit,
        offset
    )

# ❌ BAD: Unbounded query
async def get_all_packets_bad(tenant_id: UUID):
    return await conn.fetch(
        "SELECT * FROM packet_store WHERE tenant_id = $1",
        tenant_id
    )
    # ⚠️ Could return millions of rows!
```

---

## 🎯 Common Patterns

### Pattern 1: Fetch Packets with Related Data

```python
async def get_packets_with_children(
    parent_ids: list[UUID]
) -> dict[UUID, list[dict]]:
    """Fetch packets and their children in 2 queries."""

    if not parent_ids:
        return {}

    # Query 1: Fetch parent packets
    parents = await conn.fetch(
        "SELECT * FROM packet_store WHERE packet_id = ANY($1)",
        parent_ids
    )

    # Query 2: Fetch all children in one query
    children = await conn.fetch(
        """
        SELECT * FROM packet_store
        WHERE $1 && parent_ids
        """,
        parent_ids
    )

    # Group children by parent (in-memory)
    children_by_parent: dict[UUID, list] = {}
    for child in children:
        for parent_id in child["parent_ids"]:
            children_by_parent.setdefault(parent_id, []).append(child)

    return {
        parent["packet_id"]: children_by_parent.get(parent["packet_id"], [])
        for parent in parents
    }
```

### Pattern 2: Bulk Update

```python
async def update_packet_status_bulk(
    packet_ids: list[UUID],
    status: str
) -> int:
    """Update processing_status for multiple packets."""

    result = await conn.execute(
        """
        UPDATE packet_store
        SET
            processing_status = $2,
            metadata = jsonb_set(metadata, '{updated_at}', to_jsonb(now()::text))
        WHERE packet_id = ANY($1)
        """,
        packet_ids,
        status
    )

    # Parse "UPDATE N" to get count
    updated_count = int(result.split()[-1])
    return updated_count
```

### Pattern 3: Conditional Batch Operations

```python
async def archive_old_packets(
    tenant_id: UUID,
    days_old: int = 90
) -> int:
    """Archive packets older than N days."""

    result = await conn.execute(
        """
        UPDATE packet_store
        SET
            tags = array_append(tags, 'archived'),
            metadata = jsonb_set(metadata, '{archived}', 'true')
        WHERE tenant_id = $1
        AND timestamp < NOW() - make_interval(days => $2)
        AND NOT ('archived' = ANY(tags))
        """,
        tenant_id,
        days_old
    )

    archived_count = int(result.split()[-1])
    return archived_count
```

### Pattern 4: Semantic Search with Scope Filtering

```python
async def search_memories_by_scope(
    query_embedding: list[float],
    scopes: list[str],
    tenant_id: UUID,
    top_k: int = 5,
    threshold: float = 0.7,
) -> list[dict]:
    """Semantic search filtered by scope and tenant — the core MCP search pattern."""

    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"
    scope_placeholders = ", ".join([f"${i}" for i in range(4, 4 + len(scopes))])
    params = [embedding_str, threshold, top_k, *scopes, tenant_id]

    rows = await conn.fetch(
        f"""
        SELECT
            sm.embedding_id,
            sm.payload->>'packet_id' as packet_id,
            COALESCE(sm.payload->>'_text', sm.payload->>'content') as content,
            sm.scope,
            1 - (sm.vector <=> $1::vector) as similarity
        FROM semantic_memory sm
        WHERE sm.vector IS NOT NULL
        AND sm.scope IN ({scope_placeholders})
        AND sm.tenant_id = ${4 + len(scopes)}::uuid
        AND 1 - (sm.vector <=> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT $3
        """,
        *params
    )
    return [dict(r) for r in rows]
```

---

## 🧪 Testing Database Code

### 1. Use Transactions for Tests

```python
import pytest

@pytest.fixture
async def db_transaction(substrate_repo):
    """Provide a transaction that rolls back after test"""
    async with substrate_repo.acquire() as conn:
        async with conn.transaction():
            yield conn
            # Transaction automatically rolls back
```

### 2. Test Batch Operations

```python
@pytest.mark.asyncio
async def test_batch_insert(db_transaction):
    """Test batch insert performance."""
    conn = db_transaction

    packets = [
        (uuid4(), "memory.lesson", json.dumps({"payload": {}}), datetime.now(UTC))
        for _ in range(1000)
    ]

    start = time.time()
    await conn.executemany(
        "INSERT INTO packet_store (packet_id, packet_type, envelope, timestamp) VALUES ($1, $2, $3, $4)",
        packets
    )
    duration = time.time() - start

    # Should be fast (< 100ms for 1000 inserts)
    assert duration < 0.1
```

### 3. Test Tenant and Scope Isolation

```python
@pytest.mark.asyncio
async def test_scope_isolation(db_transaction):
    """Test that scope filtering works with RLS."""
    conn = db_transaction

    tenant_a = uuid5(NAMESPACE_DNS, "tenant-a")

    # Insert packets with different scopes
    await conn.execute(
        "INSERT INTO packet_store (packet_id, tenant_id, scope, ...) VALUES ($1, $2, $3, ...)",
        uuid4(), tenant_a, "cursor", ...
    )
    await conn.execute(
        "INSERT INTO packet_store (packet_id, tenant_id, scope, ...) VALUES ($1, $2, $3, ...)",
        uuid4(), tenant_a, "developer", ...
    )

    # Query with scope filter
    results = await conn.fetch(
        "SELECT * FROM packet_store WHERE tenant_id = $1 AND scope = $2",
        tenant_a, "cursor"
    )

    # Should only return cursor-scoped packet
    assert len(results) == 1
    assert results[0]["scope"] == "cursor"
```

---

## 🚨 Common Mistakes

### Mistake 1: Query in Loop

```python
# ❌ WRONG
for packet_id in packet_ids:
    await conn.execute("UPDATE packet_store SET ... WHERE packet_id = $1", packet_id)

# ✅ CORRECT
await conn.execute("UPDATE packet_store SET ... WHERE packet_id = ANY($1)", packet_ids)
```

### Mistake 2: Missing Tenant Filter

```python
# ❌ WRONG
await conn.fetch("SELECT * FROM packet_store WHERE packet_id = $1", packet_id)

# ✅ CORRECT
await conn.fetch(
    "SELECT * FROM packet_store WHERE packet_id = $1 AND tenant_id = $2",
    packet_id, tenant_id
)
```

### Mistake 3: Unbounded Queries

```python
# ❌ WRONG
await conn.fetch("SELECT * FROM packet_store")

# ✅ CORRECT
await conn.fetch("SELECT * FROM packet_store LIMIT 1000")
```

### Mistake 4: Creating Connections Instead of Using Pool

```python
# ❌ WRONG
conn = await asyncpg.connect(database_url)
# ... use conn ...
await conn.close()

# ✅ CORRECT
async with substrate_repo.acquire() as conn:
    # ... use conn ...
```

### Mistake 5: Wrong Scope for Caller

```python
# ❌ WRONG: Cursor writing to agent scope
await save_memory(content="...", scope="agent")  # Cursor should use "cursor"

# ❌ WRONG: Agent writing to cursor scope
await save_memory(content="...", scope="cursor")  # Agents should use "agent"

# ✅ CORRECT: Each caller uses their designated scope
# Cursor → scope="cursor"
# Emma/agents → scope="agent"
# L-CTO → scope="developer" or "l-private"
```

### Mistake 6: f-string SQL (ADR-0087 violation)

```python
# ❌ WRONG: SQL injection risk
await conn.fetch(f"SELECT * FROM packet_store WHERE scope = '{scope}'")

# ✅ CORRECT: Parameterized query
await conn.fetch("SELECT * FROM packet_store WHERE scope = $1", scope)
```

---

## L9 Database Schema (Key Tables)

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `packet_store` | Canonical event log | `packet_id`, `packet_type`, `envelope` (JSONB), `scope`, `tenant_id`, `timestamp` |
| `semantic_memory` | Vector embeddings (pgvector) | `embedding_id`, `vector` (1536-dim), `payload` (JSONB), `scope`, `tenant_id` |
| `knowledge_facts` | Extracted facts | `fact_id`, `content`, `scope`, `tenant_id` |
| `reasoning_traces` | Reasoning audit trail | `trace_id`, `reasoning_block` (JSONB) |
| `agent_memory_events` | Agent event log | `event_id`, `agent_id`, `event_type` |
| `graph_checkpoints` | Graph state snapshots | `checkpoint_id`, `state` (JSONB) |

**RLS-enabled tables:** `packet_store`, `semantic_memory`, `knowledge_facts`

---

## ✅ Checklist for Code Review

When reviewing database code, check:

- [ ] No database queries inside loops
- [ ] Batch queries use `ANY()` or `executemany()`
- [ ] All queries filter by `tenant_id` (and `scope` where applicable)
- [ ] Large result sets use `LIMIT` and pagination
- [ ] Connection pooling used (via `SubstrateRepository`)
- [ ] Indexes exist for queried columns
- [ ] JSONB queries use appropriate operators
- [ ] Tests cover tenant and scope isolation
- [ ] No SQL injection vulnerabilities (ADR-0087)
- [ ] No f-string SQL — always use parameterized queries
- [ ] RLS context set before transactions (`l9_set_scope()`)

---

## 📚 Additional Resources

### L9 Documentation
- `docs/MCP-MEMORY-CAPSULE.md` — Agent memory integration guide
- `docs/MEMORY_PIPELINE_MAP.md` — Ingestion/retrieval pipeline map
- `config/rls_config.py` — RLS UUID generation and configuration
- `memory/substrate_repository.py` — Repository implementation
- `memory/substrate_dag.py` — DAG pipeline (all ingestion nodes)
- `readme/adr/0005-rls-shared-tenant-model.md` — RLS architecture decision
- `readme/adr/0087-sql-parameterization.md` — SQL injection prevention

### PostgreSQL Documentation
- [ANY() operator](https://www.postgresql.org/docs/current/functions-comparisons.html)
- [Array functions](https://www.postgresql.org/docs/current/functions-array.html)
- [JSONB functions](https://www.postgresql.org/docs/current/functions-json.html)
- [Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [pgvector](https://github.com/pgvector/pgvector)

---

**Last Updated:** February 13, 2026
