# ADR 0043: Controller Profiles

## Status

Proposed

## Pattern

Define **Controller Profiles** that configure `UnifiedController` pipeline behavior. Each profile builds a different pipeline composition for different orchestration modes (simple direct, full governed, simulation-only).

## Context

L9's `UnifiedController` handles multiple orchestration modes with branching logic:
- Simple routing → execution (direct)
- Full 9-stage pipeline (governed)
- Compile → simulate → return plan (simulation)

Similar to executor profiles (ADR-0042), controller profiles make these modes declarative.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `orchestration/profiles/__init__.py` - Profile exports
- `orchestration/profiles/base_profile.py` - ControllerProfile protocol
- `orchestration/profiles/simple_direct_profile.py` - Minimal routing
- `orchestration/profiles/full_governed_profile.py` - All 9 stages
- `orchestration/profiles/sim_only_profile.py` - Simulation mode

### Files to Modify

- `orchestration/unified_controller.py` - Use profile-built pipeline

## Import Block

```python
from typing import Protocol

from orchestration.profiles import (
    ControllerProfile,
    SimpleDirectProfile,
    FullGovernedProfile,
    SimOnlyProfile,
    get_controller_profile,
)
from orchestration.pipeline import ControllerPipeline
```

## Minimal Implementation

```python
# orchestration/profiles/base_profile.py
"""Controller profile protocol."""

from typing import Protocol, runtime_checkable

from orchestration.pipeline import ControllerPipeline


@runtime_checkable
class ControllerProfile(Protocol):
    """
    Protocol for controller profiles.
    
    Each profile builds a pipeline with appropriate
    stages for its orchestration mode.
    """
    
    name: str
    
    def build_pipeline(self) -> ControllerPipeline:
        """Build the pipeline for this profile."""
        ...
```

```python
# orchestration/profiles/simple_direct_profile.py
"""Simple direct routing profile."""

from orchestration.pipeline import ControllerPipeline
from orchestration.pipeline.stages import (
    RoutingStage,
    ExecutionStage,
)


class SimpleDirectProfile:
    """
    Minimal orchestration profile.
    
    Pipeline: routing → execution
    
    Use for:
    - Simple tasks without complex planning
    - High-throughput, low-latency scenarios
    - Testing
    """
    
    name: str = "simple_direct"
    
    def build_pipeline(self) -> ControllerPipeline:
        """Build minimal 2-stage pipeline."""
        return ControllerPipeline(
            stages=[
                RoutingStage(),
                ExecutionStage(),
            ]
        )
```

```python
# orchestration/profiles/full_governed_profile.py
"""Full governed orchestration profile."""

from orchestration.pipeline import ControllerPipeline
from orchestration.pipeline.stages import (
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


class FullGovernedProfile:
    """
    Full 9-stage governed orchestration profile.
    
    Pipeline: routing → compile → validate → challenge → 
              deliberation → simulation → planning → 
              execution → reflection
    
    Use for:
    - Complex multi-step tasks
    - High-risk operations
    - Production with full governance
    """
    
    name: str = "full_governed"
    
    def build_pipeline(self) -> ControllerPipeline:
        """Build full 9-stage pipeline."""
        return ControllerPipeline(
            stages=[
                RoutingStage(),
                CompileStage(),
                ValidateStage(),
                ChallengeStage(),
                DeliberationStage(),
                SimulationStage(),
                PlanningStage(),
                ExecutionStage(),
                ReflectionStage(),
            ]
        )
```

```python
# orchestration/profiles/sim_only_profile.py
"""Simulation-only profile for planning without execution."""

from orchestration.pipeline import ControllerPipeline
from orchestration.pipeline.stages import (
    RoutingStage,
    CompileStage,
    SimulationStage,
)


class SimOnlyProfile:
    """
    Simulation-only orchestration profile.
    
    Pipeline: routing → compile → simulate → return plan
    
    Use for:
    - Plan preview before execution
    - Risk assessment
    - "What-if" analysis
    """
    
    name: str = "sim_only"
    
    def build_pipeline(self) -> ControllerPipeline:
        """Build simulation pipeline (no execution)."""
        return ControllerPipeline(
            stages=[
                RoutingStage(),
                CompileStage(),
                SimulationStage(return_plan=True),  # Return without executing
            ]
        )
```

## Usage Example

```python
# Refactored UnifiedController

class UnifiedController:
    """
    Orchestration controller using profile-built pipelines.
    """
    
    def __init__(self, profile: ControllerProfile):
        self._profile = profile
        self._pipeline = profile.build_pipeline()
    
    async def process_request(
        self,
        request: ControllerRequest,
        user_id: str,
        metadata: dict,
    ) -> ControllerResponse:
        """Process request through profile-configured pipeline."""
        
        # No conditionals — pipeline determined by profile
        pipeline = self._profile.build_pipeline()
        return await pipeline.run(request, user_id, metadata)


# Usage in api/server.py
profile_name = os.getenv("CONTROLLER_PROFILE", "full_governed")
profile = get_controller_profile(profile_name)
controller = UnifiedController(profile)

# Or per-request profile selection (advanced)
async def process_task(request: TaskRequest):
    if request.simulate_only:
        profile = SimOnlyProfile()
    elif request.fast_mode:
        profile = SimpleDirectProfile()
    else:
        profile = FullGovernedProfile()
    
    controller = UnifiedController(profile)
    return await controller.process_request(request, ...)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Branching logic inside controller
class UnifiedController:
    async def process_request(self, request, ...):
        if request.simulate_only:
            result = await self._routing_stage.run(...)
            result = await self._compile_stage.run(...)
            return await self._simulation_stage.run(...)
        
        elif request.fast_mode:
            result = await self._routing_stage.run(...)
            return await self._execution_stage.run(...)
        
        else:
            # Full 9-stage pipeline with lots of conditionals
            result = await self._routing_stage.run(...)
            if self._enable_validation:
                result = await self._validate_stage.run(...)
            # ... etc

# ✅ CORRECT — Profile determines pipeline
pipeline = self._profile.build_pipeline()
return await pipeline.run(request, user_id, metadata)
```

## Rules

1. All profiles MUST implement `ControllerProfile` protocol
2. `build_pipeline()` MUST return a complete, runnable pipeline
3. Profile selection CAN be per-request (unlike executor profiles)
4. Default profile MUST be `full_governed` for safety
5. `sim_only` MUST NOT execute any real actions
6. Profile names MUST match stage composition semantics

## AI Guidance

**DO:**

- Use `full_governed` for production tasks
- Use `simple_direct` for high-throughput simple tasks
- Use `sim_only` for plan preview and risk assessment
- Allow per-request profile override for advanced use cases

**DO NOT:**

- Mix profile logic with stage logic
- Create profiles with overlapping purposes
- Use `simple_direct` for complex or risky tasks
- Execute real actions in `sim_only` mode

## Related ADRs

- [ADR-0042: Execution Profiles](./0042-execution-profiles.md) - Same pattern for executor
- [ADR-0048: Pipeline Stage Organization](./0048-pipeline-stage-organization.md) - Stage directory structure
- [ADR-0040: Loop Stage Protocol](./0040-loop-stage-protocol.md) - Stage protocol pattern
