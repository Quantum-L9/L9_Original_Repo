# L9 Tools

## Overview

**L9 Tools** is the protocol and client layer for external tool communications. This folder contains utilities for Cursor IDE integration and Mac agent reverse-tunnel protocols.

> **Note:** This is NOT the main tool registry. The L9 tool system spans multiple directories:
> - `core/tools/` — Tool graph, registry adapter, capability enforcement
> - `runtime/l_tools.py` — Tool executor implementations  
> - `services/research/tools/` — Base tool registry and wrappers
> - `api/tools/` — HTTP API routes for tool execution

---

## Directory Contents

| File | Purpose | Status |
|------|---------|--------|
| ~~`cursor_client.py`~~ | ~~HTTP client for Cursor remote API~~ | ✅ **Moved to `agents/cursor/`** |
| `mac_protocol.py` | JSON schema for Mac agent tunnel | ✅ Active |
| `export_repo_indexes.py` | Repo indexing utility | 🟡 Legacy |
| `TOOL_LOADING_DIAGRAM.md` | Architecture diagram | ✅ Active |

---

## Architecture

See [`TOOL_LOADING_DIAGRAM.md`](./TOOL_LOADING_DIAGRAM.md) for complete tool loading flow.

### Quick Reference

```
Tool Request Flow:
  AgentExecutorService
    → TOOL_EXECUTORS (runtime/l_tools.py)
    → Capability check (core/schemas/capabilities.py)
    → Approval check (if high-risk)
    → Execute & log packet
```

---

## Mac Protocol

The Mac agent uses a JSON-only protocol for reverse tunnel communications:

### MacMessage (Request)

```python
from tools.mac_protocol import MacMessage

msg = MacMessage(
    token="auth_token",
    cmd="ls",
    args=["-la"],
    cwd="/opt/l9",
    timeout=30
)
```

### MacResponse

```python
from tools.mac_protocol import create_mac_response

response = create_mac_response(
    success=True,
    output="file1.txt\nfile2.txt\n",
    error="",
    exit_code=0
)
```

---

## Cursor Client (Legacy)

> ⚠️ **Deprecated:** The CursorClient was designed for a remote Cursor API that is not currently active.

```python
from agents.cursor.cursor_client import CursorClient

client = CursorClient(host="127.0.0.1", port=3000)
result = client.send_code("print('hello')")
```

---

## Tool System Overview

### L's Authorized Tools

L (the L9 CTO agent) has access to these tools via `DEFAULT_L_CAPABILITIES`:

| Tool | Category | Risk Level | Approval Required |
|------|----------|------------|-------------------|
| `memory_search` | Memory | Low | No |
| `memory_write` | Memory | Medium | No |
| `memory_read` | Memory | Low | No |
| `world_model_query` | Knowledge | Low | No |
| `kernel_read` | Knowledge | Low | No |
| `mcp_call_tool` | Integration | Medium | No |
| `long_plan.execute` | Orchestration | Medium | No |
| `long_plan.simulate` | Orchestration | Low | No |
| `symbolic_compute` | Computation | Low | No |
| `symbolic_codegen` | Computation | Low | No |
| `gmp_run` | Governance | **High** | ✅ Yes |
| `git_commit` | VCS | **High** | ✅ Yes |
| `mac_agent_exec_task` | Execution | **High** | ✅ Yes |

### Default Research Tools

These are registered at startup via `get_tool_registry()`:

| Tool | Description | Rate Limit |
|------|-------------|------------|
| `perplexity_search` | AI search via Perplexity | 20/min |
| `http_request` | External HTTP requests | 100/min |
| `mock_search` | Testing mock | 1000/min |
| `calculate` | Math expressions | 1000/min |

---

## Related Files

| Location | Purpose |
|----------|---------|
| `core/tools/tool_graph.py` | Neo4j tool dependency graph, ToolDefinition |
| `core/tools/registry_adapter.py` | ExecutorToolRegistry, register_l_tools() |
| `core/schemas/capabilities.py` | ToolName enum, Capability, AgentCapabilities |
| `runtime/l_tools.py` | TOOL_EXECUTORS dict, tool implementations |
| `services/research/tools/tool_registry.py` | Base ToolRegistry singleton |
| `services/research/tools/tool_wrappers.py` | PerplexityTool, HTTPTool, MockSearchTool |
| `api/tools/router.py` | POST /tools/execute endpoint |
| `orchestrators/action_tool/orchestrator.py` | ActionToolOrchestrator |
| `ci/check_tool_wiring.py` | CI gate for tool consistency |

---

## Orphaned/Legacy Files

The following files in this directory are **orphaned** (not actively wired into L9):

| File | Reason | Action |
|------|--------|--------|
| ~~`cursor_client.py`~~ | ~~Cursor remote API not active~~ | ✅ **Moved to `agents/cursor/`** |
| `export_repo_indexes.py` | One-time utility script | Can be moved to scripts/ |

---

## CI Enforcement

Tool wiring is validated by `ci/check_tool_wiring.py`:

```bash
python ci/check_tool_wiring.py
```

Checks:
1. All TOOL_EXECUTORS have ToolName enum entries
2. All TOOL_EXECUTORS have L capability entries
3. High-risk tools have `scope="requires_igor_approval"`
4. ToolDefinitions match TOOL_EXECUTORS
5. l_tools.py ↔ register_l_tools() consistency

---

## Adding New Tools

### 1. Define the tool enum

```python
# core/schemas/capabilities.py
class ToolName(str, Enum):
    MY_NEW_TOOL = "my_new_tool"
```

### 2. Add capability for L

```python
# core/schemas/capabilities.py
DEFAULT_L_CAPABILITIES = AgentCapabilities(
    capabilities=[
        # ... existing ...
        Capability(tool=ToolName.MY_NEW_TOOL, allowed=True),
    ]
)
```

### 3. Implement the executor

```python
# runtime/l_tools.py
async def my_new_tool(arg1: str, **kwargs) -> dict:
    """Implementation here."""
    return {"result": arg1}

TOOL_EXECUTORS["my_new_tool"] = my_new_tool
```

### 4. Register with metadata

```python
# core/tools/registry_adapter.py (in register_l_tools)
tools_to_register.append(
    ToolDefinition(
        name="my_new_tool",
        description="Does something useful",
        category="custom",
        scope="internal",
        risk_level="low",
        agent_id="L",
    )
)
```

### 5. Run CI check

```bash
python ci/check_tool_wiring.py
```

---

## Security Model

- **Capability sandboxing**: Each agent declares capabilities on handshake
- **Immutable capabilities**: Once set, cannot be modified during session
- **Rate limiting**: Time-based sliding window per tool
- **Approval gates**: High-risk tools require Igor approval before execution
- **Audit logging**: All tool calls logged to memory substrate

---

*Last updated: 2026-01-04*

