# ADR 0021: LangGraph Node Wrapper Pattern

## Status
Accepted

## Pattern
LangGraph nodes wrapped with `PacketNodeAdapter` to emit packets before/after execution.

## Files
- `graph_adapter/packet_node_adapter.py` - Adapter implementation
- `memory/substrate_dag.py` - SubstrateDAG nodes
- `services/research/research_graph.py` - Research graph nodes

## Import Block
```python
from graph_adapter.packet_node_adapter import PacketNodeAdapter
from memory.substrate_service import get_service
```

## Minimal Implementation
```python
from typing import Callable, TypeVar
from memory.substrate_service import MemorySubstrateService
import structlog

logger = structlog.get_logger(__name__)

StateT = TypeVar("StateT", bound=dict)

class PacketNodeAdapter:
    """
    Wraps LangGraph nodes to emit packets before/after execution.
    
    Ensures all graph operations are auditable via packet trail.
    """
    
    def __init__(
        self,
        service: MemorySubstrateService,
        agent_id: str = "graph_node",
    ):
        self._service = service
        self._agent_id = agent_id
    
    async def __call__(
        self,
        state: StateT,
        node_fn: Callable[[StateT], StateT],
        node_name: str,
    ) -> StateT:
        """
        Execute node with packet emission.
        
        Args:
            state: Current graph state
            node_fn: The actual node function
            node_name: Name for logging and packets
        
        Returns:
            Updated state from node execution
        """
        # Emit pre-execution packet
        await self._emit_packet(
            packet_type="node_start",
            node_name=node_name,
            state_keys=list(state.keys()),
        )
        
        try:
            # Execute node
            result = await node_fn(state)
            
            # Emit post-execution packet
            await self._emit_packet(
                packet_type="node_complete",
                node_name=node_name,
                state_keys=list(result.keys()),
            )
            
            return result
            
        except Exception as e:
            # Emit error packet
            await self._emit_packet(
                packet_type="node_error",
                node_name=node_name,
                error=str(e),
            )
            raise
    
    async def _emit_packet(self, packet_type: str, **kwargs) -> None:
        """Emit packet to memory substrate."""
        await self._service.write_packet({
            "packet_type": packet_type,
            "metadata": {"agent": self._agent_id},
            "payload": kwargs,
        })
```

## Usage Example
```python
from langgraph.graph import StateGraph
from graph_adapter.packet_node_adapter import PacketNodeAdapter
from memory.substrate_service import get_service

# Create adapter with service
service = await get_service()
adapter = PacketNodeAdapter(service, agent_id="research_graph")

# Define node function
async def process_node(state: dict) -> dict:
    """Process data in graph node."""
    result = await do_processing(state["input"])
    return {**state, "output": result}

# Wrap node with adapter
async def wrapped_process_node(state: dict) -> dict:
    return await adapter(state, process_node, "process_node")

# Build graph
graph = StateGraph(dict)
graph.add_node("process", wrapped_process_node)  # Wrapped node
graph.set_entry_point("process")
graph.set_finish_point("process")

# Compile and run
compiled = graph.compile()
result = await compiled.ainvoke({"input": "data"})
```

## Anti-Pattern Example
```python
# ❌ WRONG — Unwrapped node (no audit trail)
async def my_node(state: dict) -> dict:
    return await do_work(state)

graph.add_node("my_node", my_node)  # No packet emission!

# ❌ WRONG — Manual packet emission (duplicates logic)
async def my_node(state: dict) -> dict:
    await service.write_packet({"type": "start"})  # Manual
    result = await do_work(state)
    await service.write_packet({"type": "end"})    # Manual
    return result

# ✅ CORRECT — Use PacketNodeAdapter
async def wrapped_node(state: dict) -> dict:
    return await adapter(state, my_node, "my_node")

graph.add_node("my_node", wrapped_node)
```

## Packets Emitted
| Packet Type | When | Payload |
|-------------|------|---------|
| `node_start` | Before execution | `{node_name, state_keys}` |
| `node_complete` | After success | `{node_name, state_keys}` |
| `node_error` | On exception | `{node_name, error}` |

## Rules
1. ALL graph nodes MUST emit packets via adapter
2. Use `PacketNodeAdapter` for wrapping
3. Provide meaningful `node_name` for each node
4. Handle errors with packet emission before re-raise
5. Include `agent_id` for tracing

## AI Guidance
**DO:**
- Wrap all nodes with `PacketNodeAdapter`
- Include meaningful `node_name`
- Pass service instance to adapter
- Let adapter handle packet emission

**DO NOT:**
- Skip packet emission "for performance"
- Create nodes without adapter wrapping
- Emit packets manually inside nodes
- Use generic node names like "node1"
