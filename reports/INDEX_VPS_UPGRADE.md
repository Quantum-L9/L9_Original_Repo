# Index Command VPS Upgrade

## What Changed

The `/index` command now uses **VPS API** instead of direct database connections.

### Before (v1.0)
- Direct Neo4j connection (required SSH tunnel or local Docker)
- No memory summary for agent context
- Manual execution only

### After (v2.0)
- ✅ VPS HTTP API (works from anywhere)
- ✅ Writes summary to VPS memory (instant agent context)
- ✅ Efficient incremental updates
- ✅ Auto-runs at session start

---

## New Scripts

### `scripts/load_indexes_to_neo4j_vps.py`
**Purpose:** Load repo indexes to VPS Neo4j via HTTP API

**Features:**
- Uses `/api/v1/memory/graph/query` endpoint
- Batched queries (50-100 items per batch)
- Incremental updates (MERGE, not CREATE)
- Writes summary to VPS memory
- Fallback to local Docker if API unavailable

**Usage:**
```bash
python3 scripts/load_indexes_to_neo4j_vps.py
```

### `scripts/run_index_vps.sh`
**Purpose:** Complete index workflow (export + load)

**Usage:**
```bash
./scripts/run_index_vps.sh
```

---

## Session Start Integration

When `/index` runs at session start:

1. **Exports indexes** → `readme/repo-index/` (33 files)
2. **Loads to VPS Neo4j** → Graph queries available
3. **Writes to VPS memory** → Agent has instant context

**Result:** Agent knows repo structure immediately without reading files.

---

## Memory Summary Format

Written to VPS memory as `insight` kind:

```
L9 REPOSITORY STRUCTURE SUMMARY

STATISTICS:
- Files: X
- Classes: Y
- Routes: Z
...

NEO4J GRAPH: Loaded to VPS Neo4j
- Query via: /api/v1/memory/graph/query
```

**Searchable at session start:**
```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "repo structure"
```

---

## Efficiency Features

1. **Incremental Updates**
   - Checks existing nodes before clearing
   - Only reloads if needed
   - Uses MERGE to avoid duplicates

2. **Batched Queries**
   - 50-100 items per batch
   - Reduces API calls
   - Faster execution

3. **Single Memory Write**
   - One summary, not per-file
   - Concise format
   - Token-efficient

4. **No Token Bloat**
   - Summary is structured, not full dumps
   - Only statistics and locations
   - Query examples, not full data

---

## Fallback Options

| Scenario | Script | Command |
|----------|--------|---------|
| VPS API available | `load_indexes_to_neo4j_vps.py` | Default |
| Local Docker only | `load_indexes_to_neo4j.py --local` | Fallback |
| SSH tunnel to VPS | `load_indexes_to_neo4j.py --vps` | Alternative |

---

## Configuration

**Required:**
- `L9_EXECUTOR_API_KEY` in `.env` (for VPS API)

**Optional:**
- `VPS_MEMORY_URL` (default: `https://157.180.73.53:9001`)

---

## Testing

```bash
# Dry run (no writes)
python3 scripts/load_indexes_to_neo4j_vps.py --dry-run

# Verbose output
python3 scripts/load_indexes_to_neo4j_vps.py --verbose

# Full execution
python3 scripts/load_indexes_to_neo4j_vps.py
```

---

*Updated: 2026-01-09*

