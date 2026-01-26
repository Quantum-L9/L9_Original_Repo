# TypedDict vs Pydantic: Strategy Analysis

## Current L9 Strategy

L9 uses a **hybrid approach**:

- **TypedDict** for LangGraph state definitions
- **Pydantic BaseModel** for all other data structures (PacketEnvelope, API models, etc.)

## Is This a Good Strategy?

### ✅ **YES - This is a pragmatic, well-reasoned approach**

## Why TypedDict for LangGraph?

### 1. LangGraph's Native Requirements

LangGraph's `StateGraph` expects **dictionary-based state** that can be:

- **Merged incrementally** across nodes
- **Serialized/deserialized** for checkpoints
- **Updated partially** (nodes only set fields they modify)

```python
# LangGraph internally does:
new_state = {**old_state, **node_output}  # Dict merging
```

TypedDict is a **type annotation on dicts** - perfect fit.

### 2. Performance & Simplicity

**No conversion overhead:**

```python
# TypedDict (current approach)
state: SubstrateGraphState = {
    "envelope": envelope.model_dump(mode="json"),  # Convert once at entry
    "errors": []
}
# State flows as dict - no conversion needed

# If using Pydantic BaseModel:
state: SubstrateState = SubstrateState(envelope=envelope, ...)
# Would need: state.model_dump() → dict → merge → reconstruct → validate
# Much more overhead per node
```

### 3. Incremental Updates Work Naturally

With `TypedDict, total=False`, nodes can update state incrementally:

```python
# Node 1: Only sets 'evidence'
def node1(state: ResearchGraphState) -> ResearchGraphState:
    return {"evidence": [new_evidence]}  # Only this field

# Node 2: Only sets 'plan'
def node2(state: ResearchGraphState) -> ResearchGraphState:
    return {"plan": [new_step]}  # Only this field

# LangGraph merges: {**state, **node1_output, **node2_output}
```

With Pydantic, you'd need to:

- Reconstruct the full model each time
- Handle partial updates manually
- Or use `model_validate()` with `from_attributes=True` (still overhead)

## Why Pydantic Elsewhere?

### 1. Runtime Validation

Pydantic provides **runtime validation** that catches errors early:

```python
# Pydantic (used for PacketEnvelope, API models)
class PacketEnvelope(BaseModel):
    packet_id: UUID
    timestamp: datetime
    payload: dict[str, Any]

# Runtime validation catches:
envelope = PacketEnvelope(packet_id="not-a-uuid")  # ❌ ValidationError
```

TypedDict is **compile-time only** - no runtime checks.

### 2. Better Error Messages

Pydantic provides detailed validation errors:

```python
ValidationError: 1 validation error for PacketEnvelope
  packet_id
    Input should be a valid UUID [type=uuid_type, input_value='invalid', input_type=str]
```

TypedDict errors are generic type checker errors.

### 3. Serialization/Deserialization

Pydantic handles JSON/ORM conversion automatically:

```python
# Serialize
json_str = envelope.model_dump_json()

# Deserialize
envelope = PacketEnvelope.model_validate_json(json_str)

# ORM integration
envelope = PacketEnvelope.model_validate(db_row)
```

## The Conversion Pattern

L9 converts at the **boundary** between Pydantic and LangGraph:

```python
# Entry point: Pydantic → TypedDict
def process_packet(envelope: PacketEnvelope):
    initial_state: SubstrateGraphState = {
        "envelope": envelope.model_dump(mode="json"),  # Convert once
        "errors": []
    }
    # State flows as dict through graph

# Exit point: TypedDict → Pydantic (if needed)
def extract_result(state: SubstrateGraphState) -> PacketEnvelope:
    return PacketEnvelope.model_validate(state["envelope"])
```

**Key insight:** Convert at boundaries, not in the middle.

## Tradeoffs

### ✅ Advantages

| Aspect                  | TypedDict for LangGraph     | Pydantic for LangGraph          |
| ----------------------- | --------------------------- | ------------------------------- |
| **Performance**         | ✅ Fast (native dicts)      | ❌ Slower (validation overhead) |
| **State Merging**       | ✅ Natural (dict merge)     | ❌ Manual (reconstruct model)   |
| **Incremental Updates** | ✅ Built-in (`total=False`) | ❌ Complex (partial validation) |
| **Type Safety**         | ✅ Compile-time             | ✅ Runtime + compile-time       |
| **Error Messages**      | ⚠️ Generic                  | ✅ Detailed                     |
| **Serialization**       | ⚠️ Manual                   | ✅ Automatic                    |

### ⚠️ Disadvantages

1. **No Runtime Validation in Graph State**

   - TypedDict doesn't validate at runtime
   - Invalid state can flow through graph
   - **Mitigation:** Validate at entry/exit boundaries

2. **Two Type Systems**

   - Developers need to know both
   - Potential for confusion
   - **Mitigation:** Clear documentation (this file!)

3. **Manual Conversion**
   - Must convert Pydantic → dict at entry
   - Must convert dict → Pydantic at exit (if needed)
   - **Mitigation:** Helper functions at boundaries

## Alternative Approaches

### Option 1: Pure Pydantic (Not Recommended)

```python
class SubstrateGraphState(BaseModel):
    envelope: PacketEnvelope
    errors: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"  # For incremental updates
```

**Problems:**

- LangGraph state merging doesn't work naturally
- Need custom reducers for each field
- Performance overhead per node
- Partial updates are complex

### Option 2: Pure TypedDict (Not Recommended)

Use TypedDict everywhere, no Pydantic.

**Problems:**

- Lose runtime validation for API models
- Lose automatic serialization
- Lose ORM integration
- More error-prone for external data

### Option 3: Current Hybrid (✅ Recommended)

**TypedDict for LangGraph state, Pydantic for everything else.**

**Benefits:**

- Best of both worlds
- Each tool used where it excels
- Clear boundaries
- Minimal conversion overhead

## Best Practices

### 1. Validate at Boundaries

```python
# Entry: Validate Pydantic input
def process_packet(envelope: PacketEnvelope):  # Already validated
    state: SubstrateGraphState = {
        "envelope": envelope.model_dump(mode="json"),
        # ...
    }
    return graph.invoke(state)

# Exit: Validate if reconstructing
def extract_envelope(state: SubstrateGraphState) -> PacketEnvelope:
    return PacketEnvelope.model_validate(state["envelope"])  # Re-validate
```

### 2. Use Helper Functions

```python
def pydantic_to_graph_state(envelope: PacketEnvelope) -> SubstrateGraphState:
    """Convert Pydantic model to LangGraph state."""
    return {
        "envelope": envelope.model_dump(mode="json"),
        "errors": []
    }

def graph_state_to_pydantic(state: SubstrateGraphState) -> PacketEnvelope:
    """Extract Pydantic model from LangGraph state."""
    return PacketEnvelope.model_validate(state["envelope"])
```

### 3. Document the Boundary

```python
# =============================================================================
# Boundary: Pydantic ↔ TypedDict
# =============================================================================
#
# This module converts between:
# - Pydantic models (PacketEnvelope, etc.) - used in API/storage
# - TypedDict state (SubstrateGraphState) - used in LangGraph
#
# Conversion happens at graph entry/exit points only.
```

### 4. Type Hints Are Your Friend

```python
from typing import TypedDict
from pydantic import BaseModel

# Clear separation
class PacketEnvelope(BaseModel):  # Pydantic - runtime validation
    ...

class SubstrateGraphState(TypedDict):  # TypedDict - compile-time only
    envelope: dict[str, Any]  # Pydantic model as dict
```

## Real-World Example

Looking at `memory/substrate_graph.py`:

```python
# Pydantic model (validated, used in API)
envelope: PacketEnvelope = PacketEnvelope.model_validate(request_data)

# Convert to TypedDict for LangGraph
initial_state: SubstrateGraphState = {
    "envelope": envelope.model_dump(mode="json"),  # Convert once
    "errors": []
}

# State flows as dict through graph nodes
state = graph.invoke(initial_state)

# Extract result (if needed as Pydantic)
result_envelope = PacketEnvelope.model_validate(state["envelope"])
```

**Key insight:** One conversion at entry, state flows as dict, optional conversion at exit.

## When to Use Each

### Use TypedDict When:

- ✅ Defining LangGraph state schemas
- ✅ State needs incremental updates
- ✅ Performance is critical (graph execution)
- ✅ State merging is required

### Use Pydantic When:

- ✅ API request/response models
- ✅ Database models (ORM integration)
- ✅ External data validation
- ✅ Configuration schemas
- ✅ Need runtime validation

## Conclusion

**The hybrid approach (TypedDict for LangGraph, Pydantic elsewhere) is the right strategy** because:

1. **LangGraph requires dicts** - TypedDict is a natural fit
2. **Pydantic provides validation** - Critical for external data
3. **Minimal conversion overhead** - Only at boundaries
4. **Each tool used optimally** - Right tool for the job
5. **Clear boundaries** - Easy to understand and maintain

The only downside is maintaining two type systems, but the benefits far outweigh this cost.

## See Also

- [TypedDict Usage in L9](./README.md) - Complete TypedDict reference
- `memory/substrate_graph.py` - Real-world example
- `core/schemas/packet_envelope_v2.py` - Pydantic model example
