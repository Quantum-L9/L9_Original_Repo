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

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Executor Module",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "__init__",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-092",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.agent_instance",
        "core.agents.executor",
        "core.agents.idempotency_store",
        "core.agents.schemas",
    ],
    "tags": ["agent-execution", "foundation", "service"],
    "keywords": [
        "agent",
        "agentexecutorservice",
        "agents",
        "core",
        "execution",
        "executor",
        "memory",
        "module",
    ],
    "business_value": "Provides agent instantiation, tool binding, and execution loop orchestration. schemas: Pydantic models for AgentTask, AgentConfig, AIOSResult agent_instance: Running agent instance class executor: Age",
    "last_modified": "2026-01-31T22:21:46Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
