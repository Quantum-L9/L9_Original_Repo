# ADR 0046: Pipeline Stage Organization

## Status

Proposed

## Pattern

Organize orchestration pipeline stages in a dedicated directory structure: `orchestration/pipeline/stages/`. Each stage is a separate file, ≤ 200 lines, with a single `execute()` method and protocol-based dependencies.

## Context

L9's `orchestration/` directory is flat with monolithic files:

- `unified_controller.py` (~800 lines)
- `plan_executor.py` (~700 lines)

These files contain multiple pipeline phases inline. The stage-based organization enables:

- Independent testing of each stage
- Clear stage boundaries
- Pluggable stage implementations
- < 200 line files

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Directory Structure

```
orchestration/
├── __init__.py
├── pipeline/
│   ├── __init__.py
│   ├── context.py              # PipelineContext dataclass
│   ├── pipeline.py             # ControllerPipeline class
│   └── stages/
│       ├── __init__.py
│       ├── base_stage.py       # PipelineStage protocol
│       ├── routing_stage.py
│       ├── compile_stage.py
│       ├── validate_stage.py
│       ├── challenge_stage.py
│       ├── deliberation_stage.py
│       ├── simulation_stage.py
│       ├── planning_stage.py
│       ├── execution_stage.py
│       └── reflection_stage.py
├── unified_controller.py       # Uses pipeline, much smaller
├── plan_executor.py            # Simplified
└── ... (existing files)
```

### Files to Create

- `orchestration/pipeline/__init__.py`
- `orchestration/pipeline/context.py`
- `orchestration/pipeline/pipeline.py`
- `orchestration/pipeline/stages/__init__.py`
- `orchestration/pipeline/stages/base_stage.py`
- 9 stage files (routing, compile, validate, challenge, deliberation, simulation, planning, execution, reflection)

## Import Block

```python
from orchestration.pipeline import (
    ControllerPipeline,
    PipelineContext,
)
from orchestration.pipeline.stages import (
    PipelineStage,
    RoutingStage,
    CompileStage,
    ValidateStage,
    ChallengeStage,
    DeliberationStage,
    SimulationStage,
    PlanningStage,
    ExecutionStage,
    ReflectionStage,
)
```

## Minimal Implementation

```python
# orchestration/pipeline/stages/base_stage.py
"""Pipeline stage protocol."""

from typing import Protocol, runtime_checkable

from orchestration.pipeline.context import PipelineContext


@runtime_checkable
class PipelineStage(Protocol):
    """
    Protocol for orchestration pipeline stages.

    Each stage:
    - Receives PipelineContext
    - Performs one orchestration concern
    - Returns (potentially modified) context
    - Is ≤ 200 lines
    """

    name: str

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Execute this stage and return updated context."""
        ...
```

```python
# orchestration/pipeline/context.py
"""Pipeline context passed between stages."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.agents.schemas import AgentTask


@dataclass
class PipelineContext:
    """
    Context passed through orchestration pipeline.

    Immutable-style: stages return new context with modifications.
    """

    request: Any  # Original request
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Stage outputs (populated as pipeline progresses)
    routed_target: Optional[str] = None
    compiled_ir: Optional[Any] = None
    validation_result: Optional[Any] = None
    challenge_result: Optional[Any] = None
    deliberation_result: Optional[Any] = None
    simulation_result: Optional[Any] = None
    plan: Optional[Any] = None
    execution_result: Optional[Any] = None
    reflection_insights: Optional[Any] = None

    # Control flow
    status: str = "running"
    error: Optional[str] = None
    skip_remaining: bool = False

    def with_status(self, status: str) -> "PipelineContext":
        """Return context with updated status."""
        return PipelineContext(
            request=self.request,
            user_id=self.user_id,
            metadata=self.metadata,
            routed_target=self.routed_target,
            compiled_ir=self.compiled_ir,
            validation_result=self.validation_result,
            challenge_result=self.challenge_result,
            deliberation_result=self.deliberation_result,
            simulation_result=self.simulation_result,
            plan=self.plan,
            execution_result=self.execution_result,
            reflection_insights=self.reflection_insights,
            status=status,
            error=self.error,
            skip_remaining=self.skip_remaining,
        )
```

```python
# orchestration/pipeline/pipeline.py
"""Controller pipeline orchestrator."""

import logging
from typing import List

from orchestration.pipeline.context import PipelineContext
from orchestration.pipeline.stages import PipelineStage

logger = logging.getLogger(__name__)


class ControllerPipeline:
    """
    Orchestrates execution of pipeline stages.

    Runs stages in sequence, passing context through.
    Stops on terminal status or error.
    """

    def __init__(self, stages: List[PipelineStage]):
        self._stages = stages

    async def run(
        self,
        request: Any,
        user_id: str,
        metadata: dict = None,
    ) -> PipelineContext:
        """
        Run the pipeline with given request.

        Returns:
            Final context with all stage outputs.
        """
        ctx = PipelineContext(
            request=request,
            user_id=user_id,
            metadata=metadata or {},
        )

        for stage in self._stages:
            logger.debug(f"Running stage: {stage.name}")

            ctx = await stage.execute(ctx)

            if ctx.status in {"completed", "failed", "blocked"}:
                logger.info(f"Pipeline stopped at {stage.name}: {ctx.status}")
                break

            if ctx.skip_remaining:
                logger.info(f"Pipeline skipping remaining stages after {stage.name}")
                break

        return ctx
```

```python
# orchestration/pipeline/stages/routing_stage.py
"""Routing stage — determines execution target."""

import logging
from orchestration.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class RoutingStage:
    """
    Routes request to appropriate execution target.

    Analyzes:
    - Request type and complexity
    - Agent capabilities
    - Resource availability

    Outputs:
    - routed_target in context
    """

    name: str = "routing"

    def __init__(self, router_service=None):
        self._router = router_service

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Route request to target."""

        if self._router:
            target = await self._router.route(ctx.request)
        else:
            # Default routing
            target = "default"

        logger.info(f"Routed to: {target}")

        return PipelineContext(
            request=ctx.request,
            user_id=ctx.user_id,
            metadata=ctx.metadata,
            routed_target=target,
            status=ctx.status,
        )
```

## Usage Example

```python
# Refactored UnifiedController

class UnifiedController:
    """Simplified controller using pipeline."""

    def __init__(self, pipeline: ControllerPipeline):
        self._pipeline = pipeline

    async def process_request(
        self,
        request,
        user_id: str,
        metadata: dict = None,
    ):
        """Process request through pipeline."""
        ctx = await self._pipeline.run(request, user_id, metadata)
        return self._build_response(ctx)

    def _build_response(self, ctx: PipelineContext):
        """Build response from context."""
        if ctx.status == "completed":
            return ControllerResponse(
                output=ctx.execution_result,
                plan=ctx.plan,
                metadata=ctx.metadata,
            )
        else:
            return ControllerResponse(
                error=ctx.error,
                status=ctx.status,
            )


# Building pipeline with stages
pipeline = ControllerPipeline([
    RoutingStage(router_service),
    CompileStage(ir_compiler),
    ValidateStage(validator),
    ChallengeStage(challenger),
    DeliberationStage(deliberator),
    SimulationStage(simulator),
    PlanningStage(planner),
    ExecutionStage(executor),
    ReflectionStage(reflection_service),
])

controller = UnifiedController(pipeline)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Phases inline in controller (current state)
class UnifiedController:
    async def process_request(self, request, user_id, metadata):
        # Phase 1: Routing (inline)
        target = await self._route(request)

        # Phase 2: Compile (inline)
        ir = await self._compile(request)

        # Phase 3: Validate (inline)
        validation = await self._validate(ir)

        # ... 6 more phases inline ...

        # Phase 9: Reflection (inline)
        await self._reflect(result)

        return result

# ✅ CORRECT — Stages in separate files, pipeline orchestrates
ctx = await self._pipeline.run(request, user_id, metadata)
return self._build_response(ctx)
```

## Rules

1. Each stage MUST be a separate file in `orchestration/pipeline/stages/`
2. Each stage MUST be ≤ 200 lines
3. Each stage MUST implement `PipelineStage` protocol
4. Stages MUST NOT depend on other stages — only on context
5. Stage dependencies (IR compiler, simulator) MUST be injected
6. Pipeline MUST handle stage errors gracefully
7. Context MUST carry all inter-stage data

## AI Guidance

**DO:**

- Create one file per stage
- Keep stages under 200 lines
- Inject dependencies via constructor
- Pass all data via PipelineContext
- Test stages in isolation

**DO NOT:**

- Put multiple stages in one file
- Access controller internals from stages
- Skip stages conditionally inside stage code (use context.skip_remaining)
- Mutate context in place — return new context

## Related ADRs

- [ADR-0040: Loop Stage Protocol](./0040-loop-stage-protocol.md) - Similar pattern for executor
- [ADR-0043: Controller Profiles](./0043-controller-profiles.md) - Profiles compose stages
- [ADR-0041: Executor Builder Pattern](./0041-executor-builder-pattern.md) - Builder pattern
