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

# Dynamic Tool Binding (GMP-TS-META: Anthropic Tool Search pattern)
from core.agents.dynamic_tool_binding import (
    bind_tools_to_agent,
    cache_discovered_tools,
    clear_tool_cache,
    get_agent_tools,
    get_binding_mode_summary,
    get_dynamic_tool_bundle,
    get_static_tool_bundle,
    get_tool_binding_status,
    refresh_agent_tools,
)

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
    if name == "IdempotencyStore":
        from core.agents.idempotency_store import IdempotencyStore

        return IdempotencyStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AIOSResult",
    "AgentConfig",
    "AgentExecutorService",
    # Classes
    "AgentInstance",
    "IdempotencyStore",
    # Schemas
    "AgentTask",
    "ExecutorState",
    "ToolCallRequest",
    "ToolCallResult",
    # Dynamic Tool Binding (GMP-TS-META)
    "bind_tools_to_agent",
    "cache_discovered_tools",
    "clear_tool_cache",
    "get_agent_tools",
    "get_binding_mode_summary",
    "get_dynamic_tool_bundle",
    "get_static_tool_bundle",
    "get_tool_binding_status",
    "refresh_agent_tools",
]
# Runtime execution trace - updated automatically on every execution
