# Index + Audit Integration

## What Changed

The `/index` command now **automatically runs VPS memory audit** after loading indexes to Neo4j.

### Before
1. Export indexes → `readme/repo-index/`
2. Load to VPS Neo4j
3. Write summary to memory
4. **Stop** (no verification)

### After
1. Export indexes → `readme/repo-index/`
2. Load to VPS Neo4j
3. Write summary to memory
4. **Run VPS memory audit** ✅ NEW
5. Display audit report

---

## Integration Points

### 1. `scripts/load_indexes_to_neo4j_vps.py`

**New Method:** `run_memory_audit()`
- Called automatically after `write_memory_summary()`
- Runs `scripts/audit_graphs_vps.py` as subprocess
- Displays audit summary (last 30 lines)
- Handles timeouts and errors gracefully

**Location in code:**
```python
async def load_all(self):
    # ... load indexes ...
    await self.write_memory_summary()
    await self.run_memory_audit()  # ← NEW
    # ... complete ...
```

### 2. `scripts/run_index_vps.sh`

**Updated:** Added note about audit
- Script now mentions audit runs automatically
- No code changes needed (handled by Python script)

### 3. `.cursor-commands/setup-new-workspace.yaml`

**Updated:** Phase 2.5 (repo_index)
- Command now includes `load_indexes_to_neo4j_vps.py`
- Outputs include "VPS memory audit report"
- On-complete message mentions audit

---

## Audit Report Contents

After index load, audit verifies:

| Graph | What's Audited |
|-------|----------------|
| **PostgreSQL Packet Store** | Packet count, health status |
| **Semantic Memory (pgvector)** | Embedding count, dimensions |
| **Knowledge Facts** | Fact count, top predicates/subjects |
| **Neo4j Knowledge Graph** | Node types, relationship counts |
| **Agent State Graph** | Agent count, governance data |
| **Event Timeline** | Event count, timeline stats |
| **Repo Structure Graph** | File/Class/Route nodes (just loaded) |

---

## Example Output

```
============================================================
✅ VPS Neo4j Load Complete
============================================================
  Files:           734
  Routes:          198
  ...

============================================================
🔍 Running VPS Memory Audit...
============================================================

================================================================================
AUDIT REPORT
================================================================================

📊 MEMORY STATS:
   Status:            operational
   Total Packets:     168
   Total Embeddings:  14,763
   Total Facts:       293

🕸️  NEO4J KNOWLEDGE GRAPH:
   Node Types:
      File: 734
      Route: 198
      Tool: 99
      ...
```

---

## Benefits

1. **Automatic Verification**
   - No manual audit step needed
   - Immediate feedback on graph health
   - Catches issues right after index load

2. **Complete Picture**
   - Shows all graphs, not just repo structure
   - Verifies integration worked
   - Provides statistics for monitoring

3. **Session Start Integration**
   - Runs automatically in workspace setup
   - Agent sees full graph state at startup
   - No separate audit command needed

---

## Configuration

**No configuration needed** - audit runs automatically if:
- `L9_EXECUTOR_API_KEY` is set
- VPS API is accessible
- `scripts/audit_graphs_vps.py` exists

**Fallback:** If audit fails, index load still completes (non-blocking)

---

## Disabling Audit

To skip audit (for faster index loads):

```python
# In load_indexes_to_neo4j_vps.py
async def load_all(self):
    # ...
    await self.write_memory_summary()
    # await self.run_memory_audit()  # Comment out
    # ...
```

Or use `--dry-run` flag (skips audit automatically).

---

*Updated: 2026-01-09*

