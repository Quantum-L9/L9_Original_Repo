# GMP-Report-126

**ID:** GMP-126
**Task:** Tool Embeddings Wiring Fix (Tool RAG)
**Tier:** RUNTIME_TIER
**Date:** 2026-01-28
**Time:** 22:17 EST
**Status:** ✅ COMPLETE

---

## SUMMARY

Fixed critical wiring failure in Tool RAG pipeline. Root cause: init_repository() was never called during API lifespan, making get_repository() singleton unavailable to tool_embeddings.py. Solution: Added init_repository(database_url) call after init_service() in api/server.py lifespan. Result: 116/116 tool embeddings synced, dynamic tool selection operational.

---

## ROOT CAUSE

The tool_embeddings.py module calls get_repository() which expects the module-level _repository singleton to be initialized. However, api/server.py only called init_service() which creates its own internal repository instance but does NOT set the module-level _repository variable.

---

## PLAN

| ID | File | Lines | Action | Status |
|----|------|-------|--------|--------|
| T1 | `core/tools/tool_embeddings.py` | L15-30 | REPLACE | ✅ |
| T2 | `api/server.py` | L85-95 | INSERT | ✅ |

**Hash:** `2 TODOs | server.py, tool_embeddings.py`

---

## CHANGES

| File | Lines | Action | Description |
|------|-------|--------|-------------|
| `core/tools/tool_embeddings.py` | L15-30 | REPLACE | Changed from get_pool (nonexistent) to get_repository() singleton |
| `api/server.py` | L85-95 | INSERT | Added init_repository(database_url) after init_service() in lifespan |

---

## TODO → CHANGE MAP

| TODO | File | Change |
|------|------|--------|
| T1 | tool_embeddings.py | Changed from get_pool (nonexistent) to get_repository() singleton |
| T2 | server.py | Added init_repository(database_url) after init_service() in lifespan |

---

## VALIDATION

| Gate | Result |
|------|--------|
| py_compile | ✅ |
| import test | ✅ |
| tool embeddings sync | ✅ 116/116 synced |
| health check | ✅ API healthy |

---

## DECLARATION

Phases 0-6 complete. No assumptions. No drift.
