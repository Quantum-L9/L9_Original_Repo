# MCP Memory Schema vs L9 Migrations - Relationship Analysis

**Date:** 2026-01-09
**Status:** Schema conflict identified - migration path needed

---

## 🚨 Critical Discovery

**The MCP memory schema (`mcp_memory/schema/`) is DEPRECATED and conflicts with the unified L9 substrate.**

---

## Two Separate Schema Systems

### 1. **L9 Main Migrations** (`migrations/`) - ✅ PRODUCTION

**Purpose:** Unified L9 memory substrate (used by all L9 agents)

**Schema:** `public` (no schema prefix)

**Key Tables:**
- `packet_store` - Central PacketEnvelope store (v2.0)
- `memory_embeddings` - Vector embeddings with `packet_id` FK
- `semantic_memory` - Legacy vector store (being phased out)
- `agent_memory_events` - Structured agent events
- `reasoning_traces` - Reasoning blocks
- `knowledge_facts` - Extracted facts
- `world_model_entities` - Entity graph

**Migrations:**
- `0001_init_memory_substrate.sql` - Core foundation
- `0002_enhance_packet_store.sql` - Threading, lineage, scope
- `0008_memory_substrate_10x.sql` - Multi-tenant, `memory_embeddings` table

**Status:** ✅ **ACTIVE** - This is what unified handlers use

---

### 2. **MCP Memory Schema** (`mcp_memory/schema/`) - ❌ DEPRECATED

**Purpose:** Legacy MCP memory server schema (pre-unified substrate)

**Schema:** `memory` (with schema prefix)

**Key Tables:**
- `memory.short_term` - < 1 hour memories
- `memory.medium_term` - < 24 hour memories  
- `memory.long_term` - Durable memories
- `memory.audit_log` - Audit trail
- `memory.memory_relationships` - Memory relationships
- `memory.session_summaries` - Session summaries

**Migrations:**
- `init.sql` - Creates deprecated `memory.*` tables
- `001_hnsw_upgrade.sql` - HNSW index upgrade
- `002_10x_memory_upgrade.sql` - Confidence, relationships
- `003_governance_metadata.sql` - Governance columns
- `004_audit_project_id.sql` - Project ID column

**Status:** ❌ **DEPRECATED** - Per `memory-setup-instructions.md`:
> "memory.shortterm, memory.mediumterm, memory.longterm are DEPRECATED and will be deleted"

---

## The Conflict

### Current State

1. **Unified handlers** (`memory_unified.py`) use:
   - `packet_store` (from L9 migrations)
   - `memory_embeddings` (from L9 migrations)
   - ✅ **Correct** - Uses unified substrate

2. **MCP schema** (`mcp_memory/schema/`) creates:
   - `memory.short_term`, `memory.medium_term`, `memory.long_term`
   - ❌ **Wrong** - These are deprecated tables

3. **Old handlers** (`memory.py`) use:
   - `memory.*` tables
   - ❌ **Wrong** - Should be migrated to unified substrate

---

## Migration Path

### What Should Happen

1. **MCP server should NOT use `mcp_memory/schema/init.sql`**
   - These tables are deprecated
   - Unified handlers already use `packet_store` + `memory_embeddings`

2. **MCP server should use L9 migrations instead:**
   - Apply `migrations/0001_init_memory_substrate.sql`
   - Apply `migrations/0002_enhance_packet_store.sql`
   - Apply `migrations/0008_memory_substrate_10x.sql` (adds `memory_embeddings`)

3. **Only keep MCP-specific migrations:**
   - `003_governance_metadata.sql` - Adds `caller` to audit (but audit should be in unified substrate)
   - `004_audit_project_id.sql` - Adds `project_id` to audit

4. **Audit log location:**
   - Option A: Use L9's unified audit (if exists)
   - Option B: Keep `memory.audit_log` but migrate to unified substrate
   - Option C: Create audit in `public` schema (not `memory` schema)

---

## Recommended Action

### Immediate

1. **Stop using `mcp_memory/schema/init.sql`**
   - These tables conflict with unified substrate
   - Unified handlers don't use them

2. **Use L9 migrations for MCP server:**
   ```bash
   # On VPS, apply L9 migrations (if not already applied)
   psql $MEMORY_DSN -f migrations/0001_init_memory_substrate.sql
   psql $MEMORY_DSN -f migrations/0002_enhance_packet_store.sql
   psql $MEMORY_DSN -f migrations/0008_memory_substrate_10x.sql
   ```

3. **Apply only MCP-specific migrations:**
   ```bash
   # Add caller column to audit (if audit_log exists in unified substrate)
   psql $MEMORY_DSN -f mcp_memory/schema/migrations/003_governance_metadata.sql
   psql $MEMORY_DSN -f mcp_memory/schema/migrations/004_audit_project_id.sql
   ```

### Long-term

1. **Delete deprecated `memory.*` tables:**
   ```sql
   DROP TABLE IF EXISTS memory.short_term CASCADE;
   DROP TABLE IF EXISTS memory.medium_term CASCADE;
   DROP TABLE IF EXISTS memory.long_term CASCADE;
   DROP TABLE IF EXISTS memory.memory_relationships CASCADE;
   DROP TABLE IF EXISTS memory.session_summaries CASCADE;
   ```

2. **Migrate audit_log to unified substrate:**
   - Check if L9 has unified audit table
   - If yes, migrate `memory.audit_log` → unified audit
   - If no, keep `memory.audit_log` but document it

3. **Update MCP deployment scripts:**
   - Remove `mcp_memory/schema/init.sql` from deployment
   - Use L9 migrations instead
   - Keep only MCP-specific migrations (003, 004)

---

## Schema Comparison

| Component | L9 Migrations | MCP Schema | Status |
|-----------|---------------|------------|--------|
| **Packet Store** | `packet_store` | ❌ None | ✅ Use L9 |
| **Vector Embeddings** | `memory_embeddings` | ❌ None | ✅ Use L9 |
| **Short-term Memory** | ❌ None | `memory.short_term` | ❌ Deprecated |
| **Medium-term Memory** | ❌ None | `memory.medium_term` | ❌ Deprecated |
| **Long-term Memory** | ❌ None | `memory.long_term` | ❌ Deprecated |
| **Audit Log** | ❓ Check L9 | `memory.audit_log` | ⚠️ Need to reconcile |

---

## Current Handler Status

### ✅ Unified Handlers (`memory_unified.py`)
- Uses: `packet_store` + `memory_embeddings`
- Source: L9 migrations
- Status: ✅ **CORRECT**

### ❌ Old Handlers (`memory.py`)
- Uses: `memory.short_term`, `memory.medium_term`, `memory.long_term`
- Source: MCP schema
- Status: ❌ **DEPRECATED** - Should be deleted

---

## Decision Matrix

| Question | Answer |
|----------|--------|
| Should MCP server use `mcp_memory/schema/init.sql`? | ❌ **NO** - Tables are deprecated |
| Should MCP server use L9 migrations? | ✅ **YES** - Unified substrate |
| Should we keep `memory.audit_log`? | ⚠️ **MAYBE** - Check if L9 has unified audit |
| Should we delete old `memory.*` tables? | ✅ **YES** - After migration complete |
| Should unified handlers use `memory.*` tables? | ❌ **NO** - Already using unified substrate ✅ |

---

## Next Steps

1. ✅ **Verify L9 migrations are applied** on VPS
2. ⚠️ **Check if unified audit table exists** in L9 migrations
3. ⚠️ **Decide on audit_log location** (unified vs `memory.audit_log`)
4. ⚠️ **Update MCP deployment** to use L9 migrations, not MCP schema
5. ⚠️ **Delete old `memory.py` handlers** (already replaced by `memory_unified.py`)
6. ⚠️ **Delete deprecated `memory.*` tables** (after migration verified)

---

## Summary

**The MCP memory schema is a legacy artifact from before the unified substrate migration.**

**Unified handlers correctly use L9 migrations (`packet_store` + `memory_embeddings`).**

**The MCP schema (`mcp_memory/schema/`) should NOT be used for new deployments.**

**Action:** Use L9 migrations for MCP server, keep only MCP-specific migrations (003, 004) for audit enhancements.

