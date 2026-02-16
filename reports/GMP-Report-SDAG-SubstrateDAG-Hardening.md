# GMP Report: GMP-SDAG — SubstrateDAG Hardening + EnrichmentDAG Swap

| Field | Value |
|-------|-------|
| **GMP ID** | GMP-SDAG |
| **Title** | SubstrateDAG Hardening + EnrichmentDAG Swap |
| **Tier** | KERNEL_TIER |
| **Date** | 2026-02-13 |
| **Status** | PASS |

---

## TODO Plan (Locked)

| # | Action | File | Op | Status |
|---|--------|------|----|--------|
| 1 | Strip governance enforcement from intake_node | `memory/substrate_dag.py` | DELETE | ✅ |
| 2 | Strip audit preparation from intake_node | `memory/substrate_dag.py` | DELETE | ✅ |
| 3 | Add `@must_stay_async` to 4 undecorated async nodes | `memory/substrate_dag.py` | INSERT | ✅ |
| 4 | Fix no-repository false-positive in memory_write_node | `memory/substrate_dag.py` | REPLACE | ✅ |
| 5 | Fix hardcoded `plastic_brokerage` domain | `memory/substrate_dag.py` | REPLACE | ✅ |
| 6 | Swap `EnrichmentDAG` → `SubstrateDAG` in service | `memory/substrate_service.py` | REPLACE | ✅ |
| 7 | Update tests for new behavior | `tests/memory/test_ingestion_pipeline_audit.py` | REPLACE | ✅ |

---

## Scope Boundaries

**May modify:**
- `memory/substrate_dag.py` — DAG node functions
- `memory/substrate_service.py` — DAG initialization
- `tests/memory/test_ingestion_pipeline_audit.py` — Test assertions

**May NOT modify:**
- `memory/substrate_repository.py` — DB layer unchanged
- `memory/governance_gate.py` — Governance layer unchanged
- `memory/audit_utils.py` — Audit layer unchanged
- `core/schemas/` — Schema layer unchanged

---

## Architecture Decision: Option A

**Decision:** `substrate_service.write_packet()` remains the authoritative governance/audit layer. `intake_node` is stripped of governance and audit code.

**Rationale:**
1. The intake_node governance had a soft-fail `try/except` that silently continued on failure — a security gap
2. `write_packet()` governance is fail-closed (raises before DAG runs)
3. DAG swappability: governance is independent of which DAG runs
4. Testability: DAG nodes don't need governance context mocks

---

## Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `memory/substrate_dag.py` | -47/+15 | Stripped governance/audit from intake_node, added 4x `@must_stay_async`, fixed no-repo false positive, fixed `plastic_brokerage` → `l9` |
| `memory/substrate_service.py` | -4/+6 | Swapped `EnrichmentDAG` → `SubstrateDAG` import and constructor |
| `tests/memory/test_ingestion_pipeline_audit.py` | +22/-4 | Added mock repositories to 2 tests that previously ran without one |

---

## Bugs Fixed

| # | Bug | Severity | Fix |
|---|-----|----------|-----|
| 1 | **Double governance**: intake_node re-ran governance that write_packet() already enforced | Medium | Removed from intake_node |
| 2 | **Double audit**: intake_node re-ran audit prep that write_packet() already ran | Medium | Removed from intake_node |
| 3 | **Soft-fail governance**: intake_node caught governance exceptions and continued | High | Removed — service layer is fail-closed |
| 4 | **Missing `@must_stay_async`**: 4 async nodes could be accidentally called synchronously | Medium | Added decorator to all 4 |
| 5 | **False-positive written_tables**: No-repository path reported tables as written | Medium | Now reports error instead |
| 6 | **Hardcoded domain**: `plastic_brokerage` default in metadata | Low | Changed to `l9` |
| 7 | **Deprecated DAG still active**: EnrichmentDAG (archived, deprecated) was still the production DAG | High | Swapped to SubstrateDAG |

---

## Validation Results

```
tests/memory/test_substrate_dag.py                  — 22 passed
tests/memory/test_substrate_dag_native.py            — 37 passed
tests/memory/test_enrichment_dag.py                  — 37 passed
tests/memory/test_unified_pipeline.py                — 9 passed
tests/memory/test_ingestion_pipeline_audit.py        — 50 passed
tests/memory/test_mcp_bypass_compliance.py           — 3 passed, 3 skipped
                                                     ─────────────────
TOTAL                                                  158 passed, 3 skipped, 0 failures
```

---

## Phase 5: Recursive Verification

| Check | Result |
|-------|--------|
| Scope drift vs Phase 0 plan | ✅ No drift — all 7 items executed as planned |
| No hidden behavior changes | ✅ Only governance/audit removal + DAG swap |
| Tests cover new behavior | ✅ Mock repos in tests verify actual write path |
| Backward compatibility | ✅ `memory/__init__.py` still re-exports EnrichmentDAG via shim |
| No new imports added | ✅ Only import changed: `enrichment_dag` → `substrate_dag` |

---

## Outstanding Items

- **EnrichmentDAG deprecation cleanup**: `memory/enrichment_dag.py` shim and `memory/archive/enrichment_dag.py` can be removed once all external consumers (tests, docs) are migrated
- **SubstrateDAG.run() now handles intake validation**: Since write_packet() already validates, the intake_node duplicate detection is the only remaining check — consider if this is needed or if write_packet()'s `PacketValidator.validate()` is sufficient

---

## Final Declaration

All 7 TODO items executed. 158 tests pass. No scope drift. Option A architecture decision documented and enforced. EnrichmentDAG replaced by SubstrateDAG as the production memory ingestion pipeline.

**GMP-SDAG: PASS**
