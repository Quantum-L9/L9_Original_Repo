# L9 Database Best Practices

**Version:** 1.0.0
**Last Updated:** January 17, 2026
**Audience:** L9 Developers

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
async def get_packets_with_metadata_bad(packet_ids: List[UUID]):
    packets = []

    # Query 1: Fetch packets one by one
    for packet_id in packet_ids:  # ❌ Loop with query inside
        packet = await conn.fetch_one(
            "SELECT * FROM packets WHERE packet_id = $1",
            packet_id
        )

        # Query 2-101: Fetch metadata one by one
        metadata = await conn.fetch_one(
            "SELECT * FROM packet_metadata WHERE packet_id = $1",
            packet_id
        )

        packets.append({
            "packet": packet,
            "metadata": metadata
        })

    return packets

# Performance: 100 packets = 200 queries = ~1 second
```

### ✅ Best Practice: Batch Queries

```python
# GOOD: Batch queries - 2 queries for 100 packets
async def get_packets_with_metadata_good(packet_ids: List[UUID]):
    if not packet_ids:
        return []

    # Query 1: Fetch ALL packets in one query
    packets = await conn.fetch(
        "SELECT * FROM packets WHERE packet_id = ANY($1)",
        packet_ids
    )

    # Query 2: Fetch ALL metadata in one query
    metadata_rows = await conn.fetch(
        "SELECT * FROM packet_metadata WHERE packet_id = ANY($1)",
        packet_ids
    )

    # Build lookup dictionary (in-memory, fast)
    metadata_map = {row["packet_id"]: row for row in metadata_rows}

    # Combine results (no database queries)
    return [
        {
            "packet": packet,
            "metadata": metadata_map.get(packet["packet_id"])
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
    "SELECT * FROM packets WHERE packet_id = ANY($1)",
    packet_ids
)

# ❌ AVOID: IN clause with string interpolation
# (SQL injection risk, less efficient)
placeholders = ','.join(['$' + str(i) for i in range(1, len(packet_ids) + 1)])
results = await conn.fetch(
    f"SELECT * FROM packets WHERE packet_id IN ({placeholders})",
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
    UPDATE packets
    SET tags = array_cat(tags, $2)
    WHERE packet_id = ANY($1)
    """,
    packet_ids,
    ["new_tag"]
)

# Remove tags
await conn.execute(
    """
    UPDATE packets
    SET tags = array_remove(tags, $2)
    WHERE packet_id = ANY($1)
    """,
    packet_ids,
    "old_tag"
)

# Check if tag exists
results = await conn.fetch(
    """
    SELECT * FROM packets
    WHERE $1 = ANY(tags)
    """,
    "important"
)
```

### 3. JSONB Queries

Efficiently query JSONB columns:

```python
# Query by JSONB field
results = await conn.fetch(
    """
    SELECT * FROM packets
    WHERE envelope->>'type' = $1
    AND envelope->'metadata'->>'priority' = $2
    """,
    "task",
    "high"
)

# Update JSONB field
await conn.execute(
    """
    UPDATE packets
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
    (uuid1, "type1", json.dumps(envelope1), timestamp1),
    (uuid2, "type2", json.dumps(envelope2), timestamp2),
    (uuid3, "type3", json.dumps(envelope3), timestamp3),
]

await conn.executemany(
    """
    INSERT INTO packets (packet_id, packet_type, envelope, timestamp)
    VALUES ($1, $2, $3, $4)
    """,
    packets_data
)

# ❌ BAD: Insert one by one
for packet in packets:
    await conn.execute(
        "INSERT INTO packets (...) VALUES (...)",
        packet.id, packet.type, packet.envelope, packet.timestamp
    )
```

---

## 🔒 Tenant Isolation

### Always Filter by tenant_id

**Critical for security:** Every query MUST filter by tenant_id to prevent cross-tenant data leakage.

```python
# ✅ CORRECT: Explicit tenant filtering
async def get_packets(tenant_id: str, packet_ids: List[UUID]):
    return await conn.fetch(
        """
        SELECT * FROM packets
        WHERE packet_id = ANY($1)
        AND tenant_id = $2
        """,
        packet_ids,
        tenant_id
    )

# ❌ WRONG: Missing tenant filter
async def get_packets_bad(packet_ids: List[UUID]):
    return await conn.fetch(
        "SELECT * FROM packets WHERE packet_id = ANY($1)",
        packet_ids
    )
    # ⚠️ Security risk: Can access other tenants' data!
```

### Row-Level Security (RLS)

L9 uses PostgreSQL RLS for defense-in-depth:

```python
# Set RLS context before queries
await conn.execute(
    "SET LOCAL l9.tenant_id = $1",
    tenant_id
)
await conn.execute(
    "SET LOCAL l9.org_id = $1",
    org_id
)

# Now all queries are automatically filtered by RLS
packets = await conn.fetch("SELECT * FROM packets")
# RLS ensures only tenant's packets are returned
```

**Best Practice:** Use explicit tenant filtering **AND** RLS for maximum security.

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
-- Index on packet_id (already exists as primary key)
-- Index on tenant_id (critical for RLS)
CREATE INDEX idx_packets_tenant_id ON packets(tenant_id);

-- Index on timestamp for time-range queries
CREATE INDEX idx_packets_timestamp ON packets(timestamp);

-- Composite index for common query patterns
CREATE INDEX idx_packets_tenant_timestamp
ON packets(tenant_id, timestamp DESC);

-- JSONB GIN index for envelope queries
CREATE INDEX idx_packets_envelope_gin ON packets USING gin(envelope);
```

### 2. Use EXPLAIN ANALYZE

Profile slow queries:

```python
# Add EXPLAIN ANALYZE to understand query performance
query = """
EXPLAIN ANALYZE
SELECT * FROM packets
WHERE tenant_id = $1
AND timestamp > $2
ORDER BY timestamp DESC
LIMIT 100
"""

result = await conn.fetch(query, tenant_id, start_time)
for row in result:
    print(row)
```

### 3. Limit Result Sets

Always use LIMIT for potentially large result sets:

```python
# ✅ GOOD: Paginated query
async def get_packets_paginated(
    tenant_id: str,
    limit: int = 100,
    offset: int = 0
):
    return await conn.fetch(
        """
        SELECT * FROM packets
        WHERE tenant_id = $1
        ORDER BY timestamp DESC
        LIMIT $2 OFFSET $3
        """,
        tenant_id,
        limit,
        offset
    )

# ❌ BAD: Unbounded query
async def get_all_packets_bad(tenant_id: str):
    return await conn.fetch(
        "SELECT * FROM packets WHERE tenant_id = $1",
        tenant_id
    )
    # ⚠️ Could return millions of rows!
```

---

## 🎯 Common Patterns

### Pattern 1: Fetch Items with Related Data

```python
async def get_packets_with_children(
    parent_ids: List[UUID]
) -> Dict[UUID, List[Dict]]:
    """Fetch packets and their children in 2 queries"""

    if not parent_ids:
        return {}

    # Query 1: Fetch parent packets
    parents = await conn.fetch(
        "SELECT * FROM packets WHERE packet_id = ANY($1)",
        parent_ids
    )

    # Query 2: Fetch all children in one query
    children = await conn.fetch(
        """
        SELECT * FROM packets
        WHERE $1 = ANY(parent_ids)
        """,
        parent_ids
    )

    # Group children by parent (in-memory)
    children_by_parent = {}
    for child in children:
        for parent_id in child["parent_ids"]:
            children_by_parent.setdefault(parent_id, []).append(child)

    # Combine
    return {
        parent["packet_id"]: children_by_parent.get(parent["packet_id"], [])
        for parent in parents
    }
```

### Pattern 2: Bulk Update

```python
async def update_packet_status_bulk(
    packet_ids: List[UUID],
    status: str
) -> int:
    """Update status for multiple packets"""

    result = await conn.execute(
        """
        UPDATE packets
        SET
            envelope = jsonb_set(envelope, '{status}', to_jsonb($2::text)),
            updated_at = NOW()
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
    tenant_id: str,
    days_old: int = 90
) -> int:
    """Archive packets older than N days"""

    result = await conn.execute(
        """
        UPDATE packets
        SET
            tags = array_append(tags, 'archived'),
            envelope = jsonb_set(envelope, '{archived}', 'true')
        WHERE tenant_id = $1
        AND timestamp < NOW() - INTERVAL '$2 days'
        AND NOT ('archived' = ANY(tags))
        """,
        tenant_id,
        days_old
    )

    archived_count = int(result.split()[-1])
    return archived_count
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
    """Test batch insert performance"""
    conn = db_transaction

    # Insert 1000 packets
    packets = [
        (uuid4(), "test", json.dumps({}), datetime.utcnow())
        for _ in range(1000)
    ]

    start = time.time()
    await conn.executemany(
        "INSERT INTO packets (packet_id, packet_type, envelope, timestamp) VALUES ($1, $2, $3, $4)",
        packets
    )
    duration = time.time() - start

    # Should be fast (< 100ms for 1000 inserts)
    assert duration < 0.1
```

### 3. Test Tenant Isolation

```python
@pytest.mark.asyncio
async def test_tenant_isolation(db_transaction):
    """Test that tenant filtering works"""
    conn = db_transaction

    # Insert packets for two tenants
    await conn.execute(
        "INSERT INTO packets (packet_id, tenant_id, ...) VALUES ($1, $2, ...)",
        uuid1, "tenant-a", ...
    )
    await conn.execute(
        "INSERT INTO packets (packet_id, tenant_id, ...) VALUES ($1, $2, ...)",
        uuid2, "tenant-b", ...
    )

    # Query with tenant filter
    results = await conn.fetch(
        "SELECT * FROM packets WHERE tenant_id = $1",
        "tenant-a"
    )

    # Should only return tenant-a's packet
    assert len(results) == 1
    assert results[0]["tenant_id"] == "tenant-a"
```

---

## 🚨 Common Mistakes

### Mistake 1: Query in Loop

```python
# ❌ WRONG
for packet_id in packet_ids:
    await conn.execute("UPDATE packets SET ... WHERE packet_id = $1", packet_id)

# ✅ CORRECT
await conn.execute("UPDATE packets SET ... WHERE packet_id = ANY($1)", packet_ids)
```

### Mistake 2: Missing Tenant Filter

```python
# ❌ WRONG
await conn.fetch("SELECT * FROM packets WHERE packet_id = $1", packet_id)

# ✅ CORRECT
await conn.fetch(
    "SELECT * FROM packets WHERE packet_id = $1 AND tenant_id = $2",
    packet_id, tenant_id
)
```

### Mistake 3: Unbounded Queries

```python
# ❌ WRONG
await conn.fetch("SELECT * FROM packets")

# ✅ CORRECT
await conn.fetch("SELECT * FROM packets LIMIT 1000")
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

---

## 📚 Additional Resources

### L9 Documentation
- `L9_ARCHITECTURE_FOR_AI.md` - Architecture overview
- `memory/substrate_repository.py` - Repository implementation
- `memory/substrate_models.py` - Data models

### PostgreSQL Documentation
- [ANY() operator](https://www.postgresql.org/docs/current/functions-comparisons.html)
- [Array functions](https://www.postgresql.org/docs/current/functions-array.html)
- [JSONB functions](https://www.postgresql.org/docs/current/functions-json.html)
- [Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

### Tools
- `scripts/check_n_plus_1.py` - Automated N+1 detection
- `.pre-commit-config.yaml` - Pre-commit hooks

---

## ✅ Checklist for Code Review

When reviewing database code, check:

- [ ] No database queries inside loops
- [ ] Batch queries use `ANY()` or `executemany()`
- [ ] All queries filter by `tenant_id`
- [ ] Large result sets use `LIMIT` and pagination
- [ ] Connection pooling used (via `SubstrateRepository`)
- [ ] Indexes exist for queried columns
- [ ] JSONB queries use appropriate operators
- [ ] Tests cover tenant isolation
- [ ] No SQL injection vulnerabilities

---

**Last Updated:** January 17, 2026
**Maintainer:** L9 Platform Team
**Questions?** See `docs/` or ask in #l9-dev

---

*This document is part of L9's commitment to production-ready, secure, and performant code.*
