# ADR-0101: DAG Executors Exposed via SDK Adapter — Not Per-Service FastAPI Routes

## Status

**Accepted** — 2026-02-14

## Context

L9 has LangGraph-based DAG executors (e.g., `GMPLangGraphExecutor` in `workflows/dags/gmp/`) that orchestrate multi-step workflows with state management, conditional routing, and checkpointing.

These executors need to be consumable by L9 agents (L, Emma). Two approaches were considered:

### Option A: Per-Service FastAPI Routes (Rejected)

Create dedicated API endpoints for each executor:

```python
# ❌ REJECTED — Creates route sprawl
@router.post("/workflows/gmp/run")
async def run_gmp(task: str, tier: str): ...

@router.post("/workflows/gmp/resume")
async def resume_gmp(thread_id: str, updates: dict): ...
# ... repeat for every DAG executor
```

Problems:
- Route sprawl — every new DAG executor requires new routes
- Inconsistent interfaces — each executor gets bespoke endpoints
- No automatic context injection (agent_id, tenant_id)
- Duplicates the SDK adapter pattern already established in `SDK/SDK.py`

### Option B: SDK Interface (Accepted)

Wire DAG executors into the existing `L9SDK` as a `WorkflowsInterface`:

```python
# ✅ ACCEPTED — Follows SDK adapter pattern
sdk = L9SDK(agent_id="emma", tenant_id="l9")
result = await sdk.workflows.run_dag("gmp-execution-v1", task="...", tier="RUNTIME")
state = await sdk.workflows.get_state("gmp-execution-v1", thread_id)
```

## Decision

**All LangGraph DAG executors MUST be exposed through the SDK adapter (`SDK/SDK.py`), not through dedicated FastAPI routes.**

This is a specific application of the broader SDK-first principle in ADR-0102.

## Consequences

### Positive
- Single integration point for all DAG executors
- Automatic agent_id/tenant_id context injection
- Consistent interface for all clients
- New DAG executors automatically available via registry

### Negative
- SDK becomes a larger surface area (mitigated by lazy loading)

## References

- **ADR-0061:** L9 Facade Pattern for Simplified API
- **ADR-0100:** Slash Commands Are DAG-Triggered Only
- **ADR-0102:** SDK-First External Interface — Reduce Exposed API Surface
- **SDK:** `SDK/SDK.py` — `WorkflowsInterface`
- **GMP Executor:** `workflows/dags/gmp/` — first LangGraph executor wired in
