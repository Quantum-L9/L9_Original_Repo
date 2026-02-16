# GMP-132: Fix 4 Critical DB/Code Issues

**Status:** ✅ COMPLETE
**Tier:** RUNTIME
**Date:** 2026-02-02
**Commit:** `1744e03a`

---

## Summary

Fixed 4 critical issues blocking C1 VPS deployment:

| Issue                               | Root Cause                                                   | Fix                                       |
| ----------------------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| `syntax error near "#"`             | 13 SQL f-strings had `# noqa` comments INSIDE the query text | Moved comments BEFORE f-strings           |
| `relation "packets" does not exist` | Wrong table name in enrichment_dag.py                        | Changed `packets` → `packet_store`        |
| `cannot import 'get_dlq'`           | Missing factory function                                     | Added `get_dlq()` to dead_letter_queue.py |
| `packet_store_scope_check`          | Constraint missing `agent` scope                             | Created migration 0029                    |

---

## Files Modified

### 1. SQL Syntax Error Fixes (13 instances)

**memory/substrate_repository.py** (4 fixes)

- Lines 397-404: Thread search query
- Lines 416-423: Thread search query (no type)
- Lines 476-483: Search by type query
- Lines 912-919: Knowledge facts query

**memory/retrieval.py** (6 fixes)

- Line 668-676: Thread packets query
- Line 760-767: Children chain query
- Line 823-831: Knowledge facts join query
- Lines 881-893, 896-906, 912-920: Insight queries

**memory/importance_manager.py** (2 fixes)

- Lines 449-459: Prune count query
- Lines 465-476: Prune delete query

**memory/schema_introspection.py** (1 fix)

- Lines 171-178: Tables introspection query

### 2. Table Name Fix

**memory/enrichment_dag.py** line 695

```sql
-- Before (WRONG)
INSERT INTO packets (packet_id, packet_type, payload, timestamp)

-- After (CORRECT)
INSERT INTO packet_store (packet_id, packet_type, envelope, timestamp)
```

### 3. Missing Factory Function

**memory/dead_letter_queue.py** - Added:

```python
def get_dlq() -> DeadLetterQueue | None:
    """Get global DLQ instance if Redis available."""
    ...

async def get_dlq_async() -> DeadLetterQueue | None:
    """Async version."""
    ...
```

### 4. Database Migration

**migrations/0029_add_agent_scope.sql**

- Added `agent` to `packet_store_scope_check` constraint
- Updated RLS policy to allow `agent` scope
- Valid scopes now: `developer`, `global`, `l-private`, `agent`

---

## Deployment

1. ✅ Changes committed and pushed
2. ✅ Pulled to VPS `/opt/l9`
3. ✅ Migration 0029 executed on PostgreSQL
4. ✅ API container rebuilt with new code
5. ✅ All services healthy

---

## Verification

```bash
# All services healthy
docker compose ps
# l9-l9-api-1: healthy
# l9-neo4j: healthy
# l9-postgres: healthy
# ...

# No more errors in logs
docker logs l9-l9-api-1 2>&1 | grep -i 'syntax error'
# (empty - fixed)

docker logs l9-l9-api-1 2>&1 | grep -i 'get_dlq'
# (empty - fixed)
```

---

## Root Cause Analysis

### Issue: `# noqa` inside SQL f-strings

The bug pattern was:

```python
query = f"""  # noqa: ADR-0087 - comment here
    SELECT * FROM table
    ...
"""
```

The `# noqa` comment was INSIDE the f-string triple quotes, so it became part of the SQL query text. PostgreSQL saw `# noqa: ADR-0087...` as the first line of the query and failed with "syntax error at or near #".

**Fix:** Move comment BEFORE the f-string:

```python
# noqa: ADR-0087 - comment here
query = f"""
    SELECT * FROM table
    ...
"""
```

### Issue: Wrong table name

`enrichment_dag.py` tier-3 emergency fallback used `packets` instead of the correct table name `packet_store`.

### Issue: Missing factory

`dead_letter_queue.py` had the `DeadLetterQueue` class but no `get_dlq()` factory function that other modules expected.

### Issue: Scope constraint

Migration 0016 set CHECK constraint to only allow `developer`, `global`, `l-private`. But World Model and Seed Loader use `scope="agent"`.

---

## Lessons Learned

1. **Never put comments inside f-strings** - Python doesn't process `#` as a comment inside strings
2. **Table names must match migrations** - `packet_store` is the canonical table
3. **Factory functions must exist if imported** - Check all imports work
4. **Scope values must match constraints** - Add new scopes via migrations

---

## Sign-off

- [x] Phase 0: Scope identified
- [x] Phase 2: Code changes implemented
- [x] Phase 4: Deployed and verified
- [x] Phase 6: Report generated

**Signed:** L9 Agent | 2026-02-02
