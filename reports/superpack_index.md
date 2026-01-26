# L9 SUPERPACK INDEX

**Central Hub** | Risk Tiers | Change Checklists | Auto-Generated

---

## Quick Navigation

| Superpack              | File                                                     | Risk Tier | Description                     |
| ---------------------- | -------------------------------------------------------- | --------- | ------------------------------- |
| Governance & Authority | [governance_superpack.md](governance_superpack.md)       | T3        | Authority model, PacketEnvelope |
| Core & Memory          | [core_memory_superpack.md](core_memory_superpack.md)     | T3        | Kernel runtime, memory pipeline |
| Orchestration          | [orchestration_superpack.md](orchestration_superpack.md) | T3        | Orchestrator flow, workers      |
| API & Clients          | [api_clients_superpack.md](api_clients_superpack.md)     | T2        | API surface, routes             |
| Tools                  | [tools_superpack.md](tools_superpack.md)                 | T1        | Tool catalog, automation        |

## Risk Tier Definitions

| Tier   | Description                       | Approval Gate           |
| ------ | --------------------------------- | ----------------------- |
| **T3** | High-impact, protected invariants | L-CTO approval required |
| **T2** | Reversible, stability required    | Code review             |
| **T1** | Read-only, documentation          | Automated               |

## Protected Invariants (T3 Blocking)

```
✗ runtime/websocket_orchestrator.py
✗ core/agents/executor.py
✗ memory/substrate_service.py
✗ docker-compose.yml
✗ core/singleton_registry.py
```

## Inventory Files

| File                                                                  | Description                  |
| --------------------------------------------------------------------- | ---------------------------- |
| [governance_invariants.txt](architecture/governance_invariants.txt)   | Protected surfaces checklist |
| [memory_integration_map.txt](architecture/memory_integration_map.txt) | Memory dependency graph      |
| [worker_inventory.txt](architecture/worker_inventory.txt)             | Worker modules catalog       |
| [api_route_inventory.txt](architecture/api_route_inventory.txt)       | Route/handler matrix         |
| [tools_inventory.txt](architecture/tools_inventory.txt)               | Tool modules catalog         |

## Regeneration

```bash
# Regenerate all superpacks from AST scan
python -m tools.superpack_reports.main

# Or via Makefile
make superpacks
```

---

_Auto-generated: 2026-01-25 14:12 | `tools/superpack_reports/`_
