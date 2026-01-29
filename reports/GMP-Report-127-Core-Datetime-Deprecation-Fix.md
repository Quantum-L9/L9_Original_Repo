# GMP Report: Core datetime.utcnow() Deprecation Fix

**GMP ID:** GMP-127  
**Title:** Core datetime.utcnow() Deprecation Fix  
**Tier:** RUNTIME  
**Date:** 2026-01-28  
**Status:** PASS ✅

---

## Summary

Fixed Python 3.12 deprecated `datetime.utcnow()` API across 17 files in `core/`, `orchestration/`, and `motifs/` modules. Replaced with timezone-aware `datetime.now(timezone.utc)`.

---

## Scope

### Batches Executed

| Batch | Files | Replacements |
|-------|-------|--------------|
| GMP-MOTIFS-FIX | 3 | 3 |
| GMP-ORCH-DATETIME | 5 | 46 |
| GMP-CORE-DATETIME-BATCH1 | 3 | 52 |
| GMP-CORE-DATETIME-BATCH2 | 3 | 24 |
| GMP-CORE-DATETIME-BATCH3 | 3 | 19 |
| GMP-CORE-DATETIME-BATCH4 | 4 | 20 |
| **TOTAL** | **21** | **164** |

---

## Files Modified

### motifs/
- `motif_feedback_graph.py`
- `tensor_motif_linker.py`
- `__init__.py` (broken imports removed)

### orchestration/
- `orchestrator_kernel.py`
- `unified_controller.py`
- `plan_executor.py`
- `cell_orchestrator.py`
- `task_router.py`

### core/agents/bootstrap/
- `orchestrator.py`

### core/packet_envelope/
- `governance.py`
- `scalability.py`

### core/bayesian/
- `hybrid_kernel.py`

### core/schemas/
- `research_factory_state.py`
- `research_factory_models.py`
- `event_stream.py`

### core/learning/
- `auto_calibrator.py`

### core/agents/
- `agent_instance.py`

### core/tools/
- `base_registry.py`

### core/protocols/
- `connection_protocols.py`

### core/observability/
- `models.py`

### core/eos/
- `schemas.py`

---

## Changes Made

### Pattern Replacement

1. **Direct calls:**
   ```python
   # Before
   datetime.utcnow()
   
   # After
   datetime.now(timezone.utc)
   ```

2. **Factory references (dataclass/Pydantic):**
   ```python
   # Before
   field(default_factory=datetime.utcnow)
   Field(default_factory=datetime.utcnow)
   
   # After
   field(default_factory=lambda: datetime.now(timezone.utc))
   Field(default_factory=lambda: datetime.now(timezone.utc))
   ```

3. **Import updates:**
   ```python
   # Before
   from datetime import datetime
   
   # After
   from datetime import datetime, timezone
   ```

---

## Validation

| Check | Result |
|-------|--------|
| py_compile (all 21 files) | ✅ PASS |
| Linter | ✅ No errors |
| `utcnow` grep (all files) | ✅ 0 remaining |

---

## Remaining Work

~67 more `datetime.utcnow()` occurrences in `core/` across ~20 files. Recommended next batches:

- `core/schemas/ws_event_stream.py` (3)
- `core/packet_envelope/standardization.py` (3)
- `core/compliance/audit_reporter.py` (3)
- `core/tools/registry_cache.py` (2)
- `core/governance/schemas.py` (2)

**Protected file requiring KERNEL-tier GMP:**
- `core/agents/executor.py` (3 occurrences)

---

## Next Step

`/ynp` — Recommend continuing with remaining batches or commit current work.
