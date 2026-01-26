# ADR 0016: TypedDict vs Pydantic Boundary

## Status

Accepted

## Pattern

TypedDict for LangGraph state schemas; Pydantic BaseModel for API/storage; convert at boundaries.

## Files

- `langgraph/TYPEDDICT_VS_PYDANTIC.md` - Full rationale
- `memory/substrate_dag.py` - TypedDict state example
- `core/schemas/packet_envelope_v2.py` - Pydantic model example
- `graph_adapter/packet_node_adapter.py` - Conversion example

## Import Block

```python
# For TypedDict (LangGraph state)
from typing import TypedDict, NotRequired

# For Pydantic (API/storage)
from pydantic import BaseModel, Field
```

## Minimal Implementation

```python
# === LANGGRAPH STATE (TypedDict) ===
from typing import TypedDict, NotRequired

class GraphState(TypedDict, total=False):
    """LangGraph state — MUST be TypedDict."""
    messages: list[dict]           # Required
    context: NotRequired[str]      # Optional
    metadata: NotRequired[dict]    # Optional


# === API/STORAGE MODEL (Pydantic) ===
from pydantic import BaseModel, Field

class PacketEnvelopeIn(BaseModel):
    """API input — MUST be Pydantic."""
    packet_type: str = Field(..., description="Type of packet")
    payload: dict = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


# === CONVERSION AT BOUNDARY ===
def to_graph_state(packet: PacketEnvelopeIn) -> GraphState:
    """Convert Pydantic → TypedDict at graph entry."""
    return GraphState(
        messages=[packet.payload],
        metadata=packet.model_dump(),
    )

def from_graph_state(state: GraphState) -> PacketEnvelopeIn:
    """Convert TypedDict → Pydantic at graph exit."""
    return PacketEnvelopeIn(
        packet_type="result",
        payload={"messages": state.get("messages", [])},
    )
```

## Usage Example

```python
# At API route (Pydantic)
@router.post("/process")
async def process(packet: PacketEnvelopeIn):
    # Convert to TypedDict for graph
    state = to_graph_state(packet)

    # Run LangGraph (TypedDict state)
    result_state = await graph.ainvoke(state)

    # Convert back to Pydantic for response
    return from_graph_state(result_state)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Pydantic in LangGraph state
from pydantic import BaseModel

class GraphState(BaseModel):  # LangGraph won't work correctly!
    messages: list[dict]

# ❌ WRONG — TypedDict for API response
class APIResponse(TypedDict):  # No validation!
    data: dict

# ✅ CORRECT — TypedDict for graph, Pydantic for API
class GraphState(TypedDict):    # For LangGraph
    messages: list[dict]

class APIResponse(BaseModel):   # For API
    data: dict
```

## When to Use Each

| Use Case             | Type System | Why                                |
| -------------------- | ----------- | ---------------------------------- |
| LangGraph state      | TypedDict   | LangGraph requires dict-like state |
| API request/response | Pydantic    | Validation, serialization          |
| Database models      | Pydantic    | ORM integration                    |
| Configuration        | Pydantic    | Settings validation                |
| Inter-node data      | TypedDict   | Graph compatibility                |

## Rules

1. LangGraph state schemas MUST use TypedDict
2. API models MUST use Pydantic BaseModel
3. Convert at entry/exit boundaries ONLY
4. Use `total=False` for optional TypedDict fields
5. Use `model_dump()` for Pydantic → dict conversion

## AI Guidance

**DO:**

- Use TypedDict for LangGraph state schemas
- Use Pydantic for API request/response models
- Convert with helper functions at boundaries
- Use `NotRequired` for optional TypedDict fields

**DO NOT:**

- Use Pydantic BaseModel for LangGraph state
- "Fix" TypedDict to Pydantic in graph code
- Skip conversion at boundaries
- Mix TypedDict and Pydantic in same schema
