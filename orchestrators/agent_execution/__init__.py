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

from .interface import (AgentExecutionRequest, AgentExecutionResponse,
                        IAgentExecutionOrchestrator)
from .orchestrator import AgentExecutionOrchestrator
from .task_queue import complete_task  # Legacy API
from .task_queue import (enqueue_mac_task, enqueue_mac_task_dict,
                         get_next_task, list_tasks, mark_task_completed)

__all__ = [
    "IAgentExecutionOrchestrator",
    "AgentExecutionOrchestrator",
    "AgentExecutionRequest",
    "AgentExecutionResponse",
    "enqueue_mac_task",
    "enqueue_mac_task_dict",
    "get_next_task",
    "mark_task_completed",
    "complete_task",  # Legacy API
    "list_tasks",
]
