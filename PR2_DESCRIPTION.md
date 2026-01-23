# PR #2: Observability Infrastructure - Tracing & Instrumentation

## 🎯 Overview

This PR implements **Phase 0 Plans 2, 5, and 10** from the L9 refactoring initiative, establishing comprehensive observability infrastructure for distributed tracing and instrumentation.

**Branch:** `refactor/pr2-observability-tracing`  
**Risk Tier:** T2 (Additive, low-impact changes)  
**Depends On:** PR #1 (Foundation)  
**Related:** Phase 0 TODO Plan (PLANS 2, 5, 10)

---

## 📋 Changes Summary

### PLAN 2: PacketEnvelope Metadata Enrichment

**Modified File:** `core/schemas/packet_envelope_v2.py` (+15 lines)

Added three new **optional** tracing fields to `PacketEnvelope`:

1. **`trace_id: Optional[str]`**
   - Distributed trace ID (UUID format)
   - OpenTelemetry compatible
   - Enables request chain tracing across services

2. **`correlation_id: Optional[str]`**
   - Groups related packets in same task/batch
   - Enables correlation analysis
   - Defaults to trace_id if not specified

3. **`source_location: Optional[dict[str, Any]]`**
   - Source code location where packet was created
   - Format: `{file: str, line: int, function: str}`
   - Enables debugging and audit trails

**Benefits:**
- ✅ OpenTelemetry-compatible distributed tracing
- ✅ Backward compatible (all fields optional)
- ✅ No breaking changes to existing code
- ✅ Enables correlation analysis across packets

### PLAN 5: WebSocket Tracing Middleware

**New File:** `api/middleware/websocket_tracing.py` (~330 lines)

ASGI middleware for automatic trace context injection into WebSocket connections.

**Key Components:**
- `TraceContext` dataclass - Container for trace/correlation/connection IDs
- `WebSocketTracingMiddleware` - ASGI middleware for trace injection
- `get_trace_context()` - Helper to extract trace context from WebSocket
- `inject_trace_into_packet()` - Helper to inject trace context into packets

**Features:**
- Extracts trace_id from query params (`?trace_id=...`)
- Extracts trace_id from headers (`X-Trace-Id`)
- Generates new trace_id if not provided
- Logs WebSocket lifecycle events (connect, disconnect, messages)
- Propagates trace context to all packets sent through WebSocket

**Benefits:**
- ✅ Automatic trace context injection (no manual wiring)
- ✅ Structured logging for WebSocket events
- ✅ OpenTelemetry-compatible trace propagation
- ✅ Query param and header support for flexibility

### PLAN 10: Auto-Instrumentation Decorators

**New File:** `core/instrumentation/decorators.py` (~550 lines)

Decorators for automatic tracing, timing, and logging.

**Decorators:**

1. **`@traced`** - Automatic trace_id propagation
   - Injects trace_id into function context
   - Supports sync and async functions
   - Logs entry/exit with trace context
   - Handles exceptions with trace logging

2. **`@timed`** - Execution time tracking
   - Logs function execution duration
   - Optional threshold filtering (`log_threshold_ms`)
   - Supports sync and async functions
   - Includes trace_id in logs

3. **`@logged`** - Automatic structured logging
   - Logs function entry/exit
   - Optional argument logging (`log_args=True`)
   - Optional result logging (`log_result=True`)
   - Configurable log level

4. **`@with_source_location`** - Source code location capture
   - Captures file, line, function from call stack
   - Injects into function kwargs if parameter exists
   - Useful for audit trails

**Context Management:**
- `get_current_trace_id()` - Get trace_id from context
- `set_trace_id()` - Set trace_id in context
- `get_current_correlation_id()` - Get correlation_id from context
- `set_correlation_id()` - Set correlation_id in context
- `capture_source_location()` - Capture source location from stack

**Benefits:**
- ✅ Zero-boilerplate tracing (just add decorator)
- ✅ Context variable propagation (async-safe)
- ✅ Composable decorators (stack multiple)
- ✅ Performance-aware (threshold filtering)

---

## 🧪 Testing

### Unit Tests

**New Files:**
- `tests/unit/test_websocket_tracing.py` (21 tests)
- `tests/unit/test_instrumentation_decorators.py` (31 tests)

**Total:** 52 unit tests, all passing ✅

**Test Coverage:**
- TraceContext creation and export
- WebSocket middleware trace extraction (query params, headers)
- Trace context injection into packets
- @traced decorator (sync/async, propagation, exceptions)
- @timed decorator (threshold filtering, exceptions)
- @logged decorator (args, results, levels)
- @with_source_location decorator
- Context variable propagation
- Source location capture
- Mutation testing targets

### Test Results

```bash
$ pytest tests/unit/test_websocket_tracing.py tests/unit/test_instrumentation_decorators.py -v
============================= test session starts ==============================
tests/unit/test_websocket_tracing.py::TestTraceContext::test_trace_context_with_all_params PASSED
tests/unit/test_websocket_tracing.py::TestTraceContext::test_trace_context_with_defaults PASSED
[... 50 more tests ...]
============================== 52 passed in 0.39s ===============================
```

---

## 🔧 Integration Points

### Usage Examples

#### 1. WebSocket Tracing Middleware

```python
# api/server.py
from fastapi import FastAPI
from api.middleware.websocket_tracing import WebSocketTracingMiddleware

app = FastAPI()
app.add_middleware(WebSocketTracingMiddleware)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Get trace context
    from api.middleware.websocket_tracing import get_trace_context
    trace_ctx = get_trace_context(websocket)
    
    logger.info("processing", trace_id=trace_ctx.trace_id)
```

#### 2. Auto-Instrumentation Decorators

```python
from core.instrumentation.decorators import traced, timed, logged

@traced  # Automatic trace_id propagation
@timed   # Log execution time
async def process_task(task_id: str):
    logger.info("processing", task_id=task_id)
    # trace_id automatically available in logs
    return await heavy_computation()

@timed(log_threshold_ms=100)  # Only log if > 100ms
async def fast_operation():
    return await quick_db_query()

@logged(log_args=True, log_result=True)
def debug_function(arg1, arg2):
    return arg1 + arg2
```

#### 3. PacketEnvelope with Tracing

```python
from core.schemas import PacketEnvelope
from core.instrumentation.decorators import get_current_trace_id

@traced
async def create_event_packet(payload: dict):
    packet = PacketEnvelope(
        packet_type="event",
        payload=payload,
        trace_id=get_current_trace_id(),  # Inject trace_id
        correlation_id=get_current_correlation_id(),
        source_location=capture_source_location(),
    )
    return packet
```

---

## 📊 Code Quality

### Compliance

- ✅ **Python 3.9 Compatible** - Uses `Optional[X]` not `X | None`
- ✅ **Structlog Only** - No standard `logging` module
- ✅ **Type Hints** - Full type coverage
- ✅ **DORA Headers** - Metadata for observability
- ✅ **Docstrings** - Comprehensive documentation
- ✅ **Async-Safe** - Context variables for async propagation

### Formatting

```bash
$ black core/schemas/packet_envelope_v2.py api/middleware/websocket_tracing.py core/instrumentation/decorators.py
All done! ✨ 🍰 ✨
3 files left unchanged.

$ ruff check core/schemas/packet_envelope_v2.py api/middleware/websocket_tracing.py core/instrumentation/decorators.py
All checks passed!
```

---

## 🚀 Migration Path

### For Existing Code

No immediate changes required. This PR is **additive only**:
- PacketEnvelope fields are optional (backward compatible)
- Middleware is opt-in (add to FastAPI app)
- Decorators are opt-in (add to functions)

### For New Code

Recommended patterns:

```python
# 1. Add middleware to FastAPI app
app.add_middleware(WebSocketTracingMiddleware)

# 2. Use @traced decorator for automatic tracing
@traced
async def my_function():
    pass

# 3. Inject trace context into packets
packet = PacketEnvelope(
    packet_type="event",
    payload={...},
    trace_id=get_current_trace_id(),
)
```

---

## 📈 Benefits

### Immediate

1. **Distributed Tracing** - Trace requests across WebSocket connections
2. **Zero-Boilerplate Instrumentation** - Just add decorators
3. **Structured Logging** - Automatic trace context in logs
4. **Performance Monitoring** - Execution time tracking with thresholds
5. **Debugging Support** - Source location capture for audit trails

### Long-Term

1. **OpenTelemetry Integration** - Compatible trace format for future integration
2. **Correlation Analysis** - Group related packets for analysis
3. **Performance Optimization** - Identify slow operations with @timed
4. **Audit Trails** - Source location tracking for compliance
5. **Observability Foundation** - Enables future APM integrations

---

## 🔍 Reviewers' Guide

### Key Files to Review

1. **`core/schemas/packet_envelope_v2.py`** - Tracing fields addition
2. **`api/middleware/websocket_tracing.py`** - WebSocket middleware
3. **`core/instrumentation/decorators.py`** - Auto-instrumentation decorators
4. **`tests/unit/test_websocket_tracing.py`** - Test coverage
5. **`tests/unit/test_instrumentation_decorators.py`** - Test coverage

### Review Checklist

- [ ] PacketEnvelope tracing fields are optional (backward compatible)
- [ ] WebSocket middleware correctly extracts trace context
- [ ] Decorators support both sync and async functions
- [ ] Context variables propagate correctly in async code
- [ ] Tests cover boundary conditions and error cases
- [ ] Code follows L9 conventions (structlog, type hints, DORA headers)
- [ ] No breaking changes to existing code
- [ ] OpenTelemetry compatibility maintained

---

## 🎬 Next Steps

After this PR merges:

1. **Wire Middleware** - Add `WebSocketTracingMiddleware` to `api/server.py`
2. **Adopt Decorators** - Add `@traced` to key functions (executor, tools)
3. **Inject Trace Context** - Add trace_id to PacketEnvelope creation sites
4. **PR #3: Memory & Governance Enhancements** (PLANS 4, 6, 7, 8)
   - Governance policy enforcement
   - Deduplication in consolidation pipeline
   - Execution plan snapshots
   - Tool registry caching

---

## 📝 Notes

- **No Breaking Changes** - All changes are additive and optional
- **Backward Compatible** - Existing code continues to work
- **OpenTelemetry Ready** - Trace format compatible with OpenTelemetry
- **Async-Safe** - Context variables ensure async propagation
- **Performance-Aware** - Threshold filtering prevents log spam

---

## 🏷️ Labels

- `observability`
- `tracing`
- `instrumentation`
- `middleware`
- `phase-0`
- `t2-risk`

---

## 📚 References

- [Phase 0 TODO Plan](../current_work/01-20-2026/Refactor/⚙️PHASE0_TODOPLAN—REVISED(No_Factory_Term.md)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [Python Context Variables](https://docs.python.org/3/library/contextvars.html)
- [ASGI Middleware](https://asgi.readthedocs.io/en/latest/specs/main.html)

---

**Ready for Review** ✅
