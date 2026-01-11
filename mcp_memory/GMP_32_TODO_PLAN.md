# GMP-32: MCP Memory Server Audit Fixes - TODO PLAN (LOCKED)

**Date:** 2026-01-09  
**GMP ID:** GMP-32  
**Status:** LOCKED (Phase 0)

---

## TODO PLAN (LOCKED)

### Phase 1: Input Validation Models

- **[T1]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/models.py`
  - Lines: After line 153 (end of file)
  - Action: Insert
  - Target: `MCPToolArgumentModels` section
  - Change: Add Pydantic models for each MCP tool's arguments (SaveMemoryArgs, SearchMemoryArgs, etc.) matching inputSchema from get_mcp_tools()
  - Gate: py_compile, lint
  - Imports: `from pydantic import BaseModel, Field, validator` (if needed)

### Phase 2: Validation in Tool Dispatch

- **[T2]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/mcp_server.py`
  - Lines: 298-310 (handle_tool_call function start)
  - Action: Insert
  - Target: `handle_tool_call` function (after caller extraction)
  - Change: Add validation step that instantiates appropriate Pydantic model from tool.arguments, raises ValidationError if invalid
  - Gate: py_compile, lint
  - Imports: `from pydantic import ValidationError` (add to existing imports)

### Phase 3: Improve Error Handling - Memory Handlers

- **[T3]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory_unified.py`
  - Lines: 222-224 (bare Exception catch)
  - Action: Replace
  - Target: `save_memory_handler` exception handler
  - Change: Replace bare `except Exception` with specific exceptions (asyncpg.PostgresError, ValueError, HTTPException), preserve error context
  - Gate: py_compile, lint
  - Imports: `import asyncpg` (if not already imported)

- **[T4]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/routes/memory_unified.py`
  - Lines: Find other bare Exception catches (search for `except Exception`)
  - Action: Replace
  - Target: All bare exception handlers
  - Change: Replace with specific exceptions, preserve error context
  - Gate: py_compile, lint
  - Imports: NONE (use existing imports)

### Phase 4: Improve Error Handling - Main App

- **[T5]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/main.py`
  - Lines: 214-217 (general exception handler)
  - Action: Replace
  - Target: `general_exception_handler`
  - Change: Add specific exception handlers for HTTPException, ValidationError, asyncpg.PostgresError before generic handler
  - Gate: py_compile, lint
  - Imports: `from fastapi import HTTPException`, `from pydantic import ValidationError`, `import asyncpg`

### Phase 5: Architectural Decision Documentation

- **[T6]** File: `/Users/ib-mac/Projects/L9/mcp_memory/docs/ARCHITECTURE_DECISION_INGESTION.md`
  - Lines: New file
  - Action: Insert
  - Target: New file creation
  - Change: Document decision on MCP server integration with memory.ingestion.ingest_packet() - explain why MCP bypasses canonical entrypoint (external service design)
  - Gate: None (documentation)
  - Imports: NONE

### Phase 6: E2E Test Suite

- **[T7]** File: `/Users/ib-mac/Projects/L9/mcp_memory/tests/test_e2e.py`
  - Lines: New file
  - Action: Insert
  - Target: New file creation
  - Change: Create E2E test suite with 5 tests: Save Memory E2E, Search Memory E2E, Governance Enforcement E2E, Fail-Fast Validation E2E, Error Handling E2E
  - Gate: pytest (run tests)
  - Imports: `import pytest`, `from unittest.mock import AsyncMock, patch`, `from fastapi.testclient import TestClient`, `from src.main import app`

---

## TODO INDEX HASH

```
T1: models.py validation models
T2: mcp_server.py validation step
T3: memory_unified.py save_memory_handler error handling
T4: memory_unified.py other error handlers
T5: main.py exception handlers
T6: docs/ARCHITECTURE_DECISION_INGESTION.md
T7: tests/test_e2e.py E2E suite
```

**Total TODOs:** 7  
**Files to modify:** 4  
**Files to create:** 2

---

## PHASE EXECUTION ORDER

1. **Phase 1:** T1 (validation models)
2. **Phase 2:** T2 (validation in dispatch)
3. **Phase 3:** T3, T4 (error handling in handlers)
4. **Phase 4:** T5 (error handling in main)
5. **Phase 5:** T6 (architectural documentation)
6. **Phase 6:** T7 (E2E tests)

---

**Status:** LOCKED - Ready for Phase 1 execution

