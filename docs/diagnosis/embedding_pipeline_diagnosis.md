# L9 Embedding Pipeline Diagnosis Report

**Date:** 2026-01-31  
**Issue:** Packets created but embeddings not appearing in PostgreSQL  
**Severity:** Medium-High (affects semantic search capability)

---

## Executive Summary

After tracing the L9 data processing and embedding pipeline, I've identified **multiple potential causes** for embeddings not being stored in PostgreSQL despite packets being created successfully. The issue is likely a combination of **routing filters** and **configuration/initialization gaps**.

---

## Architecture Overview

The L9 embedding pipeline has **two parallel paths**:

### Path 1: EnrichmentDAG (Used by MemorySubstrateService)
```
write_packet() → EnrichmentDAG.run() → _run_tier_1() → semantic_service.embed_and_store()
```

### Path 2: SubstrateDAG (LangGraph-based)
```
ingest_packet() → SubstrateDAG → memory_write_node → route_after_memory_write → semantic_embed_node
```

**Current Configuration:** `MemorySubstrateService` uses `EnrichmentDAG` (line 139 of `substrate_service.py`).

---

## Root Cause Analysis

### 🔴 Issue 1: Aggressive Content Filtering (GMP-42)

**Location:** `memory/substrate_dag.py` lines 92-122, 1020-1038

The routing logic **skips embedding** for content that doesn't meet specific criteria:

```python
# Embedding ONLY happens if packet_type contains:
should_embed = (
    "semantic" in packet_type.lower()
    or "memory" in packet_type.lower()
    or "text" in payload
    or "content" in payload
    or "description" in payload
)
```

**Impact:** Packets with `packet_type` like `"agent_response"`, `"tool_result"`, `"decision"`, etc. will **skip embedding entirely**.

**Additionally**, the `_should_skip_embedding()` function filters:
- Text shorter than 10 characters
- Known error messages (e.g., "Sorry, I encountered a temporary error")
- Empty or null text

### 🔴 Issue 2: EnrichmentDAG Text Extraction

**Location:** `memory/enrichment_dag.py` line 466

```python
embedding_id = await self._semantic_service.embed_and_store(
    text=str(envelope.payload),  # ⚠️ Stringifies entire payload dict
    ...
)
```

**Problem:** The `EnrichmentDAG` embeds `str(envelope.payload)` which produces:
```python
"{'key': 'value', 'nested': {'data': 123}}"
```

This is **not semantically meaningful** and may hit the 10-character minimum check or produce poor embeddings.

### 🔴 Issue 3: Dual DAG Confusion

**Location:** `memory/substrate_service.py` vs `memory/ingestion.py`

There are **two different DAGs** that can process packets:

| DAG | Used By | Embedding Logic |
|-----|---------|-----------------|
| `EnrichmentDAG` | `MemorySubstrateService.write_packet()` | Embeds `str(envelope.payload)` |
| `SubstrateDAG` | `ingest_packet()` (deprecated path) | Uses `route_after_memory_write` routing |

The canonical path (`ingest_packet()`) routes through `MemorySubstrateService.write_packet()` which uses `EnrichmentDAG`, but the `SubstrateDAG` has more sophisticated text extraction.

### 🟡 Issue 4: Missing Semantic Service in Tier 2/3 Fallback

**Location:** `memory/enrichment_dag.py` lines 602-625

When the circuit breaker opens or Tier 1 fails, the fallback tiers (`_run_tier_2`, `_run_tier_3`) **do not generate embeddings**:

```python
async def _run_tier_2(self, envelope: PacketEnvelope) -> EnrichmentResult:
    """Tier 2: Core-only write (skip enrichment)."""
    await self._repository.insert_packet(envelope)  # No embedding!
    return EnrichmentResult(...)
```

**Impact:** If there are transient failures, packets are stored but embeddings are lost.

### 🟡 Issue 5: Embedding Provider Initialization

**Location:** `memory/substrate_service.py` lines 118-130

The service **fails fast** if no embedding provider is configured:

```python
if embedding_provider is None:
    raise RuntimeError(
        "Embedding provider required; missing embedding context. "
        "Set OPENAI_API_KEY or provide explicit EmbeddingProvider."
    )
```

**Check:** Verify `OPENAI_API_KEY` is set in the runtime environment.

---

## Diagnostic Queries

Run these queries against your PostgreSQL database to diagnose:

### 1. Check packet_store vs semantic_memory counts
```sql
SELECT 
    (SELECT COUNT(*) FROM packet_store) AS packet_count,
    (SELECT COUNT(*) FROM semantic_memory) AS embedding_count,
    (SELECT COUNT(*) FROM packet_store) - (SELECT COUNT(*) FROM semantic_memory) AS missing_embeddings;
```

### 2. Check packet types without embeddings
```sql
SELECT 
    ps.packet_type,
    COUNT(*) AS packet_count,
    COUNT(sm.embedding_id) AS embedding_count
FROM packet_store ps
LEFT JOIN semantic_memory sm ON ps.packet_id::text = sm.payload->>'packet_id'
GROUP BY ps.packet_type
ORDER BY packet_count DESC;
```

### 3. Check recent packets and their embedding status
```sql
SELECT 
    ps.packet_id,
    ps.packet_type,
    ps.timestamp,
    CASE WHEN sm.embedding_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_embedding
FROM packet_store ps
LEFT JOIN semantic_memory sm ON ps.packet_id::text = sm.payload->>'packet_id'
ORDER BY ps.timestamp DESC
LIMIT 50;
```

### 4. Check for circuit breaker / DLQ activity
```sql
-- If you have a dead_letter_queue table
SELECT * FROM dead_letter_queue ORDER BY created_at DESC LIMIT 20;
```

---

## Recommendations

### Immediate Fixes

#### Fix 1: Expand Embeddable Packet Types
**File:** `memory/substrate_dag.py` line 1020

```diff
  should_embed = (
      "semantic" in packet_type.lower()
      or "memory" in packet_type.lower()
+     or "response" in packet_type.lower()
+     or "decision" in packet_type.lower()
+     or "insight" in packet_type.lower()
      or "text" in payload
      or "content" in payload
      or "description" in payload
+     or "message" in payload
+     or "summary" in payload
  )
```

#### Fix 2: Improve EnrichmentDAG Text Extraction
**File:** `memory/enrichment_dag.py` line 466

```diff
- embedding_id = await self._semantic_service.embed_and_store(
-     text=str(envelope.payload),
+ # Extract meaningful text from payload
+ text_to_embed = (
+     envelope.payload.get("text")
+     or envelope.payload.get("content")
+     or envelope.payload.get("description")
+     or envelope.payload.get("message")
+     or envelope.payload.get("summary")
+ )
+ if text_to_embed and len(str(text_to_embed)) >= 10:
+     embedding_id = await self._semantic_service.embed_and_store(
+         text=str(text_to_embed),
```

#### Fix 3: Add Embedding to Tier 2 Fallback
**File:** `memory/enrichment_dag.py` line 602

```diff
  async def _run_tier_2(self, envelope: PacketEnvelope) -> EnrichmentResult:
      """Tier 2: Core-only write (skip enrichment)."""
      try:
          await self._repository.insert_packet(envelope)
+         # Best-effort embedding in Tier 2
+         if self._semantic_service:
+             try:
+                 text = envelope.payload.get("text") or envelope.payload.get("content")
+                 if text and len(str(text)) >= 10:
+                     await self._semantic_service.embed_and_store(
+                         text=str(text),
+                         payload={"packet_id": str(envelope.packet_id)},
+                     )
+             except Exception:
+                 pass  # Best-effort, don't fail Tier 2
          return EnrichmentResult(...)
```

### Configuration Checks

1. **Verify OPENAI_API_KEY is set:**
   ```bash
   echo $OPENAI_API_KEY | head -c 10
   ```

2. **Check service initialization logs:**
   ```bash
   grep -i "embedding\|semantic\|provider" /var/log/l9/*.log | tail -50
   ```

3. **Verify circuit breaker state:**
   - Check if `enrichment_dag_circuit_breaker_open` appears in logs
   - If so, investigate why Tier 1 is failing

---

## Summary Table

| Issue | Severity | Likely Cause | Fix Complexity |
|-------|----------|--------------|----------------|
| GMP-42 Content Filtering | 🔴 High | Packet types not in whitelist | Low (config change) |
| EnrichmentDAG Text Extraction | 🔴 High | `str(payload)` not meaningful | Medium (code change) |
| Tier 2/3 No Embedding | 🟡 Medium | Fallback skips embedding | Medium (code change) |
| Missing OPENAI_API_KEY | 🟡 Medium | Env var not set | Low (config) |
| Circuit Breaker Open | 🟡 Medium | Transient failures | Investigate logs |

---

## Next Steps

1. Run the diagnostic SQL queries above
2. Check application logs for `enrichment_semantic_failed` or `circuit_breaker_open`
3. Verify `OPENAI_API_KEY` is set in the runtime environment
4. Apply Fix 1 (expand embeddable packet types) as a quick win
5. Apply Fix 2 (improve text extraction) for better embedding quality

---

**Report generated by L9 Investigation Agent**
