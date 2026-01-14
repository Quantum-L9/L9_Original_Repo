# L9 Memory Routing Fix Guide

**Author:** Manus AI
**Date:** Jan 12, 2026
**Version:** 1.0

## Overview

This guide provides step-by-step instructions to fix the memory routing issues identified in the L9 Secure AI OS. The fixes address the dual ingestion pipelines, manual DAG execution, and lack of conditional routing.

## Issue 1: Manual DAG Execution

### Problem

The `SubstrateDAG.run()` method manually calls each node sequentially instead of using LangGraph's execution engine. This is located in `memory/substrate_graph.py` lines 770-820.

### Root Cause

The code was written to inject dependencies (repository, semantic_service) into nodes, but LangGraph doesn't directly support dependency injection in the traditional sense.

### Solution

Use LangGraph's `config` parameter to pass dependencies to nodes. Refactor `SubstrateDAG.run()` to use `graph.ainvoke()` or `graph.astream()`.

### Implementation Steps

**Step 1:** Modify node functions to accept dependencies from config

```python
# memory/substrate_graph.py

async def intake_node(
    state: SubstrateGraphState,
    config: Optional[dict] = None,
) -> SubstrateGraphState:
    """Entry node: validates and normalizes the PacketEnvelope."""
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
    logger.debug("intake_node: Processing packet")
    # ... rest of implementation
```

**Step 2:** Update all node functions similarly

Apply the same pattern to:
- `reasoning_node`
- `memory_write_node`
- `semantic_embed_node`
- `extract_insights_node`
- `store_insights_node`
- `world_model_trigger_node`
- `checkpoint_node`

**Step 3:** Refactor `SubstrateDAG.run()` to use LangGraph execution

```python
# memory/substrate_graph.py:770

async def run(self, envelope: PacketEnvelope) -> PacketWriteResult:
    """Run the substrate DAG for a PacketEnvelope."""
    
    # Prepare initial state
    initial_state: SubstrateGraphState = {
        "envelope": envelope.model_dump(mode="json"),
        "reasoning_block": None,
        "written_tables": [],
        "embedding_id": None,
        "saved_checkpoint_id": None,
        "insights": [],
        "facts": [],
        "world_model_triggered": False,
        "errors": [],
    }

    # Prepare config with dependencies
    config = {
        "configurable": {
            "repository": self._repository,
            "semantic_service": self._semantic_service,
            "world_model_service": self._world_model_service,
        }
    }

    # Use LangGraph to execute the graph
    try:
        final_state = await self._graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"DAG execution failed: {e}")
        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=[],
            status="error",
            error_message=str(e),
        )

    # Build result from final state
    errors = final_state.get("errors", [])
    if errors:
        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=final_state.get("written_tables", []),
            status="error",
            error_message="; ".join(errors),
        )

    return PacketWriteResult(
        packet_id=envelope.packet_id,
        written_tables=final_state.get("written_tables", []),
        status="ok",
    )
```

## Issue 2: Lack of Conditional Routing

### Problem

All packets flow through the same linear sequence of nodes, even when certain operations (like semantic embedding) are not needed.

### Solution

Add conditional edges to the graph to route packets based on their characteristics.

### Implementation Steps

**Step 1:** Create routing functions

```python
# memory/substrate_graph.py (after node definitions)

def route_after_reasoning(state: SubstrateGraphState) -> list[str]:
    """
    Determine which nodes to execute after reasoning.
    
    Returns list of node names to execute in parallel.
    """
    envelope = state.get("envelope", {})
    packet_type = envelope.get("packet_type", "")
    payload = envelope.get("payload", {})
    
    # Always execute memory_write
    next_nodes = ["memory_write_node"]
    
    # Conditionally add semantic_embed based on content
    should_embed = (
        "semantic" in packet_type.lower()
        or "memory" in packet_type.lower()
        or "text" in payload
        or "content" in payload
    )
    
    if should_embed:
        next_nodes.append("semantic_embed_node")
    
    return next_nodes


def route_to_insights(state: SubstrateGraphState) -> str:
    """Route to insights extraction after memory write and optional embedding."""
    return "extract_insights_node"
```

**Step 2:** Update graph construction with conditional edges

```python
# memory/substrate_graph.py:704

def build_substrate_graph() -> StateGraph:
    """Build the LangGraph DAG for memory substrate processing."""
    
    graph = StateGraph(SubstrateGraphState)

    # Add nodes
    graph.add_node("intake_node", intake_node)
    graph.add_node("reasoning_node", reasoning_node)
    graph.add_node("memory_write_node", memory_write_node)
    graph.add_node("semantic_embed_node", semantic_embed_node)
    graph.add_node("extract_insights_node", extract_insights_node)
    graph.add_node("store_insights_node", store_insights_node)
    graph.add_node("world_model_trigger_node", world_model_trigger_node)
    graph.add_node("checkpoint_node", checkpoint_node)

    # Linear edges
    graph.set_entry_point("intake_node")
    graph.add_edge("intake_node", "reasoning_node")
    
    # Conditional routing after reasoning
    # Note: LangGraph's add_conditional_edges for parallel execution
    # For simplicity, we'll use sequential conditional routing
    
    def should_embed(state: SubstrateGraphState) -> str:
        envelope = state.get("envelope", {})
        packet_type = envelope.get("packet_type", "")
        payload = envelope.get("payload", {})
        
        should_embed = (
            "semantic" in packet_type.lower()
            or "memory" in packet_type.lower()
            or "text" in payload
            or "content" in payload
        )
        
        return "embed" if should_embed else "skip_embed"
    
    graph.add_edge("reasoning_node", "memory_write_node")
    
    graph.add_conditional_edges(
        "memory_write_node",
        should_embed,
        {
            "embed": "semantic_embed_node",
            "skip_embed": "extract_insights_node",
        }
    )
    
    graph.add_edge("semantic_embed_node", "extract_insights_node")
    graph.add_edge("extract_insights_node", "store_insights_node")
    graph.add_edge("store_insights_node", "world_model_trigger_node")
    graph.add_edge("world_model_trigger_node", "checkpoint_node")
    graph.add_edge("checkpoint_node", END)

    return graph.compile()
```

## Issue 3: Dual Ingestion Pipelines

### Problem

Both `IngestionPipeline` (in `memory/ingestion.py`) and `SubstrateDAG` exist, creating confusion and potential for bugs.

### Solution

Deprecate `IngestionPipeline` and migrate all logic to `SubstrateDAG` nodes.

### Implementation Steps

**Step 1:** Mark `IngestionPipeline` as deprecated

```python
# memory/ingestion.py:40

import warnings

class IngestionPipeline:
    """
    DEPRECATED: Use SubstrateDAG via ingest_packet() instead.
    
    This class will be removed in v2.0.0.
    """
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "IngestionPipeline is deprecated. Use SubstrateDAG via ingest_packet().",
            DeprecationWarning,
            stacklevel=2,
        )
        # ... rest of init
```

**Step 2:** Ensure all `IngestionPipeline` logic is in DAG nodes

Review the `IngestionPipeline.ingest()` method and ensure all operations are covered by DAG nodes:

- ✅ Validation → `intake_node`
- ✅ Packet storage → `memory_write_node`
- ✅ Embedding → `semantic_embed_node`
- ✅ Artifacts → Add to `memory_write_node` if needed
- ✅ Lineage → Add to `memory_write_node` if needed
- ✅ Neo4j sync → Already in ingestion.py as `_sync_to_graph`

**Step 3:** Plan removal timeline

- **v1.2.0:** Mark as deprecated (add warnings)
- **v1.5.0:** Remove all internal usage
- **v2.0.0:** Delete `IngestionPipeline` class

## Issue 4: Overly Complex Entry Point

### Problem

The routing flow goes through multiple layers: `ingest_packet` → `MemorySubstrateService.write_packet` → `SubstrateDAG.run`.

### Solution

Simplify to: `ingest_packet` → `SubstrateDAG.run`.

### Implementation Steps

**Step 1:** Update `ingest_packet` to directly use DAG

```python
# memory/ingestion.py:597

async def ingest_packet(
    packet_in: PacketEnvelopeIn,
    dag: Optional[SubstrateDAG] = None,
) -> PacketWriteResult:
    """
    Canonical packet ingestion entrypoint.
    
    This is the SINGLE POINT OF ENTRY for all packet ingestion.
    All runtime packets MUST pass through this function.
    """
    from memory.substrate_graph import get_substrate_dag
    
    if dag is None:
        try:
            dag = await get_substrate_dag()
        except RuntimeError:
            raise RuntimeError(
                "Memory system not initialized. Call memory.init_service() at startup."
            )
    
    # Convert to envelope
    envelope = packet_in.to_envelope()
    
    # Run through DAG
    return await dag.run(envelope)
```

**Step 2:** Update `MemorySubstrateService` to delegate to `ingest_packet`

```python
# memory/substrate_service.py:158

async def write_packet(
    self,
    packet_in: PacketEnvelopeIn,
    tenant_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    role: str = "end_user",
) -> PacketWriteResult:
    """Submit a packet to the substrate for processing."""
    
    # Set RLS scope if provided
    if tenant_id and org_id and user_id:
        await self.set_session_scope(tenant_id, org_id, user_id, role)
    
    # Delegate to canonical entry point
    from memory.ingestion import ingest_packet
    return await ingest_packet(packet_in, dag=self._dag)
```

## Testing the Fixes

### Unit Tests

Create unit tests for each node function:

```python
# tests/memory/test_substrate_graph.py

import pytest
from memory.substrate_graph import intake_node, SubstrateGraphState

@pytest.mark.asyncio
async def test_intake_node_validates_packet():
    state: SubstrateGraphState = {
        "envelope": {"packet_type": "test", "payload": {"key": "value"}},
        "errors": [],
        # ... other fields
    }
    
    result = await intake_node(state)
    
    assert result["errors"] == []
    assert result["envelope"]["packet_id"] is not None
```

### Integration Tests

Test the full DAG execution:

```python
# tests/memory/test_dag_integration.py

import pytest
from memory.substrate_graph import SubstrateDAG
from memory.substrate_models import PacketEnvelopeIn

@pytest.mark.asyncio
async def test_dag_executes_full_pipeline(mock_repository, mock_semantic_service):
    dag = SubstrateDAG(
        repository=mock_repository,
        semantic_service=mock_semantic_service,
    )
    
    packet = PacketEnvelopeIn(
        packet_type="test_memory",
        payload={"text": "Test content for embedding"},
    )
    
    result = await dag.run(packet.to_envelope())
    
    assert result.status == "ok"
    assert "packet_store" in result.written_tables
    assert "semantic_memory" in result.written_tables
```

## Rollout Plan

1. **Phase 1 (Week 1):** Implement Issue 1 fix (native LangGraph execution)
2. **Phase 2 (Week 2):** Implement Issue 2 fix (conditional routing)
3. **Phase 3 (Week 3):** Implement Issue 3 fix (deprecate IngestionPipeline)
4. **Phase 4 (Week 4):** Implement Issue 4 fix (simplify entry point)
5. **Phase 5 (Week 5):** Comprehensive testing and validation
6. **Phase 6 (Week 6):** Deploy to staging and production

## Success Metrics

- ✅ All packets route through `SubstrateDAG` using LangGraph execution
- ✅ Conditional routing reduces unnecessary node executions by 30%
- ✅ `IngestionPipeline` usage drops to 0%
- ✅ Memory ingestion latency improves by 15%
- ✅ Zero routing-related bugs in production for 30 days

## Conclusion

These fixes will transform the L9 memory routing system from a fragile, manually-orchestrated pipeline into a robust, graph-based architecture that fully leverages LangGraph's capabilities. The result will be a more maintainable, scalable, and performant memory management system.
