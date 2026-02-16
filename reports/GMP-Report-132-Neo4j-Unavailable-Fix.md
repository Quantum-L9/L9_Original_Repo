# GMP-132: Neo4j "Unavailable" (But Running) - Fix

**GMP ID:** GMP-132
**Tier:** RUNTIME
**Status:** ✅ COMPLETE
**Date:** 2026-02-02

---

## Problem Statement

Neo4j service was running in Docker but showing as "unavailable" in API logs:

```
Neo4j not available, governance gates set in memory only
```

The .env configuration was correct (`NEO4J_URL=bolt://neo4j:7687`), and Neo4j container was healthy.

---

## Root Cause Analysis

**Location:** `api/server.py` lines 1625-1637

**Issue:** The server startup code was calling `get_neo4j_client()` which only **retrieves** an existing singleton client - it does NOT create/initialize one.

The `graph_client.py` docstring clearly states:

> "Call `init_neo4j_client()` during startup to initialize the singleton. This accessor does NOT create the client if it doesn't exist."

**Why it happened:**

1. `bootstrap/__main__.py` correctly calls `init_neo4j_client()`
2. But `api/server.py` was calling `get_neo4j_client()`
3. Bootstrap runs in a separate process - singleton not shared
4. Result: API server's `get_neo4j_client()` always returned `None`

---

## Fix Applied

### File 1: `api/server.py`

**Change:** Import and use `init_neo4j_client()` instead of `get_neo4j_client()` during startup

```python
# BEFORE
from memory.graph_client import close_neo4j_client, get_neo4j_client
...
neo4j = await get_neo4j_client()

# AFTER
from memory.graph_client import close_neo4j_client, get_neo4j_client, init_neo4j_client
...
# Use init_neo4j_client() on first attempt to CREATE the singleton
# GMP-132: get_neo4j_client() only retrieves existing client, does not create
neo4j = await init_neo4j_client()
```

### File 2: `memory/graph_client.py`

**Change:** Added diagnostic logging to `connect()` method

```python
# Added logging for connection attempts and failures
logger.debug(
    "Attempting Neo4j connection",
    uri=self._uri,
    user=self._user,
    database=self._database,
)
```

---

## Files Modified

| File                     | Lines     | Action                            |
| ------------------------ | --------- | --------------------------------- |
| `api/server.py`          | 1625-1640 | REPLACE - Use init_neo4j_client() |
| `memory/graph_client.py` | 133-155   | REPLACE - Add diagnostic logging  |

---

## Validation

- [x] Python syntax validation passed
- [ ] Integration test pending (requires Docker environment)
- [ ] Deployment verification pending

---

## Deployment Steps

1. Deploy updated code to C1
2. Restart l9-api service:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml restart l9-api
   ```
3. Check logs for successful Neo4j connection:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=50 | grep -i neo4j
   ```
4. Expected log: `Neo4j connected: bolt://neo4j:7687/neo4j`

---

## Rollback

If issues occur:

```bash
git checkout HEAD~1 -- api/server.py memory/graph_client.py
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart l9-api
```

---

## Lesson Learned

When a function says "does NOT create the client if it doesn't exist" in its docstring, believe it. The `get_*` pattern typically implies retrieval of existing resources, while `init_*` or `create_*` implies creation.

**Pattern to follow:** During service startup, always use `init_*` functions, not `get_*` functions, for singleton initialization.
