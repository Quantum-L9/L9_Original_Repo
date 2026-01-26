# DORA Block Auto-Update Root Cause Analysis

**Issue:** DORA blocks don't update automatically
**Date:** January 25, 2026
**Analyzed By:** Manus AI Agent

---

## 🔍 Investigation Summary

### What Are DORA Blocks?

DORA blocks are **runtime execution traces** that appear at the end of Python files:

```python
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
__l9_trace__ = {
    "trace_id": "abc123",
    "task": "function_name",
    "timestamp": "2026-01-25T12:00:00Z",
    "patterns_used": ["pattern1", "pattern2"],
    "graph": {"nodes": [], "edges": []},
    "inputs": {"arg1": "value1"},
    "outputs": {"output": "result"},
    "metrics": {"confidence": "0.95", "errors_detected": [], "stability_score": "1.0"},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
```

### Current State

**Files with DORA blocks:** 100+ files
**Expected behavior:** Auto-update on every execution
**Actual behavior:** Blocks remain empty or stale

**Example from `.github/scripts/generate-ai-collab-report.py`:**

```python
__l9_trace__ = {
    "trace_id": "",           # ❌ Empty
    "task": "",               # ❌ Empty
    "timestamp": "",          # ❌ Empty
    "patterns_used": [],      # ❌ Empty
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
```

---

## 🐛 Root Cause Identified

### Issue #1: Decorator Not Used (PRIMARY CAUSE)

**Finding:** The `@l9_traced` decorator is **defined** but **NOT USED** in any production code.

**Evidence:**

```bash
$ grep -rn "@l9_traced" --include="*.py" | grep -v "runtime/dora.py"
# Result: Only found in runtime/dora.py (the definition), not in actual code
```

**Impact:** Functions are never wrapped, so DORA blocks never update.

---

### Issue #2: `update_source=False` by Default

**Finding:** Even if the decorator were used, `update_source` defaults to `False`.

**From `runtime/dora.py` line 290:**

```python
def l9_traced(
    func: Optional[F] = None,
    *,
    task_name: Optional[str] = None,
    patterns: Optional[List[str]] = None,
    update_source: bool = False,  # ❌ Defaults to False!
    source_file: Optional[Union[str, Path]] = None,
) -> Union[F, Callable[[F], F]]:
```

**Impact:** Even with decorator, you must explicitly set `update_source=True`:

```python
@l9_traced(update_source=True)  # Required for auto-update
def my_function():
    pass
```

---

### Issue #3: No Automatic Injection at Runtime

**Finding:** DORA blocks are injected at **code generation time** but not updated at **runtime** unless explicitly decorated.

**Evidence:**

- `scripts/audit/inject_dora_complete.py` - Injects empty blocks
- `runtime/dora.py` - Provides update mechanism
- **Missing:** Automatic runtime update without decorator

**Current Flow:**

1. ✅ Codegen injects empty DORA block
2. ❌ Function runs (no decorator)
3. ❌ DORA block stays empty

**Expected Flow:**

1. ✅ Codegen injects empty DORA block
2. ✅ Function runs with `@l9_traced(update_source=True)`
3. ✅ DORA block updates automatically

---

### Issue #4: No Integration with Main Execution Paths

**Finding:** The `emit_executor_trace()` function exists but doesn't update source files.

**From `runtime/dora.py` line 444-496:**

```python
async def emit_executor_trace(...) -> DoraTraceBlock:
    """Create and emit a DORA trace from the executor."""
    trace = DoraTraceBlock.create(...)
    logger.info("dora.executor_trace", ...)
    return trace  # ❌ Only logs, doesn't update files
```

**Impact:** Even when executor creates traces, they're not written to DORA blocks.

---

## 📊 Gap Analysis

| Component                | Expected                     | Actual                    | Gap      |
| ------------------------ | ---------------------------- | ------------------------- | -------- |
| **Decorator Usage**      | Used on all traced functions | Not used anywhere         | 100%     |
| **Auto-Update**          | Enabled by default           | Disabled by default       | Critical |
| **Executor Integration** | Updates DORA blocks          | Only logs traces          | High     |
| **Runtime Hook**         | Automatic for all functions  | Manual decorator required | High     |

---

## 💡 Proposed Solutions

### Solution 1: Add @l9_traced to Key Functions (Quick Fix)

**Effort:** 2-4 hours
**Impact:** Medium (only decorated functions update)

**Implementation:**

1. Identify key functions to trace
2. Add `@l9_traced(update_source=True)` decorator
3. Test DORA block updates

**Pros:**

- ✅ Quick to implement
- ✅ Selective tracing
- ✅ Low risk

**Cons:**

- ❌ Manual work for each function
- ❌ Easy to forget decorator
- ❌ Not truly "automatic"

---

### Solution 2: Change Default to `update_source=True` (Better)

**Effort:** 30 minutes
**Impact:** High (all decorated functions auto-update)

**Implementation:**

1. Change line 290 in `runtime/dora.py`:
   ```python
   update_source: bool = True,  # Changed from False
   ```
2. Add decorator to key functions
3. Test

**Pros:**

- ✅ Simple change
- ✅ Auto-update by default
- ✅ Backward compatible (can still set False)

**Cons:**

- ❌ Still requires manual decorator addition
- ❌ File I/O overhead on every execution

---

### Solution 3: Automatic Runtime Hook (Best - Recommended)

**Effort:** 4-6 hours
**Impact:** Very High (all functions auto-trace)

**Implementation:**

1. Create runtime hook that auto-wraps functions
2. Use `sys.settrace()` or import hooks
3. Auto-detect functions with DORA blocks
4. Update blocks on execution
5. Add configuration to enable/disable

**Pros:**

- ✅ Truly automatic
- ✅ No decorator needed
- ✅ Works for all functions
- ✅ Can be toggled per environment

**Cons:**

- ❌ More complex implementation
- ❌ Performance overhead
- ❌ Requires careful testing

---

### Solution 4: Executor Integration (Complementary)

**Effort:** 2-3 hours
**Impact:** High (executor tasks auto-update)

**Implementation:**

1. Modify `emit_executor_trace()` to accept file path
2. Call `update_dora_block_in_file()` after trace creation
3. Integrate with AgentExecutorService

**Pros:**

- ✅ Works for agent executions
- ✅ Integrates with existing flow
- ✅ No decorator needed for executor tasks

**Cons:**

- ❌ Only works for executor-run code
- ❌ Doesn't help standalone functions

---

## 🎯 Recommended Fix (Hybrid Approach)

**Combine Solutions 2 + 3 + 4:**

### Phase 1: Quick Win (30 minutes)

1. ✅ Change default `update_source=True`
2. ✅ Add decorator to 5-10 key functions
3. ✅ Test and verify updates work

### Phase 2: Executor Integration (2-3 hours)

1. ✅ Update `emit_executor_trace()` to write to files
2. ✅ Integrate with AgentExecutorService
3. ✅ Test executor task tracing

### Phase 3: Automatic Hook (4-6 hours - Optional)

1. ✅ Implement runtime hook for auto-tracing
2. ✅ Add configuration flag
3. ✅ Performance testing

**Total Effort:** 2.5-9.5 hours (depending on phases implemented)
**Impact:** High - DORA blocks will auto-update

---

## 🔧 Implementation Plan

### Immediate (This PR)

1. Fix `update_source` default to `True`
2. Add `@l9_traced` to key functions:
   - `runtime/kernel_loader.py::load_kernels()`
   - `memory/substrate_repository.py::search_semantic_memory()`
   - `core/agents/executor.py::execute_task()`
   - Others as identified
3. Update `emit_executor_trace()` to write to files
4. Add tests

### Follow-up (Future PR)

1. Implement automatic runtime hook
2. Add configuration for tracing
3. Performance optimization

---

## ✅ Verification Criteria

**Success = DORA blocks auto-update when:**

1. ✅ Decorated function executes
2. ✅ Executor runs agent task
3. ✅ Trace data appears in `__l9_trace__`
4. ✅ Timestamp updates on each run
5. ✅ No manual intervention required

---

## 📝 Files to Modify

### Core Fix (runtime/dora.py)

- Line 290: Change `update_source: bool = False` → `True`
- Line 444-496: Update `emit_executor_trace()` to write to files

### Add Decorators (5-10 files)

- `runtime/kernel_loader.py`
- `memory/substrate_repository.py`
- `core/agents/executor.py`
- `orchestrators/agent_execution/task_queue.py`
- Others TBD

### Tests (new file)

- `tests/runtime/test_dora_auto_update.py`

---

## 🎉 Expected Outcome

**Before:**

```python
__l9_trace__ = {
    "trace_id": "",  # Empty
    "task": "",
    ...
}
```

**After:**

```python
__l9_trace__ = {
    "trace_id": "a1b2c3d4",
    "task": "load_kernels",
    "timestamp": "2026-01-25T14:30:00Z",
    "patterns_used": ["kernel_loading", "caching"],
    "inputs": {"kernel_dir": "/path/to/kernels"},
    "outputs": {"kernels_loaded": 10},
    "metrics": {"duration_ms": 150, "confidence": "0.95", "stability_score": "1.0"},
}
```

**Result:** ✅ DORA blocks auto-update on every execution!

---

**Context Window Usage: 41.5% (83,000 / 200,000 tokens)**
