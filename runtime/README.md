# Runtime Module

**Path:** `runtime/`  
**Purpose:** Task execution, kernel loading, and runtime infrastructure  
**Files:** 28 Python files  
**Last Updated:** 2026-01-18

---

## Overview

The `runtime` module provides the execution environment for the L9 platform, including kernel loading, task queuing, and background task management.

## Key Components

- **`kernel_loader_ultimate.py`** - **ONLY** kernel loader (with integrity checks)
- **`task_queue.py`** - Async task queue with priority support
- **`background_tasks.py`** - Background task management
- **`execution_gate.py`** - Kernel governance gate for execution
- **`tool_registry.py`** - Tool discovery and registration
- **`mcp_server_registry.py`** - MCP server management

## Critical Rules

⚠️ **NEVER use `kernel_loader.py` - ONLY use `kernel_loader_ultimate.py`**

The ultimate loader has:
- Integrity verification
- Tamper detection
- Fail-closed behavior
- Audit logging

## Usage

### Loading the Kernel

```python
from runtime.kernel_loader_ultimate import load_kernel

kernel = await load_kernel()
```

### Task Queue

```python
from runtime.task_queue import TaskQueue

queue = TaskQueue()
await queue.enqueue(task, priority=1)
result = await queue.process()
```

### Tool Registry

```python
from runtime.tool_registry import ToolRegistry

# Register a tool
ToolRegistry.register("my_tool", MyTool)

# Get a tool
tool = ToolRegistry.get("my_tool")
```

## Architecture

**Runtime Lifecycle:**
1. Kernel loading and verification
2. Registry initialization
3. Task queue startup
4. Background task scheduling
5. Execution gate activation

## Testing

```bash
pytest tests/runtime/
pytest tests/runtime/test_fail_closed_task_queue.py
```

## Related Modules

- **`core/`** - Core infrastructure
- **`agents/`** - Agent implementations
- **`orchestration/`** - Workflow orchestration

---

**Status:** Production  
**Maintainer:** L-CTO Agent  
**Security:** CRITICAL (kernel loading)
