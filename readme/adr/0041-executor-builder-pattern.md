# ADR 0041: Executor Builder Pattern

## Status

Proposed

## Pattern

Use a **builder pattern** to compose `AgentExecutorService` with configurable stages and policies. The builder allows different deployment profiles to assemble different executor configurations without subclassing.

## Context

L9's `AgentExecutorService` constructor directly instantiates its dependencies and stages. This makes it difficult to:

- Create different executor configurations for testing vs production
- Swap policies (prompt defense, reflection) per deployment
- Compose different stage pipelines for different use cases

The builder pattern separates **what** the executor does (execution logic) from **how** it's assembled (configuration).

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/agents/executor_builder.py` - ExecutorBuilder class
- `core/agents/executor_config.py` - ExecutorConfig dataclass

### Files to Modify

- `core/agents/executor.py` - Accept config/deps instead of reading env
- `api/server.py` - Use builder in lifespan bootstrap

## Import Block

```python
from core.agents.executor_builder import ExecutorBuilder
from core.agents.executor_config import ExecutorConfig, ExecutorDeps
from core.agents.stages import (
    PreGovernanceStage,
    ToolShortlistStage,
    AiosCallStage,
)
```

## Minimal Implementation

```python
# core/agents/executor_config.py
"""Executor configuration separated from environment."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ExecutorConfig:
    """
    Environment-driven configuration for executor.

    Separates config reading from executor logic.
    """

    default_agent_id: str
    max_iterations: int
    enable_memory_warming: bool
    enable_graph_hydration: bool
    enable_reflection: bool
    fallback_agent_id: str = "l9-standard-v1"

    @classmethod
    def from_env(cls) -> "ExecutorConfig":
        """Load config from environment variables."""
        return cls(
            default_agent_id=os.getenv("DEFAULT_AGENT_ID", "l-cto"),
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
            enable_memory_warming=os.getenv("ENABLE_MEMORY_WARMING", "true").lower() == "true",
            enable_graph_hydration=os.getenv("ENABLE_GRAPH_HYDRATION", "true").lower() == "true",
            enable_reflection=os.getenv("ENABLE_REFLECTION", "true").lower() == "true",
            fallback_agent_id=os.getenv("FALLBACK_AGENT_ID", "l9-standard-v1"),
        )
```

```python
# core/agents/executor_builder.py
"""Builder for composing AgentExecutorService."""

from typing import Optional, List
import logging

from core.agents.executor import AgentExecutorService
from core.agents.executor_config import ExecutorConfig
from core.agents.stages import LoopStage

logger = logging.getLogger(__name__)


class ExecutorBuilder:
    """
    Builder for composing AgentExecutorService.

    Separates assembly logic from execution logic.
    Enables different configurations for different profiles.
    """

    def __init__(self):
        self._config: Optional[ExecutorConfig] = None
        self._stages: List[LoopStage] = []
        self._policies: dict = {}
        self._deps: dict = {}

    def with_config(self, config: ExecutorConfig) -> "ExecutorBuilder":
        """Set executor configuration."""
        self._config = config
        return self

    def with_stage(self, stage: LoopStage) -> "ExecutorBuilder":
        """Add a loop stage."""
        self._stages.append(stage)
        return self

    def with_stages(self, stages: List[LoopStage]) -> "ExecutorBuilder":
        """Add multiple loop stages."""
        self._stages.extend(stages)
        return self

    def with_prompt_defense(self, policy) -> "ExecutorBuilder":
        """Add prompt defense policy."""
        self._policies["prompt_defense"] = policy
        return self

    def with_memory_warming(self, policy) -> "ExecutorBuilder":
        """Add memory warming policy."""
        self._policies["memory_warming"] = policy
        return self

    def with_graph_hydration(self, policy) -> "ExecutorBuilder":
        """Add graph hydration policy."""
        self._policies["graph_hydration"] = policy
        return self

    def with_reflection(self, policy) -> "ExecutorBuilder":
        """Add reflection policy."""
        self._policies["reflection"] = policy
        return self

    def with_dependency(self, name: str, dep) -> "ExecutorBuilder":
        """Add a named dependency."""
        self._deps[name] = dep
        return self

    def build(self) -> AgentExecutorService:
        """
        Build the configured AgentExecutorService.

        Returns:
            Fully configured executor instance.

        Raises:
            ValueError: If required config/deps missing.
        """
        if self._config is None:
            raise ValueError("Config required. Call with_config() first.")

        if not self._stages:
            raise ValueError("At least one stage required. Call with_stage() first.")

        executor = AgentExecutorService(
            config=self._config,
            stages=self._stages,
            policies=self._policies,
            **self._deps,
        )

        logger.info(
            f"Executor built: {len(self._stages)} stages, "
            f"{len(self._policies)} policies"
        )

        return executor


# Convenience function
def build_default_executor() -> AgentExecutorService:
    """Build executor with default production configuration."""
    from core.agents.stages import (
        PreGovernanceStage,
        ToolShortlistStage,
        AiosCallStage,
        ReactionLoggingStage,
        ToolDispatchStage,
        TerminationGuardStage,
        GovernanceAuditStage,
    )

    config = ExecutorConfig.from_env()

    return (
        ExecutorBuilder()
        .with_config(config)
        .with_stages([
            PreGovernanceStage(),
            ToolShortlistStage(),
            AiosCallStage(),
            ReactionLoggingStage(),
            ToolDispatchStage(),
            TerminationGuardStage(max_iterations=config.max_iterations),
            GovernanceAuditStage(),
        ])
        .build()
    )
```

## Usage Example

```python
# Production bootstrap (api/server.py lifespan)
from core.agents.executor_builder import ExecutorBuilder
from core.agents.executor_config import ExecutorConfig

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build executor with production profile
    config = ExecutorConfig.from_env()

    executor = (
        ExecutorBuilder()
        .with_config(config)
        .with_stages([
            PreGovernanceStage(governance_service),
            ToolShortlistStage(tool_registry),
            AiosCallStage(aios_runtime, circuit_breaker),
            ReactionLoggingStage(substrate_service),
            ToolDispatchStage(tool_executor),
            TerminationGuardStage(max_iterations=config.max_iterations),
            GovernanceAuditStage(audit_logger),
        ])
        .with_prompt_defense(PromptDefensePolicy())
        .with_reflection(ReflectionPolicy())
        .build()
    )

    app.state.executor = executor
    yield


# Testing with minimal stages
def test_executor_with_mock_stages():
    config = ExecutorConfig(
        default_agent_id="test-agent",
        max_iterations=3,
        enable_memory_warming=False,
        enable_graph_hydration=False,
        enable_reflection=False,
    )

    executor = (
        ExecutorBuilder()
        .with_config(config)
        .with_stage(MockStage())  # Single mock stage
        .build()
    )

    # Test with minimal executor
```

## Anti-Pattern Example

```python
# ❌ WRONG — Constructor reads env and instantiates everything
class AgentExecutorService:
    def __init__(self):
        self._default_agent_id = os.getenv("DEFAULT_AGENT_ID", "l-cto")
        self._max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

        # Hard-coded stage instantiation
        self._governance = GovernanceService()
        self._tool_registry = ToolRegistry()
        self._aios_runtime = AIOSRuntime()
        # ... more hard-coded deps

# ✅ CORRECT — Builder composes, executor executes
config = ExecutorConfig.from_env()
executor = (
    ExecutorBuilder()
    .with_config(config)
    .with_stages([...])
    .with_dependency("aios_runtime", aios_runtime)
    .build()
)
```

## Rules

1. `ExecutorBuilder` MUST be the only way to create `AgentExecutorService`
2. `ExecutorConfig` MUST NOT read environment directly — use `from_env()` factory
3. All stages MUST be passed via builder, not instantiated in executor
4. Policies MUST be optional — executor works without them
5. Builder MUST validate required components before `build()`
6. Builder SHOULD support fluent API (method chaining)
7. `build()` MUST be idempotent — calling twice returns same config

## AI Guidance

**DO:**

- Use builder for all executor instantiation
- Pass config as immutable dataclass
- Inject stages via `with_stages()`
- Use builder in tests to create minimal executors

**DO NOT:**

- Read environment in executor constructor
- Instantiate stages inside executor
- Make builder stateful beyond current build session
- Skip validation in `build()`

## Related ADRs

- [ADR-0040: Loop Stage Protocol](./0040-loop-stage-protocol.md) - Stages passed to builder
- [ADR-0042: Execution Profiles](./0042-execution-profiles.md) - Profiles use builder
- [ADR-0025: FastAPI Dependency Injection](./0025-fastapi-dependency-injection.md) - DI pattern
