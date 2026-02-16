# Package Wiring Audit: orchestration

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `orchestration`

Files checked: 11
- WIRED: 1
- PARTIAL: 9
- ORPHAN: 1
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `orchestration/cell_orchestrator.py` | 0 | 0 | - | Y | PARTIAL |
| `orchestration/email_task_router.py` | 1 | 0 | - | - | PARTIAL |
| `orchestration/input_segmenter.py` | 3 | 2 | Y | Y | OK |
| `orchestration/long_plan_graph.py` | 1 | 1 | - | - | PARTIAL |
| `orchestration/orchestrator_kernel.py` | 0 | 0 | - | Y | PARTIAL |
| `orchestration/plan_executor.py` | 0 | 1 | - | Y | PARTIAL |
| `orchestration/quantum_swarm_loader.py` | 0 | 0 | - | - | ORPHAN |
| `orchestration/slack_task_router.py` | 1 | 0 | - | - | PARTIAL |
| `orchestration/task_router.py` | 0 | 0 | - | Y | PARTIAL |
| `orchestration/unified_controller.py` | 0 | 0 | - | Y | PARTIAL |
| `orchestration/ws_task_router.py` | 0 | 2 | - | Y | PARTIAL |

## Level C: API Instantiation — `orchestration`

API Status: **HAS_API**
Symbols checked: 43
- USED: 7
- TEST_ONLY: 9
- UNUSED: 27

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `CellOrchestrator` | 0 | 0 | UNUSED |
| `CellStep` | 0 | 0 | UNUSED |
| `CellWorkflow` | 0 | 0 | UNUSED |
| `ChainStatus` | 0 | 0 | UNUSED |
| `ChainStep` | 0 | 0 | UNUSED |
| `ControllerConfig` | 0 | 0 | UNUSED |
| `ControllerPhase` | 0 | 0 | UNUSED |
| `ControllerResult` | 0 | 0 | UNUSED |
| `ControllerState` | 0 | 0 | UNUSED |
| `ExecutionChain` | 0 | 0 | UNUSED |
| `ExecutionMode` | 0 | 0 | UNUSED |
| `ExecutionStatus` | 0 | 1 | TEST_ONLY |
| `ExecutionTarget` | 0 | 0 | UNUSED |
| `IRPipelineResult` | 0 | 0 | UNUSED |
| `InputSegmenter` | 0 | 2 | TEST_ONLY |
| `KernelConfig` | 0 | 0 | UNUSED |
| `OrchestratorKernel` | 0 | 0 | UNUSED |
| `RouterConfig` | 0 | 1 | TEST_ONLY |
| `RoutingDecision` | 0 | 0 | UNUSED |
| `SegmenterConfig` | 0 | 1 | TEST_ONLY |
| `TaskComplexity` | 0 | 0 | UNUSED |
| `TaskRisk` | 0 | 0 | UNUSED |
| `TaskRoute` | 0 | 0 | UNUSED |
| `TaskRouter` | 0 | 1 | TEST_ONLY |
| `TaskType` | 0 | 0 | UNUSED |
| `UnifiedController` | 0 | 0 | UNUSED |
| `WSTaskRouter` | 0 | 2 | TEST_ONLY |
| `WorkflowResult` | 0 | 0 | UNUSED |
| `WorkflowStatus` | 0 | 0 | UNUSED |
| `broadcast_task` | 0 | 0 | UNUSED |
| `dispatch_task_to_agent` | 0 | 0 | UNUSED |
| `get_ws_orchestrator` | 0 | 0 | UNUSED |
| `route_event_to_task` | 0 | 1 | TEST_ONLY |
| `segment_input` | 0 | 1 | TEST_ONLY |
| `segment_to_tasks` | 0 | 1 | TEST_ONLY |
| `set_ws_orchestrator` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `get_client`
- `get_client`
- `get_tools_for_target`
