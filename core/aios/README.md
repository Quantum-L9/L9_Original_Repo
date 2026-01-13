# core/aios/ — L9 LLM Runtime

**This is the ONLY `aios` location in L9.**

## What's Here

| File | Purpose |
|------|---------|
| `runtime.py` | `AIOSRuntime` class — calls OpenAI with context and tools |
| `__init__.py` | Package exports |

## AIOSRuntime

The LLM reasoning engine used by `AgentExecutorService`:

```python
from core.aios.runtime import AIOSRuntime

runtime = AIOSRuntime()
result = await runtime.execute_reasoning(context)
# Returns: AIOSResult (response or tool_call)
```

## Architecture

```
Request → AgentExecutorService → AIOSRuntime → OpenAI
                ↓
         Memory Substrate
```

- **AIOSRuntime** handles LLM calls only
- **AgentExecutorService** handles tool dispatch, memory, governance
- All packets flow through memory substrate

## History

The orphaned `aios/` directory (VPS daemon) was deleted in GMP-61.  
That code bypassed governance and has been eliminated.

---

*Last updated: 2026-01-13*
