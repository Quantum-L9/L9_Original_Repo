# GMP Action: Memory Governance Gate Implementation

---
## VARIABLE BINDINGS

```yaml
TASK_NAME: memory_governance_gate_implementation
EXECUTION_SCOPE: >
  Implement centralized governance gate for all memory operations.
  Enforces caller identity (server-derived), project isolation (project_id),
  and scope restrictions (including l-private protections for Cursor).
SPEC_PATH: "mcp_memory/Deployment Guide-Memory Governance Hardening.md"
REPORT_ROOT: "/Users/ib-mac/Projects/L9/reports"
RISK_LEVEL: High
IMPACT_METRICS: Memory security, scope isolation, Cursor/L-CTO separation
VALIDATION_NOTES: >
  Run governance invariant tests after implementation.
  Verify Cursor cannot access l-private scope.
  Verify all memory operations require governance context.
```

---

## CONSTRAINTS

- [ ] KERNEL-TIER files require explicit TODO entry (memory/substrate_service.py is PROTECTED)
- [ ] No placeholders in output
- [ ] All SQL queries must use parameterized queries (no string interpolation)
- [ ] Governance context must be enforced at all entry points

---

## TODO PLAN (LOCKED)

### Phase 1: Foundation — Core Governance Module (NEW FILES)

- [T1] File: `/Users/ib-mac/Projects/L9/memory/governance_gate.py`
      Lines: 1-186
      Action: **Create**
      Target: `MemoryGovernanceContext, governance_context(), require_governance_context(), build_scope_project_filter()`
      Change: Create new governance gate module with:
        - MemoryGovernanceContext frozen dataclass (caller_id, role, scope, project_id, allowed_scopes)
        - ContextVar for async-safe context propagation
        - build_governance_context() factory function
        - governance_context() async context manager
        - require_governance_context() fail-closed enforcer
        - enforce_packet_governance() packet metadata override
        - build_scope_project_filter() SQL filter builder
      Gate: py_compile, lint
      Imports: contextlib.asynccontextmanager, contextvars.ContextVar, dataclasses.dataclass, typing.AsyncGenerator

- [T2] File: `/Users/ib-mac/Projects/L9/tests/test_memory_governance_gate.py`
      Lines: 1-61
      Action: **Create**
      Target: `test_build_governance_context_blocks_cursor_private_scope, test_enforce_packet_governance_rejects_client_metadata, test_ensure_governance_context_uses_env_fallback`
      Change: Create unit tests for governance gate:
        - Test Cursor cannot have l-private in allowed_scopes
        - Test client-supplied metadata is rejected
        - Test env fallback works when context missing
      Gate: pytest
      Imports: pytest, core.schemas.PacketEnvelopeIn

### Phase 2: Memory Module Exports

- [T3] File: `/Users/ib-mac/Projects/L9/memory/__init__.py`
      Lines: 195-199
      Action: **Insert** (after SubstrateAlignmentChecker import block)
      Target: `governance_gate exports`
      Change: Add governance gate exports:
        ```python
        # Governance Gate (GMP-GOV)
        from memory.governance_gate import (
            MemoryGovernanceContext,
            build_governance_context,
            governance_context,
            require_governance_context,
            enforce_packet_governance,
            build_scope_project_filter,
        )
        ```
      Gate: py_compile
      Imports: NONE (using relative imports)

### Phase 3: MCP Memory Integration

- [T4] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/config.py`
      Lines: 89-91
      Action: **Insert** (after MCP_API_KEYC line)
      Target: `MCP_PROJECT_ID setting`
      Change: Add project isolation config:
        ```python
        # Project isolation (server-derived, not client-supplied)
        MCP_PROJECT_ID: str = "l9"
        ```
      Gate: py_compile
      Imports: NONE

- [T5] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/db.py`
      Lines: 10 (after imports), 76-80 (in execute/fetch functions)
      Action: **Insert**
      Target: `require_governance_context calls`
      Change: Add governance check to all DB access functions:
        - Import: `from memory.governance_gate import require_governance_context`
        - Add `require_governance_context("mcp_memory.execute")` before pool.acquire() in execute()
        - Add same check to fetch_one(), fetch_all(), insert_many()
      Gate: py_compile
      Imports: memory.governance_gate.require_governance_context

- [T6] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/mcp_server.py`
      Lines: 295-520 (handle_tool_call function)
      Action: **Replace**
      Target: `handle_tool_call()`
      Change: Wrap each tool handler in governance_context():
        - Build governance_ctx at start using build_governance_context()
        - Wrap save_memory, search_memory, get_memory_stats, etc. in `async with governance_context(governance_ctx):`
        - Remove inline scope enforcement (now handled by governance gate)
        - Use settings.MCP_PROJECT_ID instead of hardcoded "l9"
      Gate: py_compile, lint
      Imports: memory.governance_gate.build_governance_context, memory.governance_gate.governance_context

- [T7] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory.py`
      Lines: 17-22
      Action: **Replace**
      Target: `router initialization`
      Change: Add dependency that disables legacy routes:
        ```python
        def _legacy_memory_disabled() -> None:
            raise HTTPException(status_code=410, detail="Legacy memory routes disabled")

        router = APIRouter(dependencies=[Depends(_legacy_memory_disabled)])
        ```
      Gate: py_compile
      Imports: fastapi.Depends

- [T8] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory_unified.py`
      Lines: 22-30, 74-180
      Action: **Replace**
      Target: `save_memory_handler(), map_mcp_scope_to_db_scope()`
      Change: 
        - Import governance_gate functions
        - Simplify scope mapping (direct passthrough: developer→developer, l-private→l-private, global→global)
        - Add `ctx = require_governance_context("mcp_memory.save_memory")` at handler start
        - Validate scope matches ctx.scope
        - Use ctx.project_id instead of deriving from metadata
        - Use ctx.caller_id, ctx.creator, ctx.source for envelope metadata
      Gate: py_compile, lint
      Imports: memory.governance_gate.require_governance_context, memory.governance_gate.ensure_governance_context

### Phase 4: Core Memory Module Integration (PROTECTED FILES)

- [T9] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py` ⚠️ PROTECTED
      Lines: 17-18 (imports), 180-220 (write_packet)
      Action: **Replace**
      Target: `write_packet()` method
      Change:
        - Import: `from memory.governance_gate import enforce_packet_governance, require_governance_context`
        - Add `ctx = require_governance_context("write_packet")` at method start
        - Validate tenant_id/org_id/user_id match ctx values
        - Call `packet_in = enforce_packet_governance(packet_in, ctx)` before processing
        - Use ctx.tenant_id, ctx.org_id, ctx.user_id for RLS scope
      Gate: py_compile, lint, pytest tests/memory/
      Imports: memory.governance_gate.enforce_packet_governance, memory.governance_gate.require_governance_context

- [T10] File: `/Users/ib-mac/Projects/L9/memory/ingestion.py`
       Lines: 27-32 (imports), 85-100 (ingest_packet)
       Action: **Insert**
       Target: `governance imports and enforcement`
       Change:
         - Import governance_gate functions
         - Add governance context check in ingest_packet()
         - Apply enforce_packet_governance() before processing
       Gate: py_compile
       Imports: memory.governance_gate.enforce_packet_governance, memory.governance_gate.ensure_governance_context, memory.governance_gate.require_governance_context

- [T11] File: `/Users/ib-mac/Projects/L9/memory/retrieval.py`
       Lines: 24-28 (imports), 326-400 (fetch_thread, fetch_lineage, fetch_facts, fetch_insights)
       Action: **Replace**
       Target: `RetrievalPipeline methods`
       Change:
         - Import governance_gate functions
         - Add `ctx = require_governance_context("retrieval.X")` at start of each method
         - Call `build_scope_project_filter(ctx, param_idx=N)` to get SQL filter clause
         - Inject filter into all SELECT queries
         - Use f-strings for SQL with filter_clause interpolation
       Gate: py_compile, lint
       Imports: memory.governance_gate.build_scope_project_filter, memory.governance_gate.ensure_governance_context, memory.governance_context.require_governance_context

### Phase 5: API Router Integration

- [T12] File: `/Users/ib-mac/Projects/L9/api/memory/router.py`
       Lines: 12-28 (imports), 28-60 (router setup)
       Action: **Replace**
       Target: `router initialization with governance dependency`
       Change:
         - Import governance_gate functions
         - Create `memory_governance_context_dependency()` async generator
         - Add as router dependency: `router = APIRouter(dependencies=[Depends(memory_governance_context_dependency)])`
         - Get scope/project_id from env vars (L9_MEMORY_SCOPE, L9_PROJECT_ID)
       Gate: py_compile, lint
       Imports: memory.governance_gate.build_governance_context, memory.governance_gate.governance_context, typing.AsyncGenerator

### Phase 6: Compliance/Audit Integration

- [T13] File: `/Users/ib-mac/Projects/L9/core/compliance/audit_log.py`
       Lines: 202-204
       Action: **Replace**
       Target: `log_memory_write return when substrate is None`
       Change: Change `return True` to `return False` when `self._substrate is None`
         - Rationale: Returning True incorrectly indicates success when no logging occurred
       Gate: py_compile
       Imports: NONE

### Phase 7: Runtime Helpers

- [T14] File: `/Users/ib-mac/Projects/L9/runtime/memory_helpers.py`
       Lines: 15-25 (imports), 45-120 (helper functions)
       Action: **Replace**
       Target: `memory helper functions`
       Change:
         - Import governance_gate
         - Wrap memory operations in governance_context
         - Derive scope/project from context
       Gate: py_compile
       Imports: memory.governance_gate.governance_context, memory.governance_gate.build_governance_context

### Phase 8: Repository Layer

- [T15] File: `/Users/ib-mac/Projects/L9/memory/substrate_repository.py`
       Lines: 50-100, 200-450
       Action: **Replace**
       Target: `query methods with scope filtering`
       Change:
         - Import governance_gate
         - Add scope/project filter to all SELECT queries using build_scope_project_filter()
         - Ensure all queries join on packet_store to filter by scope/project_id
       Gate: py_compile, lint
       Imports: memory.governance_gate.build_scope_project_filter, memory.governance_gate.require_governance_context

---

## VALIDATION GATES

- [ ] `py_compile` — All modified files compile
- [ ] `ruff check` — Lint passes
- [ ] `pytest tests/test_memory_governance_gate.py` — New governance tests pass
- [ ] `pytest tests/memory/test_governance_invariants.py` — Invariant tests pass (if exists)
- [ ] `pytest tests/integration/test_compliance_audit.py` — Audit tests pass

---

## EXECUTION ORDER

1. **Phase 1** (T1-T2): Create governance_gate.py and tests
2. **Phase 2** (T3): Export from memory/__init__.py
3. **Phase 3** (T4-T8): MCP memory integration
4. **Phase 4** (T9-T11): Core memory modules (PROTECTED - requires approval)
5. **Phase 5** (T12): API router integration
6. **Phase 6** (T13): Audit compliance fix
7. **Phase 7** (T14): Runtime helpers
8. **Phase 8** (T15): Repository layer

---

## ROLLBACK PLAN

If governance enforcement causes issues:
1. Set `L9_GOVERNANCE_GATE_ENABLED=false` in environment
2. Fallback context uses env vars (L9_MEMORY_CALLER_ID, L9_PROJECT_ID)
3. Remove router dependencies without changing module code

---

## FINAL DECLARATION

After all phases complete:
- All memory operations require governance context
- Cursor cannot access l-private scope
- Project isolation enforced at DB level
- Caller identity is server-derived (not client-supplied)
- SQL queries use parameterized filters (no injection)
