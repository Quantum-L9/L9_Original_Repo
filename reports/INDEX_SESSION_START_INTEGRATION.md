# Index Command - Session Start Integration

## Problem Solved

**Before:** At session start, agent had no instant knowledge of repo structure. Had to read files to answer "Where is X?" questions.

**After:** `/index` runs at session start, loads repo structure to VPS Neo4j, writes summary to VPS memory. Agent has instant context.

---

## How It Works

### 1. Session Start Trigger

When Cursor session starts, `/index` command executes:

```bash
python3 tools/export_repo_indexes.py && \
python3 scripts/load_indexes_to_neo4j_vps.py
```

### 2. Export Phase

- Scans entire repo
- Generates 33 index files
- Saves to `readme/repo-index/`

### 3. VPS Neo4j Load Phase

- Loads to VPS Neo4j via HTTP API
- Creates nodes: File, Class, Function, Method, Route
- Creates relationships: EXTENDS, HAS_METHOD, HANDLED_BY
- Batched queries (efficient)

### 4. Memory Summary Phase

- Writes concise summary to VPS memory
- Kind: `insight`
- Searchable: `search "repo structure"`
- Token-efficient (not full dumps)

---

## Agent Context at Session Start

After `/index` runs, agent can instantly answer:

| Question | Source |
|----------|--------|
| "Where is ToolRegistry?" | VPS Neo4j graph query |
| "What extends BaseAgent?" | VPS Neo4j graph query |
| "How many classes are there?" | VPS memory summary |
| "What handles POST /api/memory?" | VPS Neo4j graph query |

**No file reading needed** - all in VPS memory/graph.

---

## Memory Summary Content

Written to VPS memory as `insight`:

```
L9 REPOSITORY STRUCTURE SUMMARY

STATISTICS:
- Files: X
- Classes: Y
- Routes: Z

NEO4J GRAPH: Loaded to VPS Neo4j
- Query via: /api/v1/memory/graph/query
```

**Size:** ~500 bytes (token-efficient)
**Kind:** `insight` (searchable)
**Location:** VPS memory (persistent)

---

## Efficiency Guarantees

1. **No Token Bloat**
   - Summary is statistics only
   - Not full file contents
   - Not per-file writes

2. **Incremental Updates**
   - Only reloads if needed
   - Uses MERGE, not CREATE
   - Checks existing nodes first

3. **Batched Queries**
   - 50-100 items per batch
   - Reduces API calls
   - Faster execution

4. **Single Memory Write**
   - One summary per index run
   - Not per-file
   - Not per-class

---

## Integration Points

### Cursor Startup
- Runs automatically via workspace setup
- No manual intervention needed

### On-Demand
- Type `/index` anytime
- Updates both Neo4j and memory

### After Refactoring
- Run `/index` to sync changes
- Updates graph and memory

---

## Query Examples

### Via Neo4j Graph API

```cypher
# Find class location
MATCH (c:Class {name: 'ToolRegistry'})
RETURN c.file, c.location

# Find inheritance
MATCH (c:Class)-[:EXTENDS*]->(parent:Class {name: 'BaseAgent'})
RETURN c.name, c.file

# Find route handler
MATCH (r:Route {method: 'POST', path: '/api/memory'})
RETURN r.handler, r.file
```

### Via Memory Search

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "repo structure"
```

---

## Fallback Behavior

If VPS API unavailable:
1. Script detects missing API key
2. Suggests local Docker fallback
3. Provides clear error message
4. Doesn't crash session start

---

*Updated: 2026-01-09*

