# GMP-68: Memory Governance Gate — Part A (Non-Protected Files)

---
## VARIABLE BINDINGS

```yaml
TASK_NAME: memory_governance_gate_part_a
EXECUTION_SCOPE: >
  Implement centralized governance gate for memory operations (NON-PROTECTED FILES ONLY).
  Creates governance_gate.py, tests, and integrates with MCP memory, API router, 
  compliance audit, and runtime helpers. Does NOT touch protected substrate_service.py,
  substrate_repository.py, ingestion.py, or retrieval.py.
SPEC_PATH: "mcp_memory/Deployment Guide-Memory Governance Hardening.md"
REPORT_ROOT: "/Users/ib-mac/Projects/L9/reports"
RISK_LEVEL: Medium
IMPACT_METRICS: Memory security, scope isolation, Cursor/L-CTO separation
VALIDATION_NOTES: >
  Run governance unit tests after implementation.
  Verify Cursor cannot access l-private scope in tests.
  Protected files deferred to GMP-69.
```

---

## CONSTRAINTS

- [x] KERNEL-TIER files NOT in scope (substrate_service.py, etc. deferred to GMP-69)
- [ ] No placeholders in output
- [ ] All SQL queries must use parameterized queries (no injection)
- [ ] Governance context must be enforced at all entry points

---

## TODO PLAN (LOCKED)

### Phase 1: Foundation — Core Governance Module (NEW FILES)

- [T1] File: `/Users/ib-mac/Projects/L9/memory/governance_gate.py`
      Lines: 1-186
      Action: **Create**
      Target: `MemoryGovernanceContext, governance_context(), require_governance_context(), build_scope_project_filter()`
      Change: Create new governance gate module with:
        - MemoryGovernanceContext frozen dataclass (caller_id, role, scope, project_id, allowed_scopes, tenant_id, org_id, user_id, creator, source)
        - __post_init__ validation (caller_id required, project_id required, scope in allowed_scopes, Cursor cannot have l-private)
        - ContextVar _governance_context for async-safe propagation
        - build_governance_context() factory function
        - set_governance_context() / reset_governance_context()
        - require_governance_context(operation) fail-closed enforcer
        - _fallback_context() from env vars
        - ensure_governance_context() async context manager with fallback
        - governance_context() async context manager
        - enforce_packet_governance() packet metadata override
        - build_scope_project_filter() SQL filter builder with parameterized queries
      Gate: py_compile, lint
      Imports: contextlib.asynccontextmanager, contextvars.ContextVar, dataclasses.dataclass, typing.AsyncGenerator, typing.Optional, typing.Sequence, os

- [T2] File: `/Users/ib-mac/Projects/L9/tests/test_memory_governance_gate.py`
      Lines: 1-61
      Action: **Create**
      Target: `test_build_governance_context_blocks_cursor_private_scope, test_enforce_packet_governance_rejects_client_metadata, test_ensure_governance_context_uses_env_fallback`
      Change: Create unit tests for governance gate:
        - Test Cursor (caller_id="C") cannot have l-private in allowed_scopes → raises RuntimeError
        - Test client-supplied metadata (caller mismatch) is rejected → raises RuntimeError
        - Test env fallback works when context missing (L9_MEMORY_CALLER_ID, L9_PROJECT_ID)
      Gate: pytest
      Imports: pytest, sys, pathlib.Path, importlib.util, core.schemas.PacketEnvelopeIn

### Phase 2: Memory Module Exports

- [T3] File: `/Users/ib-mac/Projects/L9/memory/__init__.py`
      Lines: 199 (after SubstrateAlignmentChecker import)
      Action: **Insert**
      Target: `governance_gate exports in __all__`
      Change: Add governance gate import and exports:
        ```python
        # Governance Gate (GMP-68)
        from memory.governance_gate import (
            MemoryGovernanceContext,
            build_governance_context,
            governance_context,
            require_governance_context,
            ensure_governance_context,
            enforce_packet_governance,
            build_scope_project_filter,
        )
        ```
        And add to __all__ list
      Gate: py_compile
      Imports: NONE (relative imports)

### Phase 3: MCP Memory Integration

- [T4] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/config.py`
      Lines: 89 (after MCP_API_KEYC)
      Action: **Insert**
      Target: `MCP_PROJECT_ID setting`
      Change: Add project isolation config:
        ```python
        # Project isolation (server-derived, not client-supplied)
        MCP_PROJECT_ID: str = "l9"
        ```
      Gate: py_compile
      Imports: NONE

- [T5] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/db.py`
      Lines: 10 (imports), 76-95 (execute/fetch functions)
      Action: **Insert**
      Target: `require_governance_context calls in DB functions`
      Change: 
        - Add import: `from memory.governance_gate import require_governance_context`
        - Add `require_governance_context("mcp_memory.execute")` at start of execute()
        - Add `require_governance_context("mcp_memory.fetch_one")` at start of fetch_one()
        - Add `require_governance_context("mcp_memory.fetch_all")` at start of fetch_all()
        - Add `require_governance_context("mcp_memory.insert_many")` at start of insert_many()
      Gate: py_compile
      Imports: memory.governance_gate.require_governance_context

- [T6] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory.py`
      Lines: 17-22
      Action: **Replace**
      Target: `router initialization`
      Change: Add dependency that disables legacy routes:
        - Add import: `from fastapi import Depends`
        - Create function:
          ```python
          def _legacy_memory_disabled() -> None:
              raise HTTPException(status_code=410, detail="Legacy memory routes disabled")
          ```
        - Replace `router = APIRouter()` with `router = APIRouter(dependencies=[Depends(_legacy_memory_disabled)])`
      Gate: py_compile
      Imports: fastapi.Depends

- [T7] File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory_unified.py`
      Lines: 22-30 (imports), 40-60 (scope mapping), 74-110 (save_memory_handler start)
      Action: **Replace**
      Target: `imports, map_mcp_scope_to_db_scope(), save_memory_handler() start`
      Change:
        - Add import: `from memory.governance_gate import ensure_governance_context, require_governance_context`
        - Simplify map_mcp_scope_to_db_scope(): return mcp_scope directly (no mapping needed after migration)
        - Simplify map_db_scope_to_mcp_scope(): return db_scope directly
        - In save_memory_handler(): add `ctx = require_governance_context("mcp_memory.save_memory")`
        - Validate: `if scope != ctx.scope: raise HTTPException(status_code=403, detail="Scope not authorized")`
        - In _save_via_main_pipeline(): add `ctx = require_governance_context("mcp_memory.save_memory.pipeline")`
        - Use ctx.project_id instead of deriving from metadata
        - Use ctx.caller_id, ctx.creator, ctx.source for envelope metadata
      Gate: py_compile, lint
      Imports: memory.governance_gate.ensure_governance_context, memory.governance_gate.require_governance_context

### Phase 5: API Router Integration

- [T8] File: `/Users/ib-mac/Projects/L9/api/memory/router.py`
      Lines: 12-14 (imports), 28-42 (after router definition)
      Action: **Insert**
      Target: `governance dependency for router`
      Change:
        - Add imports:
          ```python
          from typing import AsyncGenerator
          import os
          from memory.governance_gate import (
              build_governance_context,
              governance_context,
          )
          ```
        - Create dependency function:
          ```python
          async def memory_governance_context_dependency(
              _: bool = Depends(verify_api_key),
          ) -> AsyncGenerator[None, None]:
              scope = os.getenv("L9_MEMORY_SCOPE", "shared")
              project_id = os.getenv("L9_PROJECT_ID", "l9")
              ctx = build_governance_context(
                  caller_id="api",
                  role="end_user",
                  scope=scope,
                  project_id=project_id,
                  allowed_scopes=[scope],
              )
              async with governance_context(ctx):
                  yield
          ```
        - Replace router: `router = APIRouter(dependencies=[Depends(memory_governance_context_dependency)])`
      Gate: py_compile, lint
      Imports: typing.AsyncGenerator, os, memory.governance_gate.build_governance_context, memory.governance_gate.governance_context

### Phase 6: Compliance/Audit Fix

- [T9] File: `/Users/ib-mac/Projects/L9/core/compliance/audit_log.py`
      Lines: 202-204 (in log_memory_write method)
      Action: **Replace**
      Target: `return statement when substrate is None`
      Change: Change `return True` to `return False` when `self._substrate is None`
        - Rationale: Returning True incorrectly indicates audit success when no logging occurred
        - This is a semantic fix: False means "audit not logged" which is accurate
      Gate: py_compile
      Imports: NONE

### Phase 7: Test Update

- [T10] File: `/Users/ib-mac/Projects/L9/tests/integration/test_compliance_audit.py`
       Lines: ~180 (assertion on substrate=None case)
       Action: **Replace**
       Target: `assertion for substrate=None audit behavior`
       Change: Update test to expect False when substrate is None:
         - Find assertion checking log_memory_write with None substrate
         - Change expected result from True to False (or update logic accordingly)
       Gate: pytest
       Imports: NONE

---

## VALIDATION GATES

- [ ] `py_compile` — All modified files compile
- [ ] `ruff check` — Lint passes
- [ ] `pytest tests/test_memory_governance_gate.py -v` — Governance unit tests pass
- [ ] `pytest tests/integration/test_compliance_audit.py -v` — Audit tests pass

---

## EXECUTION ORDER

1. **T1**: Create `memory/governance_gate.py`
2. **T2**: Create `tests/test_memory_governance_gate.py`
3. **T3**: Export from `memory/__init__.py`
4. **T4**: Add MCP_PROJECT_ID to config
5. **T5**: Add governance checks to `mcp_memory/src/db.py`
6. **T6**: Disable legacy routes in `mcp_memory/src/routes/memory.py`
7. **T7**: Integrate governance in `mcp_memory/src/routes/memory_unified.py`
8. **T8**: Add governance dependency to `api/memory/router.py`
9. **T9**: Fix audit_log.py return value
10. **T10**: Update compliance audit test

---

## DEFERRED TO GMP-69 (Protected Files)

The following TODO items require PROTECTED file modifications and are deferred:

- `memory/substrate_service.py` — Add require_governance_context, enforce_packet_governance
- `memory/substrate_repository.py` — Add scope/project filtering to all queries
- `memory/ingestion.py` — Add governance context enforcement
- `memory/retrieval.py` — Add scope/project filtering to all retrieval methods

---

## ROLLBACK PLAN

If governance enforcement causes issues:
1. Remove router dependencies (T6, T8)
2. Remove require_governance_context calls from db.py (T5)
3. Governance gate module can remain (no side effects when not called)

---
