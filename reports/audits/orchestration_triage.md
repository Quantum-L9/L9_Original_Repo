# Dead Code Triage: `orchestration`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (7): `ExecutionResult`, `ExecutorConfig`, `KernelState`, `PlanExecutor`, `SegmentResult`, `StepResult`, `get_segmenter`
**INTERNAL_ONLY** (8): `CellOrchestrator`, `InputSegmenter`, `KernelConfig`, `OrchestratorKernel`, `RoutingDecision`, `TaskRouter`, `UnifiedController`, `segment_input`
**TEST_ONLY** (6): `ExecutionStatus`, `RouterConfig`, `SegmenterConfig`, `WSTaskRouter`, `route_event_to_task`, `segment_to_tasks`
**ZERO_REF** (22): `CellStep`, `CellWorkflow`, `ChainStatus`, `ChainStep`, `ControllerConfig`, `ControllerPhase`, `ControllerResult`, `ControllerState`, `ExecutionChain`, `ExecutionMode`, `ExecutionTarget`, `IRPipelineResult`, `TaskComplexity`, `TaskRisk`, `TaskRoute`, `TaskType`, `WorkflowResult`, `WorkflowStatus`, `broadcast_task`, `dispatch_task_to_agent`
  ... and 2 more

## File Classification

**WIRED** (6):
- `orchestration/email_task_router.py`
- `orchestration/input_segmenter.py`
- `orchestration/long_plan_graph.py`
- `orchestration/plan_executor.py`
- `orchestration/slack_task_router.py`
- `orchestration/ws_task_router.py`
**INTERNAL_ONLY** (3):
- `orchestration/cell_orchestrator.py`
- `orchestration/orchestrator_kernel.py`
- `orchestration/task_router.py`
**WIP** (1):
- `orchestration/quantum_swarm_loader.py`
**ASPIRATIONAL** (1):
- `orchestration/unified_controller.py`

## Recommended Actions

### Remove 8 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 22 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 1 WIP files
Recently created but not yet integrated.
