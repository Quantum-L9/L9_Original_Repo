# ADR 0045: Online/Offline Execution Split

## Status

Proposed

## Pattern

Separate **online execution** (serving user requests) from **offline analytics** (self-reflection, DORA writes, kernel evolution) into distinct services. The executor handles online work; an `ExecutionAnalyticsService` handles offline work.

## Context

L9's `AgentExecutorService` mixes two fundamentally different concerns:
1. **Online** — Serving user requests with low latency
2. **Offline** — Analytics, reflection, DORA metadata, kernel evolution

These have different latency requirements, scaling characteristics, and failure modes. Separating them enables:
- Turning off analytics in "low-cost" modes
- Routing analytics to background workers
- Independent scaling and monitoring

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/agents/analytics/__init__.py` - Analytics exports
- `core/agents/analytics/execution_analytics_service.py` - Offline analytics
- `core/agents/analytics/dora_writer.py` - DORA metadata updates
- `core/agents/analytics/kernel_evolution_planner.py` - Evolution packets

### Files to Modify

- `core/agents/executor.py` - Delegate analytics to service

## Import Block

```python
from core.agents.analytics import (
    ExecutionAnalyticsService,
    DoraWriter,
    KernelEvolutionPlanner,
)
from core.agents.schemas import AgentTask, ExecutionResult
from core.agents.agent_instance import AgentInstance
```

## Minimal Implementation

```python
# core/agents/analytics/execution_analytics_service.py
"""Offline analytics service for execution post-processing."""

import logging
from typing import Optional

from core.agents.schemas import AgentTask, ExecutionResult
from core.agents.agent_instance import AgentInstance

logger = logging.getLogger(__name__)


class ExecutionAnalyticsService:
    """
    Handles offline analytics after execution completes.
    
    Responsibilities:
    - DORA trace generation
    - Self-reflection persistence
    - Kernel evolution planning
    - Performance metrics
    
    Can be:
    - Disabled for fast/low-cost modes
    - Routed to background worker queue
    - Scaled independently from executor
    """
    
    def __init__(
        self,
        dora_writer=None,
        reflection_service=None,
        evolution_planner=None,
        enabled: bool = True,
    ):
        self._dora_writer = dora_writer
        self._reflection_service = reflection_service
        self._evolution_planner = evolution_planner
        self._enabled = enabled
    
    async def on_execution_completed(
        self,
        task: AgentTask,
        result: ExecutionResult,
        instance: AgentInstance,
    ) -> None:
        """
        Process completed execution for analytics.
        
        Called after task completion. Non-blocking to user response.
        """
        if not self._enabled:
            logger.debug("Analytics disabled, skipping")
            return
        
        # 1. Write DORA trace
        if self._dora_writer:
            await self._dora_writer.write_trace(task, result, instance)
        
        # 2. Persist reflection insights
        if self._reflection_service:
            await self._reflection_service.persist(task, result, instance)
        
        # 3. Plan kernel evolution
        if self._evolution_planner:
            await self._evolution_planner.plan(task, result, instance)
        
        logger.info(f"Analytics completed for task {task.task_id}")
    
    async def on_execution_failed(
        self,
        task: AgentTask,
        error: Exception,
        instance: AgentInstance,
    ) -> None:
        """Process failed execution for analytics."""
        if not self._enabled:
            return
        
        # Log failure patterns for learning
        if self._reflection_service:
            await self._reflection_service.persist_failure(task, error, instance)
```

```python
# core/agents/analytics/dora_writer.py
"""DORA metadata writer for execution traces."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DoraWriter:
    """
    Writes DORA metadata blocks to source files.
    
    Updates __dora_meta__ blocks with:
    - Execution timestamps
    - Tool call counts
    - Performance metrics
    - Error patterns
    """
    
    def __init__(self, substrate_service=None):
        self._substrate = substrate_service
    
    async def write_trace(
        self,
        task,
        result,
        instance,
    ) -> None:
        """Write DORA trace for execution."""
        
        trace_data = {
            "task_id": str(task.task_id),
            "agent_id": instance.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": result.status,
            "tool_calls": len(result.tool_calls or []),
            "duration_ms": result.metadata.get("duration_ms"),
        }
        
        # Persist to substrate
        if self._substrate:
            await self._substrate.ingest_dora_trace(trace_data)
        
        logger.debug(f"DORA trace written: {task.task_id}")
```

```python
# core/agents/analytics/kernel_evolution_planner.py
"""Kernel evolution planning from execution patterns."""

import logging

logger = logging.getLogger(__name__)


class KernelEvolutionPlanner:
    """
    Plans kernel evolution based on execution patterns.
    
    Analyzes:
    - Repeated tool usage patterns
    - Error frequencies
    - User correction signals
    
    Emits:
    - Evolution packets for kernel updates
    """
    
    def __init__(self, packet_emitter=None, threshold: int = 10):
        self._emitter = packet_emitter
        self._threshold = threshold
    
    async def plan(
        self,
        task,
        result,
        instance,
    ) -> None:
        """Analyze execution for kernel evolution opportunities."""
        
        # Skip failed executions
        if result.status != "completed":
            return
        
        # Analyze patterns
        evolution_candidates = await self._analyze_patterns(
            task, result, instance
        )
        
        # Emit evolution packets if threshold met
        for candidate in evolution_candidates:
            if candidate["frequency"] >= self._threshold:
                await self._emit_evolution_packet(candidate)
    
    async def _analyze_patterns(self, task, result, instance) -> list:
        """Analyze execution for evolution patterns."""
        # Implementation: pattern extraction
        return []
    
    async def _emit_evolution_packet(self, candidate: dict) -> None:
        """Emit kernel evolution packet."""
        if self._emitter:
            await self._emitter.emit_evolution_packet(candidate)
```

## Usage Example

```python
# Executor delegates to analytics service

class AgentExecutorService:
    def __init__(self, ..., analytics: ExecutionAnalyticsService = None):
        self._analytics = analytics
    
    async def start_agent_task(
        self,
        task: AgentTask,
        instance: AgentInstance,
    ) -> ExecutionResult:
        """Execute task and delegate analytics."""
        
        try:
            # Online: Execute task
            result = await self._run_execution_loop(instance)
            
            # Offline: Analytics (non-blocking)
            if self._analytics:
                await self._analytics.on_execution_completed(task, result, instance)
            
            return result
            
        except Exception as e:
            # Offline: Failure analytics
            if self._analytics:
                await self._analytics.on_execution_failed(task, e, instance)
            raise


# Production: Full analytics
analytics = ExecutionAnalyticsService(
    dora_writer=DoraWriter(substrate_service),
    reflection_service=ReflectionService(),
    evolution_planner=KernelEvolutionPlanner(packet_emitter),
    enabled=True,
)
executor = ExecutorBuilder().with_dependency("analytics", analytics).build()


# Fast mode: Analytics disabled
analytics = ExecutionAnalyticsService(enabled=False)
executor = ExecutorBuilder().with_dependency("analytics", analytics).build()


# Background worker mode: Queue analytics
class QueuedAnalyticsService(ExecutionAnalyticsService):
    async def on_execution_completed(self, task, result, instance):
        # Queue for background processing instead of inline
        await self._task_queue.enqueue(
            "analytics.process",
            {"task_id": task.task_id, "result": result.dict()},
        )
```

## Anti-Pattern Example

```python
# ❌ WRONG — Analytics mixed with online execution
class AgentExecutorService:
    async def start_agent_task(self, task, instance):
        result = await self._run_execution_loop(instance)
        
        # Analytics blocking user response
        await self._write_dora_trace(task, result)  # Slow!
        await self._persist_reflection(task, result)  # Slow!
        await self._plan_evolution(task, result)  # Slow!
        
        return result  # User waits for all analytics

# ✅ CORRECT — Analytics delegated and optionally backgrounded
result = await self._run_execution_loop(instance)
await self._analytics.on_execution_completed(task, result, instance)  # Fast or backgrounded
return result  # User gets response quickly
```

## Rules

1. Executor MUST NOT directly handle DORA, reflection, or evolution
2. Analytics MUST be optional (executor works without it)
3. Analytics MUST NOT block user response (or queue to background)
4. Analytics service MUST be disableable via `enabled=False`
5. Analytics SHOULD be routeable to background workers
6. Analytics failures MUST NOT fail the execution

## AI Guidance

**DO:**

- Delegate all analytics to `ExecutionAnalyticsService`
- Make analytics optional for fast modes
- Queue analytics to background workers for latency-sensitive paths
- Log analytics failures without propagating them

**DO NOT:**

- Call DORA, reflection, or evolution directly from executor
- Block user response on analytics
- Fail execution if analytics fails
- Mix online and offline concerns in one method

## Related ADRs

- [ADR-0014: DORA Metadata Block](./0014-dora-metadata-block.md) - DORA format
- [ADR-0042: Execution Profiles](./0042-execution-profiles.md) - Profiles can disable analytics
- [ADR-0012: Memory DAG Pipeline](./0012-memory-dag-pipeline.md) - Analytics writes to memory
