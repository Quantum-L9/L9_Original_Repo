# GMP-78: Semantic Tool Retrieval (Tool RAG)

**Status:** ✅ PHASE 6 COMPLETE  
**Priority:** HIGH  
**Risk Tier:** T1 (Read-only tool selection, no side effects)  
**Date:** 2026-01-15  
**Completed:** 2026-01-15

---

## 1. Intent Summary

Implement **RAG-based tool retrieval** so agents receive only the 3-5 most relevant tools per query instead of all 100+ tools. This reduces context bloat, improves tool selection accuracy, and aligns with frontier patterns (NIST/ISO 42001).

---

## 2. Scope Boundaries

### IN SCOPE
- Tool embedding generation and storage in pgvector
- Semantic search for tool retrieval (`tool_router_find`)
- Integration into executor tool binding flow
- Max iterations guard enhancement
- Postgres/Neo4j usage guidance in tool descriptions

### OUT OF SCOPE
- ReAct reasoning loop restructuring (separate GMP)
- Saga/hybrid tool implementations (separate GMP)
- Template-only DB enforcement (already partial)

---

## 3. Current State Analysis

### What Exists

| Component | Location | Status |
|-----------|----------|--------|
| `ToolDefinition` dataclass | `core/tools/tool_graph.py:42-65` | ✅ Has name, description, category |
| `L_INTERNAL_TOOLS` list | `core/tools/tool_graph.py:727-1533` | ✅ 100+ tools defined |
| `tool_router_find` definition | `core/tools/tool_graph.py:1467-1477` | ⚠️ Defined, NOT implemented |
| `max_iterations` guard | `core/agents/executor.py:369,1153-1156` | ✅ Exists (default=10) |
| `get_approved_tools()` | `core/tools/registry_adapter.py` | ⚠️ Returns ALL tools |
| pgvector extension | Postgres | ✅ Available |

### What's Missing

| Gap | Impact |
|-----|--------|
| Tool embeddings not stored | Cannot do semantic search |
| No `find_relevant_tools()` function | Tools not shortlisted |
| Executor binds ALL tools | Context bloat |
| No negative constraints | Poor tool selection guidance |

---

## 4. TODO Plan (Locked)

### Phase 1: Tool Embedding Infrastructure

#### TODO 1.1: Add embedding column to tool storage
**File:** `migrations/0020_tool_embeddings.sql` (NEW)
**Action:** CREATE
```sql
-- Tool embeddings table for semantic search
CREATE TABLE IF NOT EXISTS tool_embeddings (
    tool_name VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(64),
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    negative_constraints TEXT[],  -- Array of "don't use when X" strings
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tool_embeddings_vector ON tool_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
```

#### TODO 1.2: Create tool embedding service
**File:** `core/tools/tool_embeddings.py` (NEW)
**Action:** CREATE
**Lines:** ~150
**Implements:**
- `embed_tool_description(description: str) -> list[float]`
- `store_tool_embedding(tool: ToolDefinition) -> bool`
- `find_relevant_tools(query: str, top_k: int = 5) -> list[ToolDefinition]`
- `sync_all_tool_embeddings() -> int`

#### TODO 1.3: Add negative constraints to key tools
**File:** `core/tools/tool_graph.py`
**Action:** REPLACE (surgical edits to ~20 ToolDefinition entries)
**Lines:** 727-1533
**Changes:**
- Add `negative_constraints: list[str] = field(default_factory=list)` to ToolDefinition
- Add constraints like: `["Do not use for PII queries", "Use neo4j tools for relationship queries instead"]`

---

### Phase 2: Tool Router Implementation

#### TODO 2.1: Implement tool_router_find executor function
**File:** `core/tools/registry_adapter.py`
**Action:** INSERT after line ~2900 (in executor functions section)
**Lines:** +80
**Implements:**
```python
async def _exec_tool_router_find(
    query: str,
    top_k: int = 5,
    exclude_categories: list[str] | None = None,
) -> dict:
    """
    Find relevant tools for a task using semantic search.
    
    Args:
        query: Task description or user query
        top_k: Number of tools to return (default 5)
        exclude_categories: Categories to exclude (e.g., ["governance"])
    
    Returns:
        {"tools": [...], "query": str, "count": int}
    """
```

#### TODO 2.2: Add get_relevant_tools to ExecutorToolRegistry
**File:** `core/tools/registry_adapter.py`
**Action:** INSERT method in ExecutorToolRegistry class
**Lines:** +40 (after get_approved_tools ~line 260)
**Implements:**
```python
async def get_relevant_tools(
    self,
    agent_id: str,
    principal_id: str,
    query: str,
    top_k: int = 5,
) -> list[ToolBinding]:
    """
    Get tools relevant to query (semantic filtered + governance approved).
    
    Combines:
    1. Semantic search to find top_k relevant tools
    2. Governance filter to ensure agent has permission
    
    Returns intersection of relevant + approved tools.
    """
```

---

### Phase 3: Executor Integration

#### TODO 3.1: Add tool shortlisting to execution loop
**File:** `core/agents/executor.py`
**Action:** REPLACE in `_run_execution_loop`
**Lines:** 1168-1177 (after user message initialization, before state transition)
**Current:**
```python
# Initialize with task payload as first message
if instance.task.payload.get("message"):
    instance.add_user_message(instance.task.payload["message"])
# ... etc

# Transition to reasoning
instance.transition_to(ExecutorState.REASONING)
```
**After:**
```python
# Initialize with task payload as first message
user_message = (
    instance.task.payload.get("message")
    or instance.task.payload.get("query")
    or instance.task.payload.get("content")
    or ""
)
if user_message:
    instance.add_user_message(user_message)

# Semantic tool shortlisting (GMP-78)
if user_message and hasattr(self._tool_registry, 'get_relevant_tools'):
    try:
        relevant_tools = await self._tool_registry.get_relevant_tools(
            agent_id=instance.task.agent_id,
            principal_id=instance.task.principal_id,
            query=user_message,
            top_k=7,  # Slightly more than 5 to account for governance filtering
        )
        if relevant_tools:
            instance.bind_tools(relevant_tools)
            logger.info(
                "agent.executor.tools.shortlisted",
                task_id=str(instance.task.id),
                tool_count=len(relevant_tools),
                tools=[t.tool_id for t in relevant_tools],
            )
    except Exception as e:
        logger.warning(f"Tool shortlisting failed, using all approved tools: {e}")

# Transition to reasoning
instance.transition_to(ExecutorState.REASONING)
```

#### TODO 3.2: Add loop iteration warning
**File:** `core/agents/executor.py`
**Action:** INSERT after line 1182 (in while loop)
**Lines:** +10
**Implements:**
```python
# Warn when approaching max iterations (GMP-78: loop guard enhancement)
if instance.iteration >= max_iterations - 2:
    logger.warning(
        "agent.executor.approaching_max_iterations",
        task_id=str(instance.task.id),
        iteration=instance.iteration,
        max_iterations=max_iterations,
        message="Consider stopping and providing partial answer",
    )
```

---

### Phase 4: Tool Description Enhancement

#### TODO 4.1: Add Postgres vs Neo4j guidance to tool descriptions
**File:** `core/tools/tool_graph.py`
**Action:** REPLACE (surgical edits to descriptions)
**Target tools:**
- `memory_search` → Add: "Use for structured data retrieval, aggregations, and text search. For relationship queries, use neo4j_query instead."
- `neo4j_query` → Add: "Use for relationship traversal, path finding, and influence analysis. For aggregations and structured reports, use memory_search instead."
- `hybrid_rag_search` → Add: "Combines vector similarity (Postgres) + graph enrichment (Neo4j). Use when you need both semantic matching AND relationship context."

---

### Phase 5: Startup Integration

#### TODO 5.1: Sync tool embeddings at startup
**File:** `api/main.py` (or startup hook location)
**Action:** INSERT in startup sequence
**Lines:** +15
**Implements:**
```python
# Sync tool embeddings (GMP-78)
from core.tools.tool_embeddings import sync_all_tool_embeddings
try:
    count = await sync_all_tool_embeddings()
    logger.info(f"Tool embeddings synced: {count} tools")
except Exception as e:
    logger.warning(f"Tool embedding sync failed (non-fatal): {e}")
```

---

## 5. Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `migrations/0020_tool_embeddings.sql` | CREATE | ~20 |
| `core/tools/tool_embeddings.py` | CREATE | ~150 |
| `core/tools/tool_graph.py` | REPLACE | ~50 (descriptions + negative_constraints) |
| `core/tools/registry_adapter.py` | INSERT | ~120 (executor + method) |
| `core/agents/executor.py` | REPLACE+INSERT | ~30 |
| `api/main.py` | INSERT | ~15 |

**Total estimated changes:** ~385 lines

---

## 6. Test Plan

### Unit Tests (Phase 4 Gate)
**File:** `tests/core/tools/test_tool_embeddings.py` (NEW)
- `test_embed_tool_description_returns_vector()`
- `test_find_relevant_tools_returns_top_k()`
- `test_find_relevant_tools_excludes_categories()`
- `test_negative_constraints_in_results()`

### Integration Tests (Phase 4 Gate)
**File:** `tests/integration/test_tool_retrieval.py` (NEW)
- `test_executor_shortlists_tools_for_memory_query()`
- `test_executor_shortlists_tools_for_graph_query()`
- `test_executor_falls_back_when_shortlisting_fails()`

### Critical Path (Phase 5 Gate)
- Run existing executor tests to ensure no regression
- Manual test: Submit query, verify only relevant tools in context

---

## 7. Validation Criteria

### Phase 4 Closure
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Tool embeddings table created and populated
- [ ] `tool_router_find` executor function works

### Phase 5 Closure (Recursive Verification)
- [ ] Executor shortlists tools (verify via logs)
- [ ] Max iterations warning emitted at iteration N-2
- [ ] No regression in existing executor tests
- [ ] Tool descriptions include Postgres/Neo4j guidance

### Phase 6 Closure
- [ ] Evidence report generated
- [ ] Commit includes phase references

---

## 8. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Embedding API rate limits | Batch sync at startup, cache embeddings |
| Semantic search returns wrong tools | Include category in search, use negative constraints |
| Shortlisting breaks existing flows | Graceful fallback to all tools on error |
| Performance overhead | Async search, cache results per query |

---

## 9. Rollback Plan

1. Remove startup sync call
2. Revert executor changes (tool shortlisting)
3. Keep migration (embedding table doesn't break anything)
4. Feature flag: `L9_ENABLE_TOOL_RAG=false` to disable

---

## 10. Dependencies

- pgvector extension (✅ already installed)
- OpenAI embeddings API (✅ already used for memory)
- Postgres connection (✅ substrate service)

---

## 11. Next Steps After This GMP

1. **GMP-79:** ReAct Reasoning Loop - Enforce THOUGHT→ACTION→OBSERVATION pattern
2. **GMP-80:** Saga Tool Implementations - `saga_fetch_and_enrich`, `hybrid_rag_search`
3. **GMP-81:** Template-Only DB Enforcement - Block raw SQL/Cypher generation

---

**Phase 0 LOCKED:** 2026-01-15  
**Ready for Phase 1 execution**
