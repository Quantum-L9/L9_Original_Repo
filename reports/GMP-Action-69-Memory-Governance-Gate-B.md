# GMP-69: Memory Governance Gate — Part B (Protected Files)

---
## VARIABLE BINDINGS

```yaml
TASK_NAME: memory_governance_gate_part_b
EXECUTION_SCOPE: >
  Complete governance gate integration for PROTECTED memory files.
  Adds governance enforcement to substrate_service.py, substrate_repository.py,
  ingestion.py, and retrieval.py. Requires explicit approval per L9 KERNEL-TIER rules.
SPEC_PATH: "mcp_memory/Deployment Guide-Memory Governance Hardening.md"
REPORT_ROOT: "/Users/ib-mac/Projects/L9/reports"
RISK_LEVEL: High
IMPACT_METRICS: Memory security, query isolation, all memory operations
VALIDATION_NOTES: >
  Run full memory integration tests after implementation.
  Verify all queries include scope/project filters.
  Test both L and Cursor access patterns.
PREREQUISITE: GMP-68 (Part A) must be complete
```

---

## ⚠️ PROTECTED FILES WARNING

This GMP modifies PROTECTED files per `.cursor/rules/gmp.md`:
- `memory/substrate_service.py` — Core memory substrate service
- `memory/substrate_repository.py` — Repository layer
- `memory/ingestion.py` — Packet ingestion pipeline
- `memory/retrieval.py` — Retrieval pipeline

**Requires explicit approval before execution.**

---

## CONSTRAINTS

- [ ] GMP-68 must be complete (governance_gate.py exists)
- [ ] All queries must use parameterized filters (build_scope_project_filter)
- [ ] No breaking changes to public API signatures
- [ ] All existing tests must continue to pass

---

## TODO PLAN (LOCKED)

### Phase 4A: Substrate Service (PROTECTED)

- [T1] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py`
      Lines: 17-18 (imports)
      Action: **Insert**
      Target: `governance_gate imports`
      Change: Add imports:
        ```python
        from memory.governance_gate import enforce_packet_governance, require_governance_context
        ```
      Gate: py_compile
      Imports: memory.governance_gate.enforce_packet_governance, memory.governance_gate.require_governance_context

- [T2] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py`
      Lines: 180-220 (write_packet method start)
      Action: **Insert**
      Target: `write_packet governance enforcement`
      Change: Add at start of write_packet():
        ```python
        ctx = require_governance_context("write_packet")
        if tenant_id and tenant_id != ctx.tenant_id:
            raise RuntimeError("tenant_id must be derived server-side")
        if org_id and org_id != ctx.org_id:
            raise RuntimeError("org_id must be derived server-side")
        if user_id and user_id != ctx.user_id:
            raise RuntimeError("user_id must be derived server-side")
        if role != "end_user" and role != ctx.role:
            raise RuntimeError("role must be derived server-side")
        packet_in = enforce_packet_governance(packet_in, ctx)
        ```
      Gate: py_compile, lint
      Imports: NONE (already imported in T1)

- [T3] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py`
      Lines: 159-180 (get_packet, search_packets_by_thread, search_packets_by_type, query_packets)
      Action: **Insert**
      Target: `read operation governance checks`
      Change: Add `require_governance_context("operation_name")` at start of each method
      Gate: py_compile
      Imports: NONE

### Phase 4B: Ingestion Pipeline (PROTECTED)

- [T4] File: `/Users/ib-mac/Projects/L9/memory/ingestion.py`
      Lines: 27-32 (imports)
      Action: **Insert**
      Target: `governance_gate imports`
      Change: Add imports:
        ```python
        from memory.governance_gate import (
            enforce_packet_governance,
            ensure_governance_context,
            require_governance_context,
        )
        ```
      Gate: py_compile
      Imports: memory.governance_gate

- [T5] File: `/Users/ib-mac/Projects/L9/memory/ingestion.py`
      Lines: 85-100 (ingest_packet or IngestionPipeline.ingest)
      Action: **Insert**
      Target: `ingest governance enforcement`
      Change: Add governance context requirement and packet enforcement
      Gate: py_compile
      Imports: NONE

### Phase 4C: Retrieval Pipeline (PROTECTED)

- [T6] File: `/Users/ib-mac/Projects/L9/memory/retrieval.py`
      Lines: 24-28 (imports)
      Action: **Insert**
      Target: `governance_gate imports`
      Change: Add imports:
        ```python
        from memory.governance_gate import (
            build_scope_project_filter,
            ensure_governance_context,
            require_governance_context,
        )
        ```
      Gate: py_compile
      Imports: memory.governance_gate

- [T7] File: `/Users/ib-mac/Projects/L9/memory/retrieval.py`
      Lines: 326-400 (fetch_thread, fetch_lineage, fetch_facts, fetch_insights)
      Action: **Replace**
      Target: `RetrievalPipeline query methods`
      Change: For each method:
        1. Add `ctx = require_governance_context("retrieval.method_name")`
        2. Call `filter_clause, params, next_idx = build_scope_project_filter(ctx, param_idx=N)`
        3. Inject filter_clause into SQL WHERE clause
        4. Pass params to query
      Gate: py_compile, lint
      Imports: NONE

### Phase 4D: Repository Layer (PROTECTED)

- [T8] File: `/Users/ib-mac/Projects/L9/memory/substrate_repository.py`
      Lines: 20-30 (imports)
      Action: **Insert**
      Target: `governance_gate imports`
      Change: Add imports:
        ```python
        from memory.governance_gate import build_scope_project_filter, require_governance_context
        ```
      Gate: py_compile
      Imports: memory.governance_gate

- [T9] File: `/Users/ib-mac/Projects/L9/memory/substrate_repository.py`
      Lines: 200-450 (query methods)
      Action: **Replace**
      Target: `repository query methods with scope filtering`
      Change: For relevant query methods:
        1. Add `ctx = require_governance_context("repository.method_name")`
        2. Use `build_scope_project_filter(ctx, ...)` for all SELECT queries
        3. Ensure JOINs on packet_store for scope/project_id filtering
      Gate: py_compile, lint
      Imports: NONE

---

## VALIDATION GATES

- [ ] `py_compile` — All 4 protected files compile
- [ ] `ruff check` — Lint passes
- [ ] `pytest tests/memory/` — All memory tests pass
- [ ] `pytest tests/integration/` — Integration tests pass

---

## EXECUTION ORDER

1. **T1-T3**: substrate_service.py (write + read governance)
2. **T4-T5**: ingestion.py (ingest governance)
3. **T6-T7**: retrieval.py (query filtering)
4. **T8-T9**: substrate_repository.py (repository filtering)

---

## ROLLBACK PLAN

If governance enforcement breaks memory operations:
1. Set `L9_GOVERNANCE_GATE_BYPASS=true` in environment
2. Add bypass check at start of require_governance_context()
3. Monitor logs for governance violations
4. Fix queries incrementally

---
