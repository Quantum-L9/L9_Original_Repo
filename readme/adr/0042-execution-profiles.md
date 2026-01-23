# ADR 0042: Execution Profiles

## Status

Proposed

## Pattern

Define **Execution Profiles** that configure the executor for different risk modes and deployment scenarios. Each profile uses `ExecutorBuilder` to compose a specific set of stages and policies.

## Context

L9's executor has many conditional branches for different modes:
- Production (full governance, all checks)
- Testing (minimal checks, mock tools)
- Local development (no approvals, fast iteration)
- High-security (additional gates, stricter thresholds)

These conditions are scattered throughout the code. Profiles make them declarative and composable.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/agents/profiles/__init__.py` - Profile exports
- `core/agents/profiles/base_profile.py` - ExecutionProfile protocol
- `core/agents/profiles/safe_default_profile.py` - Production default
- `core/agents/profiles/fast_local_profile.py` - Development/testing
- `core/agents/profiles/paranoid_profile.py` - High-security mode

### Files to Modify

- `api/server.py` - Select profile at startup
- `core/agents/executor_builder.py` - Accept profile

## Import Block

```python
from typing import Protocol

from core.agents.profiles import (
    ExecutionProfile,
    SafeDefaultProfile,
    FastLocalProfile,
    ParanoidProfile,
    get_profile_by_name,
)
from core.agents.executor_builder import ExecutorBuilder
```

## Minimal Implementation

```python
# core/agents/profiles/base_profile.py
"""Execution profile protocol."""

from typing import Protocol, runtime_checkable

from core.agents.executor_builder import ExecutorBuilder


@runtime_checkable
class ExecutionProfile(Protocol):
    """
    Protocol for execution profiles.
    
    Each profile configures an ExecutorBuilder with
    appropriate stages and policies for its use case.
    """
    
    name: str
    
    async def configure_executor(self, builder: ExecutorBuilder) -> None:
        """Configure the builder with this profile's settings."""
        ...
```

```python
# core/agents/profiles/safe_default_profile.py
"""Production default profile with full governance."""

from core.agents.profiles.base_profile import ExecutionProfile
from core.agents.executor_builder import ExecutorBuilder
from core.agents.stages import (
    PreGovernanceStage,
    ToolShortlistStage,
    AiosCallStage,
    ReactionLoggingStage,
    ToolDispatchStage,
    TerminationGuardStage,
    GovernanceAuditStage,
)


class SafeDefaultProfile:
    """
    Production-safe execution profile.
    
    Includes:
    - Full governance checks
    - All approval gates
    - Self-reflection enabled
    - Memory warming enabled
    - Complete audit logging
    """
    
    name: str = "safe_default"
    
    async def configure_executor(self, builder: ExecutorBuilder) -> None:
        """Configure builder with production-safe settings."""
        builder.with_stages([
            PreGovernanceStage(),
            ToolShortlistStage(),
            AiosCallStage(),
            ReactionLoggingStage(),
            ToolDispatchStage(),
            TerminationGuardStage(),
            GovernanceAuditStage(),
        ])
        
        # Enable all policies
        from core.agents.policies import (
            PromptDefensePolicy,
            MemoryWarmPolicy,
            GraphHydrationPolicy,
            ReflectionPolicy,
        )
        
        builder.with_prompt_defense(PromptDefensePolicy())
        builder.with_memory_warming(MemoryWarmPolicy())
        builder.with_graph_hydration(GraphHydrationPolicy())
        builder.with_reflection(ReflectionPolicy())
```

```python
# core/agents/profiles/fast_local_profile.py
"""Fast local development profile."""

from core.agents.profiles.base_profile import ExecutionProfile
from core.agents.executor_builder import ExecutorBuilder
from core.agents.stages import (
    ToolShortlistStage,
    AiosCallStage,
    ToolDispatchStage,
    TerminationGuardStage,
)


class FastLocalProfile:
    """
    Fast local development profile.
    
    Stripped down for rapid iteration:
    - No governance checks
    - No approval gates
    - No self-reflection
    - No memory warming
    - Minimal logging
    """
    
    name: str = "fast_local"
    
    async def configure_executor(self, builder: ExecutorBuilder) -> None:
        """Configure builder with minimal settings."""
        builder.with_stages([
            ToolShortlistStage(),
            AiosCallStage(),
            ToolDispatchStage(),
            TerminationGuardStage(max_iterations=5),  # Lower limit
        ])
        
        # No policies — fastest possible execution
```

```python
# core/agents/profiles/paranoid_profile.py
"""High-security profile with additional gates."""

from core.agents.profiles.base_profile import ExecutionProfile
from core.agents.executor_builder import ExecutorBuilder
from core.agents.stages import (
    PreGovernanceStage,
    ToolShortlistStage,
    AiosCallStage,
    ReactionLoggingStage,
    ToolDispatchStage,
    TerminationGuardStage,
    GovernanceAuditStage,
)


class ParanoidProfile:
    """
    High-security execution profile.
    
    Maximum safety:
    - All governance checks
    - All approval gates
    - Additional validation stages
    - Stricter thresholds
    - Comprehensive logging
    """
    
    name: str = "paranoid"
    
    async def configure_executor(self, builder: ExecutorBuilder) -> None:
        """Configure builder with maximum security settings."""
        builder.with_stages([
            PreGovernanceStage(strict_mode=True),
            ToolShortlistStage(whitelist_only=True),
            AiosCallStage(timeout_ms=5000),  # Shorter timeout
            ReactionLoggingStage(verbose=True),
            ToolDispatchStage(require_approval=True),
            TerminationGuardStage(max_iterations=3),  # Very conservative
            GovernanceAuditStage(audit_level="detailed"),
        ])
        
        # Enable all policies with strict settings
        from core.agents.policies import (
            PromptDefensePolicy,
            MemoryWarmPolicy,
            GraphHydrationPolicy,
            ReflectionPolicy,
        )
        
        builder.with_prompt_defense(PromptDefensePolicy(strict=True))
        builder.with_memory_warming(MemoryWarmPolicy())
        builder.with_graph_hydration(GraphHydrationPolicy())
        builder.with_reflection(ReflectionPolicy(always_reflect=True))
```

## Usage Example

```python
# Selecting profile at startup (api/server.py)
import os
from core.agents.profiles import get_profile_by_name
from core.agents.executor_builder import ExecutorBuilder
from core.agents.executor_config import ExecutorConfig

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Profile from environment
    profile_name = os.getenv("EXECUTION_PROFILE", "safe_default")
    profile = get_profile_by_name(profile_name)
    
    config = ExecutorConfig.from_env()
    builder = ExecutorBuilder().with_config(config)
    
    # Profile configures the builder
    await profile.configure_executor(builder)
    
    # Build executor
    executor = builder.build()
    app.state.executor = executor
    
    logger.info(f"Executor started with profile: {profile.name}")
    yield


# Profile registry
def get_profile_by_name(name: str) -> ExecutionProfile:
    """Get profile by name."""
    profiles = {
        "safe_default": SafeDefaultProfile(),
        "fast_local": FastLocalProfile(),
        "paranoid": ParanoidProfile(),
    }
    
    if name not in profiles:
        raise ValueError(f"Unknown profile: {name}. Available: {list(profiles.keys())}")
    
    return profiles[name]
```

## Anti-Pattern Example

```python
# ❌ WRONG — Scattered conditionals throughout executor
class AgentExecutorService:
    async def _run_execution_loop(self, ...):
        if os.getenv("FAST_MODE"):
            # Skip governance
            pass
        else:
            await self._check_governance(...)
        
        if os.getenv("HIGH_SECURITY"):
            await self._extra_validation(...)
        
        if not os.getenv("SKIP_REFLECTION"):
            await self._reflect(...)
        
        # ... conditionals everywhere ...

# ✅ CORRECT — Profile configures builder once
profile = get_profile_by_name(os.getenv("EXECUTION_PROFILE", "safe_default"))
await profile.configure_executor(builder)
executor = builder.build()
# Executor has no conditionals — profile determined everything
```

## Rules

1. All profiles MUST implement `ExecutionProfile` protocol
2. Profile selection MUST happen at startup, not per-request
3. Profiles MUST NOT be changed during runtime
4. `safe_default` MUST be the default if no profile specified
5. Each profile MUST be self-contained (no inheritance chain)
6. Profile names MUST be lowercase with underscores
7. Environment variable: `EXECUTION_PROFILE`

## AI Guidance

**DO:**

- Use `safe_default` in production
- Use `fast_local` in development/testing
- Use `paranoid` for high-security deployments
- Create new profiles for new deployment scenarios

**DO NOT:**

- Mix profile logic with executor logic
- Change profiles at runtime
- Skip profile for ad-hoc configuration
- Create profiles that differ only in one setting (use config instead)

## Related ADRs

- [ADR-0040: Loop Stage Protocol](./0040-loop-stage-protocol.md) - Stages configured by profiles
- [ADR-0041: Executor Builder Pattern](./0041-executor-builder-pattern.md) - Builder used by profiles
- [ADR-0008: Feature Flag Gating](./0008-feature-flag-gating.md) - Config vs profile distinction
