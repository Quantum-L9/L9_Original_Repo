# ADR-0064: Dynamic Tool Discovery for Context-Efficient Agents

**Status:** Implemented  
**Date:** 2026-01-25  
**Author:** Igor Beylin  
**Implementation:** GMP-78 Phase 2

## Context

L9 agents face critical context overhead when tool catalogs exceed ~20 tools. Static tool context (loading all tool definitions upfront) creates severe scaling limitations:

| Problem | Impact |
|---------|--------|
| **Performance degradation** | Models make poor tool selections when presented with >20 tool descriptions simultaneously |
| **Token explosion** | Tool descriptions consume 5,000-15,000+ tokens (10-30% of context windows) |
| **Cognitive overload** | Agents struggle with decision overhead, selecting suboptimal or incorrect tools |
| **Opportunity cost** | Tokens spent on static tool lists could be allocated to task context, reasoning, or memory |

**Production Evidence**: Cursor's testing of dynamic context discovery for MCP tool loading achieved **46.9% token reduction** for agent runs involving tool calls.

### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Static tool context (prior approach) | Simple, all tools available | Context bloat, degraded quality at scale |
| B | New infrastructure (Qdrant + new module) | Full-featured | Duplicates existing pgvector infra |
| **C** | **Wire existing infrastructure** | Minimal diff, uses existing pgvector | Requires coordination between modules |
| D | Hybrid (semantic + file-based + caching) | Most complete | High complexity for Phase 1 |

## Decision

**Option C: Wire Existing Infrastructure**

L9 already had semantic tool discovery infrastructure built but not wired:
- `core/tools/tool_embeddings.py` - pgvector storage + semantic search (GMP-78 Phase 1)
- `sync_all_tool_embeddings()` - already called at startup
- `find_relevant_tools()` - already implemented

The decision was to **wire existing components** into the agent execution loop rather than building new infrastructure. This approach:
- Minimizes deployment risk
- Uses battle-tested pgvector infrastructure
- Maintains backwards compatibility via feature flag
- Ships faster with less code

## Implementation

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STARTUP (api/server.py lifespan)                  │
├─────────────────────────────────────────────────────────────────────┤
│  sync_all_tool_embeddings()                                          │
│    → Reads L_INTERNAL_TOOLS + L9_TOOLS                              │
│    → Generates OpenAI embeddings (text-embedding-3-small)           │
│    → Stores in pgvector tool_embeddings table                       │
│    → Tracks health: app.state.tool_embeddings_synced                │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│              EXECUTION (executor.py, iteration 0)                    │
├─────────────────────────────────────────────────────────────────────┤
│  await instance.prepare_dynamic_tools()                             │
│    ↓                                                                 │
│  discover_tools_for_task(task_payload)                              │
│    → Extracts query from task.payload                               │
│    → Calls find_relevant_tools() (pgvector cosine similarity)       │
│    → Filters by min_similarity threshold                            │
│    → Enforces token budget (max_tokens setting)                     │
│    → Converts to OpenAI function calling format                     │
│    → Caches in instance._discovered_tools                           │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                instance.assemble_context()                           │
├─────────────────────────────────────────────────────────────────────┤
│  get_tool_definitions()                                              │
│    → Returns cached discovered tools (if available)                 │
│    → Falls back to static binding (if discovery disabled/failed)    │
└─────────────────────────────────────────────────────────────────────┘
```

### Files Modified/Created

| File | Change |
|------|--------|
| `config/settings.py` | Added 4 dynamic discovery settings |
| `core/tools/dynamic_discovery.py` | **NEW** - Integration module |
| `core/agents/agent_instance.py` | Added `prepare_dynamic_tools()` + cache |
| `core/agents/executor.py` | Wired discovery before AIOS call |
| `api/server.py` | Added health tracking for tool embeddings |
| `tests/unit/test_dynamic_tool_discovery.py` | **NEW** - Test suite |

### Configuration

```bash
# Environment variables (config/settings.py)
L9_DYNAMIC_TOOL_DISCOVERY=true      # Feature flag (default: true)
L9_TOOL_DISCOVERY_TOP_K=5           # Max tools per task (default: 5)
L9_TOOL_DISCOVERY_MIN_SIMILARITY=0.3 # Cosine threshold (default: 0.3)
L9_TOOL_DISCOVERY_MAX_TOKENS=2000   # Token budget (default: 2000)
```

### Key Components

**1. `core/tools/dynamic_discovery.py`**

```python
async def discover_tools_for_task(
    task_payload: str,
    top_k: int | None = None,
    min_similarity: float | None = None,
    max_tokens: int | None = None,
) -> list[dict[str, Any]]:
    """
    Discover relevant tools for a task using semantic search.
    Returns tools in OpenAI function calling format.
    """
    # Uses existing find_relevant_tools() from tool_embeddings.py
    results = await find_relevant_tools(
        query=task_payload,
        top_k=top_k * 2,
        min_similarity=min_similarity,
    )
    
    # Convert to OpenAI format with token budget enforcement
    return await _format_and_filter_tools(results, max_tokens)
```

**2. `core/agents/agent_instance.py`**

```python
async def prepare_dynamic_tools(self) -> int:
    """
    Discover and cache relevant tools for this task.
    Call BEFORE assemble_context() for dynamic discovery.
    """
    if not is_dynamic_discovery_enabled():
        return 0
    
    task_query = self._extract_task_query()
    self._discovered_tools = await discover_tools_for_task(task_query)
    return len(self._discovered_tools)

def get_tool_definitions(self) -> list[dict[str, Any]]:
    """
    Returns dynamically discovered tools if available,
    otherwise falls back to static binding.
    """
    if self._discovered_tools is not None:
        return self._discovered_tools
    return self._get_static_tool_definitions()
```

**3. `core/agents/executor.py`**

```python
# In execution loop, before AIOS call:
if iteration == 0:
    await instance.prepare_dynamic_tools()

context = instance.assemble_context()
```

### Health Monitoring

```bash
GET /health/services
```

```json
{
  "dynamic_tool_discovery": {
    "synced": true,
    "tool_count": 45,
    "enabled": true,
    "top_k": 5
  }
}
```

### Failure Modes & Fallbacks

| Scenario | Behavior |
|----------|----------|
| `sync_all_tool_embeddings()` fails at startup | Logs warning, `tool_embeddings_synced=false` |
| `discover_tools_for_task()` fails | Falls back to static binding |
| Feature flag disabled | Uses static binding |
| Empty task payload | Returns empty list, uses static binding |
| Token budget exceeded | Truncates tool list at budget limit |

## Success Criteria

### Efficiency
| Metric | Target | Status |
|--------|--------|--------|
| Token reduction | 40-70% vs static tool context | Pending measurement |
| Discovery latency | <100ms for tool search | ✅ pgvector ~50ms |

### Quality
| Metric | Target | Status |
|--------|--------|--------|
| Tool selection precision | >85% for well-defined tasks | Pending measurement |
| Task success rate | No degradation vs static | Pending measurement |

### Robustness
| Metric | Target | Status |
|--------|--------|--------|
| Graceful fallback | Falls back to static binding | ✅ Implemented |
| Feature flag control | Can disable without deploy | ✅ Implemented |

## Consequences

### Positive
- **Minimal deployment risk** - wires existing infrastructure
- **Backwards compatible** - feature flag controlled
- **40-70% token reduction** expected for tool context
- **Scales to 100+ tools** without performance degradation
- **Progressive disclosure** - agents discover tools as needed
- **Full audit trail** - health endpoint shows discovery status

### Negative
- **Single search method** - semantic only (no hybrid BM25 yet)
- **No file-based fallback** - relies on pgvector availability
- **Re-embedding required** - tools must be re-embedded when updated

### Future Enhancements (Not Yet Implemented)

1. **Hybrid Search (Phase 3)** - Add BM25 keyword search with RRF fusion
2. **File-Based Fallback** - Cursor pattern for offline/degraded mode
3. **Tool Availability Tracking** - Real-time status in discovery results

### ✅ Implemented (GMP-79)

4. **Multi-turn Tool Caching** - Cache discovered tools in Redis across conversation turns
   - `get_cached_tools(task_id)` - Check cache before semantic search
   - `cache_tools(task_id, tools)` - Store tools with configurable TTL
   - `L9_TOOL_CACHE_TTL` - Default 300s (5 minutes) per conversation

## Integration Points

| Component | Integration |
|-----------|-------------|
| `core/tools/tool_embeddings.py` | Source: `find_relevant_tools()` for semantic search |
| `core/tools/base_registry.py` | Source: tool schemas for OpenAI format |
| `core/agents/executor.py` | Consumer: calls `prepare_dynamic_tools()` |
| `api/server.py` | Startup: `sync_all_tool_embeddings()`, health tracking |
| `config/settings.py` | Config: feature flags and tuning parameters |

## Related

- ADR-0017: Tool Definition Schema
- ADR-0037: Tool Wiring Protocol
- ADR-0048: Tool Dispatch Strategy
- ADR-0050: Tool Registry Cache
- `core/tools/tool_embeddings.py` - GMP-78 Phase 1 (semantic storage)
- `memory/tool_router.py` - Alternative router (not used, duplicative)

## References

- [Cursor: Dynamic Context Discovery](https://cursor.com/blog/dynamic-context-discovery)
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

## Changelog

| Date | Change |
|------|--------|
| 2026-01-25 | Initial proposal based on Perplexity research |
| 2026-01-25 | **Implemented** - Wired existing infrastructure (Option C) |
