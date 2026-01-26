"""
L9 Core Agents - Agent Executor Module
======================================

Provides agent instantiation, tool binding, and execution loop orchestration.

Components:
- schemas: Pydantic models for AgentTask, AgentConfig, AIOSResult
- agent_instance: Running agent instance class
- executor: AgentExecutorService for task execution

Version: 1.0.0

Note: The executor module requires memory.substrate_models which has heavy
dependencies (asyncpg). Import AgentExecutorService directly from
core.agents.executor when needed.
"""

from core.agents.agent_instance import AgentInstance

# Light imports (no heavy dependencies)
from core.agents.schemas import (
    AgentConfig,
    AgentTask,
    AIOSResult,
    ExecutorState,
    ToolCallRequest,
    ToolCallResult,
)


# Lazy import for executor (heavy deps)
def __getattr__(name: str):
    """Lazy import for heavy dependency modules."""
    if name == "AgentExecutorService":
        from core.agents.executor import AgentExecutorService

        return AgentExecutorService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AIOSResult",
    "AgentConfig",
    "AgentExecutorService",
    # Classes
    "AgentInstance",
    # Schemas
    "AgentTask",
    "ExecutorState",
    "ToolCallRequest",
    "ToolCallResult",
]
