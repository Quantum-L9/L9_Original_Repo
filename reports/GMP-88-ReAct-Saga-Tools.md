# GMP-88: ReAct Loop Enhancement + Saga Tools

**Status:** ✅ PHASE 6 COMPLETE  
**Priority:** HIGH  
**Risk Tier:** T2 (Executor + Tool implementations)  
**Date:** 2026-01-15  
**Completed:** 2026-01-15

---

## 1. Intent Summary

Implement **ReAct pattern enforcement** with explicit THOUGHT/OBSERVATION logging and **4 saga tool executors** for cross-database operations (Postgres → Neo4j chains).

**Components:**
1. **ReAct Enhancement**: Add structured logging for reasoning steps
2. **Saga Tools**: Implement cross-DB chain operations

---

## 2. Scope Boundaries

### IN SCOPE
- Add THOUGHT/OBSERVATION packet logging to executor
- Implement 4 saga tool executors in `base_registry.py`
- Add negative constraints to saga tool definitions
- Enhanced descriptions for saga tools

### OUT OF SCOPE
- Template-only DB enforcement (separate GMP)
- Changes to AIOS runtime (KERNEL tier)
- LLM prompt modifications (separate GMP)

---

## 3. Current State Analysis

### What Exists

| Component | Location | Status |
|-----------|----------|--------|
| `ExecutorState.REASONING` | `core/agents/executor.py` | ✅ State exists |
| `ExecutorState.TOOL_USE` | `core/agents/executor.py` | ✅ State exists |
| `saga_fetch_and_enrich` def | `core/tools/tool_graph.py:1438` | ⚠️ Defined, NOT implemented |
| `saga_enrich_entities` def | `core/tools/tool_graph.py:1449` | ⚠️ Defined, NOT implemented |
| `saga_timeline_correlation` def | `core/tools/tool_graph.py:1460` | ⚠️ Defined, NOT implemented |
| `saga_execute_custom` def | `core/tools/tool_graph.py:1471` | ⚠️ Defined, NOT implemented |

### What's Missing

| Gap | Impact |
|-----|--------|
| No THOUGHT logging in executor | Reasoning not transparent |
| No OBSERVATION logging | Tool results not tracked as ReAct step |
| Saga tools have no executors | Tools exist but fail on call |

---

## 4. TODO Plan (Locked)

### Phase 1: ReAct Logging Enhancement

#### TODO 1.1: Add THOUGHT packet emission
**File:** `core/agents/executor.py`
**Action:** INSERT after reasoning call (~line 1287-1303)
**Lines:** +15
**Change:** Emit packet with `kind="THOUGHT"` containing LLM reasoning

```python
# GMP-88: ReAct THOUGHT logging
if aios_result.content:
    await self._emit_packet(
        packet_type="agent.executor.thought",
        payload={
            "task_id": str(instance.task.id),
            "iteration": iteration,
            "thought": aios_result.content[:500],  # Truncate for storage
            "action_type": aios_result.result_type.value,
        },
        agent_id=instance.task.agent_id,
        thread_id=instance.thread_id,
    )
```

#### TODO 1.2: Add OBSERVATION packet emission
**File:** `core/agents/executor.py`
**Action:** INSERT after tool result (~line 1361)
**Lines:** +15
**Change:** Emit packet with `kind="OBSERVATION"` containing tool result

```python
# GMP-88: ReAct OBSERVATION logging
await self._emit_packet(
    packet_type="agent.executor.observation",
    payload={
        "task_id": str(instance.task.id),
        "iteration": iteration,
        "tool_id": tool_call.tool_id,
        "observation": str(tool_result.result)[:500] if tool_result.success else tool_result.error,
        "success": tool_result.success,
    },
    agent_id=instance.task.agent_id,
    thread_id=instance.thread_id,
)
```

---

### Phase 2: Saga Tool Implementations

#### TODO 2.1: Implement saga_fetch_and_enrich
**File:** `core/tools/base_registry.py`
**Action:** INSERT after tool_router_find (~line 830)
**Lines:** +80
**Implements:**
```python
async def saga_fetch_and_enrich(
    query: str,
    entity_types: Optional[List[str]] = None,
    limit: int = 10,
) -> dict:
    """
    Cross-DB saga: vector search → entity extraction → graph enrichment.
    
    Steps:
    1. Postgres: Vector similarity search on query
    2. Extract: Identify entity IDs from results
    3. Neo4j: Enrich entities with graph relationships
    4. Combine: Merge structured data + graph context
    """
```

#### TODO 2.2: Implement saga_enrich_entities
**File:** `core/tools/base_registry.py`
**Action:** INSERT after saga_fetch_and_enrich
**Lines:** +60
**Implements:**
```python
async def saga_enrich_entities(
    entity_ids: List[str],
    relationship_types: Optional[List[str]] = None,
    depth: int = 1,
) -> dict:
    """
    Cross-DB saga: lookup entities → enrich with graph relationships.
    
    Steps:
    1. Take entity IDs (from previous step or user input)
    2. Neo4j: Query relationships up to specified depth
    3. Return enriched entity graph
    """
```

#### TODO 2.3: Implement saga_timeline_correlation
**File:** `core/tools/base_registry.py`
**Action:** INSERT after saga_enrich_entities
**Lines:** +70
**Implements:**
```python
async def saga_timeline_correlation(
    start_entity_id: str,
    time_range_hours: int = 24,
    event_types: Optional[List[str]] = None,
) -> dict:
    """
    Cross-DB saga: fetch events → trace causal chains → correlate timeline.
    
    Steps:
    1. Postgres: Fetch events for entity in time range
    2. Neo4j: Trace causal chains between events
    3. Return correlated timeline
    """
```

#### TODO 2.4: Implement saga_execute_custom
**File:** `core/tools/base_registry.py`
**Action:** INSERT after saga_timeline_correlation
**Lines:** +50
**Implements:**
```python
async def saga_execute_custom(
    steps: List[dict],
) -> dict:
    """
    Execute a custom saga with user-defined steps.
    
    Each step must have:
    - tool: str (tool name to call)
    - args: dict (arguments for tool)
    - output_key: str (key to store result)
    
    Results are passed forward: step N can reference step N-1's output.
    """
```

---

### Phase 3: Tool Description Enhancement

#### TODO 3.1: Add negative constraints to saga tools
**File:** `core/tools/tool_graph.py`
**Action:** REPLACE saga tool definitions
**Lines:** 1437-1480
**Changes:**
- Add `negative_constraints` to each saga tool
- Enhance descriptions with when-to-use guidance

---

## 5. Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `core/agents/executor.py` | INSERT | ~30 (THOUGHT + OBSERVATION logging) |
| `core/tools/base_registry.py` | INSERT | ~260 (4 saga executors) |
| `core/tools/tool_graph.py` | REPLACE | ~50 (negative constraints + descriptions) |

**Total estimated changes:** ~340 lines

---

## 6. Test Plan

### Unit Tests (Phase 4 Gate)
- `test_thought_packet_emitted_on_reasoning()`
- `test_observation_packet_emitted_on_tool_result()`
- `test_saga_fetch_and_enrich_chains_correctly()`
- `test_saga_execute_custom_passes_outputs()`

### Integration Tests (Phase 4 Gate)
- `test_executor_emits_react_packets()` - verify packet flow
- `test_saga_tools_callable()` - verify executors registered

---

## 7. Validation Criteria

### Phase 4 Closure
- [ ] py_compile passes on all modified files
- [ ] Saga tools importable
- [ ] THOUGHT/OBSERVATION logging verified

### Phase 5 Closure (Recursive Verification)
- [ ] All changes trace to TODO items
- [ ] No unauthorized diffs
- [ ] Executor state machine unchanged

---

## 8. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Saga tools fail if Neo4j unavailable | Graceful fallback with error message |
| THOUGHT logging overhead | Truncate to 500 chars, async emit |
| Custom saga injection | Validate step structure before execution |

---

**Phase 0 LOCKED:** 2026-01-15  
**Ready for Phase 1 execution**
