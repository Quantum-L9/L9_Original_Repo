# ADR 0049: Checkpoint Plan Snapshots

## Status

Proposed

## Pattern

Include **execution plan snapshots** in graph checkpoints to enable crash recovery with full plan context. When the system recovers from a checkpoint, it knows exactly what was being executed.

## Context

L9's current checkpoints store execution state but not the plan being executed. On crash recovery:
- We can restore to a checkpoint
- But we don't know what plan step was being executed
- Recovery requires manual plan reconstruction

Adding plan snapshots enables fully automatic recovery.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### Files to Modify

- `memory/checkpoint/postgres_saver.py` - Add plan snapshot field
- `memory/substrate_graph.py` - Store plan in Neo4j checkpoint node
- `orchestration/plan_executor.py` - Snapshot plan before checkpoint

### New Files (Optional)

- `core/schemas/plan.py` - Add `to_dict()` / `from_dict()` if missing

## Import Block

```python
from typing import Any, Dict, Optional
from uuid import UUID
import json

from core.schemas.plan import Plan
from memory.checkpoint import CheckpointManager
```

## Minimal Implementation

```python
# memory/checkpoint/models.py (or postgres_saver.py)
"""Enhanced checkpoint with plan snapshot."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
import json
import time


@dataclass
class GraphCheckpoint:
    """
    Checkpoint with execution plan snapshot.
    
    Fields:
    - execution_plan_snapshot: Serialized Plan for crash recovery
    - step_index: Current step being executed
    - state: Full execution state
    """
    
    checkpoint_id: UUID
    execution_plan_snapshot: Optional[Dict[str, Any]] = None  # NEW
    step_index: int = 0
    state: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.state is None:
            self.state = {}
    
    def to_neo4j_node(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "checkpoint_id": str(self.checkpoint_id),
            "execution_plan_snapshot": json.dumps(self.execution_plan_snapshot) if self.execution_plan_snapshot else None,
            "step_index": self.step_index,
            "state": json.dumps(self.state),
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_neo4j_node(cls, node_data: Dict[str, Any]) -> "GraphCheckpoint":
        """Create from Neo4j node."""
        plan_snapshot = None
        if node_data.get("execution_plan_snapshot"):
            try:
                plan_snapshot = json.loads(node_data["execution_plan_snapshot"])
            except json.JSONDecodeError:
                pass
        
        state = {}
        if node_data.get("state"):
            try:
                state = json.loads(node_data["state"])
            except json.JSONDecodeError:
                pass
        
        return cls(
            checkpoint_id=UUID(node_data["checkpoint_id"]),
            execution_plan_snapshot=plan_snapshot,
            step_index=node_data.get("step_index", 0),
            state=state,
            timestamp=node_data.get("timestamp"),
        )
```

```python
# memory/substrate_graph.py additions
"""Graph checkpoint methods with plan snapshots."""

from uuid import uuid4
from typing import Optional, Tuple


class SubstrateGraph:
    """Neo4j graph operations."""
    
    async def create_checkpoint(
        self,
        execution_plan,  # Plan object
        current_step_index: int,
        state: dict,
    ) -> str:
        """
        Create checkpoint with plan snapshot.
        
        Args:
            execution_plan: Current Plan being executed
            current_step_index: Which step we're on
            state: Additional execution state
        
        Returns:
            Checkpoint ID
        """
        checkpoint_id = uuid4()
        
        # Serialize plan
        plan_dict = execution_plan.to_dict() if hasattr(execution_plan, 'to_dict') else {}
        
        checkpoint = GraphCheckpoint(
            checkpoint_id=checkpoint_id,
            execution_plan_snapshot=plan_dict,
            step_index=current_step_index,
            state=state,
        )
        
        node_props = checkpoint.to_neo4j_node()
        
        await self._neo4j.execute(
            """
            CREATE (cp:Checkpoint {
                checkpoint_id: $checkpoint_id,
                execution_plan_snapshot: $execution_plan_snapshot,
                step_index: $step_index,
                state: $state,
                timestamp: $timestamp
            })
            RETURN cp.checkpoint_id
            """,
            node_props,
        )
        
        return str(checkpoint_id)
    
    async def restore_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Tuple["Plan", int, dict]]:
        """
        Restore checkpoint with plan.
        
        Returns:
            Tuple of (Plan, step_index, state) or None if not found
        """
        result = await self._neo4j.fetch_one(
            """
            MATCH (cp:Checkpoint {checkpoint_id: $checkpoint_id})
            RETURN cp
            """,
            {"checkpoint_id": checkpoint_id},
        )
        
        if not result:
            return None
        
        checkpoint = GraphCheckpoint.from_neo4j_node(result["cp"])
        
        # Deserialize plan
        from core.schemas.plan import Plan
        plan = Plan.from_dict(checkpoint.execution_plan_snapshot) if checkpoint.execution_plan_snapshot else None
        
        return plan, checkpoint.step_index, checkpoint.state
```

```python
# orchestration/plan_executor.py checkpoint integration
"""Plan executor with checkpoint snapshots."""


class PlanExecutor:
    """Executes plans with checkpoint support."""
    
    async def execute_plan(self, plan: "Plan") -> "ExecutionResult":
        """Execute plan with checkpoint snapshots."""
        
        for step_index, step in enumerate(plan.steps):
            # Create checkpoint before each step
            checkpoint_id = await self._graph.create_checkpoint(
                execution_plan=plan,
                current_step_index=step_index,
                state={"last_result": self._last_result},
            )
            
            try:
                result = await self._execute_step(step)
                self._last_result = result
            except Exception as e:
                # On failure, checkpoint allows recovery
                raise ExecutionError(
                    f"Failed at step {step_index}",
                    checkpoint_id=checkpoint_id,
                ) from e
        
        return ExecutionResult(...)
    
    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
    ) -> "ExecutionResult":
        """Resume execution from checkpoint."""
        
        restored = await self._graph.restore_checkpoint(checkpoint_id)
        if not restored:
            raise CheckpointNotFoundError(checkpoint_id)
        
        plan, step_index, state = restored
        self._last_result = state.get("last_result")
        
        # Resume from step_index
        for i, step in enumerate(plan.steps):
            if i < step_index:
                continue  # Skip completed steps
            
            result = await self._execute_step(step)
            self._last_result = result
        
        return ExecutionResult(...)
```

## Usage Example

```python
# Crash recovery scenario

# 1. Execution starts
executor = PlanExecutor(graph=substrate_graph)
try:
    result = await executor.execute_plan(plan)
except ExecutionError as e:
    # Crash occurred, checkpoint_id is available
    failed_checkpoint = e.checkpoint_id
    logger.error(f"Execution failed, checkpoint: {failed_checkpoint}")

# 2. Later: Resume from checkpoint
result = await executor.resume_from_checkpoint(failed_checkpoint)
# Execution continues from where it left off


# Checkpoint inspection
checkpoint_id = "abc-123-..."
plan, step_index, state = await substrate_graph.restore_checkpoint(checkpoint_id)
print(f"Plan: {plan.name}")
print(f"Step: {step_index}/{len(plan.steps)}")
print(f"State: {state}")
```

## Anti-Pattern Example

```python
# ❌ WRONG — Checkpoint without plan
async def create_checkpoint(self, step_index, state):
    # No plan snapshot — can't resume intelligently
    return await self._db.insert({
        "step_index": step_index,
        "state": state,
    })

# On recovery:
restored = await self.restore_checkpoint(checkpoint_id)
# We know step_index=5, but what plan? Manual reconstruction needed

# ✅ CORRECT — Checkpoint includes plan
async def create_checkpoint(self, plan, step_index, state):
    return await self._db.insert({
        "execution_plan_snapshot": plan.to_dict(),  # Full plan
        "step_index": step_index,
        "state": state,
    })

# On recovery:
plan, step_index, state = await self.restore_checkpoint(checkpoint_id)
# Automatic resume from step 5 of the original plan
```

## Rules

1. Checkpoints MUST include serialized execution plan
2. Plan MUST implement `to_dict()` / `from_dict()` for serialization
3. Checkpoint creation MUST happen before each risky step
4. Recovery MUST be automatic (no manual plan reconstruction)
5. Checkpoint metadata MUST include step_index and timestamp
6. Plan snapshots SHOULD be stored in Neo4j for graph queries

## AI Guidance

**DO:**

- Include full plan in every checkpoint
- Create checkpoints before each step (not after)
- Implement `to_dict()` / `from_dict()` on Plan class
- Log checkpoint IDs in error messages

**DO NOT:**

- Store checkpoints without plan context
- Assume plan can be reconstructed from step_index alone
- Skip checkpoints for "simple" steps
- Mutate plan after checkpoint creation

## Related ADRs

- [ADR-0046: Pipeline Stage Organization](./0046-pipeline-stage-organization.md) - Stages create checkpoints
- [ADR-0012: Memory DAG Pipeline](./0012-memory-dag-pipeline.md) - Checkpoint storage
- [ADR-0047: Memory Facade Decomposition](./0047-memory-facade-decomposition.md) - CheckpointService
