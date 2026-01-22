"""
L9 Orchestration - Unified System Controller
============================================

GOD-MODE orchestration layer for L9 IR Engine system.

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                     UnifiedController (Façade)                   │
│  ┌──────────────┬──────────────────┬────────────────────────┐   │
│  │  TaskRouter  │ OrchestratorKernel│   CellOrchestrator     │   │
│  └──────────────┴──────────────────┴────────────────────────┘   │
│                          │                                       │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │                    PlanExecutor                          │    │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Deterministic Phases:
  ingest → IR → validate → simulate → plan → execute → reflect

Components:
- UnifiedController: GOD-MODE top-level controller
- TaskRouter: Route tasks to cells/agents based on complexity/risk
- OrchestratorKernel: Core deterministic execution loop with IR Engine
- CellOrchestrator: Multi-cell workflow coordination
- PlanExecutor: Execute finalized plans with memory hooks

Version: 2.0.0
"""

from orchestration.cell_orchestrator import (CellOrchestrator, CellStep,
                                             CellWorkflow, WorkflowResult,
                                             WorkflowStatus)
# Input Segmenter (Harvested from tokenizer - multi-part directive support)
from orchestration.input_segmenter import (InputSegmenter, SegmenterConfig,
                                           SegmentResult, get_segmenter,
                                           segment_input, segment_to_tasks)
from orchestration.orchestrator_kernel import (ChainStatus, ChainStep,
                                               ExecutionChain,
                                               IRPipelineResult, KernelConfig,
                                               KernelState, OrchestratorKernel)
from orchestration.plan_executor import (ExecutionResult, ExecutionStatus,
                                         ExecutorConfig, PlanExecutor,
                                         StepResult)
from orchestration.task_router import (ExecutionTarget, RoutingDecision,
                                       TaskComplexity, TaskRisk, TaskRoute,
                                       TaskRouter, TaskType)
# WebSocket Dispatch Functions (Phase 2.5)
from orchestration.unified_controller import (ControllerConfig,
                                              ControllerPhase,
                                              ControllerResult,
                                              ControllerState, ExecutionMode,
                                              UnifiedController,
                                              broadcast_task,
                                              dispatch_task_to_agent,
                                              get_ws_orchestrator,
                                              set_ws_orchestrator)
# WebSocket Task Router (Phase 2.5)
from orchestration.ws_task_router import (RouterConfig, WSTaskRouter,
                                          route_event_to_task)

__all__ = [
    # Unified Controller (Main Façade)
    "UnifiedController",
    "ControllerConfig",
    "ControllerState",
    "ControllerResult",
    "ControllerPhase",
    "ExecutionMode",
    # Task Router
    "TaskRouter",
    "TaskRoute",
    "RoutingDecision",
    "TaskType",
    "ExecutionTarget",
    "TaskComplexity",
    "TaskRisk",
    # Orchestrator Kernel
    "OrchestratorKernel",
    "KernelConfig",
    "KernelState",
    "ExecutionChain",
    "ChainStep",
    "ChainStatus",
    "IRPipelineResult",
    # Cell Orchestrator
    "CellOrchestrator",
    "CellWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    "CellStep",
    # Plan Executor
    "PlanExecutor",
    "ExecutorConfig",
    "ExecutionResult",
    "ExecutionStatus",
    "StepResult",
    # Input Segmenter (multi-part directive support)
    "InputSegmenter",
    "SegmenterConfig",
    "SegmentResult",
    "get_segmenter",
    "segment_input",
    "segment_to_tasks",
    # WebSocket Task Router (Phase 2.5)
    "route_event_to_task",
    "RouterConfig",
    "WSTaskRouter",
    # WebSocket Dispatch Functions (Phase 2.5)
    "dispatch_task_to_agent",
    "broadcast_task",
    "get_ws_orchestrator",
    "set_ws_orchestrator",
]

__version__ = "2.0.0"
