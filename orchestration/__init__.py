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

# ============================================================================
__dora_meta__ = {
    "component_name": "Unified System Controller",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "__init__",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from orchestration.cell_orchestrator import (
    CellOrchestrator,
    CellStep,
    CellWorkflow,
    WorkflowResult,
    WorkflowStatus,
)

# Input Segmenter (Harvested from tokenizer - multi-part directive support)
from orchestration.input_segmenter import (
    InputSegmenter,
    SegmenterConfig,
    SegmentResult,
    get_segmenter,
    segment_input,
    segment_to_tasks,
)
from orchestration.orchestrator_kernel import (
    ChainStatus,
    ChainStep,
    ExecutionChain,
    IRPipelineResult,
    KernelConfig,
    KernelState,
    OrchestratorKernel,
)
from orchestration.plan_executor import (
    ExecutionResult,
    ExecutionStatus,
    ExecutorConfig,
    PlanExecutor,
    StepResult,
)
from orchestration.task_router import (
    ExecutionTarget,
    RoutingDecision,
    TaskComplexity,
    TaskRisk,
    TaskRoute,
    TaskRouter,
    TaskType,
)

# WebSocket Dispatch Functions (Phase 2.5)
from orchestration.unified_controller import (
    ControllerConfig,
    ControllerPhase,
    ControllerResult,
    ControllerState,
    ExecutionMode,
    UnifiedController,
    broadcast_task,
    dispatch_task_to_agent,
    get_ws_orchestrator,
    set_ws_orchestrator,
)

# WebSocket Task Router (Phase 2.5)
from orchestration.ws_task_router import RouterConfig, WSTaskRouter, route_event_to_task

__all__ = [
    # Cell Orchestrator
    "CellOrchestrator",
    "CellStep",
    "CellWorkflow",
    "ChainStatus",
    "ChainStep",
    "ControllerConfig",
    "ControllerPhase",
    "ControllerResult",
    "ControllerState",
    "ExecutionChain",
    "ExecutionMode",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionTarget",
    "ExecutorConfig",
    "IRPipelineResult",
    # Input Segmenter (multi-part directive support)
    "InputSegmenter",
    "KernelConfig",
    "KernelState",
    # Orchestrator Kernel
    "OrchestratorKernel",
    # Plan Executor
    "PlanExecutor",
    "RouterConfig",
    "RoutingDecision",
    "SegmentResult",
    "SegmenterConfig",
    "StepResult",
    "TaskComplexity",
    "TaskRisk",
    "TaskRoute",
    # Task Router
    "TaskRouter",
    "TaskType",
    # Unified Controller (Main Façade)
    "UnifiedController",
    "WSTaskRouter",
    "WorkflowResult",
    "WorkflowStatus",
    "broadcast_task",
    # WebSocket Dispatch Functions (Phase 2.5)
    "dispatch_task_to_agent",
    "get_segmenter",
    "get_ws_orchestrator",
    # WebSocket Task Router (Phase 2.5)
    "route_event_to_task",
    "segment_input",
    "segment_to_tasks",
    "set_ws_orchestrator",
]

__version__ = "2.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-005",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["engine", "event-driven", "intelligence", "orchestration", "realtime"],
    "keywords": [
        "cellorchestrator",
        "controller",
        "deterministic",
        "engine",
        "execute",
        "memory",
        "mode",
        "orchestration",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:56Z",
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
