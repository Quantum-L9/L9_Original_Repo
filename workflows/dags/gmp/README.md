# GMP LangGraph Executor

Programmatic GMP (Governance Managed Process) execution via LangGraph StateGraph.

## Architecture

```
workflows/dags/gmp/
├── __init__.py      # Package exports
├── state.py         # GMPState dataclass, GMPPhase enum
├── routing.py       # Conditional routing (scope confirm, validation confirm)
├── graph.py         # build_gmp_graph() → StateGraph
├── executor.py      # GMPLangGraphExecutor class + CLI
└── nodes/
    ├── __init__.py
    └── core.py      # All node functions (12 nodes)
```

## Execution Flow

```
start → memory_read → scope_lock → user_confirm_scope
                                          │
                              ┌───────────┼───────────┐
                              ↓           ↓           ↓
                          baseline     aborted       END
                              ↓
                          implement → validate → user_confirm_validation
                                                      │
                                          ┌───────────┼───────────┐
                                          ↓           ↓           ↓
                                    memory_write   implement   aborted
                                          ↓         (retry)
                                      finalize → end → END
```

## Two Consumers, Two Patterns

| Consumer | Mechanism | File |
|----------|-----------|------|
| **Cursor agent** | SessionDAG — agent reads node `action` fields in conversation | `gmp_execution_dag.py` |
| **L / Emma agents** | LangGraph StateGraph — programmatic execution via SDK | `gmp/` (this package) |

The SessionDAG and LangGraph executor share the same phases and flow but serve different runtime contexts. See ADR-0101 for the SDK integration pattern.

## Current Status: WIP

| Component | Status | Notes |
|-----------|--------|-------|
| State model | Done | `GMPState` with all fields |
| Graph wiring | Done | All nodes + conditional edges |
| Routing | Done | Scope confirm, validation confirm |
| `node_memory_read` | Done | Calls cursor_memory_client via subprocess |
| `node_memory_write` | Done | Calls cursor_memory_client via subprocess |
| `node_validate` | Done | Calls gmp-validate-stage.py |
| `node_finalize` | Done | 3-step: generate → validate → update workflow_state |
| `node_implement` | **WIP** | No-op — needs agent executor integration |
| `node_scope_lock` | **WIP** | No-op — needs TODO plan input mechanism |
| SDK integration | **Not started** | ADR-0101 accepted, needs WorkflowsInterface |
| Checkpointing | **Partial** | MemorySaver in-memory only, needs Redis backend |

## Usage (CLI — current)

```bash
# Run GMP
python3 -m workflows.dags.gmp.executor "task description" --tier RUNTIME

# Resume from checkpoint
python3 -m workflows.dags.gmp.executor --resume <thread_id>

# Print Mermaid diagram
python3 -m workflows.dags.gmp.executor --mermaid
```

## Usage (SDK — target, per ADR-0101)

```python
sdk = L9SDK(agent_id="emma", tenant_id="l9")
result = await sdk.workflows.run_dag("gmp-execution-v1", task="...", tier="RUNTIME")
```

## References

- **ADR-0101:** DAG Executors via SDK, Not Per-Service Routes
- **ADR-0021:** LangGraph Node Wrapper Pattern
- **SessionDAG:** `workflows/dags/gmp_execution_dag.py` (Cursor-agent version)
- **SDK:** `SDK/SDK.py` (target integration point)
