# TypedDict Usage in L9 LangGraph

This document describes how `TypedDict` is used throughout the L9 codebase for LangGraph state management.

## Overview

`TypedDict` is primarily used to define **type-safe state structures** for LangGraph DAGs (Directed Acyclic Graphs). These state definitions provide:

- Type checking for dictionary-based state structures
- Clear documentation of state schemas
- Integration with LangGraph's `StateGraph` execution model
- Serialization compatibility with Memory Substrate

## Primary Use Case: LangGraph State Definitions

All LangGraph workflows in L9 use `TypedDict` to define their state schemas. This ensures type safety while maintaining the flexibility of dictionary-based state that LangGraph requires.

## Common Patterns

### 1. `total=False` Pattern

Most state definitions use `TypedDict, total=False` to make all fields optional:

```python
class ResearchGraphState(TypedDict, total=False):
    """All fields are optional - allows incremental state updates."""
    thread_id: str
    request_id: str
    evidence: list[Evidence]
    # ... more fields
```

**Why?** Graph nodes can update state incrementally. Not every node needs to set every field.

### 2. Nested TypedDicts

Complex states use nested TypedDict definitions:

```python
class ResearchStep(TypedDict, total=False):
    step_id: str
    agent: str
    status: str

class ResearchGraphState(TypedDict, total=False):
    plan: list[ResearchStep]  # Nested TypedDict
    evidence: list[Evidence]  # Another nested TypedDict
```

### 3. Required Fields (No `total=False`)

Some states require certain fields to always be present:

```python
class SubstrateGraphState(TypedDict):
    """All fields are required."""
    envelope: dict[str, Any]
    errors: list[str]
```

## State Definitions by Component

### Research Graph State

**File:** `services/research/graph_state.py`

Defines state for the research LangGraph DAG:

```python
class ResearchGraphState(TypedDict, total=False):
    # Identity
    thread_id: str
    request_id: str
    user_id: str
    
    # Input
    original_query: str
    refined_goal: str
    
    # Planning
    plan: list[ResearchStep]
    current_step_idx: int
    
    # Research Results
    evidence: list[Evidence]
    sources: list[str]
    
    # Output
    final_summary: str
    final_output: dict[str, Any]
    
    # Errors
    errors: list[str]
```

**Nested Types:**
- `ResearchStep` - Individual research step
- `Evidence` - Gathered evidence with confidence scores

### Memory Substrate Graph State

**File:** `memory/substrate_graph.py`

State for packet processing through the memory substrate DAG:

```python
class SubstrateGraphState(TypedDict):
    # Input
    envelope: dict[str, Any]  # PacketEnvelope as dict
    
    # Processing results
    reasoning_block: dict[str, Any] | None
    written_tables: list[str]
    embedding_id: str | None
    saved_checkpoint_id: str | None
    
    # Insight extraction
    insights: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    world_model_triggered: bool
    
    # Status
    errors: list[str]
```

**Note:** This state uses required fields (no `total=False`) because the envelope is always present.

### Long Plan Execution State

**File:** `orchestration/long_plan_graph.py`

State for long-running plan execution workflows:

```python
class LongPlanState(TypedDict):
    # Input
    goal: str
    constraints: List[str]
    target_apps: List[str]
    
    # Phase tracking
    phase: Literal["PLAN", "EXECUTE", "HALT"]
    
    # Memory context
    governance_rules: List[Dict[str, Any]]
    project_history: List[Dict[str, Any]]
    
    # Gathered context
    github_context: Optional[Dict[str, Any]]
    notion_context: Optional[Dict[str, Any]]
    
    # Drafted work
    draft_plan: Optional[str]
    draft_code: Optional[str]
    
    # Pending actions (require approval)
    pending_gmp_tasks: List[Dict[str, Any]]
    pending_git_commits: List[Dict[str, Any]]
    
    # Results
    completed_actions: List[Dict[str, Any]]
    errors: List[str]
```

### WebSocket Task Router State

**File:** `orchestration/ws_task_router.py`

State for WebSocket event routing:

```python
class RouterState(TypedDict):
    event: Dict[str, Any]
    event_type: str
    context: Dict[str, Any]
    world_model_context: Dict[str, Any]
    classification: str
    task_envelope: Optional[Dict[str, Any]]
    errors: List[str]
```

### World Model Graph State

**File:** `world_model/nodes/service_nodes.py`

State for world model update operations:

```python
class WorldModelGraphState(TypedDict, total=False):
    # Input: insights to process
    insights: list[dict[str, Any]]
    
    # Output: update results
    world_model_result: dict[str, Any]
    snapshot_result: Optional[dict[str, Any]]
    
    # State tracking
    state_version: int
    entities_affected: list[str]
    
    # Errors
    errors: list[str]
```

### Reasoning Node State

**File:** `orchestrators/reasoning/adapter_node.py`

State for reasoning orchestration:

```python
class ReasoningNodeState(TypedDict):
    context: str
    mode: str
    depth: int
    branch_factor: int
    result: Optional[dict[str, Any]]
    errors: list[str]
```

## Files Using TypedDict

| File | Purpose | State Class |
|------|---------|-------------|
| `services/research/graph_state.py` | Research graph state | `ResearchGraphState`, `ResearchStep`, `Evidence` |
| `memory/substrate_graph.py` | Memory substrate processing | `SubstrateGraphState` |
| `orchestration/long_plan_graph.py` | Long plan execution | `LongPlanState` |
| `orchestration/ws_task_router.py` | WebSocket task routing | `RouterState` |
| `world_model/nodes/service_nodes.py` | World model updates | `WorldModelGraphState` |
| `orchestrators/reasoning/adapter_node.py` | Reasoning orchestration | `ReasoningNodeState` |
| `tests/performance/test_state_bloat.py` | Test mocks | `ResearchGraphState` (mock) |

## Best Practices

### 1. Use `total=False` for Incremental Updates

When state is updated incrementally across multiple graph nodes:

```python
class MyGraphState(TypedDict, total=False):
    field1: str
    field2: int
```

### 2. Use Required Fields for Critical State

When certain fields must always be present:

```python
class MyGraphState(TypedDict):
    required_field: str  # Always present
    optional_field: Optional[str]  # Can be None
```

### 3. Document State Purpose

Always include docstrings explaining:
- What the state represents
- How it flows through the graph
- Which fields are required vs optional

### 4. Use Nested TypedDicts for Complex Structures

Break down complex state into smaller, reusable TypedDicts:

```python
class Step(TypedDict, total=False):
    id: str
    status: str

class GraphState(TypedDict, total=False):
    steps: list[Step]  # Reusable nested type
```

## Integration with LangGraph

TypedDict states are used directly with LangGraph's `StateGraph`:

```python
from langgraph.graph import StateGraph

# Define state
class MyState(TypedDict, total=False):
    value: str

# Create graph
graph = StateGraph(MyState)

# Add nodes that receive/return MyState
graph.add_node("process", my_node_function)
```

## Type Safety Benefits

1. **IDE Support**: Autocomplete and type checking in IDEs
2. **Runtime Validation**: Can be used with runtime validators (Pydantic, etc.)
3. **Documentation**: Self-documenting state schemas
4. **Refactoring Safety**: Type checker catches breaking changes

## Serialization

TypedDict states are serialized to:
- **Memory Substrate**: Stored in `graph_checkpoints` table
- **Packet Store**: Persisted as `PacketEnvelope` payloads
- **Redis**: Cached for fast retrieval

All TypedDict states must be JSON-serializable (use `dict[str, Any]` for complex nested objects).

## See Also

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Python TypedDict Documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- L9 Memory Substrate: `memory/substrate_graph.py`
- L9 Orchestration: `orchestration/long_plan_graph.py`

