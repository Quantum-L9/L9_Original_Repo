# ORCHESTRATION & WORKERS SUPERPACK

**Risk Tier:** T3 (High-Impact) | **Auto-Generated**

---

## Purpose

Map orchestrator flow, worker scheduling, session lifecycle, and PacketEnvelope construction.

---

## Orchestrator Modules (AST Scanned)

| Module                                       | Classes | Functions | Async | LOC  |
| -------------------------------------------- | ------- | --------- | ----- | ---- |
| `orchestration.__init__`                     | 0       | 0         |       | 117  |
| `orchestration.cell_orchestrator`            | 6       | 0         |       | 1023 |
| `orchestration.email_task_router`            | 0       | 2         |       | 260  |
| `orchestration.input_segmenter`              | 3       | 3         |       | 393  |
| `orchestration.long_plan_graph`              | 1       | 11        | ✓     | 981  |
| `orchestration.orchestrator_kernel`          | 8       | 0         |       | 1087 |
| `orchestration.plan_executor`                | 6       | 0         |       | 1337 |
| `orchestration.quantum_swarm_loader`         | 2       | 1         | ✓     | 328  |
| `orchestration.slack_task_router`            | 0       | 2         |       | 285  |
| `orchestration.task_router`                  | 8       | 4         |       | 1145 |
| `orchestration.unified_controller`           | 6       | 4         | ✓     | 1411 |
| `orchestration.ws_task_router`               | 4       | 4         |       | 673  |
| `orchestrators.__init__`                     | 0       | 0         |       | 36   |
| `orchestrators.action_tool.__init__`         | 0       | 0         |       | 19   |
| `orchestrators.action_tool.interface`        | 4       | 0         |       | 120  |
| `orchestrators.action_tool.orchestrator`     | 1       | 0         |       | 274  |
| `orchestrators.action_tool.validator`        | 2       | 0         |       | 297  |
| `orchestrators.agent_execution.__init__`     | 0       | 0         |       | 33   |
| `orchestrators.agent_execution.interface`    | 4       | 0         |       | 137  |
| `orchestrators.agent_execution.orchestrator` | 1       | 1         | ✓     | 402  |
| `orchestrators.agent_execution.task_queue`   | 1       | 7         |       | 416  |
| `orchestrators.evolution.__init__`           | 0       | 0         |       | 26   |
| `orchestrators.evolution.apply_engine`       | 1       | 0         |       | 300  |
| `orchestrators.evolution.interface`          | 8       | 0         |       | 208  |
| `orchestrators.evolution.orchestrator`       | 1       | 0         |       | 331  |
| `orchestrators.memory.__init__`              | 0       | 0         |       | 18   |
| `orchestrators.memory.housekeeping`          | 1       | 0         |       | 514  |
| `orchestrators.memory.interface`             | 4       | 0         |       | 139  |
| `orchestrators.memory.orchestrator`          | 1       | 0         |       | 284  |
| `orchestrators.meta.__init__`                | 0       | 0         |       | 25   |
| `orchestrators.meta.adapter`                 | 1       | 0         |       | 286  |
| `orchestrators.meta.interface`               | 8       | 0         |       | 194  |
| `orchestrators.meta.orchestrator`            | 1       | 0         |       | 286  |
| `orchestrators.orchestrator_registry`        | 0       | 9         |       | 337  |
| `orchestrators.pattern.__init__`             | 0       | 0         |       | 56   |
| `orchestrators.pattern.cell_adapter`         | 2       | 2         |       | 677  |
| `orchestrators.pattern.interface`            | 21      | 0         |       | 350  |
| `orchestrators.pattern.master_orchestrator`  | 4       | 1         |       | 469  |
| `orchestrators.pattern.metrics`              | 1       | 0         |       | 270  |
| `orchestrators.pattern.orchestrator`         | 3       | 1         |       | 670  |
| `orchestrators.reasoning.__init__`           | 0       | 0         |       | 19   |
| `orchestrators.reasoning.adapter_node`       | 2       | 1         |       | 200  |
| `orchestrators.reasoning.interface`          | 4       | 0         |       | 120  |
| `orchestrators.reasoning.orchestrator`       | 1       | 0         |       | 288  |
| `orchestrators.research_swarm.__init__`      | 0       | 0         |       | 19   |
| `orchestrators.research_swarm.convergence`   | 1       | 0         |       | 90   |
| `orchestrators.research_swarm.interface`     | 3       | 0         |       | 105  |
| `orchestrators.research_swarm.orchestrator`  | 1       | 0         |       | 283  |
| `orchestrators.world_model.__init__`         | 0       | 0         |       | 19   |
| `orchestrators.world_model.interface`        | 4       | 0         |       | 140  |
| `orchestrators.world_model.orchestrator`     | 1       | 0         |       | 304  |
| `orchestrators.world_model.scheduler`        | 1       | 0         |       | 204  |
| `orchestrators.ws_bridge`                    | 2       | 3         | ✓     | 350  |

## Worker Modules (AST Scanned)

| Module                              | Classes | Functions | LOC |
| ----------------------------------- | ------- | --------- | --- |
| `workers.__init__`                  | 0       | 0         | 53  |
| `workers.anomaly_classifier`        | 7       | 1         | 497 |
| `workers.anomaly_response_monitor`  | 5       | 1         | 621 |
| `workers.remediation_engine`        | 6       | 1         | 562 |
| `workers.violation_patterns`        | 6       | 1         | 520 |
| `workers.violation_tracker_service` | 4       | 1         | 637 |

## Session Lifecycle

```
Session Creation:
  1. Create session metadata
  2. Initialize orchestrator context
  3. Bind memory substrate
  4. Set up telemetry scope

Session Execution:
  1. Receive PacketEnvelope
  2. Validate governance
  3. Execute kernel
  4. Emit result PacketEnvelope
  5. Write to memory

Session Cleanup:
  1. Flush pending writes
  2. Close memory connections
  3. Emit session-end event
```

## Risk Zones

```
HIGH-RISK:
  ✗ websocket_orchestrator.py (protected; no edits)
  ✗ Governance bypass attempts (audit+reject)
  ✗ Worker scheduling changes (must test end-to-end)
```

---

_Auto-generated by `tools/superpack_reports/` | Regenerate: `make superpacks`_
