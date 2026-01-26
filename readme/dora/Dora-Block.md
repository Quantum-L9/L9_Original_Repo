# L9 DORA BLOCK (L9_TRACE_TEMPLATE)

**Purpose:** Machine-readable runtime trace — auto-updates on every execution.

**Location:** VERY END OF FILE — after Header Meta, after Footer Meta, after all code.

**Updates:** 100% machine-updated on every execution — NEVER touched by humans.

---

## 🔒 LOCKED TERMINOLOGY — THREE DISTINCT BLOCKS

| Block | Location | Purpose | Updates |
|-------|----------|---------|---------|
| **Header Meta** | TOP of file | Module identity, governance | On generation |
| **Footer Meta** | BOTTOM of file | Extended metadata (header points here) | On generation |
| **DORA Block** | VERY END (after Footer Meta) | Runtime execution trace | Auto on EVERY run |

### CRITICAL DEFINITIONS

- **DORA Block** = L9_TRACE_TEMPLATE ONLY — runtime trace, auto-updates
- **Header Meta** ≠ DORA Block — static module identity at top
- **Footer Meta** ≠ DORA Block — extended metadata, header tells AI to look here

---

## FILE STRUCTURE

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER META (TOP)                                          │
│  - Module identity, governance, static                      │
│  - Points to Footer Meta: "See footer for extended meta"    │
├─────────────────────────────────────────────────────────────┤
│  [... ALL MODULE CODE ...]                                  │
├─────────────────────────────────────────────────────────────┤
│  FOOTER META (BOTTOM, before DORA Block)                    │
│  - Extended metadata that header references                 │
│  - Static, set on generation                                │
├─────────────────────────────────────────────────────────────┤
│  DORA BLOCK (VERY END)                                      │
│  - L9_TRACE_TEMPLATE                                        │
│  - 100% machine-managed, auto-updates                       │
│  - Never human-edited                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## L9_TRACE_TEMPLATE (The DORA Block Schema)

```json
{
  "trace_id": "",
  "task": "",
  "timestamp": "",
  "patterns_used": [],
  "graph": {
    "nodes": [],
    "edges": []
  },
  "inputs": {},
  "outputs": {},
  "metrics": {
    "confidence": "",
    "errors_detected": [],
    "stability_score": ""
  }
}
```

---

## Format by File Type

### Python (.py)
```python
# [... all module code ...]
# [... footer meta ...]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
__l9_trace__ = {
    "trace_id": "abc123",
    "task": "expression_evaluation",
    "timestamp": "2026-01-02T02:30:00Z",
    "patterns_used": ["symbolic_eval", "safety_check"],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {
        "confidence": "0.95",
        "errors_detected": [],
        "stability_score": "1.0"
    }
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
```

### YAML (.yaml, .yml)
```yaml
# [... all YAML content ...]
# [... footer meta ...]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
l9_trace:
  trace_id: "abc123"
  task: "config_load"
  timestamp: "2026-01-02T02:30:00Z"
  patterns_used: []
  graph:
    nodes: []
    edges: []
  inputs: {}
  outputs: {}
  metrics:
    confidence: ""
    errors_detected: []
    stability_score: ""
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
```

### JSON (.json)
```json
{
  "actual_content": {},
  "footer_meta": {},
  
  "_l9_trace": {
    "trace_id": "abc123",
    "task": "data_processing",
    "timestamp": "2026-01-02T02:30:00Z",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {
      "confidence": "",
      "errors_detected": [],
      "stability_score": ""
    }
  }
}
```

---

## Enforcement Rules

1. **DORA Block = VERY LAST thing** — After footer meta, after all code
2. **100% MACHINE-MANAGED** — Never edited by humans
3. **AUTO-UPDATES ON EVERY RUN** — Runtime hook updates after each execution
4. **PARSEABLE** — CI/observability systems can extract and analyze

---

## Integration with Codegen

The codegen system must:
1. **Inject Header Meta** at TOP (points to Footer Meta)
2. **Inject Footer Meta** at BOTTOM (extended metadata)
3. **Inject empty DORA Block** at VERY END (after Footer Meta)
4. **Runtime hook updates** DORA Block after each execution
5. **CI validates** presence of all three blocks

---

## Implementation Status

### ✅ IMPLEMENTED

| Component | Location | Description |
|-----------|----------|-------------|
| `@l9_traced` decorator | `runtime/dora.py` | Wraps functions to capture execution traces |
| `DoraTraceBlock` dataclass | `runtime/dora.py` | Data model for L9_TRACE_TEMPLATE |
| `update_dora_block_in_file()` | `runtime/dora.py` | Writes trace data to file footer |
| `emit_executor_trace()` | `runtime/dora.py` | Hook for AgentExecutorService |
| Executor integration | `core/agents/executor.py` | Calls `emit_executor_trace()` after task completion |
| Template with DORA Block | `codegen/templates/python-dora-template.py` | Module template with all three blocks |
| Template with DORA Block | `codegen/templates/python-l9-module-template.py` | Full module template |

### How Auto-Update Works

1. **Decorator pattern**: Functions decorated with `@l9_traced` auto-capture:
   - Inputs (function arguments)
   - Outputs (return value)
   - Duration (execution time in ms)
   - Errors (if any exception raised)
   - Patterns used (optional, specified in decorator)

2. **Executor hook**: `AgentExecutorService` calls `emit_executor_trace()` after every task:
   ```python
   await emit_executor_trace(
       task_id=task_id_str,
       task_name=task.name or "agent_task",
       agent_id=task.agent_id,
       inputs={...},
       outputs={...},
       duration_ms=result.duration_ms,
       errors=[result.error] if result.error else None,
   )
   ```

3. **File update (optional)**: When `update_source=True`, the decorator writes to the source file:
   ```python
   @l9_traced(patterns=["safety_check"], update_source=True)
   def my_function(...):
       ...
   ```

### Usage Example

```python
from runtime.dora import l9_traced

@l9_traced(patterns=["symbolic_eval", "safety_check"])
async def process_expression(expr: str) -> dict:
    \"\"\"Process a symbolic expression.\"\"\"
    result = evaluate(expr)
    return {"result": result}
```

---

**Status:** ACTIVE  
**Created:** 2026-01-02  
**Updated:** 2026-01-02  
**Implemented:** 2026-01-02  
**Location:** `codegen/sympy/phase 4/Dora-Block.md`
