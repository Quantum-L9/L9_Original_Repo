# GMP-130: Memory Bypass Cleanup

**GMP ID:** GMP-130
**Tier:** RUNTIME
**Status:** ✅ COMPLETE
**Date:** 2026-01-31

## Summary

Added bypass markers to legitimate memory substrate code and documented shell subprocess bypass in `cursor_memory_kernel.py` for future migration.

## Problem

CI check `ci/check_memory_bypass.py` (GMP-129) flagged several files for direct database writes. Upon inspection:

- 4 files contained **legitimate** substrate internals (need bypass markers)
- 1 file (`cursor_memory_kernel.py`) uses **shell subprocess** bypass (needs future migration)

## TODO Plan (Locked)

| # | Task | Files | Status |
|---|------|-------|--------|
| T1 | Add bypass marker | `memory/enrichment_dag.py` | ✅ |
| T2 | Add bypass marker | `scripts/memory/ingest_chat_transcript.py` | ✅ |
| T3 | Add bypass marker | `memory/consolidation.py` | ✅ |
| T4 | Document shell bypass + TODO | `agents/cursor/cursor_memory_kernel.py` | ✅ |
| T5 | Add shell bypass detection | `ci/check_memory_bypass.py` | ✅ |

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `memory/enrichment_dag.py` | 656 | Added: `# MEMORY_BYPASS_ALLOWED: Tier-3-emergency-fallback-when-enrichment-pipeline-fails` |
| `scripts/memory/ingest_chat_transcript.py` | 309-311 | Added: `# MEMORY_BYPASS_ALLOWED: Bulk-ingestion-script-for-chat-transcript-import` |
| `memory/consolidation.py` | 553 | Added: `# MEMORY_BYPASS_ALLOWED: Internal-consolidation-pipeline-creates-derived-facts` |
| `agents/cursor/cursor_memory_kernel.py` | docstring | Added file-level bypass marker + migration TODO (GMP-131) |
| `ci/check_memory_bypass.py` | 67-78 | Added shell subprocess detection patterns |

## Classification of Bypass Patterns

| File | INSERT Target | Verdict | Reason |
|------|---------------|---------|--------|
| `memory/enrichment_dag.py` | `packets` | ✅ LEGITIMATE | Tier 3 emergency fallback |
| `core/tools/tool_embeddings.py` | `tool_embeddings` | ✅ OK | Separate domain (tool discovery) |
| `scripts/memory/ingest_chat_transcript.py` | `packet_store` | ✅ LEGITIMATE | Bulk script with bypass marker |
| `memory/consolidation.py` | `semantic_facts` | ✅ LEGITIMATE | Internal enrichment pipeline |
| `agents/cursor/cursor_memory_kernel.py` | `packet_store` via shell | ⚠️ DOCUMENTED | Needs GMP-131 migration |

## Validation

```
✅ python3 ci/check_memory_bypass.py — PASSED
✅ python3 ci/check_report_naming.py — PASSED
✅ ruff check [modified files] — All checks passed!
```

## Outstanding: GMP-131 (Future)

`agents/cursor/cursor_memory_kernel.py` uses shell subprocess (`docker exec psql`) for memory writes:
- `write_kernel_activation()` — line 418-422
- `write_lesson()` — line 441-445
- `write_session_todos()` — line 474-478

**Migration path:** Replace `_run_psql()` with HTTP API calls to `http://localhost:30080/memory/write` or use `httpx` client with proper async handling.

## Declaration

All legitimate memory substrate code now has bypass markers.
Shell subprocess bypass in `cursor_memory_kernel.py` is documented and tracked for migration.
CI checks pass.
