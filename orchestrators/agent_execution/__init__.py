"""
L9 Agent Execution Orchestrator
================================

Orchestrates Mac Agent task execution from file-based queue.

Exports:
- AgentExecutionOrchestrator: Main orchestrator class
- IAgentExecutionOrchestrator: Protocol interface
- enqueue_mac_task: Queue Mac Agent tasks
- get_next_task: Retrieve next task from queue
- mark_task_completed: Mark task as completed
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-31T22:21:55Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .interface import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    IAgentExecutionOrchestrator,
)
from .orchestrator import AgentExecutionOrchestrator
from .task_queue import (
    complete_task,  # Legacy API
    enqueue_mac_task,
    enqueue_mac_task_dict,
    get_next_task,
    list_tasks,
    mark_task_completed,
)

__all__ = [
    "AgentExecutionOrchestrator",
    "AgentExecutionRequest",
    "AgentExecutionResponse",
    "IAgentExecutionOrchestrator",
    "complete_task",  # Legacy API
    "enqueue_mac_task",
    "enqueue_mac_task_dict",
    "get_next_task",
    "list_tasks",
    "mark_task_completed",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-052",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "intelligence", "orchestration", "queue", "utility"],
    "keywords": ["agent", "execution", "orchestrator", "queue", "task"],
    "business_value": "Orchestrates Mac Agent task execution from file-based queue. AgentExecutionOrchestrator: Main orchestrator class IAgentExecutionOrchestrator: Protocol interface enqueue_mac_task: Queue Mac Agent tasks",
    "last_modified": "2026-01-31T22:21:55Z",
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
